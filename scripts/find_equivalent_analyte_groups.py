#!/usr/bin/env python3
"""
Находит группы анализов, которые одинаковы по смыслу, но отличаются по названию и ед. измерения.

Примеры:
- (BAS#) Базофилы, 10*9/л  |  Базофилы, 10^9/л  |  Базофилы, тыс/мкл  |  Базофилы, х10^9/л  — одна группа
- (BAS%) Базофилы, %  |  Базофилы, %  — другая группа (процент)

Запуск:
  python scripts/find_equivalent_analyte_groups.py
  python scripts/find_equivalent_analyte_groups.py --csv lab_analyte_unit_combinations.csv --output equivalent_groups.csv
"""

import argparse
import csv
import re
from pathlib import Path
from collections import defaultdict

# Нормализация единиц: разные обозначения одной единицы -> каноническая
UNIT_TO_CANONICAL = {
    # Абсолютные 10^9/л (клеток)
    "10*9/л": "10*9/л",
    "10^9/л": "10*9/л",
    "х10^9/л": "10*9/л",
    "x10^9/л": "10*9/л",
    "x10*9/л": "10*9/л",
    "тыс/мкл": "10*9/л",  # тыс/мкл = 10^9/л
    # Абсолютные 10^12/л (эритроциты)
    "10*12/л": "10*12/л",
    "10^12/л": "10*12/л",
    "х10^12/л": "10*12/л",
    "x10^12/л": "10*12/л",
    "x10*12/л": "10*12/л",
    "млн/мкл": "10*12/л",
    # СОЭ
    "мм/ч": "мм/час",
    "мм/час": "мм/час",
    # pH
    "ед. ph": "pH",
    "ph": "pH",
    "pH": "pH",
    # Проценты
    "%": "%",
    "количество/100 клеток": "%",
    # г/дл и г/л — разные, не объединяем
    # п/зр
    "п/зр.": "п/зр",
    "п/зр": "п/зр",
}

# Маппинг названий: вариант -> (каноническое_название, суффикс_типа: "%" | "10*9/л" | "10*12/л" | "")
# Суффикс нужен для различения % и абс. количества
NAME_TO_CANONICAL = {
    "mch": "Среднее содержание гемоглобина в эритроците",
    "mcv": "Средний объем эритроцита",
    "rdw": "Ширина распределения эритроцитов",
    "mpv": "Средний объем тромбоцитов",
    "pct": "Общий объем тромбоцитов в крови",
    "pdw": "Ширина распределения тромбоцитов по объему",
    "соэ": "СОЭ",
    "скорость оседания эритроцитов": "СОЭ",
    "алат": "Аланинаминотрансфераза",
    "аст": "Аспартатаминотрансфераза",
    "алт": "Аланинаминотрансфераза",
    "ггт": "Гамма-глутамилтрансфераза",
    "ттг": "Тиреотропный гормон",
    "т3 свободный": "Трийодтиронин свободный",
    "т4 свободный": "Тироксин свободный",
    "ср.объем эритроцита": "Средний объем эритроцита",
    "средний объём эритроцита": "Средний объем эритроцита",
    "ср. концентрация гемоглобина в эритроците": "Средняя концентрация гемоглобина в эритроците",
    "средняя концентрация гемоглобина в эритроцитах": "Средняя концентрация гемоглобина в эритроците",
    "тромбоцитокрит": "Общий объем тромбоцитов в крови",
    "rdw-cv": "Ширина распределения эритроцитов",
    "rdw-sd": "Ширина распределения эритроцитов",
    # Абсолютные/относительные количества
    "абсолютное количество базофилов": "Базофилы",
    "абсолютное количество эозинофилов": "Эозинофилы",
    "абсолютное количество лимфоцитов": "Лимфоциты",
    "абсолютное количество моноцитов": "Моноциты",
    "абсолютное количество нейтрофилов": "Нейтрофилы",
    "абсолютное количество нормобластов": "Нормобласты",
    "относительное количество базофилов": "Базофилы",
    "относительное количество эозинофилов": "Эозинофилы",
    "относительное количество лимфоцитов": "Лимфоциты",
    "относительное количество моноцитов": "Моноциты",
    "относительное количество нейтрофилов": "Нейтрофилы",
    "относительное количество нормобластов": "Нормобласты",
    "количество лейкоцитов": "Лейкоциты",
    "количество тромбоцитов": "Тромбоциты",
    "количество эритроцитов": "Эритроциты",
    "лимфоциты %": "Лимфоциты",
    "моноциты %": "Моноциты",
    "нейтрофилы сегментоядерные %": "Нейтрофилы сегментоядерные",
    # Билирубин
    "билирубин общий": "Билирубин общий",
    "билирубин": "Билирубин",
    "билирубин непрямой": "Билирубин непрямой",
    "билирубин прямой": "Билирубин прямой",
    "билирубин прямой (конъюгированный)": "Билирубин прямой",
}


