"""Google Calendar remote MCP (https://calendarmcp.googleapis.com/mcp/v1)."""
import json
import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from app.config import get_settings
from app.services.calendar import (
    _connection_owner_profile_id,
    get_calendar_access_token,
)

logger = logging.getLogger(__name__)


def _mcp_url() -> str:
    return get_settings().calendar_mcp_url.rstrip("/")


def _extract_event_id(payload: Any) -> str | None:
    """Walk MCP JSON-RPC result for a created event id."""
    if not isinstance(payload, dict):
        return None
    if payload.get("error"):
        return None
    result = payload.get("result")
    if isinstance(result, dict):
        if result.get("isError"):
            return None
        structured = result.get("structuredContent") or result.get("structured_content")
        if isinstance(structured, dict) and structured.get("id"):
            return str(structured["id"])
        event = result.get("event")
        if isinstance(event, dict) and event.get("id"):
            return str(event["id"])
        for key in ("id", "eventId", "event_id"):
            if result.get(key):
                return str(result[key])
    # Deep search for calendar event shape
    stack: list[Any] = [payload]

    def looks_like_event(obj: dict[str, Any]) -> bool:
        return bool(obj.get("id")) and any(k in obj for k in ("summary", "start", "htmlLink"))

    while stack:
        node = stack.pop()
        if isinstance(node, dict):
            if looks_like_event(node):
                return str(node["id"])
            stack.extend(node.values())
        elif isinstance(node, list):
            stack.extend(node)
    return None


async def mcp_create_event(
    *,
    connection: dict[str, Any],
    summary: str,
    description: str,
    start_dt: datetime,
    end_dt: datetime,
    calendar_id: str = "primary",
) -> str | None:
    """Create event via Calendar MCP. Returns event id or None."""
    owner_id = _connection_owner_profile_id(connection)
    if not owner_id:
        return None

    token = get_calendar_access_token(owner_id)
    if not token:
        logger.info("Calendar MCP: no access token for %s", owner_id)
        return None

    start_iso = start_dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    end_iso = end_dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "create_event",
            "arguments": {
                "summary": summary,
                "description": description,
                "startTime": start_iso,
                "endTime": end_iso,
                "calendarId": calendar_id,
                "timeZone": "Asia/Karachi",
            },
        },
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(_mcp_url(), json=payload, headers=headers)
            body_text = resp.text
            if resp.status_code >= 400:
                logger.warning(
                    "Calendar MCP HTTP %s for %s: %s",
                    resp.status_code,
                    owner_id,
                    body_text[:500],
                )
                return None
            try:
                data = resp.json()
            except json.JSONDecodeError:
                logger.warning(
                    "Calendar MCP non-JSON response for %s: %s",
                    owner_id,
                    body_text[:500],
                )
                return None

            event_id = _extract_event_id(data)
            if event_id:
                logger.info("Calendar MCP event created for %s: %s", owner_id, event_id)
                return event_id

            logger.warning(
                "Calendar MCP did not return an event id for %s: %s",
                owner_id,
                json.dumps(data)[:500],
            )
            return None
    except Exception:
        logger.exception("Calendar MCP create_event failed for %s", owner_id)
        return None
