"""
Database fetch helpers for the AI assistant.

All functions are pure async data accessors — no LLM logic here.
They are called by tool implementations in tools.py.
"""
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings


def _parse_date(value) -> "date | None":
    """Convert ISO string 'YYYY-MM-DD' or date object to date; return None on failure."""
    if value is None:
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except (ValueError, TypeError):
        return None


async def fetch_lab_results(
    mongo_db,
    db: AsyncSession,
    user_id: str,
    date_from: str | None = None,
    date_to: str | None = None,
    analyte_name: str | None = None,
    limit: int | None = None,
) -> list:
    from sqlalchemy import text

    if limit is None:
        limit = settings.ASSISTANT_LAB_RESULTS_LIMIT

    df = _parse_date(date_from)
    dt = _parse_date(date_to)

    conditions = [
        "user_id = :uid",
        "document_type = 'Результаты анализа'",
        "processing_status = 'completed'",
    ]
    bind: dict = {"uid": user_id}

    if df:
        conditions.append("document_date >= :df")
        bind["df"] = df
    if dt:
        conditions.append("document_date <= :dt")
        bind["dt"] = dt

    where = " AND ".join(conditions)
    rows = (await db.execute(
        text(f"SELECT mongodb_metadata_id, document_date FROM documents "
             f"WHERE {where} ORDER BY document_date DESC LIMIT :lim"),
        {**bind, "lim": limit},
    )).fetchall()

    results = []
    for row in rows:
        meta_id = row[0]
        if not meta_id:
            continue
        try:
            from bson import ObjectId
            meta = await mongo_db.document_metadata.find_one({"_id": ObjectId(meta_id)})
        except Exception:
            meta = await mongo_db.document_metadata.find_one({"document_id": meta_id})

        if not meta:
            continue

        tests = meta.get("extracted_data", {}).get("lab_results", [])
        if analyte_name:
            low = analyte_name.lower()
            tests = [t for t in tests if low in (t.get("test_name") or "").lower()]

        if tests:
            results.append({"date": str(row[1]), "tests": tests})

    return results


async def fetch_doctor_visits(
    mongo_db,
    db: AsyncSession,
    user_id: str,
    date_from: str | None = None,
    date_to: str | None = None,
    specialty: str | None = None,
    limit: int | None = None,
) -> list:
    from sqlalchemy import text

    if limit is None:
        limit = settings.ASSISTANT_DOCTOR_VISITS_LIMIT

    df = _parse_date(date_from)
    dt = _parse_date(date_to)

    conditions = [
        "user_id = :uid",
        "document_type = 'Прием врача'",
        "processing_status = 'completed'",
    ]
    bind: dict = {"uid": user_id}

    if df:
        conditions.append("document_date >= :df")
        bind["df"] = df
    if dt:
        conditions.append("document_date <= :dt")
        bind["dt"] = dt

    where = " AND ".join(conditions)
    rows = (await db.execute(
        text(f"SELECT mongodb_metadata_id, document_date, medical_facility "
             f"FROM documents WHERE {where} ORDER BY document_date DESC LIMIT :lim"),
        {**bind, "lim": limit},
    )).fetchall()

    visits = []
    for row in rows:
        meta_id = row[0]
        meta: dict = {}
        if meta_id:
            try:
                from bson import ObjectId
                meta = await mongo_db.document_metadata.find_one({"_id": ObjectId(meta_id)}) or {}
            except Exception:
                meta = await mongo_db.document_metadata.find_one({"document_id": meta_id}) or {}

        classification = meta.get("classification") or {}
        specialties = classification.get("specialties") or []
        extracted = meta.get("extracted_data") or {}

        visit_specialty = specialties[0] if specialties else None
        if specialty and visit_specialty:
            if specialty.lower() not in visit_specialty.lower():
                continue

        visits.append({
            "date": str(row[1]),
            "facility": row[2],
            "specialty": visit_specialty,
            "summary": extracted.get("summary"),
        })

    return visits


