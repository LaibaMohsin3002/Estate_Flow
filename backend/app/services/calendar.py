import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import Flow

from app.config import get_settings
from app.db import get_supabase_admin

logger = logging.getLogger(__name__)


def _settings() -> Any:
    return get_settings()


def _scopes() -> list[str]:
    scopes = _settings().google_scopes
    return [scope.strip() for scope in scopes.split(",") if scope.strip()]


def _client_config() -> dict[str, Any]:
    settings = _settings()
    return {
        "web": {
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [settings.google_redirect_uri],
        }
    }


def _build_flow() -> Flow:
    settings = _settings()
    if not settings.google_client_id or not settings.google_client_secret or not settings.google_redirect_uri:
        raise RuntimeError("Google Calendar OAuth is not configured")
    flow = Flow.from_client_config(_client_config(), scopes=_scopes())
    flow.redirect_uri = settings.google_redirect_uri
    return flow


def build_google_connect_url() -> str:
    flow = _build_flow()
    authorization_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    return authorization_url


def exchange_google_code(code: str) -> dict[str, Any]:
    flow = _build_flow()
    flow.fetch_token(code=code)
    credentials = flow.credentials
    payload = json.loads(credentials.to_json())
    return {
        "access_token": payload.get("token"),
        "refresh_token": payload.get("refresh_token"),
        "token_expiry": payload.get("expiry"),
        "scopes": _scopes(),
    }


def _parse_expiry(value: Any) -> datetime | None:
    """Return token expiry as naive UTC (google-auth compares to naive utcnow())."""
    if not value:
        return None
    try:
        if isinstance(value, datetime):
            parsed = value
        else:
            raw = str(value).strip()
            if raw.endswith("Z"):
                raw = raw[:-1] + "+00:00"
            parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is not None:
        return parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def _normalize_credentials_expiry(credentials: Credentials) -> None:
    """google-auth `expired` uses naive UTC; timestamptz from DB is often offset-aware."""
    if credentials.expiry and credentials.expiry.tzinfo is not None:
        credentials.expiry = credentials.expiry.astimezone(timezone.utc).replace(tzinfo=None)


def _credentials_from_row(row: dict[str, Any]) -> Credentials | None:
    if not row.get("access_token_enc"):
        return None
    settings = _settings()
    expiry = _parse_expiry(row.get("token_expiry"))
    credentials = Credentials(
        token=row.get("access_token_enc"),
        refresh_token=row.get("refresh_token_enc"),
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        token_uri="https://oauth2.googleapis.com/token",
        scopes=list(row.get("scopes") or _scopes()),
        expiry=expiry,
    )
    _normalize_credentials_expiry(credentials)
    return credentials


def _persist_credentials(profile_id: str, calendar_id: str, credentials: Credentials) -> None:
    admin = get_supabase_admin()
    existing = (
        admin.table("calendar_connections")
        .select("id")
        .eq("profile_id", profile_id)
        .eq("provider", "google")
        .execute()
    )
    payload = {
        "profile_id": profile_id,
        "provider": "google",
        "calendar_id": calendar_id or "primary",
        "access_token_enc": credentials.token,
        "refresh_token_enc": credentials.refresh_token,
        "token_expiry": credentials.expiry.isoformat() if credentials.expiry else None,
        "scopes": list(credentials.scopes or _scopes()),
        "updated_at": datetime.utcnow().isoformat(),
    }
    if existing.data:
        admin.table("calendar_connections").update(payload).eq("id", existing.data[0]["id"]).execute()
    else:
        payload["connected_at"] = datetime.utcnow().isoformat()
        admin.table("calendar_connections").insert(payload).execute()


def clear_calendar_connection(profile_id: str) -> None:
    """Remove stale OAuth row after invalid_grant so the UI shows disconnected."""
    admin = get_supabase_admin()
    admin.table("calendar_connections").delete().eq("profile_id", profile_id).eq("provider", "google").execute()


def get_calendar_connection_for_account(account_id: str | None) -> dict[str, Any] | None:
    """Resolve calendar OAuth row by profile id, vendor id, or vendor→profile mapping."""
    if not account_id:
        return None
    connection = get_calendar_connection(account_id)
    if connection:
        return connection

    admin = get_supabase_admin()
    by_vendor = (
        admin.table("calendar_connections")
        .select("*")
        .eq("vendor_id", account_id)
        .eq("provider", "google")
        .limit(1)
        .execute()
    )
    if by_vendor.data:
        return by_vendor.data[0]

    profile = (
        admin.table("profiles")
        .select("id")
        .eq("vendor_id", account_id)
        .limit(1)
        .execute()
    )
    if profile.data:
        return get_calendar_connection(profile.data[0]["id"])
    return None


def _connection_owner_profile_id(connection: dict[str, Any]) -> str | None:
    owner = connection.get("profile_id")
    return str(owner) if owner else None


