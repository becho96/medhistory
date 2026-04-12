"""
LangGraph ReAct agent for the medical AI assistant.

Graph topology:
  load_profile → agent ←──────────┐
                    │              │
              tool_calls?         │
                    │ yes          │
                    ▼             │
                  tools ──────────┘
                    │ no (final response)
                    ▼
                   END
"""
import json
import logging
import uuid
from datetime import date, datetime
from typing import Literal

from langchain_core.messages import SystemMessage, ToolMessage, AIMessage
from langgraph.graph import StateGraph, END
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.services.assistant.state import MedicalAssistantState
from app.services.assistant.llm_factory import get_llm
from app.services.assistant.tools import create_tools
from app.models.user import User

logger = logging.getLogger("medhistory.assistant")


# ─── Patient profile loader ───────────────────────────────────────────────────

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


# ─── System prompt ────────────────────────────────────────────────────────────

def _build_system_prompt(profile: dict) -> str:
    today = datetime.now().strftime("%d %B %Y")

    profile_parts = []
    if profile.get("full_name"):
        profile_parts.append(f"имя: {profile['full_name']}")
    if profile.get("gender"):
        g = "мужской" if profile["gender"] == "male" else "женский"
        profile_parts.append(f"пол: {g}")
    if profile.get("age"):
        profile_parts.append(f"возраст: {profile['age']} лет")

    profile_str = (
        "Пациент: " + ", ".join(profile_parts) + "."
        if profile_parts else ""
    )

    return f"""\
Ты — медицинский ИИ-ассистент сервиса MedHistory. Помогаешь пользователям понять \
их медицинскую историю, интерпретировать анализы и ориентироваться в состоянии здоровья.

Сегодняшняя дата: {today}.
{profile_str}

У тебя есть доступ к медицинским данным пациента через инструменты. \
Используй их когда вопрос требует реальных данных из медкарты:
- Вопросы про анализы, лабораторные показатели → get_lab_results
- Вопросы про посещения врачей, диагнозы → get_doctor_visits
- Вопросы про ЭКГ, УЗИ, МРТ, КТ и другие исследования → get_studies
- Вопросы про самочувствие, симптомы → get_health_events
- Нужны референсные значения для показателя → get_analyte_reference
- Нужен контекст прошлых заключений → get_interpretations

ВАЖНО — работа с датами и инструментами:
- Ты знаешь сегодняшнюю дату. Если пользователь говорит "за последние 2 недели", \
"за прошлый месяц", "в этом году" — самостоятельно вычисли date_from и date_to и сразу вызови инструмент. \
Не задавай уточняющих вопросов про даты.
- Если период не указан — вызывай инструмент без фильтра по датам (вернутся все данные).
- Вызывай инструменты сразу, не спрашивая разрешения.

Правила:
1. Отвечай на русском языке, понятно и без лишнего медицинского жаргона.
2. Не ставь диагнозы и не назначай лечение.
3. При отклонениях от нормы рекомендуй обратиться к врачу.
4. Всегда указывай даты при обсуждении конкретных данных.
5. Не выдумывай данные — если инструмент вернул пустой результат, честно скажи об этом.
6. При интерпретации медицинских данных добавляй: \
"Это не медицинский диагноз. Для точной оценки обратитесь к врачу."\
"""


# ─── Graph builder ────────────────────────────────────────────────────────────

def build_graph(db: AsyncSession, mongo_db):
    """
    Build and compile the LangGraph ReAct StateGraph.

    Args:
        db:       SQLAlchemy async session.
        mongo_db: Motor async MongoDB database handle.
    """

    # ── Node: load patient profile ────────────────────────────────────────────
    async def load_profile_node(state: MedicalAssistantState) -> dict:
        profile = await _fetch_profile(db, state["user_id"])
        logger.info("[ASSISTANT] Профиль загружен | user_id=%s | %s", state["user_id"], profile)
        return {"patient_profile": profile}

    # ── Node: agent (LLM with tools) ──────────────────────────────────────────
    async def agent_node(state: MedicalAssistantState) -> dict:
        profile = state.get("patient_profile") or {}
        cfg = state.get("model_config") or {}
        gender = profile.get("gender")

        tools = create_tools(db, mongo_db, state["user_id"], gender)
        llm = get_llm(cfg.get("provider"), cfg.get("model_id"))
        llm_with_tools = llm.bind_tools(tools)

        system = _build_system_prompt(profile)
        response = await llm_with_tools.ainvoke([
            SystemMessage(content=system),
            *state["messages"],
        ])

        tool_calls = getattr(response, "tool_calls", None) or []
        logger.info(
            "[ASSISTANT] agent | tool_calls=%s",
            [tc["name"] for tc in tool_calls] if tool_calls else "none (final response)",
        )
        return {"messages": [response]}

    # ── Node: tool executor ───────────────────────────────────────────────────
    async def tools_node(state: MedicalAssistantState) -> dict:
        profile = state.get("patient_profile") or {}
        gender = profile.get("gender")

        tools = create_tools(db, mongo_db, state["user_id"], gender)
        tools_by_name = {t.name: t for t in tools}

        last_message = state["messages"][-1]
        tool_messages = []

        for tc in (getattr(last_message, "tool_calls", None) or []):
            tool = tools_by_name.get(tc["name"])
            if not tool:
                result = f"Инструмент '{tc['name']}' не найден."
            else:
                try:
                    result = await tool.ainvoke(tc["args"])
                    logger.info("[TOOL] %s выполнен | результат: %d символов",
                                tc["name"], len(str(result)))
                except Exception as exc:
                    logger.exception("[TOOL] %s ошибка: %s", tc["name"], exc)
                    result = f"Ошибка при выполнении инструмента: {exc}"

            tool_messages.append(ToolMessage(
                content=str(result),
                tool_call_id=tc["id"],
                name=tc["name"],
            ))

        return {"messages": tool_messages}

    # ── Conditional: continue loop or finish ──────────────────────────────────
    def should_continue(state: MedicalAssistantState) -> Literal["tools", "__end__"]:
        last = state["messages"][-1]
        if getattr(last, "tool_calls", None):
            return "tools"
        return END

    # ── Assemble graph ─────────────────────────────────────────────────────────
    graph = StateGraph(MedicalAssistantState)

    graph.add_node("load_profile", load_profile_node)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tools_node)

    graph.set_entry_point("load_profile")
    graph.add_edge("load_profile", "agent")
    graph.add_conditional_edges("agent", should_continue, {
        "tools": "tools",
        END: END,
    })
    graph.add_edge("tools", "agent")

    return graph.compile()
