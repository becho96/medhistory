"""Backfill semantic-search embeddings for existing documents.

Walks every completed document whose `documents.embedding` is NULL, fetches the
corresponding summary from MongoDB, batches them through the embeddings sidecar,
and writes the resulting vectors back to PostgreSQL.

Idempotent: re-running only processes documents still missing an embedding.

Usage (inside the backend container, sidecar must be up):
    docker compose exec backend python scripts/backfill_embeddings.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

import httpx
from bson import ObjectId
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.postgres import AsyncSessionLocal
from app.db.mongodb import document_metadata_collection
from app.services.embeddings_client import embed_passages

BATCH_SIZE = 16


async def _fetch_pending(db: AsyncSession) -> list[dict]:
    sql = text(
        """
        SELECT id, mongodb_metadata_id
        FROM documents
        WHERE processing_status = 'completed'
          AND embedding IS NULL
          AND mongodb_metadata_id IS NOT NULL
        ORDER BY created_at
        """
    )
    rows = (await db.execute(sql)).mappings().all()
    return [dict(r) for r in rows]


async def _load_summaries(mongo_ids: list[str]) -> dict[str, str]:
    object_ids = []
    for mid in mongo_ids:
        try:
            object_ids.append(ObjectId(mid))
        except Exception:
            continue
    if not object_ids:
        return {}

    summaries: dict[str, str] = {}
    cursor = document_metadata_collection.find(
        {"_id": {"$in": object_ids}},
        {"extracted_data.summary": 1},
    )
    async for doc in cursor:
        s = (doc.get("extracted_data") or {}).get("summary") or ""
        if s.strip():
            summaries[str(doc["_id"])] = s
    return summaries


async def _wait_for_sidecar() -> None:
    """Block until the sidecar is reachable. First start downloads the model
    (~30s); we wait up to 2 minutes."""
    url = f"{settings.EMBEDDINGS_URL.rstrip('/')}/health"
    deadline = 120
    async with httpx.AsyncClient(timeout=5.0) as client:
        for _ in range(deadline):
            try:
                r = await client.get(url)
                if r.status_code == 200:
                    print(f"✅ Sidecar ready: {r.json()}")
                    return
            except Exception:
                pass
            await asyncio.sleep(1)
    raise RuntimeError(f"Embeddings sidecar not reachable at {url} after {deadline}s")


async def main() -> None:
    await _wait_for_sidecar()

    async with AsyncSessionLocal() as db:
        pending = await _fetch_pending(db)
        print(f"📋 Pending documents: {len(pending)}")
        if not pending:
            return

        total_done = 0
        for i in range(0, len(pending), BATCH_SIZE):
            batch = pending[i : i + BATCH_SIZE]
            summaries = await _load_summaries([r["mongodb_metadata_id"] for r in batch])

            ordered = [(r, summaries.get(r["mongodb_metadata_id"])) for r in batch]
            usable = [(r, s) for r, s in ordered if s]
            skipped = len(ordered) - len(usable)
            if not usable:
                if skipped:
                    print(f"⏭  Skipped batch: {skipped} documents have no summary")
                continue

            vectors = await embed_passages([s for _, s in usable])

            for (row, _), vec in zip(usable, vectors):
                await db.execute(
                    text("UPDATE documents SET embedding = CAST(:v AS vector) WHERE id = :id"),
                    {"v": str(vec), "id": row["id"]},
                )
            await db.commit()

            total_done += len(usable)
            print(f"📦 Batch {i // BATCH_SIZE + 1}: indexed {len(usable)}, skipped {skipped}")

        print(f"✅ Done. Embedded {total_done} documents.")


if __name__ == "__main__":
    asyncio.run(main())
