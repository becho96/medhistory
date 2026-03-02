"""Tools: get_lab_results, get_analyte_standard — lab test results and reference ranges."""
import json
from typing import Optional
from mcp.server.fastmcp import FastMCP


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    async def get_lab_results(
        user_id: str,
        analyte_name: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: int = 50,
    ) -> str:
        """
        Retrieve patient lab test results extracted from clinic documents.
        Results are stored in MongoDB document_metadata collection.

        Args:
            user_id: UUID of the patient.
            analyte_name: Optional filter — name of the analyte (e.g. "гемоглобин", "глюкоза").
            date_from: ISO date string "YYYY-MM-DD". Filter results from this date.
            date_to:   ISO date string "YYYY-MM-DD". Filter results up to this date.
            limit: Maximum number of documents to scan (default 50).
        """
        from mcp_server.database import get_mongo_db, get_pg_connection

        # Step 1: get list of document IDs belonging to this user (lab result docs)
        conn = await get_pg_connection()
        try:
            conditions = ["user_id = $1::uuid", "document_type = 'Результаты анализа'",
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
                f"SELECT mongodb_metadata_id, document_date FROM documents "
                f"WHERE {where} ORDER BY document_date DESC LIMIT ${ len(params) + 1 }",
                *params, limit,
            )
        finally:
            await conn.close()

        if not rows:
            return json.dumps([])

        # Step 2: fetch rich metadata from MongoDB
        mongo_db = get_mongo_db()
        results = []
        for row in rows:
            meta_id = row["mongodb_metadata_id"]
            if not meta_id:
                continue
            from bson import ObjectId
            try:
                meta = await mongo_db.document_metadata.find_one({"_id": ObjectId(meta_id)})
            except Exception:
                meta = await mongo_db.document_metadata.find_one({"document_id": meta_id})

            if not meta:
                continue

            # Pull lab_results from extracted_data (written by LabAnalysisService)
            extracted = meta.get("extracted_data", {})
            tests = extracted.get("lab_results", [])

            if analyte_name:
                low = analyte_name.lower()
                tests = [t for t in tests if low in (t.get("test_name") or "").lower()]

            if tests:
                results.append({
                    "document_date": str(row["document_date"]),
                    "tests": tests,
                })

        return json.dumps(results, ensure_ascii=False)

    @mcp.tool()
    async def get_analyte_standard(
        analyte_name: str,
        gender: Optional[str] = None,
    ) -> str:
        """
        Look up reference (normal) ranges for a lab analyte from the standards database.
        Use this after get_lab_results to check if a patient's value is within normal range.

        Args:
            analyte_name: Name of the analyte to look up (in Russian or English).
            gender: Patient gender — "male" or "female". Affects reference range selection.
        """
        from mcp_server.database import get_pg_connection

        conn = await get_pg_connection()
        try:
            # Search by synonym first, then by canonical name
            row = await conn.fetchrow(
                """
                SELECT
                    s.canonical_name,
                    s.standard_unit,
                    s.description,
                    s.reference_male_min,
                    s.reference_male_max,
                    s.reference_female_min,
                    s.reference_female_max
                FROM analyte_standards s
                LEFT JOIN analyte_synonyms syn ON syn.analyte_id = s.id
                WHERE lower(s.canonical_name) = lower($1)
                   OR lower(syn.synonym) = lower($1)
                LIMIT 1
                """,
                analyte_name,
            )
        finally:
            await conn.close()

        if not row:
            return json.dumps({"error": f"Analyte '{analyte_name}' not found in standards"})

        if gender == "male":
            ref_min = float(row["reference_male_min"]) if row["reference_male_min"] else None
            ref_max = float(row["reference_male_max"]) if row["reference_male_max"] else None
        else:
            ref_min = float(row["reference_female_min"]) if row["reference_female_min"] else None
            ref_max = float(row["reference_female_max"]) if row["reference_female_max"] else None

        return json.dumps({
            "canonical_name": row["canonical_name"],
            "standard_unit": row["standard_unit"],
            "description": row["description"],
            "reference_min": ref_min,
            "reference_max": ref_max,
            "gender_used": gender,
        }, ensure_ascii=False)
