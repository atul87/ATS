import requests
from pathlib import Path
import json

BASE = "http://127.0.0.1:8000/api/v1"
HEADERS = {"Authorization": "Bearer mock-access-token"}
ARTIFACTS = Path("artifacts")
ARTIFACTS.mkdir(exist_ok=True)

# Fetch history
resp = requests.get(f"{BASE}/history", headers=HEADERS)
if resp.status_code != 200:
    print("Failed to fetch history", resp.status_code, resp.text)
    exit(1)
h = resp.json()
if not h:
    print("No history entries available")
    exit(0)

entry = h[0]
entry_id = entry["id"]
print("Using history entry", entry_id)

# Download history PDF
r_pdf = requests.get(f"{BASE}/history/{entry_id}/pdf", headers=HEADERS)
print("history pdf status", r_pdf.status_code)
if r_pdf.status_code == 200:
    p = ARTIFACTS / f"history_{entry_id}.pdf"
    p.write_bytes(r_pdf.content)
    print("Wrote", p)
else:
    print("History PDF error:", r_pdf.status_code, r_pdf.text[:200])

# POST generate-pdf using analysis_result
analysis = entry.get("analysis_result")
if not analysis:
    print("No analysis_result found")
    exit(0)

# The /generate-pdf expects JSON body matching AnalysisResponse model
r_gen = requests.post(
    f"{BASE}/generate-pdf",
    headers={**HEADERS, "Content-Type": "application/json"},
    data=json.dumps(analysis),
)
print("generate-pdf status", r_gen.status_code)
if r_gen.status_code == 200:
    p2 = ARTIFACTS / f"generated_{entry_id}.pdf"
    p2.write_bytes(r_gen.content)
    print("Wrote", p2)
else:
    print("Generate PDF error:", r_gen.status_code, r_gen.text[:500])
