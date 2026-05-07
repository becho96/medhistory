"""Tool: search_documents — full-text search over document summaries."""
import json
from bson import ObjectId
from mcp.server.fastmcp import FastMCP

from mcp_server.database import get_pg_pool, get_mongo_db
from mcp_server.tools._user import resolve_user_id

SNIPPET_LEN = 240


def _snippet(summary: str) -> str:
    if not summary:
        return ""
    s = summary.strip()
    return s if len(s) <= SNIPPET_LEN else s[:SNIPPET_LEN].rstrip() + "…"


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    async def search_documents(query: str, limit: int = 20) -> str:
        """
        Lexical full-text search across the patient's document summaries.
        Uses Russian-language stemming. Returns the most relevant documents
        with a short snippet from each summary.

        Args:
            query: Search terms (e.g. "щитовидная железа", "холестерин").
            limit: Maximum number of matching documents to return (default 20).
        """
        pool = await get_pg_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT id, mongodb_metadata_id, document_type, document_date, medical_facility "
                "FROM documents "
                "WHERE user_id = $1::uuid AND processing_status = 'completed' "
                "AND mongodb_metadata_id IS NOT NULL",
                resolve_user_id(),
            )

        meta_index: dict = {}
        object_ids: list = []
        for r in rows:
            meta_id = r["mongodb_metadata_id"]
            try:
                oid = ObjectId(meta_id)
            except Exception:
                continue
            meta_index[str(oid)] = r
            object_ids.append(oid)

        if not object_ids:
            return json.dumps([])

        mongo_db = get_mongo_db()
        cursor = mongo_db.document_metadata.find(
            {"_id": {"$in": object_ids}, "$text": {"$search": query}},
            {"score": {"$meta": "textScore"}, "extracted_data.summary": 1},
        ).sort([("score", {"$meta": "textScore"})]).limit(limit)

        results = []
        async for doc in cursor:
            r = meta_index.get(str(doc["_id"]))
            if not r:
                continue
            summary = (doc.get("extracted_data") or {}).get("summary") or ""
            results.append({
                "document_id": str(r["id"]),
                "type": r["document_type"],
                "date": str(r["document_date"]) if r["document_date"] else None,
                "facility": r["medical_facility"],
                "score": doc.get("score"),
                "snippet": _snippet(summary),
            })

        return json.dumps(results, ensure_ascii=False)
