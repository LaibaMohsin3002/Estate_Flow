import re
from datetime import date, datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from app.services.llm import structured_completion

KARACHI = ZoneInfo("Asia/Karachi")
WEEKDAYS = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}
MONTHS = {
    "january": 1,
    "jan": 1,
    "february": 2,
    "feb": 2,
    "march": 3,
    "mar": 3,
    "april": 4,
    "apr": 4,
    "may": 5,
    "june": 6,
    "jun": 6,
    "july": 7,
    "jul": 7,
    "august": 8,
    "aug": 8,
    "september": 9,
    "sep": 9,
    "sept": 9,
    "october": 10,
    "oct": 10,
    "november": 11,
    "nov": 11,
    "december": 12,
    "dec": 12,
}
DECLINE_PATTERNS = (
    "not available",
    "unavailable",
    "can't make",
    "cannot make",
    "can't do",
    "cannot do",
    "decline",
    "pass on",
    "not possible",
    "too busy",
)
ACCEPT_PATTERNS = (
    "yes",
    "okay",
    "ok",
    "available",
    "can do",
    "can make",
    "sounds good",
    "i can do",
    "i am available",
    "i'll be there",
)


def _normalize_text(text: str) -> str:
    return " ".join(text.replace("\n", " ").split())


def _parse_explicit_date(value: str, base_date: date) -> date | None:
    value = value.strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            parsed = datetime.strptime(value, fmt).date()
            return parsed
        except ValueError:
            continue
    return None


