"""
Recommendation agent: suggests which doctor/specialist the patient should visit.
Handles intent: doctor_recommendation.
"""
import json
import logging
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from app.services.assistant.state import MedicalAssistantState

logger = logging.getLogger("medhistory.assistant")
from app.services.assistant.llm_factory import get_llm

SYSTEM_PROMPT = """\
Ты — медицинский ИИ-ассистент, который помогает пациентам понять, к какому специалисту \
обратиться, исходя из их медицинской истории и текущих показателей.

Правила:
1. Основывай рекомендацию на РЕАЛЬНЫХ данных пациента (анализы, посещения, симптомы).
2. Объясни, ПОЧЕМУ ты рекомендуешь именно этого специалиста.
3. Если есть несколько вариантов — ранжируй по приоритету.
4. Укажи срочность: плановый приём или нужно обратиться скорее.
5. Отвечай на русском языке.
6. Всегда добавляй: "Это рекомендация на основе данных в системе. \
Окончательное решение принимает лечащий врач."
"""


async def recommendation_node(state: MedicalAssistantState) -> dict:
    """Generate a doctor recommendation response."""
    cfg = state.get("model_config") or {}
    llm = get_llm(cfg.get("provider"), cfg.get("model_id"))

    profile = state.get("patient_profile") or {}
    data = state.get("retrieved_data") or {}

    context_parts = []

    if profile:
        context_parts.append(f"Пациент: {profile.get('full_name')}, "
                              f"пол: {profile.get('gender')}, возраст: {profile.get('age')} лет")

    if data.get("lab_results"):
        context_parts.append(f"\nАнализы:\n{json.dumps(data['lab_results'], ensure_ascii=False, indent=2)}")

    if data.get("doctor_visits"):
        context_parts.append(f"\nПосещения врачей:\n{json.dumps(data['doctor_visits'], ensure_ascii=False, indent=2)}")

    if data.get("interpretations"):
        context_parts.append(f"\nИнтерпретации:\n{json.dumps(data['interpretations'], ensure_ascii=False, indent=2)}")

    if data.get("studies"):
        context_parts.append(f"\nИнструментальные исследования и функциональная диагностика:\n"
                              f"{json.dumps(data['studies'], ensure_ascii=False, indent=2)}")

    if data.get("health_events"):
        context_parts.append(f"\nСамочувствие (последние показатели):\n"
                              f"{json.dumps(data['health_events'], ensure_ascii=False, indent=2)}")

    if not any([data.get("lab_results"), data.get("doctor_visits"),
                data.get("interpretations"), data.get("studies")]):
        context_parts.append("\nМедицинских данных в системе не найдено.")

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

    logger.info("[ASSISTANT] recommendation ответ готов | длина=%d символов",
                len(response.content or ""))
    return {
        "messages": [AIMessage(content=response.content)],
        "retrieved_data": {**data, "_agent": "recommendation"},
    }
