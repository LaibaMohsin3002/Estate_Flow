"""Incremental pipeline progress for live frontend polling."""

from typing import Any

from app.agents.state import MaintenanceGraphState
from app.db import get_supabase_admin


def _partial_pipeline_row(state: MaintenanceGraphState) -> dict[str, Any]:
    return {
        "request_id": state["request_id"],
        "category": state.get("category"),
        "urgency": state.get("urgency"),
        "summary": state.get("summary"),
        "vendor_specialty": state.get("vendor_specialty"),
        "estimated_time": state.get("estimated_time"),
        "priority_reason": state.get("priority_reason"),
        "agents_run": state.get("agents_run", []),
        "pii_found": state.get("pii_found", False),
        "pii_log": state.get("pii_log"),
        "is_safe": state.get("is_safe", True),
        "security_notes": state.get("security_notes"),
        "threat_type": state.get("threat_type", "none"),
        "is_compliant": state.get("is_compliant", True),
        "governance_notes": state.get("governance_notes"),
        "compliance_flags": state.get("compliance_flags", []),
        "performance_score": state.get("performance_score"),
        "sla_target_hours": state.get("sla_target_hours"),
        "performance_notes": state.get("performance_notes"),
        "assigned_vendor": state.get("assigned_vendor"),
        "vendor_phone": state.get("vendor_phone"),
        "assigned_vendor_id": state.get("assigned_vendor_id"),
        "scheduled_time": state.get("scheduled_time"),
        "db_status": state.get("db_status"),
        "human_approved": state.get("human_approved", False),
        "report_summary": state.get("report_summary"),
        "report_pdf_path": state.get("report_pdf_path"),
        "report_signed": state.get("report_signed", False),
        "report_pending_signature": state.get("report_pending_signature", False),
        "audit_ledger": state.get("audit_ledger", []),
        "token_usage_estimate": state.get("llm_tokens_estimated"),
        "performance_alerts": state.get("performance_alerts", []),
        "recommended_model": state.get("recommended_model"),
    }


async def init_pipeline_progress(request_id: str) -> None:
    admin = get_supabase_admin()
    existing = (
        admin.table("maintenance_pipeline_results")
        .select("id")
        .eq("request_id", request_id)
        .execute()
    )
    if not existing.data:
        admin.table("maintenance_pipeline_results").insert(
            {"request_id": request_id, "agents_run": [], "summary": "AI pipeline running…"}
        ).execute()
    admin.table("maintenance_requests").update({"status": "In Progress"}).eq("id", request_id).execute()


async def persist_agent_step(
    state: MaintenanceGraphState,
    agent_name: str,
    output: dict[str, Any],
    duration_ms: int,
) -> None:
    request_id = state["request_id"]
    admin = get_supabase_admin()

    success = not (agent_name == "security_agent" and state.get("pipeline_blocked"))
    admin.table("agent_logs").insert(
        {
            "pipeline_type": "maintenance",
            "reference_id": request_id,
            "agent_name": agent_name,
            "duration_ms": duration_ms,
            "success": success,
            "output": output,
        }
    ).execute()

    row = _partial_pipeline_row(state)
    admin.table("maintenance_pipeline_results").update(row).eq("request_id", request_id).execute()

    status = state.get("db_status") or "In Progress"
    if state.get("report_pending_signature") and not state.get("report_signed"):
        status = "Pending Approval"
    elif state.get("requires_human_approval") and not state.get("human_approved"):
        status = "Pending Approval"
    if state.get("pipeline_blocked"):
        status = "Blocked"

    admin.table("maintenance_requests").update(
        {
            "status": status,
            "redacted_issue": state.get("redacted_issue"),
            "image_desc": state.get("image_desc"),
        }
    ).eq("id", request_id).execute()
