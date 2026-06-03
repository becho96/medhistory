"""Tool: search_documents — full-text search over extracted document content."""
import json
import re
from bson import ObjectId
from mcp.server.fastmcp import FastMCP

from mcp_server.database import get_pg_pool, get_mongo_db
from mcp_server.tools._user import resolve_user_id

SNIPPET_LEN = 240


def _snippet(text: str, query: str) -> str:
    if not text:
        return ""
    s = text.strip()
    terms = [t for t in re.split(r"\s+", query.strip().lower()) if len(t) >= 3]
    lower = s.lower()
    for term in terms:
        pos = lower.find(term)
        if pos >= 0:
            start = max(0, pos - 80)
            end = min(len(s), start + SNIPPET_LEN)
            prefix = "…" if start > 0 else ""
            suffix = "…" if end < len(s) else ""
            return prefix + s[start:end].strip() + suffix
    return s if len(s) <= SNIPPET_LEN else s[:SNIPPET_LEN].rstrip() + "…"


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    async def search_documents(query: str, limit: int = 20) -> str:
        """
        Lexical full-text search across the patient's document summaries and
        near-full extracted text when available.
        Uses Russian-language stemming. Returns the most relevant documents
        with a short snippet from the matching extracted content.

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
            {
                "score": {"$meta": "textScore"},
                "extracted_data.summary": 1,
                "extracted_data.full_text": 1,
            },
        ).sort([("score", {"$meta": "textScore"})]).limit(limit)

        results = []
        async for doc in cursor:
            r = meta_index.get(str(doc["_id"]))
            if not r:
                continue
            extracted = doc.get("extracted_data") or {}
            summary = extracted.get("summary") or ""
            full_text = extracted.get("full_text") or ""
            snippet_source = f"{summary}\n\n{full_text}".strip()
            results.append({
                "document_id": str(r["id"]),
                "type": r["document_type"],
                "date": str(r["document_date"]) if r["document_date"] else None,
                "facility": r["medical_facility"],
                "score": doc.get("score"),
                "snippet": _snippet(snippet_source, query),
                "has_full_text": bool(full_text),
            })

        return json.dumps(results, ensure_ascii=False)
