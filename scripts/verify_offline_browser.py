import os
import time
import subprocess
from pathlib import Path
from playwright.sync_api import sync_playwright

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_PORT = 8011
FRONTEND_PORT = 8511
BACKEND_URL = f"http://127.0.0.1:{BACKEND_PORT}"
FRONTEND_URL = f"http://127.0.0.1:{FRONTEND_PORT}"


def main():
    print("Starting backend and frontend servers for verification...")
    # Prepare environment
    env = os.environ.copy()
    env["MOCK_AUTH"] = "true"
    env["ATS_FAST_MODEL_MODE"] = "true"
    env["E2E_TESTING"] = "false"  # Enable auto-login
    env["BACKEND_API_URL"] = BACKEND_URL

    logs_dir = REPO_ROOT / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    # Launch backend (uvicorn)
    backend_log = open(logs_dir / "verify_backend.log", "w", encoding="utf-8")
    backend_proc = subprocess.Popen(
        [
            os.path.join(REPO_ROOT, ".venv", "Scripts", "python.exe"),
            "-m",
            "uvicorn",
            "backend.main:app",
            "--port",
            str(BACKEND_PORT),
        ],
        cwd=str(REPO_ROOT),
        env=env,
        stdout=backend_log,
        stderr=backend_log,
    )

    # Launch frontend (streamlit)
    frontend_log = open(logs_dir / "verify_frontend.log", "w", encoding="utf-8")
    frontend_proc = subprocess.Popen(
        [
            os.path.join(REPO_ROOT, ".venv", "Scripts", "python.exe"),
            "-m",
            "streamlit",
            "run",
            "frontend/streamlit_app.py",
            "--server.port",
            str(FRONTEND_PORT),
            "--server.address",
            "127.0.0.1",
        ],
        cwd=str(REPO_ROOT),
        env=env,
        stdout=frontend_log,
        stderr=frontend_log,
    )

    # Wait for backend and frontend to be ready
    print("Waiting for servers to start...")
    time.sleep(15)

    try:
        with sync_playwright() as p:
            print("Launching browser...")
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1280, "height": 720})
            page = context.new_page()

            print(f"Navigating to {FRONTEND_URL}...")
            page.goto(FRONTEND_URL)
            time.sleep(5)

            # Save landing page screenshot
            artifacts_dir = REPO_ROOT / "artifacts"
            artifacts_dir.mkdir(parents=True, exist_ok=True)

            landing_screenshot = artifacts_dir / "verify_1_landing.png"
            page.screenshot(path=str(landing_screenshot))
            print(f"Saved landing screenshot: {landing_screenshot}")

            # Click ATS Scorer
            print("Navigating to ATS Scorer...")
            page.locator("button:has-text('ATS Scorer')").click()
            time.sleep(3)
            scorer_screenshot = artifacts_dir / "verify_2_scorer.png"
            page.screenshot(path=str(scorer_screenshot))
            print(f"Saved scorer screenshot: {scorer_screenshot}")

            # Upload resume
            resume_path = REPO_ROOT / "tests" / "fixtures" / "generated" / "good_resume.docx"
            print(f"Uploading resume: {resume_path}...")
            page.locator("input[type='file']").first.set_input_files(str(resume_path))
            time.sleep(3)
            upload_screenshot = artifacts_dir / "verify_3_uploaded.png"
            page.screenshot(path=str(upload_screenshot))
            print(f"Saved upload screenshot: {upload_screenshot}")

            # Run analysis
            print("Running analysis...")
            page.locator("button:has-text('Analyze Resume')").click()
            time.sleep(20)  # Wait for full analysis pipeline
            analysis_screenshot = artifacts_dir / "verify_4_results.png"
            page.screenshot(path=str(analysis_screenshot))
            print(f"Saved analysis results screenshot: {analysis_screenshot}")

            # Navigate to History
            print("Navigating to History...")
            page.locator("button:has-text('History')").click()
            time.sleep(5)
            history_screenshot = artifacts_dir / "verify_5_history.png"
            page.screenshot(path=str(history_screenshot))
            print(f"Saved history screenshot: {history_screenshot}")

            print("Browser verification completed successfully!")

    except Exception as e:
        print(f"Error occurred during verification: {e}")
        import traceback

        traceback.print_exc()
    finally:
        print("Terminating servers...")
        backend_proc.terminate()
        frontend_proc.terminate()
        backend_proc.wait()
        frontend_proc.wait()
        backend_log.close()
        frontend_log.close()


if __name__ == "__main__":
    main()
