"""
Шаг 3: Генерация SQL для перестройки analyte_standards + analyte_synonyms.

Читает groups_draft.json + текущие analyte_categories из PostgreSQL.
Генерирует analytics/generated/rebuild.sql — полный TRUNCATE + INSERT.

Важно: canonical_name также добавляется в analyte_synonyms с is_primary=TRUE,
т.к. analyte_normalization_service_db ищет по индексу синонимов (не по standards).
"""

import asyncio
import json
import os
import uuid
from pathlib import Path

import asyncpg

GROUPS_PATH = "/analytics/groups_draft.json"
OUTPUT_DIR = Path("/analytics/generated")
OUTPUT_PATH = OUTPUT_DIR / "rebuild.sql"

PG_DSN = (
    os.environ.get("DATABASE_URL", "")
    .replace("postgresql+asyncpg://", "postgresql://")
    .replace("+asyncpg", "")
    or "postgresql://medhistory_user:medhistory_local_pass@postgres:5432/medhistory"
)


# ── Загрузка категорий ────────────────────────────────────────────────────────

async def fetch_category_ids(pg_dsn: str) -> dict[str, str]:
    """Возвращает {category_name: category_id}"""
    conn = await asyncpg.connect(pg_dsn)
    rows = await conn.fetch(
        "SELECT id, name FROM analyte_categories WHERE is_active = TRUE"
    )
    await conn.close()
    return {row["name"]: str(row["id"]) for row in rows}


# ── Экранирование строк для SQL ───────────────────────────────────────────────

def sql_str(value: str | None) -> str:
    if value is None:
        return "NULL"
    escaped = str(value).replace("'", "''")
    return f"'{escaped}'"


def sql_num(value: float | None) -> str:
    if value is None:
        return "NULL"
    return str(float(value))


# ── Генерация SQL ─────────────────────────────────────────────────────────────

def generate_sql(groups: list[dict], category_ids: dict[str, str]) -> str:
    lines = [
        "-- ============================================================",
        "-- Автоматически сгенерировано из analytics/groups_draft.json",
        "-- Не редактировать вручную — изменяй groups_draft.json и перегенерируй",
        "-- ============================================================",
        "",
        "BEGIN;",
        "",
        "-- Очищаем таблицы (CASCADE распространяется на analyte_synonyms и unit_conversions)",
        "TRUNCATE analyte_standards CASCADE;",
        "",
    ]

    standards_lines = ["-- analyte_standards", ""]
    synonyms_lines  = ["-- analyte_synonyms", ""]

    missing_categories = set()
    sort_order = 0

    for group in groups:
        canonical_name = group["canonical_name"]
        category       = group.get("category", "")
        standard_unit  = group.get("standard_unit", "")
        synonyms       = group.get("synonyms", [])

        category_id = category_ids.get(category)
        if not category_id:
            missing_categories.add(category)
            continue

        analyte_id = str(uuid.uuid4())

        # INSERT analyte_standards
        standards_lines.append(
            f"INSERT INTO analyte_standards "
            f"(id, category_id, canonical_name, standard_unit, "
            f"reference_male_min, reference_male_max, reference_female_min, reference_female_max, "
            f"sort_order, is_active) VALUES ("
            f"{sql_str(analyte_id)}, "
            f"{sql_str(category_id)}, "
            f"{sql_str(canonical_name)}, "
            f"{sql_str(standard_unit)}, "
            f"NULL, NULL, NULL, NULL, "
            f"{sort_order}, TRUE);"
        )
        sort_order += 1

        # INSERT analyte_synonyms — canonical первым (is_primary=TRUE)
        canonical_synonym = next(
            (s for s in synonyms if s.get("is_canonical")),
            None
        )
        if canonical_synonym is None and synonyms:
            canonical_synonym = synonyms[0]

        # Дедупликация по (synonym_lower, unit_lower) внутри группы
        seen_keys: set[tuple[str, str]] = set()

        def insert_synonym(s_name: str, s_unit: str, coeff: float, is_primary: bool) -> None:
            key = (s_name.lower(), s_unit.lower())
            if key in seen_keys:
                return
            seen_keys.add(key)
            synonyms_lines.append(
                f"INSERT INTO analyte_synonyms "
                f"(id, analyte_id, synonym, synonym_lower, unit, unit_lower, "
                f"coefficient, source, is_primary) VALUES ("
                f"{sql_str(str(uuid.uuid4()))}, "
                f"{sql_str(analyte_id)}, "
                f"{sql_str(s_name)}, "
                f"{sql_str(s_name.lower())}, "
                f"{sql_str(s_unit)}, "
                f"{sql_str(s_unit.lower())}, "
                f"{sql_num(coeff)}, {sql_str('mongodb')}, {str(is_primary).upper()});"
            )

        # canonical synonym (is_primary=TRUE)
        if canonical_synonym:
            insert_synonym(
                canonical_synonym["test_name"],
                canonical_synonym.get("unit", ""),
                1.0,
                True
            )

        # остальные синонимы
        for syn in synonyms:
            if syn.get("is_canonical"):
                continue
            insert_synonym(
                syn["test_name"],
                syn.get("unit", ""),
                float(syn.get("coefficient", 1.0)),
                False
            )

    lines.extend(standards_lines)
    lines.append("")
    lines.extend(synonyms_lines)
    lines.append("")
    lines.append("COMMIT;")

    if missing_categories:
        lines.append("")
        lines.append("-- ВНИМАНИЕ: следующие категории не найдены в analyte_categories:")
        for c in sorted(missing_categories):
            lines.append(f"--   '{c}'")

    return "\n".join(lines)


# ── main ──────────────────────────────────────────────────────────────────────

async def main():
    print("📖 Читаю groups_draft.json...")
    with open(GROUPS_PATH, encoding="utf-8") as f:
        groups = json.load(f)
    print(f"   Загружено {len(groups)} групп.")

    print("🗃️  Загружаю ID категорий из PostgreSQL...")
    category_ids = await fetch_category_ids(PG_DSN)
    print(f"   Найдено {len(category_ids)} категорий: {list(category_ids.keys())}")

    print("⚙️  Генерирую SQL...")
    sql = generate_sql(groups, category_ids)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(sql)

    # Статистика
    standards_count = sql.count("INSERT INTO analyte_standards")
    synonyms_count  = sql.count("INSERT INTO analyte_synonyms")
    print(f"\n✅ SQL сгенерирован → {OUTPUT_PATH}")
    print(f"   analyte_standards: {standards_count} записей")
    print(f"   analyte_synonyms:  {synonyms_count} записей")
    print("   Запусти 04_apply.sh для применения.")


if __name__ == "__main__":
    asyncio.run(main())
