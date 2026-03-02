"""
Lab analysis agent: answers questions about lab results and health trends.
Handles intents: lab_analysis, health_trends.
"""
import json
import logging
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from app.services.assistant.state import MedicalAssistantState

logger = logging.getLogger("medhistory.assistant")
from app.services.assistant.llm_factory import get_llm

SYSTEM_PROMPT = """\
Ты — медицинский ИИ-ассистент, специализирующийся на интерпретации лабораторных анализов. \
Ты анализируешь реальные данные анализов пациента и объясняешь результаты простым языком.

Правила:
1. Опирайся ТОЛЬКО на предоставленные данные пациента — не придумывай показатели.
2. Всегда указывай даты анализов при обсуждении динамики.
3. Если показатель выходит за пределы нормы — чётко это обозначь.
4. Используй доступные референсные значения для оценки.
5. При выявлении отклонений — рекомендуй проконсультироваться с врачом.
6. Отвечай на русском языке, доступно, без чрезмерного использования медицинских терминов.
7. В конце добавь дисклеймер: "Это не медицинский диагноз. Для точной оценки обратитесь к врачу."
"""


async def lab_analysis_node(state: MedicalAssistantState) -> dict:
    """Generate a lab results analysis response."""
    cfg = state.get("model_config") or {}
    llm = get_llm(cfg.get("provider"), cfg.get("model_id"))

    profile = state.get("patient_profile") or {}
    data = state.get("retrieved_data") or {}
    intent = state.get("intent", "lab_analysis")

    # Build context block from retrieved data
    context_parts = []

    if profile:
        context_parts.append(f"Пациент: {profile.get('full_name')}, "
                              f"пол: {profile.get('gender')}, возраст: {profile.get('age')} лет")

    lab_results = data.get("lab_results")
    if lab_results:
        context_parts.append(f"\nРезультаты анализов:\n{json.dumps(lab_results, ensure_ascii=False, indent=2)}")
    else:
        context_parts.append("\nРезультаты анализов: данные не найдены в системе.")

    analyte_standards = data.get("analyte_standards")
    if analyte_standards:
        context_parts.append(f"\nРеференсные значения:\n{json.dumps(analyte_standards, ensure_ascii=False, indent=2)}")

    context = "\n".join(context_parts)

    # Pull the last user message
    last_user_msg = ""
    for msg in reversed(state["messages"]):
        if hasattr(msg, "type") and msg.type == "human":
            last_user_msg = msg.content
            break

    task_hint = ("Проанализируй динамику показателей во времени." if intent == "health_trends"
                 else "Проанализируй лабораторные показатели пациента.")

    user_prompt = f"{task_hint}\n\nДанные пациента:\n{context}\n\nВопрос пациента: {last_user_msg}"

    response = await llm.ainvoke([
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=user_prompt),
    ])

    logger.info("[ASSISTANT] lab_analysis ответ готов | длина=%d символов",
                len(response.content or ""))
    return {
        "messages": [AIMessage(content=response.content)],
        "retrieved_data": {**data, "_agent": "lab_analysis"},
    }
