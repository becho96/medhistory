from sqlalchemy import Column, String, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from app.db.postgres import Base


class HealthEvent(Base):
    """
    Модель события самочувствия пациента.
    
    PostgreSQL хранит минимум данных для реляционной целостности.
    Все параметры здоровья хранятся в MongoDB для гибкости.
    """
    __tablename__ = "health_events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    event_datetime = Column(DateTime(timezone=True), nullable=False, index=True)
    notes = Column(Text, nullable=True)
    mongodb_id = Column(String(255), nullable=True, index=True)  # ObjectId как строка
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
