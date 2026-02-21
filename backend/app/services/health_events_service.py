"""
Сервис для работы с событиями самочувствия
"""
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
import uuid
from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import HTTPException

from app.models.health_event import HealthEvent
from app.schemas.health_event import HealthEventCreate, HealthEventUpdate, HealthEventResponse


async def get_parameter_definitions(
    mongodb: AsyncIOMotorDatabase,
    primary_only: bool = False
) -> List[Dict]:
    """
    Получить библиотеку параметров из MongoDB
    
    Args:
        mongodb: База данных MongoDB
        primary_only: Вернуть только основные параметры (7 шт)
    
    Returns:
        Список определений параметров
    """
    filter_query = {"is_primary": True} if primary_only else {}
    cursor = mongodb.health_parameter_definitions.find(filter_query)
    cursor.sort("sort_order", 1)
    
    definitions = await cursor.to_list(length=100)
    
    # Преобразуем ObjectId в строку для сериализации
    for definition in definitions:
        definition["_id"] = str(definition["_id"])
    
    return definitions


async def validate_parameters(
    parameters: Dict[str, Any],
    definitions: List[Dict]
) -> Dict[str, Any]:
    """
    Валидация параметров по типам из библиотеки
    
    Args:
        parameters: Словарь параметров от пользователя
        definitions: Определения параметров из библиотеки
    
    Returns:
        Валидированный словарь параметров
    
    Raises:
        ValueError: Если валидация не прошла
    """
    validated = {}
    definitions_map = {d["key"]: d for d in definitions}
    
    for key, value in parameters.items():
        if key not in definitions_map:
            # Игнорируем неизвестные параметры
            continue
        
        if value is None:
            # Пропускаем пустые значения
            continue
        
        param_def = definitions_map[key]
        param_type = param_def["type"]
        
        # Валидация по типу
        if param_type == "number":
            if not isinstance(value, (int, float)):
                raise ValueError(f"{key}: ожидается число")
            
            config = param_def.get("config", {})
            if "min" in config and value < config["min"]:
                raise ValueError(f"{key}: значение {value} ниже минимума {config['min']}")
            if "max" in config and value > config["max"]:
                raise ValueError(f"{key}: значение {value} выше максимума {config['max']}")
        
        elif param_type == "scale":
            # Проверка допустимых значений для шкалы с options
            options = param_def.get("config", {}).get("options", [])
            if options:
                valid_values = [opt["value"] for opt in options]
                if value not in valid_values:
                    raise ValueError(f"{key}: недопустимое значение '{value}'. Допустимые: {valid_values}")
            
            # Для scale с min/max (слайдер)
            config = param_def.get("config", {})
            if "min" in config and "max" in config:
                if not isinstance(value, int):
                    raise ValueError(f"{key}: ожидается целое число")
                if value < config["min"] or value > config["max"]:
                    raise ValueError(f"{key}: значение должно быть от {config['min']} до {config['max']}")
        
        elif param_type == "boolean":
            if not isinstance(value, bool):
                raise ValueError(f"{key}: ожидается boolean")
        
        elif param_type == "text":
            if not isinstance(value, str):
                raise ValueError(f"{key}: ожидается строка")
        
        validated[key] = value
    
    return validated


