"""Vector retrieval from knowledge_chunks."""

import logging
import math
from typing import Any

from app.config import get_settings
from app.db import get_supabase_admin
from app.services.rag.embeddings import embed_text

logger = logging.getLogger(__name__)


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)

async def retrieve_chunks(
    *,
    query: str,
    property_id: str | None = None,
    tenant_id: str | None = None,
    top_k: int | None = None,
    min_similarity: float | None = None,
) -> list[dict[str, Any]]:
    settings = get_settings()
    if not settings.rag_enabled:
        return []

    top_k = top_k or settings.rag_top_k
    min_similarity = min_similarity if min_similarity is not None else settings.rag_min_similarity

    embedding = await embed_text(query)
    if not embedding:
        return await _policy_text_fallback(top_k)

    admin = get_supabase_admin()
    hits: list[dict[str, Any]] = []
    use_fallback = False
    
    # ALWAYS try the vector database RPC first, even for global manager searches
    try:
        result = admin.rpc(
            "match_knowledge_chunks",
            {
                "query_embedding": embedding,
                "match_count": top_k,
                "match_property_id": property_id, # Can be null
                "match_tenant_id": tenant_id,     # Can be null
                "include_global": True,
            },
        ).execute()
        hits = result.data or []
    except Exception as exc:
        logger.warning("RPC match_knowledge_chunks failed (%s), using fallback scan", exc)
        use_fallback = True

    if use_fallback:
        hits = await _fallback_scan(embedding, property_id, tenant_id, top_k)

    filtered = [h for h in hits if float(h.get("similarity") or 0) >= min_similarity]
    if not filtered and hits:
        # Keep best matches even if below threshold (e.g. sparse index)
        filtered = sorted(hits, key=lambda h: float(h.get("similarity") or 0), reverse=True)[:top_k]
    
    if not filtered:
        extra = await _policy_text_fallback(top_k)
        seen = {h.get("id") for h in hits}
        for row in extra:
            if row.get("id") not in seen:
                filtered.append(row)
                
    return filtered[:top_k]

# async def retrieve_chunks(
#     *,
#     query: str,
#     property_id: str | None = None,
#     tenant_id: str | None = None,
#     top_k: int | None = None,
#     min_similarity: float | None = None,
# ) -> list[dict[str, Any]]:
#     settings = get_settings()
#     if not settings.rag_enabled:
#         return []

#     top_k = top_k or settings.rag_top_k
#     min_similarity = min_similarity if min_similarity is not None else settings.rag_min_similarity

#     embedding = await embed_text(query)
#     if not embedding:
#         return await _policy_text_fallback(top_k)

#     admin = get_supabase_admin()
#     # Broad manager search (no property): use fallback — RPC only returns policies when both IDs null
#     use_fallback = not property_id and not tenant_id
#     hits: list[dict[str, Any]] = []
#     if not use_fallback:
#         try:
#             result = admin.rpc(
#                 "match_knowledge_chunks",
#                 {
#                     "query_embedding": embedding,
#                     "match_count": top_k,
#                     "match_property_id": property_id,
#                     "match_tenant_id": tenant_id,
#                     "include_global": True,
#                 },
#             ).execute()
#             hits = result.data or []
#         except Exception as exc:
#             logger.warning("RPC match_knowledge_chunks failed (%s), using fallback scan", exc)
#             use_fallback = True
#     if use_fallback:
#         hits = await _fallback_scan(embedding, property_id, tenant_id, top_k)

#     filtered = [h for h in hits if float(h.get("similarity") or 0) >= min_similarity]
#     if not filtered and hits:
#         # Keep best matches even if below threshold (e.g. sparse index)
#         filtered = sorted(hits, key=lambda h: float(h.get("similarity") or 0), reverse=True)[:top_k]
#     if not filtered:
#         extra = await _policy_text_fallback(top_k)
#         seen = {h.get("id") for h in hits}
#         for row in extra:
#             if row.get("id") not in seen:
#                 filtered.append(row)
#     return filtered[:top_k]


async def _policy_text_fallback(top_k: int) -> list[dict[str, Any]]:
    """When embeddings fail, still return global policy chunks (no vector search)."""
    admin = get_supabase_admin()
    try:
        result = (
            admin.table("knowledge_chunks")
            .select("id, content, source_type, source_id, property_id, metadata")
            .eq("source_type", "policy")
            .limit(top_k)
            .execute()
        )
        return [
            {**row, "similarity": 0.5, "fallback": True}
            for row in (result.data or [])
        ]
    except Exception as exc:
        logger.warning("Policy text fallback failed: %s", exc)
        return []


async def _fallback_scan(
    embedding: list[float],
    property_id: str | None,
    tenant_id: str | None,
    top_k: int,
) -> list[dict[str, Any]]:
    admin = get_supabase_admin()
    q = admin.table("knowledge_chunks").select(
        "id, content, source_type, source_id, property_id, metadata, embedding"
    )
    if property_id:
        q = q.or_(f"property_id.eq.{property_id},source_type.eq.policy")
    result = q.limit(150).execute()
    scored: list[dict[str, Any]] = []
    for row in result.data or []:
        emb = row.get("embedding")
        if not emb or isinstance(emb, str):
            continue
        if tenant_id and row.get("metadata", {}).get("tenant_id"):
            if str(row["metadata"]["tenant_id"]) != str(tenant_id):
                if row.get("source_type") != "policy":
                    continue
        sim = _cosine_similarity(embedding, [float(x) for x in emb])
        scored.append({**row, "similarity": sim})
    scored.sort(key=lambda x: x["similarity"], reverse=True)
    return scored[:top_k]


async def retrieve_for_request(
    *,
    query: str,
    property_id: str | None,
    tenant_id: str | None = None,
) -> list[dict[str, Any]]:
    return await retrieve_chunks(
        query=query,
        property_id=property_id,
        tenant_id=tenant_id,
    )


def format_chunks_for_prompt(chunks: list[dict[str, Any]], *, max_chars: int = 3500) -> str:
    if not chunks:
        return ""
    lines: list[str] = []
    total = 0
    for i, c in enumerate(chunks, 1):
        meta = c.get("metadata") or {}
        title = meta.get("title") or meta.get("ticket_id") or c.get("source_type", "record")
        sim = c.get("similarity")
        sim_s = f" (relevance {sim:.2f})" if sim is not None else ""
        line = f"{i}. [{title}]{sim_s}\n{c.get('content', '')}"
        if total + len(line) > max_chars:
            break
        lines.append(line)
        total += len(line)
    return "\n\n".join(lines)
