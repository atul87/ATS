import os

if os.getenv("MOCK_AUTH", "").lower() == "true":
    from backend.auth.mock_auth import get_current_user_mock as get_current_user
else:
    from backend.auth.real_auth import get_current_user_real as get_current_user

__all__ = ["get_current_user"]