async def create_health_event(
    db: AsyncSession,
    mongodb: AsyncIOMotorDatabase,
    user_id: uuid.UUID,
    data: HealthEventCreate
) -> HealthEventResponse:
    """
    Создание события самочувствия
    
    Args:
        db: Сессия PostgreSQL
        mongodb: База данных MongoDB
        user_id: ID пользователя
        data: Данные для создания события
    
    Returns:
        Созданное событие с параметрами
    """
    # 1. Валидация параметров
    definitions = await get_parameter_definitions(mongodb)
    validated_params = await validate_parameters(data.parameters, definitions)
    
    # 2. Создание в PostgreSQL
    db_event = HealthEvent(
        user_id=user_id,
        event_datetime=data.event_datetime,
        notes=data.notes
    )
    db.add(db_event)
    await db.flush()
    
    # 3. Создание в MongoDB
    mongo_doc = {
        "event_id": str(db_event.id),
        "user_id": str(user_id),
        "event_datetime": data.event_datetime,
        "parameters": validated_params,
        "tags": data.tags,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    result = await mongodb.health_events.insert_one(mongo_doc)
    
    # 4. Обновление ссылки на MongoDB
    db_event.mongodb_id = str(result.inserted_id)
    await db.commit()
    await db.refresh(db_event)
    
    # 5. Возврат полных данных
    return HealthEventResponse(
        id=db_event.id,
        user_id=db_event.user_id,
        event_datetime=db_event.event_datetime,
        parameters=validated_params,
        tags=data.tags,
        notes=db_event.notes,
        created_at=db_event.created_at,
        updated_at=db_event.updated_at
    )


async def get_health_events(
    mongodb: AsyncIOMotorDatabase,
    user_id: uuid.UUID,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    tags: Optional[List[str]] = None,
    limit: int = 100,
    offset: int = 0
) -> Tuple[List[Dict], int]:
    """
    Получение списка событий с данными из MongoDB
    
    Args:
        mongodb: База данных MongoDB
        user_id: ID пользователя
        date_from: Фильтр по дате (от)
        date_to: Фильтр по дате (до)
        tags: Фильтр по тегам
        limit: Лимит записей
        offset: Смещение для пагинации
    
    Returns:
        Tuple (список событий, общее количество)
    """
    # Построение фильтра
    mongo_filter = {"user_id": str(user_id)}
    
    if date_from:
        mongo_filter["event_datetime"] = {"$gte": date_from}
    if date_to:
        mongo_filter.setdefault("event_datetime", {})["$lte"] = date_to
    if tags:
        mongo_filter["tags"] = {"$in": tags}
    
    # Получение из MongoDB
    total = await mongodb.health_events.count_documents(mongo_filter)
    cursor = mongodb.health_events.find(mongo_filter)
    cursor.sort("event_datetime", -1).skip(offset).limit(limit)
    
    events = await cursor.to_list(length=limit)
    
    # Преобразуем ObjectId в строку
    for event in events:
        event["id"] = event["event_id"]
        event["_id"] = str(event["_id"])
    
    return events, total


async def get_health_event_by_id(
    db: AsyncSession,
    mongodb: AsyncIOMotorDatabase,
    event_id: uuid.UUID,
    user_id: uuid.UUID
) -> HealthEventResponse:
    """
    Получение события по ID
    
    Args:
        db: Сессия PostgreSQL
        mongodb: База данных MongoDB
        event_id: ID события
        user_id: ID пользователя (для проверки доступа)
    
    Returns:
        Событие с параметрами
    
    Raises:
        HTTPException: Если событие не найдено или нет доступа
    """
    # Проверка в PostgreSQL
    query = select(HealthEvent).where(
        and_(
            HealthEvent.id == event_id,
            HealthEvent.user_id == user_id
        )
    )
    result = await db.execute(query)
    db_event = result.scalar_one_or_none()
    
    if not db_event:
        raise HTTPException(status_code=404, detail="Событие не найдено")
    
    # Получение данных из MongoDB
    mongo_doc = await mongodb.health_events.find_one({"event_id": str(event_id)})
    
    if not mongo_doc:
        # Если в MongoDB нет данных, возвращаем пустые параметры
        mongo_doc = {"parameters": {}, "tags": []}
    
    return HealthEventResponse(
        id=db_event.id,
        user_id=db_event.user_id,
        event_datetime=db_event.event_datetime,
        parameters=mongo_doc.get("parameters", {}),
        tags=mongo_doc.get("tags", []),
        notes=db_event.notes,
        created_at=db_event.created_at,
        updated_at=db_event.updated_at
    )


async def update_health_event(
    db: AsyncSession,
    mongodb: AsyncIOMotorDatabase,
    event_id: uuid.UUID,
    user_id: uuid.UUID,
    data: HealthEventUpdate
) -> HealthEventResponse:
    """
    Обновление события самочувствия
    
    Args:
        db: Сессия PostgreSQL
        mongodb: База данных MongoDB
        event_id: ID события
        user_id: ID пользователя (для проверки доступа)
        data: Данные для обновления
    
    Returns:
        Обновленное событие
    
    Raises:
        HTTPException: Если событие не найдено или нет доступа
    """
    # Проверка в PostgreSQL
    query = select(HealthEvent).where(
        and_(
            HealthEvent.id == event_id,
            HealthEvent.user_id == user_id
        )
    )
    result = await db.execute(query)
    db_event = result.scalar_one_or_none()
    
    if not db_event:
        raise HTTPException(status_code=404, detail="Событие не найдено")
    
    # Обновление в PostgreSQL
    update_data = data.model_dump(exclude_unset=True)
    
    if "event_datetime" in update_data:
        db_event.event_datetime = update_data["event_datetime"]
    if "notes" in update_data:
        db_event.notes = update_data["notes"]
    
    # Обновление в MongoDB
    mongo_update = {"updated_at": datetime.utcnow()}
    
    if "parameters" in update_data:
        # Валидация параметров
        definitions = await get_parameter_definitions(mongodb)
        validated_params = await validate_parameters(update_data["parameters"], definitions)
        mongo_update["parameters"] = validated_params
    
    if "tags" in update_data:
        mongo_update["tags"] = update_data["tags"]
    
    if "event_datetime" in update_data:
        mongo_update["event_datetime"] = update_data["event_datetime"]
    
    await mongodb.health_events.update_one(
        {"event_id": str(event_id)},
        {"$set": mongo_update}
    )
    
    await db.commit()
    await db.refresh(db_event)
    
    # Получение обновленных данных
    return await get_health_event_by_id(db, mongodb, event_id, user_id)


async def delete_health_event(
    db: AsyncSession,
    mongodb: AsyncIOMotorDatabase,
    event_id: uuid.UUID,
    user_id: uuid.UUID
) -> None:
    """
    Удаление события самочувствия
    
    Args:
        db: Сессия PostgreSQL
        mongodb: База данных MongoDB
        event_id: ID события
        user_id: ID пользователя (для проверки доступа)
    
    Raises:
        HTTPException: Если событие не найдено или нет доступа
    """
    # Проверка в PostgreSQL
    query = select(HealthEvent).where(
        and_(
            HealthEvent.id == event_id,
            HealthEvent.user_id == user_id
        )
    )
    result = await db.execute(query)
    db_event = result.scalar_one_or_none()
    
    if not db_event:
        raise HTTPException(status_code=404, detail="Событие не найдено")
    
    # Удаление из MongoDB
    await mongodb.health_events.delete_one({"event_id": str(event_id)})
    
    # Удаление из PostgreSQL
    await db.delete(db_event)
    await db.commit()
