"""RAG-grounded chat answers for managers and tenants."""

import logging
import re
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.config import get_settings
from app.db import get_supabase_admin
from app.services.llm import chat_completion
from app.services.rag.retriever import format_chunks_for_prompt, retrieve_chunks

logger = logging.getLogger(__name__)

MANAGER_SYSTEM = """You are EstateFlow Property Assistant for managers and admins.
Answer the user's questions in a warm, professional, and conversational human tone. 
When providing details about tickets, weave the information naturally into sentences or clear summaries rather than just dumping rigid bullet points.
If the context doesn't have the answer, politely let them know and suggest checking Approvals."""

TENANT_SYSTEM = """You are EstateFlow Help for tenants.
Answer questions about maintenance statuses or requests in a friendly, empathetic, and conversational tone.
Speak like a helpful property management assistant. Explain their ticket statuses naturally.
If unsure, gently suggest submitting a new request or checking their dashboard."""

# Change this to guide the tone instead of forcing rigid structures
RESPONSE_FORMAT = """
Format your response using clean, easy-to-read Markdown. 
Avoid sounding like a database dump; talk like a real human assistant helping a customer."""

ACTIVE_STATUSES = ("Open", "In Progress", "Scheduled", "Pending Approval", "Blocked")


def _clean_text(value: Any, *, max_len: int | None = None) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if max_len and len(text) > max_len:
        text = text[: max_len - 3].rsplit(" ", 1)[0].rstrip(".,;:-") + "..."
    return text


def _parse_ticket_chunk(chunk: dict[str, Any]) -> dict[str, str]:
    """Extract ticket fields from the compact indexed ticket document."""
    meta = chunk.get("metadata") or {}
    content = chunk.get("content") or ""

    def line_value(label: str) -> str:
        match = re.search(rf"^{label}:\s*(.+)$", content, flags=re.IGNORECASE | re.MULTILINE)
        return _clean_text(match.group(1)) if match else ""

    ticket_match = re.search(r"\bTKT-[A-Z0-9-]+\b", content, flags=re.IGNORECASE)
    category_line = line_value("Category")
    property_line = line_value("Property")

    category = str(meta.get("category") or "").strip()
    urgency = str(meta.get("urgency") or "").strip()
    status = str(meta.get("status") or "").strip()
    if category_line:
        category = category or _clean_text(re.split(r"\s*(?:[|]|\u00c2\u00b7|\u00b7)\s*", category_line)[0])
        urgency_match = re.search(r"Urgency:\s*([^|\u00c2\u00b7\u00b7]+)", category_line, flags=re.IGNORECASE)
        status_match = re.search(r"Status:\s*([^|\u00c2\u00b7\u00b7]+)", category_line, flags=re.IGNORECASE)
        urgency = urgency or _clean_text(urgency_match.group(1) if urgency_match else "")
        status = status or _clean_text(status_match.group(1) if status_match else "")

    prop = property_line
    unit = ""
    prop_match = re.search(r"(.+?)\s*(?:[|]|\u00c2\u00b7|\u00b7)\s*Unit\s+(.+)", property_line, flags=re.IGNORECASE)
    if prop_match:
        prop = _clean_text(prop_match.group(1))
        unit = _clean_text(prop_match.group(2))

    return {
        "id": str(chunk.get("source_id") or ""),
        "ticket_id": str(meta.get("ticket_id") or (ticket_match.group(0).upper() if ticket_match else "Ticket")),
        "status": status or "Open",
        "property_name": prop or "Property",
        "unit": unit,
        "category": category or "General",
        "urgency": urgency or "Medium",
        "issue": line_value("Summary") or line_value("Issue") or _clean_text(content, max_len=120),
    }


def _is_request_status_question(message: str) -> bool:
    q = message.lower()
    subject = any(word in q for word in ("request", "requests", "ticket", "tickets", "issue", "issues"))
    status_intent = any(
        phrase in q
        for phrase in (
            "status",
            "open",
            "still",
            "active",
            "current",
            "outstanding",
            "unresolved",
            "not resolved",
            "in progress",
            "scheduled",
            "pending",
            "approval",
            "resolved",
            "closed",
            "completed",
        )
    )
    return subject and status_intent


