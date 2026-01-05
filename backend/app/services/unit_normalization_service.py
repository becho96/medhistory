"""
Сервис для нормализации единиц измерения в результатах лабораторных анализов.

Этот сервис решает проблему дублирования единиц измерения из-за:
- Различий в написании (точки в конце, пробелы)
- Разных обозначений одной и той же единицы (мм/ч vs мм/час)
- Вариаций в формате (10*9/л vs х10^9/л)

Сервис может быть расширен для:
- Конвертации между единицами (г/дл -> г/л)
- Валидации единиц измерения
- Постобработки "сырых" результатов анализов
"""

import re
from typing import Optional, Dict, List, Tuple
from collections import defaultdict


class UnitNormalizationService:
    """Сервис для нормализации единиц измерения"""
    
    # Маппинг исходных единиц на нормализованные
    # Ключ - исходная единица (точное совпадение или regex)
    # Значение - нормализованная единица
    UNIT_MAPPING: Dict[str, str] = {
        # Дубликаты с точками и без
        "п/зр.": "п/зр",
        "п/зр": "п/зр",
        
        # Варианты времени
        "мм/ч": "мм/час",
        "мм/час": "мм/час",
        
        # Варианты обозначения степени (10^9/л)
        "10*9/л": "×10⁹/л",
        "х10^9/л": "×10⁹/л",
        "×10⁹/л": "×10⁹/л",
        "10^9/л": "×10⁹/л",
        
        "10*12/л": "×10¹²/л",
        "х10^12/л": "×10¹²/л",
        "×10¹²/л": "×10¹²/л",
        "10^12/л": "×10¹²/л",
        
        # Варианты pH
        "ед. pH": "pH",
        "pH": "pH",
        
        # Варианты с пробелами (если появятся)
        "г/л": "г/л",
        "г/ дл": "г/дл",
        "г/дл": "г/дл",
        
        # Проценты (должны оставаться как есть, но нормализуем пробелы)
        "%": "%",
    }
    
    # Regex паттерны для более сложных случаев
    REGEX_PATTERNS: List[Tuple[re.Pattern, str]] = [
        # Убираем точки в конце
        (re.compile(r'^(.+?)\.+$'), r'\1'),
        # Нормализуем пробелы
        (re.compile(r'\s+'), ' '),
        # Нормализуем варианты степени
        (re.compile(r'10\*(\d+)/л'), r'×10\1/л'),
        (re.compile(r'х10\^(\d+)/л'), r'×10\1/л'),
        (re.compile(r'10\^(\d+)/л'), r'×10\1/л'),
    ]
    
    @classmethod
    def normalize_unit(cls, unit: Optional[str]) -> Optional[str]:
        """
        Нормализует единицу измерения.
        
        Args:
            unit: Исходная единица измерения (может быть None)
            
        Returns:
            Нормализованная единица измерения или None
        """
        if unit is None:
            return None
        
        # Убираем пробелы в начале и конце
        unit = unit.strip()
        
        if not unit:
            return None
        
        # Сначала проверяем точное совпадение в маппинге
        if unit in cls.UNIT_MAPPING:
            return cls.UNIT_MAPPING[unit]
        
        # Применяем regex паттерны
        normalized = unit
        for pattern, replacement in cls.REGEX_PATTERNS:
            normalized = pattern.sub(replacement, normalized)
        
        # Проверяем, есть ли нормализованная версия в маппинге
        if normalized in cls.UNIT_MAPPING:
            return cls.UNIT_MAPPING[normalized]
        
        # Если не нашли в маппинге, возвращаем нормализованную версию
        return normalized.strip()
    
    @classmethod
    def normalize_lab_result(cls, lab_result: Dict) -> Dict:
        """
        Нормализует единицу измерения в результате анализа.
        
        Args:
            lab_result: Словарь с результатом анализа
                {
                    "test_name": str,
                    "value": str,
                    "unit": str | None,
                    "reference_range": str | None,
                    "flag": str | None
                }
            
        Returns:
            Словарь с нормализованной единицей измерения
        """
        normalized = lab_result.copy()
        original_unit = lab_result.get("unit")
        normalized_unit = cls.normalize_unit(original_unit)
        normalized["unit"] = normalized_unit
        normalized["original_unit"] = original_unit  # Сохраняем оригинал для отладки
        
        return normalized
    
    @classmethod
    def normalize_lab_results(cls, lab_results: List[Dict]) -> List[Dict]:
        """
        Нормализует единицы измерения в списке результатов анализов.
        
        Args:
            lab_results: Список результатов анализов
            
        Returns:
            Список результатов с нормализованными единицами
        """
        return [cls.normalize_lab_result(result) for result in lab_results]
    
    @classmethod
    def get_unit_groups(cls, units: List[Optional[str]]) -> Dict[str, List[str]]:
        """
        Группирует единицы измерения по нормализованным значениям.
        
        Args:
            units: Список единиц измерения
            
        Returns:
            Словарь {нормализованная_единица: [список_исходных_единиц]}
        """
        groups = defaultdict(list)
        for unit in units:
            normalized = cls.normalize_unit(unit)
            if normalized:
                groups[normalized].append(unit)
        
        # Убираем дубликаты в группах
        return {k: list(set(v)) for k, v in groups.items()}
    
    @classmethod
    def add_unit_mapping(cls, original: str, normalized: str) -> None:
        """
        Добавляет новое правило маппинга единиц измерения.
        
        Args:
            original: Исходная единица
            normalized: Нормализованная единица
        """
        cls.UNIT_MAPPING[original] = normalized
    
    @classmethod
    def get_mapping_stats(cls) -> Dict:
        """
        Возвращает статистику по маппингу единиц.
        
        Returns:
            Словарь со статистикой
        """
        # Группируем по нормализованным значениям
        reverse_mapping = defaultdict(list)
        for original, normalized in cls.UNIT_MAPPING.items():
            reverse_mapping[normalized].append(original)
        
        return {
            "total_mappings": len(cls.UNIT_MAPPING),
            "normalized_units": len(reverse_mapping),
            "mappings_by_normalized": dict(reverse_mapping),
            "regex_patterns": len(cls.REGEX_PATTERNS)
        }


# Создаем глобальный экземпляр сервиса
unit_normalization_service = UnitNormalizationService()

