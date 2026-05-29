"""Backfill RAG: index tickets + embed chunks. Run from backend/: python scripts/backfill_rag.py"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.rag.indexer import backfill_embeddings, backfill_maintenance_tickets  # noqa: E402


async def main() -> None:
    tickets = await backfill_maintenance_tickets(limit=200)
    print("Tickets indexed:", tickets)
    emb = await backfill_embeddings(limit=500)
    print("Embeddings:", emb)


if __name__ == "__main__":
    asyncio.run(main())
