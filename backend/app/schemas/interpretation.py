from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from uuid import UUID


class InterpretationDocumentInfo(BaseModel):
    """Информация о документе в интерпретации"""
    id: UUID
    original_filename: str
    document_date: Optional[datetime] = None
    document_type: Optional[str] = None
    document_subtype: Optional[str] = None


class InterpretationCreate(BaseModel):
    """Схема для создания новой интерпретации"""
    document_ids: List[UUID] = Field(..., min_items=1, description="Список ID документов для анализа")


class InterpretationBase(BaseModel):
    """Базовая схема интерпретации"""
    id: UUID
    user_id: UUID
    status: str
    interpretation_text: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class InterpretationResponse(InterpretationBase):
    """Полная информация об интерпретации"""
    documents: List[InterpretationDocumentInfo] = []

    class Config:
        from_attributes = True


class InterpretationList(BaseModel):
    """Список интерпретаций"""
    total: int
    items: List[InterpretationResponse]