def normalize_unit(unit: str) -> str:
    """Возвращает каноническую единицу."""
    if not unit:
        return ""
    u = unit.strip().lower()
    return UNIT_TO_CANONICAL.get(u, unit.strip())


def extract_core_name(name: str) -> str:
    """Извлекает ядро названия: убирает (XXX) префикс."""
    if not name:
        return ""
    # (BAS#) Базофилы -> Базофилы
    m = re.match(r"^\([^)]+\)\s*(.+)$", name.strip())
    if m:
        return m.group(1).strip()
    return name.strip()


def get_canonical_name(name: str, unit: str) -> str:
    """Каноническое название с учётом типа (%, абс)."""
    n = name.lower().strip()
    n = re.sub(r"\s+", " ", n)
    core = extract_core_name(name)
    core_lower = core.lower()
    
    # Сначала проверяем явные алиасы
    if n in NAME_TO_CANONICAL:
        return NAME_TO_CANONICAL[n]
    
    # Проверяем алиасы по core (без скобок)
    if core_lower in NAME_TO_CANONICAL:
        return NAME_TO_CANONICAL[core_lower]
    
    return core


def get_group_key(name: str, unit: str) -> tuple:
    """(canonical_name, canonical_unit) для группировки."""
    canonical_name = get_canonical_name(name, unit)
    canonical_unit = normalize_unit(unit)
    return (canonical_name, canonical_unit)


def main():
    parser = argparse.ArgumentParser(
        description="Находит группы эквивалентных анализов (разные названия/единицы, один смысл)"
    )
    parser.add_argument(
        "--csv",
        default="lab_analyte_unit_combinations.csv",
        help="Входной CSV с колонками test_name, unit",
    )
    parser.add_argument(
        "--output",
        default="equivalent_analyte_groups.csv",
        help="Выходной CSV с группами",
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent
    csv_path = project_root / args.csv
    out_path = project_root / args.output

    if not csv_path.exists():
        print(f"Ошибка: файл {csv_path} не найден")
        return 1

    rows = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            tn = (r.get("test_name") or "").strip()
            un = (r.get("unit") or "").strip()
            if tn:
                rows.append((tn, un))

    # Группируем по (canonical_name, canonical_unit)
    groups: dict[tuple, list[tuple[str, str]]] = defaultdict(list)
    for name, unit in rows:
        key = get_group_key(name, unit)
        pair = (name, unit)
        if pair not in groups[key]:
            groups[key].append(pair)

    # Оставляем только группы с 2+ вариантами
    multi_groups = {k: v for k, v in groups.items() if len(v) >= 2}
    multi_groups = dict(sorted(multi_groups.items(), key=lambda x: (-len(x[1]), x[0][0])))

    # Записываем результат
    out_rows = []
    for (canonical_name, canonical_unit), variants in multi_groups.items():
        for name, unit in variants:
            out_rows.append({
                "group_id": f"{canonical_name} [{canonical_unit}]",
                "canonical_name": canonical_name,
                "canonical_unit": canonical_unit,
                "variant_count": len(variants),
                "test_name": name,
                "unit": unit,
            })

    with open(out_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[
            "group_id", "canonical_name", "canonical_unit", "variant_count",
            "test_name", "unit",
        ])
        w.writeheader()
        w.writerows(out_rows)

    print(f"Найдено {len(multi_groups)} групп эквивалентных анализов")
    print(f"Результат сохранён в {out_path}")
    print()
    for (cn, cu), variants in list(multi_groups.items())[:20]:
        print(f"  {cn} [{cu}] — {len(variants)} вариантов:")
        for name, unit in variants[:5]:
            print(f"    - {name}, {unit}")
        if len(variants) > 5:
            print(f"    ... и ещё {len(variants) - 5}")
    return 0


if __name__ == "__main__":
    exit(main())
