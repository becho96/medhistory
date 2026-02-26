#!/usr/bin/env python3
"""
Seed analyte_standards и analyte_synonyms из lab_combinations.csv.

Группирует эквивалентные анализы, нормализует единицы, создаёт маппинг.
Требует: миграция apply_analyte_synonym_unit_migration применена.

Запуск:
  python scripts/seed_analyte_mappings_from_csv.py
  python scripts/seed_analyte_mappings_from_csv.py --csv lab_combinations.csv --dry-run
"""

import argparse
import csv
import os
import re
import sys
import uuid
from pathlib import Path
from collections import defaultdict

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

env_file = project_root / ".env.local"
if env_file.exists():
    from dotenv import load_dotenv
    load_dotenv(env_file)

# Нормализация названий (вариант -> канонический)
NAME_ALIASES = {
    "mch": "Среднее содержание гемоглобина в эритроците",
    "mcv": "Средний объем эритроцита",
    "rdw": "Ширина распределения эритроцитов",
    "mpv": "Средний объем тромбоцитов",
    "pct": "Общий объем тромбоцитов в крови (тромбоцитокрит)",
    "pdw": "Ширина распределения тромбоцитов по объему",
    "соэ": "СОЭ",
    "скорость оседания эритроцитов": "СОЭ",
    "алат": "Аланинаминотрансфераза (АЛТ)",
    "аст": "Аспартатаминотрансфераза (АСТ)",
    "алт": "Аланинаминотрансфераза (АЛТ)",
    "ггт": "Гамма-глутамилтрансфераза (ГГТ)",
    "ттг": "Тиреотропный гормон (ТТГ)",
    "т3": "Трийодтиронин свободный (Т3)",
    "т4": "Тироксин свободный (Т4)",
    "т3 свободный": "Трийодтиронин свободный (Т3)",
    "т4 свободный": "Тироксин свободный (Т4)",
    "ср.объем эритроцита": "Средний объем эритроцита",
    "средний объём эритроцита": "Средний объем эритроцита",
    "ср. концентрация гемоглобина в эритроците": "Средняя концентрация гемоглобина в эритроците",
    "средняя концентрация гемоглобина в эритроцитах": "Средняя концентрация гемоглобина в эритроците",
    "тромбоцитокрит": "Общий объем тромбоцитов в крови (тромбоцитокрит)",
    "ph мочи": "pH мочи",
    "относительная плотность": "Относительная плотность",
}

# (standard_unit, coefficient) для конвертации
UNIT_TO_STANDARD = {
    "10*9/л": ("10*9/л", 1.0),
    "10^9/л": ("10*9/л", 1.0),
    "х10^9/л": ("10*9/л", 1.0),
    "х10*9/л": ("10*9/л", 1.0),
    "тыс/мкл": ("10*9/л", 1.0),
    "10*12/л": ("10*12/л", 1.0),
    "10^12/л": ("10*12/л", 1.0),
    "х10^12/л": ("10*12/л", 1.0),
    "г/дл": ("г/л", 10.0),
    "мм/ч": ("мм/час", 1.0),
    "ед. ph": ("pH", 1.0),
}

