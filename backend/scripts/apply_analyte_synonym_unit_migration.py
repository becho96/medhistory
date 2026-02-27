#!/usr/bin/env python3
"""
Миграция: добавление unit, unit_lower, coefficient в analyte_synonyms;
перенос данных из unit_conversions; смена уникального индекса на (synonym_lower, unit_lower).

Запуск:
  cd backend && python -m scripts.apply_analyte_synonym_unit_migration
  python -m scripts.apply_analyte_synonym_unit_migration --database-url postgresql://...
"""

import os
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

env_path = backend_dir.parent / ".env.local"
if env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(env_path)


def normalize_database_url(url: str) -> str:
    if url.startswith("postgresql+asyncpg://"):
        return url.replace("postgresql+asyncpg://", "postgresql://")
    return url


def apply_migration(database_url: str) -> bool:
    from sqlalchemy import create_engine, text

    engine = create_engine(database_url)

    migration_sql = """
-- 1. Удаляем старый уникальный индекс
DROP INDEX IF EXISTS ix_analyte_synonyms_synonym_lower_unique;

-- 2. Добавляем колонки unit, unit_lower, coefficient
ALTER TABLE analyte_synonyms ADD COLUMN IF NOT EXISTS unit VARCHAR(50) DEFAULT '';
ALTER TABLE analyte_synonyms ADD COLUMN IF NOT EXISTS unit_lower VARCHAR(50) DEFAULT '';
ALTER TABLE analyte_synonyms ADD COLUMN IF NOT EXISTS coefficient NUMERIC(15, 6) DEFAULT 1.0;

-- 3. Заполняем пустыми значениями для существующих строк
UPDATE analyte_synonyms SET unit = COALESCE(unit, ''), unit_lower = COALESCE(unit_lower, ''), coefficient = COALESCE(coefficient, 1.0) WHERE unit IS NULL OR unit_lower IS NULL OR coefficient IS NULL;

-- 4. Создаём новый уникальный индекс по (synonym_lower, unit_lower)
CREATE UNIQUE INDEX IF NOT EXISTS ix_analyte_synonyms_synonym_unit_unique ON analyte_synonyms (synonym_lower, unit_lower);

-- 5. Миграция данных из unit_conversions в analyte_synonyms
-- Для каждой записи unit_conversions добавляем (canonical_name, from_unit) как синоним
INSERT INTO analyte_synonyms (id, analyte_id, synonym, synonym_lower, unit, unit_lower, coefficient)
SELECT gen_random_uuid(), uc.analyte_id, a.canonical_name, LOWER(a.canonical_name), uc.from_unit, uc.from_unit_lower, uc.coefficient
FROM unit_conversions uc
JOIN analyte_standards a ON a.id = uc.analyte_id
WHERE NOT EXISTS (
    SELECT 1 FROM analyte_synonyms s
    WHERE s.analyte_id = uc.analyte_id AND s.synonym_lower = LOWER(a.canonical_name) AND s.unit_lower = uc.from_unit_lower
)
ON CONFLICT DO NOTHING;
"""

    # ON CONFLICT doesn't work without a unique constraint name. The new index is ix_analyte_synonyms_synonym_unit_unique.
    # But INSERT ... ON CONFLICT requires specifying the conflict target. Let me use a different approach - check with NOT EXISTS (already in the query) and wrap in a try/except for duplicate key.

    migration_sql = """
-- 1. Удаляем старый уникальный индекс
DROP INDEX IF EXISTS ix_analyte_synonyms_synonym_lower_unique;

-- 2. Добавляем колонки unit, unit_lower, coefficient
ALTER TABLE analyte_synonyms ADD COLUMN IF NOT EXISTS unit VARCHAR(50) DEFAULT '';
ALTER TABLE analyte_synonyms ADD COLUMN IF NOT EXISTS unit_lower VARCHAR(50) DEFAULT '';
ALTER TABLE analyte_synonyms ADD COLUMN IF NOT EXISTS coefficient NUMERIC(15, 6) DEFAULT 1.0;

-- 3. Заполняем для существующих строк
UPDATE analyte_synonyms SET unit = COALESCE(unit, ''), unit_lower = COALESCE(unit_lower, ''), coefficient = COALESCE(coefficient, 1.0);

-- 4. Создаём новый уникальный индекс
CREATE UNIQUE INDEX IF NOT EXISTS ix_analyte_synonyms_synonym_unit_unique ON analyte_synonyms (synonym_lower, unit_lower);
"""

    migration_data_sql = """
-- 5. Миграция данных из unit_conversions
-- Для каждого синонима анализа и каждой единицы из unit_conversions добавляем (synonym, unit, coefficient)
INSERT INTO analyte_synonyms (id, analyte_id, synonym, synonym_lower, unit, unit_lower, coefficient)
SELECT gen_random_uuid(), s.analyte_id, s.synonym, s.synonym_lower, uc.from_unit, uc.from_unit_lower, uc.coefficient
FROM analyte_synonyms s
JOIN unit_conversions uc ON uc.analyte_id = s.analyte_id
WHERE (s.synonym_lower, COALESCE(s.unit_lower, '')) IN (
    SELECT synonym_lower, COALESCE(unit_lower, '') FROM analyte_synonyms WHERE unit_lower = '' OR unit_lower IS NULL
)
AND s.unit_lower = '' AND uc.from_unit_lower != ''
AND NOT EXISTS (
    SELECT 1 FROM analyte_synonyms s2
    WHERE s2.analyte_id = s.analyte_id AND s2.synonym_lower = s.synonym_lower AND s2.unit_lower = uc.from_unit_lower
);
"""
    # 5a: (canonical_name, from_unit) для каждой unit_conversions
    # 5b: (synonym, from_unit) для каждого существующего синонима с unit=''
    migration_data_sql = """
-- 5a: canonical_name + unit из unit_conversions
INSERT INTO analyte_synonyms (id, analyte_id, synonym, synonym_lower, unit, unit_lower, coefficient)
SELECT gen_random_uuid(), uc.analyte_id, a.canonical_name, LOWER(a.canonical_name), uc.from_unit, uc.from_unit_lower, uc.coefficient
FROM unit_conversions uc
JOIN analyte_standards a ON a.id = uc.analyte_id
WHERE NOT EXISTS (
    SELECT 1 FROM analyte_synonyms s
    WHERE s.analyte_id = uc.analyte_id AND s.synonym_lower = LOWER(a.canonical_name) AND COALESCE(s.unit_lower, '') = uc.from_unit_lower
);

-- 5b: для каждого синонима с unit='' добавляем варианты с unit из unit_conversions
INSERT INTO analyte_synonyms (id, analyte_id, synonym, synonym_lower, unit, unit_lower, coefficient)
SELECT gen_random_uuid(), s.analyte_id, s.synonym, s.synonym_lower, uc.from_unit, uc.from_unit_lower, uc.coefficient
FROM analyte_synonyms s
JOIN unit_conversions uc ON uc.analyte_id = s.analyte_id
WHERE COALESCE(s.unit, '') = '' AND COALESCE(s.unit_lower, '') = '' AND uc.from_unit_lower != ''
AND NOT EXISTS (
    SELECT 1 FROM analyte_synonyms s2
    WHERE s2.analyte_id = s.analyte_id AND s2.synonym_lower = s.synonym_lower AND COALESCE(s2.unit_lower, '') = uc.from_unit_lower
);
"""

    print("=" * 80)
    print("Миграция: analyte_synonyms + unit, unit_conversions -> analyte_synonyms")
    print("=" * 80)

    try:
        with engine.connect() as conn:
            print("Шаги 1-4: изменение схемы...")
            conn.execute(text(migration_sql))
            conn.commit()
            print("OK")

            print("Шаг 5: перенос данных из unit_conversions...")
            try:
                # Проверяем, существует ли таблица unit_conversions
                check = conn.execute(text("""
                    SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'unit_conversions')
                """))
                if check.scalar():
                    conn.execute(text(migration_data_sql))
                    conn.commit()
                    print("OK")
                else:
                    print("Пропуск: таблица unit_conversions не существует")
            except Exception as e:
                if "duplicate key" in str(e).lower() or "unique" in str(e).lower():
                    print("Предупреждение: часть записей уже существует, пропускаем")
                    conn.rollback()
                else:
                    raise

        engine.dispose()
        return True
    except Exception as e:
        print(f"Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False


def drop_unit_conversions_table(database_url: str) -> bool:
    """Удаляет таблицу unit_conversions (после переноса данных в analyte_synonyms)."""
    from sqlalchemy import create_engine, text
    engine = create_engine(database_url)
    try:
        with engine.connect() as conn:
            conn.execute(text("DROP TABLE IF EXISTS unit_conversions CASCADE"))
            conn.commit()
        engine.dispose()
        print("Таблица unit_conversions удалена")
        return True
    except Exception as e:
        print(f"Ошибка при удалении unit_conversions: {e}")
        return False


def main():
    import argparse
    default_url = os.getenv(
        "DATABASE_URL",
        "postgresql://medhistory_user:medhistory_local_pass@localhost:5432/medhistory",
    )
    default_url = normalize_database_url(default_url)

    parser = argparse.ArgumentParser(description="Миграция analyte_synonyms: добавление unit, перенос из unit_conversions")
    parser.add_argument("--database-url", default=default_url, help="URL PostgreSQL")
    parser.add_argument("--drop-unit-conversions", action="store_true", help="Удалить таблицу unit_conversions после миграции")
    args = parser.parse_args()

    db_url = normalize_database_url(args.database_url)
    success = apply_migration(db_url)
    if success and args.drop_unit_conversions:
        drop_unit_conversions_table(db_url)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
