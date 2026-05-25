"""Predictive Maintenance Agent (#12) — async weekly forecaster."""

from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Any

from app.config import get_settings
from app.db import get_supabase_admin


FORECAST_RULES: list[tuple[str, str, int]] = [
    ("plumbing", "Pipe/valve wear — schedule preventive plumbing inspection", 3),
    ("hvac", "HVAC seasonal failure risk — filter & coil service recommended", 3),
    ("electrical", "Electrical fault cluster — licensed inspection before peak load", 2),
    ("structural", "Structural recurrence — engineering assessment advised", 2),
    ("general", "General maintenance volume elevated — review staffing", 4),
]


async def run_predictive_maintenance_batch() -> dict[str, Any]:
    """
    Scan historical maintenance_requests (90 days), detect recurring issues,
    forecast failures, persist snapshots, notify property managers.
    """
    admin = get_supabase_admin()
    settings = get_settings()
    since = (datetime.utcnow() - timedelta(days=90)).isoformat()

    requests = (
        admin.table("maintenance_requests")
        .select("id, property_id, property_name, original_issue, created_at, status")
        .gte("created_at", since)
        .execute()
    )
    rows = requests.data or []

    by_property: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        pid = str(r.get("property_id") or "unknown")
        by_property[pid].append(r)

    pipeline_rows = (
        admin.table("maintenance_pipeline_results")
        .select("request_id, category, urgency, summary")
        .execute()
    )
    category_by_request = {
        str(p["request_id"]): (p.get("category") or "General").lower()
        for p in (pipeline_rows.data or [])
    }

    snapshots_created = 0
    alerts_sent = 0

    for property_id, prop_requests in by_property.items():
        if len(prop_requests) < 2:
            continue

        prop_name = prop_requests[0].get("property_name") or "Property"
        categories: list[str] = []
        for r in prop_requests:
            cat = category_by_request.get(str(r["id"]), "general")
            categories.append(cat)

        counts = Counter(categories)
        recurring: list[dict[str, Any]] = []
        forecasts: list[dict[str, Any]] = []

        for cat, count in counts.most_common(5):
            if count >= 2:
                recurring.append(
                    {
                        "category": cat,
                        "occurrences_90d": count,
                        "severity": "high" if count >= 4 else "medium",
                    }
                )
            for rule_cat, message, threshold in FORECAST_RULES:
                if rule_cat in cat and count >= threshold:
                    forecasts.append(
                        {
                            "category": cat,
                            "forecast": message,
                            "confidence": min(0.95, 0.5 + count * 0.1),
                            "window_days": 30,
                        }
                    )

        if not recurring and not forecasts:
            continue

        risk_score = min(100, 20 * len(recurring) + 15 * len(forecasts))
        savings = float(risk_score * 500)  # illustrative PKR prevention estimate

        snapshot = {
            "property_id": None if property_id == "unknown" else property_id,
            "property_name": prop_name,
            "forecast_period": "weekly",
            "recurring_issues": recurring,
            "failure_forecasts": forecasts,
            "risk_score": risk_score,
            "estimated_savings_pkr": savings,
            "agent_notes": (
                f"Predictive scan: {len(prop_requests)} tickets in 90d; "
                f"{len(recurring)} recurring patterns; model={settings.openrouter_model}"
            ),
            "agents_run": ["predictive_maintenance_agent"],
        }
        ins = admin.table("predictive_maintenance_snapshots").insert(snapshot).execute()
        snapshots_created += 1

        admin.table("agent_logs").insert(
            {
                "pipeline_type": "predictive",
                "reference_id": (ins.data or [{"id": property_id}])[0].get("id", property_id),
                "agent_name": "predictive_maintenance_agent",
                "duration_ms": 0,
                "success": True,
                "output": {
                    "property_name": prop_name,
                    "recurring_count": len(recurring),
                    "forecast_count": len(forecasts),
                    "risk_score": risk_score,
                },
            }
        ).execute()

        managers = (
            admin.table("profiles")
            .select("id")
            .in_("role", ["manager", "admin"])
            .execute()
        )
        msg = (
            f"Predictive maintenance: {prop_name} has {len(recurring)} recurring issue pattern(s). "
            f"Review forecast in EstateFlow dashboard."
        )
        for m in managers.data or []:
            try:
                admin.table("notifications").insert(
                    {
                        "type": "whatsapp",
                        "recipient_id": m["id"],
                        "subject": "Predictive maintenance alert",
                        "message": msg,
                        "reference_type": "predictive_snapshot",
                        "reference_id": (ins.data or [{}])[0].get("id"),
                        "status": "pending",
                    }
                ).execute()
                alerts_sent += 1
            except Exception:
                pass

    return {
        "properties_scanned": len(by_property),
        "snapshots_created": snapshots_created,
        "manager_alerts": alerts_sent,
        "requests_analyzed": len(rows),
    }
