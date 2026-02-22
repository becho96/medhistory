#!/usr/bin/env python3
"""
Диагностика: почему "Абсолютное количество нейтрофилов" не отображается на графике
при выборе "Нейтрофилы (абс)" на экране "Анализы".

Запуск из корня проекта:
  cd backend && python -m scripts.diagnose_timeseries_mapping
  # или с указанием email/файла:
  python -m scripts.diagnose_timeseries_mapping --email becho15rus@gmail.com --doc "Клинический анализ крови"
"""

import argparse
import os
import re
import sys
from pathlib import Path

# Добавляем backend в path для импортов
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

# Загрузка .env
env_path = backend_dir.parent / ".env.local"
if env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(env_path)

import psycopg2
from psycopg2.extras import RealDictCursor
from pymongo import MongoClient
from urllib.parse import quote_plus


def get_pg_conn():
    return psycopg2.connect(
        host=os.getenv("PG_HOST", "localhost"),
        port=int(os.getenv("PG_PORT", "5432")),
        database=os.getenv("POSTGRES_DB", os.getenv("PG_DB", "medhistory")),
        user=os.getenv("POSTGRES_USER", os.getenv("PG_USER", "medhistory_user")),
        password=os.getenv("POSTGRES_PASSWORD", os.getenv("PG_PASSWORD", "medhistory_local_pass")),
    )


def get_mongo_client():
    user = os.getenv("MONGO_INITDB_ROOT_USERNAME", os.getenv("MONGO_USER", "admin"))
    password = os.getenv("MONGO_PASSWORD", "mongodb_secure_pass")
    host = os.getenv("MONGO_HOST", "localhost")
    port = int(os.getenv("MONGODB_PORT", os.getenv("MONGO_PORT", "27017")))
    db_name = os.getenv("MONGO_INITDB_DATABASE", os.getenv("MONGO_DB", "medhistory"))
    url = f"mongodb://{quote_plus(user)}:{quote_plus(password)}@{host}:{port}/?authSource=admin"
    return MongoClient(url)[db_name]


