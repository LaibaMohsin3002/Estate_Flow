import logging
import re
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_current_user, require_roles
from app.config import get_settings
from app.db import get_supabase_admin
from app.schemas import VendorCreate, VendorRateBody, VendorReplyWebhookBody
from app.services.calendar import create_events_for_appointment
from app.services.notifications_helper import notify_in_app, schedule_follow_up_iso
from app.services.phone import normalize_phone
from app.services.vendor_reply_parser import parse_vendor_reply
from app.services.vendor_matching import rank_vendors
from app.services.whatsapp import send_whatsapp

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/vendors", tags=["vendors"])

_REQUEST_SELECT = "id, tenant_id, status, vendor_replied, ticket_id"


def _normalize_phone(phone: str | None) -> str:
    return normalize_phone(phone)


def _vendor_phone_value(vendor: dict[str, Any]) -> str:
    raw = vendor.get("whatsapp_phone") or vendor.get("phone")
    return _normalize_phone(raw)


def _vendor_id_for_phone(admin, phone: str) -> str | None:
    norm = _normalize_phone(phone)
    if not norm:
        return None
    vendors = admin.table("vendors").select("id, phone, whatsapp_phone").execute()
    for row in vendors.data or []:
        if _vendor_phone_value(row) == norm:
            return row["id"]
    return None


def _fetch_maintenance_request(admin, request_id: str):
    return (
        admin.table("maintenance_requests")
        .select(_REQUEST_SELECT)
        .eq("id", request_id)
        .single()
        .execute()
    )


