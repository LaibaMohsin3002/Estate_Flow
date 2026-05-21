from typing import Annotated, Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.db import get_supabase_admin

security = HTTPBearer(auto_error=False)


def _user_id_from_supabase(token: str) -> str:
    """Validate access token via Supabase Auth API (recommended — no JWT secret mismatch)."""
    admin = get_supabase_admin()
    try:
        response = admin.auth.get_user(token)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session. Please sign out and sign in again.",
        ) from exc

    if not response or not response.user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session. Please sign out and sign in again.",
        )
    return str(response.user.id)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> dict[str, Any]:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing authorization token")

    token = credentials.credentials.strip()
    if token.lower().startswith("bearer "):
        token = token[7:].strip()

    user_id = _user_id_from_supabase(token)

    admin = get_supabase_admin()
    profile = (
        admin.table("profiles")
        .select("id, role, full_name, phone, property_id, unit_id")
        .eq("id", user_id)
        .execute()
    )

    if not profile.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

    row = profile.data[0] if isinstance(profile.data, list) else profile.data
    return {"id": user_id, "access_token": token, **row}


def require_roles(*roles: str):
    async def checker(user: Annotated[dict[str, Any], Depends(get_current_user)]) -> dict[str, Any]:
        if user.get("role") not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user

    return checker
