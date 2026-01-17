#!/usr/bin/env python3
"""
Скрипт для заполнения таблицы analyte_standards референсными значениями
из CSV файла test_unit_reference_ranges.csv
"""

import csv
import re
import os
from decimal import Decimal
from typing import Optional, Tuple

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker


def parse_reference_range(range_str: str) -> Optional[Tuple[Optional[float], Optional[float]]]:
    """
    Парсит строку с референсным диапазоном.
    
    Returns:
        (min_value, max_value) или None если не удалось распарсить
    """
    if not range_str or range_str == "Нет данных":
        return None
    
    # Убираем пробелы
    range_str = range_str.strip()
    
    # Заменяем запятые на точки для чисел
    range_str = range_str.replace(',', '.')
    
    # Паттерн для диапазона: "X-Y" или "X - Y"
    range_pattern = r'(\d+(?:\.\d+)?)\s*[-–—]\s*(\d+(?:\.\d+)?)'
    match = re.search(range_pattern, range_str)
    if match:
        return (float(match.group(1)), float(match.group(2)))
    
    # Паттерн для "< X" или "<X"
    max_pattern = r'<?[<]\s*(\d+(?:\.\d+)?)'
    match = re.search(max_pattern, range_str)
    if match:
        return (None, float(match.group(1)))
    
    # Паттерн для "> X" или ">X"
    min_pattern = r'>?\s*>\s*(\d+(?:\.\d+)?)'
    match = re.search(min_pattern, range_str)
    if match:
        return (float(match.group(1)), None)
    
    # Если только одно число - считаем это максимальным значением
    single_num = r'^(\d+(?:\.\d+)?)$'
    match = re.match(single_num, range_str)
    if match:
        return (None, float(match.group(1)))
    
    return None


def extract_test_name_and_unit(combined: str) -> Tuple[str, Optional[str]]:
    """
    Извлекает название теста и единицу измерения из строки вида "Название (единица)"
    
    Returns:
        (test_name, unit)
    """
    # Паттерн: "Название (единица)"
    pattern = r'^(.+?)\s*\((.+?)\)$'
    match = re.match(pattern, combined)
    
    if match:
        test_name = match.group(1).strip()
        unit = match.group(2).strip()
        return (test_name, unit)
    
    # Если нет скобок, возвращаем всю строку как название
    return (combined.strip(), None)


def normalize_unit(unit: str) -> str:
    """Нормализует единицу измерения для сравнения"""
    if not unit:
        return ""
    
    # Убираем пробелы
    unit = unit.strip()
    
    # Заменяем различные варианты записи степеней
    unit = unit.replace('10*9', '×10⁹')
    unit = unit.replace('10^9', '×10⁹')
    unit = unit.replace('10*12', '×10¹²')
    unit = unit.replace('10^12', '×10¹²')
    unit = unit.replace('x10*12', '×10¹²')
    
    return unit.lower()


def load_csv_data(csv_file: str):
    """Загружает данные из CSV файла"""
    data = []
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            combined = row['Анализ (единица измерения)']
            ranges_str = row['Диапазоны нормальных значений']
            
            test_name, unit = extract_test_name_and_unit(combined)
            
            # Парсим все диапазоны (могут быть множественные через ";")
            ranges = []
            if ranges_str and ranges_str != "Нет данных":
                for single_range in ranges_str.split(';'):
                    parsed = parse_reference_range(single_range.strip())
                    if parsed:
                        ranges.append(parsed)
            
            if ranges:
                data.append({
                    'test_name': test_name,
                    'unit': unit,
                    'ranges': ranges
                })
    
    return data


def find_analyte_id(conn, test_name: str, unit: Optional[str]):
    """
    Ищет ID анализа в таблице analyte_standards по названию и единице измерения
    """
    # Сначала пробуем точное совпадение по canonical_name
    result = conn.execute(
        text("""
            SELECT id, canonical_name, standard_unit 
            FROM analyte_standards 
            WHERE canonical_name = :name
        """),
        {"name": test_name}
    )
    
    row = result.fetchone()
    if row:
        analyte_id, canonical_name, standard_unit = row
        
        # Проверяем совпадение единиц (если единица указана)
        if unit:
            if normalize_unit(standard_unit) == normalize_unit(unit):
                return analyte_id, canonical_name, standard_unit
        else:
            # Если единица не указана в CSV, возвращаем найденный анализ
            return analyte_id, canonical_name, standard_unit
    
    # Пробуем найти через синонимы
    result = conn.execute(
        text("""
            SELECT a.id, a.canonical_name, a.standard_unit
            FROM analyte_standards a
            JOIN analyte_synonyms s ON a.id = s.analyte_id
            WHERE s.synonym = :name OR s.synonym_lower = :name_lower
        """),
        {"name": test_name, "name_lower": test_name.lower()}
    )
    
    row = result.fetchone()
    if row:
        analyte_id, canonical_name, standard_unit = row
        
        if unit:
            if normalize_unit(standard_unit) == normalize_unit(unit):
                return analyte_id, canonical_name, standard_unit
        else:
            return analyte_id, canonical_name, standard_unit
    
    return None, None, None


