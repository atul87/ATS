import time
import requests
from pathlib import Path
import json

BACKEND = "http://127.0.0.1:8000/api/v1/analyze-resume"
HEADERS = {"Authorization": "Bearer mock-access-token"}

fixtures_dir = Path("tests/fixtures/generated")
files = sorted([p for p in fixtures_dir.glob("*") if p.is_file()])
results = []

for p in files:
    start = time.time()
    with open(p, "rb") as fh:
        files_payload = {"resume": (p.name, fh, "application/octet-stream")}
        data = {"job_description": "Python FastAPI SQL"}
        try:
            resp = requests.post(
                BACKEND, headers=HEADERS, files=files_payload, data=data, timeout=30
            )
        except Exception as e:
            latency = time.time() - start
            results.append(
                {"file": p.name, "status_code": None, "latency_s": latency, "error": str(e)}
            )
            print(f"{p.name}: ERROR {e}")
            continue
    latency = time.time() - start
    try:
        j = resp.json()
    except Exception:
        j = {"raw_text": resp.text}
    # try to extract score keys commonly used
    score = None
    for key in ("overall_score", "ats_score", "ATS_score", "overall", "score"):
        if isinstance(j, dict) and key in j:
            score = j[key]
            break
    # also try nested analysis
    if score is None and isinstance(j, dict):
        for candidate in ("analysis", "body_summary", "result", "data"):
            if candidate in j and isinstance(j[candidate], dict):
                for key in ("overall_score", "overall", "ats_score", "ATS_score"):
                    if key in j[candidate]:
                        score = j[candidate][key]
                        break
                if score is not None:
                    break
    results.append(
        {
            "file": p.name,
            "status_code": resp.status_code,
            "latency_s": round(latency, 3),
            "score": score,
            "body": j,
        }
    )
    print(f"{p.name}: {resp.status_code} in {latency:.3f}s -> score={score}")

# summary
scores = [r["score"] for r in results if isinstance(r.get("score"), (int, float))]
print("\nSummary:")
print(f"Files tested: {len(results)}")
print(f"Successful scores: {len(scores)}")
if scores:
    import statistics

    print(f"Mean: {statistics.mean(scores):.1f}")
    print(f"Min: {min(scores)}")
    print(f"Max: {max(scores)}")

# Save results

Path("artifacts").mkdir(exist_ok=True)
with open("artifacts/ats_batch_results.json", "w", encoding="utf-8") as fh:
    json.dump(results, fh, indent=2, ensure_ascii=False)
print("Results written to artifacts/ats_batch_results.json")
