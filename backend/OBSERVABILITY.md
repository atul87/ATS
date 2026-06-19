Prometheus metrics

This project exposes basic Prometheus metrics from the backend API.

Endpoints

- `/metrics` - Prometheus scrape endpoint (text/plain; version=0.0.4).

Metrics included

- `ats_requests_total{method,endpoint,http_status}` - total HTTP requests.
- `ats_request_latency_seconds{method,endpoint}` - histogram of request latency.
- `ats_model_load_seconds{model}` - gauge capturing model load time in seconds.

How to scrape locally

1. Install dependencies:

   pip install -r requirements.txt

2. Start the backend (example):

```powershell
.venv\Scripts\Activate.ps1
$env:MOCK_AUTH='true'
$env:ATS_FAST_MODEL_MODE='false'  # if you want real model loads
python -m uvicorn backend.main:app --port 8000
```

1. Point Prometheus or curl to `http://127.0.0.1:8000/metrics`.

Notes

- The metrics integration is intentionally lightweight. For production, consider:
  - adding labels for `environment`, `commit`, or `instance_id`.
  - using a pushgateway or OTLP exporter for tracing alongside metrics.
  - securing the `/metrics` endpoint behind auth in multi-tenant environments.
