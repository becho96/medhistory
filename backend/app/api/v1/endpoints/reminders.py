from datetime import date, datetime
from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.postgres import get_db
from app.models.user import User
from app.models.reminder import Reminder
from app.schemas.reminder import ReminderCreate, ReminderUpdate, ReminderRead
from app.api.deps import get_current_user, get_profile_user_id
from app.services.reminder_service import list_reminders, get_owned_reminder

router = APIRouter()


class ReminderDismissRequest(BaseModel):
    reason: Optional[str] = "not_required"  # not_required | incorrect


@router.get("/", response_model=List[ReminderRead])
async def get_reminders(
    include_resolved: bool = Query(False),
    current_user: User = Depends(get_current_user),
    profile_user_id: uuid.UUID = Depends(get_profile_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Активные напоминания профиля, отсортированные по срочности."""
    return await list_reminders(
        user_id=profile_user_id,
        db=db,
        today=date.today(),
        include_resolved=include_resolved,
    )


@router.post("/", response_model=ReminderRead, status_code=status.HTTP_201_CREATED)
async def create_reminder(
    body: ReminderCreate,
    current_user: User = Depends(get_current_user),
    profile_user_id: uuid.UUID = Depends(get_profile_user_id),
    db: AsyncSession = Depends(get_db),
):
    reminder = Reminder(
        user_id=profile_user_id,
        origin="manual",
        kind=body.kind,
        title=body.title.strip(),
        target_document_type=body.target_document_type,
        target_specialty=body.target_specialty,
        due_date=body.due_date,
        due_source="manual" if body.due_date else None,
        status="active",
        status_source="manual",
        note=body.note,
    )
    db.add(reminder)
    await db.commit()
    await db.refresh(reminder)
    return _single(reminder, today=date.today())


@router.patch("/{reminder_id}", response_model=ReminderRead)
async def update_reminder(
    reminder_id: uuid.UUID,
    body: ReminderUpdate,
    current_user: User = Depends(get_current_user),
    profile_user_id: uuid.UUID = Depends(get_profile_user_id),
    db: AsyncSession = Depends(get_db),
):
    reminder = await _get_or_404(reminder_id, profile_user_id, db)
    data = body.model_dump(exclude_unset=True)

    if "title" in data and data["title"]:
        reminder.title = data["title"].strip()
    if "kind" in data and data["kind"]:
        reminder.kind = data["kind"]
    if "target_specialty" in data:
        reminder.target_specialty = data["target_specialty"]
    if "note" in data:
        reminder.note = data["note"]
    if "due_date" in data:
        reminder.due_date = data["due_date"]
        reminder.due_source = "manual" if data["due_date"] else None

    await db.commit()
    await db.refresh(reminder)
    return _single(reminder, today=date.today())


@router.post("/{reminder_id}/done", response_model=ReminderRead)
async def complete_reminder(
    reminder_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    profile_user_id: uuid.UUID = Depends(get_profile_user_id),
    db: AsyncSession = Depends(get_db),
):
    reminder = await _get_or_404(reminder_id, profile_user_id, db)
    reminder.status = "done"
    reminder.status_source = "manual"
    reminder.resolution = "completed_manual"
    reminder.completed_at = datetime.utcnow()
    await db.commit()
    await db.refresh(reminder)
    return _single(reminder, today=date.today())


@router.post("/{reminder_id}/dismiss", response_model=ReminderRead)
async def dismiss_reminder(
    reminder_id: uuid.UUID,
    body: ReminderDismissRequest = ReminderDismissRequest(),
    current_user: User = Depends(get_current_user),
    profile_user_id: uuid.UUID = Depends(get_profile_user_id),
    db: AsyncSession = Depends(get_db),
):
    reminder = await _get_or_404(reminder_id, profile_user_id, db)
    reason = body.reason if body.reason in ("not_required", "incorrect") else "not_required"
    reminder.status = "dismissed"
    reminder.status_source = "manual"
    reminder.resolution = reason
    await db.commit()
    await db.refresh(reminder)
    return _single(reminder, today=date.today())


@router.delete("/{reminder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reminder(
    reminder_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    profile_user_id: uuid.UUID = Depends(get_profile_user_id),
    db: AsyncSession = Depends(get_db),
):
    reminder = await _get_or_404(reminder_id, profile_user_id, db)
    if reminder.origin == "manual":
        await db.delete(reminder)
    else:
        # Авто-напоминание не удаляем физически — скрываем как dismissed,
        # чтобы повторный анализ документа не воскресил его.
        reminder.status = "dismissed"
        reminder.status_source = "manual"
        reminder.resolution = "not_required"
    await db.commit()
    return None


async def _get_or_404(reminder_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession) -> Reminder:
    reminder = await get_owned_reminder(reminder_id, user_id, db)
    if not reminder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Напоминание не найдено")
    return reminder


def _single(reminder: Reminder, today: date) -> dict:
    """DTO для одиночного напоминания (без read-time авто-закрытия)."""
    from app.services.reminder_service import classify_urgency
    level, days_left = classify_urgency(reminder.due_date, today)
    return {
        "id": reminder.id,
        "origin": reminder.origin,
        "kind": reminder.kind,
        "title": reminder.title,
        "due_date": reminder.due_date,
        "urgency_level": level,
        "days_left": days_left,
        "status": reminder.status,
        "target_document_type": reminder.target_document_type,
        "target_specialty": reminder.target_specialty,
        "note": reminder.note,
        "source_document_id": reminder.source_document_id,
        "source_document_title": None,
        "source_document_date": None,
        "completed_document_id": reminder.completed_document_id,
        "created_at": reminder.created_at,
    }
