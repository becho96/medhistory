"""Tools: get_doctor_visits, get_documents — clinic visits and uploaded documents."""
import json
from typing import Optional
from mcp.server.fastmcp import FastMCP


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    async def get_doctor_visits(
        user_id: str,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: int = 20,
    ) -> str:
        """
        Return a list of the patient's doctor visits with AI-generated summaries.
        Each visit includes date, medical facility, and the AI summary extracted from the document.

        Args:
            user_id: UUID of the patient.
            date_from: ISO date "YYYY-MM-DD". Only visits from this date onward.
            date_to:   ISO date "YYYY-MM-DD". Only visits up to this date.
            limit: Maximum number of visits to return.
        """
        from mcp_server.database import get_pg_connection, get_mongo_db

        conn = await get_pg_connection()
        try:
            conditions = ["user_id = $1::uuid", "document_type = 'Прием врача'",
                          "processing_status = 'completed'"]
            params: list = [user_id]

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
        finally:
            await conn.close()

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

            extracted = meta.get("extracted_fields", {})
            visits.append({
                "date": str(row["document_date"]),
                "facility": row["medical_facility"],
                "specialty": meta.get("classification", {}).get("specialty"),
                "summary": extracted.get("summary"),
                "diagnosis": extracted.get("diagnosis"),
                "recommendations": extracted.get("recommendations"),
            })

        return json.dumps(visits, ensure_ascii=False)

    @mcp.tool()
    async def get_documents(
        user_id: str,
        document_type: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: int = 30,
    ) -> str:
        """
        Return a list of all medical documents uploaded by the patient.
        Document types: 'Прием врача', 'Результаты анализа', 'Инструментальное исследование',
        'Функциональная диагностика', 'Другое'.

        Args:
            user_id: UUID of the patient.
            document_type: Optional filter by document type (use Russian names above).
            date_from: ISO date "YYYY-MM-DD".
            date_to:   ISO date "YYYY-MM-DD".
            limit: Maximum number of documents to return.
        """
        from mcp_server.database import get_pg_connection

        conn = await get_pg_connection()
        try:
            conditions = ["user_id = $1::uuid", "processing_status = 'completed'"]
            params: list = [user_id]

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
                f"SELECT original_filename, document_type, document_date, medical_facility "
                f"FROM documents WHERE {where} "
                f"ORDER BY document_date DESC LIMIT ${len(params) + 1}",
                *params, limit,
            )
        finally:
            await conn.close()

        docs = [
            {
                "filename": r["original_filename"],
                "type": r["document_type"],
                "date": str(r["document_date"]) if r["document_date"] else None,
                "facility": r["medical_facility"],
            }
            for r in rows
        ]
        return json.dumps(docs, ensure_ascii=False)
