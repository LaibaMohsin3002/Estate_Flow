"""Index and update knowledge_chunks in Supabase."""

import logging
from typing import Any

from app.db import get_supabase_admin
from app.services.rag.chunker import build_ticket_document, chunk_text
from app.services.rag.embeddings import embed_text

logger = logging.getLogger(__name__)


async def _upsert_chunk(
    *,
    source_type: str,
    source_id: str | None,
    property_id: str | None,
    chunk_index: int,
    content: str,
    metadata: dict[str, Any],
    embedding: list[float] | None,
) -> None:
    admin = get_supabase_admin()
    row: dict[str, Any] = {
        "source_type": source_type,
        "source_id": source_id,
        "property_id": property_id,
        "chunk_index": chunk_index,
        "content": content,
        "metadata": metadata,
    }
    if embedding is not None:
        row["embedding"] = embedding

    admin.table("knowledge_chunks").upsert(
        row,
        on_conflict="source_type,source_id,chunk_index",
    ).execute()


async def index_maintenance_ticket(
    *,
    request_id: str,
    property_id: str | None,
    tenant_id: str | None,
    ticket_id: str,
    summary: str,
    issue: str,
    category: str | None = None,
    urgency: str | None = None,
    status: str | None = None,
    property_name: str | None = None,
    unit: str | None = None,
) -> int:
    doc = build_ticket_document(
        ticket_id=ticket_id,
        summary=summary or issue[:200],
        issue=issue,
        category=category,
        urgency=urgency,
        status=status,
        property_name=property_name,
        unit=unit,
    )
    chunks = chunk_text(doc)
    if not chunks:
        return 0

    metadata_base: dict[str, Any] = {
        "ticket_id": ticket_id,
        "tenant_id": tenant_id,
        "category": category,
        "urgency": urgency,
        "status": status,
    }
    count = 0
    for i, chunk in enumerate(chunks):
        emb = await embed_text(chunk)
        await _upsert_chunk(
            source_type="maintenance_ticket",
            source_id=request_id,
            property_id=property_id,
            chunk_index=i,
            content=chunk,
            metadata=metadata_base,
            embedding=emb,
        )
        count += 1
    return count


async def index_inspection(
    *,
    inspection_id: str,
    property_id: str | None,
    property_name: str,
    executive_summary: str,
    recommendations: list[str] | None = None,
    top_issues: list[str] | None = None,
    risk_level: str | None = None,
) -> int:
    recs = "\n".join(f"- {r}" for r in (recommendations or [])[:10])
    issues = "\n".join(f"- {t}" for t in (top_issues or [])[:10])
    doc = (
        f"Inspection at {property_name}\n"
        f"Risk: {risk_level or 'Medium'}\n"
        f"Summary: {executive_summary}\n"
        f"Top issues:\n{issues or 'None'}\n"
        f"Recommendations:\n{recs or 'None'}"
    )
    chunks = chunk_text(doc)
    metadata = {"property_name": property_name, "risk_level": risk_level}
    count = 0
    for i, chunk in enumerate(chunks):
        emb = await embed_text(chunk)
        await _upsert_chunk(
            source_type="inspection",
            source_id=inspection_id,
            property_id=property_id,
            chunk_index=i,
            content=chunk,
            metadata=metadata,
            embedding=emb,
        )
        count += 1
    return count


async def index_policy_text(
    *,
    content: str,
    title: str,
    chunk_index: int = 0,
) -> int:
    emb = await embed_text(content)
    await _upsert_chunk(
        source_type="policy",
        source_id=None,
        property_id=None,
        chunk_index=chunk_index,
        content=content,
        metadata={"title": title},
        embedding=emb,
    )
    return 1


async def backfill_maintenance_tickets(*, limit: int = 150) -> dict[str, int]:
    """Index historical maintenance requests into knowledge_chunks."""
    admin = get_supabase_admin()
    rows = (
        admin.table("maintenance_requests")
        .select(
            "id, ticket_id, property_id, property_name, unit, tenant_id, "
            "original_issue, redacted_issue, status"
        )
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    indexed = 0
    chunks_total = 0
    for row in rows.data or []:
        pipe = (
            admin.table("maintenance_pipeline_results")
            .select("category, urgency, summary")
            .eq("request_id", row["id"])
            .limit(1)
            .execute()
        )
        pl = (pipe.data or [{}])[0]
        n = await index_maintenance_ticket(
            request_id=row["id"],
            property_id=str(row["property_id"]) if row.get("property_id") else None,
            tenant_id=str(row["tenant_id"]) if row.get("tenant_id") else None,
            ticket_id=row.get("ticket_id") or row["id"][:8],
            summary=pl.get("summary") or "",
            issue=row.get("redacted_issue") or row.get("original_issue") or "",
            category=pl.get("category"),
            urgency=pl.get("urgency"),
            status=row.get("status"),
            property_name=row.get("property_name"),
            unit=row.get("unit"),
        )
        if n:
            indexed += 1
            chunks_total += n
    return {"requests_indexed": indexed, "chunks_written": chunks_total}


async def backfill_embeddings(*, limit: int = 200) -> dict[str, int]:
    """Embed policy rows and chunks missing vectors."""
    admin = get_supabase_admin()
    rows = (
        admin.table("knowledge_chunks")
        .select("id, content, source_type, source_id, property_id, chunk_index, metadata")
        .is_("embedding", "null")
        .limit(limit)
        .execute()
    )
    updated = 0
    failed = 0
    for row in rows.data or []:
        emb = await embed_text(row["content"])
        if not emb:
            failed += 1
            continue
        admin.table("knowledge_chunks").update({"embedding": emb}).eq("id", row["id"]).execute()
        updated += 1
    return {"updated": updated, "failed": failed, "pending": len(rows.data or [])}