def _find_request_by_phone(admin, phone: str):
    norm = _normalize_phone(phone)
    if not norm:
        return None

    pipelines = (
        admin.table("maintenance_pipeline_results")
        .select("request_id, vendor_phone, assigned_vendor_id")
        .not_.is_("vendor_phone", "null")
        .order("created_at", desc=True)
        .limit(100)
        .execute()
    )
    for row in pipelines.data or []:
        if _normalize_phone(row.get("vendor_phone")) == norm:
            return _fetch_maintenance_request(admin, row["request_id"])

    vendor_id = _vendor_id_for_phone(admin, norm)
    if vendor_id:
        match = (
            admin.table("maintenance_pipeline_results")
            .select("request_id")
            .eq("assigned_vendor_id", vendor_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if match.data:
            return _fetch_maintenance_request(admin, match.data[0]["request_id"])
    return None


def _extract_ticket_id(message: str) -> str | None:
    match = re.search(r"\bTKT-[A-Z0-9]{5,}\b", message.upper())
    if match:
        return match.group(0)
    return None


def _is_unavailable_message(message: str) -> bool:
    lowered = message.lower()
    return any(
        phrase in lowered
        for phrase in (
            "not available",
            "unavailable",
            "busy",
            "cannot",
            "can't",
            "not possible",
            "not free",
            "unable",
            "not this time",
        )
    )


def _looks_like_appointment_message(message: str) -> bool:
    lowered = message.lower()
    return any(
        marker in lowered
        for marker in (
            "appointment",
            "schedule",
            "tomorrow",
            "today",
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
            "pm",
            "am",
            "at ",
            "time",
            "date",
        )
    )


async def _notify_tenant(request_id: str, tenant_id: str | None, message: str, subject: str) -> None:
    if not tenant_id:
        return
    await notify_in_app(
        recipient_id=tenant_id,
        message=message,
        subject=subject,
        reference_type="maintenance_request",
        reference_id=request_id,
    )


async def _assign_next_vendor(
    admin,
    request_id: str,
    *,
    current_vendor_id: str | None = None,
    current_vendor_phone: str | None = None,
) -> dict[str, Any] | None:
    request = (
        admin.table("maintenance_requests")
        .select("id, tenant_id, latitude, longitude, property_id, status")
        .eq("id", request_id)
        .single()
        .execute()
    )
    if not request.data:
        return None

    pipeline = (
        admin.table("maintenance_pipeline_results")
        .select("*")
        .eq("request_id", request_id)
        .limit(1)
        .execute()
    )
    pipeline_data = (pipeline.data or [None])[0] or {}

    specialty = (pipeline_data.get("vendor_specialty") or "general").lower()
    radius_km = get_settings().vendor_search_radius_km

    vendors_rows = admin.table("vendors").select("*").execute()
    filtered = [
        vendor
        for vendor in (vendors_rows.data or [])
        if str(vendor.get("id")) != str(current_vendor_id or "")
    ]
    selected = rank_vendors(
        filtered,
        specialty,
        request.data.get("latitude"),
        request.data.get("longitude"),
        radius_km,
    )
    if not selected:
        return None

    follow_up = schedule_follow_up_iso(24)
    admin.table("maintenance_pipeline_results").update(
        {
            "assigned_vendor": selected.get("name"),
            "vendor_phone": _normalize_phone(
                selected.get("whatsapp_phone") or selected.get("phone")
            ),
            "assigned_vendor_id": selected.get("id"),
            "vendor_distance_km": selected.get("distance_km"),
            "vendor_license_valid": bool(selected.get("id")),
            "external_search_used": False,
            "follow_up_at": follow_up,
        }
    ).eq("request_id", request_id).execute()

    admin.table("maintenance_requests").update(
        {
            "status": "In Progress",
            "vendor_replied": False,
        }
    ).eq("id", request_id).execute()

    vendor_phone = selected.get("whatsapp_phone") or selected.get("phone") or current_vendor_phone
    if vendor_phone:
        await send_whatsapp(
            vendor_phone,
            f"Hi {selected.get('name') or 'Vendor'}, a new maintenance request is being reassigned to you.\nTicket: {request.data.get('ticket_id') or request_id[:8].upper()}.\nPlease reply within 24 hours.",
        )

    admin.table("vendors").update(
        {
            "total_assignments": int(selected.get("total_assignments") or 0) + 1,
        }
    ).eq("id", selected.get("id")).execute()

    return selected


async def process_pending_vendor_followups() -> int:
    admin = get_supabase_admin()
    now = datetime.utcnow().isoformat()
    pipeline_rows = (
        admin.table("maintenance_pipeline_results")
        .select("request_id, assigned_vendor_id, vendor_phone, vendor_specialty, follow_up_at")
        .lt("follow_up_at", now)
        .execute()
    )

    processed = 0
    for row in pipeline_rows.data or []:
        request = (
            admin.table("maintenance_requests")
            .select("id, tenant_id, vendor_replied, status")
            .eq("id", row["request_id"])
            .single()
            .execute()
        )
        if not request.data:
            continue
        if request.data.get("vendor_replied"):
            continue
        if request.data.get("status") not in ("In Progress", "Open"):
            continue

        await _assign_next_vendor(
            admin,
            row["request_id"],
            current_vendor_id=row.get("assigned_vendor_id"),
            current_vendor_phone=row.get("vendor_phone"),
        )
        processed += 1

    return processed


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


@router.post("/requests/{request_id}/vendor-reply")
async def vendor_reply(
    request_id: str,
    user: dict = Depends(get_current_user),
):
    admin = get_supabase_admin()
    req = (
        admin.table("maintenance_requests")
        .select("id, status, vendor_replied")
        .eq("id", request_id)
        .limit(1)
        .execute()
    )
    if not req.data:
        raise HTTPException(status_code=404, detail="Request not found")

    pipeline = (
        admin.table("maintenance_pipeline_results")
        .select("vendor_phone")
        .eq("request_id", request_id)
        .limit(1)
        .execute()
    )
    vendor_phone = _normalize_phone((pipeline.data or [{}])[0].get("vendor_phone"))
    if vendor_phone:
        await send_whatsapp(
            vendor_phone,
            "Hi, this is a reminder to confirm availability for the maintenance request. Please reply with availability or a proposed date and time.",
        )

    return {"message": "Reminder sent to the assigned vendor."}


@router.post("/webhook")
async def vendor_whatsapp_webhook(body: VendorReplyWebhookBody):
    admin = get_supabase_admin()
    message = body.message or ""
    phone = _normalize_phone(body.from_)
    ticket_id = body.ticket_id or _extract_ticket_id(message)

    request = None
    if body.request_id:
        request = _fetch_maintenance_request(admin, body.request_id)

    if ticket_id and (not request or not request.data):
        request = (
            admin.table("maintenance_requests")
            .select(_REQUEST_SELECT)
            .eq("ticket_id", ticket_id)
            .single()
            .execute()
        )

    if not request or not request.data:
        request = _find_request_by_phone(admin, phone)

    if not request or not request.data:
        logger.warning(
            "WhatsApp webhook: no maintenance request for from=%s ticket_id=%s",
            phone,
            ticket_id,
        )
        raise HTTPException(
            status_code=404,
            detail="No matching request found for webhook payload (check vendor_phone on the active job)",
        )

    req_data = request.data
    request_id = req_data["id"]

    current_phone = _normalize_phone(
        (admin.table("maintenance_pipeline_results")
         .select("vendor_phone")
         .eq("request_id", request_id)
         .limit(1)
         .execute().data or [{}])[0].get("vendor_phone")
    )
    current_vendor_id = (
        admin.table("maintenance_pipeline_results")
        .select("assigned_vendor_id")
        .eq("request_id", request_id)
        .limit(1)
        .execute().data or [{}]
    )[0].get("assigned_vendor_id")

    parsed = await parse_vendor_reply(message)
    decision = parsed.get("decision")

    if decision == "decline":
        new_vendor = await _assign_next_vendor(
            admin,
            request_id,
            current_vendor_id=current_vendor_id,
            current_vendor_phone=current_phone,
        )
        await _notify_tenant(
            request_id,
            req_data.get("tenant_id"),
            f"Vendor {new_vendor['name'] if new_vendor else 'could not reassign'} confirmed they are unavailable. A replacement vendor was queued for the request.",
            "Vendor follow-up",
        )
        return {"status": "reassigned", "request_id": request_id, "vendor": new_vendor.get("name") if new_vendor else None}

    if decision == "accept" and parsed.get("appointment_iso"):
        start_dt = datetime.fromisoformat(parsed["appointment_iso"].replace("Z", "+00:00"))
        end_dt = start_dt + timedelta(hours=1)
        appt_label = parsed.get("appointment_text") or message
        used_default = bool(parsed.get("appointment_default"))

        admin.table("maintenance_requests").update(
            {
                "status": "Scheduled",
                "vendor_replied": True,
            }
        ).eq("id", request_id).execute()
        admin.table("maintenance_pipeline_results").update(
            {"scheduled_time": start_dt.isoformat()}
        ).eq("request_id", request_id).execute()

        event_result = await create_events_for_appointment(
            tenant_id=req_data.get("tenant_id"),
            vendor_id=current_vendor_id,
            summary=f"Maintenance visit {req_data.get('ticket_id') or request_id[:8].upper()}",
            description=appt_label,
            start_dt=start_dt,
            end_dt=end_dt,
        )
        calendar_created = event_result.get("created", [])
        calendar_skipped = event_result.get("skipped", [])

        appt_msg = (
            f"Your vendor scheduled a visit: {appt_label}."
            if not used_default
            else f"Your vendor accepted the job. A default visit was booked for {appt_label}."
        )
        if calendar_skipped and not calendar_created:
            appt_msg += (
                " Connect Google Calendar on the Calendar page (same OAuth as Calendar MCP) "
                "to book this visit on your calendar."
            )
        elif calendar_skipped:
            appt_msg += " (Calendar synced for some accounts only — connect Calendar if yours was skipped.)"

        await _notify_tenant(
            request_id,
            req_data.get("tenant_id"),
            appt_msg + " Open your request to rate the vendor and close the ticket.",
            "Appointment scheduled",
        )
        logger.info(
            "Webhook scheduled request %s: calendar_created=%s calendar_skipped=%s details=%s",
            request_id,
            calendar_created,
            calendar_skipped,
            event_result.get("details"),
        )
        return {
            "status": "scheduled",
            "request_id": request_id,
            "appointment_default": used_default,
            "appointment_iso": parsed.get("appointment_iso"),
            "rating_ready": True,
            "calendar_created": calendar_created,
            "calendar_skipped": calendar_skipped,
            "calendar_details": event_result.get("details", []),
        }

    admin.table("maintenance_requests").update({"vendor_replied": True}).eq("id", request_id).execute()
    await _notify_tenant(
        request_id,
        req_data.get("tenant_id"),
        "Your vendor replied, but the message was unclear. Please review the request or ask for clarification.",
        "Vendor reply",
    )
    return {"status": "acknowledged", "request_id": request_id}


@router.post("/followups")
async def process_vendor_followups():
    count = await process_pending_vendor_followups()
    return {"processed": count}


@router.get("/my-active-jobs")
async def vendor_active_jobs(user: dict = Depends(get_current_user)):
    admin = get_supabase_admin()
    vendor = (
        admin.table("vendors")
        .select("id, name")
        .eq("id", user["id"])
        .limit(1)
        .execute()
    )
    if not vendor.data:
        return {"data": []}

    vendor_id = vendor.data[0]["id"]
    pipeline_rows = (
        admin.table("maintenance_pipeline_results")
        .select("request_id")
        .eq("assigned_vendor_id", vendor_id)
        .execute()
    )
    request_ids = [r["request_id"] for r in (pipeline_rows.data or [])]
    if not request_ids:
        return {"data": []}

    reqs = (
        admin.table("maintenance_requests")
        .select("id, ticket_id, original_issue, status, vendor_replied, created_at")
        .in_("id", request_ids)
        .execute()
    )
    return {"data": reqs.data or []}


@router.post("/{vendor_id}/rate")
async def rate_vendor(
    vendor_id: str,
    body: VendorRateBody,
    user: dict = Depends(get_current_user),
):
    admin = get_supabase_admin()
    v = admin.table("vendors").select("id, rating, total_assignments").eq("id", vendor_id).limit(1).execute()
    if not v.data:
        raise HTTPException(status_code=404, detail="Vendor not found")

    matched_request_id: str | None = None
    if body.request_id:
        tenant_req = (
            admin.table("maintenance_requests")
            .select("id")
            .eq("id", body.request_id)
            .eq("tenant_id", user["id"])
            .eq("vendor_replied", True)
            .limit(1)
            .execute()
        )
        if tenant_req.data:
            pipeline = (
                admin.table("maintenance_pipeline_results")
                .select("assigned_vendor_id")
                .eq("request_id", body.request_id)
                .limit(1)
                .execute()
            )
            if (pipeline.data or [{}])[0].get("assigned_vendor_id") == vendor_id:
                matched_request_id = body.request_id

    if not matched_request_id:
        req = (
            admin.table("maintenance_pipeline_results")
            .select("request_id")
            .eq("assigned_vendor_id", vendor_id)
            .execute()
        )
        request_ids = [r["request_id"] for r in (req.data or [])]
        if request_ids:
            tenant_req = (
                admin.table("maintenance_requests")
                .select("id")
                .eq("tenant_id", user["id"])
                .eq("vendor_replied", True)
                .in_("id", request_ids)
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
            if tenant_req.data:
                matched_request_id = tenant_req.data[0]["id"]

    if not matched_request_id:
        raise HTTPException(
            status_code=403,
            detail="You can only rate a vendor after they have accepted the job.",
        )

    try:
        admin.table("vendor_ratings").upsert(
            {
                "vendor_id": vendor_id,
                "request_id": matched_request_id,
                "tenant_id": user["id"],
                "rating": body.rating,
                "comment": body.comment,
            },
            on_conflict="vendor_id,request_id",
        ).execute()
    except Exception:
        pass

    admin.table("maintenance_requests").update({"status": "Resolved"}).eq("id", matched_request_id).execute()

    all_ratings = (
        admin.table("vendor_ratings")
        .select("rating")
        .eq("vendor_id", vendor_id)
        .execute()
    )
    avg = body.rating
    if all_ratings.data:
        avg = sum(r["rating"] for r in all_ratings.data) / len(all_ratings.data)
        admin.table("vendors").update({"rating": round(avg, 1)}).eq("id", vendor_id).execute()

    return {"message": "Rating submitted and ticket closed!", "new_avg": round(avg, 1)}

