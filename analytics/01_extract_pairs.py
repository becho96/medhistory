"""
Шаг 1: Выгрузка всех уникальных (test_name, unit, count) из MongoDB.

Читает все документы из коллекции document_metadata, разворачивает
extracted_data.lab_results и группирует по (test_name, unit) с подсчётом.

Вывод: analytics/pairs.json — список пар, отсортированных по убыванию count.
"""

import asyncio
import json
import os

from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URL = os.environ.get(
    "MONGODB_URL",
    "mongodb://admin:mongodb_secure_pass@mongodb:27017/medhistory?authSource=admin"
)
MONGO_DB = os.environ.get("MONGO_DB", "medhistory")
OUTPUT_PATH = "/analytics/pairs.json"


async def main():
    print("📦 Подключаюсь к MongoDB...")
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[MONGO_DB]
    col = db["document_metadata"]

    pipeline = [
        {"$unwind": "$extracted_data.lab_results"},
        {
            "$group": {
                "_id": {
                    "test_name": "$extracted_data.lab_results.test_name",
                    "unit": "$extracted_data.lab_results.unit"
                },
                "count": {"$sum": 1}
            }
        },
        {"$sort": {"count": -1}}
    ]

    pairs = []
    async for doc in col.aggregate(pipeline):
        test_name = (doc["_id"].get("test_name") or "").strip()
        unit = (doc["_id"].get("unit") or "").strip()
        count = doc["count"]
        if not test_name:
            continue
        pairs.append({"test_name": test_name, "unit": unit, "count": count})

    client.close()

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(pairs, f, ensure_ascii=False, indent=2)

    print(f"✅ Выгружено {len(pairs)} уникальных пар → {OUTPUT_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
