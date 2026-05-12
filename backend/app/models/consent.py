from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, INET
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.db.postgres import Base


class UserConsent(Base):
    """Time-stamped record of consent granted by a user (152-ФЗ).

    document_version pins the consent to the exact text the user saw —
    it's the sha256 of the legal markdown file at the moment of grant.
    """
    __tablename__ = "user_consents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    consent_type = Column(String, nullable=False)
    document_version = Column(String, nullable=False)
    granted_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    ip_address = Column(INET, nullable=True)
    user_agent = Column(Text, nullable=True)

    user = relationship("User", foreign_keys=[user_id])