# Категории по ключевым словам (для автоопределения)
CATEGORY_KEYWORDS = {
    "Общий анализ крови": [
        "гемоглобин", "лейкоциты", "эритроциты", "тромбоциты", "нейтрофилы",
        "лимфоциты", "моноциты", "эозинофилы", "базофилы", "гематокрит",
        "нейтрофилов", "лимфоцитов", "моноцитов", "эозинофилов", "базофилов",  # абсолютное количество X
        "нормобластов", "нормобласт",
        "mch", "mcv", "rdw", "mpv", "pct", "pdw",
        "палочкоядерные", "сегментоядерные",
        "тромбоцитокрит", "объём тромбоцитов", "объем тромбоцитов",
        "процент крупных", "ширина распределения", "средний объем",
        "средняя концентрация гемоглобина", "среднее содержание гемоглобина",
    ],
    "Биохимия крови": [
        "глюкоза", "креатинин", "мочевина", "билирубин", "белок", "альбумин",
        "аланинаминотрансфераза", "аспартатаминотрансфераза", "алт", "аст",
        "амилаза", "липаза", "ггт", "щелочная фосфатаза",
    ],
    "Липидный профиль": ["холестерин", "триглицерид", "лпнп", "лпвп", "липид"],
    "Гормоны": ["ттг", "тиреотропный", "тироксин", "трийодтиронин", "т3", "т4", "гормон"],
    "Витамины и микроэлементы": ["витамин", "кальций", "калий", "натрий", "магний", "железо"],
    "Маркеры воспаления": ["с-реактивный", "crp", "соэ"],
    "Общий анализ мочи": [
        "моч", "относительная плотность", "белок", "глюкоза", "кетон",
        "билирубин", "уробилиноген", "ph мочи", "лейкоциты п/зр",
        "эритроциты п/зр", "бактерии", "слизь", "кристалл", "цилиндр",
        "эпителий", "trichomonas", "грибы",
        "ph мочи", "ph", "плотность",  # pH мочи, относительная плотность
    ],
}


def normalize_name(name: str) -> str:
    """Нормализует название для поиска алиаса"""
    n = name.lower().strip()
    n = re.sub(r"\s+", " ", n)
    return n


def get_canonical_name(name: str) -> str:
    """Возвращает каноническое название или исходное"""
    n = normalize_name(name)
    return NAME_ALIASES.get(n, name.strip())


def get_standard_unit_and_coef(unit: str) -> tuple:
    """(standard_unit, coefficient)"""
    if not unit:
        return ("", 1.0)
    u = unit.strip().lower()
    return UNIT_TO_STANDARD.get(u, (unit.strip(), 1.0))


# Анализы с двумя версиями: % и абсолютные (10*9/л и т.п.)
DUAL_ANALYTES = {"лимфоциты", "нейтрофилы", "моноциты", "эозинофилы", "базофилы"}


def get_canonical_name_and_std_unit(name: str, unit: str) -> tuple:
    """(canonical_name, standard_unit) с учётом % vs абс"""
    canonical = get_canonical_name(name)
    std_unit, coef = get_standard_unit_and_coef(unit)
    base_lower = canonical.lower()
    if base_lower in DUAL_ANALYTES:
        is_pct = "%" in (unit or "").lower()
        if is_pct:
            return (f"{canonical} (%)", "%")
        else:
            return (f"{canonical} (абс)", std_unit or "10*9/л")
    return (canonical, std_unit)


def detect_category(name: str, unit: str) -> str:
    """Определяет категорию по названию и единице"""
    n = normalize_name(name)
    u = (unit or "").lower()
    for cat, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in n or kw in u:
                return cat
    return "Другие анализы"


