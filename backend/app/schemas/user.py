from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Literal, Dict
from datetime import datetime, date
import uuid

class UserBase(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None


# Required consent types at registration (152-ФЗ).
# Keys are consent_type, values are sha256 of the legal markdown the user saw.
REQUIRED_CONSENTS = ("terms_and_privacy", "special_category")


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    gender: Optional[Literal["male", "female", "other"]] = None
    consents: Dict[str, str] = Field(
        ...,
        description="Required: {'terms_and_privacy': '<sha256>', 'special_category': '<sha256>'}",
    )

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserUpdate(BaseModel):
    """Схема для обновления данных пользователя"""
    full_name: Optional[str] = None
    birth_date: Optional[date] = None
    gender: Optional[Literal["male", "female", "other"]] = None

class User(UserBase):
    id: uuid.UUID
    is_active: bool
    birth_date: Optional[date] = None
    gender: Optional[Literal["male", "female", "other"]] = None
    has_credentials: bool = True
    subscription_tier: Literal["free", "pro"] = "free"
    pro_expires_at: Optional[datetime] = None
    is_admin: bool = False
    created_at: datetime

    class Config:
        from_attributes = True

class UserWithFamily(User):
    """Пользователь с информацией о количестве членов семьи"""
    family_members_count: int = 0

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    user_id: Optional[str] = None

