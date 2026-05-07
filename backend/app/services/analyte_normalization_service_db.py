"""
Сервис нормализации названий анализов и конвертации единиц измерения.
Версия с хранением в PostgreSQL и кэшированием в памяти.

Решает проблемы:
- Разные названия одного анализа в разных лабораториях
- Разные единицы измерения для одного анализа
- Необходимость конвертации значений для корректного сравнения

Пример использования:
    # Загрузка данных при старте приложения
    await analyte_normalization_service.load_from_db(db_session)
    
    # Использование
    result = analyte_normalization_service.normalize_and_convert(
        test_name="Витамин D, 25-гидрокси",
        value="50",
        unit="нмоль/л"
    )
    # result = ("Витамин D (25-OH)", 20.0, "нг/мл", "Витамины и микроэлементы")
"""

import asyncio
from typing import Optional, Dict, List, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging

# Тип ключа: (synonym_lower, unit_lower) -> (canonical_name, coefficient)
SynonymUnitKey = Tuple[str, str]

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from sqlalchemy.orm import selectinload

logger = logging.getLogger(__name__)


@dataclass
class CachedAnalyte:
    """Кэшированные данные анализа"""
    id: str
    canonical_name: str
    standard_unit: str
    category_id: str
    category_name: str
    category_icon: str
    synonyms: List[str] = field(default_factory=list)
    conversions: Dict[str, float] = field(default_factory=dict)


@dataclass
class CachedCategory:
    """Кэшированные данные категории"""
    id: str
    name: str
    icon: str
    sort_order: int


