#!/usr/bin/env python3
"""
Скрипт для миграции таблиц справочника анализов из локальной БД в продакшн.

Таблицы для миграции:
- analyte_categories
- analyte_standards  
- analyte_synonyms
- unit_conversions

Скрипт:
1. Проверяет наличие данных в локальной БД
2. Проверяет, что продакшн таблицы пустые
3. Копирует данные с сохранением UUID и связей
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Any
import asyncio
from datetime import datetime

import asyncpg
from dotenv import load_dotenv


class Colors:
    """ANSI коды для цветного вывода"""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_header(text: str):
    """Печать заголовка"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 70}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 70}{Colors.ENDC}\n")


def print_success(text: str):
    """Печать успеха"""
    print(f"{Colors.OKGREEN}✓ {text}{Colors.ENDC}")


def print_info(text: str):
    """Печать информации"""
    print(f"{Colors.OKCYAN}ℹ {text}{Colors.ENDC}")


def print_warning(text: str):
    """Печать предупреждения"""
    print(f"{Colors.WARNING}⚠ {text}{Colors.ENDC}")


def print_error(text: str):
    """Печать ошибки"""
    print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")


async def get_db_connection(db_url: str) -> asyncpg.Connection:
    """Создает подключение к БД"""
    # Парсим DATABASE_URL
    # Формат: postgresql+asyncpg://user:pass@host:port/dbname
    # Для asyncpg нужен формат: postgresql://user:pass@host:port/dbname
    db_url = db_url.replace('postgresql+asyncpg://', 'postgresql://')
    
    return await asyncpg.connect(db_url)


async def get_table_count(conn: asyncpg.Connection, table_name: str) -> int:
    """Получает количество записей в таблице"""
    result = await conn.fetchval(f"SELECT COUNT(*) FROM {table_name}")
    return result


async def check_local_data(conn: asyncpg.Connection) -> Dict[str, int]:
    """Проверяет наличие данных в локальной БД"""
    print_info("Проверка данных в локальной БД...")
    
    counts = {}
    tables = ['analyte_categories', 'analyte_standards', 'analyte_synonyms', 'unit_conversions']
    
    for table in tables:
        count = await get_table_count(conn, table)
        counts[table] = count
        if count > 0:
            print_success(f"  {table}: {count} записей")
        else:
            print_warning(f"  {table}: пустая таблица")
    
    return counts


async def check_production_empty(conn: asyncpg.Connection) -> bool:
    """Проверяет, что продакшн таблицы пустые"""
    print_info("Проверка продакшн БД...")
    
    tables = ['analyte_categories', 'analyte_standards', 'analyte_synonyms', 'unit_conversions']
    all_empty = True
    
    for table in tables:
        count = await get_table_count(conn, table)
        if count > 0:
            print_error(f"  {table}: содержит {count} записей (должна быть пустой!)")
            all_empty = False
        else:
            print_success(f"  {table}: пустая")
    
    return all_empty


async def migrate_table(
    local_conn: asyncpg.Connection,
    prod_conn: asyncpg.Connection,
    table_name: str,
    columns: List[str]
) -> int:
    """Мигрирует данные одной таблицы"""
    print_info(f"Миграция таблицы {table_name}...")
    
    # Читаем данные из локальной БД
    columns_str = ', '.join(columns)
    query = f"SELECT {columns_str} FROM {table_name} ORDER BY created_at"
    rows = await local_conn.fetch(query)
    
    if not rows:
        print_warning(f"  Нет данных для миграции")
        return 0
    
    # Вставляем данные в продакшн
    placeholders = ', '.join([f'${i+1}' for i in range(len(columns))])
    insert_query = f"INSERT INTO {table_name} ({columns_str}) VALUES ({placeholders})"
    
    migrated = 0
    for row in rows:
        values = [row[col] for col in columns]
        try:
            await prod_conn.execute(insert_query, *values)
            migrated += 1
        except Exception as e:
            print_error(f"  Ошибка при вставке записи: {e}")
            print_error(f"  Значения: {values}")
            raise
    
    print_success(f"  Мигрировано {migrated} записей")
    return migrated


