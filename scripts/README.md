# Integration scripts

This folder contains simple, reusable scripts to validate the Supabase-backed integration end-to-end.

Files

- `check_table_exists.py`: Confirms the `public.analyses` table is reachable via PostgREST.
- `verify_integration.py`: Runs a full login → upload → analysis → history → PDF → (optional) restart rehearsal.

Required environment variables

- `SUPABASE_URL` — your Supabase project URL (e.g. `https://xyz.supabase.co`)
- `SUPABASE_ANON_KEY` — Supabase anon/public key (used to check the table)
- `TEST_EMAIL` — test user email (used by the integration rehearsal)
- `TEST_PASSWORD` — test user password

Optional environment variables

- `BACKEND_URL` — backend base URL (default `http://localhost:8000`)
- `RESTART_CMD` — command to restart the backend (e.g. `docker-compose restart backend`)

Quick usage

1. (Ensure `public.analyses` exists in Supabase SQL Editor — see Troubleshooting below.)

2. Run the table check (auto-loads `.env` if present):

```powershell
cd E:\ATS
py -3 scripts/check_table_exists.py
```

Expected output:

```
PASS analyses table exists
```

1. Run the full integration rehearsal (auto-loads `.env` if present):

```powershell
py -3 tests/generate_fixtures.py
py -3 scripts/verify_integration.py --resume tests/fixtures/generated/good_resume.docx
```

Expected outputs (sequence):

```
PASS login
PASS upload
PASS analysis
PASS history
PASS pdf
PASS restart   # if RESTART_CMD set and restart succeeded
PASS persistence
```

Troubleshooting

- If `check_table_exists.py` returns a 404 mentioning `Could not find the table 'public.analyses'`, create the table using the SQL below in the Supabase SQL Editor and re-run the check.

```sql
CREATE TABLE public.analyses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    filename TEXT NOT NULL,
    ats_score NUMERIC NOT NULL DEFAULT 0,
    keyword_match NUMERIC NOT NULL DEFAULT 0,
    missing_keywords JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now()),
    analysis_result JSONB NOT NULL DEFAULT '{}'::jsonb
);

ALTER TABLE public.analyses ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can insert their own analyses"
ON public.analyses
FOR INSERT
WITH CHECK (auth.uid()::text=user_id::text);

CREATE POLICY "Users can view their own analyses"
ON public.analyses
FOR SELECT
USING (auth.uid()::text=user_id::text);

CREATE POLICY "Users can delete their own analyses"
ON public.analyses
FOR DELETE
USING (auth.uid()::text=user_id::text);

CREATE INDEX idx_analyses_user_id ON public.analyses(user_id);
CREATE INDEX idx_analyses_created_at ON public.analyses(created_at DESC);
```

Notes

- Both scripts will attempt to `load_dotenv()` if `python-dotenv` is installed, so you can place values in a local `.env` file for convenience.
- Keep `service_role` keys out of local `.env` files used for these scripts. Use the anon/public key for the table check and real user creds for the integration rehearsal.