def update_reference_ranges(database_url: str, csv_file: str, dry_run: bool = False):
    """
    Обновляет референсные значения в таблице analyte_standards
    """
    engine = create_engine(database_url)
    
    # Загружаем данные из CSV
    print("📂 Загрузка данных из CSV...")
    csv_data = load_csv_data(csv_file)
    print(f"✅ Загружено {len(csv_data)} записей")
    print()
    
    updated_count = 0
    not_found_count = 0
    skipped_count = 0
    
    with engine.connect() as conn:
        for item in csv_data:
            test_name = item['test_name']
            unit = item['unit']
            ranges = item['ranges']
            
            # Ищем анализ в БД
            analyte_id, canonical_name, standard_unit = find_analyte_id(conn, test_name, unit)
            
            if not analyte_id:
                print(f"⚠️  Не найден: {test_name} ({unit})")
                not_found_count += 1
                continue
            
            # Берем первый диапазон (обычно самый распространенный)
            min_val, max_val = ranges[0]
            
            # Если несколько диапазонов, используем среднее или самый широкий
            if len(ranges) > 1:
                all_mins = [r[0] for r in ranges if r[0] is not None]
                all_maxs = [r[1] for r in ranges if r[1] is not None]
                
                if all_mins:
                    min_val = min(all_mins)  # Берем минимальное из минимальных
                if all_maxs:
                    max_val = max(all_maxs)  # Берем максимальное из максимальных
            
            # Конвертируем в Decimal для PostgreSQL
            min_decimal = Decimal(str(min_val)) if min_val is not None else None
            max_decimal = Decimal(str(max_val)) if max_val is not None else None
            
            if dry_run:
                print(f"🔍 {canonical_name} ({standard_unit}): {min_val} - {max_val}")
            else:
                # Обновляем БД (используем одинаковые значения для обоих полов)
                update_sql = text("""
                    UPDATE analyte_standards 
                    SET 
                        reference_male_min = :min_val,
                        reference_male_max = :max_val,
                        reference_female_min = :min_val,
                        reference_female_max = :max_val,
                        updated_at = NOW()
                    WHERE id = :analyte_id
                """)
                
                conn.execute(update_sql, {
                    "min_val": min_decimal,
                    "max_val": max_decimal,
                    "analyte_id": analyte_id
                })
                
                conn.commit()
                
                print(f"✅ {canonical_name} ({standard_unit}): {min_val} - {max_val}")
                updated_count += 1
    
    print()
    print("=" * 80)
    if dry_run:
        print("🔍 ТЕСТОВЫЙ РЕЖИМ - изменения НЕ применены")
    print(f"✅ Обновлено: {updated_count}")
    print(f"⚠️  Не найдено: {not_found_count}")
    print("=" * 80)
    
    engine.dispose()


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Заполнение референсных значений в analyte_standards'
    )
    parser.add_argument(
        '--database-url',
        default='postgresql://medhistory_user:medhistory_pass@localhost:5432/medhistory',
        help='URL базы данных PostgreSQL'
    )
    parser.add_argument(
        '--csv-file',
        default='test_unit_reference_ranges.csv',
        help='Путь к CSV файлу с данными'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Тестовый режим (не применять изменения)'
    )
    
    args = parser.parse_args()
    
    # Проверяем существование CSV файла
    script_dir = os.path.dirname(__file__)
    csv_path = os.path.join(script_dir, args.csv_file)
    
    if not os.path.exists(csv_path):
        print(f"❌ Файл не найден: {csv_path}")
        return
    
    print("=" * 80)
    print("📥 ЗАПОЛНЕНИЕ РЕФЕРЕНСНЫХ ЗНАЧЕНИЙ")
    print("=" * 80)
    print(f"CSV файл: {csv_path}")
    print(f"База данных: {args.database_url}")
    if args.dry_run:
        print("⚠️  ТЕСТОВЫЙ РЕЖИМ (изменения не будут применены)")
    print()
    
    try:
        update_reference_ranges(args.database_url, csv_path, args.dry_run)
        print()
        print("✅ Готово!")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