class AnalyteNormalizationServiceDB:
    """
    Сервис для нормализации названий анализов и конвертации единиц измерения.
    Данные загружаются из PostgreSQL и кэшируются в памяти.
    """
    
    def __init__(self):
        # Кэш данных
        self._categories: Dict[str, CachedCategory] = {}  # id -> category
        self._analytes: Dict[str, CachedAnalyte] = {}  # canonical_name -> analyte
        # (synonym_lower, unit_lower) -> (canonical_name, coefficient)
        self._synonym_unit_index: Dict[SynonymUnitKey, Tuple[str, float]] = {}
        self._loaded: bool = False
        self._last_load: Optional[datetime] = None
        self._cache_ttl: timedelta = timedelta(hours=1)
    
    @property
    def is_loaded(self) -> bool:
        """Проверяет, загружены ли данные"""
        return self._loaded
    
    @property
    def needs_reload(self) -> bool:
        """Проверяет, нужно ли перезагрузить кэш"""
        if not self._loaded or self._last_load is None:
            return True
        return datetime.utcnow() - self._last_load > self._cache_ttl
    
    async def load_from_db(self, db: AsyncSession, force: bool = False) -> None:
        """
        Загружает данные из базы данных в кэш.
        
        Args:
            db: Сессия SQLAlchemy
            force: Принудительная перезагрузка даже если кэш актуален
        """
        if self._loaded and not force and not self.needs_reload:
            return
        
        logger.info("🔄 Загрузка справочника анализов из БД...")
        
        try:
            # Загружаем категории
            categories_result = await db.execute(
                text("""
                    SELECT id, name, icon, sort_order 
                    FROM analyte_categories 
                    WHERE is_active = TRUE
                    ORDER BY sort_order
                """)
            )
            
            self._categories = {}
            for row in categories_result.fetchall():
                cat = CachedCategory(
                    id=str(row[0]),
                    name=row[1],
                    icon=row[2] or "📋",
                    sort_order=row[3] or 0
                )
                self._categories[cat.id] = cat
            
            # Загружаем анализы с синонимами и конверсиями
            analytes_result = await db.execute(
                text("""
                    SELECT 
                        a.id,
                        a.canonical_name,
                        a.standard_unit,
                        a.category_id,
                        c.name as category_name,
                        c.icon as category_icon
                    FROM analyte_standards a
                    JOIN analyte_categories c ON c.id = a.category_id
                    WHERE a.is_active = TRUE AND c.is_active = TRUE
                    ORDER BY c.sort_order, a.sort_order
                """)
            )
            
            self._analytes = {}
            analyte_ids = []
            
            for row in analytes_result.fetchall():
                analyte = CachedAnalyte(
                    id=str(row[0]),
                    canonical_name=row[1],
                    standard_unit=row[2] or "",
                    category_id=str(row[3]),
                    category_name=row[4],
                    category_icon=row[5] or "📋"
                )
                self._analytes[analyte.canonical_name] = analyte
                analyte_ids.append(str(row[0]))
            
            # Загружаем синонимы с unit и coefficient (unit_conversions объединены в analyte_synonyms)
            if analyte_ids:
                synonyms_result = await db.execute(
                    text("""
                        SELECT analyte_id, synonym, synonym_lower, COALESCE(unit, ''), COALESCE(unit_lower, ''), COALESCE(coefficient, 1.0)
                        FROM analyte_synonyms
                        WHERE analyte_id = ANY(:ids)
                    """),
                    {"ids": analyte_ids}
                )
                
                self._synonym_unit_index = {}
                analyte_id_to_name = {a.id: a.canonical_name for a in self._analytes.values()}
                
                for row in synonyms_result.fetchall():
                    analyte_id = str(row[0])
                    synonym = row[1]
                    synonym_lower = row[2]
                    unit = str(row[3]) if row[3] is not None else ""
                    unit_lower = str(row[4]) if row[4] is not None else ""
                    coefficient = float(row[5])
                    
                    canonical_name = analyte_id_to_name.get(analyte_id)
                    if canonical_name:
                        key: SynonymUnitKey = (synonym_lower, unit_lower)
                        self._synonym_unit_index[key] = (canonical_name, coefficient)
                        if canonical_name in self._analytes:
                            self._analytes[canonical_name].synonyms.append(f"{synonym} [{unit}]" if unit else synonym)
                            # conversions для convert_value: unit_lower -> coefficient
                            if unit_lower:
                                self._analytes[canonical_name].conversions[unit_lower] = coefficient
            
            self._loaded = True
            self._last_load = datetime.utcnow()
            
            logger.info(
                f"✅ Загружено: {len(self._categories)} категорий, "
                f"{len(self._analytes)} анализов, "
                f"{len(self._synonym_unit_index)} синонимов"
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки справочника анализов: {e}")
            raise
    
    def invalidate_cache(self) -> None:
        """Инвалидирует кэш (данные будут перезагружены при следующем запросе)"""
        self._loaded = False
        self._last_load = None
    
    def get_canonical_name(self, test_name: str, unit: Optional[str] = None) -> Optional[str]:
        """
        Возвращает каноническое название анализа по паре (test_name, unit).
        
        Args:
            test_name: Название анализа из документа
            unit: Единица измерения (обязательна для различения, напр. "%" vs "10^9/л")
            
        Returns:
            Каноническое название или None если не найдено
        """
        if not test_name or not self._loaded:
            return None
        
        normalized = test_name.lower().strip()
        unit_lower = (unit or "").lower().strip()
        
        # Точный поиск по (synonym_lower, unit_lower)
        key: SynonymUnitKey = (normalized, unit_lower)
        if key in self._synonym_unit_index:
            return self._synonym_unit_index[key][0]
        
        # Fallback: синонимы с unit='' (универсальный маппинг по имени)
        fallback_key: SynonymUnitKey = (normalized, "")
        if fallback_key in self._synonym_unit_index:
            return self._synonym_unit_index[fallback_key][0]
        
        return None
    
    def find_canonical_unit_agnostic(self, test_name: str) -> Optional[str]:
        """
        Возвращает канонкое имя по синониму, игнорируя unit.

        В отличие от get_canonical_name, не требует юнит. Удобно для коротких
        пользовательских запросов («B12», «ТТГ»), где unit неизвестен.
        Если один и тот же синоним мапится на разные канониклы для разных юнитов
        (теоретически возможно), вернёт первый найденный.
        """
        if not test_name or not self._loaded:
            return None
        normalized = test_name.lower().strip()
        for (syn, _unit), (canonical, _coef) in self._synonym_unit_index.items():
            if syn == normalized:
                return canonical
        return None

    def get_analyte(self, canonical_name: str) -> Optional[CachedAnalyte]:
        """Возвращает данные анализа по каноническому названию"""
        return self._analytes.get(canonical_name)
    
    def get_standard_unit(self, canonical_name: str) -> Optional[str]:
        """Возвращает стандартную единицу измерения для анализа"""
        analyte = self.get_analyte(canonical_name)
        return analyte.standard_unit if analyte else None
    
    def get_category(self, canonical_name: str) -> Optional[str]:
        """Возвращает категорию анализа"""
        analyte = self.get_analyte(canonical_name)
        return analyte.category_name if analyte else None
    
    def convert_value(
        self, 
        value: Any, 
        from_unit: Optional[str], 
        canonical_name: str,
        strict: bool = True
    ) -> Tuple[Optional[float], Optional[str]]:
        """
        Конвертирует значение в стандартную единицу измерения.
        
        Args:
            value: Значение анализа (строка или число)
            from_unit: Исходная единица измерения
            canonical_name: Каноническое название анализа
            strict: Если True, возвращает None для несовместимых единиц.
                    Если False, возвращает исходное значение без конвертации.
            
        Returns:
            Кортеж (конвертированное_значение, стандартная_единица)
            Возвращает (None, None) если единица несовместима (в strict режиме)
        """
        analyte = self.get_analyte(canonical_name)
        if not analyte:
            return None, None
        
        # Парсим значение
        if value is None:
            return None, analyte.standard_unit
        
        try:
            numeric_value = float(str(value).replace(',', '.').strip())
        except (ValueError, TypeError):
            return None, analyte.standard_unit
        
        # Ищем коэффициент конвертации
        if from_unit:
            normalized_unit = from_unit.strip()
            
            # Пробуем найти точное совпадение
            if normalized_unit in analyte.conversions:
                coefficient = analyte.conversions[normalized_unit]
                return numeric_value * coefficient, analyte.standard_unit
            
            # Пробуем lowercase
            if normalized_unit.lower() in analyte.conversions:
                coefficient = analyte.conversions[normalized_unit.lower()]
                return numeric_value * coefficient, analyte.standard_unit
            
            # Конверсия не найдена - единица несовместима
            if strict:
                return None, None
        
        # Если единица не указана или strict=False, возвращаем исходное значение
        return numeric_value, analyte.standard_unit
    
    def normalize_and_convert(
        self,
        test_name: str,
        value: Any,
        unit: Optional[str]
    ) -> Tuple[Optional[str], Optional[float], Optional[str], Optional[str]]:
        """
        Полная нормализация: название + значение + единица + категория.
        
        Args:
            test_name: Название анализа из документа
            value: Значение
            unit: Единица измерения
            
        Returns:
            Кортеж (canonical_name, converted_value, standard_unit, category)
        """
        canonical_name = self.get_canonical_name(test_name, unit)
        
        if not canonical_name:
            return None, None, None, None
        
        converted_value, standard_unit = self.convert_value(value, unit, canonical_name)
        category = self.get_category(canonical_name)
        
        return canonical_name, converted_value, standard_unit, category
    
    def normalize_lab_result(self, lab_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Нормализует результат анализа.
        
        Args:
            lab_result: Словарь с результатом анализа
            
        Returns:
            Нормализованный результат с дополнительными полями
        """
        result = lab_result.copy()
        
        test_name = lab_result.get("test_name", "")
        value = lab_result.get("value")
        unit = lab_result.get("unit")
        
        canonical_name, converted_value, standard_unit, category = self.normalize_and_convert(
            test_name, value, unit
        )
        
        result["canonical_name"] = canonical_name
        result["converted_value"] = converted_value
        result["standard_unit"] = standard_unit
        result["category"] = category
        
        return result
    
    def get_all_categories(self) -> List[Dict[str, Any]]:
        """Возвращает список всех категорий"""
        return [
            {
                "id": cat.id,
                "name": cat.name,
                "icon": cat.icon,
                "sort_order": cat.sort_order
            }
            for cat in sorted(self._categories.values(), key=lambda x: x.sort_order)
        ]
    
    def get_analytes_by_category(self, category_name: str) -> List[str]:
        """Возвращает список канонических названий анализов для категории"""
        return sorted([
            name for name, analyte in self._analytes.items()
            if analyte.category_name == category_name
        ])
    
    def get_all_analytes_grouped(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Возвращает все анализы, сгруппированные по категориям.
        Формат для API.
        """
        result = {}
        
        for cat in sorted(self._categories.values(), key=lambda x: x.sort_order):
            analytes = []
            for name, analyte in self._analytes.items():
                if analyte.category_id == cat.id:
                    analytes.append({
                        "canonical_name": analyte.canonical_name,
                        "standard_unit": analyte.standard_unit,
                        "synonyms": analyte.synonyms
                    })
            
            if analytes:
                result[cat.name] = {
                    "icon": cat.icon,
                    "analytes": sorted(analytes, key=lambda x: x["canonical_name"])
                }
        
        return result
    
    def is_known_analyte(self, test_name: str, unit: Optional[str] = None) -> bool:
        """Проверяет, известен ли анализ в справочнике (по test_name и unit)"""
        return self.get_canonical_name(test_name, unit) is not None
    
    def get_stats(self) -> Dict[str, Any]:
        """Возвращает статистику справочника"""
        return {
            "loaded": self._loaded,
            "last_load": self._last_load.isoformat() if self._last_load else None,
            "categories_count": len(self._categories),
            "analytes_count": len(self._analytes),
            "synonyms_count": len(self._synonym_unit_index)
        }


# Глобальный экземпляр сервиса
analyte_normalization_service_db = AnalyteNormalizationServiceDB()

