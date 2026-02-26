#!/usr/bin/env python3
"""
Экспорт уникальных комбинаций (test_name, unit, reference_range) из MongoDB.

Запуск:
  cd backend && python -m scripts.export_unique_lab_combinations
  python -m scripts.export_unique_lab_combinations -o -  # stdout
  # Production по SSH:
  ./scripts/export_unique_lab_combinations_prod.sh
"""

import argparse
import csv
import os
import sys
from pathlib import Path

_script_dir = Path(__file__).resolve().parent
# Корень проекта: scripts/ -> parent; backend/scripts/ -> parent.parent
project_root = _script_dir.parent if _script_dir.name == "scripts" else _script_dir.parent.parent
sys.path.insert(0, str(project_root))

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


def get_mongo_config(prod: bool):
    # MONGODB_URL имеет приоритет (используется в Docker)
    url = os.getenv("MONGODB_URL")
    if url:
        return {"url": url}
    if prod:
        return {
            "host": "localhost",
            "port": int(os.getenv("PROD_MONGO_PORT", "17017")),
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
    parser = argparse.ArgumentParser(description="Экспорт уникальных комбинаций (test_name, unit, reference_range) в CSV")
    parser.add_argument("--prod", action="store_true", help="Использовать production (SSH туннель)")
    parser.add_argument("-o", "--output", default="unique_lab_combinations.csv", help="Путь к выходному CSV (- для stdout)")
    args = parser.parse_args()

    if args.prod:
        os.environ["USE_PROD"] = "1"
        print("⚠️  Режим Production: убедитесь, что SSH туннель к Mongo запущен")
        print()

    print("=" * 70, file=sys.stderr)
    print("Экспорт уникальных комбинаций (test_name, unit, reference_range)", file=sys.stderr)
    print("=" * 70, file=sys.stderr)

    try:
        from pymongo import MongoClient
        from urllib.parse import quote_plus

        mc = get_mongo_config(args.prod)
        if "url" in mc:
            mongo_url = mc["url"]
            client = MongoClient(mongo_url)
            db_name = mongo_url.split("/")[-1].split("?")[0]
            db = client[db_name]
        else:
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
                    "test_name": {"$ifNull": ["$extracted_data.lab_results.test_name", ""]},
                    "unit": {"$ifNull": ["$extracted_data.lab_results.unit", ""]},
                    "reference_range": {"$ifNull": ["$extracted_data.lab_results.reference_range", ""]},
                },
                "count": {"$sum": 1},
            }},
            {"$sort": {"count": -1, "_id.test_name": 1, "_id.unit": 1}},
        ]

        rows = list(coll.aggregate(pipeline))
        total_unique = len(rows)

        output_path = Path(args.output)
        if str(output_path) == "-":
            import io
            f = io.StringIO()
            writer = csv.writer(f)
            writer.writerow(["test_name", "unit", "reference_range", "count"])
            for r in rows:
                writer.writerow([
                    r["_id"].get("test_name", ""),
                    r["_id"].get("unit", ""),
                    r["_id"].get("reference_range", ""),
                    r["count"],
                ])
            print(f.getvalue(), end="")
        else:
            with open(output_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["test_name", "unit", "reference_range", "count"])
                for r in rows:
                    writer.writerow([
                        r["_id"].get("test_name", ""),
                        r["_id"].get("unit", ""),
                        r["_id"].get("reference_range", ""),
                        r["count"],
                    ])

        if str(output_path) != "-":
            print(f"✅ Уникальных комбинаций (test_name, unit, reference_range): {total_unique}")
            print(f"✅ CSV сохранён: {output_path.resolve()}")
        else:
            print(f"✅ Уникальных комбинаций: {total_unique}", file=sys.stderr)

    except Exception as e:
        print(f"❌ Ошибка: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
