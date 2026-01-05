#!/usr/bin/env python3
"""
Скрипт для анализа проблем с единицами измерения и процентными значениями
в результатах лабораторных анализов.

Анализирует данные одного пользователя из локальной базы данных MongoDB
и выявляет:
1. Анализы с одинаковым test_name, но разными unit
2. Анализы, где unit содержит проценты (%)
3. Потенциальные проблемы группировки данных
"""

import asyncio
import sys
import os
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Set, Tuple
import json

# Добавляем корневую директорию проекта в путь
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "backend"))

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient
from dotenv import load_dotenv

# Загружаем переменные окружения
env_file = project_root / ".env.local"
if not env_file.exists():
    env_file = project_root / "environments" / "local.env"
load_dotenv(env_file)

# Параметры подключения MongoDB из переменных окружения
MONGO_USER = os.getenv("MONGO_INITDB_ROOT_USERNAME", "admin")
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD", "mongodb_local_pass")
MONGO_DB = os.getenv("MONGO_INITDB_DATABASE", "medhistory")

# Определяем хост: если MONGODB_URL задан, используем его, иначе определяем автоматически
MONGODB_URL_ENV = os.getenv("MONGODB_URL")
if MONGODB_URL_ENV:
    MONGODB_URL = MONGODB_URL_ENV
else:
    # Проверяем, запущены ли мы внутри Docker (по наличию /.dockerenv или переменной окружения)
    is_docker = os.path.exists("/.dockerenv") or os.getenv("DOCKER_CONTAINER") == "true"
    MONGO_HOST = "mongodb" if is_docker else os.getenv("MONGODB_HOST", "localhost")
    MONGO_PORT = os.getenv("MONGODB_PORT", "27017")
    MONGODB_URL = f"mongodb://{MONGO_USER}:{MONGO_PASSWORD}@{MONGO_HOST}:{MONGO_PORT}/{MONGO_DB}?authSource=admin"


