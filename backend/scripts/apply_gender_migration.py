#!/usr/bin/env python3
"""
Скрипт для применения миграции добавления поля gender в таблицу users
"""

import os
from sqlalchemy import create_engine, text

def apply_migration(database_url: str):
    """Применяет SQL миграцию для добавления поля gender"""
    
    engine = create_engine(database_url)
    
    migration_sql = """
-- Создаем enum тип для пола пользователя
DO $$ BEGIN
    CREATE TYPE genderenum AS ENUM ('male', 'female', 'other');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Добавляем поле gender в таблицу users
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS gender genderenum;

-- Комментарий для документации
COMMENT ON COLUMN users.gender IS 'Пол пользователя: male (мужской), female (женский), other (другой)';
"""
    
    print("=" * 80)
    print("📝 ПРИМЕНЕНИЕ МИГРАЦИИ: добавление поля gender")
    print("=" * 80)
    print()
    
    try:
        with engine.connect() as conn:
            print("🔄 Выполняем миграцию...")
            conn.execute(text(migration_sql))
            conn.commit()
            print("✅ Миграция успешно применена!")
            print()
            
            # Проверяем, что поле добавлено
            result = conn.execute(text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'users' AND column_name = 'gender'
            """))
            row = result.fetchone()
            
            if row:
                print("✓ Поле 'gender' успешно добавлено в таблицу 'users'")
                print(f"  Тип: {row[1]}")
                print(f"  Nullable: {row[2]}")
            else:
                print("⚠️ Поле не найдено в таблице")
                
    except Exception as e:
        print(f"❌ Ошибка при применении миграции: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        engine.dispose()
    
    return True


def normalize_database_url(url: str) -> str:
    """Конвертирует postgresql+asyncpg:// в postgresql:// для psycopg2"""
    if url.startswith('postgresql+asyncpg://'):
        return url.replace('postgresql+asyncpg://', 'postgresql://')
    return url


def main():
    import argparse
    
    # Пытаемся получить DATABASE_URL из переменных окружения
    default_database_url = os.getenv('DATABASE_URL', 'postgresql://medhistory_user:medhistory_pass@localhost:5432/medhistory')
    
    # Конвертируем asyncpg URL в psycopg2 URL
    default_database_url = normalize_database_url(default_database_url)
    
    parser = argparse.ArgumentParser(
        description='Применение миграции добавления поля gender'
    )
    parser.add_argument(
        '--database-url',
        default=default_database_url,
        help='URL базы данных PostgreSQL (по умолчанию берётся из DATABASE_URL env)'
    )
    
    args = parser.parse_args()
    
    # Нормализуем URL
    database_url = normalize_database_url(args.database_url)
    
    print(f"База данных: {database_url.split('@')[1] if '@' in database_url else 'скрыт'}")
    print()
    
    success = apply_migration(database_url)
    
    if success:
        print()
        print("=" * 80)
        print("✅ ГОТОВО!")
        print("=" * 80)
    else:
        print()
        print("=" * 80)
        print("❌ ОШИБКА!")
        print("=" * 80)
        exit(1)


if __name__ == "__main__":
    main()
