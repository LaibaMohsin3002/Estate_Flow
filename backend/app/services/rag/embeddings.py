"""Text embeddings via OpenRouter (OpenAI-compatible)."""

import logging

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

EMBEDDING_DIM = 1536


def _normalize_vector(vec: list[float]) -> list[float] | None:
    """Ensure vector fits knowledge_chunks.embedding vector(1536)."""
    if not vec:
        return None
    if len(vec) == EMBEDDING_DIM:
        return [float(x) for x in vec]
    if len(vec) > EMBEDDING_DIM:
        logger.warning("Truncating embedding from %s to %s dims", len(vec), EMBEDDING_DIM)
        return [float(x) for x in vec[:EMBEDDING_DIM]]
    # Pad shorter vectors (some free models return 1024 etc.)
    padded = [float(x) for x in vec] + [0.0] * (EMBEDDING_DIM - len(vec))
    logger.info("Padded embedding from %s to %s dims", len(vec), EMBEDDING_DIM)
    return padded


async def _request_embedding(model: str, text: str, api_key: str, base_url: str) -> list[float] | None:
    payload = {"model": model, "input": text[:8000]}
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://estateflow.local",
        "X-Title": "EstateFlow-RAG",
    }
    async with httpx.AsyncClient(timeout=45.0) as client:
        resp = await client.post(
            f"{base_url.rstrip('/')}/embeddings",
            json=payload,
            headers=headers,
        )
        resp.raise_for_status()
        data = resp.json()
        vec = data["data"][0]["embedding"]
        return _normalize_vector(vec)


async def embed_text(text: str) -> list[float] | None:
    """Return embedding vector or None if disabled / all models failed."""
    settings = get_settings()
    if not settings.rag_enabled:
        return None

    cleaned = (text or "").strip()
    if not cleaned:
        return None

    models = [settings.embedding_model]
    for m in settings.embedding_fallback_models.split(","):
        m = m.strip()
        if m and m not in models:
            models.append(m)

    last_err: Exception | None = None
    for model in models:
        try:
            vec = await _request_embedding(
                model,
                cleaned,
                settings.openrouter_api_key,
                settings.openrouter_base_url,
            )
            if vec:
                return vec
        except Exception as exc:
            last_err = exc
            logger.warning("Embedding model %s failed: %s", model, exc)

    if last_err:
        logger.warning("All embedding models failed; RAG will use text fallback. Last: %s", last_err)
    return None
