import os
from backend.database.base import DocumentStore
from backend.database.supabase_store import SupabaseStore
from backend.database.memory_store import MemoryStore

_db_instance: DocumentStore | None = None


def get_db() -> DocumentStore:
    global _db_instance
    if _db_instance is None:
        if os.getenv("MOCK_AUTH", "").lower() == "true":
            _db_instance = MemoryStore()
        else:
            _db_instance = SupabaseStore()
    return _db_instance
