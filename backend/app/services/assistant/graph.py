"""
LangGraph StateGraph for the medical AI assistant.

Graph topology:
  load_profile → supervisor → (conditional) ──→ data_retrieval → (conditional) → lab_analysis
                                              ↘                              ↘→ health_history
                                               → general_qa                  ↘→ recommendation

All terminal nodes route to END.
"""
import json
import logging
import uuid
from datetime import date
from typing import Literal

from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, END
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.services.assistant.state import MedicalAssistantState
from app.services.assistant.agents.supervisor import supervisor_node
from app.services.assistant.agents.lab_analysis import lab_analysis_node
from app.services.assistant.agents.health_history import health_history_node
from app.services.assistant.agents.recommendation import recommendation_node
from app.services.assistant.agents.general_qa import general_qa_node
from app.models.user import User

logger = logging.getLogger("medhistory.assistant")


# ─── Helper: fetch patient profile ───────────────────────────────────────────

async def _fetch_profile(db: AsyncSession, user_id: str) -> dict:
    result = await db.execute(
        select(User.full_name, User.gender, User.birth_date).where(
            User.id == uuid.UUID(user_id)
        )
    )
    row = result.one_or_none()
    if not row:
        return {}

    age = None
    if row.birth_date:
        today = date.today()
        bd = row.birth_date
        age = today.year - bd.year - ((today.month, today.day) < (bd.month, bd.day))

    return {
        "full_name": row.full_name,
        "gender": row.gender.value if row.gender else None,
        "age": age,
    }


# ─── Helper: fetch lab results from MongoDB ───────────────────────────────────

async def _fetch_lab_results(mongo_db, db: AsyncSession, user_id: str,
                              params: dict, limit: int | None = None) -> list:
    from sqlalchemy import text

    date_from = params.get("date_from")
    date_to   = params.get("date_to")
    analyte   = params.get("analyte_name")

    if limit is None:
        limit = settings.ASSISTANT_LAB_RESULTS_LIMIT

    conditions = ["user_id = :uid", "document_type = 'Результаты анализа'",
                  "processing_status = 'completed'"]
    bind: dict = {"uid": user_id}

    if date_from:
        conditions.append("document_date >= :df")
        bind["df"] = date_from
    if date_to:
        conditions.append("document_date <= :dt")
        bind["dt"] = date_to

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
        if analyte:
            low = analyte.lower()
            tests = [t for t in tests if low in (t.get("test_name") or "").lower()]

        if tests:
            results.append({"date": str(row[1]), "tests": tests})

    return results


async def _fetch_doctor_visits(mongo_db, db: AsyncSession, user_id: str,
                                params: dict, limit: int | None = None) -> list:
    from sqlalchemy import text

    if limit is None:
        limit = settings.ASSISTANT_DOCTOR_VISITS_LIMIT

    date_from = params.get("date_from")
    date_to   = params.get("date_to")

    conditions = ["user_id = :uid", "document_type = 'Прием врача'",
                  "processing_status = 'completed'"]
    bind: dict = {"uid": user_id}

    if date_from:
        conditions.append("document_date >= :df")
        bind["df"] = date_from
    if date_to:
        conditions.append("document_date <= :dt")
        bind["dt"] = date_to

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
        visits.append({
            "date": str(row[1]),
            "facility": row[2],
            "specialty": specialties[0] if specialties else None,
            "summary": extracted.get("summary"),
        })

    return visits


async def _fetch_interpretations(db: AsyncSession, user_id: str, limit: int | None = None) -> list:
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


async def _fetch_studies(mongo_db, db: AsyncSession, user_id: str,
                          params: dict, limit: int | None = None) -> list:
    """Fetch instrumental studies and functional diagnostics."""
    from sqlalchemy import text

    if limit is None:
        limit = settings.ASSISTANT_STUDIES_LIMIT

    date_from = params.get("date_from")
    date_to   = params.get("date_to")

    conditions = [
        "user_id = :uid",
        "document_type IN ('Инструментальное исследование', 'Функциональная диагностика')",
        "processing_status = 'completed'",
    ]
    bind: dict = {"uid": user_id}

    if date_from:
        conditions.append("document_date >= :df")
        bind["df"] = date_from
    if date_to:
        conditions.append("document_date <= :dt")
        bind["dt"] = date_to

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

        studies.append({
            "date": str(row[1]),
            "facility": row[2],
            "type": row[3],
            "summary": summary,
        })

    return studies


async def _fetch_health_events(mongo_db, db: AsyncSession, user_id: str,
                                params: dict, limit: int | None = None) -> list:
    from sqlalchemy import text

    if limit is None:
        limit = settings.ASSISTANT_HEALTH_EVENTS_LIMIT

    date_from = params.get("date_from")
    date_to   = params.get("date_to")

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


# ─── Helper: log retrieved data summary (для отладки) ─────────────────────────

