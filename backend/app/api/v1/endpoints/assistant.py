"""
AI Assistant endpoints.

WebSocket: WS /api/v1/assistant/ws
  - JWT auth via ?token=<jwt> query param
  - Client sends: {"message": "...", "session_id": "uuid|null",
                   "model": {"provider": "anthropic", "model_id": "claude-sonnet-4-6"}}
  - Server streams: {"type": "thinking"|"token"|"done"|"error"|"session_created", ...}

REST:
  GET    /api/v1/assistant/sessions               → list user's sessions
  DELETE /api/v1/assistant/sessions/{id}          → delete session
  GET    /api/v1/assistant/sessions/{id}/messages → message history
  GET    /api/v1/assistant/models                 → available models
"""
import json
import logging
import uuid
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, Query
from langchain_core.messages import HumanMessage
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.api.deps import get_current_user, get_db
from app.core.security import decode_access_token
from app.db.mongodb import mongodb
from app.models.user import User
from app.models.chat import ChatSession, ChatMessage
from app.services.assistant.graph import build_graph
from app.services.assistant.llm_factory import AVAILABLE_MODELS, get_llm
from app.core.config import settings

router = APIRouter()
# Временный логер для отладки ассистента (виден в консоли при LOG_LEVEL=DEBUG)
logger = logging.getLogger("medhistory.assistant")


# ─── Auth helper for WebSocket (query-param token) ────────────────────────────

async def _ws_authenticate(token: str, db: AsyncSession) -> Optional[User]:
    payload = decode_access_token(token)
    if not payload:
        return None
    user_id = payload.get("sub")
    if not user_id:
        return None
    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        return None
    return user


# ─── Session helpers ──────────────────────────────────────────────────────────

async def _get_or_create_session(
    db: AsyncSession,
    user_id: uuid.UUID,
    session_id: Optional[str],
    model_provider: str,
    model_id: str,
) -> ChatSession:
    if session_id:
        result = await db.execute(
            select(ChatSession).where(
                ChatSession.id == uuid.UUID(session_id),
                ChatSession.user_id == user_id,
            )
        )
        session = result.scalar_one_or_none()
        if session:
            return session

    session = ChatSession(
        user_id=user_id,
        model_provider=model_provider,
        model_id=model_id,
    )
    db.add(session)
    await db.flush()
    return session


async def _load_history(db: AsyncSession, session_id: uuid.UUID, limit: int) -> list:
    from langchain_core.messages import AIMessage

    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(limit)
    )
    rows = list(reversed(result.scalars().all()))

    messages = []
    for row in rows:
        if row.role == "user":
            messages.append(HumanMessage(content=row.content))
        else:
            messages.append(AIMessage(content=row.content))  # type: ignore[arg-type]
    return messages


async def _save_messages(
    db: AsyncSession,
    session_id: uuid.UUID,
    user_text: str,
    assistant_text: str,
    intent: str,
    model_provider: str,
    model_id: str,
) -> uuid.UUID:
    user_msg = ChatMessage(
        session_id=session_id,
        role="user",
        content=user_text,
        metadata_={},
    )
    db.add(user_msg)

    asst_msg = ChatMessage(
        session_id=session_id,
        role="assistant",
        content=assistant_text,
        metadata_={"intent": intent, "model_provider": model_provider, "model_id": model_id},
    )
    db.add(asst_msg)
    await db.flush()
    return asst_msg.id


async def _auto_title(session: ChatSession, user_text: str, db: AsyncSession) -> None:
    """Generate a short session title with a quick LLM call."""
    try:
        from langchain_core.messages import SystemMessage, HumanMessage as HM
        llm = get_llm(session.model_provider, session.model_id)
        response = await llm.ainvoke([
            SystemMessage(content=(
                "Придумай короткое (до 6 слов) название для чата на основе вопроса. "
                "Верни ТОЛЬКО название, без кавычек и пояснений."
            )),
            HM(content=user_text),
        ])
        session.title = response.content.strip()[:500]
        await db.flush()
    except Exception:
        pass  # non-critical


# ─── WebSocket ────────────────────────────────────────────────────────────────

