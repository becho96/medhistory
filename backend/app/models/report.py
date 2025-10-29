from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from app.db.postgres import Base

class Report(Base):
    __tablename__ = "reports"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    report_type = Column(String(100))
    filters_applied = Column(Text)  # JSON string
    file_url = Column(Text, nullable=False)
    file_size = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

