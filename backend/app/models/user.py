from sqlalchemy import Column, String, Boolean, DateTime, Date, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
import enum

from app.db.postgres import Base

class GenderEnum(str, enum.Enum):
    """Пол пользователя"""
    male = "male"
    female = "female"
    other = "other"

class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=True, index=True)  # Nullable for family members
    password_hash = Column(String(255), nullable=True)  # Nullable for family members without credentials
    google_id = Column(String(255), unique=True, nullable=True, index=True)  # Google OAuth ID
    full_name = Column(String(255))
    birth_date = Column(Date, nullable=True)  # Дата рождения
    gender = Column(Enum(GenderEnum), nullable=True)  # Пол пользователя
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    interpretations = relationship("Interpretation", back_populates="user", cascade="all, delete-orphan")
    
    # Family relationships - members that this user owns/manages
    family_members = relationship(
        "FamilyRelation",
        foreign_keys="FamilyRelation.owner_id",
        back_populates="owner",
        cascade="all, delete-orphan"
    )
    
    # Family relationships - users that own/manage this user
    family_owners = relationship(
        "FamilyRelation",
        foreign_keys="FamilyRelation.member_id",
        back_populates="member",
        cascade="all, delete-orphan"
    )
    
    @property
    def has_credentials(self) -> bool:
        """Check if user has email and password set for independent login"""
        return self.email is not None and self.password_hash is not None
    
    @property
    def can_login(self) -> bool:
        """Check if user can login independently"""
        return self.has_credentials and self.is_active

