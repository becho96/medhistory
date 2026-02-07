"""
Telegram Bot API endpoints.

These endpoints are called by n8n workflows, NOT by regular users.
Authentication is handled via X-Bot-Secret header (shared secret
between n8n and backend on the internal Docker network).
"""

from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import uuid
import logging

from app.db.postgres import get_db
from app.models.user import User
from app.models.bot_state import TelegramBotState
from app.core.config import settings
from app.core.security import verify_password, create_access_token

logger = logging.getLogger(__name__)

router = APIRouter()


# ===================== Pydantic schemas =====================

class BotStateResponse(BaseModel):
    chat_id: int
    user_id: Optional[str] = None
    state: str
    data: dict
    jwt_token: Optional[str] = None
    updated_at: Optional[datetime] = None


class BotStateUpdate(BaseModel):
    state: Optional[str] = None
    data: Optional[dict] = None
    jwt_token: Optional[str] = None
    user_id: Optional[str] = None


class BotAuthLinkRequest(BaseModel):
    email: str
    password: str
    telegram_id: int
    chat_id: int


class BotAuthLinkResponse(BaseModel):
    success: bool
    jwt_token: Optional[str] = None
    user_id: Optional[str] = None
    full_name: Optional[str] = None
    error: Optional[str] = None


class BotAuthCheckResponse(BaseModel):
    linked: bool
    user_id: Optional[str] = None
    full_name: Optional[str] = None
    jwt_token: Optional[str] = None


# ===================== Bot secret dependency =====================

async def verify_bot_secret(x_bot_secret: str = Header(..., alias="X-Bot-Secret")):
    """Verify the shared secret sent by n8n."""
    if not settings.BOT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Bot secret is not configured"
        )
    if x_bot_secret != settings.BOT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid bot secret"
        )
    return True


# ===================== State endpoints =====================

@router.get("/state/{chat_id}", response_model=BotStateResponse)
async def get_bot_state(
    chat_id: int,
    _: bool = Depends(verify_bot_secret),
    db: AsyncSession = Depends(get_db)
):
    """Get or create conversation state for a Telegram chat."""
    query = select(TelegramBotState).where(TelegramBotState.chat_id == chat_id)
    result = await db.execute(query)
    bot_state = result.scalar_one_or_none()

    if not bot_state:
        # Create new idle state
        bot_state = TelegramBotState(chat_id=chat_id, state="idle", data={})
        db.add(bot_state)
        await db.commit()
        await db.refresh(bot_state)

    return BotStateResponse(
        chat_id=bot_state.chat_id,
        user_id=str(bot_state.user_id) if bot_state.user_id else None,
        state=bot_state.state,
        data=bot_state.data or {},
        jwt_token=bot_state.jwt_token,
        updated_at=bot_state.updated_at,
    )


@router.put("/state/{chat_id}", response_model=BotStateResponse)
async def update_bot_state(
    chat_id: int,
    update: BotStateUpdate,
    _: bool = Depends(verify_bot_secret),
    db: AsyncSession = Depends(get_db)
):
    """Update conversation state for a Telegram chat."""
    query = select(TelegramBotState).where(TelegramBotState.chat_id == chat_id)
    result = await db.execute(query)
    bot_state = result.scalar_one_or_none()

    if not bot_state:
        bot_state = TelegramBotState(chat_id=chat_id, state="idle", data={})
        db.add(bot_state)

    if update.state is not None:
        bot_state.state = update.state
    if update.data is not None:
        bot_state.data = update.data
    if update.jwt_token is not None:
        bot_state.jwt_token = update.jwt_token
    if update.user_id is not None:
        bot_state.user_id = uuid.UUID(update.user_id)

    await db.commit()
    await db.refresh(bot_state)

    return BotStateResponse(
        chat_id=bot_state.chat_id,
        user_id=str(bot_state.user_id) if bot_state.user_id else None,
        state=bot_state.state,
        data=bot_state.data or {},
        jwt_token=bot_state.jwt_token,
        updated_at=bot_state.updated_at,
    )


# ===================== Auth endpoints =====================

@router.post("/auth/link", response_model=BotAuthLinkResponse)
async def link_telegram_account(
    request: BotAuthLinkRequest,
    _: bool = Depends(verify_bot_secret),
    db: AsyncSession = Depends(get_db)
):
    """
    Link a Telegram account to a MedHistory user.
    
    Validates email + password, then:
      - Sets telegram_id on the user
      - Creates a JWT token
      - Saves the token + user_id into telegram_bot_state
    """
    # Find user by email
    query = select(User).where(User.email == request.email)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user or not user.password_hash:
        return BotAuthLinkResponse(success=False, error="Неверный email или пароль")

    if not verify_password(request.password, user.password_hash):
        return BotAuthLinkResponse(success=False, error="Неверный email или пароль")

    if not user.is_active:
        return BotAuthLinkResponse(success=False, error="Аккаунт деактивирован")

    # Check if this telegram_id is already linked to another user
    existing_query = select(User).where(
        User.telegram_id == request.telegram_id,
        User.id != user.id
    )
    existing_result = await db.execute(existing_query)
    existing_user = existing_result.scalar_one_or_none()
    if existing_user:
        return BotAuthLinkResponse(
            success=False,
            error="Этот Telegram-аккаунт уже привязан к другому пользователю"
        )

    # Link telegram_id to user
    user.telegram_id = request.telegram_id
    
    # Create JWT token
    jwt_token = create_access_token(data={"sub": str(user.id)})

    # Update bot state
    state_query = select(TelegramBotState).where(TelegramBotState.chat_id == request.chat_id)
    state_result = await db.execute(state_query)
    bot_state = state_result.scalar_one_or_none()

    if not bot_state:
        bot_state = TelegramBotState(chat_id=request.chat_id)
        db.add(bot_state)

    bot_state.user_id = user.id
    bot_state.jwt_token = jwt_token
    bot_state.state = "idle"
    bot_state.data = {}

    await db.commit()

    logger.info(f"Telegram account {request.telegram_id} linked to user {user.id}")

    return BotAuthLinkResponse(
        success=True,
        jwt_token=jwt_token,
        user_id=str(user.id),
        full_name=user.full_name,
    )


@router.get("/auth/check/{telegram_id}", response_model=BotAuthCheckResponse)
async def check_telegram_link(
    telegram_id: int,
    _: bool = Depends(verify_bot_secret),
    db: AsyncSession = Depends(get_db)
):
    """Check if a Telegram user is linked to a MedHistory account."""
    query = select(User).where(User.telegram_id == telegram_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        return BotAuthCheckResponse(linked=False)

    # Also fetch the stored JWT from bot_state (if any)
    # We look up by user_id since the user may have multiple chat_ids
    state_query = select(TelegramBotState).where(TelegramBotState.user_id == user.id)
    state_result = await db.execute(state_query)
    bot_state = state_result.scalar_one_or_none()

    return BotAuthCheckResponse(
        linked=True,
        user_id=str(user.id),
        full_name=user.full_name,
        jwt_token=bot_state.jwt_token if bot_state else None,
    )