def _extract_time(text: str) -> tuple[int, int] | None:
    match = re.search(
        r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        match = re.search(r"\b(\d{1,2})\s*(am|pm)\b", text, flags=re.IGNORECASE)
    if not match:
        return None
    hour = int(match.group(1))
    minute = int(match.group(2) or 0)
    suffix = match.group(3).lower()
    if suffix == "pm" and hour < 12:
        hour += 12
    if suffix == "am" and hour == 12:
        hour = 0
    return hour, minute


def _parse_natural_date(text: str) -> tuple[date | None, str | None]:
    """e.g. 26th may 2026, 26 may 2026, may 26 2026."""
    dmy = re.search(
        r"\b(\d{1,2})(?:st|nd|rd|th)?\s+"
        r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
        r"jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
        r"\s+(\d{4})\b",
        text,
        flags=re.IGNORECASE,
    )
    if dmy:
        month_key = dmy.group(2).lower()
        month = MONTHS.get(month_key)
        if month:
            try:
                parsed = date(int(dmy.group(3)), month, int(dmy.group(1)))
                return parsed, dmy.group(0)
            except ValueError:
                pass

    mdy = re.search(
        r"\b(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
        r"jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
        r"\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})\b",
        text,
        flags=re.IGNORECASE,
    )
    if mdy:
        month_key = mdy.group(1).lower()
        month = MONTHS.get(month_key)
        if month:
            try:
                parsed = date(int(mdy.group(3)), month, int(mdy.group(2)))
                return parsed, mdy.group(0)
            except ValueError:
                pass
    return None, None


def _next_weekday(target: int, base_date: date) -> date:
    delta = (target - base_date.weekday()) % 7
    if delta == 0:
        delta = 7
    return base_date + timedelta(days=delta)


def _extract_appointment_datetime(text: str, *, now: datetime | None = None) -> tuple[datetime | None, str | None]:
    normalized = _normalize_text(text)
    now = now or datetime.now(KARACHI)
    base_date = now.date()
    appointment_text = None

    if re.search(r"\btoday\b", normalized, flags=re.IGNORECASE):
        appointment_date = base_date
        appointment_text = "today"
    elif re.search(r"\btomorrow\b", normalized, flags=re.IGNORECASE):
        appointment_date = base_date + timedelta(days=1)
        appointment_text = "tomorrow"
    else:
        weekday_match = re.search(r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", normalized, flags=re.IGNORECASE)
        explicit_match = re.search(r"\b(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}|\d{2}-\d{2}-\d{4})\b", normalized)
        appointment_date = None
        if weekday_match:
            appointment_date = _next_weekday(WEEKDAYS[weekday_match.group(1).lower()], base_date)
            appointment_text = weekday_match.group(1)
        elif explicit_match:
            parsed_date = _parse_explicit_date(explicit_match.group(1), base_date)
            if parsed_date:
                appointment_date = parsed_date
                appointment_text = explicit_match.group(1)
        if appointment_date is None:
            natural_date, natural_label = _parse_natural_date(normalized)
            if natural_date:
                appointment_date = natural_date
                appointment_text = natural_label

    time = _extract_time(normalized)
    if time is None:
        time = (10, 0)

    if appointment_date is None:
        return None, None

    local_dt = datetime.combine(appointment_date, datetime.min.time().replace(hour=time[0], minute=time[1]), tzinfo=KARACHI)
    return local_dt.astimezone(timezone.utc), appointment_text


async def parse_vendor_reply(message: str) -> dict[str, Any]:
    text = _normalize_text(message)
    lower = text.lower()

    decision = "unclear"
    if any(pattern in lower for pattern in DECLINE_PATTERNS):
        decision = "decline"
    elif any(pattern in lower for pattern in ACCEPT_PATTERNS):
        decision = "accept"
    elif re.search(
        r"\b(today|tomorrow|monday|tuesday|wednesday|thursday|friday|saturday|sunday|"
        r"\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}|\d{2}-\d{2}-\d{4}|"
        r"\d{1,2}(?:st|nd|rd|th)?\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)|"
        r"\d{1,2}(?::\d{2})?\s*(?:am|pm)|\d{1,2}\s*(?:am|pm))\b",
        text,
        flags=re.IGNORECASE,
    ):
        decision = "accept"

    appointment_dt, appointment_label = _extract_appointment_datetime(text)
    result: dict[str, Any] = {
        "decision": decision,
        "appointment_text": text if decision == "accept" and appointment_dt else None,
        "appointment_iso": appointment_dt.isoformat().replace("+00:00", "Z") if appointment_dt else None,
        "notes": None,
    }

    system = (
        "You parse short vendor WhatsApp replies for estate maintenance requests. "
        "Return compact JSON with keys: decision, appointment_text, appointment_iso, notes. "
        "decision must be one of accept, decline, or unclear."
    )
    try:
        llm_result = await structured_completion(system, text)
        if isinstance(llm_result, dict):
            if llm_result.get("decision") in {"accept", "decline", "unclear"}:
                result["decision"] = str(llm_result.get("decision"))
            if llm_result.get("appointment_text"):
                result["appointment_text"] = str(llm_result.get("appointment_text"))
            if llm_result.get("appointment_iso"):
                result["appointment_iso"] = str(llm_result.get("appointment_iso"))
            if llm_result.get("notes"):
                result["notes"] = str(llm_result.get("notes"))
    except Exception:
        pass

    if result["appointment_iso"] is None and appointment_label:
        result["appointment_text"] = text

    if result["decision"] == "accept" and not result["appointment_iso"]:
        default_dt = _default_appointment_datetime()
        result["appointment_iso"] = default_dt.isoformat().replace("+00:00", "Z")
        result["appointment_default"] = True
        result["appointment_text"] = result.get("appointment_text") or (
            "Tomorrow 10:00 AM (Asia/Karachi) — assign a time in WhatsApp to change this"
        )

    return result


def _default_appointment_datetime(*, now: datetime | None = None) -> datetime:
    """Next-day 10:00 AM Karachi when the vendor accepts without a concrete time."""
    now = now or datetime.now(KARACHI)
    target_date = now.date() + timedelta(days=1)
    local_dt = datetime.combine(
        target_date,
        datetime.min.time().replace(hour=10, minute=0),
        tzinfo=KARACHI,
    )
    return local_dt.astimezone(timezone.utc)
