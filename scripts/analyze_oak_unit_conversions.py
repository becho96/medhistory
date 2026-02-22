#!/usr/bin/env python3
"""
Анализ: каких записей не хватает в unit_conversions для 8 анализов ОАК.

Запуск локально (с .env.local):
  python scripts/analyze_oak_unit_conversions.py

Запуск на production (с .env.production):
  1. Сначала поднять SSH туннель:
     ssh -L 15432:localhost:5432 -L 17017:localhost:27017 -l yc-user 93.77.182.26 -N
  2. В другом терминале:
     python scripts/analyze_oak_unit_conversions.py --prod

  Или на сервере напрямую (без туннеля):
     ssh -l yc-user 93.77.182.26 'cd ~/medhistory && PROD_PG_PORT=5432 PROD_MONGO_PORT=27017 python3 scripts/analyze_oak_unit_conversions.py --prod'
"""

import argparse
import os
import sys
from pathlib import Path
from collections import defaultdict

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# Load env
env_file = project_root / ".env.local"
if env_file.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(env_file)
    except ImportError:
        pass

if os.getenv("USE_PROD") or "--prod" in sys.argv:
    prod_env = project_root / ".env.production"
    if prod_env.exists():
        try:
            from dotenv import load_dotenv
            load_dotenv(prod_env)
        except ImportError:
            pass


# 8 анализов ОАК (последние добавленные синонимы)
OAK_ANALYTES = [
    "Эозинофилы (абс)",
    "Лимфоциты (%)",
    "Моноциты (%)",
    "Нейтрофилы (%)",
    "Базофилы (абс)",
    "Моноциты (абс)",
    "Нейтрофилы (абс)",
    "Лимфоциты (абс)",
]

# Синонимы из документов, маппящиеся на эти анализы (из analyte_synonyms)
OAK_SYNONYM_SUBSTRINGS = [
    "эозинофил", "лимфоцит", "моноцит", "нейтрофил", "базофил",
    "абсолютное количество", "относительное количество",
]


def get_pg_config(prod: bool):
    if prod:
        # По умолчанию порты туннеля 15432/17017 (как в db-viewer Production)
        host = os.getenv("PROD_PG_HOST", "localhost")
        port = int(os.getenv("PROD_PG_PORT", "15432"))
        return {
            "host": host,
            "port": port,
            "database": os.getenv("PROD_PG_DB", "medhistory"),
            "user": os.getenv("PROD_PG_USER", "medhistory_user"),
            "password": os.getenv("PROD_PG_PASSWORD", ""),
        }
    return {
        "host": os.getenv("PG_HOST", "localhost"),
        "port": int(os.getenv("PG_PORT", "5432")),
        "database": os.getenv("POSTGRES_DB", os.getenv("PG_DB", "medhistory")),
        "user": os.getenv("POSTGRES_USER", os.getenv("PG_USER", "medhistory_user")),
        "password": os.getenv("POSTGRES_PASSWORD", os.getenv("PG_PASSWORD", "")),
    }


def get_mongo_config(prod: bool):
    if prod:
        port = int(os.getenv("PROD_MONGO_PORT", "17017"))
        return {
            "host": "localhost",
            "port": port,
            "user": os.getenv("PROD_MONGO_USER", os.getenv("MONGO_INITDB_ROOT_USERNAME", "admin")),
            "password": os.getenv("PROD_MONGO_PASSWORD", os.getenv("MONGO_PASSWORD", "")),
            "db": os.getenv("PROD_MONGO_DB", os.getenv("MONGO_INITDB_DATABASE", "medhistory")),
        }
    return {
        "host": os.getenv("MONGO_HOST", "localhost"),
        "port": int(os.getenv("MONGODB_PORT", os.getenv("MONGO_PORT", "27017"))),
        "user": os.getenv("MONGO_INITDB_ROOT_USERNAME", "admin"),
        "password": os.getenv("MONGO_PASSWORD", ""),
        "db": os.getenv("MONGO_INITDB_DATABASE", os.getenv("MONGO_DB", "medhistory")),
    }


