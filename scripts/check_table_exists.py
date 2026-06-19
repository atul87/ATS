"""
Simple check to verify `analyses` table exists in Supabase via PostgREST.
Usage:
  SUPABASE_URL=https://... SUPABASE_ANON_KEY=... python scripts/check_table_exists.py
"""

import os
import sys
import requests

# Attempt to load environment from a local .env file if python-dotenv is available
try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    # If dotenv isn't installed, continue — env vars may be provided by the shell.
    pass

SUPABASE_URL = os.environ.get("SUPABASE_URL")
ANON_KEY = os.environ.get("SUPABASE_ANON_KEY")

if not SUPABASE_URL or not ANON_KEY:
    print("Missing SUPABASE_URL or SUPABASE_ANON_KEY environment variables.")
    sys.exit(2)

url = SUPABASE_URL.rstrip("/") + "/rest/v1/analyses?select=id&limit=1"
headers = {
    "apikey": ANON_KEY,
    "Authorization": f"Bearer {ANON_KEY}",
    "Accept": "application/json",
}

try:
    resp = requests.get(url, headers=headers, timeout=10)
except Exception as e:
    print(f"ERROR: Request failed: {e}")
    sys.exit(2)

if resp.status_code == 200:
    print("PASS analyses table exists")
    sys.exit(0)
else:
    print(f"FAIL analyses table check: HTTP {resp.status_code}\n{resp.text}")
    sys.exit(3)