def main():
    parser = argparse.ArgumentParser(description="Seed analyte mappings from CSV")
    parser.add_argument("--csv", default="lab_combinations.csv", help="Path to CSV file")
    parser.add_argument("--dry-run", action="store_true", help="Print without writing to DB")
    args = parser.parse_args()

    csv_path = Path(args.csv)
    if not csv_path.is_absolute():
        csv_path = project_root / csv_path
    if not csv_path.exists():
        print(f"Ошибка: файл {csv_path} не найден")
        return 1

    rows = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append({
                "test_name": (r.get("test_name") or "").strip(),
                "unit": (r.get("unit") or "").strip(),
                "count": int(r.get("count", 0)),
            })

    # Группируем: (canonical_name, standard_unit) -> [(original_name, unit, coefficient), ...]
    groups: dict[tuple, list] = defaultdict(list)
    for r in rows:
        if not r["test_name"]:
            continue
        canonical, std_unit = get_canonical_name_and_std_unit(r["test_name"], r["unit"])
        _, coef = get_standard_unit_and_coef(r["unit"])
        key = (canonical, std_unit)
        groups[key].append((r["test_name"], r["unit"], coef))

    # Дедупликация внутри группы
    seen_pairs = set()
    unique_groups = {}
    for key, items in groups.items():
        unique_items = []
        for name, unit, coef in items:
            pair = (name.lower(), (unit or "").lower())
            if pair not in seen_pairs:
                seen_pairs.add(pair)
                unique_items.append((name, unit, coef))
        unique_groups[key] = unique_items

    print(f"Загружено {len(rows)} строк, {len(unique_groups)} уникальных анализов")
    if args.dry_run:
        for (canonical, std_unit), items in sorted(unique_groups.items(), key=lambda x: -sum(1 for _ in x[1])):
            cat = detect_category(canonical, std_unit)
            print(f"  {canonical} [{std_unit}] -> {cat}: {len(items)} синонимов")
        return 0

    # Подключение к БД
    from sqlalchemy import create_engine, text
    db_url = os.getenv("DATABASE_URL", "postgresql://medhistory_user:medhistory_local_pass@localhost:5432/medhistory")
    if db_url.startswith("postgresql+asyncpg://"):
        db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
    engine = create_engine(db_url)

    with engine.connect() as conn:
        # Получить/создать категории
        cat_result = conn.execute(text("SELECT id, name FROM analyte_categories WHERE is_active = TRUE"))
        cats = {row[1]: str(row[0]) for row in cat_result.fetchall()}
        if "Другие анализы" not in cats:
            cats["Другие анализы"] = str(uuid.uuid4())
            conn.execute(text("""
                INSERT INTO analyte_categories (id, name, icon, sort_order, is_active)
                VALUES (:id, 'Другие анализы', '📋', 999, TRUE)
            """), {"id": cats["Другие анализы"]})
            conn.commit()
            print("Создана категория 'Другие анализы'")

        created_standards = 0
        created_synonyms = 0
        for (canonical_name, standard_unit), items in unique_groups.items():
            category = detect_category(canonical_name, standard_unit)
            category_id = cats.get(category, cats["Другие анализы"])

            # Найти или создать analyte_standard (уникальность только по canonical_name)
            r = conn.execute(text("""
                SELECT id, category_id FROM analyte_standards WHERE canonical_name = :name
            """), {"name": canonical_name})
            row = r.fetchone()
            if row:
                analyte_id = str(row[0])
                # Обновить категорию, если должна быть другая
                target_cat_id = cats.get(category, cats["Другие анализы"])
                if str(row[1]) != target_cat_id:
                    conn.execute(text("""
                        UPDATE analyte_standards SET category_id = :cat_id WHERE id = :id
                    """), {"cat_id": target_cat_id, "id": analyte_id})
            else:
                analyte_id = str(uuid.uuid4())
                conn.execute(text("""
                    INSERT INTO analyte_standards (id, category_id, canonical_name, standard_unit, is_active)
                    VALUES (:id, :cat_id, :name, :unit, TRUE)
                """), {"id": analyte_id, "cat_id": category_id, "name": canonical_name, "unit": standard_unit or ""})
                created_standards += 1

            for orig_name, orig_unit, coef in items:
                syn_lower = orig_name.lower()
                unit_lower = (orig_unit or "").lower()
                exists = conn.execute(text("""
                    SELECT 1 FROM analyte_synonyms WHERE synonym_lower = :sl AND COALESCE(unit_lower, '') = :ul LIMIT 1
                """), {"sl": syn_lower, "ul": unit_lower}).fetchone()
                if exists:
                    continue
                try:
                    conn.execute(text("""
                        INSERT INTO analyte_synonyms (id, analyte_id, synonym, synonym_lower, unit, unit_lower, coefficient)
                        VALUES (:id, :aid, :syn, :syn_lower, :unit, :unit_lower, :coef)
                    """), {
                        "id": str(uuid.uuid4()),
                        "aid": analyte_id,
                        "syn": orig_name,
                        "syn_lower": syn_lower,
                        "unit": orig_unit or "",
                        "unit_lower": unit_lower,
                        "coef": coef,
                    })
                    created_synonyms += 1
                except Exception as e:
                    print(f"  Ошибка {orig_name} [{orig_unit}]: {e}")

        conn.commit()

    print(f"Создано analyte_standards: {created_standards}")
    print(f"Добавлено analyte_synonyms: {created_synonyms}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
