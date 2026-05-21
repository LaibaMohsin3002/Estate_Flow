import math
from typing import Any


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def rank_vendors(
    vendors: list[dict[str, Any]],
    specialty: str,
    tenant_lat: float | None,
    tenant_lon: float | None,
    radius_km: float,
) -> dict[str, Any] | None:
    specialty_norm = specialty.lower().strip()
    candidates: list[tuple[float, dict]] = []

    for vendor in vendors:
        if not vendor.get("available", True):
            continue
        if vendor.get("specialty", "").lower() != specialty_norm:
            continue

        score = float(vendor.get("rating") or 0)
        distance = None

        if tenant_lat is not None and tenant_lon is not None:
            vlat, vlon = vendor.get("latitude"), vendor.get("longitude")
            if vlat is not None and vlon is not None:
                distance = haversine_km(tenant_lat, tenant_lon, float(vlat), float(vlon))
                if distance > radius_km:
                    continue
                score += max(0, 5 - distance)

        candidates.append((score, {**vendor, "distance_km": distance}))

    if not candidates:
        return None

    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1]
