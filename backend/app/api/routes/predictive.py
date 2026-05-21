from fastapi import APIRouter, Depends

from app.agents.predictive_maintenance import run_predictive_maintenance_batch
from app.auth import get_current_user, require_roles
from app.db import get_supabase_admin

router = APIRouter(prefix="/predictive-maintenance", tags=["predictive"])


@router.get("")
async def list_snapshots(user: dict = Depends(get_current_user)):
    admin = get_supabase_admin()
    q = (
        admin.table("predictive_maintenance_snapshots")
        .select("*")
        .order("created_at", desc=True)
        .limit(50)
    )
    if user["role"] == "manager" and user.get("property_id"):
        q = q.eq("property_id", user["property_id"])
    result = q.execute()
    return {"data": result.data or []}


@router.post("/run")
async def trigger_predictive_run(user: dict = Depends(require_roles("admin", "manager"))):
    """Manual trigger for Predictive Maintenance Agent (normally weekly)."""
    stats = await run_predictive_maintenance_batch()
    return {"message": "Predictive maintenance batch completed", "stats": stats}
