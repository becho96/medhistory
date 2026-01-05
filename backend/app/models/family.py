from sqlalchemy import Column, String, DateTime, ForeignKey, Enum as SQLAlchemyEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
import enum

from app.db.postgres import Base


class RelationType(str, enum.Enum):
    """Типы семейных отношений"""
    PARENT = "parent"           # Родитель
    CHILD = "child"             # Ребенок
    SPOUSE = "spouse"           # Супруг/супруга
    GRANDPARENT = "grandparent" # Бабушка/дедушка
    GRANDCHILD = "grandchild"   # Внук/внучка
    SIBLING = "sibling"         # Брат/сестра
    OTHER = "other"             # Другое


# Обратные связи для двусторонних отношений
INVERSE_RELATIONS = {
    RelationType.PARENT: RelationType.CHILD,
    RelationType.CHILD: RelationType.PARENT,
    RelationType.SPOUSE: RelationType.SPOUSE,
    RelationType.GRANDPARENT: RelationType.GRANDCHILD,
    RelationType.GRANDCHILD: RelationType.GRANDPARENT,
    RelationType.SIBLING: RelationType.SIBLING,
    RelationType.OTHER: RelationType.OTHER,
}


class FamilyRelation(Base):
    """
    Модель семейных связей между пользователями.
    
    Связь создается от owner_id к member_id.
    owner_id - пользователь, который добавил члена семьи и управляет его профилем.
    member_id - добавленный член семьи.
    relation_type - тип отношения (как member приходится owner-у).
    """
    __tablename__ = "family_relations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Владелец связи - тот, кто добавил члена семьи
    owner_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("users.id", ondelete="CASCADE"), 
        nullable=False, 
        index=True
    )
    
    # Член семьи - добавленный пользователь
    member_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("users.id", ondelete="CASCADE"), 
        nullable=False, 
        index=True
    )
    
    # Тип отношения (как member приходится owner-у)
    # Например: owner добавил member как "child" (ребенок owner-а)
    relation_type = Column(
        SQLAlchemyEnum(RelationType, name="relation_type_enum"),
        nullable=False
    )
    
    # Пользовательское описание связи (если type=OTHER)
    custom_relation = Column(String(100))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    owner = relationship("User", foreign_keys=[owner_id], back_populates="family_members")
    member = relationship("User", foreign_keys=[member_id], back_populates="family_owners")

