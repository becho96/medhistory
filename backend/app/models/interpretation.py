from sqlalchemy import Column, String, Text, DateTime, Enum as SQLEnum, ForeignKey, Table
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.db.postgres import Base


class InterpretationStatus(str, enum.Enum):
    """Статус обработки интерпретации"""
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


# Association table for many-to-many relationship between interpretations and documents
interpretation_documents = Table(
    'interpretation_documents',
    Base.metadata,
    Column('interpretation_id', UUID(as_uuid=True), ForeignKey('interpretations.id', ondelete='CASCADE')),
    Column('document_id', UUID(as_uuid=True), ForeignKey('documents.id', ondelete='CASCADE'))
)


class Interpretation(Base):
    """Модель для хранения AI-интерпретаций результатов анализов"""
    __tablename__ = "interpretations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Статус обработки
    status = Column(
        SQLEnum(InterpretationStatus), 
        nullable=False, 
        default=InterpretationStatus.pending
    )
    
    # Результат интерпретации от AI
    interpretation_text = Column(Text, nullable=True)
    
    # Ошибка (если status = failed)
    error_message = Column(Text, nullable=True)
    
    # Метаданные
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="interpretations")
    documents = relationship(
        "Document",
        secondary=interpretation_documents,
        back_populates="interpretations"
    )

    def __repr__(self):
        return f"<Interpretation(id={self.id}, user_id={self.user_id}, status={self.status})>"

