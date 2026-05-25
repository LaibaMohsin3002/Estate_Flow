"""WhatsApp notification service via TextMeBot API."""
import asyncio
import logging

import httpx

from app.config import get_settings
from app.services.phone import normalize_phone

logger = logging.getLogger(__name__)

TEXTMEBOT_URL = "https://api.textmebot.com/send.php"


async def send_whatsapp(
    phone: str,
    message: str,
    *,
    doc_url: str | None = None,
    image_url: str | None = None,
    delay_seconds: int = 5,
) -> bool:
    """
    Send a WhatsApp message via TextMeBot.

    Args:
        phone: Recipient phone number (any common format, auto-normalized).
        message: Plain text message (encoded once by the HTTP client for the query string).
        doc_url: Optional PDF/document URL to attach.
        image_url: Optional image URL to attach.
        delay_seconds: Mandatory delay before sending (TextMeBot anti-ban). Default 5s.

    Returns:
        True if the API call succeeded, False otherwise (never raises).
    """
    settings = get_settings()
    api_key = settings.textmebot_key or settings.textmebot_api_key
    if not api_key:
        logger.debug("TextMeBot API key not configured — WhatsApp notification skipped.")
        return False

    normalized = normalize_phone(phone)
    if not normalized:
        logger.warning("WhatsApp: invalid phone number '%s' — skipped.", phone)
        return False

    # Mandatory delay to avoid WhatsApp rate-limiting / bans
    await asyncio.sleep(delay_seconds)

    params: dict[str, str] = {
        "recipient": normalized,
        "apikey": api_key,
        "text": message,
        "json": "yes",
    }
    if doc_url:
        params["document"] = doc_url
    elif image_url:
        params["file"] = image_url

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(TEXTMEBOT_URL, params=params)
            if resp.status_code == 200:
                logger.info("WhatsApp sent to %s", normalized)
                return True
            logger.warning(
                "TextMeBot returned HTTP %s for %s: %s",
                resp.status_code, normalized, resp.text[:200],
            )
            return False
    except Exception as exc:
        logger.error("WhatsApp send failed for %s: %s", normalized, exc)
        return False


async def send_whatsapp_to_managers(
    message: str,
    *,
    doc_url: str | None = None,
) -> int:
    """Send a WhatsApp message to all managers/admins who have a whatsapp_phone set."""
    from app.db import get_supabase_admin

    admin = get_supabase_admin()
    managers = (
        admin.table("profiles")
        .select("whatsapp_phone")
        .in_("role", ["manager", "admin"])
        .execute()
    )
    sent = 0
    for m in managers.data or []:
        phone = (m.get("whatsapp_phone") or "").strip()
        if phone:
            ok = await send_whatsapp(phone, message, doc_url=doc_url)
            if ok:
                sent += 1
    return sent
