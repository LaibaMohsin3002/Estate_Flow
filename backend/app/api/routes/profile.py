from fastapi import APIRouter, Depends

from app.auth import get_current_user
from app.db import get_supabase_admin
from app.schemas import ProfileUpdate

router = APIRouter(prefix="/profile", tags=["profile"])


def _normalize_specialties(raw) -> list[str]:
    if isinstance(raw, list):
        return [str(item).strip() for item in raw if str(item).strip()]
    if isinstance(raw, str):
        return [item.strip() for item in raw.split(",") if item.strip()]
    return []


def _merge_vendor_profile(user: dict, vendor_row: dict | None) -> dict:
    merged = dict(user)
    if not vendor_row:
        return merged

    merged["full_name"] = vendor_row.get("name") or merged.get("full_name")
    merged["area"] = vendor_row.get("area")
    merged["city"] = vendor_row.get("city")
    merged["latitude"] = vendor_row.get("latitude")
    merged["longitude"] = vendor_row.get("longitude")
    merged["specialties"] = _normalize_specialties(vendor_row.get("specialty"))
    merged["whatsapp_phone"] = vendor_row.get("whatsapp_phone") or vendor_row.get("phone") or merged.get("whatsapp_phone")
    merged["phone"] = vendor_row.get("phone") or merged.get("phone")
    merged["email"] = vendor_row.get("email") or merged.get("email")
    return merged


async def _load_profile(user: dict) -> dict:
    admin = get_supabase_admin()
    if user.get("role") != "vendor":
        return dict(user)

    vendor_row = (
        admin.table("vendors")
        .select("name, area, city, latitude, longitude, specialty, phone, whatsapp_phone, email")
        .eq("id", user["id"])
        .limit(1)
        .execute()
    )
    data = vendor_row.data[0] if vendor_row.data else None
    return _merge_vendor_profile(user, data)


@router.get("/me")
async def get_me(user: dict = Depends(get_current_user)):
    return {"data": await _load_profile(user)}


@router.patch("/me")
@router.put("/me")
async def update_me(body: ProfileUpdate, user: dict = Depends(get_current_user)):
    admin = get_supabase_admin()
    payload = body.model_dump(exclude_none=True)
    if not payload:
        return {"data": await _load_profile(user)}

    profile_payload = dict(payload)
    vendor_payload = {}

    if user.get("role") == "vendor":
        if "full_name" in profile_payload:
            vendor_payload["name"] = profile_payload["full_name"]
        if "phone" in profile_payload:
            vendor_payload["phone"] = profile_payload["phone"]
        if "whatsapp_phone" in profile_payload:
            vendor_payload["phone"] = profile_payload["whatsapp_phone"] or vendor_payload.get("phone")
        if "area" in profile_payload:
            vendor_payload["area"] = profile_payload["area"]
        if "city" in profile_payload:
            vendor_payload["city"] = profile_payload["city"]
        if "latitude" in profile_payload:
            vendor_payload["latitude"] = profile_payload["latitude"]
        if "longitude" in profile_payload:
            vendor_payload["longitude"] = profile_payload["longitude"]
        if "specialties" in profile_payload:
            vendor_payload["specialty"] = profile_payload["specialties"]

        profile_payload = {}

    if profile_payload:
        admin.table("profiles").update(profile_payload).eq("id", user["id"]).execute()
    if vendor_payload:
        admin.table("vendors").update(vendor_payload).eq("id", user["id"]).execute()

    return {"data": await _load_profile(user)}
