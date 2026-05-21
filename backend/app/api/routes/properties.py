from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_current_user, require_roles
from app.db import get_supabase_admin
from app.schemas import PropertyCreate, UnitCreate

router = APIRouter(prefix="/properties", tags=["properties"])


@router.get("")
async def list_properties(user: dict = Depends(get_current_user)):
    admin = get_supabase_admin()
    result = admin.table("properties").select("*, units(*)").order("name").execute()
    return {"data": result.data or []}


@router.post("")
async def create_property(
    body: PropertyCreate,
    user: dict = Depends(require_roles("admin", "manager")),
):
    admin = get_supabase_admin()
    row = body.model_dump(exclude={"unit_numbers"}, exclude_none=True)
    inserted = admin.table("properties").insert(row).execute()
    if not inserted.data:
        raise HTTPException(status_code=500, detail="Failed to create property")

    prop = inserted.data[0]
    for unit_number in body.unit_numbers:
        admin.table("units").insert(
            {
                "property_id": prop["id"],
                "unit_number": unit_number.strip(),
                "is_occupied": False,
            }
        ).execute()

    refreshed = (
        admin.table("properties")
        .select("*, units(*)")
        .eq("id", prop["id"])
        .single()
        .execute()
    )
    return {"data": refreshed.data}


@router.post("/{property_id}/units")
async def add_unit(
    property_id: str,
    body: UnitCreate,
    user: dict = Depends(require_roles("admin", "manager")),
):
    admin = get_supabase_admin()
    result = admin.table("units").insert(
        {
            "property_id": property_id,
            "unit_number": body.unit_number,
            "floor": body.floor,
            "bedrooms": body.bedrooms,
            "bathrooms": body.bathrooms,
            "is_occupied": False,
        }
    ).execute()
    return {"data": result.data[0] if result.data else None}


@router.get("/{property_id}/units")
async def list_units(property_id: str, user: dict = Depends(get_current_user)):
    admin = get_supabase_admin()
    result = (
        admin.table("units")
        .select("*")
        .eq("property_id", property_id)
        .order("unit_number")
        .execute()
    )
    return {"data": result.data or []}
