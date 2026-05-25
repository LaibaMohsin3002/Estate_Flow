"""Shared phone normalization for WhatsApp and vendor matching."""
import re


def normalize_phone(phone: str | None) -> str:
    """Normalize to digits-only international form (e.g. 923001234567)."""
    if not phone:
        return ""
    cleaned = re.sub(r"\D", "", str(phone).strip())
    if cleaned.startswith("0") and len(cleaned) == 11:
        cleaned = "92" + cleaned[1:]
    return cleaned
