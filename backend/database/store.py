import os
from backend.database.base import DocumentStore
from backend.database.supabase_store import SupabaseStore
from backend.database.sqlite_store import SQLiteStore

_db_instance: DocumentStore | None = None


def get_db() -> DocumentStore:
    global _db_instance
    if _db_instance is None:
        mock_auth = os.getenv("MOCK_AUTH", "").lower() in {"1", "true", "yes", "on"}
        supabase_url = os.getenv("SUPABASE_URL", "").strip()
        supabase_key = (
            os.getenv("SUPABASE_KEY", "").strip() or os.getenv("SUPABASE_SERVICE_KEY", "").strip()
        )

        if mock_auth or not supabase_url or not supabase_key:
            _db_instance = SQLiteStore()
        else:
            _db_instance = SupabaseStore()
    return _db_instance
