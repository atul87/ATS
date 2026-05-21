from abc import ABC, abstractmethod
from typing import Dict, List, Optional

class DocumentStore(ABC):
    @abstractmethod
    async def save_analysis(self, user_id: str, filename: str, analysis_result: Dict) -> Optional[str]:
        """Save a resume analysis result to the database."""
        pass

    @abstractmethod
    async def get_user_history(self, user_id: str) -> List[Dict]:
        """Fetch the history of analyses for a given user."""
        pass

    @abstractmethod
    async def delete_analysis(self, analysis_id: str, user_id: str) -> bool:
        """Delete an analysis entry from the database."""
        pass
