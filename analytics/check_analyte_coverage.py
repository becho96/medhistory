"""
Проверка покрытия анализов таблицей соответствий (analyte_synonyms).

Выгружает все уникальные (test_name, unit) из MongoDB lab_results,
затем проверяет, есть ли для каждой пары соответствие в analyte_synonyms
(используя ту же логику, что и AnalyteNormalizationServiceDB.get_canonical_name).

Результат сохраняется в analytics/results.json и выводится в консоль.
"""

import asyncio
import json
import os
from collections import defaultdict

import asyncpg
from motor.motor_asyncio import AsyncIOMotorClient


# ── подключения ────────────────────────────────────────────────────────────────

MONGO_URL = os.environ.get(
    "MONGODB_URL",
    "mongodb://admin:mongodb_secure_pass@mongodb:27017/medhistory?authSource=admin"
)
MONGO_DB = os.environ.get("MONGO_DB", "medhistory")

PG_DSN = os.environ.get(
    "DATABASE_URL",
    "postgresql://medhistory_user:medhistory_local_pass@postgres:5432/medhistory"
).replace("postgresql+asyncpg://", "postgresql://").replace("+asyncpg", "")


# ── шаг 1: уникальные пары из MongoDB ─────────────────────────────────────────

async def fetch_mongo_pairs(mongo_url: str, db_name: str) -> dict:
    """
    Возвращает словарь:
      (test_name_lower, unit_lower) → {
          "test_name": <оригинал>,
          "unit": <оригинал>,
          "count": <сколько раз встречается>
      }
    """
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
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

    pairs = {}
    async for doc in col.aggregate(pipeline):
        raw_name = (doc["_id"].get("test_name") or "").strip()
        raw_unit = (doc["_id"].get("unit") or "").strip()
        count    = doc["count"]
        if not raw_name:
            continue
        key = (raw_name.lower(), raw_unit.lower())
        pairs[key] = {"test_name": raw_name, "unit": raw_unit, "count": count}

    client.close()
    return pairs


# ── шаг 2: индекс синонимов из PostgreSQL ─────────────────────────────────────

async def fetch_pg_synonym_index(pg_dsn: str) -> dict:
    """
    Строит synonym_unit_index точно так же, как AnalyteNormalizationServiceDB:
      (synonym_lower, unit_lower) → canonical_name
    """
    conn = await asyncpg.connect(pg_dsn)

    rows = await conn.fetch("""
        SELECT
            s.synonym_lower,
            COALESCE(s.unit_lower, '') AS unit_lower,
            a.canonical_name
        FROM analyte_synonyms s
        JOIN analyte_standards a ON a.id = s.analyte_id
        JOIN analyte_categories c ON c.id = a.category_id
        WHERE a.is_active = TRUE AND c.is_active = TRUE
    """)

    index = {}
    for row in rows:
        key = (row["synonym_lower"], row["unit_lower"])
        index[key] = row["canonical_name"]

    await conn.close()
    return index


# ── шаг 3: проверка покрытия ───────────────────────────────────────────────────

def check_coverage(pairs: dict, index: dict) -> dict:
    """
    Возвращает структуру с:
      - matched:   список пар, для которых найдено соответствие
      - unmatched: список пар без соответствия
    """
    matched   = []
    unmatched = []

    for (name_lower, unit_lower), meta in sorted(pairs.items(), key=lambda x: -x[1]["count"]):
        # Логика get_canonical_name:
        # 1) точный поиск по (name_lower, unit_lower)
        # 2) fallback: (name_lower, "")
        canonical = index.get((name_lower, unit_lower)) or index.get((name_lower, ""))

        entry = {
            "test_name": meta["test_name"],
            "unit":      meta["unit"],
            "count":     meta["count"],
            "canonical": canonical,
        }

        if canonical:
            matched.append(entry)
        else:
            unmatched.append(entry)

    return {"matched": matched, "unmatched": unmatched}


# ── шаг 4: вывод и сохранение ─────────────────────────────────────────────────

def print_report(result: dict):
    matched   = result["matched"]
    unmatched = result["unmatched"]
    total     = len(matched) + len(unmatched)

    total_measurements_matched   = sum(e["count"] for e in matched)
    total_measurements_unmatched = sum(e["count"] for e in unmatched)
    total_measurements = total_measurements_matched + total_measurements_unmatched

    print("\n" + "="*70)
    print(f"ИТОГО уникальных пар (test_name, unit): {total}")
    print(f"  ✅ найдено соответствие: {len(matched)}")
    print(f"  ❌ нет соответствия:    {len(unmatched)}")
    pct_pairs = 100 * len(matched) / total if total else 0
    print(f"  Покрытие (пар):         {pct_pairs:.1f}%")
    print()
    print(f"ИТОГО измерений: {total_measurements}")
    print(f"  ✅ покрыто измерений:   {total_measurements_matched}")
    print(f"  ❌ не покрыто:          {total_measurements_unmatched}")
    pct_meas = 100 * total_measurements_matched / total_measurements if total_measurements else 0
    print(f"  Покрытие (измерений):   {pct_meas:.1f}%")
    print("="*70)

    if unmatched:
        print("\n❌ ПАРЫ БЕЗ СООТВЕТСТВИЯ (отсортировано по убыванию count):\n")
        print(f"  {'#':>3}  {'test_name':<45} {'unit':<15} {'count':>6}")
        print(f"  {'-'*3}  {'-'*45} {'-'*15} {'-'*6}")
        for i, e in enumerate(unmatched, 1):
            name = e['test_name'][:44]
            unit = (e['unit'] or '')[:14]
            print(f"  {i:>3}  {name:<45} {unit:<15} {e['count']:>6}")
    else:
        print("\n✅ Все пары покрыты таблицей соответствий!")

    print()


# ── main ───────────────────────────────────────────────────────────────────────

async def main():
    print("📦 Подключаюсь к MongoDB и выгружаю уникальные (test_name, unit)...")
    pairs = await fetch_mongo_pairs(MONGO_URL, MONGO_DB)
    print(f"   Найдено уникальных пар: {len(pairs)}")

    print("🗃️  Загружаю индекс синонимов из PostgreSQL...")
    index = await fetch_pg_synonym_index(PG_DSN)
    print(f"   Загружено синонимов: {len(index)}")

    print("🔍 Проверяю покрытие...")
    result = check_coverage(pairs, index)

    print_report(result)

    out_path = "/analytics/results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"💾 Полный результат сохранён в {out_path}\n")


if __name__ == "__main__":
    asyncio.run(main())
