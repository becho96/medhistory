from sqlalchemy import Column, String, Boolean, DateTime, Integer, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.db.postgres import Base


class PromoCode(Base):
    __tablename__ = "promo_codes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(64), nullable=False, unique=True, index=True)
    duration_days = Column(Integer, nullable=False)
    max_activations = Column(Integer, nullable=False, default=1)
    activations_count = Column(Integer, nullable=False, default=0)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    comment = Column(Text, nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    activations = relationship("PromoCodeActivation", back_populates="promo_code", cascade="all, delete-orphan")


class PromoCodeActivation(Base):
    __tablename__ = "promo_code_activations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    promo_code_id = Column(UUID(as_uuid=True), ForeignKey("promo_codes.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    activated_at = Column(DateTime(timezone=True), server_default=func.now())
    pro_extended_to = Column(DateTime(timezone=True), nullable=False)

    promo_code = relationship("PromoCode", back_populates="activations")
    user = relationship("User")