def _status_filter(message: str) -> tuple[tuple[str, ...] | None, str, str]:
    q = message.lower()
    if any(phrase in q for phrase in ("pending approval", "approval", "approve")):
        return ("Pending Approval",), "pending approval request", "Pending approval requests need manager action."
    if "in progress" in q or "progress" in q:
        return ("In Progress",), "in-progress request", "In-progress requests have already moved to vendor/workflow handling."
    if "scheduled" in q or "appointment" in q or "visit" in q:
        return ("Scheduled",), "scheduled request", "Scheduled requests have a vendor visit attached."
    if any(phrase in q for phrase in ("resolved", "closed", "completed", "done")):
        return ("Resolved",), "resolved request", "These are already closed."
    if any(phrase in q for phrase in ("open", "still", "active", "current", "outstanding", "unresolved", "not resolved")):
        return ACTIVE_STATUSES, "active request", "Resolved requests are hidden for this question."
    return None, "recent request", "Showing the most recent matching requests."


def _format_ticket_rows(rows: list[dict[str, Any]], *, label: str, note: str) -> str:
    if not rows:
        return f"**No {label}s found.**\n\nYou're all caught up for this view."

    noun = label if len(rows) == 1 else f"{label}s"
    lines = [f"**{len(rows)} {noun} found**", ""]
    for row in rows:
        pipe = row.get("pipeline") or {}
        ticket_id = row.get("ticket_id") or str(row.get("id", ""))[:8].upper()
        location = ", ".join(
            part for part in (row.get("property_name"), f"Unit {row.get('unit')}" if row.get("unit") else "") if part
        )
        category = pipe.get("category") or row.get("category")
        urgency = pipe.get("urgency") or row.get("urgency")
        issue = _clean_text(row.get("original_issue") or row.get("issue"), max_len=115)
        details = [
            _clean_text(row.get("status") or "Open"),
            _clean_text(location),
            _clean_text(f"{category} / {urgency} urgency" if category and urgency else category or urgency),
        ]
        detail_text = " - ".join(part for part in details if part)
        lines.append(f"- **{ticket_id}** - {detail_text}. {issue}")

    if note:
        lines.extend(["", note])
    return "\n".join(lines)

def _query_ticket_status_answer(
    *,
    message: str,
    role: str,
    property_id: str | None,
    tenant_id: str | None,
) -> dict[str, Any] | None:
    if not _is_request_status_question(message):
        return None

    # 1. Look for a specific ticket ID in the user's message
    ticket_match = re.search(r"\bTKT-[A-Z0-9-]+\b", message, flags=re.IGNORECASE)
    specific_ticket_id = ticket_match.group(0).upper() if ticket_match else None

    statuses, label, note = _status_filter(message)
    admin = get_supabase_admin()
    
    query = (
        admin.table("maintenance_requests")
        .select("id, ticket_id, property_id, property_name, unit, tenant_id, original_issue, status, created_at")
        .order("created_at", desc=True)
        .limit(8)
    )

    # 2. Filter by specific ticket ID if one was found
    if specific_ticket_id:
        query = query.eq("ticket_id", specific_ticket_id)
        label = "specific ticket"
        note = "" # Clear the "recent requests" note
    else:
        # Only apply broad status filters if no specific ticket is requested
        if statuses:
            query = query.in_("status", list(statuses))

    if tenant_id:
        query = query.eq("tenant_id", tenant_id)
    if property_id:
        query = query.eq("property_id", property_id)

    result = query.execute()
    rows = result.data or []
    
    # ... (Keep the rest of the function exactly the same from here down)
    request_ids = [row["id"] for row in rows if row.get("id")]
    
# def _query_ticket_status_answer(
#     *,
#     message: str,
#     role: str,
#     property_id: str | None,
#     tenant_id: str | None,
# ) -> dict[str, Any] | None:
#     if not _is_request_status_question(message):
#         return None

#     statuses, label, note = _status_filter(message)
#     admin = get_supabase_admin()
#     query = (
#         admin.table("maintenance_requests")
#         .select("id, ticket_id, property_id, property_name, unit, tenant_id, original_issue, status, created_at")
#         .order("created_at", desc=True)
#         .limit(8)
#     )
#     if tenant_id:
#         query = query.eq("tenant_id", tenant_id)
#     if property_id:
#         query = query.eq("property_id", property_id)
#     if statuses:
#         query = query.in_("status", list(statuses))

