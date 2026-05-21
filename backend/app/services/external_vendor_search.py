"""Optional Brave Search fallback when no internal vendor matches."""

import httpx

from app.config import get_settings


async def search_external_vendor(specialty: str, city: str = "Karachi") -> dict | None:
    settings = get_settings()
    api_key = getattr(settings, "brave_api_key", None) or ""
    if not api_key:
        return None

    query = f"{specialty} contractor emergency {city} Pakistan phone"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                "https://api.search.brave.com/res/v1/web/search",
                headers={"X-Subscription-Token": api_key, "Accept": "application/json"},
                params={"q": query, "count": 3},
            )
            resp.raise_for_status()
            data = resp.json()
            results = data.get("web", {}).get("results") or []
            if not results:
                return None
            top = results[0]
            return {
                "name": top.get("title", "External vendor"),
                "phone": None,
                "source": "brave_search",
                "url": top.get("url"),
                "description": top.get("description"),
            }
    except Exception:
        return None
