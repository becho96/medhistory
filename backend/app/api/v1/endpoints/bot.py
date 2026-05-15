"""Trusted endpoints for the Telegram bot service.

register / resolve / link are called server-to-server by the bot and are
guarded by a shared secret (X-Bot-Secret). miniapp is called from the browser
inside a Telegram Mini App and is instead protected by the initData HMAC
signature, so it deliberately does NOT require the bot secret.
"""
import hmac

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_access_token, verify_password
from app.db.postgres import get_db
from app.models.user import User
from app.schemas.bot import (
    BotAuthResponse,
    BotLinkRequest,
    BotMiniAppRequest,
    BotRegisterRequest,
    BotResolveRequest,
)
from app.schemas.user import REQUIRED_CONSENTS
from app.services.consent_service import record_consents
from app.services.telegram_auth import InitDataError, parse_init_data

router = APIRouter()


async def verify_bot_secret(x_bot_secret: str = Header(..., alias="X-Bot-Secret")) -> None:
    """Guard for server-to-server bot endpoints."""
    if not settings.BOT_SECRET or not hmac.compare_digest(x_bot_secret, settings.BOT_SECRET):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid bot secret")


def _auth_response(user: User, *, is_new: bool) -> BotAuthResponse:
    """Mint a JWT for the user and wrap it in the bot auth response."""
    token = create_access_token(data={"sub": str(user.id)})
    return BotAuthResponse(
        access_token=token,
        user_id=str(user.id),
        full_name=user.full_name,
        is_new=is_new,
        subscription_tier=user.subscription_tier,
    )


@router.post(
    "/auth/register",
    response_model=BotAuthResponse,
    dependencies=[Depends(verify_bot_secret)],
)
async def bot_register(payload: BotRegisterRequest, db: AsyncSession = Depends(get_db)):
    """Seamlessly create an account for a Telegram user.

    The account is credential-less (no email/password, like a family member)
    and identified by telegram_id. 152-ФЗ consents are mandatory and stored
    exactly as for web registration.
    """
    missing = [c for c in REQUIRED_CONSENTS if c not in payload.consents]
    if missing:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f"Missing required consents: {', '.join(missing)}",
        )

    existing = await db.execute(
        select(User).where(User.telegram_id == payload.telegram_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Telegram account already registered",
        )

    user = User(full_name=payload.full_name, telegram_id=payload.telegram_id)
    db.add(user)
    await db.flush()  # populate user.id before consent rows

    # Record every consent sent (REQUIRED_CONSENTS plus any future type such
    # as telegram_cross_border). No real IP/User-Agent exists over Telegram.
    record_consents(
        db, user, payload.consents,
        ip_address=None, user_agent="telegram-bot",
    )

    await db.commit()
    await db.refresh(user)
    return _auth_response(user, is_new=True)


@router.post(
    "/auth/resolve",
    response_model=BotAuthResponse,
    dependencies=[Depends(verify_bot_secret)],
)
async def bot_resolve(payload: BotResolveRequest, db: AsyncSession = Depends(get_db)):
    """Return a fresh JWT for an already-linked Telegram user."""
    result = await db.execute(
        select(User).where(User.telegram_id == payload.telegram_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Telegram account not linked")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="User account is inactive")
    return _auth_response(user, is_new=False)


@router.post(
    "/auth/link",
    response_model=BotAuthResponse,
    dependencies=[Depends(verify_bot_secret)],
)
async def bot_link(payload: BotLinkRequest, db: AsyncSession = Depends(get_db)):
    """Link a Telegram user to an existing email/password account."""
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    if not user or not user.password_hash or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="User account is inactive")

    taken = await db.execute(
        select(User).where(
            User.telegram_id == payload.telegram_id,
            User.id != user.id,
        )
    )
    if taken.scalar_one_or_none():
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="This Telegram account is already linked to another user",
        )

    user.telegram_id = payload.telegram_id
    await db.commit()
    await db.refresh(user)
    return _auth_response(user, is_new=False)


@router.post("/auth/miniapp", response_model=BotAuthResponse)
async def bot_miniapp(payload: BotMiniAppRequest, db: AsyncSession = Depends(get_db)):
    """Exchange validated Telegram Mini App initData for a JWT.

    Protected by the initData HMAC signature (not X-Bot-Secret) because it is
    called from the browser inside Telegram.
    """
    try:
        fields = parse_init_data(payload.init_data, settings.TELEGRAM_BOT_TOKEN)
    except InitDataError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail=str(exc))

    telegram_id = fields.get("user", {}).get("id")
    if not telegram_id:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="initData has no user id")

    result = await db.execute(select(User).where(User.telegram_id == int(telegram_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Telegram account not linked")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="User account is inactive")
    return _auth_response(user, is_new=False)
