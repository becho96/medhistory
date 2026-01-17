from pydantic import BaseModel, EmailStr
from typing import Optional, Literal
from datetime import datetime, date
import uuid

class UserBase(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    gender: Optional[Literal["male", "female", "other"]] = None

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

