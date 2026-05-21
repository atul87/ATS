import hashlib
import itertools
import re
from datetime import datetime, timezone

import numpy as np
import pytest
from fastapi.testclient import TestClient

from backend.api.auth import get_current_user
from backend.database import supabase_db
from backend.main import app
from backend.services import groq_parser


class FakeDoc:
    ents = ()
    noun_chunks = ()


class FakeNLP:
    def __call__(self, text):
        return FakeDoc()


class FakeEmbedder:
    def encode(self, text, convert_to_tensor=False):
        vector = np.zeros(64, dtype=float)
        for token in re.findall(r"[a-z0-9+#.]+", (text or "").lower()):
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            vector[digest[0] % len(vector)] += 1.0

        if not vector.any():
            vector[0] = 1.0
        return vector


@pytest.fixture(autouse=True)
def isolated_app(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    groq_parser._client = None

    app.state.nlp = FakeNLP()
    app.state.embedder = FakeEmbedder()
    app.dependency_overrides[get_current_user] = lambda: "test-user"

    history = []
    id_counter = itertools.count(1)

    async def fake_save_analysis(user_id, filename, analysis_result):
        analysis_id = str(next(id_counter))
        history.append(
            {
                "id": analysis_id,
                "user_id": user_id,
                "filename": filename,
                "resume_name": filename,
                "job_title": "Software Engineer",
                "ats_score": analysis_result.get("ats_score", 0),
                "keyword_match": analysis_result.get("keyword_match", 0),
                "missing_keywords": analysis_result.get("missing_keywords", []),
                "date": datetime.now(timezone.utc).isoformat(),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "analysis_result": analysis_result,
            }
        )
        return analysis_id

    async def fake_get_user_history(user_id):
        return [item for item in history if item["user_id"] == user_id]

    async def fake_delete_analysis(analysis_id, user_id):
        for index, item in enumerate(history):
            if item["id"] == analysis_id and item["user_id"] == user_id:
                del history[index]
                return True
        return False

    monkeypatch.setattr(supabase_db, "save_analysis", fake_save_analysis)
    monkeypatch.setattr(supabase_db, "get_user_history", fake_get_user_history)
    monkeypatch.setattr(supabase_db, "delete_analysis", fake_delete_analysis)

    yield history

    app.dependency_overrides.clear()


@pytest.fixture
def client():
    test_client = TestClient(app)
    yield test_client
    test_client.close()


@pytest.fixture
def analysis_payload():
    return {
        "ATS_score": 82.5,
        "ats_score": 82.5,
        "component_scores": {
            "formatting": 16.0,
            "keywords": 21.0,
            "content": 19.0,
            "skill_validation": 12.0,
            "ats_compatibility": 14.0,
        },
        "issues_summary": ["Missing Projects Section"],
        "detailed_feedback": [],
        "jd_match_analysis": None,
        "skill_validation_details": {
            "validated": [{"skill": "Python", "projects": ["Experience Section"]}],
            "unvalidated": ["Docker"],
            "total": 2,
            "validated_count": 1,
            "validation_pct": 50.0,
        },
        "keyword_match": 0.0,
        "missing_keywords": [],
        "matched_keywords": ["Python"],
        "skills": ["Python", "Docker"],
        "jd_comparison": None,
        "interpretation": "Test interpretation",
    }
