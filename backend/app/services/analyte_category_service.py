"""
Сервис категоризации анализов.

Для анализов, не найденных в справочнике AnalyteNormalizationService,
использует AI для определения категории и кэширует результат в MongoDB.
"""

import json
from typing import Optional, Dict, Any, List
from datetime import datetime

from app.services.analyte_normalization_service import (
    analyte_normalization_service,
    ANALYTE_STANDARDS,
    _SYNONYM_INDEX,
    _register_analyte
)
from app.core.config import settings


# Коллекция для кэширования AI-определенных категорий
_CATEGORY_CACHE_COLLECTION = "analyte_category_cache"


class AnalyteCategoryService:
    """Сервис для определения категории анализов"""
    
    # Список известных категорий для AI
    KNOWN_CATEGORIES = [
        "Общий анализ крови",
        "Биохимия крови",
        "Липидный профиль",
        "Коагулограмма",
        "Гормоны",
        "Витамины и микроэлементы",
        "Маркеры воспаления",
        "Общий анализ мочи",
        "Инфекции",
        "Микробиология",
        "Онкомаркеры",
        "Аутоиммунные маркеры",
        "Другое"
    ]
    
    @classmethod
    def get_category(cls, test_name: str) -> Optional[str]:
        """
        Возвращает категорию анализа.
        Сначала ищет в справочнике, затем в кэше.
        
        Args:
            test_name: Название анализа
            
        Returns:
            Категория анализа или None
        """
        # 1. Проверяем справочник
        canonical_name = analyte_normalization_service.get_canonical_name(test_name)
        if canonical_name:
            return analyte_normalization_service.get_category(canonical_name)
        
        # 2. Если не нашли в справочнике, возвращаем "Другое"
        # AI-определение будет происходить асинхронно
        return "Другое"
    
    @classmethod
    async def get_category_with_ai(
        cls, 
        test_name: str,
        unit: Optional[str] = None
    ) -> str:
        """
        Возвращает категорию анализа с использованием AI для неизвестных.
        
        Args:
            test_name: Название анализа
            unit: Единица измерения (для контекста)
            
        Returns:
            Категория анализа
        """
        # 1. Проверяем справочник
        canonical_name = analyte_normalization_service.get_canonical_name(test_name)
        if canonical_name:
            category = analyte_normalization_service.get_category(canonical_name)
            if category:
                return category
        
        # 2. Проверяем кэш в MongoDB
        cached = await cls._get_cached_category(test_name)
        if cached:
            return cached
        
        # 3. Запрашиваем у AI
        category = await cls._determine_category_with_ai(test_name, unit)
        
        # 4. Кэшируем результат
        await cls._cache_category(test_name, category, unit)
        
        return category
    
    @classmethod
    async def _get_cached_category(cls, test_name: str) -> Optional[str]:
        """Получает категорию из кэша MongoDB"""
        try:
            from app.db.mongodb import get_metadata_collection
            
            # Используем ту же коллекцию, но с другим типом документа
            db = get_metadata_collection().database
            cache_collection = db[_CATEGORY_CACHE_COLLECTION]
            
            doc = await cache_collection.find_one({
                "test_name_lower": test_name.lower().strip()
            })
            
            if doc:
                return doc.get("category")
            
            return None
        except Exception as e:
            print(f"⚠️ Ошибка при чтении кэша категорий: {e}")
            return None
    
    @classmethod
    async def _cache_category(
        cls, 
        test_name: str, 
        category: str,
        unit: Optional[str] = None
    ) -> None:
        """Кэширует категорию в MongoDB"""
        try:
            from app.db.mongodb import get_metadata_collection
            
            db = get_metadata_collection().database
            cache_collection = db[_CATEGORY_CACHE_COLLECTION]
            
            await cache_collection.update_one(
                {"test_name_lower": test_name.lower().strip()},
                {
                    "$set": {
                        "test_name": test_name,
                        "test_name_lower": test_name.lower().strip(),
                        "category": category,
                        "unit": unit,
                        "updated_at": datetime.utcnow()
                    },
                    "$setOnInsert": {
                        "created_at": datetime.utcnow()
                    }
                },
                upsert=True
            )
        except Exception as e:
            print(f"⚠️ Ошибка при кэшировании категории: {e}")
    
    @classmethod
    async def _determine_category_with_ai(
        cls, 
        test_name: str,
        unit: Optional[str] = None
    ) -> str:
        """
        Определяет категорию анализа с помощью AI.
        
        Args:
            test_name: Название анализа
            unit: Единица измерения
            
        Returns:
            Название категории
        """
        try:
            import httpx
            
            prompt = f"""Определи категорию медицинского анализа.

Название анализа: {test_name}
{f"Единица измерения: {unit}" if unit else ""}

Выбери ОДНУ категорию из списка:
{chr(10).join(f"- {cat}" for cat in cls.KNOWN_CATEGORIES)}

Ответь ТОЛЬКО названием категории, без объяснений."""

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": settings.OPENROUTER_MODEL,
                        "messages": [
                            {"role": "user", "content": prompt}
                        ],
                        "max_tokens": 50,
                        "temperature": 0
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    category = data["choices"][0]["message"]["content"].strip()
                    
                    # Проверяем, что категория из списка
                    if category in cls.KNOWN_CATEGORIES:
                        return category
                    
                    # Пробуем найти похожую категорию
                    category_lower = category.lower()
                    for known_cat in cls.KNOWN_CATEGORIES:
                        if known_cat.lower() in category_lower or category_lower in known_cat.lower():
                            return known_cat
                    
                    return "Другое"
                else:
                    print(f"⚠️ AI API error: {response.status_code}")
                    return "Другое"
                    
        except Exception as e:
            print(f"⚠️ Ошибка при определении категории через AI: {e}")
            return "Другое"
    
    @classmethod
    def get_categories_with_analytes(cls) -> Dict[str, List[Dict[str, Any]]]:
        """
        Возвращает все категории с их анализами.
        
        Returns:
            Словарь {категория: [список анализов с метаданными]}
        """
        result: Dict[str, List[Dict[str, Any]]] = {}
        
        for canonical_name, standard in ANALYTE_STANDARDS.items():
            category = standard.category
            
            if category not in result:
                result[category] = []
            
            result[category].append({
                "canonical_name": canonical_name,
                "standard_unit": standard.standard_unit,
                "synonyms": standard.synonyms
            })
        
        # Сортируем анализы внутри каждой категории
        for category in result:
            result[category] = sorted(result[category], key=lambda x: x["canonical_name"])
        
        return result
    
    @classmethod
    def get_category_order(cls) -> List[str]:
        """Возвращает порядок категорий для отображения"""
        return [
            "Общий анализ крови",
            "Биохимия крови",
            "Липидный профиль",
            "Коагулограмма",
            "Гормоны",
            "Витамины и микроэлементы",
            "Маркеры воспаления",
            "Общий анализ мочи",
            "Инфекции",
            "Микробиология",
            "Онкомаркеры",
            "Аутоиммунные маркеры",
            "Другое"
        ]
    
    @classmethod
    async def enrich_analytes_with_categories(
        cls,
        analytes: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Обогащает список аналитов категориями.
        
        Args:
            analytes: Список аналитов из MongoDB
                [{"name": str, "count": int, ...}]
            
        Returns:
            Список с добавленными полями canonical_name, category, standard_unit
        """
        enriched = []
        
        for analyte in analytes:
            name = analyte.get("name", "")
            
            # Пытаемся нормализовать
            canonical_name = analyte_normalization_service.get_canonical_name(name)
            
            if canonical_name:
                standard = analyte_normalization_service.get_standard(canonical_name)
                enriched.append({
                    **analyte,
                    "canonical_name": canonical_name,
                    "category": standard.category if standard else "Другое",
                    "standard_unit": standard.standard_unit if standard else None
                })
            else:
                # Неизвестный анализ - используем AI категорию
                category = await cls.get_category_with_ai(name)
                enriched.append({
                    **analyte,
                    "canonical_name": name,  # Оставляем оригинальное название
                    "category": category,
                    "standard_unit": None
                })
        
        return enriched
    
    @classmethod
    def group_by_category(
        cls,
        analytes: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Группирует список аналитов по категориям.
        
        Args:
            analytes: Обогащенный список аналитов
            
        Returns:
            Список категорий с вложенными аналитами:
            [
                {
                    "name": "Общий анализ крови",
                    "analytes": [...]
                }
            ]
        """
        # Группируем по категориям
        categories_dict: Dict[str, List[Dict[str, Any]]] = {}
        
        for analyte in analytes:
            category = analyte.get("category", "Другое")
            if category not in categories_dict:
                categories_dict[category] = []
            categories_dict[category].append(analyte)
        
        # Сортируем по порядку категорий
        order = cls.get_category_order()
        result = []
        
        for category_name in order:
            if category_name in categories_dict:
                result.append({
                    "name": category_name,
                    "analytes": sorted(
                        categories_dict[category_name],
                        key=lambda x: x.get("canonical_name", x.get("name", ""))
                    )
                })
        
        # Добавляем категории, которых нет в порядке
        for category_name, analytes_list in categories_dict.items():
            if category_name not in order:
                result.append({
                    "name": category_name,
                    "analytes": sorted(
                        analytes_list,
                        key=lambda x: x.get("canonical_name", x.get("name", ""))
                    )
                })
        
        return result


# Глобальный экземпляр сервиса
analyte_category_service = AnalyteCategoryService()

