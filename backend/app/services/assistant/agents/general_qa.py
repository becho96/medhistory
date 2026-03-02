"""
General QA agent: answers general medical questions without patient-specific data.
Handles intent: general_qa.
"""
import logging
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from app.services.assistant.state import MedicalAssistantState

logger = logging.getLogger("medhistory.assistant")
from app.services.assistant.llm_factory import get_llm

SYSTEM_PROMPT = """\
Ты — дружелюбный медицинский ИИ-ассистент. Ты отвечаешь на общие медицинские вопросы, \
объясняешь медицинские термины и помогаешь пациентам лучше понимать свои здоровье.

Правила:
1. Отвечай чётко, понятно и без лишнего жаргона.
2. Не ставь диагнозы и не назначай лечение.
3. При необходимости рекомендуй обратиться к врачу.
4. Если вопрос требует данных пациента (анализов, истории болезни) — \
   попроси уточнить или предложи загрузить документы в сервис.
5. Отвечай на русском языке.
6. В конце ответа добавляй: \
   "Для персонализированной рекомендации на основе ваших данных — \
    загрузите медицинские документы в сервис."
"""


async def general_qa_node(state: MedicalAssistantState) -> dict:
    """Answer a general medical question without patient data retrieval."""
    cfg = state.get("model_config") or {}
    llm = get_llm(cfg.get("provider"), cfg.get("model_id"))

    # Pass the last few messages as conversation context
    messages = state.get("messages", [])
    context_msgs = messages[-10:] if len(messages) > 10 else messages

    response = await llm.ainvoke([
        SystemMessage(content=SYSTEM_PROMPT),
        *context_msgs,
    ])

    logger.info("[ASSISTANT] general_qa ответ готов | длина=%d символов",
                len(response.content or ""))
    return {
        "messages": [AIMessage(content=response.content)],
        "retrieved_data": {"_agent": "general_qa"},
    }
