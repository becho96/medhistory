"""
Internal endpoints for service-to-service communication.
Used by db-viewer for cache invalidation and the analyte mapping review queue.
"""
import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.db.mongodb import document_metadata_collection
from app.services.analyte_normalization_service_db import analyte_normalization_service_db
from app.services.analyte_resolver import analyte_resolver

logger = logging.getLogger(__name__)

router = APIRouter()


def _invalidate_caches() -> None:
    analyte_normalization_service_db.invalidate_cache()
    analyte_resolver.invalidate()


@router.post("/analytes/reload")
async def reload_analytes_cache():
    """Invalidate the analyte normalization cache (and resolver ref index)."""
    _invalidate_caches()
    return {"status": "ok", "message": "Cache invalidated"}


# ============== Mapping review queue ==============


async def _distinct_lab_pairs() -> list[dict]:
    """All distinct (test_name, unit) across every user's documents, with counts."""
    pipeline = [
        {"$match": {"extracted_data.lab_results": {"$exists": True, "$ne": []}}},
        {"$project": {"extracted_data.lab_results": 1}},
        {"$unwind": "$extracted_data.lab_results"},
        {"$group": {
            "_id": {
                "name": {"$ifNull": ["$extracted_data.lab_results.test_name", ""]},
                "unit": {"$ifNull": ["$extracted_data.lab_results.unit", ""]},
            },
            "count": {"$sum": 1},
        }},
    ]
    rows = []
    async for doc in document_metadata_collection.aggregate(pipeline):
        name = (doc["_id"].get("name") or "").strip()
        if not name:
            continue
        rows.append({"name": name, "unit": (doc["_id"].get("unit") or "").strip(), "count": doc["count"]})
    return rows


@router.post("/analytes/queue/rebuild")
async def rebuild_mapping_queue(
    limit: int = Query(200, description="Max new misses to resolve in one run"),
    db: AsyncSession = Depends(get_db),
):
    """Scan all lab results, enqueue proposals for currently-unmapped (name, unit) pairs.

    Idempotent: pairs that already resolve, or already have a queue row, are skipped
    (occurrences are refreshed). Only genuinely new misses hit the resolver/LLM.
    """
    await analyte_normalization_service_db.load_from_db(db)

    pairs = await _distinct_lab_pairs()
    existing = {
        (r[0], r[1])
        for r in (await db.execute(text(
            "SELECT original_name_lower, unit_lower FROM analyte_mapping_queue"
        ))).fetchall()
    }

    resolved = skipped = queued = failed = 0
    for pair in pairs:
        name, unit, count = pair["name"], pair["unit"], pair["count"]
        if analyte_normalization_service_db.get_canonical_name(name, unit):
            resolved += 1
            continue
        key = (name.lower(), unit.lower())
        if key in existing:
            await db.execute(text(
                "UPDATE analyte_mapping_queue SET occurrences=:c, updated_at=now() "
                "WHERE original_name_lower=:n AND unit_lower=:u"
            ), {"c": count, "n": key[0], "u": key[1]})
            skipped += 1
            continue
        if queued >= limit:
            continue
        try:
            proposal = await analyte_resolver.resolve(db, name, unit)
        except Exception as e:
            logger.warning(f"resolver failed for {name!r} [{unit}]: {type(e).__name__}")
            failed += 1
            continue
        await db.execute(text("""
            INSERT INTO analyte_mapping_queue
                (original_name, original_name_lower, unit, unit_lower, occurrences,
                 candidates, proposed_action, proposed_target, proposed_new_name,
                 proposed_new_category, proposed_new_unit, llm_confidence, llm_reason)
            VALUES
                (:name, :name_l, :unit, :unit_l, :count,
                 CAST(:cands AS jsonb), :action, :target, :new_name,
                 :new_cat, :new_unit, :conf, :reason)
            ON CONFLICT (original_name_lower, unit_lower) DO NOTHING
        """), {
            "name": name, "name_l": key[0], "unit": unit, "unit_l": key[1], "count": count,
            "cands": json.dumps(proposal["candidates"], ensure_ascii=False),
            "action": proposal["action"], "target": proposal.get("target"),
            "new_name": proposal.get("new_name"), "new_cat": proposal.get("new_category"),
            "new_unit": proposal.get("new_std_unit"), "conf": proposal.get("confidence"),
            "reason": proposal.get("reason"),
        })
        existing.add(key)
        queued += 1

    await db.commit()
    return {"status": "ok", "resolved": resolved, "already_queued": skipped,
            "newly_queued": queued, "failed": failed, "total_pairs": len(pairs)}


