import os
import sys
import time
import subprocess
import pytest
import requests
import docx
from pathlib import Path


@pytest.fixture(scope="module")
def app_servers():
    # Setup paths
    logs_dir = Path("logs")
    logs_dir.mkdir(parents=True, exist_ok=True)

    backend_log_path = logs_dir / "backend_server.log"
    frontend_log_path = logs_dir / "frontend_server.log"

    # Open files for writing stdout/stderr
    backend_log = open(backend_log_path, "w", encoding="utf-8")
    frontend_log = open(frontend_log_path, "w", encoding="utf-8")

    # Build environment with MOCK_AUTH=true
    env = os.environ.copy()
    env["MOCK_AUTH"] = "true"

    # Launch backend (uvicorn)
    backend_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.main:app", "--port", "8000"],
        env=env,
        stdout=backend_log,
        stderr=backend_log,
    )

    # Launch frontend (streamlit)
    frontend_proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            "frontend/streamlit_app.py",
            "--server.port",
            "8501",
            "--server.address",
            "127.0.0.1",
        ],
        env=env,
        stdout=frontend_log,
        stderr=frontend_log,
    )

    # Wait/Poll health endpoints
    start_time = time.time()
    backend_ready = False
    frontend_ready = False

    while (
        time.time() - start_time < 60
    ):  # Allow up to 60 seconds for models to load and server to start
        # Check backend
        if not backend_ready:
            try:
                r = requests.get("http://127.0.0.1:8000/api/v1/health", timeout=1)
                if r.status_code == 200:
                    backend_ready = True
            except Exception:
                pass
        # Check frontend
        if not frontend_ready:
            try:
                r = requests.get("http://127.0.0.1:8501", timeout=1)
                if r.status_code == 200:
                    frontend_ready = True
            except Exception:
                pass

        if backend_ready and frontend_ready:
            break

        time.sleep(1)
    else:
        # Teardown processes before raising
        backend_proc.terminate()
        frontend_proc.terminate()
        backend_proc.wait()
        frontend_proc.wait()
        backend_log.close()
        frontend_log.close()
        raise RuntimeError(
            f"Servers failed to start within 60 seconds. "
            f"Backend ready: {backend_ready}, Frontend ready: {frontend_ready}. "
            f"Check logs at {backend_log_path} and {frontend_log_path}"
        )

    yield "http://127.0.0.1:8501"

    # Teardown
    backend_proc.terminate()
    frontend_proc.terminate()
    try:
        backend_proc.wait(timeout=5)
    except Exception:
        backend_proc.kill()
    try:
        frontend_proc.wait(timeout=5)
    except Exception:
        frontend_proc.kill()

    backend_log.close()
    frontend_log.close()


def test_e2e_happy_path(app_servers, page, tmp_path):
    # 1. Open the page in browser
    page.goto(app_servers)

    # 2. Wait for sign-in tab/form to load
    page.wait_for_selector("text=Sign in", timeout=15000)

    # Fill in the sign-in form
    page.locator("input[aria-label='Email']:visible").first.fill("test@example.com")
    page.locator("input[aria-label='Password']:visible").first.fill("password123")

    # Submit the form
    page.locator("[data-testid='stFormSubmitButton'] button:visible").first.click()

    # 3. Verify sidebar changes to "Signed in as test@example.com"
    page.wait_for_selector("text=Signed in as test@example.com", timeout=15000)

    # 4. Click "🎯 ATS Scorer"
    page.locator("button:has-text('ATS Scorer')").click()

    # Wait for the Scorer page view
    page.locator("text=Upload your resume to begin").wait_for(state="visible", timeout=15000)

    # 5. Dynamically write a valid DOCX resume to disk
    resume_path = tmp_path / "resume.docx"
    doc = docx.Document()
    doc.add_heading("John Doe", 0)
    doc.add_paragraph("Email: john.doe@example.com")
    doc.add_heading("Experience", level=1)
    doc.add_paragraph(
        "Senior Python Developer at Tech Corp. Developed and scaled backend APIs using FastAPI and Python."
    )
    doc.add_heading("Skills", level=1)
    doc.add_paragraph("Python, FastAPI, Docker, SQL, Git")
    doc.save(str(resume_path))

    # Upload it
    page.locator("input[type='file']").first.set_input_files(str(resume_path))

    # Wait for upload completion message in Streamlit
    page.locator("text=resume.docx").wait_for(state="visible", timeout=15000)

    # 6. Run resume analysis
    page.locator("button:has-text('Analyze Resume')").click()

    # 7. Verify that the results dashboard shows the score
    page.locator("text=Analysis Results").wait_for(state="visible", timeout=30000)
    page.locator("text=Overall ATS Score").wait_for(state="visible", timeout=30000)

    # 8. Check that the history page displays the entry
    page.locator("button:has-text('History')").click()
    page.locator("text=Analysis History").wait_for(state="visible", timeout=15000)
    page.locator("text=resume.docx").first.wait_for(state="visible", timeout=15000)


