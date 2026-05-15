from typing import Dict, Optional

from pydantic import BaseModel, EmailStr, Field


class BotRegisterRequest(BaseModel):
    """Seamless account creation from the Telegram bot."""
    telegram_id: int
    full_name: Optional[str] = None
    consents: Dict[str, str] = Field(
        default_factory=dict,
        description="sha256 of each legal document the user accepted, keyed by consent_type",
    )


class BotResolveRequest(BaseModel):
    telegram_id: int


class BotLinkRequest(BaseModel):
    telegram_id: int
    email: EmailStr
    password: str


class BotMiniAppRequest(BaseModel):
    init_data: str = Field(..., description="Raw Telegram WebApp initData query string")


class BotAuthResponse(BaseModel):
    """JWT plus minimal user info returned after a successful bot auth call."""
    access_token: str
    token_type: str = "bearer"
    user_id: str
    full_name: Optional[str] = None
    is_new: bool = False
    subscription_tier: str = "free"
