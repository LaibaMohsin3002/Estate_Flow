from fastapi import APIRouter, Depends

from app.auth import get_current_user, require_roles
from app.db import get_supabase_admin
from app.schemas import VendorCreate

router = APIRouter(prefix="/vendors", tags=["vendors"])


@router.get("")
async def list_vendors(user: dict = Depends(get_current_user)):
    admin = get_supabase_admin()
    result = admin.table("vendors").select("*").order("rating", desc=True).execute()
    return {"data": result.data or []}


@router.post("")
async def create_vendor(
    body: VendorCreate,
    user: dict = Depends(require_roles("admin", "manager")),
):
    admin = get_supabase_admin()
    result = admin.table("vendors").insert(body.model_dump(exclude_none=True)).execute()
    return {"data": result.data[0] if result.data else None}