def test_e2e_error_path(app_servers, page, tmp_path):
    # 1. Open the page in browser
    page.goto(app_servers)

    # 2. Check if we are already signed in.
    if not page.locator("text=Signed in as").is_visible():
        page.wait_for_selector("text=Sign in", timeout=15000)
        page.locator("input[aria-label='Email']:visible").first.fill("test@example.com")
        page.locator("input[aria-label='Password']:visible").first.fill("password123")
        page.locator("[data-testid='stFormSubmitButton'] button:visible").first.click()
        page.wait_for_selector("text=Signed in as test@example.com", timeout=15000)

    # 3. Click "🎯 ATS Scorer"
    page.locator("button:has-text('ATS Scorer')").click()

    # Wait for the Scorer page view
    page.locator("text=Upload your resume to begin").wait_for(state="visible", timeout=15000)

    # 4. Upload a malformed file (e.g. empty file named corrupt.pdf)
    corrupt_path = tmp_path / "corrupt.pdf"
    corrupt_path.write_bytes(b"")

    page.locator("input[type='file']").first.set_input_files(str(corrupt_path))

    # Wait for upload completion message
    page.locator("text=corrupt.pdf").wait_for(state="visible", timeout=15000)

    # 5. Click analyze
    page.locator("button:has-text('Analyze Resume')").click()

    # 6. Verify that the UI reports "Could not read or parse the resume"
    page.locator("text=Could not read or parse the resume").wait_for(state="visible", timeout=30000)


def test_e2e_artifact_generation_on_failure(tmp_path):
    import subprocess
    import sys
    from pathlib import Path

    # 1. Create a dummy test file that uses playwright page fixture and fails
    dummy_test_file = tmp_path / "test_dummy_failure_for_artifacts.py"
    dummy_test_file.write_text("""
def test_dummy_fail_run(page):
    page.goto("about:blank")
    assert False
""")

    import shutil

    shutil.copy("tests/conftest.py", tmp_path / "conftest.py")

    # 2. Clean up any existing matching artifacts
    artifacts_dir = Path("artifacts")
    if artifacts_dir.exists():
        for f in artifacts_dir.glob("failure_test_dummy_fail_run*.png"):
            try:
                f.unlink()
            except Exception:
                pass
        for f in artifacts_dir.glob("trace_test_dummy_fail_run*.zip"):
            try:
                f.unlink()
            except Exception:
                pass

    # 3. Execute pytest in a subprocess
    res = subprocess.run(
        [sys.executable, "-m", "pytest", str(dummy_test_file), "-v"],
        capture_output=True,
        text=True,
        cwd="e:/ATS",
    )

    # 4. Assert that the test failed
    assert res.returncode != 0

    # 5. Assert that the screenshot and trace were created
    screenshots = list(artifacts_dir.glob("failure_test_dummy_fail_run*.png"))
    traces = list(artifacts_dir.glob("trace_test_dummy_fail_run*.zip"))

    assert (
        len(screenshots) > 0
    ), f"Failure screenshot not created! Pytest Output: {res.stdout}\n{res.stderr}"
    assert len(traces) > 0, f"Failure trace not created! Pytest Output: {res.stdout}\n{res.stderr}"

    # 6. Clean up the created files
    for f in screenshots:
        try:
            f.unlink()
        except Exception:
            pass
    for f in traces:
        try:
            f.unlink()
        except Exception:
            pass
