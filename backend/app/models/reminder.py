from sqlalchemy import Column, String, Integer, Text, Date, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from app.db.postgres import Base


class Reminder(Base):
    """Разовое напоминание со сроком (повторный приём / направление).

    Единый источник истины. Авто-напоминания материализуются из
    извлечённых назначений документа (ключ upsert — source_document_id +
    source_order_index); ручные создаются пользователем (source_document_id
    is NULL). Авто-закрытие и эскалация срочности считаются на чтении.
    """
    __tablename__ = "reminders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    origin = Column(String(16), nullable=False)  # auto | manual
    kind = Column(String(32), nullable=False)    # follow_up_appointment | referral_research | referral_specialist
    title = Column(String(500), nullable=False)

    # Цели матчинга (зеркалят поля order), для read-time авто-закрытия
    order_type = Column(String(32), nullable=True)
    target_document_type = Column(String(100), nullable=True)
    target_document_subtype = Column(String(100), nullable=True)
    target_research_area = Column(String(100), nullable=True)
    target_specialty = Column(String(100), nullable=True)

    # Источник (только auto)
    source_document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=True)
    source_order_index = Column(Integer, nullable=True)

    # Срок
    due_date = Column(Date, nullable=True)
    due_source = Column(String(16), nullable=True)  # absolute | relative | manual

    # Жизненный цикл
    status = Column(String(16), nullable=False, default="active")  # active | done | dismissed
    status_source = Column(String(16), nullable=False, default="auto")
    resolution = Column(String(32), nullable=True)  # completed_uploaded | completed_manual | not_required | incorrect
    completed_document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    note = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