@router.get("/analytes/queue")
async def list_mapping_queue(
    status: str = Query("pending"),
    db: AsyncSession = Depends(get_db),
):
    """List queue rows for review (default: pending), most frequent first."""
    rows = (await db.execute(text("""
        SELECT id, original_name, unit, occurrences, candidates, proposed_action,
               proposed_target, proposed_new_name, proposed_new_category,
               proposed_new_unit, proposed_coefficient, llm_confidence, llm_reason, status
        FROM analyte_mapping_queue
        WHERE status = :status
        ORDER BY occurrences DESC, original_name
    """), {"status": status})).mappings().all()

    def _row(r):
        d = dict(r)
        d["id"] = str(d["id"])
        cands = d.get("candidates")
        if isinstance(cands, str):
            try:
                d["candidates"] = json.loads(cands)
            except (ValueError, TypeError):
                d["candidates"] = []
        return d

    return {"items": [_row(r) for r in rows]}


class ApproveBody(BaseModel):
    action: str                       # 'map' | 'create'
    target: Optional[str] = None      # canonical name (map)
    new_name: Optional[str] = None
    new_category: Optional[str] = None
    new_std_unit: Optional[str] = None
    coefficient: float = 1.0
    resolved_by: Optional[str] = None


async def _canonical_id(db: AsyncSession, name: str) -> Optional[str]:
    row = (await db.execute(text(
        "SELECT id FROM analyte_standards WHERE canonical_name = :n"
    ), {"n": name})).first()
    return str(row[0]) if row else None


async def _add_synonym(db: AsyncSession, analyte_id: str, synonym: str, unit: str, coef: float) -> None:
    await db.execute(text("""
        INSERT INTO analyte_synonyms
            (id, analyte_id, synonym, synonym_lower, unit, unit_lower, coefficient, source)
        VALUES
            (gen_random_uuid(), :aid, :syn, lower(:syn), :unit, lower(:unit), :coef, 'queue_approved')
        ON CONFLICT (synonym_lower, unit_lower) DO NOTHING
    """), {"aid": analyte_id, "syn": synonym, "unit": unit or "", "coef": coef})


@router.post("/analytes/queue/{item_id}/approve")
async def approve_mapping(item_id: str, body: ApproveBody, db: AsyncSession = Depends(get_db)):
    """Apply a queue item: add a synonym (map) or create a canonical + synonym (create)."""
    row = (await db.execute(text(
        "SELECT original_name, unit FROM analyte_mapping_queue WHERE id = :id AND status = 'pending'"
    ), {"id": item_id})).first()
    if not row:
        raise HTTPException(status_code=404, detail="Queue item not found or already resolved")
    original_name, original_unit = row[0], row[1]

    if body.action == "map":
        if not body.target:
            raise HTTPException(status_code=400, detail="target required for action=map")
        analyte_id = await _canonical_id(db, body.target)
        if not analyte_id:
            raise HTTPException(status_code=400, detail=f"Canonical not found: {body.target}")
        await _add_synonym(db, analyte_id, original_name, original_unit, body.coefficient)

    elif body.action == "create":
        new_name = (body.new_name or "").strip()
        if not new_name:
            raise HTTPException(status_code=400, detail="new_name required for action=create")
        category = body.new_category or "Другие анализы"
        std_unit = body.new_std_unit if body.new_std_unit is not None else (original_unit or "")
        cat_row = (await db.execute(text(
            "SELECT id FROM analyte_categories WHERE name = :n"
        ), {"n": category})).first()
        if not cat_row:
            cat_row = (await db.execute(text(
                "SELECT id FROM analyte_categories WHERE name = 'Другие анализы'"
            ))).first()
        analyte_id = await _canonical_id(db, new_name)
        if not analyte_id:
            await db.execute(text("""
                INSERT INTO analyte_standards (id, category_id, canonical_name, standard_unit)
                VALUES (gen_random_uuid(), :cat, :name, :unit)
            """), {"cat": str(cat_row[0]), "name": new_name, "unit": std_unit})
            analyte_id = await _canonical_id(db, new_name)
        # self-synonym so the canonical resolves by its own name, + the observed variant
        await _add_synonym(db, analyte_id, new_name, std_unit, 1.0)
        await _add_synonym(db, analyte_id, original_name, original_unit, body.coefficient)

    else:
        raise HTTPException(status_code=400, detail="action must be 'map' or 'create'")

    await db.execute(text("""
        UPDATE analyte_mapping_queue
        SET status='approved', resolved_at=now(), resolved_by=:by, updated_at=now()
        WHERE id=:id
    """), {"id": item_id, "by": body.resolved_by})
    await db.commit()
    _invalidate_caches()
    return {"status": "ok", "action": body.action}


@router.post("/analytes/queue/{item_id}/reject")
async def reject_mapping(item_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(text("""
        UPDATE analyte_mapping_queue
        SET status='rejected', resolved_at=now(), updated_at=now()
        WHERE id=:id AND status='pending'
    """), {"id": item_id})
    await db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Queue item not found or already resolved")
    return {"status": "ok"}
