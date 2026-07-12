"""Transplant genuine AI reading output (full_text / summary / vision
transcriptions) from one environment's demo account to another's, matched by
original filename.

Why: document *reading* runs through OpenRouter/Gemini. When one environment's
OpenRouter key is unavailable (e.g. prod returns 403), its demo documents end
up with empty full_text. Since the local rehearsal produced real Gemini output
(PDF text extraction + handwriting vision transcription + summaries), we export
it and import it onto the target so the demo is fully populated everywhere.

Usage (inside a backend container, cwd /app):
    python -m scripts.demo_seed.repair_fulltext export   # writes out/fulltext_export.json
    python -m scripts.demo_seed.repair_fulltext import    # applies it + recomputes embeddings
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))  # /app

from sqlalchemy import select

from app.db.postgres import AsyncSessionLocal
from app.db.mongodb import document_metadata_collection
from app.models.user import User
from app.models.document import Document
from app.models.family import FamilyRelation

from . import config as C

HERE = Path(__file__).resolve().parent
EXPORT_PATH = HERE / "out" / "fulltext_export.json"

FIELDS = ("full_text", "full_text_source", "summary", "tables")


async def _demo_docs(db):
    res = await db.execute(select(User.id).where(User.email == C.OWNER_EMAIL))
    owner_id = res.scalar_one_or_none()
    if owner_id is None:
        return []
    res = await db.execute(select(FamilyRelation.member_id).where(FamilyRelation.owner_id == owner_id))
    ids = [owner_id, *res.scalars().all()]
    res = await db.execute(select(Document).where(Document.user_id.in_(ids)))
    return list(res.scalars().all())


async def do_export() -> None:
    async with AsyncSessionLocal() as db:
        docs = await _demo_docs(db)
        out: dict[str, dict] = {}
        for d in docs:
            m = await document_metadata_collection.find_one(
                {"document_id": str(d.id)}, {"extracted_data": 1}
            )
            ed = (m or {}).get("extracted_data") or {}
            out[d.original_filename] = {k: ed.get(k) for k in FIELDS}
        EXPORT_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        have_ft = sum(1 for v in out.values() if v.get("full_text"))
        vision = sum(1 for v in out.values() if v.get("full_text_source") == "ai_vision_transcription")
        print(f"Exported {len(out)} docs -> {EXPORT_PATH}")
        print(f"  with full_text: {have_ft} | vision transcriptions: {vision}")


async def do_import() -> None:
    data = json.loads(EXPORT_PATH.read_text(encoding="utf-8"))
    try:
        from app.services.embeddings_client import embed_passages, EmbeddingsError
    except Exception:  # pragma: no cover
        embed_passages = None
        EmbeddingsError = Exception  # type: ignore

    async with AsyncSessionLocal() as db:
        docs = await _demo_docs(db)
        n_updated = n_missing = n_embed = 0
        for d in docs:
            payload = data.get(d.original_filename)
            if not payload or not payload.get("full_text"):
                n_missing += 1
                continue
            set_fields = {f"extracted_data.{k}": payload.get(k) for k in FIELDS
                          if payload.get(k) is not None}
            await document_metadata_collection.update_one(
                {"document_id": str(d.id)}, {"$set": set_fields}
            )
            n_updated += 1
            if embed_passages and payload.get("summary"):
                try:
                    vectors = await embed_passages([payload["summary"]])
                    d.embedding = vectors[0]
                    n_embed += 1
                except Exception as exc:  # noqa: BLE001
                    print(f"  embedding skipped for {d.original_filename[:30]}: {exc}")
        await db.commit()
        print(f"Imported full_text into {n_updated} docs "
              f"(missing/skipped {n_missing}); embeddings recomputed: {n_embed}")


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode == "export":
        asyncio.run(do_export())
    elif mode == "import":
        asyncio.run(do_import())
    else:
        print("usage: python -m scripts.demo_seed.repair_fulltext [export|import]")
        sys.exit(1)


if __name__ == "__main__":
    main()
