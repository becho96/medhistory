"""
API эндпоинты для работы с событиями самочувствия
"""
from fastapi import APIRouter, Depends, Query, status
from typing import Optional, List
from datetime import datetime
import uuid

from app.api.deps import get_current_user, get_profile_user_id
from app.db.postgres import get_db
from app.db.mongodb import mongodb
from app.models.user import User
from app.schemas.health_event import (
    HealthEventCreate,
    HealthEventUpdate,
    HealthEventResponse,
    HealthEventsListResponse,
    ParameterDefinition
)
from app.services import health_events_service
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.get("/parameters", response_model=List[ParameterDefinition])
async def get_parameters(
    primary_only: bool = Query(False, description="Вернуть только основные параметры")
):
    """
    Получить библиотеку параметров здоровья
    
    Args:
        primary_only: Если True, вернуть только 7 основных параметров
    
    Returns:
        Список определений параметров
    """
    definitions = await health_events_service.get_parameter_definitions(
        mongodb, 
        primary_only=primary_only
    )
    return definitions


@router.post("/", response_model=HealthEventResponse, status_code=status.HTTP_201_CREATED)
async def create_event(
    data: HealthEventCreate,
    current_user: User = Depends(get_current_user),
    profile_user_id: uuid.UUID = Depends(get_profile_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Создать событие самочувствия
    
    Args:
        data: Данные события
        current_user: Текущий пользователь
        profile_user_id: ID профиля (свой или члена семьи)
        db: Сессия БД
    
    Returns:
        Созданное событие с параметрами
    """
    return await health_events_service.create_health_event(
        db, mongodb, profile_user_id, data
    )


@router.get("/", response_model=HealthEventsListResponse)
async def get_events(
    date_from: Optional[datetime] = Query(None, description="Фильтр по дате (от)"),
    date_to: Optional[datetime] = Query(None, description="Фильтр по дате (до)"),
    tags: Optional[List[str]] = Query(None, description="Фильтр по тегам"),
    limit: int = Query(100, le=1000, description="Лимит записей"),
    offset: int = Query(0, ge=0, description="Смещение для пагинации"),
    profile_user_id: uuid.UUID = Depends(get_profile_user_id)
):
    """
    Получить список событий самочувствия
    
    Args:
        date_from: Фильтр по дате (от)
        date_to: Фильтр по дате (до)
        tags: Фильтр по тегам
        limit: Лимит записей
        offset: Смещение для пагинации
        profile_user_id: ID профиля
    
    Returns:
        Список событий с общим количеством
    """
    events, total = await health_events_service.get_health_events(
        mongodb, profile_user_id, date_from, date_to, tags, limit, offset
    )
    
    # Преобразуем в response модели
    event_responses = []
    for event in events:
        event_responses.append(HealthEventResponse(
            id=uuid.UUID(event["event_id"]),
            user_id=uuid.UUID(event["user_id"]),
            event_datetime=event["event_datetime"],
            parameters=event.get("parameters", {}),
            tags=event.get("tags", []),
            notes=None,  # notes хранятся в PostgreSQL, но для списка не обязательны
            created_at=event.get("created_at", datetime.utcnow()),
            updated_at=event.get("updated_at", datetime.utcnow())
        ))
    
    return HealthEventsListResponse(
        total=total,
        events=event_responses
    )


@router.get("/{event_id}", response_model=HealthEventResponse)
async def get_event(
    event_id: uuid.UUID,
    profile_user_id: uuid.UUID = Depends(get_profile_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Получить детали события по ID
    
    Args:
        event_id: ID события
        profile_user_id: ID профиля
        db: Сессия БД
    
    Returns:
        Событие с параметрами
    """
    return await health_events_service.get_health_event_by_id(
        db, mongodb, event_id, profile_user_id
    )


@router.patch("/{event_id}", response_model=HealthEventResponse)
async def update_event(
    event_id: uuid.UUID,
    data: HealthEventUpdate,
    profile_user_id: uuid.UUID = Depends(get_profile_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Обновить событие самочувствия
    
    Args:
        event_id: ID события
        data: Данные для обновления
        profile_user_id: ID профиля
        db: Сессия БД
    
    Returns:
        Обновленное событие
    """
    return await health_events_service.update_health_event(
        db, mongodb, event_id, profile_user_id, data
    )


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(
    event_id: uuid.UUID,
    profile_user_id: uuid.UUID = Depends(get_profile_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Удалить событие самочувствия
    
    Args:
        event_id: ID события
        profile_user_id: ID профиля
        db: Сессия БД
    
    Returns:
        Статус 204 при успешном удалении
    """
    await health_events_service.delete_health_event(
        db, mongodb, event_id, profile_user_id
    )