def main():
    parser = argparse.ArgumentParser(description="Анализ unit_conversions для ОАК")
    parser.add_argument("--prod", action="store_true", help="Production (на сервере или через туннель)")
    args = parser.parse_args()

    if args.prod:
        os.environ["USE_PROD"] = "1"

    prod = args.prod
    env_name = "Production" if prod else "Local"

    print("=" * 70)
    print(f"Анализ unit_conversions для 8 анализов ОАК [{env_name}]")
    print("=" * 70)
    print()

    # 1. PostgreSQL: analyte_standards для ОАК + их unit_conversions
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor

        pg = get_pg_config(prod)
        conn = psycopg2.connect(**pg)

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            placeholders = ",".join(["%s"] * len(OAK_ANALYTES))
            cur.execute("""
                SELECT a.id, a.canonical_name, a.standard_unit
                FROM analyte_standards a
                JOIN analyte_categories c ON c.id = a.category_id
                WHERE a.canonical_name IN ({0}) AND c.name ILIKE '%%общ%%'
            """.format(placeholders), OAK_ANALYTES)
            analytes = cur.fetchall()

        if not analytes:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT a.id, a.canonical_name, a.standard_unit
                    FROM analyte_standards a
                    WHERE a.canonical_name IN %s
                """, (tuple(OAK_ANALYTES),))
                analytes = cur.fetchall()

        analyte_ids = [str(a["id"]) for a in analytes]
        canonical_to_standard = {a["canonical_name"]: a["standard_unit"] for a in analytes}

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT uc.analyte_id, uc.from_unit, uc.from_unit_lower, uc.coefficient
                FROM unit_conversions uc
                WHERE uc.analyte_id = ANY(%s)
            """, (analyte_ids,))
            conversions = cur.fetchall()

        conn.close()

        # Группируем по canonical_name
        id_to_canonical = {str(a["id"]): a["canonical_name"] for a in analytes}
        existing_units: dict[str, set[str]] = defaultdict(set)
        for c in conversions:
            cn = id_to_canonical.get(str(c["analyte_id"]))
            if cn:
                existing_units[cn].add(c["from_unit"])
                existing_units[cn].add(c["from_unit_lower"])

        print("📋 PostgreSQL — 8 анализов ОАК и их unit_conversions:")
        for a in analytes:
            cn = a["canonical_name"]
            std = a["standard_unit"]
            units = sorted(existing_units.get(cn, set())) or ["(пусто)"]
            print(f"   • {cn} (standard: {std})")
            print(f"     Есть: {units}")
        print()

    except Exception as e:
        print(f"❌ PostgreSQL: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # 2. MongoDB: какие (test_name, unit) есть в документах для ОАК-подобных анализов
    try:
        from pymongo import MongoClient
        from urllib.parse import quote_plus

        mc = get_mongo_config(prod)
        url = f"mongodb://{quote_plus(mc['user'])}:{quote_plus(mc['password'])}@{mc['host']}:{mc['port']}/?authSource=admin"
        client = MongoClient(url)
        db = client[mc["db"]]
        coll = db["document_metadata"]

        # Собираем все test_name, unit для lab_results
        pipeline = [
            {"$match": {"extracted_data.lab_results": {"$exists": True, "$ne": []}}},
            {"$project": {"extracted_data.lab_results": 1}},
            {"$unwind": "$extracted_data.lab_results"},
            {"$group": {
                "_id": {
                    "name_lower": {"$toLower": {"$ifNull": ["$extracted_data.lab_results.test_name", ""]}},
                    "unit": {"$ifNull": ["$extracted_data.lab_results.unit", ""]}
                },
                "name": {"$first": "$extracted_data.lab_results.test_name"},
                "unit": {"$first": "$extracted_data.lab_results.unit"},
                "count": {"$sum": 1}
            }},
            {"$sort": {"name": 1}},
        ]
        all_rows = list(coll.aggregate(pipeline))

        # Фильтруем только те, что маппятся на ОАК (через synonym_lower из analyte_synonyms)
        pg2 = get_pg_config(prod)
        with psycopg2.connect(**pg2) as conn2:
            with conn2.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT s.synonym_lower, a.canonical_name
                    FROM analyte_synonyms s
                    JOIN analyte_standards a ON a.id = s.analyte_id
                    WHERE a.canonical_name IN %s
                """, (tuple(OAK_ANALYTES),))
                synonym_to_canonical = {r["synonym_lower"]: r["canonical_name"] for r in cur.fetchall()}

        mongo_oak_pairs = []
        for r in all_rows:
            name = (r.get("name") or "").strip()
            name_lower = name.lower()
            unit = (r.get("unit") or "").strip()
            if name_lower in synonym_to_canonical:
                mongo_oak_pairs.append({
                    "name": name,
                    "name_lower": name_lower,
                    "unit": unit,
                    "canonical": synonym_to_canonical[name_lower],
                    "count": r.get("count", 0),
                })

        client.close()

        print("📋 MongoDB — (test_name, unit) в документах, маппящиеся на ОАК:")
        if not mongo_oak_pairs:
            print("   (нет документов с lab_results или нет совпадений с analyte_synonyms)")
        else:
            seen = set()
            for p in mongo_oak_pairs:
                key = (p["name_lower"], p["unit"])
                if key not in seen:
                    seen.add(key)
                    print(f"   • {repr(p['name'])} | unit={repr(p['unit'])} → {p['canonical']} (count={p['count']})")
        print()

    except Exception as e:
        print(f"❌ MongoDB: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # 3. Сравнение: какие unit из MongoDB отсутствуют в unit_conversions
    print("🔍 Недостающие записи в unit_conversions:")
    print()

    missing_by_analyte: dict[str, set[str]] = defaultdict(set)
    for p in mongo_oak_pairs:
        cn = p["canonical"]
        unit = p["unit"]
        if not unit:
            continue
        existing = existing_units.get(cn, set())
        unit_lower = unit.lower()
        if unit not in existing and unit_lower not in existing:
            missing_by_analyte[cn].add(unit)

    if not missing_by_analyte:
        print("   ✅ Все единицы из документов уже есть в unit_conversions.")
    else:
        for cn in OAK_ANALYTES:
            if cn not in missing_by_analyte:
                continue
            std = canonical_to_standard.get(cn, "?")
            missing = sorted(missing_by_analyte[cn])
            print(f"   ❌ {cn} (standard: {std})")
            for u in missing:
                print(f"      Не хватает: {repr(u)}")
            print()

    # 4. Рекомендуемые записи для INSERT (с коэффициентами)
    print("=" * 70)
    print("📝 Рекомендуемые INSERT для unit_conversions:")
    print()

    # Коэффициенты: для %→% и вариантов 10^9→×10⁹ = 1.0
    # тыс/мкл = ×10⁹/л (1:1)
    UNIT_COEFFICIENTS = {
        "%": 1.0,
        "10*9/л": 1.0,
        "10^9/л": 1.0,
        "х10^9/л": 1.0,
        "×10⁹/л": 1.0,
        "тыс/мкл": 1.0,
        "10^9/л.": 1.0,
        "г/л": 1.0,
    }

    if missing_by_analyte:
        for a in analytes:
            cn = a["canonical_name"]
            aid = str(a["id"])
            if cn not in missing_by_analyte:
                continue
            for unit in sorted(missing_by_analyte[cn]):
                coef = UNIT_COEFFICIENTS.get(unit, 1.0)
                ul = unit.lower()
                print(f"   INSERT INTO unit_conversions (id, analyte_id, from_unit, from_unit_lower, coefficient)")
                print(f"   VALUES (gen_random_uuid(), '{aid}', {repr(unit)}, {repr(ul)}, {coef})")
                print(f"   ON CONFLICT (analyte_id, from_unit_lower) DO NOTHING;")
                print()
    else:
        print("   (дополнительных INSERT не требуется)")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
