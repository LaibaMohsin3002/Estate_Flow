"""Notifications API routes — focused unread inbox, mark-as-read."""
from fastapi import APIRouter, Depends, Query

from app.auth import get_current_user
from app.db import get_supabase_admin

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("")
async def list_notifications(
    include_read: bool = Query(False),
    limit: int = Query(12, ge=1, le=30),
    user: dict = Depends(get_current_user),
):
    """Return the current user's most relevant notifications, newest first."""
    admin = get_supabase_admin()
    unread_result = (
        admin.table("notifications")
        .select("id", count="exact")
        .eq("recipient_id", user["id"])
        .eq("type", "in_app")
        .in_("status", ["sent", "pending"])
        .is_("read_at", "null")
        .execute()
    )
    query = (
        admin.table("notifications")
        .select("*")
        .eq("recipient_id", user["id"])
        .eq("type", "in_app")
        .in_("status", ["sent", "pending"])
        .order("created_at", desc=True)
        .limit(limit)
    )
    if not include_read:
        query = query.is_("read_at", "null")

    result = query.execute()
    rows = result.data or []
    return {"data": rows, "unread_count": unread_result.count or 0}


@router.patch("/{notification_id}/read")
async def mark_read(notification_id: str, user: dict = Depends(get_current_user)):
    """Mark a single notification as read."""
    admin = get_supabase_admin()
    from datetime import datetime

    admin.table("notifications").update(
        {"read_at": datetime.utcnow().isoformat()}
    ).eq("id", notification_id).eq("recipient_id", user["id"]).execute()
    return {"ok": True}


@router.patch("/read-all")
async def mark_all_read(user: dict = Depends(get_current_user)):
    """Mark all of the current user's notifications as read."""
    admin = get_supabase_admin()
    from datetime import datetime

    admin.table("notifications").update(
        {"read_at": datetime.utcnow().isoformat()}
    ).eq("recipient_id", user["id"]).is_("read_at", "null").execute()
    return {"ok": True}
