#!/usr/bin/env python3
"""
Скрипт для проверки: логируются ли данные о потраченных токенах для каждого документа.

Подключение к БД — как в db-viewer: через .env.local из корня проекта.
Для локального Docker: localhost:27017 (MongoDB), localhost:5432 (PostgreSQL).

Запуск из корня проекта:
  python backend/scripts/check_llm_usage_stats.py

Или с явным env-file:
  export $(grep -v '^#' .env.local | xargs) && python backend/scripts/check_llm_usage_stats.py
"""

import os
import sys
from pathlib import Path

# Корень проекта (где лежит .env.local)
project_root = Path(__file__).resolve().parent.parent.parent
env_local = project_root / ".env.local"
if env_local.exists():
    from dotenv import load_dotenv
    load_dotenv(env_local, override=True)

# MONGODB_URL для локального Docker: хост localhost (скрипт на хосте подключается к exposed порту)
if not os.getenv("MONGODB_URL"):
    mongo_user = os.getenv("MONGO_INITDB_ROOT_USERNAME", "admin")
    mongo_pass = os.getenv("MONGO_PASSWORD", "mongodb_secure_pass")
    mongo_db = os.getenv("MONGO_INITDB_DATABASE", "medhistory")
    mongo_host = os.getenv("MONGO_HOST", "localhost")
    mongo_port = os.getenv("MONGO_PORT", "27017")
    os.environ["MONGODB_URL"] = f"mongodb://{mongo_user}:{mongo_pass}@{mongo_host}:{mongo_port}/{mongo_db}?authSource=admin"

# Добавляем backend в path для импорта настроек
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from pymongo import MongoClient


def main():
    from app.core.config import settings

    # timeout для быстрого fail при недоступности MongoDB
    client = MongoClient(settings.MONGODB_URL, serverSelectionTimeoutMS=5000)
    db = client.medhistory
    coll = db.document_metadata

    print("=" * 60)
    print("🔍 ПРОВЕРКА: Логируются ли токены LLM для документов?")
    print("=" * 60)

    # Общее количество документов
    total = coll.count_documents({})
    print(f"\n📊 Всего документов в document_metadata: {total}")

    if total == 0:
        print("\n⚠️  Коллекция пуста. Нет данных для анализа.")
        return

    # Получить один документ и посмотреть структуру ai_response
    sample = coll.find_one({}, {"ai_response": 1, "ai_response_labs": 1})
    print("\n📋 Структура ai_response (классификация):")
    if sample and "ai_response" in sample:
        for k, v in sample["ai_response"].items():
            print(f"   - {k}: {v}")
        if "usage" not in sample["ai_response"] and "prompt_tokens" not in str(sample["ai_response"]):
            print("   ❌ НЕТ полей: prompt_tokens, completion_tokens, total_tokens")
    else:
        print("   (пусто или отсутствует)")

    print("\n📋 Структура ai_response_labs (извлечение анализов):")
    if sample and "ai_response_labs" in sample:
        for k, v in sample["ai_response_labs"].items():
            print(f"   - {k}: {v}")
        if "usage" not in str(sample.get("ai_response_labs", {})):
            print("   ❌ НЕТ полей: prompt_tokens, completion_tokens, total_tokens")
    else:
        print("   (пусто или отсутствует)")

    # Агрегация: сколько документов имеют ai_response, ai_response_labs
    pipeline = [
        {
            "$facet": {
                "with_ai_response": [
                    {"$match": {"ai_response": {"$exists": True, "$ne": None}}},
                    {"$count": "n"},
                ],
                "with_ai_response_labs": [
                    {"$match": {"ai_response_labs": {"$exists": True, "$ne": None}}},
                    {"$count": "n"},
                ],
                "with_usage_in_ai_response": [
                    {
                        "$match": {
                            "$or": [
                                {"ai_response.usage": {"$exists": True}},
                                {"ai_response.prompt_tokens": {"$exists": True}},
                            ]
                        }
                    },
                    {"$count": "n"},
                ],
            }
        }
    ]
    n_ai = n_labs = n_usage = 0
    result = list(coll.aggregate(pipeline))
    if result:
        r = result[0]
        n_ai = r["with_ai_response"][0]["n"] if r["with_ai_response"] else 0
        n_labs = r["with_ai_response_labs"][0]["n"] if r["with_ai_response_labs"] else 0
        n_usage = r["with_usage_in_ai_response"][0]["n"] if r["with_usage_in_ai_response"] else 0

        print("\n📈 Статистика:")
        print(f"   - Документов с ai_response: {n_ai}")
        print(f"   - Документов с ai_response_labs: {n_labs}")
        print(f"   - Документов с usage/tokens в ai_response: {n_usage}")

    # Вывод: есть ли вообще токены
    print("\n" + "=" * 60)
    if total > 0 and n_usage == 0:
        print("❌ ВЫВОД: Данные о потраченных токенах НЕ логируются.")
        print("   OpenRouter возвращает usage в ответе, но мы его не сохраняем в MongoDB.")
        print("   Рекомендация: добавить извлечение и сохранение usage при обработке.")
    elif total > 0 and n_usage > 0:
        print("✅ ВЫВОД: Данные о токенах логируются.")
        print("   Можно собрать статистику по реальным затратам.")
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        print("\nПроверьте:")
        print("  1. Docker запущен: docker compose up -d")
        print("  2. .env.local в корне проекта с MONGO_PASSWORD, MONGO_INITDB_ROOT_USERNAME")
        print("  3. MongoDB слушает на localhost:27017 (порт проброшен из контейнера)")
        sys.exit(1)
