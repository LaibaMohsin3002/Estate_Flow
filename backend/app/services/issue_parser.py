"""Fast rule-based issue parsing when LLM is slow or unavailable."""

from typing import Any

TRADE_KEYWORDS: list[tuple[str, list[str]]] = [
    ("plumbing", ["leak", "leakage", "pipe", "tap", "drain", "bathroom", "toilet", "sink", "water"]),
    ("hvac", ["ac", "cooling", "heating", "hvac", "air condition", "chiller", "garmi", "thandi"]),
    ("electrical", ["electric", "spark", "fuse", "power", "short", "wiring", "light", "bijli"]),
    ("structural", ["crack", "wall", "ceiling", "structural", "collapse", "foundation"]),
    ("pest control", ["pest", "cockroach", "rat", "termite", "bug"]),
    ("appliances", ["fridge", "refrigerator", "oven", "appliance", "machine", "washer"]),
]


def parse_issue_fast(issue: str, image_desc: str = "") -> dict[str, Any]:
    text = f"{issue} {image_desc}".lower()
    trade = "general"
    for specialty, keywords in TRADE_KEYWORDS:
        if any(kw in text for kw in keywords):
            trade = specialty
            break

    category_map = {
        "plumbing": "Plumbing",
        "hvac": "HVAC",
        "electrical": "Electrical",
        "structural": "Structural",
        "pest control": "Pest Control",
        "appliances": "Appliances",
        "general": "General",
    }
    category = category_map.get(trade, "General")
    summary = issue.strip()[:200] if issue else "Maintenance request"

    return {
        "trade": trade,
        "vendor_specialty": trade,
        "category": category,
        "location_detail": "unknown",
        "summary": summary,
        "estimated_time": "2-4 hours",
        "confidence": 0.65,
        "source": "rule_based_fallback",
    }


def parse_urgency_fast(issue: str, risk_hits: list[str], boost: str | None = None) -> dict[str, Any]:
    text = issue.lower()
    critical_kw = ("gas", "fire", "flood", "electroc", "collapse", "no water", "sewage")
    high_kw = ("leak", "spark", "no power", "broken", "urgent", "emergency")

    urgency = "Medium"
    if any(k in text for k in critical_kw) or "critical" in [h.lower() for h in risk_hits]:
        urgency = "Critical"
    elif any(k in text for k in high_kw) or "high" in [h.lower() for h in risk_hits]:
        urgency = "High"
    elif boost:
        urgency = boost

    return {
        "urgency": urgency,
        "priority_reason": "Rule-based urgency (LLM unavailable or slow)",
        "source": "rule_based_fallback",
    }
