"""
LangChain tool definitions for the medical AI assistant.

Tools are created as closures via create_tools(), which injects
db, mongo_db, user_id and gender at call time.
"""
import json
import logging
from typing import Optional

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.assistant.data import (
    fetch_lab_results,
    fetch_doctor_visits,
    fetch_studies,
    fetch_interpretations,
    fetch_health_events,
    fetch_analyte_standard,
)

logger = logging.getLogger("medhistory.assistant")


# ─── Input schemas ────────────────────────────────────────────────────────────

class LabResultsInput(BaseModel):
    date_from: Optional[str] = Field(None, description="Начало периода ISO YYYY-MM-DD (включительно)")
    date_to: Optional[str] = Field(None, description="Конец периода ISO YYYY-MM-DD (включительно)")
    analyte_name: Optional[str] = Field(None, description="Название показателя для фильтрации, например 'гемоглобин', 'глюкоза', 'холестерин'")


class DoctorVisitsInput(BaseModel):
    date_from: Optional[str] = Field(None, description="Начало периода ISO YYYY-MM-DD")
    date_to: Optional[str] = Field(None, description="Конец периода ISO YYYY-MM-DD")
    specialty: Optional[str] = Field(None, description="Специальность врача для фильтрации, например 'кардиолог', 'гастроэнтеролог'")


class StudiesInput(BaseModel):
    date_from: Optional[str] = Field(None, description="Начало периода ISO YYYY-MM-DD")
    date_to: Optional[str] = Field(None, description="Конец периода ISO YYYY-MM-DD")
    study_type: Optional[str] = Field(None, description="Тип исследования для фильтрации, например 'ЭКГ', 'УЗИ', 'МРТ', 'ЭЭГ'")


class InterpretationsInput(BaseModel):
    pass


class HealthEventsInput(BaseModel):
    date_from: Optional[str] = Field(None, description="Начало периода ISO YYYY-MM-DD")
    date_to: Optional[str] = Field(None, description="Конец периода ISO YYYY-MM-DD")


class AnalyteReferenceInput(BaseModel):
    analyte_name: str = Field(..., description="Название аналита, например 'гемоглобин', 'глюкоза'")


# ─── Tool factory ─────────────────────────────────────────────────────────────

def create_tools(db: AsyncSession, mongo_db, user_id: str, gender: str | None = None) -> list:
    """
    Create tool instances with injected user context.
    Called once per agent node invocation.
    """

    async def _get_lab_results(
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        analyte_name: Optional[str] = None,
    ) -> str:
        logger.info("[TOOL] get_lab_results | date_from=%s date_to=%s analyte=%s",
                    date_from, date_to, analyte_name)
        results = await fetch_lab_results(
            mongo_db, db, user_id,
            date_from=date_from, date_to=date_to, analyte_name=analyte_name,
        )
        if not results:
            return "Результаты анализов не найдены за указанный период."
        return json.dumps(results, ensure_ascii=False)

    async def _get_doctor_visits(
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        specialty: Optional[str] = None,
    ) -> str:
        logger.info("[TOOL] get_doctor_visits | date_from=%s date_to=%s specialty=%s",
                    date_from, date_to, specialty)
        visits = await fetch_doctor_visits(
            mongo_db, db, user_id,
            date_from=date_from, date_to=date_to, specialty=specialty,
        )
        if not visits:
            return "Посещения врачей не найдены за указанный период."
        return json.dumps(visits, ensure_ascii=False)

    async def _get_studies(
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        study_type: Optional[str] = None,
    ) -> str:
        logger.info("[TOOL] get_studies | date_from=%s date_to=%s study_type=%s",
                    date_from, date_to, study_type)
        studies = await fetch_studies(
            mongo_db, db, user_id,
            date_from=date_from, date_to=date_to, study_type=study_type,
        )
        if not studies:
            return "Инструментальные исследования не найдены за указанный период."
        return json.dumps(studies, ensure_ascii=False)

    async def _get_interpretations() -> str:
        logger.info("[TOOL] get_interpretations")
        interps = await fetch_interpretations(db, user_id)
        if not interps:
            return "Предыдущих интерпретаций анализов не найдено."
        return json.dumps(interps, ensure_ascii=False)

    async def _get_health_events(
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> str:
        logger.info("[TOOL] get_health_events | date_from=%s date_to=%s", date_from, date_to)
        events = await fetch_health_events(
            mongo_db, db, user_id,
            date_from=date_from, date_to=date_to,
        )
        if not events:
            return "Записи о самочувствии не найдены за указанный период."
        return json.dumps(events, ensure_ascii=False)

    async def _get_analyte_reference(analyte_name: str) -> str:
        logger.info("[TOOL] get_analyte_reference | analyte=%s", analyte_name)
        ref = await fetch_analyte_standard(db, analyte_name, gender)
        if not ref:
            return f"Референсные значения для '{analyte_name}' не найдены в базе."
        return json.dumps(ref, ensure_ascii=False)

    return [
        StructuredTool.from_function(
            coroutine=_get_lab_results,
            name="get_lab_results",
            description=(
                "Получить результаты лабораторных анализов пациента. "
                "Используй когда пациент спрашивает про анализы, показатели крови, мочи и т.д. "
                "Можно фильтровать по периоду и названию показателя."
            ),
            args_schema=LabResultsInput,
        ),
        StructuredTool.from_function(
            coroutine=_get_doctor_visits,
            name="get_doctor_visits",
            description=(
                "Получить историю посещений врачей пациента: диагнозы, назначения, выводы специалистов. "
                "Используй для вопросов о диагнозах, визитах, лечении. "
                "Можно фильтровать по периоду и специальности врача."
            ),
            args_schema=DoctorVisitsInput,
        ),
        StructuredTool.from_function(
            coroutine=_get_studies,
            name="get_studies",
            description=(
                "Получить результаты инструментальных исследований и функциональной диагностики: "
                "ЭКГ, УЗИ, МРТ, КТ, рентген, ЭЭГ, спирометрия и др. "
                "Используй когда пациент спрашивает про конкретные исследования. "
                "Можно фильтровать по периоду и типу исследования."
            ),
            args_schema=StudiesInput,
        ),
        StructuredTool.from_function(
            coroutine=_get_interpretations,
            name="get_interpretations",
            description=(
                "Получить предыдущие AI-интерпретации анализов пациента. "
                "Используй когда нужен контекст прошлых автоматических заключений."
            ),
            args_schema=InterpretationsInput,
        ),
        StructuredTool.from_function(
            coroutine=_get_health_events,
            name="get_health_events",
            description=(
                "Получить записи дневника самочувствия пациента: симптомы, жалобы, параметры. "
                "Используй для вопросов о симптомах и субъективном состоянии здоровья."
            ),
            args_schema=HealthEventsInput,
        ),
        StructuredTool.from_function(
            coroutine=_get_analyte_reference,
            name="get_analyte_reference",
            description=(
                "Получить референсные значения (норму) для конкретного лабораторного показателя. "
                "Используй когда нужно уточнить является ли значение нормальным."
            ),
            args_schema=AnalyteReferenceInput,
        ),
    ]