async def fetch_studies(
    mongo_db,
    db: AsyncSession,
    user_id: str,
    date_from: str | None = None,
    date_to: str | None = None,
    study_type: str | None = None,
    limit: int | None = None,
) -> list:
    """Fetch instrumental studies and functional diagnostics."""
    from sqlalchemy import text

    if limit is None:
        limit = settings.ASSISTANT_STUDIES_LIMIT

    df = _parse_date(date_from)
    dt = _parse_date(date_to)

    conditions = [
        "user_id = :uid",
        "document_type IN ('Инструментальное исследование', 'Функциональная диагностика')",
        "processing_status = 'completed'",
    ]
    bind: dict = {"uid": user_id}

    if df:
        conditions.append("document_date >= :df")
        bind["df"] = df
    if dt:
        conditions.append("document_date <= :dt")
        bind["dt"] = dt

    where = " AND ".join(conditions)
    rows = (await db.execute(
        text(f"SELECT mongodb_metadata_id, document_date, medical_facility, document_type "
             f"FROM documents WHERE {where} ORDER BY document_date DESC LIMIT :lim"),
        {**bind, "lim": limit},
    )).fetchall()

    studies = []
    for row in rows:
        meta_id = row[0]
        summary = None
        if meta_id:
            try:
                from bson import ObjectId
                meta = await mongo_db.document_metadata.find_one({"_id": ObjectId(meta_id)})
            except Exception:
                meta = await mongo_db.document_metadata.find_one({"document_id": meta_id})
            if meta:
                summary = (meta.get("extracted_data") or {}).get("summary")

        doc_type = row[3]
        if study_type and study_type.lower() not in (summary or "").lower():
            # Also check document type and facility name
            if study_type.lower() not in doc_type.lower() and study_type.lower() not in (row[2] or "").lower():
                pass  # include anyway — LLM will filter by content

        studies.append({
            "date": str(row[1]),
            "facility": row[2],
            "type": doc_type,
            "summary": summary,
        })

    return studies


async def fetch_interpretations(
    db: AsyncSession,
    user_id: str,
    limit: int | None = None,
) -> list:
    from sqlalchemy import text

    if limit is None:
        limit = settings.ASSISTANT_INTERPRETATIONS_LIMIT

    rows = (await db.execute(
        text("SELECT interpretation_text, completed_at, created_at "
             "FROM interpretations WHERE user_id = :uid AND status = 'completed' "
             "ORDER BY created_at DESC LIMIT :lim"),
        {"uid": user_id, "lim": limit},
    )).fetchall()

    return [
        {"date": (r[1] or r[2]).isoformat(), "text": r[0]}
        for r in rows
    ]


async def fetch_health_events(
    mongo_db,
    db: AsyncSession,
    user_id: str,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int | None = None,
) -> list:
    from sqlalchemy import text

    if limit is None:
        limit = settings.ASSISTANT_HEALTH_EVENTS_LIMIT

    conditions = ["user_id = :uid"]
    bind: dict = {"uid": user_id}

    if date_from:
        conditions.append("event_datetime >= :df::timestamptz")
        bind["df"] = date_from
    if date_to:
        conditions.append("event_datetime <= :dt::timestamptz")
        bind["dt"] = date_to

    where = " AND ".join(conditions)
    rows = (await db.execute(
        text(f"SELECT mongodb_id, event_datetime, notes FROM health_events "
             f"WHERE {where} ORDER BY event_datetime DESC LIMIT :lim"),
        {**bind, "lim": limit},
    )).fetchall()

    events = []
    for row in rows:
        mongo_id = row[0]
        parameters: dict = {}
        if mongo_id:
            try:
                from bson import ObjectId
                doc = await mongo_db.health_events.find_one({"_id": ObjectId(mongo_id)})
            except Exception:
                doc = await mongo_db.health_events.find_one({"_id": mongo_id})
            if doc:
                parameters = doc.get("parameters", {})

        events.append({
            "datetime": row[1].isoformat(),
            "notes": row[2],
            "parameters": parameters,
        })

    return events


async def fetch_analyte_standard(
    db: AsyncSession,
    analyte_name: str,
    gender: str | None = None,
) -> dict | None:
    from sqlalchemy import text

    row = (await db.execute(
        text("""
            SELECT s.canonical_name, s.standard_unit, s.description,
                   s.reference_male_min, s.reference_male_max,
                   s.reference_female_min, s.reference_female_max
            FROM analyte_standards s
            LEFT JOIN analyte_synonyms syn ON syn.analyte_id = s.id
            WHERE lower(s.canonical_name) = lower(:name)
               OR lower(syn.synonym)       = lower(:name)
            LIMIT 1
        """),
        {"name": analyte_name},
    )).fetchone()

    if not row:
        return None

    if gender == "male":
        ref_min = float(row[3]) if row[3] else None
        ref_max = float(row[4]) if row[4] else None
    else:
        ref_min = float(row[5]) if row[5] else None
        ref_max = float(row[6]) if row[6] else None

    return {
        "canonical_name": row[0],
        "standard_unit": row[1],
        "description": row[2],
        "reference_min": ref_min,
        "reference_max": ref_max,
    }
