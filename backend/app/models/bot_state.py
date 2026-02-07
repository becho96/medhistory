from sqlalchemy import Column, String, BigInteger, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.db.postgres import Base


class TelegramBotState(Base):
    """Stores conversation state for the Telegram bot.
    
    Each Telegram chat_id maps to one row. The 'state' field drives
    the multi-step dialog logic in n8n (e.g. awaiting_email, awaiting_password).
    The 'data' JSONB column holds ephemeral data needed between steps.
    """
    __tablename__ = "telegram_bot_state"

    chat_id = Column(BigInteger, primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    state = Column(String(50), nullable=False, default="idle")
    data = Column(JSONB, default={})
    jwt_token = Column(Text, nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationship
    user = relationship("User", foreign_keys=[user_id])
