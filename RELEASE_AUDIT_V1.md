# ATS Resume Scorer Release Audit v1.0.0

**Audit date:** 2026-06-03
**Live backend:** <https://ats-production-9787.up.railway.app>  
**Live frontend:** <https://appapppy-ktwxupi73vqhjzweksze9d.streamlit.app>  
**Runtime fix commit:** `d09d9c5`

## Release Status

The application is end-to-end functional locally. Commit `d09d9c5` is deployed
and fixes three
production release issues found during this audit:

1. Production startup validation now accepts the documented
   `SUPABASE_SERVICE_KEY` variable and the legacy `SUPABASE_KEY` alias.
2. CORS origins are normalized without a trailing slash, matching browser
   `Origin` headers from the Streamlit deployment.
3. An empty Docker `BUILD_TIME` argument now returns `"unknown"` instead of an
   empty string.

Streamlit Community Cloud visibility, Supabase Auth email/provider settings,
and the stale `v1.0.0` tag still need dashboard/release updates before the
release should be considered fully complete.

## Local Verification

| Check | Result |
| --- | --- |
| `pytest tests -v` | PASS: 54 passed, 1 skipped |
| Chromium browser E2E | PASS: login, upload, score, history, delete, PDF, errors, restart recovery |
| `ruff check .` | PASS |
| `black --check .` | PASS |
| `python -m compileall -q backend frontend` | PASS |
| `git diff --check` | PASS |

The single skipped test checks host OCR binaries (`tesseract` and `pdftoppm`).
The backend Docker image installs both binaries.

## Live Acceptance

| Check | Result | Evidence |
| --- | --- | --- |
| Health | PASS | `/api/v1/health` returns healthy with both models loaded |
| Release version | PASS | `/version` returns `1.0.0`, `production`, and commit `7a0774a` |
| Build metadata | PASS | `/build` returns `2026-05-31T12:00:00Z`, `production`, and `fast_mode=false` |
| Commit metadata | PASS | `/commit` reports `7a0774a` from Railway |
| API root | PASS | `/` lists the primary endpoints |
| Prometheus metrics | PASS | `/metrics` exposes request, latency, and model-load metrics |
| Swagger docs | PASS | `/docs` returns HTTP 200 |
| Auth guards | PASS | unauthenticated history and analyze requests return HTTP 401 |
| Streamlit frontend | PARTIAL | redirects to Streamlit Cloud authorization; public walkthrough is blocked |
| Browser CORS | PASS | live preflight returns HTTP 200 for both observed Streamlit origins |

The machine-readable live results are in `acceptance_results.json`.

## GitHub Actions Findings

`main` CI is green. The latest successful `main` run is GitHub Actions run
`26866855725` for commit `7a0774a`.

The failing CI/CD item is the `v1.0.0` tag run `26706701931`, not `main`. Its
`lint-and-unit` and `docker-dry-run` jobs passed. The `e2e` job failed only in
`test_history[chromium]` while waiting for `good_resume.docx` to disappear after
deletion.

Root cause: the tag points to older commit `9b13850`, where the test reused a
non-unique fixture filename and then asserted that all text matching that
filename became hidden. That is brittle once any other history entry with the
same filename exists. Commit `7a0774a` fixes this by uploading a unique filename
for the delete-history scenario. Local and GitHub `main` E2E now pass.

## Railway Deployment Values

Set or confirm these values in the Railway backend service before redeploying:

```env
ENVIRONMENT=production
BUILD_TIME=<UTC deployment timestamp>
MOCK_AUTH=false
SUPABASE_URL=https://lzudxufewzruizbwnunb.supabase.co
SUPABASE_SERVICE_KEY=<backend-only secret or legacy service_role key>
ALLOWED_ORIGINS=https://appapppy-ktwxupi73vqhjzweksze9d.streamlit.app,https://ekmfboeemgmecad7bfufbb.streamlit.app
AUTH_REDIRECT_URL=https://appapppy-ktwxupi73vqhjzweksze9d.streamlit.app
```

`SUPABASE_JWT_SECRET` is only needed while accepting legacy HS256 access
tokens. Modern asymmetric tokens are verified through Supabase JWKS.

`GROQ_API_KEY` is optional for functional release readiness. Without it, the
tested local regex parser fallback is used. Add the key to enable Groq-enhanced
parsing and verify `parser_source == "groq"` after redeployment.

## Supabase Auth Findings

The Supabase project `lzudxufewzruizbwnunb` is active and healthy. The
`public.analyses` table exists, has RLS enabled, and contained 6 rows at audit
time.

Auth logs for the last 24 hours showed only a successful `/settings` request,
not a mailer failure. There is no recent Supabase mailer stack trace to quote.

Current public Auth settings show:

```json
{
  "external.email": true,
  "disable_signup": false,
  "mailer_autoconfirm": false,
  "external.google": false
}
```

Exact effect:

- Password sign-up requires an email confirmation.
- Google OAuth is disabled in Supabase.
- Without Custom SMTP, Supabase's default Auth email service is restricted and
  is not production delivery for arbitrary users.
- The frontend must set `AUTH_REDIRECT_URL` so confirmation/OAuth redirects go
  to Streamlit instead of localhost.
- Supabase auth logs show a recent `/settings` request from
  `https://ekmfboeemgmecad7bfufbb.streamlit.app`; keep that origin in
  `ALLOWED_ORIGINS` if that Streamlit app is still active.

The frontend now reads `AUTH_REDIRECT_URL` from environment or Streamlit secrets
and sends it to Supabase password sign-up and OAuth flows.

## Remaining Release Steps

1. Set `AUTH_REDIRECT_URL` in Streamlit secrets to the deployed Streamlit URL.
2. Configure Supabase Custom SMTP, or disable email confirmation for a demo-only
   deployment.
3. Enable Google OAuth in Supabase if the Google button should be available.
4. Make the Streamlit app public or complete an authenticated UI walkthrough.
5. Provision and verify `GROQ_API_KEY` if Groq-enhanced parsing is required for
   v1.0.0.
6. Move/recreate the existing `v1.0.0` tag only after live acceptance and tag CI
   pass.

Railway CLI is not installed in this workspace, so Railway variable changes
and redeployment must be completed through the Railway dashboard or another
authenticated deployment environment.