async def main():
    """Основная функция"""
    print_header("🚀 Миграция справочника анализов: LOCAL → PRODUCTION")
    
    # Определяем корневую директорию проекта
    project_root = Path(__file__).parent.parent
    
    # Загружаем .env.local
    env_local = project_root / '.env.local'
    if not env_local.exists():
        print_error(f"Файл {env_local} не найден!")
        sys.exit(1)
    
    load_dotenv(env_local)
    
    # Пытаемся получить DATABASE_URL или собрать из компонентов
    local_db_url = os.getenv('DATABASE_URL')
    if not local_db_url:
        # Собираем из отдельных параметров
        postgres_user = os.getenv('POSTGRES_USER')
        postgres_password = os.getenv('POSTGRES_PASSWORD')
        postgres_db = os.getenv('POSTGRES_DB', 'medhistory')
        postgres_host = os.getenv('POSTGRES_HOST', 'localhost')
        postgres_port = os.getenv('POSTGRES_PORT', '5432')
        
        if not postgres_user or not postgres_password:
            print_error("Не найдены параметры подключения к БД в .env.local!")
            print_error("Требуются: POSTGRES_USER, POSTGRES_PASSWORD")
            sys.exit(1)
        
        local_db_url = f"postgresql://{postgres_user}:{postgres_password}@{postgres_host}:{postgres_port}/{postgres_db}"
    
    # Загружаем .env.production
    env_prod = project_root / '.env.production'
    if not env_prod.exists():
        print_error(f"Файл {env_prod} не найден!")
        sys.exit(1)
    
    # Очищаем переменные окружения перед загрузкой production
    for key in ['DATABASE_URL', 'POSTGRES_USER', 'POSTGRES_PASSWORD', 'POSTGRES_DB', 'POSTGRES_HOST', 'POSTGRES_PORT']:
        os.environ.pop(key, None)
    
    load_dotenv(env_prod, override=True)
    
    # Пытаемся получить DATABASE_URL или собрать из компонентов
    prod_db_url = os.getenv('DATABASE_URL')
    if not prod_db_url:
        # Собираем из отдельных параметров
        postgres_user = os.getenv('POSTGRES_USER')
        postgres_password = os.getenv('POSTGRES_PASSWORD')
        postgres_db = os.getenv('POSTGRES_DB', 'medhistory')
        # Для продакшн используем IP сервера или переменную POSTGRES_HOST
        postgres_host = os.getenv('POSTGRES_HOST', '158.160.99.232')
        postgres_port = os.getenv('POSTGRES_PORT', '5432')
        
        if not postgres_user or not postgres_password:
            print_error("Не найдены параметры подключения к БД в .env.production!")
            print_error("Требуются: POSTGRES_USER, POSTGRES_PASSWORD")
            sys.exit(1)
        
        prod_db_url = f"postgresql://{postgres_user}:{postgres_password}@{postgres_host}:{postgres_port}/{postgres_db}"
    
    print_info(f"Локальная БД: {local_db_url.split('@')[1] if '@' in local_db_url else 'не определена'}")
    print_info(f"Продакшн БД: {prod_db_url.split('@')[1] if '@' in prod_db_url else 'не определена'}")
    
    # Подключаемся к БД
    print_info("\nПодключение к базам данных...")
    try:
        local_conn = await get_db_connection(local_db_url)
        print_success("Подключено к локальной БД")
    except Exception as e:
        print_error(f"Ошибка подключения к локальной БД: {e}")
        sys.exit(1)
    
    try:
        prod_conn = await get_db_connection(prod_db_url)
        print_success("Подключено к продакшн БД")
    except Exception as e:
        print_error(f"Ошибка подключения к продакшн БД: {e}")
        await local_conn.close()
        sys.exit(1)
    
    try:
        # Проверяем данные в локальной БД
        print()
        local_counts = await check_local_data(local_conn)
        
        if all(count == 0 for count in local_counts.values()):
            print_error("\n❌ В локальной БД нет данных для миграции!")
            return
        
        # Проверяем, что продакшн таблицы пустые
        print()
        if not await check_production_empty(prod_conn):
            print_error("\n❌ Продакшн таблицы не пустые! Миграция отменена.")
            print_warning("\nЕсли вы хотите перезаписать данные, сначала очистите таблицы:")
            print_warning("  TRUNCATE TABLE unit_conversions CASCADE;")
            print_warning("  TRUNCATE TABLE analyte_synonyms CASCADE;")
            print_warning("  TRUNCATE TABLE analyte_standards CASCADE;")
            print_warning("  TRUNCATE TABLE analyte_categories CASCADE;")
            return
        
        # Подтверждение миграции
        print()
        print_warning("Вы собираетесь мигрировать данные:")
        for table, count in local_counts.items():
            if count > 0:
                print_warning(f"  • {table}: {count} записей")
        
        print()
        response = input(f"{Colors.BOLD}Продолжить миграцию? (yes/no): {Colors.ENDC}").strip().lower()
        if response not in ['yes', 'y', 'да']:
            print_info("Миграция отменена пользователем")
            return
        
        # Выполняем миграцию
        print()
        print_header("📦 Миграция данных")
        
        total_migrated = 0
        
        # 1. Мигрируем analyte_categories
        categories_cols = ['id', 'name', 'icon', 'sort_order', 'description', 'is_active', 'created_at', 'updated_at']
        count = await migrate_table(local_conn, prod_conn, 'analyte_categories', categories_cols)
        total_migrated += count
        
        # 2. Мигрируем analyte_standards
        standards_cols = [
            'id', 'category_id', 'canonical_name', 'standard_unit', 'description',
            'reference_male_min', 'reference_male_max', 'reference_female_min', 'reference_female_max',
            'sort_order', 'is_active', 'created_at', 'updated_at'
        ]
        count = await migrate_table(local_conn, prod_conn, 'analyte_standards', standards_cols)
        total_migrated += count
        
        # 3. Мигрируем analyte_synonyms
        synonyms_cols = [
            'id', 'analyte_id', 'synonym', 'synonym_lower', 'source', 'is_primary', 'created_at'
        ]
        count = await migrate_table(local_conn, prod_conn, 'analyte_synonyms', synonyms_cols)
        total_migrated += count
        
        # 4. Мигрируем unit_conversions
        conversions_cols = [
            'id', 'analyte_id', 'from_unit', 'from_unit_lower', 'coefficient', 'created_at'
        ]
        count = await migrate_table(local_conn, prod_conn, 'unit_conversions', conversions_cols)
        total_migrated += count
        
        # Финальная проверка
        print()
        print_header("✅ Миграция завершена успешно!")
        print_success(f"Всего мигрировано {total_migrated} записей")
        
        # Показываем финальное состояние продакшн БД
        print()
        print_info("Финальное состояние продакшн БД:")
        for table in ['analyte_categories', 'analyte_standards', 'analyte_synonyms', 'unit_conversions']:
            count = await get_table_count(prod_conn, table)
            print_success(f"  {table}: {count} записей")
        
    except Exception as e:
        print_error(f"\n❌ Ошибка при миграции: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        # Закрываем подключения
        await local_conn.close()
        await prod_conn.close()
        print_info("\nПодключения к БД закрыты")


if __name__ == "__main__":
    asyncio.run(main())
