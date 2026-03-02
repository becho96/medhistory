from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.db.postgres import Base


class ChatSession(Base):
    """A conversation thread between a user and the AI assistant."""
    __tablename__ = "chat_sessions"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id        = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
                            nullable=False, index=True)
    title          = Column(String(500), nullable=False, default="Новый чат")
    model_provider = Column(String(50),  nullable=False, default="anthropic")
    model_id       = Column(String(100), nullable=False, default="claude-sonnet-4-6")
    created_at     = Column(DateTime(timezone=True), server_default=func.now())
    updated_at     = Column(DateTime(timezone=True), server_default=func.now(),
                            onupdate=func.now())

    messages = relationship("ChatMessage", back_populates="session",
                            cascade="all, delete-orphan",
                            order_by="ChatMessage.created_at")


class ChatMessage(Base):
    """A single message in a chat session."""
    __tablename__ = "chat_messages"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id", ondelete="CASCADE"),
                        nullable=False, index=True)
    role       = Column(String(20), nullable=False)   # 'user' | 'assistant'
    content    = Column(Text, nullable=False)
    metadata_  = Column("metadata", JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("ChatSession", back_populates="messages")
