"""
Health history agent: summarises diseases, diagnoses, and visit history.
Handles intent: health_history.
"""
import json
import logging
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from app.services.assistant.state import MedicalAssistantState

logger = logging.getLogger("medhistory.assistant")
from app.services.assistant.llm_factory import get_llm

SYSTEM_PROMPT = """\
Ты — медицинский ИИ-ассистент, который помогает пациентам понять их историю болезни. \
Ты суммаризируешь посещения врачей, диагнозы, результаты анализов и интерпретации.

Правила:
1. Опирайся ТОЛЬКО на предоставленные данные — не добавляй диагнозы, которых нет.
2. Структурируй ответ хронологически или по системам организма.
3. Выдели хронические состояния и часто повторяющиеся проблемы.
4. Укажи, когда было последнее посещение специалиста.
5. Отвечай на русском языке, понятно и структурированно.
6. Добавь дисклеймер: "Это обзор данных из системы. Для полной медицинской оценки обратитесь к врачу."
"""


async def health_history_node(state: MedicalAssistantState) -> dict:
    """Generate a health history summary response."""
    cfg = state.get("model_config") or {}
    llm = get_llm(cfg.get("provider"), cfg.get("model_id"))

    profile = state.get("patient_profile") or {}
    data = state.get("retrieved_data") or {}

    context_parts = []

    if profile:
        context_parts.append(f"Пациент: {profile.get('full_name')}, "
                              f"пол: {profile.get('gender')}, возраст: {profile.get('age')} лет")

    visits = data.get("doctor_visits")
    if visits:
        context_parts.append(f"\nПосещения врачей:\n{json.dumps(visits, ensure_ascii=False, indent=2)}")
    else:
        context_parts.append("\nПосещения врачей: данные не найдены.")

    lab_results = data.get("lab_results")
    if lab_results:
        context_parts.append(f"\nРезультаты анализов:\n{json.dumps(lab_results, ensure_ascii=False, indent=2)}")
    else:
        context_parts.append("\nРезультаты анализов: данные не найдены в системе.")

    interps = data.get("interpretations")
    if interps:
        context_parts.append(f"\nПредыдущие интерпретации анализов:\n"
                              f"{json.dumps(interps, ensure_ascii=False, indent=2)}")

    context = "\n".join(context_parts)

    last_user_msg = ""
    for msg in reversed(state["messages"]):
        if hasattr(msg, "type") and msg.type == "human":
            last_user_msg = msg.content
            break

    user_prompt = (
        f"Данные пациента:\n{context}\n\n"
        f"Вопрос пациента: {last_user_msg}"
    )

    response = await llm.ainvoke([
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=user_prompt),
    ])

    logger.info("[ASSISTANT] health_history ответ готов | длина=%d символов | "
                "источников: visits=%d lab=%d interps=%d",
                len(response.content or ""),
                len(visits or []), len(lab_results or []), len(interps or []))
    return {
        "messages": [AIMessage(content=response.content)],
        "retrieved_data": {**data, "_agent": "health_history"},
    }
