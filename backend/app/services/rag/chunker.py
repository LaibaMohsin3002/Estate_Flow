"""Simple text chunking for RAG indexing."""

from typing import Any


def chunk_text(text: str, *, max_chars: int = 1200, overlap: int = 150) -> list[str]:
    text = (text or "").strip()
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        if end < len(text):
            break_at = text.rfind("\n", start, end)
            if break_at > start + max_chars // 2:
                end = break_at + 1
        chunks.append(text[start:end].strip())
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return [c for c in chunks if c]


def build_ticket_document(
    *,
    ticket_id: str,
    summary: str,
    issue: str,
    category: str | None,
    urgency: str | None,
    status: str | None,
    property_name: str | None,
    unit: str | None,
) -> str:
    parts = [
        f"Ticket {ticket_id}",
        f"Property: {property_name or 'Unknown'} · Unit {unit or 'N/A'}",
        f"Category: {category or 'General'} · Urgency: {urgency or 'Medium'} · Status: {status or 'Open'}",
        f"Summary: {summary}",
        f"Issue: {issue}",
    ]
    return "\n".join(parts)
