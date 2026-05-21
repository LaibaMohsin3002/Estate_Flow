"""Property risk matrix lookup (lightweight RAG-style retrieval from Supabase history)."""

from typing import Any


RISK_RULES: list[dict[str, Any]] = [
    {"keywords": ["fuse", "electric", "spark", "shock", "wire"], "hit": "electrical_near_water", "boost": "Critical"},
    {"keywords": ["gas", "smell gas", "leak gas"], "hit": "gas_leak", "boost": "Critical"},
    {"keywords": ["flood", "flooding", "ceiling collapse"], "hit": "structural_flood", "boost": "Critical"},
    {"keywords": ["no heat", "winter", "heater"], "hit": "no_heat_winter", "boost": "High"},
    {"keywords": ["mold", "sewage"], "hit": "health_hazard", "boost": "High"},
    {"keywords": ["elevator", "stuck"], "hit": "elevator_trap", "boost": "Critical"},
]


def lookup_risk_hits(issue_text: str, historical_categories: list[str] | None = None) -> tuple[list[str], str | None]:
    text = issue_text.lower()
    hits: list[str] = []
    max_boost: str | None = None
    order = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}

    for rule in RISK_RULES:
        if any(kw in text for kw in rule["keywords"]):
            hits.append(rule["hit"])
            boost = rule.get("boost")
            if boost and (max_boost is None or order.get(boost, 0) > order.get(max_boost, 0)):
                max_boost = boost

    if historical_categories and len(historical_categories) >= 3:
        hits.append("recurring_property_issues")
        if max_boost is None or order.get(max_boost, 0) < order["High"]:
            max_boost = "High"

    return hits, max_boost


SLA_BY_URGENCY = {
    "Critical": 2,
    "High": 24,
    "Medium": 48,
    "Low": 72,
}
