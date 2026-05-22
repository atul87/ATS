import os
from abc import ABC, abstractmethod
from typing import Dict, Any
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
except ImportError:
    pass


class AuthProvider(ABC):
    @abstractmethod
    def sign_in_with_password(self, email: str, password: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def sign_up_with_password(self, email: str, password: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def google_oauth_url(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    def exchange_code_for_session(self, auth_code: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def sign_out(self) -> None:
        pass


if os.getenv("MOCK_AUTH", "").lower() == "true":
    from frontend.services.mock_auth import MockAuthProvider

    auth_client = MockAuthProvider()
else:
    from frontend.services.supabase_auth import SupabaseAuthProvider

    auth_client = SupabaseAuthProvider()
