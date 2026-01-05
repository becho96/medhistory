#!/usr/bin/env python3
"""
Скрипт для анализа всех единиц измерения в базе данных
и создания маппинга для нормализации.
"""

import asyncio
import sys
import os
from pathlib import Path
from collections import defaultdict, Counter
import json
import re

# Добавляем корневую директорию проекта в путь
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "backend"))

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Загружаем переменные окружения
env_file = project_root / ".env.local"
if not env_file.exists():
    env_file = project_root / "environments" / "local.env"
load_dotenv(env_file)

# Параметры подключения MongoDB
MONGO_USER = os.getenv("MONGO_INITDB_ROOT_USERNAME", "admin")
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD", "mongodb_local_pass")
MONGO_DB = os.getenv("MONGO_INITDB_DATABASE", "medhistory")

# Определяем хост
MONGODB_URL_ENV = os.getenv("MONGODB_URL")
if MONGODB_URL_ENV:
    MONGODB_URL = MONGODB_URL_ENV
else:
    is_docker = os.path.exists("/.dockerenv") or os.getenv("DOCKER_CONTAINER") == "true"
    MONGO_HOST = "mongodb" if is_docker else os.getenv("MONGODB_HOST", "localhost")
    MONGO_PORT = os.getenv("MONGODB_PORT", "27017")
    MONGODB_URL = f"mongodb://{MONGO_USER}:{MONGO_PASSWORD}@{MONGO_HOST}:{MONGO_PORT}/{MONGO_DB}?authSource=admin"


async def analyze_all_units():
    """Анализирует все единицы измерения в базе данных"""
    
    print(f"🔌 Подключение к MongoDB...")
    client = AsyncIOMotorClient(MONGODB_URL)
    db = client[MONGO_DB]
    collection = db.document_metadata
    
    # Получаем все единицы измерения
    print("\n📊 Сбор всех единиц измерения...")
    pipeline = [
        {"$match": {"extracted_data.lab_results": {"$exists": True, "$ne": []}}},
        {"$project": {"extracted_data.lab_results": 1}},
        {"$unwind": "$extracted_data.lab_results"},
        {
            "$group": {
                "_id": "$extracted_data.lab_results.unit",
                "count": {"$sum": 1},
                "test_names": {"$addToSet": "$extracted_data.lab_results.test_name"}
            }
        },
        {"$sort": {"count": -1}}
    ]
    
    units_data = []
    async for doc in collection.aggregate(pipeline):
        unit = doc["_id"]
        count = doc.get("count", 0)
        test_names = doc.get("test_names", [])
        units_data.append({
            "unit": unit,
            "count": count,
            "test_names": sorted(test_names)[:10]  # Первые 10 для примера
        })
    
    print(f"✅ Найдено {len(units_data)} уникальных единиц измерения\n")
    
    # Группируем похожие единицы
    print("🔍 Анализ похожих единиц...\n")
    
    # Нормализуем для сравнения (убираем пробелы, приводим к нижнему регистру, убираем точки)
    def normalize_for_comparison(unit):
        if not unit:
            return None
        # Убираем пробелы, точки в конце, приводим к нижнему регистру
        normalized = str(unit).strip().lower()
        normalized = re.sub(r'\.+$', '', normalized)  # Убираем точки в конце
        normalized = re.sub(r'\s+', ' ', normalized)  # Нормализуем пробелы
        return normalized
    
    # Группируем по нормализованному значению
    normalized_groups = defaultdict(list)
    for unit_data in units_data:
        unit = unit_data["unit"]
        normalized = normalize_for_comparison(unit)
        normalized_groups[normalized].append(unit_data)
    
    # Находим группы с несколькими вариантами
    duplicates = {k: v for k, v in normalized_groups.items() if len(v) > 1 and k is not None}
    
    print(f"📌 Найдено {len(duplicates)} групп с дублирующимися единицами:\n")
    
    for normalized, variants in sorted(duplicates.items(), key=lambda x: sum(v["count"] for v in x[1]), reverse=True):
        total_count = sum(v["count"] for v in variants)
        print(f"  Группа: '{normalized}' (всего {total_count} записей)")
        for variant in sorted(variants, key=lambda x: x["count"], reverse=True):
            print(f"    - '{variant['unit']}' ({variant['count']} записей)")
        print()
    
    # Сохраняем полный список единиц
    output_file = Path("/app/scripts/all_units_analysis.json") if os.path.exists("/.dockerenv") else project_root / "backend" / "scripts" / "all_units_analysis.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({
            "total_unique_units": len(units_data),
            "duplicate_groups": {
                k: [{"unit": v["unit"], "count": v["count"]} for v in variants]
                for k, variants in duplicates.items()
            },
            "all_units": units_data
        }, f, ensure_ascii=False, indent=2)
    
    print(f"💾 Полный анализ сохранен в: {output_file}")
    
    # Статистика
    print(f"\n📊 Статистика:")
    print(f"   Всего уникальных единиц: {len(units_data)}")
    print(f"   Групп с дубликатами: {len(duplicates)}")
    print(f"   Единиц с null: {sum(1 for u in units_data if u['unit'] is None)}")
    
    client.close()
    return units_data, duplicates


if __name__ == "__main__":
    asyncio.run(analyze_all_units())

