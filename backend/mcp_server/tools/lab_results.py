"""Tools for lab analytes: results, reference ranges, trend, abnormal."""
import json
from typing import Callable, Optional, Tuple
from mcp.server.fastmcp import FastMCP

from app.services.analyte_normalization_service_db import (
    analyte_normalization_service_db as _norm,
)
from mcp_server.database import get_pg_pool, get_mongo_db
from mcp_server.tools._user import resolve_user_id


def _resolve_query_canonical(query: str) -> Optional[str]:
    if not query or not _norm.is_loaded:
        return None
    return _norm.get_canonical_name(query) or _norm.find_canonical_unit_agnostic(query)


def _make_matcher(query: str) -> Tuple[Optional[str], Callable[[Optional[str], Optional[str]], bool]]:
    """Return (resolved_canonical, predicate).

    If the query resolves to a canonical analyte, the predicate is *strict*:
    only lab results that themselves resolve to the same canonical match. This
    avoids false positives like "Свободный тестостерон" matching a query for
    "тестостерон" (they are distinct catalog entries).

    If the query does not resolve, fall back to lower-cased substring on the
    raw test_name — best effort for analytes the catalog does not cover.
    """
    target = _resolve_query_canonical(query)
    query_low = (query or "").lower().strip()

    if target and _norm.is_loaded:
        def matches_strict(test_name: Optional[str], unit: Optional[str]) -> bool:
            cn = _norm.get_canonical_name(test_name or "", unit)
            if cn is None:
                cn = _norm.find_canonical_unit_agnostic(test_name or "")
            return cn == target
        return target, matches_strict

    def matches_substring(test_name: Optional[str], unit: Optional[str]) -> bool:
        return bool(query_low) and query_low in (test_name or "").lower()
    return None, matches_substring


# Hard cap on docs fetched from Postgres in a single call. Caller decides how
# many to actually return after Mongo-side filtering. Set well above any
# realistic per-patient lab-doc count so we don't silently drop history.
_LAB_DOCS_HARD_CAP = 500


async def _fetch_lab_docs(date_from: Optional[str], date_to: Optional[str]):
    """Return list of (mongodb_metadata_id, document_date) for the patient's lab docs,
    newest first, up to _LAB_DOCS_HARD_CAP rows."""
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        conditions = ["user_id = $1::uuid", "document_type = 'Результаты анализа'",
                      "processing_status = 'completed'"]
        params: list = [resolve_user_id()]

        if date_from:
            params.append(date_from)
            conditions.append(f"document_date >= ${len(params)}::date")
        if date_to:
            params.append(date_to)
            conditions.append(f"document_date <= ${len(params)}::date")

        where = " AND ".join(conditions)
        return await conn.fetch(
            f"SELECT mongodb_metadata_id, document_date FROM documents "
            f"WHERE {where} ORDER BY document_date DESC LIMIT ${len(params) + 1}",
            *params, _LAB_DOCS_HARD_CAP,
        )


