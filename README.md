# ATS Resume Analyzer

A production-ready resume analysis application that scores resumes against job descriptions and returns actionable feedback. The project combines a FastAPI backend (NLP + scoring) with a Streamlit frontend (user UI). It uses spaCy and Sentence Transformers for parsing and semantic matching, and optionally leverages the Groq LLM API for richer feedback.

This README covers quickstart, development, containerized runs, testing, and deployment notes.

## Highlights

- FastAPI backend with model-loading and health checks
- Streamlit frontend with components and reusable UI
- Resume parsing (PDF/DOC/DOCX), skill extraction, semantic JD matching
- Upload protections (MIME + extension checks, max size)
- Docker-friendly with `docker-compose.yml` for local integration
- Deployment guide in `DEPLOYMENT.md`

## Repository layout

Top-level layout (important directories):

```
.
├── backend/                # FastAPI app, services, models
├── frontend/               # Streamlit UI and components
├── tests/                  # Unit, integration and e2e tests
├── jupyter notebooks/      # Research and experiments (not required at runtime)
├── docker-compose.yml
├── .env.example
└── DEPLOYMENT.md           # Deployment & verification guide
```

## Quickstart

There are two primary ways to run the project locally: (A) with Docker Compose (recommended for parity with deployment) or (B) in a Python virtualenv.

### A. Docker Compose (recommended)

1. Copy `.env.example` to `.env` and fill in development keys as needed.
2. Build and run:

```bash
docker compose up --build
```

This starts:

- Backend: `http://localhost:8000` (health: `/api/v1/health`)
- Frontend: `http://localhost:8501`

Open the Streamlit UI and exercise the upload + analysis flow.

### B. Local Python (dev)

1. Create and activate a virtual environment:

```bash
python -m venv .venv
# Windows
.\.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate
```

1. Install dependencies and download spaCy model:

```bash
pip install -r requirements.txt
python -m spacy download en_core_web_md
```

1. Copy environment template and run services:

```bash
cp .env.example .env
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
streamlit run frontend/streamlit_app.py
```

## Environment variables

Use `.env.example` as the source of truth. Key variables include:

- `ENVIRONMENT` — `development` or `production` (production enables fail-fast env validation)
- `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` for the backend and `SUPABASE_ANON_KEY` for the frontend
- `SUPABASE_JWT_SECRET` only when legacy HS256 token verification is still needed
- `GROQ_API_KEY` — optional but recommended for LLM suggestions
- `ALLOWED_ORIGINS` — optional comma-separated browser origins for CORS
- `AUTH_REDIRECT_URL` — Streamlit app URL used by Supabase email/OAuth redirects
- `MOCK_AUTH` — set `true` for local testing without real auth providers
- `ATS_FAST_MODEL_MODE` — test-only switch used by CI to avoid downloading NLP models

See `DEPLOYMENT.md` for example dev/prod envs and recommended values.

## Testing

The automated suite runs in deterministic CI mode:

- `MOCK_AUTH=true`
- in-memory history store
- local Groq parser fallback
- lightweight deterministic model stubs for browser E2E startup

Generate ignored resume/JD fixtures when you want to inspect or reuse them locally:

```bash
python tests/generate_fixtures.py
```

Run unit/integration tests:

```bash
pytest tests/ -v -k "not test_e2e"
```

Run browser E2E:

```bash
pytest tests/test_e2e.py -v
```

CI is configured to run linting and tests; run the same checks locally before pushing:

```bash
ruff check .
black --check .
pytest tests/ -v
```

For real pre-production validation, start the stack with real Supabase/Groq values and `MOCK_AUTH=false`; do not use this mode for CI. The E2E harness can be forced into that mode with `PRE_PROD=true`.

To catch formatting issues before they reach CI, install and enable pre-commit hooks once:

```bash
pip install pre-commit
pre-commit install
```

## Deployment

Recommended flow:

- Backend: Railway (supports Docker and long-running ML workloads)
- Frontend: Streamlit Community Cloud, or deploy the Streamlit container on Railway

The backend Docker image installs the OCR runtime binaries (`tesseract-ocr` and `poppler-utils`) so scanned PDF support works in containers as well as locally.
When deploying the backend on Railway, set the service Dockerfile path to `backend/Dockerfile`; do not rely on root-level auto-detection.

See `DEPLOYMENT.md` for step-by-step instructions, smoke tests, and troubleshooting guidance.

## Load Testing

The `load/locustfile.py` scenario exercises normal resume uploads, OCR-backed scanned PDFs, and malformed file handling.

Run it with mock auth enabled for local or container benchmarking:

```bash
MOCK_AUTH=true locust -f load/locustfile.py --host=http://localhost:8000
```

Use Locust's UI or CLI flags to test 10, 25, 50, and 100 concurrent users. The script fails the run when p95 latency exceeds `LOCUST_P95_THRESHOLD_MS` (default `2000`) or failure rate exceeds `LOCUST_FAILURE_RATE_THRESHOLD` (default `0.01`).

## Troubleshooting & Tips

- If startup fails complaining about missing env vars in production, ensure `ENVIRONMENT=production` and required keys are present; the service is intentionally fail-fast in production.
- If spaCy model fallback occurs, confirm `en_core_web_md` is installed or increase container memory / pre-pull models during image build.
- If scanned PDFs do not OCR correctly, install the OCR runtime binaries (`poppler` and `tesseract`) on the host image in addition to the Python packages.
- For parsing errors with malformed PDFs, check backend logs (`docker compose logs backend --follow`) — the parser returns a 422 on parse failures.

## Contributing

Please follow the repo's linting rules and tests. Opening PRs that include small, focused changes and tests is appreciated.

1. Fork and branch from `main`.
2. Run tests locally.
3. Open a pull request with a clear description and test coverage for non-trivial changes.

## License

This project is provided under the MIT license (see `LICENSE` if present).

---
