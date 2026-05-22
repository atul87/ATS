from typing import Any, Dict
from frontend.services.auth_provider import AuthProvider


class MockAuthProvider(AuthProvider):
    def sign_in_with_password(self, email: str, password: str) -> Dict[str, Any]:
        if not email or not password or email.startswith("invalid") or password == "wrong-password":
            return {"error": "Wrong email or password"}

        return {
            "access_token": "mock-access-token",
            "refresh_token": "mock-refresh-token",
            "user_id": "mock-user-id",
            "email": email or "mock@example.com",
        }

    def sign_up_with_password(self, email: str, password: str) -> Dict[str, Any]:
        if not email:
            return {"error": "Email is required"}
        if len(password or "") < 6:
            return {"error": "Password too short (Supabase default is 6 characters)"}

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