async def _load_tests_for_doc(meta_id) -> list:
    if not meta_id:
        return []
    from bson import ObjectId
    mongo_db = get_mongo_db()
    try:
        meta = await mongo_db.document_metadata.find_one({"_id": ObjectId(meta_id)})
    except Exception:
        meta = await mongo_db.document_metadata.find_one({"document_id": meta_id})
    if not meta:
        return []
    return meta.get("extracted_data", {}).get("lab_results", []) or []


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    async def get_lab_results(
        analyte_name: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: int = 50,
    ) -> str:
        """
        Retrieve patient lab test results extracted from clinic documents,
        grouped by source document. Returns up to `limit` documents that
        actually contain lab results (newest first).

        Args:
            analyte_name: Optional filter — name of the analyte (e.g. "гемоглобин", "глюкоза").
            date_from: ISO date string "YYYY-MM-DD". Filter results from this date.
            date_to:   ISO date string "YYYY-MM-DD". Filter results up to this date.
            limit: Maximum number of documents WITH RESULTS to return (default 50).
        """
        rows = await _fetch_lab_docs(date_from, date_to)
        if not rows:
            return json.dumps([])

        matches = None
        if analyte_name:
            _, matches = _make_matcher(analyte_name)

        results = []
        for row in rows:
            if len(results) >= limit:
                break
            tests = await _load_tests_for_doc(row["mongodb_metadata_id"])
            if matches is not None:
                tests = [t for t in tests if matches(t.get("test_name"), t.get("unit"))]
            if tests:
                results.append({
                    "document_date": str(row["document_date"]),
                    "tests": tests,
                })

        return json.dumps(results, ensure_ascii=False)

    @mcp.tool()
    async def get_test_trend(
        test_name: str,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> str:
        """
        Return a flat time series for a single lab analyte across all the patient's documents.
        Use this for trend questions like "how has my hemoglobin changed over the past year".

        Matching uses both lower-cased substring AND a synonym catalog (so "HGB",
        "Гемоглобин (HGB)" and "гемоглобин" all collapse to the same canonical name
        when the catalog covers them). The response includes canonical_name when
        resolved — useful for citing the standard term back to the user.

        Args:
            test_name: Analyte name; can be a substring, a known synonym, or canonical.
            date_from: ISO date "YYYY-MM-DD".
            date_to:   ISO date "YYYY-MM-DD".
        """
        rows = await _fetch_lab_docs(date_from, date_to)
        canonical, matches = _make_matcher(test_name)

        series = []
        for row in rows:
            tests = await _load_tests_for_doc(row["mongodb_metadata_id"])
            for t in tests:
                if matches(t.get("test_name"), t.get("unit")):
                    series.append({
                        "date": str(row["document_date"]),
                        "test_name": t.get("test_name"),
                        "value": t.get("value"),
                        "unit": t.get("unit"),
                        "flag": t.get("flag"),
                        "reference_range": t.get("reference_range"),
                    })
        series.sort(key=lambda x: x["date"])
        return json.dumps(
            {"canonical_name": canonical, "query": test_name, "series": series},
            ensure_ascii=False,
        )

    @mcp.tool()
    async def list_abnormal_results(
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> str:
        """
        Return all lab test results flagged as out of range (Low/High/Abnormal).
        Useful for "what is currently abnormal in my results" type questions.

        Args:
            date_from: ISO date "YYYY-MM-DD".
            date_to:   ISO date "YYYY-MM-DD".
        """
        rows = await _fetch_lab_docs(date_from, date_to)
        flagged = []
        for row in rows:
            tests = await _load_tests_for_doc(row["mongodb_metadata_id"])
            for t in tests:
                flag = (t.get("flag") or "").upper()
                if flag in ("L", "H", "A"):
                    flagged.append({
                        "date": str(row["document_date"]),
                        "test_name": t.get("test_name"),
                        "value": t.get("value"),
                        "unit": t.get("unit"),
                        "flag": flag,
                        "reference_range": t.get("reference_range"),
                    })
        flagged.sort(key=lambda x: x["date"], reverse=True)
        return json.dumps(flagged, ensure_ascii=False)

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
        pool = await get_pg_pool()
        async with pool.acquire() as conn:
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

        if not row:
            return json.dumps({"error": f"Analyte '{analyte_name}' not found in standards"})

        def _f(v):
            return float(v) if v is not None else None

        male = (_f(row["reference_male_min"]), _f(row["reference_male_max"]))
        female = (_f(row["reference_female_min"]), _f(row["reference_female_max"]))

        response = {
            "canonical_name": row["canonical_name"],
            "standard_unit": row["standard_unit"],
            "description": row["description"],
            "gender_used": gender,
        }

        if gender == "male":
            response["reference_min"], response["reference_max"] = male
        elif gender == "female":
            response["reference_min"], response["reference_max"] = female
        else:
            # No gender — return both ranges so the caller can pick correctly.
            # Silently defaulting to one sex causes wrong-norm interpretations.
            response["reference_male_min"], response["reference_male_max"] = male
            response["reference_female_min"], response["reference_female_max"] = female
            response["warning"] = (
                "Gender not specified — both male and female reference ranges returned. "
                "Pass gender='male' or 'female' to get a single range."
            )

        return json.dumps(response, ensure_ascii=False)
