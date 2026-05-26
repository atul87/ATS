import time
import requests
from pathlib import Path

BACKEND_URL = "http://127.0.0.1:8000/api/v1/analyze-resume"
AUTH_HEADER = {"Authorization": "Bearer mock-access-token"}
FIX_DIR = Path("tests/fixtures/generated")

FILES = [
    "good_resume.docx",
    "good_resume.pdf",
    "resume_scanned_image.pdf",
    "bad_resume.pdf",
    "empty.pdf",
    "large_resume.pdf",
    "unicode_resume.docx",
    "table_resume.docx",
    "too_large.pdf",
]

results = []

for fname in FILES:
    path = FIX_DIR / fname
    if not path.exists():
        print(f"Skipping missing fixture: {path}")
        continue
    print(f"Uploading {fname}...")
    with open(path, "rb") as f:
        files = {"resume": (fname, f)}
        data = {"job_description": "Python FastAPI SQL"}
        start = time.time()
        try:
            resp = requests.post(
                BACKEND_URL, files=files, data=data, headers=AUTH_HEADER, timeout=120
            )
            latency = time.time() - start
            try:
                body = resp.json()
            except Exception:
                body = resp.text[:1000]
            results.append(
                {
                    "file": fname,
                    "status_code": resp.status_code,
                    "latency_s": round(latency, 3),
                    "body_summary": (body if isinstance(body, dict) else str(body)),
                }
            )
            print(f"{fname}: {resp.status_code} in {latency:.3f}s")
        except Exception as e:
            latency = time.time() - start
            results.append(
                {
                    "file": fname,
                    "status_code": "error",
                    "latency_s": round(latency, 3),
                    "body_summary": str(e),
                }
            )
            print(f"{fname}: ERROR {e}")

print("\nSummary:")
for r in results:
    print(r)
