"""RAG chat and knowledge index maintenance."""

from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_current_user, require_roles
from app.config import get_settings
from app.db import get_supabase_admin
from app.schemas import ChatRequest
from app.services.rag.chat import answer_with_rag
from app.services.rag.embeddings import embed_text
from app.services.rag.indexer import backfill_embeddings, backfill_maintenance_tickets

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.get("/status")
async def rag_status(user: dict = Depends(get_current_user)):
    """Diagnostics: is RAG configured and are embeddings present?"""
    admin = get_supabase_admin()
    settings = get_settings()
    total = 0
    with_emb = 0
    try:
        rows = admin.table("knowledge_chunks").select("id", count="exact").execute()
        total = rows.count or 0
        emb_rows = (
            admin.table("knowledge_chunks")
            .select("id", count="exact")
            .not_.is_("embedding", "null")
            .execute()
        )
        with_emb = emb_rows.count or 0
    except Exception as exc:
        return {
            "data": {
                "rag_enabled": settings.rag_enabled,
                "table_exists": False,
                "error": str(exc),
                "hint": "Run supabase/migrations/012_rag_knowledge_chunks.sql",
            }
        }

    test_embed = None
    if settings.rag_enabled:
        test_embed = await embed_text("test") is not None

    return {
        "data": {
            "rag_enabled": settings.rag_enabled,
            "openrouter_model": settings.openrouter_model,
            "embedding_model": settings.embedding_model,
            "chunks_total": total,
            "chunks_with_embeddings": with_emb,
            "embedding_api_ok": test_embed,
            "hint": (
                "Run: python scripts/backfill_rag.py"
                if with_emb < total
                else "RAG index looks ready"
            ),
        }
    }


@router.post("/chat/manager")
async def chat_manager(body: ChatRequest, user: dict = Depends(require_roles("admin", "manager", "inspector"))):
    """Phase 2: manager/inspector RAG chat scoped to property when set."""
    if not get_settings().rag_enabled:
        raise HTTPException(status_code=503, detail="RAG is disabled on this server.")

    property_id = body.property_id or user.get("property_id")
    if user.get("role") == "admin":
        property_id = body.property_id or property_id

    result = await answer_with_rag(
        message=body.message,
        role=user.get("role", "manager"),
        property_id=str(property_id) if property_id else None,
        tenant_id=None,
        history=[h.model_dump() for h in body.history],
    )
    return {"data": result}


@router.post("/chat/tenant")
async def chat_tenant(body: ChatRequest, user: dict = Depends(require_roles("tenant"))):
    """Phase 3: tenant RAG chat — only their tickets and property context."""
    if not get_settings().rag_enabled:
        raise HTTPException(status_code=503, detail="RAG is disabled on this server.")

    result = await answer_with_rag(
        message=body.message,
        role="tenant",
        property_id=str(user["property_id"]) if user.get("property_id") else None,
        tenant_id=str(user["id"]),
        history=[h.model_dump() for h in body.history],
    )
    return {"data": result}


@router.post("/backfill")
async def backfill_knowledge_embeddings(
    user: dict = Depends(require_roles("admin", "manager")),
):
    """Embed chunks that are missing vectors (policies + indexed tickets)."""
    stats = await backfill_embeddings(limit=300)
    return {"data": stats}


@router.post("/index-tickets")
async def index_historical_tickets(
    user: dict = Depends(require_roles("admin", "manager")),
):
    """Index recent maintenance requests for RAG (more than the 3 policy chunks)."""
    stats = await backfill_maintenance_tickets(limit=200)
    emb = await backfill_embeddings(limit=400)
    return {"data": {**stats, "embeddings": emb}}
