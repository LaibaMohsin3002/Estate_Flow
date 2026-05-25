from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_current_user
from app.db import get_supabase_admin
from app.schemas import CalendarConnectRequest
from app.services.calendar import build_google_connect_url, exchange_google_code, get_calendar_connection, save_calendar_connection

router = APIRouter(prefix="/calendar", tags=["calendar"])


@router.get("/status")
async def get_calendar_status(user: dict = Depends(get_current_user)):
    connection = get_calendar_connection(user["id"])
    if not connection:
        return {
            "data": {
                "connected": False,
                "provider": "google",
                "calendar_id": "primary",
            }
        }

    return {
        "data": {
            "connected": True,
            "provider": connection.get("provider") or "google",
            "calendar_id": connection.get("calendar_id") or "primary",
            "connected_at": connection.get("connected_at"),
        }
    }


@router.get("/connect-url")
async def calendar_connect_url(user: dict = Depends(get_current_user)):
    try:
        auth_url = build_google_connect_url()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return {"data": {"auth_url": auth_url}}


@router.post("/connect")
async def calendar_connect(body: CalendarConnectRequest, user: dict = Depends(get_current_user)):
    try:
        token_payload = exchange_google_code(body.code)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Unable to exchange Google OAuth code") from exc

    status = save_calendar_connection(user["id"], body.calendar_id or "primary", token_payload)
    return {"data": status}


@router.get("/connections")
async def list_calendar_connections(user: dict = Depends(get_current_user)):
    admin = get_supabase_admin()
    rows = (
        admin.table("calendar_connections")
        .select("id, provider, calendar_id, connected_at, updated_at")
        .eq("profile_id", user["id"])
        .execute()
    )
    return {"data": rows.data or []}
