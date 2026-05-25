from typing import Annotated, Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.db import get_supabase_admin, get_supabase_for_token

security = HTTPBearer(auto_error=False)


def _user_from_supabase(token: str) -> tuple[str, Any]:
    """Validate access token via the Supabase auth client and return the user payload."""
    auth_client = get_supabase_for_token(token)
    try:
        response = auth_client.auth.get_user(token)
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

    return str(response.user.id), response.user


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> dict[str, Any]:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing authorization token")

    token = credentials.credentials.strip()
    if token.lower().startswith("bearer "):
        token = token[7:].strip()

    user_id, user = _user_from_supabase(token)

    admin = get_supabase_admin()
    profile = (
        admin.table("profiles")
        .select("id, role, full_name, phone, property_id, unit_id")
        .eq("id", user_id)
        .execute()
    )

    if profile.data:
        row = profile.data[0] if isinstance(profile.data, list) else profile.data
        return {"id": user_id, "email": getattr(user, "email", None), "access_token": token, **row}

    vendor = (
        admin.table("vendors")
        .select("id, name, phone, email, area, city, latitude, longitude, specialty")
        .eq("id", user_id)
        .limit(1)
        .execute()
    )

    if not vendor.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

    row = vendor.data[0] if isinstance(vendor.data, list) else vendor.data
    return {
        "id": user_id,
        "email": row.get("email") or getattr(user, "email", None),
        "access_token": token,
        "role": "vendor",
        "full_name": row.get("name"),
        "phone": row.get("phone"),
        "property_id": None,
        "unit_id": None,
        "area": row.get("area"),
        "city": row.get("city"),
        "latitude": row.get("latitude"),
        "longitude": row.get("longitude"),
        "specialties": row.get("specialty"),
    }


def require_roles(*roles: str):
    def checker(user: Annotated[dict[str, Any], Depends(get_current_user)]) -> dict[str, Any]:
        if user.get("role") not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user

    return checker
