import requests

url = "http://127.0.0.1:8000/api/v1/history"
headers = {"Authorization": "Bearer mock-access-token"}
resp = requests.get(url, headers=headers)
print("status", resp.status_code)
try:
    print(resp.json())
except Exception:
    print(resp.text)
