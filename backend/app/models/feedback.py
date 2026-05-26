from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid

from app.db.postgres import Base


class Feedback(Base):
    """User-submitted feedback with snapshot of client metadata."""
    __tablename__ = "feedback"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    user_email = Column(String(255), nullable=True)
    message = Column(Text, nullable=False)
    url = Column(Text, nullable=True)
    user_agent = Column(Text, nullable=True)
    client_meta = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
