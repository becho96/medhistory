from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
import uuid


class FeedbackCreate(BaseModel):
    """Payload for user-submitted feedback."""
    message: str = Field(..., min_length=1, max_length=5000)
    url: Optional[str] = Field(None, max_length=2048)
    user_agent: Optional[str] = Field(None, max_length=1024)
    client_meta: Dict[str, Any] = Field(default_factory=dict)


class FeedbackResponse(BaseModel):
    id: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True
