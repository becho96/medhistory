"""Tools for retrieving patient documents and extracted document content."""
import json
from typing import Optional
from mcp.server.fastmcp import FastMCP

from app.core.config import settings
from app.services.document_download_token import create_download_token
from mcp_server.database import get_pg_pool, get_mongo_db
from mcp_server.tools._user import resolve_user_id

ORIGINAL_URL_EXPIRES_SECONDS = 300


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    async def get_doctor_visits(
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: int = 20,
    ) -> str:
        """
        Return a list of the patient's doctor visits with AI-generated summaries.

        Args:
            date_from: ISO date "YYYY-MM-DD". Only visits from this date onward.
            date_to:   ISO date "YYYY-MM-DD". Only visits up to this date.
            limit: Maximum number of visits to return.
        """
        pool = await get_pg_pool()
        async with pool.acquire() as conn:
            conditions = ["user_id = $1::uuid", "document_type = 'Прием врача'",
                          "processing_status = 'completed'"]
            params: list = [resolve_user_id()]

            if date_from:
                params.append(date_from)
                conditions.append(f"document_date >= ${len(params)}::date")
            if date_to:
                params.append(date_to)
                conditions.append(f"document_date <= ${len(params)}::date")

            where = " AND ".join(conditions)
            rows = await conn.fetch(
                f"SELECT mongodb_metadata_id, document_date, medical_facility "
                f"FROM documents WHERE {where} "
                f"ORDER BY document_date DESC LIMIT ${len(params) + 1}",
                *params, limit,
            )

        if not rows:
            return json.dumps([])

        mongo_db = get_mongo_db()
        visits = []
        for row in rows:
            meta_id = row["mongodb_metadata_id"]
            meta = {}
            if meta_id:
                from bson import ObjectId
                try:
                    meta = await mongo_db.document_metadata.find_one({"_id": ObjectId(meta_id)}) or {}
                except Exception:
                    meta = await mongo_db.document_metadata.find_one({"document_id": meta_id}) or {}

            extracted = meta.get("extracted_data", {})
            visits.append({
                "date": str(row["document_date"]),
                "facility": row["medical_facility"],
                "specialties": meta.get("classification", {}).get("specialties") or [],
                "summary": extracted.get("summary"),
            })

        return json.dumps(visits, ensure_ascii=False)

    @mcp.tool()
    async def list_documents(
        document_type: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: int = 30,
    ) -> str:
        """
        Return a list of all medical documents uploaded by the patient (metadata only,
        no content). Use get_document_content when you need detailed extracted
        content, get_document_summary for a short summary, or get_document_original
        to retrieve the source file.

        Document types: 'Прием врача', 'Результаты анализа', 'Инструментальное исследование',
        'Функциональная диагностика', 'Другое'.

        Args:
            document_type: Optional filter by document type (use Russian names above).
            date_from: ISO date "YYYY-MM-DD".
            date_to:   ISO date "YYYY-MM-DD".
            limit: Maximum number of documents to return.
        """
        pool = await get_pg_pool()
        async with pool.acquire() as conn:
            conditions = ["user_id = $1::uuid", "processing_status = 'completed'"]
            params: list = [resolve_user_id()]

            if document_type:
                params.append(document_type)
                conditions.append(f"document_type = ${len(params)}")
            if date_from:
                params.append(date_from)
                conditions.append(f"document_date >= ${len(params)}::date")
            if date_to:
                params.append(date_to)
                conditions.append(f"document_date <= ${len(params)}::date")

            where = " AND ".join(conditions)
            rows = await conn.fetch(
                f"SELECT id, original_filename, file_type, file_size, file_url, "
                f"document_type, document_date, medical_facility "
                f"FROM documents WHERE {where} "
                f"ORDER BY document_date DESC LIMIT ${len(params) + 1}",
                *params, limit,
            )

        docs = [
            {
                "document_id": str(r["id"]),
                "filename": r["original_filename"],
                "type": r["document_type"],
                "date": str(r["document_date"]) if r["document_date"] else None,
                "facility": r["medical_facility"],
                "file_type": r["file_type"],
                "file_size": r["file_size"],
                "has_original": bool(r["file_url"]),
            }
            for r in rows
        ]
        return json.dumps(docs, ensure_ascii=False)

    @mcp.tool()
    async def get_document_summary(document_id: str) -> str:
        """
        Return the AI-generated summary of a single document by its ID.
        Use get_document_content instead when clinical details or tables matter.
        Get document IDs from list_documents or search_documents.

        Args:
            document_id: UUID of the document.
        """
        pool = await get_pg_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT mongodb_metadata_id, document_type, document_date, medical_facility "
                "FROM documents WHERE id = $1::uuid AND user_id = $2::uuid",
                document_id, resolve_user_id(),
            )

        if not row:
            return json.dumps({"error": "Document not found"})

        summary = None
        meta_id = row["mongodb_metadata_id"]
        if meta_id:
            from bson import ObjectId
            mongo_db = get_mongo_db()
            try:
                meta = await mongo_db.document_metadata.find_one({"_id": ObjectId(meta_id)}) or {}
            except Exception:
                meta = await mongo_db.document_metadata.find_one({"document_id": meta_id}) or {}
            summary = meta.get("extracted_data", {}).get("summary")

        return json.dumps({
            "document_id": document_id,
            "type": row["document_type"],
            "date": str(row["document_date"]) if row["document_date"] else None,
            "facility": row["medical_facility"],
            "summary": summary,
        }, ensure_ascii=False)

    @mcp.tool()
    async def get_document_content(document_id: str) -> str:
        """
        Return rich extracted content for a single uploaded medical document.

        Use this when a summary is not enough: it returns the AI/system extracted
        near-full text, recognized tables, and structured lab results when
        available. Get document IDs from list_documents or search_documents.

        Args:
            document_id: UUID of the document.
        """
        pool = await get_pg_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT mongodb_metadata_id, document_type, document_date, medical_facility "
                "FROM documents WHERE id = $1::uuid AND user_id = $2::uuid",
                document_id, resolve_user_id(),
            )

        if not row:
            return json.dumps({"error": "Document not found"})

        extracted = {}
        meta_id = row["mongodb_metadata_id"]
        if meta_id:
            from bson import ObjectId
            mongo_db = get_mongo_db()
            try:
                meta = await mongo_db.document_metadata.find_one({"_id": ObjectId(meta_id)}) or {}
            except Exception:
                meta = await mongo_db.document_metadata.find_one({"document_id": meta_id}) or {}
            extracted = meta.get("extracted_data", {}) or {}

        return json.dumps({
            "document_id": document_id,
            "type": row["document_type"],
            "date": str(row["document_date"]) if row["document_date"] else None,
            "facility": row["medical_facility"],
            "summary": extracted.get("summary"),
            "full_text": extracted.get("full_text"),
            "full_text_source": extracted.get("full_text_source"),
            "tables": extracted.get("tables") or [],
            "lab_results": extracted.get("lab_results") or [],
        }, ensure_ascii=False)

    @mcp.tool()
    async def get_document_original(document_id: str) -> str:
        """
        Return a short-lived download URL for the original uploaded source file.
        Get document IDs from list_documents or search_documents.

        Args:
            document_id: UUID of the document.
        """
        user_id = resolve_user_id()
        pool = await get_pg_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT original_filename, file_type, file_size, file_url, "
                "document_type, document_date, medical_facility "
                "FROM documents WHERE id = $1::uuid AND user_id = $2::uuid",
                document_id, user_id,
            )

        if not row:
            return json.dumps({"error": "Document not found"})

        if not row["file_url"]:
            return json.dumps({"error": "Original file is not available"})

        token = create_download_token(
            user_id=user_id,
            document_id=document_id,
            expires_in_seconds=ORIGINAL_URL_EXPIRES_SECONDS,
        )
        download_url = (
            f"{settings.PUBLIC_BASE_URL.rstrip('/')}"
            f"/api/v1/documents/{document_id}/download?token={token}"
        )

        return json.dumps({
            "document_id": document_id,
            "filename": row["original_filename"],
            "file_type": row["file_type"],
            "file_size": row["file_size"],
            "type": row["document_type"],
            "date": str(row["document_date"]) if row["document_date"] else None,
            "facility": row["medical_facility"],
            "download_url": download_url,
            "expires_in_seconds": ORIGINAL_URL_EXPIRES_SECONDS,
        }, ensure_ascii=False)
