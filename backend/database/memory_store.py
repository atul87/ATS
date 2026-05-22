from datetime import datetime, timezone
import uuid
import json
from typing import Dict, List, Optional
from backend.database.base import DocumentStore


class MemoryStore(DocumentStore):
    def __init__(self):
        self.history: List[Dict] = []

    async def save_analysis(
        self, user_id: str, filename: str, analysis_result: Dict
    ) -> Optional[str]:
        inserted_id = str(uuid.uuid4())

        def _json_default(o):
            if hasattr(o, "model_dump"):
                return o.model_dump()
            return str(o)

        serializable_result = json.loads(json.dumps(analysis_result, default=_json_default))

        self.history.append(
            {
                "id": inserted_id,
                "user_id": user_id,
                "filename": filename,
                "resume_name": filename,
                "job_title": "Software Engineer",
                "ats_score": serializable_result.get("ats_score", 0),
                "keyword_match": serializable_result.get("keyword_match", 0),
                "missing_keywords": serializable_result.get("missing_keywords", []),
                "date": datetime.now(timezone.utc).isoformat(),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "analysis_result": serializable_result,
            }
        )
        return inserted_id

    async def get_user_history(self, user_id: str) -> List[Dict]:
        results = [item for item in self.history if item["user_id"] == user_id]
        results.sort(key=lambda x: x["created_at"], reverse=True)
        return results

    async def delete_analysis(self, analysis_id: str, user_id: str) -> bool:
        for index, item in enumerate(self.history):
            if item["id"] == analysis_id and item["user_id"] == user_id:
                del self.history[index]
                return True
        return False
