# Deployment guide

This document describes quick deployment and verification steps for the ATS project.

## Local (developer smoke test)

Build and run both services locally with Docker Compose:

```bash
docker compose up --build
```

Open these endpoints to verify services are running:

- Backend health: <http://localhost:8000/api/v1/health>
- Release Version: <http://localhost:8000/version> (also <http://localhost:8000/api/v1/version>)
- Build Metadata: <http://localhost:8000/build> (also <http://localhost:8000/api/v1/build>)
- Commit SHA: <http://localhost:8000/commit> (also <http://localhost:8000/api/v1/commit>)
- Frontend (Streamlit): <http://localhost:8501>

### Release Metadata Endpoints

The backend exposes three metadata endpoints that return details about the deployment:

1. **/version**

   ```json
   {
     "version": "0.9.0-beta",
     "environment": "preprod",
     "commit": "46b41b9"
   }
   ```

2. **/build**

   ```json
   {
     "build_time": "2026-05-23T12:45:00Z",
     "environment": "preprod",
     "fast_mode": false
   }
   ```

3. **/commit**

   ```json
   {
     "commit": "46b41b9",
     "source": "git"
   }
   ```

Note: The `BUILD_TIME` environment variable is automatically injected during container build time. In Docker Compose, this is passed using the build arg `BUILD_TIME`.

## Development environment (recommended env)

Use a development `.env` with these values (example):

```env
ENVIRONMENT=development
MOCK_AUTH=true
```

Set any other test keys from `.env.example` as needed.

## Production environment (required keys)

In production you must set these environment variables (example):

```env
ENVIRONMENT=production
SUPABASE_URL=https://your-supabase-url
SUPABASE_SERVICE_KEY=service_role_key_here
GROQ_API_KEY=your_groq_api_key
MOCK_AUTH=false
```

Notes:

- When `ENVIRONMENT=production` the backend will fail-fast if required env vars are missing.
- Use the values from `.env.example` as a guide.

## Smoke test checklist

- [ ] ✓ health endpoint responds and models loaded
- [ ] ✓ upload a normal resume and receive analysis
- [ ] ✓ upload a malformed/edge-case PDF and observe handled error
- [ ] ✓ generate PDF report via `/api/v1/generate-pdf`
- [ ] ✓ fetch history via `/api/v1/history`
- [ ] ✓ inspect startup logs for model load times and env validation
- [ ] ✓ metadata endpoints (`/version`, `/build`, `/commit`) respond with correct JSON payloads

## Deploying backend (Railway recommended)

1. Sign in to Railway with GitHub and create a new project.
2. Choose "Deploy from GitHub" and select this repository (`atul87/ATS`).
3. Add environment variables from the **Production environment** section.
4. Configure build command (optional): `docker build -t ats_backend backend/` or allow Railway to use the `Dockerfile` at `backend/Dockerfile`.
5. Railway will build and deploy on push. Monitor logs for startup and model-loading messages.

## Deploying frontend

Option A — Streamlit Community Cloud:

1. Sign in with GitHub and create a new app from this repo.
2. Set the entrypoint to `frontend/streamlit_app.py` and provide only frontend-safe secrets: `SUPABASE_URL`, `SUPABASE_ANON_KEY`, and `BACKEND_API_URL`.

Option B — Deploy the Streamlit container on Railway (use `frontend/Dockerfile`).

## Post-deploy verification

- Confirm backend `/api/v1/health` shows `nlp_loaded: true` and `embedder_loaded: true`.
- Run a few sample uploads to ensure parsing and scoring behave as expected.
- Verify logs for any warnings about missing env vars or model load fallbacks.

## Troubleshooting

- If startup fails with missing env vars: ensure `ENVIRONMENT` and required keys are present.
- If model load falls back to a smaller spaCy model, consider provisioning more memory or pre-pulling models in your container build step.

## Additions

- Keep `.env.example` updated with any new secrets.
- Ensure `artifacts/`, `logs/`, `.pytest_cache/`, and `playwright-report/` are in `.gitignore` (already included).

## Load Testing & SLA Thresholds

To verify the performance of the ATS resume scoring engine under concurrency, we run load tests using [Locust](file:///e:/ATS/load/locustfile.py).

### How to Run Load Tests

1. Start the backend locally:

   ```bash
   uvicorn backend.main:app --port 8000
   ```

2. Run Locust from the root directory:

   ```bash
   locust -f load/locustfile.py --host=http://localhost:8000
   ```

3. Open the Locust web UI at <http://localhost:8089> to configure spawn rate and target users.

### SLA Performance Thresholds

For production readiness, the application must meet the following SLAs under a concurrent load of up to 50 users:

- **95th Percentile Latency**: `< 2.0 seconds` for resume analysis requests.
- **Error Rate**: `< 1.0%` total error rate during sustained testing.
- **Resource Constraints**: Backend memory utilization must remain under `2GB` (configured in docker-compose.yml mem_limit).

## Database Setup (Supabase)

The project uses Supabase as a persistent storage backend when `MOCK_AUTH=false`. The `analyses` table stores parsed results and history.

### SQL Schema Definitions

Run the following SQL in your Supabase SQL Editor to create the necessary table and security policies:

```sql
-- Create the analyses table
CREATE TABLE public.analyses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    filename TEXT NOT NULL,
    ats_score NUMERIC NOT NULL DEFAULT 0,
    keyword_match NUMERIC NOT NULL DEFAULT 0,
    missing_keywords JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    analysis_result JSONB NOT NULL DEFAULT '{}'::jsonb
);

-- Enable Row Level Security (RLS)
ALTER TABLE public.analyses ENABLE ROW LEVEL SECURITY;

-- RLS Policies
CREATE POLICY "Users can insert their own analyses" ON public.analyses
    FOR INSERT WITH CHECK (auth.uid()::text = user_id::text);

CREATE POLICY "Users can view their own analyses" ON public.analyses
    FOR SELECT USING (auth.uid()::text = user_id::text);

CREATE POLICY "Users can delete their own analyses" ON public.analyses
    FOR DELETE USING (auth.uid()::text = user_id::text);

-- Indexes for performance
CREATE INDEX idx_analyses_user_id ON public.analyses(user_id);
CREATE INDEX idx_analyses_created_at ON public.analyses(created_at DESC);
CREATE INDEX idx_analyses_user_created ON public.analyses(user_id, created_at DESC);
```
