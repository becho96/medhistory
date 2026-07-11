"""Эндпоинты плана лечения (граф-проекция поверх documents + reminders)."""
from datetime import date
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.postgres import get_db
from app.models.user import User
from app.models.plan_override import PlanOverride
from app.api.deps import get_current_user, get_profile_user_id
from app.schemas.treatment_plan import PlanGraph, PlanOverrideCreate, PlanOverrideOut
from app.services.treatment_plan import build_plan_graph

router = APIRouter()

_ALLOWED_KINDS = {"rename", "merge"}


@router.get("/graph", response_model=PlanGraph)
async def get_plan_graph(
    current_user: User = Depends(get_current_user),
    profile_user_id: uuid.UUID = Depends(get_profile_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Граф плана лечения профиля: эпизоды, узлы и направления между ними."""
    return await build_plan_graph(user_id=profile_user_id, db=db, today=date.today())


@router.post("/overrides", response_model=PlanOverrideOut, status_code=status.HTTP_201_CREATED)
async def create_override(
    body: PlanOverrideCreate,
    current_user: User = Depends(get_current_user),
    profile_user_id: uuid.UUID = Depends(get_profile_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Ручная правка эпизода: rename (имя) или merge (слияние двух эпизодов)."""
    if body.kind not in _ALLOWED_KINDS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Неподдерживаемый тип правки")
    if body.kind == "rename" and not (body.title and body.title.strip()):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Нужно имя эпизода")
    if body.kind == "merge" and not body.other_key:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Нужен второй эпизод для слияния")

    # Переименование одного якоря — идемпотентно: заменяем предыдущее имя.
    if body.kind == "rename":
        await db.execute(
            delete(PlanOverride).where(
                PlanOverride.user_id == profile_user_id,
                PlanOverride.kind == "rename",
                PlanOverride.anchor_key == body.anchor_key,
            )
        )

    override = PlanOverride(
        user_id=profile_user_id,
        kind=body.kind,
        anchor_key=body.anchor_key,
        other_key=body.other_key if body.kind == "merge" else None,
        title=body.title.strip() if body.kind == "rename" and body.title else None,
    )
    db.add(override)
    await db.commit()
    await db.refresh(override)
    return override


@router.delete("/overrides/{override_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_override(
    override_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    profile_user_id: uuid.UUID = Depends(get_profile_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Отмена ручной правки."""
    result = await db.execute(
        select(PlanOverride).where(
            PlanOverride.id == override_id,
            PlanOverride.user_id == profile_user_id,
        )
    )
    override = result.scalar_one_or_none()
    if not override:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Правка не найдена")
    await db.delete(override)
    await db.commit()
    return None
