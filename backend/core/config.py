import os
import logging
import subprocess
from pathlib import Path

# Load .env from the project root (two levels up from this file) explicitly —
# load_dotenv() with no args relies on caller-frame inspection that can fail
# silently under uvicorn reload, leaving env vars unset.
try:
    from dotenv import load_dotenv

    _ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
    load_dotenv(_ENV_PATH)
except ImportError:
    pass

# api metadata
APP_TITLE = "ATS RESUME ANALYZER API"


def get_commit_details():
    # 1. COMMIT_SHA env var
    env_commit = os.getenv("COMMIT_SHA") or os.getenv("RAILWAY_GIT_COMMIT_SHA")
    if env_commit:
        return env_commit[:7], "env"

    # 2. git rev-parse --short HEAD
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=True,
        )
        sha = result.stdout.strip()
        if sha:
            return sha, "git"
    except Exception:
        pass

    # 3. Fallback
    return "unknown", "unknown"


def get_commit_sha() -> str:
    sha, _ = get_commit_details()
    return sha


APP_VERSION = os.getenv("APP_VERSION", "0.9.0-beta")
APP_DESCRIPTION = "analyse resumes against job description using nlp + ml"


ALLOWED_ORIGINS = ["https://appapppy-ktwxupi73vqhjzweksze9d.streamlit.app/"]

# file
MAX_FILE_SIZE_MB = 5
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

# Supported MIME types and their short names
SUPPORTED_MIME_TYPES = {
    "application/pdf": "pdf",
    "application/msword": "doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
}

SUPPORTED_EXTENSIONS = {".pdf", ".doc", ".docx"}

SPACY_MODEL_PRIMARY = "en_core_web_md"  # better accuracy
SPACY_MODEL_SECONDARY = "en_core_web_sm"
SENTENCE_TRANSFORMER_MODEL = os.getenv("SENTENCE_TRANSFORMER_MODEL", "all-MiniLM-L6-v2")

# Score component weights — this is business logic treated as config
SCORE_WEIGHTS = {
    "formatting": 20,
    "keywords": 25,
    "content": 25,
    "skill_validation": 15,
    "ats_compatibility": 15,
}

JD_KEYWORD_WEIGHT = 0.6
JD_SEMANTIC_WEIGHT = 0.4

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv(
    "SUPABASE_SERVICE_KEY", os.getenv("SUPABASE_KEY", "")
)  # service_role — DB writes (backend-only)
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")  # public anon — frontend auth calls
SUPABASE_JWT_SECRET = os.getenv(
    "SUPABASE_JWT_SECRET", ""
)  # used by backend to verify access tokens
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")


def check_required_env_vars(required=None):
    """Check for required environment variables and return a list of missing ones.

    This function logs a warning when variables are missing but does not raise.
    Raising can be enabled by callers if they want strict startup failure.
    """
    if required is None:
        required = ["SUPABASE_URL", "SUPABASE_KEY", "GROQ_API_KEY"]

    missing = [name for name in required if not os.getenv(name)]
    if missing:
        logging.getLogger("ats_resume_scorer").warning("Missing env vars: %s", missing)

    return missing
