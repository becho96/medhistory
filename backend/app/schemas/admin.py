from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime
import uuid


class PromoCodeCreate(BaseModel):
    code: Optional[str] = Field(None, max_length=64, description="If empty, server generates a random code")
    duration_days: int = Field(..., gt=0, le=3650)
    max_activations: int = Field(1, gt=0, le=1_000_000)
    expires_at: Optional[datetime] = None
    comment: Optional[str] = None


class PromoCodeUpdate(BaseModel):
    is_active: Optional[bool] = None
    comment: Optional[str] = None


class PromoCodeOut(BaseModel):
    id: uuid.UUID
    code: str
    duration_days: int
    max_activations: int
    activations_count: int
    expires_at: Optional[datetime] = None
    is_active: bool
    comment: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AdminUserListItem(BaseModel):
    id: uuid.UUID
    email: Optional[str] = None
    full_name: Optional[str] = None
    subscription_tier: Literal["free", "pro"]
    pro_expires_at: Optional[datetime] = None
    is_admin: bool
    is_active: bool
    created_at: datetime
    documents_count: int = 0

    class Config:
        from_attributes = True


class GrantProRequest(BaseModel):
    days: int = Field(..., gt=0, le=3650)


class SetAdminRequest(BaseModel):
    is_admin: bool


class AdminStats(BaseModel):
    total_users: int
    pro_users: int
    active_promocodes: int
    activations_this_month: int
