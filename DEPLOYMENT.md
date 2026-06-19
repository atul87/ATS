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
     "version": "1.0.0",
     "environment": "production",
     "commit": "b7b1060"
   }
   ```

2. **/build**

   ```json
   {
     "build_time": "2026-05-31T12:00:00Z",
     "environment": "production",
     "fast_mode": false
   }
   ```

3. **/commit**

   ```json
   {
     "commit": "b7b1060",
     "source": "env"
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
SUPABASE_URL=https://lzudxufewzruizbwnunb.supabase.co
SUPABASE_SERVICE_KEY=<backend-only-secret-or-legacy-service-role-key>
SUPABASE_JWT_SECRET=legacy_hs256_jwt_secret_if_needed
GROQ_API_KEY=optional_groq_api_key
MOCK_AUTH=false
BUILD_TIME=2026-05-27T22:00:00Z
ALLOWED_ORIGINS=https://appapppy-ktwxupi73vqhjzweksze9d.streamlit.app,https://ekmfboeemgmecad7bfufbb.streamlit.app
AUTH_REDIRECT_URL=https://appapppy-ktwxupi73vqhjzweksze9d.streamlit.app
```

Notes:

- When `ENVIRONMENT=production` the backend will fail fast if `SUPABASE_URL` or
  the backend-only `SUPABASE_SERVICE_KEY` is missing. The legacy `SUPABASE_KEY`
  alias is still accepted.
- `SUPABASE_JWT_SECRET` is only required for legacy HS256 access tokens. Modern
  asymmetric tokens are verified through the project's JWKS endpoint.
- `GROQ_API_KEY` is optional. Without it, the app uses the local regex parser
  fallback.
- Set `BUILD_TIME` to the deployment timestamp, or inject it during the Docker build.
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
3. In the Railway service settings, set the Dockerfile path to `backend/Dockerfile`.
4. Add environment variables from the **Production environment** section.
5. Do not rely on Railpack auto-detection for this service; the FastAPI app lives under `backend/main.py`, so the repo-root heuristic will fail.
6. Railway will build and deploy on push. Monitor logs for startup and model-loading messages.

## Deploying frontend

Option A — Streamlit Community Cloud:

1. Sign in with GitHub and create a new app from this repo.
2. Set the entrypoint to `frontend/streamlit_app.py` and provide only frontend-safe secrets: `SUPABASE_URL`, `SUPABASE_ANON_KEY` or `SUPABASE_PUBLISHABLE_KEY`, plus backend URL as either `[backend].url` (preferred) or `BACKEND_API_URL`.

   Current production backend URL:

   ```text
   https://ats-production-9787.up.railway.app
   ```

   Keep the hyphens. `https://atsproduction9787.up.railway.app` is not the deployed app.

   Streamlit secrets can be top-level:

   ```toml
   BACKEND_API_URL = "https://ats-production-9787.up.railway.app"
   AUTH_REDIRECT_URL = "https://appapppy-ktwxupi73vqhjzweksze9d.streamlit.app"
   SUPABASE_URL = "https://lzudxufewzruizbwnunb.supabase.co"
   SUPABASE_ANON_KEY = "your_rotated_anon_or_publishable_key_here"
   ```

   Or include the nested layout too:

   ```toml
   BACKEND_API_URL = "https://ats-production-9787.up.railway.app"
   AUTH_REDIRECT_URL = "https://appapppy-ktwxupi73vqhjzweksze9d.streamlit.app"
   SUPABASE_URL = "https://lzudxufewzruizbwnunb.supabase.co"
   SUPABASE_ANON_KEY = "your_rotated_anon_or_publishable_key_here"

   [backend]
   url = "https://ats-production-9787.up.railway.app"

   [supabase]
   url = "https://lzudxufewzruizbwnunb.supabase.co"
   anon_key = "your_rotated_anon_or_publishable_key_here"
   ```

### Supabase Auth email settings

The current Supabase project requires email confirmation
(`mailer_autoconfirm=false`). For production sign-up to work for real users,
configure one of these in Supabase Dashboard > Authentication:

- Recommended: enable Custom SMTP so confirmation emails can be sent to all
  users. Supabase's default email service is only for testing and is restricted.
- Demo-only alternative: disable email confirmation if you intentionally want
  users to be signed in immediately after password sign-up.

Also set Authentication > URL Configuration:

```text
Site URL: https://appapppy-ktwxupi73vqhjzweksze9d.streamlit.app
Redirect URLs: https://appapppy-ktwxupi73vqhjzweksze9d.streamlit.app/**
```

Use the exact active Streamlit URL for `AUTH_REDIRECT_URL`. If both Streamlit
apps are still in use, include both origins in backend `ALLOWED_ORIGINS`, but
set `AUTH_REDIRECT_URL` to the one users should land on after auth.

Option B — Deploy the Streamlit container on Railway (use `frontend/Dockerfile`).

## Post-deploy verification

- Confirm backend `/api/v1/health` shows `nlp_loaded: true` and `embedder_loaded: true`.
- Run a few sample uploads to ensure parsing and scoring behave as expected.
- Verify logs for any warnings about missing env vars or model load fallbacks.

## Troubleshooting

- If startup fails with missing env vars: ensure `ENVIRONMENT` and required keys are present.
- If Railway reports "No start command detected", confirm the service is using `backend/Dockerfile` and not the default Railpack auto-detect path.
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
