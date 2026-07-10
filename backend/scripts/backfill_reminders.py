"""Backfill auto reminders for existing documents.

Walks every completed document, loads its extracted `orders` from MongoDB and
materializes auto reminders via the same sync used at ingestion time.

Idempotent: sync upserts by (source_document_id, source_order_index), so
re-running only refreshes/inserts rows.

Usage (inside the backend container):
    docker compose exec backend python scripts/backfill_reminders.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.postgres import AsyncSessionLocal
from app.db.mongodb import document_metadata_collection
from app.models.document import Document
from app.services.reminder_service import sync_document_reminders


async def _load_orders_by_doc(doc_ids: list[str]) -> dict[str, list]:
    if not doc_ids:
        return {}
    orders_by_doc: dict[str, list] = {}
    cursor = document_metadata_collection.find(
        {"document_id": {"$in": doc_ids}},
        {"document_id": 1, "extracted_data.orders": 1},
    )
    async for m in cursor:
        orders = (m.get("extracted_data") or {}).get("orders") or []
        orders_by_doc[m.get("document_id")] = orders
    return orders_by_doc


async def main() -> None:
    async with AsyncSessionLocal() as db:  # type: AsyncSession
        result = await db.execute(
            select(Document).where(
                Document.processing_status == "completed",
                Document.mongodb_metadata_id.isnot(None),
            )
        )
        documents = result.scalars().all()
        print(f"📋 Completed documents: {len(documents)}")

        orders_by_doc = await _load_orders_by_doc([str(d.id) for d in documents])

        synced = 0
        for document in documents:
            orders = orders_by_doc.get(str(document.id)) or []
            await sync_document_reminders(document, orders, db)
            await db.commit()
            if orders:
                synced += 1

        print(f"✅ Done. Synced reminders for {synced} documents with orders.")


if __name__ == "__main__":
    asyncio.run(main())