async def analyze_lab_units():
    """Основная функция анализа"""
    
    # Подключаемся к MongoDB
    print(f"🔌 Подключение к MongoDB: {MONGODB_URL.split('@')[1] if '@' in MONGODB_URL else MONGODB_URL}")
    client = AsyncIOMotorClient(MONGODB_URL)
    db = client[MONGO_DB]
    collection = db.document_metadata
    
    # Получаем список всех пользователей с данными анализов
    print("\n📊 Поиск пользователей с данными анализов...")
    pipeline_users = [
        {
            "$match": {
                "extracted_data.lab_results": {"$exists": True, "$ne": []}
            }
        },
        {
            "$group": {
                "_id": "$user_id",
                "doc_count": {"$sum": 1},
                "total_labs": {
                    "$sum": {"$size": {"$ifNull": ["$extracted_data.lab_results", []]}}
                }
            }
        },
        {"$sort": {"total_labs": -1}},
        {"$limit": 10}
    ]
    
    users_data = []
    async for doc in collection.aggregate(pipeline_users):
        users_data.append({
            "user_id": doc["_id"],
            "doc_count": doc.get("doc_count", 0),
            "total_labs": doc.get("total_labs", 0)
        })
    
    if not users_data:
        print("❌ Не найдено пользователей с данными анализов")
        client.close()
        return
    
    print(f"✅ Найдено {len(users_data)} пользователей с данными")
    print("\nПользователи с наибольшим количеством анализов:")
    for i, user in enumerate(users_data[:5], 1):
        print(f"  {i}. User {user['user_id']}: {user['doc_count']} документов, {user['total_labs']} анализов")
    
    # Берем первого пользователя для анализа
    selected_user = users_data[0]
    user_id = selected_user["user_id"]
    print(f"\n🎯 Анализируем данные пользователя: {user_id}")
    print(f"   Документов: {selected_user['doc_count']}")
    print(f"   Всего анализов: {selected_user['total_labs']}")
    
    # Получаем все результаты анализов для этого пользователя
    print("\n📥 Загрузка данных анализов...")
    cursor = collection.find(
        {"user_id": user_id, "extracted_data.lab_results": {"$exists": True, "$ne": []}},
        {"document_id": 1, "extracted_data.lab_results": 1}
    )
    
    all_labs = []
    async for doc in cursor:
        doc_id = doc.get("document_id")
        lab_results = doc.get("extracted_data", {}).get("lab_results", [])
        if not isinstance(lab_results, list):
            continue
        
        for lab in lab_results:
            if not isinstance(lab, dict):
                continue
            all_labs.append({
                "document_id": doc_id,
                "test_name": lab.get("test_name"),
                "value": lab.get("value"),
                "unit": lab.get("unit"),
                "reference_range": lab.get("reference_range"),
                "flag": lab.get("flag")
            })
    
    print(f"✅ Загружено {len(all_labs)} результатов анализов")
    
    # Анализ 1: Находим анализы с одинаковым test_name, но разными unit
    print("\n" + "="*80)
    print("АНАЛИЗ 1: Анализы с одинаковым названием, но разными единицами измерения")
    print("="*80)
    
    test_name_to_units = defaultdict(set)
    test_name_to_labs = defaultdict(list)
    
    for lab in all_labs:
        test_name = lab.get("test_name")
        if not test_name:
            continue
        
        unit = lab.get("unit") or "null"
        test_name_to_units[test_name].add(unit)
        test_name_to_labs[test_name].append(lab)
    
    # Находим тесты с разными единицами
    problematic_tests = {
        name: units 
        for name, units in test_name_to_units.items() 
        if len(units) > 1
    }
    
    print(f"\n🔍 Найдено {len(problematic_tests)} анализов с разными единицами измерения:\n")
    
    for test_name in sorted(problematic_tests.keys()):
        units = sorted(problematic_tests[test_name])
        labs = test_name_to_labs[test_name]
        
        print(f"📌 {test_name}")
        print(f"   Единицы измерения: {', '.join(repr(u) for u in units)} ({len(units)} вариантов)")
        print(f"   Всего записей: {len(labs)}")
        
        # Группируем по единицам
        unit_groups = defaultdict(list)
        for lab in labs:
            unit = lab.get("unit") or "null"
            unit_groups[unit].append(lab)
        
        print(f"   Распределение по единицам:")
        for unit, unit_labs in sorted(unit_groups.items()):
            print(f"     - {repr(unit)}: {len(unit_labs)} записей")
            # Показываем примеры значений
            examples = unit_labs[:3]
            for ex in examples:
                print(f"       • {ex.get('value')} {ex.get('unit') or ''} "
                      f"(ref: {ex.get('reference_range') or 'N/A'})")
        
        print()
    
    # Анализ 2: Находим процентные значения
    print("\n" + "="*80)
    print("АНАЛИЗ 2: Анализы с процентными значениями")
    print("="*80)
    
    percentage_labs = []
    for lab in all_labs:
        unit = lab.get("unit")
        if unit and ("%" in str(unit) or "процент" in str(unit).lower() or "percent" in str(unit).lower()):
            percentage_labs.append(lab)
    
    print(f"\n🔍 Найдено {len(percentage_labs)} результатов с процентными единицами:\n")
    
    if percentage_labs:
        percentage_by_test = defaultdict(list)
        for lab in percentage_labs:
            test_name = lab.get("test_name") or "Unknown"
            percentage_by_test[test_name].append(lab)
        
        for test_name in sorted(percentage_by_test.keys()):
            labs = percentage_by_test[test_name]
            print(f"📌 {test_name}")
            print(f"   Записей: {len(labs)}")
            units = set(lab.get("unit") for lab in labs if lab.get("unit"))
            print(f"   Единицы: {', '.join(repr(u) for u in units)}")
            for lab in labs[:5]:  # Показываем первые 5 примеров
                print(f"     • {lab.get('value')} {lab.get('unit') or ''} "
                      f"(ref: {lab.get('reference_range') or 'N/A'})")
            if len(labs) > 5:
                print(f"     ... и еще {len(labs) - 5} записей")
            print()
    
    # Анализ 3: Находим анализы, где один и тот же тест может быть и абсолютным, и процентным
    print("\n" + "="*80)
    print("АНАЛИЗ 3: Анализы с одновременно абсолютными и процентными значениями")
    print("="*80)
    
    mixed_tests = {}
    for test_name, units in problematic_tests.items():
        has_percentage = any("%" in str(u) or "процент" in str(u).lower() or "percent" in str(u).lower() 
                            for u in units)
        has_absolute = any("%" not in str(u) and "процент" not in str(u).lower() and "percent" not in str(u).lower() 
                          for u in units if u != "null")
        
        if has_percentage and has_absolute:
            mixed_tests[test_name] = units
    
    print(f"\n🔍 Найдено {len(mixed_tests)} анализов с одновременно абсолютными и процентными значениями:\n")
    
    for test_name in sorted(mixed_tests.keys()):
        units = sorted(mixed_tests[test_name])
        labs = test_name_to_labs[test_name]
        
        print(f"⚠️  {test_name}")
        print(f"   Единицы: {', '.join(repr(u) for u in units)}")
        
        # Разделяем на абсолютные и процентные
        absolute_labs = [lab for lab in labs 
                        if lab.get("unit") and "%" not in str(lab.get("unit")) 
                        and "процент" not in str(lab.get("unit")).lower()
                        and "percent" not in str(lab.get("unit")).lower()]
        percentage_labs = [lab for lab in labs 
                          if lab.get("unit") and ("%" in str(lab.get("unit")) 
                          or "процент" in str(lab.get("unit")).lower()
                          or "percent" in str(lab.get("unit")).lower())]
        
        print(f"   Абсолютные значения: {len(absolute_labs)} записей")
        for lab in absolute_labs[:3]:
            print(f"     • {lab.get('value')} {lab.get('unit') or ''}")
        
        print(f"   Процентные значения: {len(percentage_labs)} записей")
        for lab in percentage_labs[:3]:
            print(f"     • {lab.get('value')} {lab.get('unit') or ''}")
        print()
    
    # Анализ 4: Статистика по единицам измерения
    print("\n" + "="*80)
    print("АНАЛИЗ 4: Общая статистика по единицам измерения")
    print("="*80)
    
    unit_stats = defaultdict(int)
    null_unit_count = 0
    
    for lab in all_labs:
        unit = lab.get("unit")
        if not unit:
            null_unit_count += 1
        else:
            unit_stats[unit] += 1
    
    print(f"\n📊 Всего результатов: {len(all_labs)}")
    print(f"   Без единиц измерения: {null_unit_count}")
    print(f"   С единицами измерения: {len(all_labs) - null_unit_count}")
    print(f"   Уникальных единиц: {len(unit_stats)}")
    
    print(f"\nТоп-20 наиболее часто встречающихся единиц:")
    for unit, count in sorted(unit_stats.items(), key=lambda x: x[1], reverse=True)[:20]:
        print(f"   {repr(unit):40} {count:5} записей")
    
    # Рекомендации
    print("\n" + "="*80)
    print("РЕКОМЕНДАЦИИ ПО РЕШЕНИЮ ПРОБЛЕМ")
    print("="*80)
    
    print("\n1. Проблема группировки в timeseries:")
    print("   Текущая реализация группирует анализы только по test_name.")
    print("   Это приводит к смешиванию абсолютных и процентных значений.")
    print("   РЕШЕНИЕ: Группировать по комбинации (test_name, unit)")
    
    print("\n2. Разные единицы измерения в разных клиниках:")
    print(f"   Найдено {len(problematic_tests)} анализов с разными единицами.")
    print("   РЕШЕНИЕ: Нормализация единиц измерения или создание отдельных временных рядов")
    
    print("\n3. Процентные и абсолютные значения:")
    print(f"   Найдено {len(mixed_tests)} анализов с одновременным наличием обоих типов.")
    print("   РЕШЕНИЕ: Обязательно разделять на разные графики")
    
    print("\n4. Предлагаемые улучшения:")
    print("   - Добавить поле normalized_unit в схему данных")
    print("   - Изменить ключ группировки в timeseries на (test_name, unit)")
    print("   - Добавить визуальное разделение на фронтенде")
    print("   - Улучшить промпт для AI, чтобы явно указывать тип единицы")
    
    # Сохраняем детальный отчет в JSON
    report_file = Path("/app/scripts/lab_analysis_report.json") if os.path.exists("/.dockerenv") else project_root / "backend" / "scripts" / "lab_analysis_report.json"
    report = {
        "user_id": user_id,
        "total_documents": selected_user["doc_count"],
        "total_labs": len(all_labs),
        "problematic_tests": {
            name: {
                "units": list(units),
                "count": len(test_name_to_labs[name])
            }
            for name, units in problematic_tests.items()
        },
        "percentage_tests": {
            name: len(labs)
            for name, labs in percentage_by_test.items()
        },
        "mixed_tests": {
            name: {
                "units": list(units),
                "count": len(test_name_to_labs[name])
            }
            for name, units in mixed_tests.items()
        },
        "unit_statistics": dict(sorted(unit_stats.items(), key=lambda x: x[1], reverse=True)),
        "null_unit_count": null_unit_count
    }
    
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 Детальный отчет сохранен в: {report_file}")
    
    client.close()
    print("\n✅ Анализ завершен")


if __name__ == "__main__":
    asyncio.run(analyze_lab_units())

