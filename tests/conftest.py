import hashlib
import itertools
import re
from datetime import datetime, timezone

import numpy as np
import pytest
from fastapi.testclient import TestClient

from backend.api.auth import get_current_user
from backend.database.store import get_db
from backend.database.base import DocumentStore
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

    class FakeStore(DocumentStore):
        def __init__(self, history_list, id_cnt):
            self.history = history_list
            self.id_counter = id_cnt

        async def save_analysis(self, user_id, filename, analysis_result):
            analysis_id = str(next(self.id_counter))
            self.history.append(
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

        async def get_user_history(self, user_id):
            return [item for item in self.history if item["user_id"] == user_id]

        async def delete_analysis(self, analysis_id, user_id):
            for index, item in enumerate(self.history):
                if item["id"] == analysis_id and item["user_id"] == user_id:
                    del self.history[index]
                    return True
            return False

    app.dependency_overrides[get_db] = lambda: FakeStore(history, id_counter)

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


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    setattr(item, "rep_" + rep.when, rep)


@pytest.fixture(autouse=True)
def playwright_artifacts(request):
    if "page" not in request.fixturenames:
        yield
        return

    page = request.getfixturevalue("page")
    context = page.context

    try:
        context.tracing.start(screenshots=True, snapshots=True, sources=True)
    except Exception:
        pass

    yield page

    node = request.node
    failed = False
    if hasattr(node, "rep_call") and node.rep_call.failed:
        failed = True
    elif hasattr(node, "rep_setup") and node.rep_setup.failed:
        failed = True

    if failed:
        import shutil
        from pathlib import Path

        artifacts_dir = Path("artifacts")
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        
        test_name = node.name.replace("[", "_").replace("]", "_")

        screenshot_path = artifacts_dir / f"failure_{test_name}.png"
        try:
            page.screenshot(path=str(screenshot_path), full_page=True)
            print(f"\nCaptured failure screenshot to {screenshot_path}")
        except Exception as e:
            print(f"Failed to capture screenshot: {e}")

        trace_path = artifacts_dir / f"trace_{test_name}.zip"
        try:
            context.tracing.stop(path=str(trace_path))
            print(f"Captured failure trace to {trace_path}")
        except Exception as e:
            print(f"Failed to save trace: {e}")
            
        logs_dir = Path("logs")
        for log_name in ["backend_server.log", "frontend_server.log"]:
            log_src = logs_dir / log_name
            if log_src.exists():
                try:
                    shutil.copy(log_src, artifacts_dir / log_name)
                    print(f"Copied log {log_name} to artifacts/")
                except Exception as e:
                    print(f"Failed to copy log {log_name}: {e}")
    else:
        try:
            context.tracing.stop()
        except Exception:
            pass

