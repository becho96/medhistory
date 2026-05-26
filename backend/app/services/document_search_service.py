"""Semantic search over document summaries (pgvector cosine + e5 embeddings)."""
import uuid
from typing import List, Optional, TypedDict

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.mongodb import document_metadata_collection
from app.services.embeddings_client import embed_query

SNIPPET_LEN = 240


class SearchHit(TypedDict):
    document_id: str
    score: float
    snippet: str
    document_type: Optional[str]
    document_date: Optional[str]
    medical_facility: Optional[str]


def _snippet(summary: Optional[str]) -> str:
    if not summary:
        return ""
    s = summary.strip()
    return s if len(s) <= SNIPPET_LEN else s[:SNIPPET_LEN].rstrip() + "…"


async def search_documents_semantic(
    user_id: uuid.UUID,
    query: str,
    db: AsyncSession,
    limit: int = 20,
) -> List[SearchHit]:
    """Return top-K documents for the user ranked by cosine similarity
    between the query embedding and each document's stored summary embedding.

    Documents without an embedding (older uploads not yet backfilled, or those
    that failed embedding at upload time) are excluded.
    """
    query_vec = await embed_query(query)

    # pgvector: `<=>` is the cosine *distance* operator (0..2);
    # similarity = 1 - distance, so higher score = better match.
    sql = text(
        """
        SELECT id, document_type, document_date, medical_facility,
               mongodb_metadata_id,
               1 - (embedding <=> CAST(:q AS vector)) AS score
        FROM documents
        WHERE user_id = :uid
          AND processing_status = 'completed'
          AND embedding IS NOT NULL
        ORDER BY embedding <=> CAST(:q AS vector)
        LIMIT :k
        """
    )
    rows = (
        await db.execute(sql, {"q": str(query_vec), "uid": user_id, "k": limit})
    ).mappings().all()

    if not rows:
        return []

    # Batch-fetch summaries from Mongo so we issue one query, not N.
    from bson import ObjectId

    mongo_ids = []
    for r in rows:
        try:
            mongo_ids.append(ObjectId(r["mongodb_metadata_id"]))
        except Exception:
            continue

    summaries: dict[str, str] = {}
    if mongo_ids:
        cursor = document_metadata_collection.find(
            {"_id": {"$in": mongo_ids}},
            {"extracted_data.summary": 1},
        )
        async for doc in cursor:
            summaries[str(doc["_id"])] = (
                (doc.get("extracted_data") or {}).get("summary") or ""
            )

    hits: List[SearchHit] = []
    for r in rows:
        hits.append({
            "document_id": str(r["id"]),
            "score": float(r["score"]),
            "snippet": _snippet(summaries.get(r["mongodb_metadata_id"], "")),
            "document_type": r["document_type"],
            "document_date": r["document_date"].isoformat() if r["document_date"] else None,
            "medical_facility": r["medical_facility"],
        })
    return hits
