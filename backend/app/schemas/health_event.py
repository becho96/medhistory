from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid


class ParameterDefinition(BaseModel):
    """Определение параметра здоровья из библиотеки"""
    key: str
    label_ru: str
    type: str  # "number", "scale", "text", "boolean"
    config: Dict[str, Any] = Field(default_factory=dict)
    is_primary: bool
    sort_order: int


class HealthEventCreate(BaseModel):
    """Схема для создания события самочувствия"""
    event_datetime: datetime
    parameters: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    notes: Optional[str] = None
    
    @field_validator('event_datetime')
    @classmethod
    def validate_not_future(cls, v: datetime) -> datetime:
        if v > datetime.now():
            raise ValueError('Дата события не может быть в будущем')
        return v


class HealthEventUpdate(BaseModel):
    """Схема для обновления события самочувствия"""
    event_datetime: Optional[datetime] = None
    parameters: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    notes: Optional[str] = None
    
    @field_validator('event_datetime')
    @classmethod
    def validate_not_future(cls, v: Optional[datetime]) -> Optional[datetime]:
        if v and v > datetime.now():
            raise ValueError('Дата события не может быть в будущем')
        return v


class HealthEventResponse(BaseModel):
    """Схема ответа с данными события самочувствия"""
    id: uuid.UUID
    user_id: uuid.UUID
    event_datetime: datetime
    parameters: Dict[str, Any]
    tags: List[str]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class HealthEventsListResponse(BaseModel):
    """Схема ответа со списком событий"""
    total: int
    events: List[HealthEventResponse]