def _log_retrieved_data(intent: str, params: dict, retrieved: dict, user_id: str) -> None:
    """Логирует результат получения данных истории болезни из БД (аналог MCP tools)."""
    lab = retrieved.get("lab_results") or []
    visits = retrieved.get("doctor_visits") or []
    interps = retrieved.get("interpretations") or []
    events = retrieved.get("health_events") or []
    studies = retrieved.get("studies") or []
    analyte = retrieved.get("analyte_standards")

    summary = []
    if lab:
        doc_count = len(lab)
        total_tests = sum(len(r.get("tests", [])) for r in lab)
        summary.append(f"lab_results: {doc_count} документов, {total_tests} тестов")
    else:
        summary.append("lab_results: нет данных")

    if intent in ("health_history", "doctor_recommendation"):
        summary.append(f"doctor_visits: {len(visits)}")
        summary.append(f"interpretations: {len(interps)}")
        summary.append(f"studies: {len(studies)}")
    if intent == "doctor_recommendation":
        summary.append(f"health_events: {len(events)}")
    if analyte:
        summary.append(f"analyte_standards: {analyte.get('canonical_name', '?')}")

    logger.info(
        "[ASSISTANT] Получение данных истории болезни (data_retrieval) | "
        "user_id=%s intent=%s params=%s | %s",
        user_id, intent, params, " | ".join(summary),
    )
    # DEBUG: sample данных (включить при LOG_LEVEL=DEBUG)
    if logger.isEnabledFor(logging.DEBUG):
        sample = {k: (f"<list[{len(v)}]" if isinstance(v, list) else v)
                  for k, v in retrieved.items() if k != "_agent"}
        logger.debug("[ASSISTANT] retrieved_data keys: %s", list(sample.keys()))


# ─── Graph builder ─────────────────────────────────────────────────────────────

def build_graph(db: AsyncSession, mongo_db):
    """
    Build and compile the LangGraph StateGraph.

    Args:
        db:       SQLAlchemy async session (injected from FastAPI).
        mongo_db: Motor async MongoDB database handle.
    """

    # ── Node: load patient profile ────────────────────────────────────────────
    async def load_profile_node(state: MedicalAssistantState) -> dict:
        profile = await _fetch_profile(db, state["user_id"])
        logger.info("[ASSISTANT] Профиль пациента загружен | user_id=%s | %s",
                    state["user_id"], profile)
        return {"patient_profile": profile}

    # ── Node: data retrieval (dispatches by intent) ───────────────────────────
    async def data_retrieval_node(state: MedicalAssistantState) -> dict:
        intent  = state.get("intent", "general_qa")
        params  = state.get("tool_params") or {}
        uid     = state["user_id"]
        profile = state.get("patient_profile") or {}
        gender  = profile.get("gender")

        retrieved: dict = {}

        if intent in ("lab_analysis", "health_trends"):
            # Sequential: asyncpg does not allow concurrent ops on one connection
            retrieved["lab_results"] = await _fetch_lab_results(mongo_db, db, uid, params)
            analyte_std = await _fetch_analyte_standard(db, params.get("analyte_name"), gender)
            if analyte_std:
                retrieved["analyte_standards"] = analyte_std

        elif intent == "health_history":
            retrieved["doctor_visits"]   = await _fetch_doctor_visits(mongo_db, db, uid, params)
            retrieved["interpretations"] = await _fetch_interpretations(db, uid)
            retrieved["lab_results"]     = await _fetch_lab_results(mongo_db, db, uid, params)
            retrieved["studies"]         = await _fetch_studies(mongo_db, db, uid, params)

        elif intent == "doctor_recommendation":
            retrieved["lab_results"]     = await _fetch_lab_results(mongo_db, db, uid, params)
            retrieved["doctor_visits"]   = await _fetch_doctor_visits(mongo_db, db, uid, params)
            retrieved["interpretations"] = await _fetch_interpretations(db, uid)
            retrieved["health_events"]   = await _fetch_health_events(mongo_db, db, uid, params)
            retrieved["studies"]         = await _fetch_studies(mongo_db, db, uid, params)

        # Лог получения данных истории болезни (аналог MCP-источников: documents, lab_results, etc.)
        _log_retrieved_data(intent, params, retrieved, uid)
        return {"retrieved_data": retrieved}

    # ── Conditional: after supervisor ─────────────────────────────────────────
    def route_from_supervisor(state: MedicalAssistantState) -> Literal[
        "data_retrieval", "general_qa"
    ]:
        return "general_qa" if state.get("intent") == "general_qa" else "data_retrieval"

    # ── Conditional: after data retrieval ─────────────────────────────────────
    def route_from_data(state: MedicalAssistantState) -> Literal[
        "lab_analysis", "health_history", "recommendation"
    ]:
        intent = state.get("intent", "lab_analysis")
        if intent in ("lab_analysis", "health_trends"):
            return "lab_analysis"
        if intent == "health_history":
            return "health_history"
        return "recommendation"

    # ── Assemble graph ─────────────────────────────────────────────────────────
    graph = StateGraph(MedicalAssistantState)

    graph.add_node("load_profile",   load_profile_node)
    graph.add_node("supervisor",     supervisor_node)
    graph.add_node("data_retrieval", data_retrieval_node)
    graph.add_node("lab_analysis",   lab_analysis_node)
    graph.add_node("health_history", health_history_node)
    graph.add_node("recommendation", recommendation_node)
    graph.add_node("general_qa",     general_qa_node)

    graph.set_entry_point("load_profile")
    graph.add_edge("load_profile", "supervisor")

    graph.add_conditional_edges("supervisor", route_from_supervisor, {
        "data_retrieval": "data_retrieval",
        "general_qa":     "general_qa",
    })
    graph.add_conditional_edges("data_retrieval", route_from_data, {
        "lab_analysis":  "lab_analysis",
        "health_history": "health_history",
        "recommendation": "recommendation",
    })

    for terminal in ("lab_analysis", "health_history", "recommendation", "general_qa"):
        graph.add_edge(terminal, END)

    return graph.compile()


# ─── Analyte standard helper (needs DB, kept here to avoid circular imports) ──

async def _fetch_analyte_standard(db: AsyncSession, analyte_name: str | None,
                                   gender: str | None) -> dict | None:
    if not analyte_name:
        return None

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
