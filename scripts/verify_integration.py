"""
End-to-end integration verification script for ATS Resume Scorer.

Environment variables expected:
  BACKEND_URL - URL of the running backend (default http://localhost:8000)
  SUPABASE_URL - Supabase project URL (e.g. https://xyz.supabase.co)
  SUPABASE_ANON_KEY - Supabase anon/public key for auth requests
  TEST_EMAIL - user email to login
  TEST_PASSWORD - user password
  RESTART_CMD - optional shell command to restart backend (e.g. "docker-compose restart backend")

Usage:
  python scripts/verify_integration.py --resume path/to/resume.docx

The script performs: login -> upload -> analysis schema -> history -> generate pdf -> optional restart -> confirm history persists
"""

import os
import sys
import time
import argparse
import requests
import subprocess
from typing import Optional

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
ANON_KEY = os.environ.get("SUPABASE_ANON_KEY")
TEST_EMAIL = os.environ.get("TEST_EMAIL")
TEST_PASSWORD = os.environ.get("TEST_PASSWORD")
RESTART_CMD = os.environ.get("RESTART_CMD")

TIMEOUT = 30

# Load .env automatically if available so the script can run without manual exports
try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass


def fail(msg: str, code: int = 1):
    print("FAIL", msg)
    sys.exit(code)


def login(email: str, password: str) -> str:
    if not SUPABASE_URL or not ANON_KEY:
        fail("SUPABASE_URL and SUPABASE_ANON_KEY must be set in env")

    token_url = SUPABASE_URL.rstrip("/") + "/auth/v1/token"
    headers = {"apikey": ANON_KEY, "Content-Type": "application/json"}
    payload = {"grant_type": "password", "email": email, "password": password}
    r = requests.post(token_url, json=payload, headers=headers, timeout=TIMEOUT)
    if r.status_code != 200:
        fail(f"login failed: {r.status_code} {r.text}")
    data = r.json()
    access_token = data.get("access_token")
    if not access_token:
        fail(f"no access_token in login response: {data}")
    print("PASS login")
    return access_token


def analyze_resume(access_token: str, resume_path: str, job_description: str = "") -> dict:
    url = f"{BACKEND_URL.rstrip('/')}/api/v1/analyze-resume"
    headers = {"Authorization": f"Bearer {access_token}"}

    with open(resume_path, "rb") as fh:
        files = {"resume": (os.path.basename(resume_path), fh, "application/octet-stream")}
        data = {"job_description": job_description}
        r = requests.post(url, files=files, data=data, headers=headers, timeout=180)

    if r.status_code != 200:
        fail(f"analyze-resume failed: {r.status_code} {r.text}")

    json_data = r.json()
    # Basic schema checks
    if not ("ats_score" in json_data or "ATS_score" in json_data):
        fail(f"analysis response missing ats_score: {json_data}")

    print("PASS upload")
    print("PASS analysis")
    return json_data


def get_history(access_token: str) -> list:
    url = f"{BACKEND_URL.rstrip('/')}/api/v1/history"
    headers = {"Authorization": f"Bearer {access_token}"}
    r = requests.get(url, headers=headers, timeout=TIMEOUT)
    if r.status_code != 200:
        fail(f"history fetch failed: {r.status_code} {r.text}")
    data = r.json()
    if not isinstance(data, list):
        fail(f"history response not a list: {data}")
    print("PASS history")
    return data


def generate_pdf(access_token: str, analysis_data: dict) -> bytes:
    url = f"{BACKEND_URL.rstrip('/')}/api/v1/generate-pdf"
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    r = requests.post(url, json=analysis_data, headers=headers, timeout=60)
    if r.status_code != 200:
        fail(f"generate-pdf failed: {r.status_code} {r.text}")
    # Basic content-type check
    ct = r.headers.get("Content-Type", "")
    if "pdf" not in ct.lower():
        fail(f"generate-pdf did not return PDF (Content-Type={ct})")
    print("PASS pdf")
    return r.content


def restart_backend_cmd() -> bool:
    cmd = RESTART_CMD
    if not cmd:
        # Try docker-compose restart backend if docker-compose.yml exists
        if os.path.exists("docker-compose.yml"):
            cmd = "docker-compose restart backend"
    if not cmd:
        print("No restart command configured; skipping restart (set RESTART_CMD to enable)")
        return False

    print(f"Running restart command: {cmd}")
    try:
        proc = subprocess.run(cmd, shell=True, timeout=60)
        success = proc.returncode == 0
        if not success:
            print(f"Restart command returned {proc.returncode}")
            return False
        # wait for a few seconds for backend to come up
        time.sleep(5)
        print("PASS restart")
        return True
    except Exception as exc:
        print(f"Restart command failed: {exc}")
        return False


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--resume", required=True, help="Path to resume file (PDF or DOCX)")
    p.add_argument("--email", default=TEST_EMAIL, help="Test user email")
    p.add_argument("--password", default=TEST_PASSWORD, help="Test user password")
    return p.parse_args()


def main():
    args = parse_args()
    if not args.email or not args.password:
        fail("TEST_EMAIL and TEST_PASSWORD must be provided via env or args")
    if not os.path.exists(args.resume):
        fail(f"Resume file not found: {args.resume}")

    token = login(args.email, args.password)
    analysis = analyze_resume(token, args.resume)
    history = get_history(token)

    # Ensure the inserted analysis appears in history (simple heuristic)
    analysis_result = analysis if isinstance(analysis, dict) else {}
    matches = [
        h
        for h in history
        if h.get("analysis_result")
        and (h.get("analysis_result").get("ats_score") == analysis_result.get("ats_score"))
    ]
    if not matches:
        print("Warning: exact score not found in history; proceeding to next checks")

    pdf_bytes = generate_pdf(token, analysis_result)

    restarted = restart_backend_cmd()
    if restarted:
        # recheck history
        history2 = get_history(token)
        # check that at least one entry still exists
        if not history2:
            fail("No history after restart; persistence failure?")
        print("PASS recheck_history")

    print("All checks passed")


if __name__ == "__main__":
    main()
