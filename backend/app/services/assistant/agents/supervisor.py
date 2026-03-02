"""
Supervisor agent: classifies the user's message intent and extracts query parameters.

Output:
  intent: one of the 5 supported intents
  tool_params: date ranges, analyte names, etc. for data retrieval
"""
import json
import logging
import re
from langchain_core.messages import SystemMessage, HumanMessage

from app.services.assistant.state import MedicalAssistantState
from app.services.assistant.llm_factory import get_llm

logger = logging.getLogger("medhistory.assistant")

SYSTEM_PROMPT = """\
Ты — медицинский триаж-ассистент. Твоя задача: проанализировать сообщение пациента \
и вернуть JSON-объект с классификацией намерения и параметрами запроса.

Возможные intent-ы:
- lab_analysis         — ЛЮБОЙ вопрос об анализах: "мои анализы", "какие анализы", "результаты анализов", "лабораторные показатели", "показатели крови", "какие данные об анализах"
- health_trends        — динамика показателя во времени ("как менялся гемоглобин")
- health_history       — болезни, диагнозы, посещения врача (БЕЗ упоминания анализов)
- doctor_recommendation — рекомендация специалиста/врача
- general_qa           — общий медицинский вопрос, не требующий данных пациента

ВАЖНО: Если пациент спрашивает про "анализы", "результаты", "лабораторные данные", "показатели" — ВСЕГДА используй lab_analysis.

В поле params укажи:
- analyte_name   (если речь об анализе, например "гемоглобин")
- date_from / date_to  (ISO YYYY-MM-DD, если упоминается период)
- specialty      (если упоминается специалист)

Верни ТОЛЬКО валидный JSON. Пример:
{"intent": "lab_analysis", "params": {"analyte_name": "глюкоза", "date_from": "2025-01-01"}}
{"intent": "general_qa",   "params": {}}
"""


async def supervisor_node(state: MedicalAssistantState) -> dict:
    """Classify intent and extract query params from the latest user message."""
    cfg = state.get("model_config") or {}
    llm = get_llm(cfg.get("provider"), cfg.get("model_id"))

    # Use only the latest user message to keep the context focused
    last_user_msg = ""
    for msg in reversed(state["messages"]):
        if hasattr(msg, "type") and msg.type == "human":
            last_user_msg = msg.content
            break

    response = await llm.ainvoke([
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=last_user_msg),
    ])

    raw = response.content.strip()

    # Extract JSON even if the LLM adds markdown fences
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    parsed: dict = {}
    if match:
        try:
            parsed = json.loads(match.group())
        except json.JSONDecodeError:
            pass

    intent = parsed.get("intent", "general_qa")
    tool_params = parsed.get("params", {})

    logger.info("[ASSISTANT] Supervisor классификация | intent=%s | tool_params=%s",
                intent, tool_params)
    return {"intent": intent, "tool_params": tool_params}