@router.websocket("/ws")
async def assistant_ws(
    websocket: WebSocket,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    await websocket.accept()

    user = await _ws_authenticate(token, db)
    if not user:
        await websocket.send_json({"type": "error", "detail": "Unauthorized"})
        await websocket.close(code=4001)
        return

    try:
        while True:
            raw = await websocket.receive_text()
            payload = json.loads(raw)

            user_text  = payload.get("message", "").strip()
            session_id = payload.get("session_id")
            model_cfg  = payload.get("model") or {}
            provider   = model_cfg.get("provider") or settings.ASSISTANT_PROVIDER
            model_id   = model_cfg.get("model_id") or settings.ASSISTANT_MODEL

            if not user_text:
                continue

            logger.info(
                "[ASSISTANT] Новое сообщение | user_id=%s session_id=%s | текст: %s",
                user.id, session_id, user_text[:80] + ("..." if len(user_text) > 80 else ""),
            )

            session = await _get_or_create_session(
                db, user.id, session_id, provider, model_id
            )
            is_new = not session_id or str(session.id) != (session_id or "")

            if is_new:
                await websocket.send_json({
                    "type":       "session_created",
                    "session_id": str(session.id),
                })

            history = await _load_history(db, session.id, settings.CHAT_HISTORY_LIMIT)

            graph = build_graph(db, mongodb)

            initial_state: dict = {
                "messages":        history + [HumanMessage(content=user_text)],
                "user_id":         str(user.id),
                "session_id":      str(session.id),
                "model_config":    {"provider": provider, "model_id": model_id},
                "patient_profile": {},
                "intent":          "",
                "tool_params":     {},
                "retrieved_data":  {},
            }

            assistant_text = ""
            intent_used    = "general_qa"
            capture_tokens = False  # Only stream from terminal agents, not supervisor

            await websocket.send_json({"type": "thinking", "agent": "supervisor"})

            async for event in graph.astream_events(initial_state, version="v2"):
                kind = event.get("event")

                if kind == "on_chain_start":
                    agent_name = event.get("name", "")
                    logger.info("[ASSISTANT] Агент запущен: %s", agent_name)
                    if agent_name in ("lab_analysis", "health_history",
                                      "recommendation", "general_qa"):
                        capture_tokens = True
                        await websocket.send_json({"type": "thinking", "agent": agent_name})
                    elif agent_name == "supervisor":
                        capture_tokens = False

                elif kind == "on_chat_model_stream" and capture_tokens:
                    chunk = event.get("data", {}).get("chunk")
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        token_text = chunk.content
                        assistant_text += token_text
                        await websocket.send_json({"type": "token", "content": token_text})

                elif kind == "on_chain_end" and event.get("name") == "supervisor":
                    output = event.get("data", {}).get("output") or {}
                    intent_used = output.get("intent", "general_qa")
                    tool_params = output.get("tool_params") or {}
                    logger.info(
                        "[ASSISTANT] Supervisor → intent=%s | tool_params=%s",
                        intent_used, tool_params,
                    )

            if assistant_text:
                if is_new:
                    await _auto_title(session, user_text, db)

                msg_id = await _save_messages(
                    db, session.id, user_text, assistant_text,
                    intent_used, provider, model_id,
                )
                await db.commit()

                await websocket.send_json({
                    "type":       "done",
                    "message_id": str(msg_id),
                    "intent":     intent_used,
                })

                logger.info(
                    "[ASSISTANT] Ответ готов | intent=%s | длина ответа=%d символов",
                    intent_used, len(assistant_text),
                )

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        try:
            await websocket.send_json({"type": "error", "detail": str(exc)})
        except Exception:
            pass


# ─── REST ─────────────────────────────────────────────────────────────────────

@router.get("/sessions")
async def list_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.user_id == current_user.id)
        .order_by(ChatSession.updated_at.desc())
        .limit(50)
    )
    sessions = result.scalars().all()
    return [
        {
            "id":             str(s.id),
            "title":          s.title,
            "model_provider": s.model_provider,
            "model_id":       s.model_id,
            "created_at":     s.created_at.isoformat(),
            "updated_at":     s.updated_at.isoformat(),
        }
        for s in sessions
    ]


@router.delete("/sessions/{session_id}", status_code=204)
async def delete_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == uuid.UUID(session_id),
            ChatSession.user_id == current_user.id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Session not found")

    await db.execute(
        delete(ChatSession).where(ChatSession.id == uuid.UUID(session_id))
    )
    await db.commit()


@router.get("/sessions/{session_id}/messages")
async def get_session_messages(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == uuid.UUID(session_id),
            ChatSession.user_id == current_user.id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Session not found")

    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == uuid.UUID(session_id))
        .order_by(ChatMessage.created_at.asc())
    )
    messages = result.scalars().all()
    return [
        {
            "id":         str(m.id),
            "role":       m.role,
            "content":    m.content,
            "metadata":   m.metadata_,
            "created_at": m.created_at.isoformat(),
        }
        for m in messages
    ]


@router.get("/models")
async def get_available_models():
    """Return all supported providers and model IDs for the frontend ModelSelector."""
    return AVAILABLE_MODELS
