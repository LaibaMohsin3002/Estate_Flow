import time

from fastapi import APIRouter, BackgroundTasks, Depends

from app.auth import get_current_user, require_roles
from app.db import get_supabase_admin
from app.schemas import InspectionCreate
from app.services.llm import structured_completion

router = APIRouter(prefix="/inspections", tags=["inspections"])


async def _run_inspection_pipeline(inspection_id: str, items: list[dict], notes: dict):
    admin = get_supabase_admin()
    start = time.perf_counter()

    failed = [i for i in items if i.get("result") == "fail"]
    passed = [i for i in items if i.get("result") == "pass"]

    system = """You are EstateFlow inspection risk assessor. Return ONLY JSON:
overall_condition (Excellent|Good|Fair|Poor|Critical),
risk_level (Low|Medium|High|Critical),
executive_summary (string),
top_issues (array of strings),
recommendations (array of strings),
next_inspection_due (string),
estimated_repair_cost (string)."""

    user = f"Passed: {len(passed)}, Failed: {len(failed)}, Items: {items}, Notes: {notes}"
    parsed = await structured_completion(system, user)

    duration_ms = int((time.perf_counter() - start) * 1000)
    row = {
        "inspection_id": inspection_id,
        "overall_condition": parsed.get("overall_condition", "Fair"),
        "risk_level": parsed.get("risk_level", "Medium"),
        "executive_summary": parsed.get("executive_summary", ""),
        "top_issues": parsed.get("top_issues", []),
        "recommendations": parsed.get("recommendations", []),
        "next_inspection_due": parsed.get("next_inspection_due"),
        "estimated_repair_cost": parsed.get("estimated_repair_cost"),
        "work_order_count": len(failed),
        "agents_run": ["risk_assessor", "compliance_checker"],
        "duration_ms": duration_ms,
    }

    existing = (
        admin.table("inspection_pipeline_results")
        .select("id")
        .eq("inspection_id", inspection_id)
        .execute()
    )
    if existing.data:
        admin.table("inspection_pipeline_results").update(row).eq(
            "inspection_id", inspection_id
        ).execute()
    else:
        admin.table("inspection_pipeline_results").insert(row).execute()

    for item in failed:
        admin.table("work_orders").insert(
            {
                "inspection_id": inspection_id,
                "item": item.get("item_name", "Inspection failure"),
                "priority": "High",
                "assigned_specialty": "general",
                "note": item.get("note"),
                "status": "Pending",
            }
        ).execute()

    admin.table("agent_logs").insert(
        {
            "pipeline_type": "inspection",
            "reference_id": inspection_id,
            "agent_name": "risk_assessor",
            "duration_ms": duration_ms,
            "success": True,
            "output": parsed,
        }
    ).execute()


@router.get("")
async def list_inspections(user: dict = Depends(get_current_user)):
    admin = get_supabase_admin()
    result = (
        admin.table("inspections")
        .select("*, inspection_pipeline_results(*), inspection_items(*)")
        .order("created_at", desc=True)
        .execute()
    )
    return {"data": result.data or []}


@router.post("")
async def create_inspection(
    body: InspectionCreate,
    background_tasks: BackgroundTasks,
    user: dict = Depends(require_roles("admin", "manager", "inspector")),
):
    admin = get_supabase_admin()
    passed = sum(1 for i in body.items if i.get("result") == "pass")
    failed = sum(1 for i in body.items if i.get("result") == "fail")
    skipped = sum(1 for i in body.items if i.get("result") == "na")

    row = {
        "property_id": body.property_id,
        "property_name": body.property_name,
        "unit": body.unit,
        "inspection_type": body.inspection_type,
        "inspector_name": user.get("full_name") or "Inspector",
        "inspector_id": user["id"],
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "notes": body.notes,
        "status": "Completed",
    }
    inserted = admin.table("inspections").insert(row).execute()
    inspection = inserted.data[0]
    inspection_id = inspection["id"]

    for item in body.items:
        admin.table("inspection_items").insert(
            {
                "inspection_id": inspection_id,
                "item_name": item.get("item_name", "Item"),
                "result": item.get("result"),
                "note": item.get("note"),
                "storage_path": item.get("storage_path"),
            }
        ).execute()

    background_tasks.add_task(_run_inspection_pipeline, inspection_id, body.items, body.notes)
    return {"data": inspection}
