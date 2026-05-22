from typing import Any, Dict
from frontend.services.auth_provider import AuthProvider


class MockAuthProvider(AuthProvider):
    def sign_in_with_password(self, email: str, password: str) -> Dict[str, Any]:
        return {
            "access_token": "mock-access-token",
            "refresh_token": "mock-refresh-token",
            "user_id": "mock-user-id",
            "email": email or "mock@example.com",
        }

    def sign_up_with_password(self, email: str, password: str) -> Dict[str, Any]:
        return {
            "access_token": "mock-access-token",
            "refresh_token": "mock-refresh-token",
            "user_id": "mock-user-id",
            "email": email or "mock@example.com",
        }

    def google_oauth_url(self) -> Dict[str, Any]:
        return {"error": "Google sign-in unavailable in mock mode"}

    def exchange_code_for_session(self, auth_code: str) -> Dict[str, Any]:
        return {"error": "Google sign-in unavailable in mock mode"}

    def sign_out(self) -> None:
        pass
