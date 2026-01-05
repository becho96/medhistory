from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime, date
import uuid
from enum import Enum


class RelationType(str, Enum):
    """Типы семейных отношений"""
    PARENT = "parent"           # Родитель
    CHILD = "child"             # Ребенок
    SPOUSE = "spouse"           # Супруг/супруга
    GRANDPARENT = "grandparent" # Бабушка/дедушка
    GRANDCHILD = "grandchild"   # Внук/внучка
    SIBLING = "sibling"         # Брат/сестра
    OTHER = "other"             # Другое


# Human-readable names for relation types (Russian)
RELATION_TYPE_NAMES = {
    RelationType.PARENT: "Родитель",
    RelationType.CHILD: "Ребенок",
    RelationType.SPOUSE: "Супруг/супруга",
    RelationType.GRANDPARENT: "Бабушка/дедушка",
    RelationType.GRANDCHILD: "Внук/внучка",
    RelationType.SIBLING: "Брат/сестра",
    RelationType.OTHER: "Другое",
}


class FamilyMemberBase(BaseModel):
    """Базовая схема для члена семьи"""
    full_name: str = Field(..., min_length=2, max_length=255, description="ФИО члена семьи")
    birth_date: date = Field(..., description="Дата рождения")
    relation_type: RelationType = Field(..., description="Тип отношения")
    custom_relation: Optional[str] = Field(None, max_length=100, description="Пользовательское описание связи")


class FamilyMemberCreate(FamilyMemberBase):
    """Схема для создания нового члена семьи"""
    email: Optional[EmailStr] = Field(None, description="Email (опционально)")


class FamilyMemberUpdate(BaseModel):
    """Схема для обновления члена семьи"""
    full_name: Optional[str] = Field(None, min_length=2, max_length=255)
    birth_date: Optional[date] = None
    relation_type: Optional[RelationType] = None
    custom_relation: Optional[str] = Field(None, max_length=100)


class SetCredentials(BaseModel):
    """Схема для установки учетных данных члену семьи"""
    email: EmailStr = Field(..., description="Email для входа")
    password: str = Field(..., min_length=6, description="Пароль для входа")


class FamilyMemberResponse(BaseModel):
    """Ответ с информацией о члене семьи"""
    id: uuid.UUID
    full_name: str
    birth_date: Optional[date]
    email: Optional[str]
    has_credentials: bool = Field(description="Может ли войти самостоятельно")
    relation_type: RelationType
    relation_type_display: str = Field(description="Отображаемое название связи")
    custom_relation: Optional[str]
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class FamilyMemberWithAccess(FamilyMemberResponse):
    """Член семьи с информацией о доступе (для переключения профилей)"""
    is_owner: bool = Field(description="Является ли текущий пользователь владельцем этого профиля")


class FamilyListResponse(BaseModel):
    """Список членов семьи"""
    members: List[FamilyMemberWithAccess]
    total: int


class InviteExistingUser(BaseModel):
    """Приглашение существующего пользователя в семью"""
    email: EmailStr = Field(..., description="Email существующего пользователя")
    relation_type: RelationType = Field(..., description="Тип отношения")
    custom_relation: Optional[str] = Field(None, max_length=100)


class DetachFromFamily(BaseModel):
    """Запрос на отвязку от семьи"""
    owner_id: uuid.UUID = Field(..., description="ID пользователя, от которого нужно отвязаться")


class FamilyOwnerInfo(BaseModel):
    """Информация о владельце профиля (для тех, кем управляют)"""
    id: uuid.UUID
    full_name: Optional[str]
    email: Optional[str]
    relation_type: RelationType
    relation_type_display: str


class MyFamilyInfo(BaseModel):
    """Полная информация о семейных связях пользователя"""
    managed_by: List[FamilyOwnerInfo] = Field(default_factory=list, description="Кто управляет моим профилем")
    managing: List[FamilyMemberWithAccess] = Field(default_factory=list, description="Кем я управляю")
    can_detach: bool = Field(description="Может ли пользователь отвязаться")

