from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime
import uuid


class SubscriptionInfo(BaseModel):
    tier: Literal["free", "pro"]
    limit: int
    used: int
    remaining: int
    pro_expires_at: Optional[datetime] = None
    billing_owner_id: uuid.UUID
    is_billing_owner: bool


class ActivatePromoCodeRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=64)


class ActivatePromoCodeResponse(BaseModel):
    subscription: SubscriptionInfo
    duration_days: int
    activated_until: datetime