#     result = query.execute()
#     rows = result.data or []
#     request_ids = [row["id"] for row in rows if row.get("id")]
#     pipeline_by_id: dict[str, dict[str, Any]] = {}
#     if request_ids:
#         pipes = (
#             admin.table("maintenance_pipeline_results")
#             .select("request_id, category, urgency, assigned_vendor, scheduled_time")
#             .in_("request_id", request_ids)
#             .execute()
#         )
#         pipeline_by_id = {row["request_id"]: row for row in (pipes.data or []) if row.get("request_id")}

#     for row in rows:
#         row["pipeline"] = pipeline_by_id.get(row.get("id"), {})

#     answer = _format_ticket_rows(rows, label=label, note=note)
#     sources = [
#         {
#             "source_type": "maintenance_ticket",
#             "source_id": row.get("id"),
#             "title": row.get("ticket_id") or str(row.get("id", ""))[:8].upper(),
#             "snippet": " - ".join(
#                 part
#                 for part in (
#                     row.get("status"),
#                     row.get("property_name"),
#                     f"Unit {row.get('unit')}" if row.get("unit") else "",
#                 )
#                 if part
#             ),
#             "similarity": 1.0,
#         }
#         for row in rows[:3]
#     ]
#     return {"answer": answer, "sources": sources, "source": "structured_status"}


def _sources_from_chunks(chunks: list[dict[str, Any]], *, prefer_tickets: bool = False) -> list[dict[str, Any]]:
    ordered = sorted(
        chunks,
        key=lambda c: (
            0 if prefer_tickets and c.get("source_type") == "maintenance_ticket" else 1,
            -float(c.get("similarity") or 0),
        ),
    )
    sources: list[dict[str, Any]] = []
    seen: set[tuple[Any, Any]] = set()
    for chunk in ordered:
        key = (chunk.get("source_type"), chunk.get("source_id") or chunk.get("id"))
        if key in seen:
            continue
        seen.add(key)
        meta = chunk.get("metadata") or {}
        sources.append(
            {
                "source_type": chunk.get("source_type"),
                "source_id": chunk.get("source_id"),
                "title": meta.get("title") or meta.get("ticket_id") or chunk.get("source_type"),
                "snippet": _clean_text(chunk.get("content"), max_len=150),
                "similarity": chunk.get("similarity"),
            }
        )
        if len(sources) >= 3:
            break
    return sources


def _synthesize_local_answer(message: str, chunks: list[dict[str, Any]], role: str) -> str:
    """Natural-ish answer without LLM when rate-limited."""
    if not chunks:
        return (
            "I don't have property records loaded for that yet. "
            "Submit a maintenance request or ask your manager to run "
            "POST /api/knowledge/index-tickets to index past tickets."
        )

    q = message.lower()
    tickets = [c for c in chunks if c.get("source_type") == "maintenance_ticket"]
    inspections = [c for c in chunks if c.get("source_type") == "inspection"]

    if any(w in q for w in ("approval", "approve", "pending", "sign")):
        return (
            "Requests needing your action appear under Approvals in the sidebar. "
            "You'll get a bell notification titled \"Approval required\" when a ticket "
            "needs manager sign-off for critical urgency or report signature."
        )

    if tickets and any(w in q for w in ("status", "ticket", "request", "open", "resolved")):
        statuses, label, note = _status_filter(message)
        rows = [_parse_ticket_chunk(ticket) for ticket in tickets]
        if statuses:
            rows = [row for row in rows if row.get("status") in statuses]
        return _format_ticket_rows(rows[:5], label=label, note=note)

    if inspections:
        c = inspections[0]
        return f"**Recent inspection note**\n\n{_clean_text(c.get('content'), max_len=500)}"

    parts = ["**Relevant information from your property knowledge base**", ""]
    for c in chunks[:5]:
        meta = c.get("metadata") or {}
        title = meta.get("title") or meta.get("ticket_id") or c.get("source_type", "Note")
        body = _clean_text(c.get("content"), max_len=280)
        parts.append(f"- **{title}** - {body}")
    if role == "manager":
        parts.append("\nFor live ticket status, open the dashboard or Approvals.")
    else:
        parts.append("\nFor your requests, check My Requests on the dashboard.")
    return "\n".join(parts)