def main():
    parser = argparse.ArgumentParser(description="Диагностика маппинга анализов для графика")
    parser.add_argument("--email", default="becho15rus@gmail.com", help="Email пользователя")
    parser.add_argument("--doc", default="Клинический анализ крови", help="Подстрока в названии файла документа")
    parser.add_argument("--analyte", default="Нейтрофилы (абс)", help="Каноническое название анализа")
    parser.add_argument("--list-docs", action="store_true", help="Только показать документы пользователя и выйти")
    args = parser.parse_args()

    print("=" * 70)
    print("Диагностика: почему анализ не отображается на графике")
    print("=" * 70)
    print(f"Пользователь: {args.email}")
    print(f"Документ (подстрока): {args.doc}")
    print(f"Анализ: {args.analyte}")
    print()

    # 1. Найти user_id
    with get_pg_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT id, email FROM users WHERE email = %s", (args.email,))
            user_row = cur.fetchone()
    if not user_row:
        print(f"❌ Пользователь с email {args.email} не найден в PostgreSQL")
        return 1
    user_id = str(user_row["id"])
    print(f"✅ User ID: {user_id}")

    if args.list_docs:
        with get_pg_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """SELECT id, original_filename FROM documents WHERE user_id = %s::uuid ORDER BY id LIMIT 50""",
                    (user_id,),
                )
                docs = cur.fetchall()
        print(f"\nДокументы пользователя ({len(docs)} шт.):")
        for d in docs:
            print(f"  {d['original_filename']}")
        return 0

    # 2. Найти документ и document_id
    with get_pg_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """SELECT id, original_filename, mongodb_metadata_id FROM documents 
                   WHERE user_id = %s::uuid AND original_filename ILIKE %s""",
                (user_id, f"%{args.doc}%"),
            )
            docs = cur.fetchall()
        if not docs and "Клинич" in args.doc:
            # Fallback: возможна разница Unicode (и/і и т.п.)
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """SELECT id, original_filename, mongodb_metadata_id FROM documents 
                       WHERE user_id = %s::uuid AND (original_filename ILIKE %s OR original_filename ILIKE %s)""",
                    (user_id, "%5 Diff%", "%анализ крови%"),
                )
                docs = cur.fetchall()
    if not docs:
        print(f"❌ Документы с подстрокой '{args.doc}' не найдены")
        with get_pg_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """SELECT id, original_filename FROM documents WHERE user_id = %s::uuid LIMIT 20""",
                    (user_id,),
                )
                all_docs = cur.fetchall()
        if all_docs:
            print("   Документы пользователя (примеры):")
            for d in all_docs:
                print(f"     - {repr(d['original_filename'])}")
        return 1
    doc_ids = [str(d["id"]) for d in docs]
    print(f"✅ Найдено документов: {len(docs)}")
    for d in docs:
        print(f"   - {d['original_filename']} (id={d['id']}, mongo_id={d.get('mongodb_metadata_id')})")

    # 3. Получить lab_results из MongoDB
    mongo = get_mongo_client()
    coll = mongo.document_metadata

    query = {"user_id": user_id}
    if doc_ids:
        query["document_id"] = {"$in": doc_ids}
    meta_docs = list(coll.find(query, {"document_id": 1, "extracted_data.lab_results": 1}))

    if not meta_docs:
        print(f"❌ Записей document_metadata для user_id={user_id} не найдено")
        return 1

    # Собрать все lab_results, ищем нейтрофилы
    neutrophil_entries = []
    for m in meta_docs:
        lrs = m.get("extracted_data", {}).get("lab_results", [])
        if not isinstance(lrs, list):
            continue
        for lr in lrs:
            if not isinstance(lr, dict):
                continue
            tn = (lr.get("test_name") or "").strip()
            tn_lower = tn.lower()
            if "нейтрофил" in tn_lower or "neutrophil" in tn_lower:
                neutrophil_entries.append({
                    "document_id": m.get("document_id"),
                    "test_name": tn,
                    "test_name_repr": repr(tn),
                    "value": lr.get("value"),
                    "unit": lr.get("unit"),
                })

    if not neutrophil_entries:
        print("❌ Записей с 'нейтрофил' в test_name в lab_results не найдено")
        print("   Доступные test_name в документах:")
        seen = set()
        for m in meta_docs:
            for lr in (m.get("extracted_data", {}).get("lab_results") or []):
                if isinstance(lr, dict):
                    tn = lr.get("test_name", "")
                    if tn and tn not in seen:
                        seen.add(tn)
        for t in sorted(seen):
            print(f"     - {repr(t)}")
        return 1

    print(f"✅ Найдено записей с нейтрофилами: {len(neutrophil_entries)}")
    for e in neutrophil_entries:
        print(f"   test_name={e['test_name_repr']}, value={e['value']}, unit={e['unit']}")

    # 4. Синонимы из analyte_synonyms для "Нейтрофилы (абс)"
    with get_pg_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT s.synonym, s.synonym_lower 
                FROM analyte_synonyms s
                JOIN analyte_standards a ON a.id = s.analyte_id
                WHERE a.canonical_name = %s
                """,
                (args.analyte,),
            )
            synonyms_rows = cur.fetchall()
    synonyms = [r["synonym"] for r in synonyms_rows] if synonyms_rows else []
    synonym_lower_set = {r["synonym_lower"] for r in synonyms_rows} if synonyms_rows else set()

    if not synonyms:
        print(f"\n❌ В analyte_synonyms нет синонимов для '{args.analyte}'")
        print("   Добавьте синонимы через db-viewer или напрямую в БД")
        return 1

    print(f"\n✅ Синонимов для '{args.analyte}': {len(synonyms)}")
    has_abs_count = "абсолютное количество нейтрофилов" in synonym_lower_set
    if has_abs_count:
        print(f"   ✅ 'Абсолютное количество нейтрофилов' ЕСТЬ в синонимах")
    else:
        print(f"   ❌ 'Абсолютное количество нейтрофилов' ОТСУТСТВУЕТ в синонимах")
    print(f"   Примеры: {synonyms[:10]}...")

    # 5. Проверка совпадения regex
    escaped = [re.escape(s) for s in synonyms]
    regex_pattern = f"^({'|'.join(escaped)})$"
    print(f"\n📋 Regex для поиска: {regex_pattern[:120]}...")

    for e in neutrophil_entries:
        tn = e["test_name"]
        match = bool(re.match(regex_pattern, tn, re.IGNORECASE))
        status = "✅" if match else "❌"
        print(f"   {status} test_name={repr(tn)} -> match={match}")

    # 6. unit_conversions для "Нейтрофилы (абс)"
    with get_pg_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT uc.from_unit, uc.from_unit_lower, uc.coefficient 
                FROM unit_conversions uc
                JOIN analyte_standards a ON a.id = uc.analyte_id
                WHERE a.canonical_name = %s
                """,
                (args.analyte,),
            )
            conversions = cur.fetchall()
    conv_map = {r["from_unit"]: r["coefficient"] for r in conversions}
    conv_map_lower = {r["from_unit_lower"]: r["coefficient"] for r in conversions}

    print(f"\n📋 unit_conversions для '{args.analyte}': {list(conv_map.keys())}")

    for e in neutrophil_entries:
        u = (e.get("unit") or "").strip()
        can_convert = (
            u in conv_map or
            (u.lower() in conv_map_lower)
        ) or not u
        status = "✅" if can_convert else "❌"
        print(f"   {status} unit={repr(u)} -> конвертируема={can_convert}")

    # 7. Фильтр % для абсолютного анализа
    print("\n📋 Фильтр unit по % (для абс анализов отбрасываем unit с %):")
    for e in neutrophil_entries:
        u = (e.get("unit") or "")
        has_percent = "%" in u
        skip = has_percent  # для "Нейтрофилы (абс)" записи с % пропускаются
        status = "⏭️ отбросится" if skip else "✅ пройдёт"
        print(f"   unit={repr(u)}, contains %={has_percent} -> {status}")

    # Итог
    print("\n" + "=" * 70)
    print("ВЫВОД")
    print("=" * 70)
    problems = []
    if not has_abs_count:
        problems.append(
            "1. Добавьте синоним 'Абсолютное количество нейтрофилов' в analyte_synonyms "
            "для анализа 'Нейтрофилы (абс)' (через db-viewer или INSERT в БД)"
        )
    for e in neutrophil_entries:
        tn = e["test_name"]
        if not re.match(regex_pattern, tn, re.IGNORECASE):
            problems.append(
                f"2. test_name в MongoDB '{tn}' не совпадает ни с одним синонимом. "
                f"Возможны лишние пробелы или другой регистр. "
                f"Добавьте точное значение как синоним или проверьте извлечение AI."
            )
            break
    for e in neutrophil_entries:
        u = (e.get("unit") or "").strip()
        if "%" in u:
            problems.append(
                f"3. Unit содержит '%' — для абсолютного анализа такие записи отбрасываются. "
                f"Проверьте, не перепутало ли AI единицы."
            )
            break
    for e in neutrophil_entries:
        u = (e.get("unit") or "").strip()
        if u and u not in conv_map and u.lower() not in conv_map_lower:
            problems.append(
                f"4. Unit '{u}' отсутствует в unit_conversions — convert_value вернёт None, "
                f"точка не попадёт на график. Добавьте конверсию в unit_conversions."
            )
            break

    if problems:
        for p in problems:
            print(f"⚠️  {p}")
        print("\nПосле исправления перезагрузите кэш: POST /api/v1/internal/analytes/reload")
    else:
        print("Все проверки пройдены. Если график пуст, проверьте кэш бэкенда (reload analytes).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
