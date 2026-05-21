"""PDF reports and audit ledgers for the Report Agent (Node I)."""

import io
from datetime import datetime
from typing import Any

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.lib import colors

from app.db import get_supabase_admin


def build_audit_ledger(state: dict[str, Any], ticket_id: str) -> list[dict[str, Any]]:
    """Immutable-style audit trail for manager sign-off."""
    now = datetime.utcnow().isoformat() + "Z"
    entries = [
        {"ts": now, "event": "report_generated", "actor": "report_agent"},
        {"ts": now, "event": "security_check", "value": state.get("is_safe", True)},
        {"ts": now, "event": "pii_redacted", "value": state.get("pii_found", False)},
        {"ts": now, "event": "urgency", "value": state.get("urgency")},
        {"ts": now, "event": "category", "value": state.get("category")},
        {"ts": now, "event": "vendor", "value": state.get("assigned_vendor")},
        {"ts": now, "event": "compliance", "value": state.get("is_compliant", True)},
        {"ts": now, "event": "human_approval_required", "value": state.get("requires_human_approval")},
        {"ts": now, "event": "agents_run", "value": state.get("agents_run", [])},
    ]
    for name, ms in (state.get("node_timings_ms") or {}).items():
        entries.append({"ts": now, "event": f"agent_{name}_ms", "value": ms})
    entries.append({"ts": now, "event": "ticket_id", "value": ticket_id})
    return entries


def build_report_summary(state: dict[str, Any], ticket_id: str) -> str:
    """Executive summary for managers (template-based; fast and audit-safe)."""
    urgency = state.get("urgency", "Medium")
    summary = state.get("summary") or state.get("original_issue", "")[:300]
    vendor = state.get("assigned_vendor") or "Pending assignment"
    scheduled = state.get("scheduled_time") or "Pending"
    flags = ", ".join(state.get("compliance_flags") or []) or "None"
    return (
        f"Maintenance Report — {ticket_id}\n"
        f"Urgency: {urgency} | Category: {state.get('category', 'General')}\n"
        f"Issue: {summary}\n"
        f"Vendor: {vendor} | Scheduled: {scheduled}\n"
        f"Compliance flags: {flags}\n"
        f"Governance: {state.get('governance_notes', 'N/A')}"
    )


def render_maintenance_pdf(
    state: dict[str, Any],
    ticket_id: str,
    report_summary: str,
    audit_ledger: list[dict[str, Any]],
    *,
    draft: bool = False,
) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story: list[Any] = []

    title = "EstateFlow Maintenance Report (DRAFT)" if draft else "EstateFlow Maintenance Report"
    story.append(Paragraph(title, styles["Title"]))
    story.append(Spacer(1, 12))
    story.append(Paragraph(f"<b>Ticket:</b> {ticket_id}", styles["Normal"]))
    story.append(Paragraph(f"<b>Generated:</b> {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}", styles["Normal"]))
    story.append(Spacer(1, 16))
    story.append(Paragraph("<b>Executive Summary</b>", styles["Heading2"]))
    for line in report_summary.split("\n"):
        story.append(Paragraph(line.replace("&", "&amp;"), styles["Normal"]))
    story.append(Spacer(1, 16))
    story.append(Paragraph("<b>Audit Ledger</b>", styles["Heading2"]))

    table_data = [["Event", "Value"]]
    for row in audit_ledger[:20]:
        table_data.append([str(row.get("event", "")), str(row.get("value", ""))[:80]])

    table = Table(table_data, colWidths=[180, 300])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F766E")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
            ]
        )
    )
    story.append(table)

    if draft:
        story.append(Spacer(1, 24))
        story.append(
            Paragraph(
                "<i>Pending manager signature — dispatch blocked until approved in EstateFlow.</i>",
                styles["Italic"],
            )
        )

    doc.build(story)
    return buffer.getvalue()


async def upload_report_pdf(request_id: str, pdf_bytes: bytes, draft: bool) -> str:
    admin = get_supabase_admin()
    suffix = "draft" if draft else "final"
    path = f"{request_id}/maintenance-report-{suffix}.pdf"
    bucket = "maintenance-reports"
    try:
        admin.storage.from_(bucket).upload(
            path,
            pdf_bytes,
            {"content-type": "application/pdf", "upsert": "true"},
        )
    except Exception:
        pass
    return f"{bucket}/{path}"
