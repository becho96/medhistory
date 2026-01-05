"""
Модели для справочника анализов и маппинга единиц измерения.

Таблицы:
- AnalyteCategory: категории анализов (ОАК, Биохимия и т.д.)
- AnalyteStandard: канонические названия анализов
- AnalyteSynonym: синонимы названий анализов
- UnitConversion: коэффициенты конвертации единиц измерения
"""

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, Boolean, Numeric, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.db.postgres import Base


class AnalyteCategory(Base):
    """Категории анализов (Общий анализ крови, Биохимия и т.д.)"""
    __tablename__ = "analyte_categories"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, unique=True)
    icon = Column(String(10), default="📋")  # Эмодзи для отображения
    sort_order = Column(Integer, default=0)  # Порядок сортировки в UI
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    analytes = relationship("AnalyteStandard", back_populates="category", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<AnalyteCategory {self.name}>"


class AnalyteStandard(Base):
    """Канонические названия анализов с их стандартными единицами"""
    __tablename__ = "analyte_standards"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category_id = Column(UUID(as_uuid=True), ForeignKey("analyte_categories.id", ondelete="CASCADE"), nullable=False, index=True)
    
    canonical_name = Column(String(150), nullable=False, unique=True)  # Стандартное название
    standard_unit = Column(String(30), nullable=False)  # Стандартная единица измерения
    description = Column(Text)  # Описание анализа
    
    # Референсные значения (опционально, для будущего)
    reference_male_min = Column(Numeric(15, 4))
    reference_male_max = Column(Numeric(15, 4))
    reference_female_min = Column(Numeric(15, 4))
    reference_female_max = Column(Numeric(15, 4))
    
    sort_order = Column(Integer, default=0)  # Порядок внутри категории
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    category = relationship("AnalyteCategory", back_populates="analytes")
    synonyms = relationship("AnalyteSynonym", back_populates="analyte", cascade="all, delete-orphan")
    unit_conversions = relationship("UnitConversion", back_populates="analyte", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<AnalyteStandard {self.canonical_name}>"


class AnalyteSynonym(Base):
    """Синонимы названий анализов (для маппинга разных лабораторий)"""
    __tablename__ = "analyte_synonyms"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analyte_id = Column(UUID(as_uuid=True), ForeignKey("analyte_standards.id", ondelete="CASCADE"), nullable=False, index=True)
    
    synonym = Column(String(200), nullable=False)  # Вариант названия
    synonym_lower = Column(String(200), nullable=False, index=True)  # Нижний регистр для поиска
    source = Column(String(100))  # Источник (название лаборатории, опционально)
    is_primary = Column(Boolean, default=False)  # Основной синоним (= canonical_name)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    analyte = relationship("AnalyteStandard", back_populates="synonyms")
    
    # Уникальный индекс по synonym_lower
    __table_args__ = (
        Index('ix_analyte_synonyms_synonym_lower_unique', 'synonym_lower', unique=True),
    )
    
    def __repr__(self):
        return f"<AnalyteSynonym {self.synonym}>"


class UnitConversion(Base):
    """Коэффициенты конвертации единиц измерения для анализов"""
    __tablename__ = "unit_conversions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analyte_id = Column(UUID(as_uuid=True), ForeignKey("analyte_standards.id", ondelete="CASCADE"), nullable=False, index=True)
    
    from_unit = Column(String(30), nullable=False)  # Исходная единица
    from_unit_lower = Column(String(30), nullable=False)  # Нижний регистр для поиска
    coefficient = Column(Numeric(15, 6), nullable=False)  # Коэффициент: value * coefficient = standard_value
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    analyte = relationship("AnalyteStandard", back_populates="unit_conversions")
    
    # Уникальный индекс по analyte_id + from_unit_lower
    __table_args__ = (
        Index('ix_unit_conversions_analyte_unit', 'analyte_id', 'from_unit_lower', unique=True),
    )
    
    def __repr__(self):
        return f"<UnitConversion {self.from_unit} -> standard (×{self.coefficient})>"


# Опционально: пользовательские маппинги (для будущего)
class UserAnalyteMapping(Base):
    """Пользовательские маппинги названий анализов (для будущего расширения)"""
    __tablename__ = "user_analyte_mappings"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    original_name = Column(String(200), nullable=False)  # Название из документа
    original_name_lower = Column(String(200), nullable=False, index=True)
    analyte_id = Column(UUID(as_uuid=True), ForeignKey("analyte_standards.id", ondelete="SET NULL"), nullable=True)
    
    # Если analyte_id = NULL, значит пользователь пометил как "не анализ" или "игнорировать"
    is_ignored = Column(Boolean, default=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('ix_user_analyte_mappings_user_name', 'user_id', 'original_name_lower', unique=True),
    )
    
    def __repr__(self):
        return f"<UserAnalyteMapping {self.original_name}>"

