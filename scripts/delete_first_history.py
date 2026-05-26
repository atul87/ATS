import requests

BASE = "http://127.0.0.1:8000/api/v1"
HEADERS = {"Authorization": "Bearer mock-access-token"}

# get history
resp = requests.get(f"{BASE}/history", headers=HEADERS)
print("GET history", resp.status_code)
hist = resp.json()
if not hist:
    print("No history to delete")
    exit(0)
first_id = hist[0]["id"]
print("Deleting", first_id)
resp2 = requests.delete(f"{BASE}/history/{first_id}", headers=HEADERS)
print("DELETE", resp2.status_code, resp2.text)
# fetch again
resp3 = requests.get(f"{BASE}/history", headers=HEADERS)
print("After GET", resp3.status_code, len(resp3.json()))
