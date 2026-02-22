#!/usr/bin/env python3
"""
Диагностика: почему маппинг "Абсолютное количество эозинофилов" не работает на экране Анализы.

Запуск:
  # Для локальной конфигурации:
  python scripts/diagnose_analyte_mapping.py --search "эозинофил"
  
  # Для production (требует PROD_* переменные):
  PROD_PG_PASSWORD=... PROD_MONGO_PASSWORD=... python scripts/diagnose_analyte_mapping.py --search "эозинофил" --prod
"""

import argparse
import os
import sys
from pathlib import Path

# Add project root
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

# For production
if os.getenv("USE_PROD") or "--prod" in sys.argv:
    prod_env = project_root / ".env.production"
    if prod_env.exists():
        try:
            from dotenv import load_dotenv
            load_dotenv(prod_env)
        except ImportError:
            pass


def get_pg_config(prod: bool):
    if prod:
        return {
            "host": os.getenv("PROD_PG_HOST", "localhost"),
            "port": int(os.getenv("PROD_PG_PORT", "15432")),  # SSH tunnel
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
        return {
            "host": "localhost",
            "port": int(os.getenv("PROD_MONGO_PORT", "17017")),  # SSH tunnel
            "user": os.getenv("PROD_MONGO_USER", "admin"),
            "password": os.getenv("PROD_MONGO_PASSWORD", ""),
            "db": os.getenv("PROD_MONGO_DB", "medhistory"),
        }
    return {
        "host": os.getenv("MONGO_HOST", "localhost"),
        "port": int(os.getenv("MONGODB_PORT", os.getenv("MONGO_PORT", "27017"))),
        "user": os.getenv("MONGO_INITDB_ROOT_USERNAME", "admin"),
        "password": os.getenv("MONGO_PASSWORD", ""),
        "db": os.getenv("MONGO_INITDB_DATABASE", "medhistory"),
    }


def main():
    parser = argparse.ArgumentParser(description="Диагностика маппинга анализов")
    parser.add_argument("--search", default="эозинофил", help="Подстрока для поиска в названиях")
    parser.add_argument("--prod", action="store_true", help="Использовать production (SSH туннель)")
    args = parser.parse_args()

    if args.prod:
        os.environ["USE_PROD"] = "1"
        print("⚠️  Режим Production: убедитесь, что SSH туннель к проду запущен (db-viewer в режиме Production)")
        print()

    env = "Production" if args.prod else "Local"
    print("=" * 70)
    print(f"Диагностика маппинга анализов [{env}]")
    print("=" * 70)
    print(f"Поиск: '{args.search}'")
    print()

    # 1. MongoDB: какие (test_name, unit) есть в документах
    try:
        from pymongo import MongoClient
        from urllib.parse import quote_plus

        mc = get_mongo_config(args.prod)
        url = f"mongodb://{quote_plus(mc['user'])}:{quote_plus(mc['password'])}@{mc['host']}:{mc['port']}/?authSource=admin"
        client = MongoClient(url)
        db = client[mc["db"]]
        coll = db["document_metadata"]

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
            {"$match": {"_id.name_lower": {"$regex": args.search.lower(), "$options": "i"}}},
            {"$sort": {"name": 1}},
        ]
        rows = list(coll.aggregate(pipeline))
        client.close()

        print("📋 MongoDB — названия анализов в документах (содержат '{0}'):".format(args.search))
        if not rows:
            print("   (не найдено)")
        else:
            for r in rows:
                name = (r.get("name") or "")
                unit = r.get("unit") or ""
                count = r.get("count", 0)
                repr_name = repr(name)  # Показать точную строку (пробелы, unicode)
                print(f"   • {repr_name} | unit={repr(unit)} | count={count}")

        print()
    except Exception as e:
        print(f"❌ MongoDB: {e}")
        print()

    # 2. PostgreSQL: какие синонимы есть для эталонов с "эозин"
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor

        pg = get_pg_config(args.prod)
        conn = psycopg2.connect(**pg)

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT a.canonical_name, s.synonym, s.synonym_lower
                FROM analyte_synonyms s
                JOIN analyte_standards a ON a.id = s.analyte_id
                WHERE s.synonym_lower LIKE %s OR a.canonical_name ILIKE %s
                ORDER BY a.canonical_name, s.synonym
            """, (f"%{args.search.lower()}%", f"%{args.search}%"))
            synonyms_rows = cur.fetchall()

        print("📋 PostgreSQL — синонимы в analyte_synonyms (содержат '{0}'):".format(args.search))
        if not synonyms_rows:
            print("   (не найдено — маппинг не добавлен или в другом окружении)")
        else:
            for r in synonyms_rows:
                print(f"   • synonym={repr(r['synonym'])} → canonical={r['canonical_name']}")

        conn.close()
        print()
    except Exception as e:
        print(f"❌ PostgreSQL: {e}")
        print()

    # 3. Проверка: будет ли match при get_canonical_name
    print("🔍 Проверка соответствия:")
    if rows and synonyms_rows:
        synonym_lower_set = {r["synonym_lower"] for r in synonyms_rows}
        for r in rows:
            name = (r.get("name") or "").strip()
            name_lower = name.lower()
            unit = r.get("unit") or ""
            if name_lower in synonym_lower_set:
                print(f"   ✅ '{name}' (unit={unit}) → найдено в synonym_lower")
            else:
                print(f"   ❌ '{name}' (unit={unit}) → НЕ найдено в synonym_lower")
                print(f"      Точная строка: {repr(name)}")
    else:
        print("   (недостаточно данных для проверки)")

    print()
    print("Рекомендации:")
    print("1. Если в MongoDB другая строка — добавьте маппинг для ТОЧНОГО названия из документа")
    print("2. Убедитесь, что маппинг добавлен в том же окружении (Local/Production), что и приложение")
    print("3. После добавления маппинга: обновите страницу Анализы (F5) или переключите вкладку и обратно")
    print("4. Для production: нажмите «Обновить кэш backend» в db-viewer или перезапустите backend")
    print("=" * 70)


if __name__ == "__main__":
    main()
