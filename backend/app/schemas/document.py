from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime, date
import uuid

class DocumentBase(BaseModel):
    original_filename: str
    file_size: int
    file_type: str

class DocumentCreate(DocumentBase):
    pass

class DocumentMetadata(BaseModel):
    """Complete metadata returned by AI - includes both PostgreSQL and MongoDB fields"""
    # PostgreSQL fields
    document_type: str  # Required - one of 5 types
    document_date: Optional[date] = None
    patient_name: Optional[str] = None
    medical_facility: Optional[str] = None
    
    # MongoDB classification fields
    document_subtype: Optional[str] = None  # Required for some types
    research_area: Optional[str] = None  # Only for "Инструментальное исследование"
    specialties: Optional[list[str]] = None  # Required for "Прием врача", null for others
    document_language: Optional[str] = "ru"
    confidence: Optional[float] = None
    
    # MongoDB extracted_data fields
    summary: Optional[str] = None

class Document(DocumentBase):
    id: uuid.UUID
    user_id: uuid.UUID
    file_url: str
    document_type: Optional[str] = None
    document_date: Optional[date] = None
    patient_name: Optional[str] = None
    medical_facility: Optional[str] = None
    processing_status: str
    mongodb_metadata_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class DocumentWithMetadata(Document):
    """Document with MongoDB metadata fields for frontend display"""
    specialty: Optional[str] = None  # Joined specialties from MongoDB
    document_subtype: Optional[str] = None  # From MongoDB
    research_area: Optional[str] = None  # From MongoDB
    summary: Optional[str] = None  # From MongoDB

class DocumentUploadResponse(BaseModel):
    document_id: uuid.UUID
    status: str
    message: str

class TimelineEvent(BaseModel):
    document_id: uuid.UUID
    date: Optional[date]
    document_type: Optional[str]
    document_subtype: Optional[str] = None
    specialty: Optional[str]
    title: str
    medical_facility: Optional[str]
    icon: str = "document"
    color: str = "#3B82F6"
    file_url: Optional[str] = None
    original_filename: Optional[str] = None
    summary: Optional[str] = None

class TimelineResponse(BaseModel):
    total_count: int
    date_range: Optional[Dict[str, Any]] = None
    events: list[TimelineEvent]

class ReportFilters(BaseModel):
    document_type: Optional[str] = None
    patient_name: Optional[str] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    medical_facility: Optional[str] = None

class ReportGenerateRequest(BaseModel):
    filters: ReportFilters
    
class ReportGenerateResponse(BaseModel):
    report_id: uuid.UUID
    status: str
    message: str

