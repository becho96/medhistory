from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import date, datetime
import uuid

ReminderKind = Literal["follow_up_appointment", "referral_research", "referral_specialist"]
ReminderStatus = Literal["active", "done", "dismissed"]
ReminderUrgency = Literal["overdue", "urgent", "soon", "planned", "no_date"]


class ReminderCreate(BaseModel):
    """Ручное создание напоминания пользователем."""
    kind: ReminderKind = "follow_up_appointment"
    title: str = Field(..., min_length=1, max_length=500)
    due_date: Optional[date] = None
    target_specialty: Optional[str] = None
    target_document_type: Optional[str] = None
    note: Optional[str] = None


class ReminderUpdate(BaseModel):
    kind: Optional[ReminderKind] = None
    title: Optional[str] = Field(default=None, min_length=1, max_length=500)
    due_date: Optional[date] = None
    target_specialty: Optional[str] = None
    note: Optional[str] = None


class ReminderRead(BaseModel):
    id: uuid.UUID
    origin: str
    kind: str
    title: str
    due_date: Optional[date] = None
    urgency_level: ReminderUrgency = "no_date"
    days_left: Optional[int] = None
    status: str = "active"

    target_document_type: Optional[str] = None
    target_specialty: Optional[str] = None
    note: Optional[str] = None

    # Источник (для авто-напоминаний)
    source_document_id: Optional[uuid.UUID] = None
    source_document_title: Optional[str] = None
    source_document_date: Optional[date] = None
    source_specialty: Optional[str] = None  # специальность приёма, где назначили
    source_doctor_name: Optional[str] = None  # ФИО врача, назначившего

    # Автозакрытие по подходящему документу (read-time overlay)
    completed_document_id: Optional[uuid.UUID] = None

    created_at: Optional[datetime] = None