def refresh_calendar_credentials(profile_id: str) -> Credentials | None:
    """
    Return credentials with a valid access token.
    Refreshes when expired; clears the connection if refresh is rejected (invalid_grant).
    """
    connection = get_calendar_connection_for_account(profile_id)
    if not connection:
        return None
    owner_id = _connection_owner_profile_id(connection)
    if not owner_id:
        logger.warning("Calendar connection missing profile_id (account=%s)", profile_id)
        return None
    profile_id = owner_id
    credentials = _credentials_from_row(connection)
    if not credentials:
        return None

    if not credentials.expired:
        return credentials

    if not credentials.refresh_token:
        logger.warning(
            "Calendar access expired for profile %s and no refresh token — reconnect on /calendar",
            profile_id,
        )
        clear_calendar_connection(profile_id)
        return None

    try:
        credentials.refresh(Request())
        _normalize_credentials_expiry(credentials)
        _persist_credentials(profile_id, connection.get("calendar_id") or "primary", credentials)
        return credentials
    except RefreshError as exc:
        logger.warning(
            "Calendar refresh failed for profile %s (%s) — user must reconnect Google Calendar",
            profile_id,
            exc,
        )
        clear_calendar_connection(profile_id)
        return None


def get_calendar_access_token(profile_id: str) -> str | None:
    credentials = refresh_calendar_credentials(profile_id)
    return credentials.token if credentials else None


def get_calendar_connection(profile_id: str) -> dict[str, Any] | None:
    admin = get_supabase_admin()
    row = (
        admin.table("calendar_connections")
        .select("*")
        .eq("profile_id", profile_id)
        .eq("provider", "google")
        .limit(1)
        .execute()
    )
    if not row.data:
        return None
    return row.data[0]


def save_calendar_connection(profile_id: str, calendar_id: str, token_payload: dict[str, Any]) -> dict[str, Any]:
    settings = _settings()
    if not settings.google_client_id or not settings.google_client_secret or not settings.google_redirect_uri:
        raise RuntimeError("Google Calendar OAuth is not configured")

    credentials = Credentials(
        token=token_payload.get("access_token"),
        refresh_token=token_payload.get("refresh_token"),
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        token_uri="https://oauth2.googleapis.com/token",
        scopes=token_payload.get("scopes") or _scopes(),
        expiry=_parse_expiry(token_payload.get("token_expiry")),
    )
    _normalize_credentials_expiry(credentials)
    _persist_credentials(profile_id, calendar_id, credentials)
    return {"connected": True, "calendar_id": calendar_id or "primary"}


def _create_calendar_event_rest(
    *,
    connection: dict[str, Any],
    summary: str,
    description: str,
    start_dt: datetime,
    end_dt: datetime,
) -> str | None:
    """Create via Calendar REST API. Returns Google event id on success."""
    owner_id = _connection_owner_profile_id(connection)
    if not owner_id:
        return None

    credentials = refresh_calendar_credentials(owner_id)
    if not credentials:
        return None

    try:
        service = build("calendar", "v3", credentials=credentials)
        event = {
            "summary": summary,
            "description": description,
            "start": {
                "dateTime": start_dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
                "timeZone": "Asia/Karachi",
            },
            "end": {
                "dateTime": end_dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
                "timeZone": "Asia/Karachi",
            },
        }
        created = (
            service.events()
            .insert(calendarId=connection.get("calendar_id") or "primary", body=event)
            .execute()
        )
        event_id = created.get("id") if isinstance(created, dict) else None
        if event_id:
            logger.info("Calendar REST event created for %s: %s", owner_id, event_id)
        return event_id
    except Exception as exc:
        logger.warning("Calendar REST create failed for %s: %s", owner_id, exc)
        return None


async def create_events_for_appointment(
    *,
    tenant_id: str,
    vendor_id: str,
    summary: str,
    description: str,
    start_dt: datetime,
    end_dt: datetime,
) -> dict[str, Any]:
    from app.services.calendar_mcp import mcp_create_event

    created: list[str] = []
    skipped: list[str] = []
    details: list[dict[str, Any]] = []
    use_mcp = _settings().use_calendar_mcp

    for account_id in (tenant_id, vendor_id):
        if not account_id:
            skipped.append("no_profile")
            continue
        connection = get_calendar_connection_for_account(account_id)
        if not connection:
            logger.info("Calendar: no connection for account %s — skipped", account_id)
            skipped.append(account_id)
            details.append({"account_id": account_id, "reason": "not_connected"})
            continue
        owner_id = _connection_owner_profile_id(connection) or account_id
        calendar_id = connection.get("calendar_id") or "primary"
        event_id: str | None = None
        via: str | None = None
        try:
            event_id = _create_calendar_event_rest(
                connection=connection,
                summary=summary,
                description=description,
                start_dt=start_dt,
                end_dt=end_dt,
            )
            if event_id:
                via = "rest"

            if not event_id and use_mcp:
                event_id = await mcp_create_event(
                    connection=connection,
                    summary=summary,
                    description=description,
                    start_dt=start_dt,
                    end_dt=end_dt,
                    calendar_id=calendar_id,
                )
                if event_id:
                    via = "mcp"

            if event_id:
                created.append(account_id)
                details.append(
                    {"account_id": account_id, "owner_id": owner_id, "via": via, "event_id": event_id}
                )
                logger.info(
                    "Calendar booked for account %s (owner %s) via %s: %s",
                    account_id,
                    owner_id,
                    via,
                    event_id,
                )
            else:
                skipped.append(account_id)
                details.append({"account_id": account_id, "owner_id": owner_id, "reason": "create_failed"})
                logger.warning(
                    "Calendar: booking failed for account %s (owner %s) — reconnect on /calendar",
                    account_id,
                    owner_id,
                )
        except Exception:
            logger.exception("Google Calendar event creation failed for %s", account_id)
            skipped.append(account_id)
            details.append({"account_id": account_id, "reason": "exception"})

    return {"created": created, "skipped": skipped, "details": details}
