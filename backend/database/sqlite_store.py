import os
import sqlite3
import json
import uuid
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional
from backend.database.base import DocumentStore

logger = logging.getLogger("ats_resume_scorer")


class SQLiteStore(DocumentStore):
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            if os.getenv("E2E_TESTING") == "true":
                self.db_path = Path(__file__).resolve().parents[2] / "ats_history_test.db"
            else:
                self.db_path = Path(__file__).resolve().parents[2] / "ats_history.db"
        else:
            self.db_path = Path(db_path)

        logger.info(f"Initializing SQLiteStore at: {self.db_path}")
        self._init_db()

    def _get_connection(self):
        # Return a connection to SQLite. Note: sqlite3 connections are thread-local,
        # so we open and close them per operation.
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS analyses (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    resume_name TEXT,
                    job_title TEXT,
                    ats_score INTEGER,
                    keyword_match REAL,
                    missing_keywords TEXT,
                    created_at TEXT,
                    analysis_result TEXT
                )
                """)
            conn.commit()

    async def save_analysis(
        self, user_id: str, filename: str, analysis_result: Dict
    ) -> Optional[str]:
        inserted_id = str(uuid.uuid4())

        def _json_default(o):
            if hasattr(o, "model_dump"):
                return o.model_dump()
            return str(o)

        serializable_result = json.loads(json.dumps(analysis_result, default=_json_default))

        missing_keywords = serializable_result.get("missing_keywords", [])
        created_at = datetime.now(timezone.utc).isoformat()

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO analyses (
                    id, user_id, filename, resume_name, job_title, ats_score, 
                    keyword_match, missing_keywords, created_at, analysis_result
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    inserted_id,
                    user_id,
                    filename,
                    filename,
                    "Software Engineer",
                    serializable_result.get("ats_score", 0),
                    serializable_result.get("keyword_match", 0),
                    json.dumps(missing_keywords),
                    created_at,
                    json.dumps(serializable_result),
                ),
            )
            conn.commit()

        return inserted_id

    async def get_user_history(self, user_id: str) -> List[Dict]:
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM analyses WHERE user_id = ? ORDER BY created_at DESC", (user_id,)
            )
            rows = cursor.fetchall()

        results = []
        for row in rows:
            try:
                analysis_result = json.loads(row["analysis_result"])
            except Exception:
                analysis_result = {}

            try:
                missing_keywords = json.loads(row["missing_keywords"])
            except Exception:
                missing_keywords = []

            results.append(
                {
                    "id": row["id"],
                    "filename": row["filename"],
                    "resume_name": row["resume_name"] or row["filename"],
                    "job_title": row["job_title"] or "Software Engineer",
                    "ats_score": row["ats_score"],
                    "keyword_match": row["keyword_match"],
                    "missing_keywords": missing_keywords,
                    "date": row["created_at"],
                    "created_at": row["created_at"],
                    "analysis_result": analysis_result,
                }
            )
        return results

    async def delete_analysis(self, analysis_id: str, user_id: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM analyses WHERE id = ? AND user_id = ?", (analysis_id, user_id)
            )
            conn.commit()
            return cursor.rowcount > 0
