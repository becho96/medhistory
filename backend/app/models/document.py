from sqlalchemy import Column, String, Integer, Date, Float, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.db.postgres import Base

class Document(Base):
    __tablename__ = "documents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # File information
    original_filename = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)
    file_type = Column(String(50), nullable=False)
    file_url = Column(Text, nullable=False)
    file_hash = Column(String(64), index=True)  # SHA256 hash for duplicate detection
    
    # Core metadata (extracted by AI) - stored in PostgreSQL
    document_type = Column(String(100), index=True)  # Only 5 types: "Прием врача", "Результаты анализа", etc.
    document_date = Column(Date, index=True)
    patient_name = Column(String(255))
    medical_facility = Column(String(255))
    
    # Processing status
    processing_status = Column(String(50), default="pending", index=True)
    
    # MongoDB reference
    mongodb_metadata_id = Column(String(255))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    interpretations = relationship(
        "Interpretation",
        secondary="interpretation_documents",
        back_populates="documents"
    )


class Tag(Base):
    __tablename__ = "tags"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    color = Column(String(7))  # hex color #RRGGBB
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class DocumentTag(Base):
    __tablename__ = "document_tags"
    
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True)
    tag_id = Column(UUID(as_uuid=True), ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True)
    is_auto_generated = Column(Boolean, default=False)


class Specialty(Base):
    __tablename__ = "specialties"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    name = Column(String(100), nullable=False)
    category = Column(String(100))
    icon_name = Column(String(50))
    usage_count = Column(Integer, default=1)


class DocumentType(Base):
    __tablename__ = "document_types"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    name = Column(String(100), nullable=False)
    parent_type_id = Column(UUID(as_uuid=True), ForeignKey("document_types.id"))
    icon_name = Column(String(50))
    color = Column(String(7))
    usage_count = Column(Integer, default=1)


# Report model moved to app/models/report.py