# async def answer_with_rag(
#     *,
#     message: str,
#     role: str,
#     property_id: str | None = None,
#     tenant_id: str | None = None,
#     history: list[dict[str, str]] | None = None,
# ) -> dict[str, Any]:
#     structured = _query_ticket_status_answer(
#         message=message,
#         role=role,
#         property_id=property_id,
#         tenant_id=tenant_id if role == "tenant" else None,
#     )
#     if structured:
#         return {
#             "answer": structured["answer"],
#             "sources": structured["sources"],
#             "tokens": 0,
#             "rag_hit_count": len(structured["sources"]),
#             "llm_source": structured["source"],
#         }

#     settings = get_settings()
#     chunks = await retrieve_chunks(
#         query=message,
#         property_id=property_id,
#         tenant_id=tenant_id if role == "tenant" else None,
#         top_k=settings.rag_chat_top_k,
#     )
#     context = format_chunks_for_prompt(chunks, max_chars=4000)

#     system = MANAGER_SYSTEM if role in ("manager", "admin", "inspector") else TENANT_SYSTEM
#     system += RESPONSE_FORMAT
#     if context:
#         system += f"\n\n--- Retrieved context ---\n{context}\n--- End context ---"

#     messages: list = [SystemMessage(content=system)]
#     for turn in (history or [])[-6:]:
#         r = turn.get("role")
#         c = turn.get("content", "")
#         if r == "user":
#             messages.append(HumanMessage(content=c))
#         elif r == "assistant":
#             messages.append(AIMessage(content=c))
#     messages.append(HumanMessage(content=message))

#     answer, tokens, source = await chat_completion(messages)

#     if not answer:
#         answer = _synthesize_local_answer(message, chunks, role)
#         source = "local_rag"

#     sources = _sources_from_chunks(chunks, prefer_tickets=_is_request_status_question(message))

#     return {
#         "answer": answer,
#         "sources": sources,
#         "tokens": tokens,
#         "rag_hit_count": len(chunks),
#         "llm_source": source,
#     }

async def answer_with_rag(
    *,
    message: str,
    role: str,
    property_id: str | None = None,
    tenant_id: str | None = None,
    history: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    
    # 1. Fetch live database tickets (if the user asked for status)
    structured = _query_ticket_status_answer(
        message=message,
        role=role,
        property_id=property_id,
        tenant_id=tenant_id if role == "tenant" else None,
    )

    # 2. Fetch semantic RAG chunks (policies, past knowledge)
    settings = get_settings()
    chunks = await retrieve_chunks(
        query=message,
        property_id=property_id,
        tenant_id=tenant_id if role == "tenant" else None,
        top_k=settings.rag_chat_top_k,
    )
    
    # 3. Combine both into a single Context for the LLM to read
    context = ""
    sources = []
    
    if structured:
        context += f"--- Live Database Ticket Status ---\n{structured['answer']}\n\n"
        sources.extend(structured["sources"])
        
    rag_context = format_chunks_for_prompt(chunks, max_chars=4000)
    if rag_context:
        context += f"--- Knowledge Base Context ---\n{rag_context}\n"
        sources.extend(_sources_from_chunks(chunks, prefer_tickets=_is_request_status_question(message)))

    # 4. Prepare the LLM Prompt
    system = MANAGER_SYSTEM if role in ("manager", "admin", "inspector") else TENANT_SYSTEM
    
    if context:
        system += f"\n\nUse the following information to answer the user conversationally:\n{context}"

    messages: list = [SystemMessage(content=system)]
    for turn in (history or [])[-6:]:
        r = turn.get("role")
        c = turn.get("content", "")
        if r == "user":
            messages.append(HumanMessage(content=c))
        elif r == "assistant":
            messages.append(AIMessage(content=c))
    messages.append(HumanMessage(content=message))

    # 5. Call the LLM
    answer, tokens, source = await chat_completion(messages)

    # 6. Fallback if the LLM crashes or rate-limits
    if not answer:
        answer = _synthesize_local_answer(message, chunks, role)
        source = "local_rag"

    return {
        "answer": answer,
        "sources": sources[:4], # Keep UI clean by limiting to 4 sources
        "tokens": tokens,
        "rag_hit_count": len(chunks) + (1 if structured else 0),
        "llm_source": source,
    }