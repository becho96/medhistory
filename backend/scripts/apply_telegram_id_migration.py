#!/usr/bin/env python3
"""
Скрипт для применения миграции добавления поля telegram_id в таблицу users
"""

import os
from pathlib import Path
from sqlalchemy import create_engine, text

# Загружаем .env.local из корня проекта
PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_LOCAL = PROJECT_ROOT / ".env.local"
if ENV_LOCAL.exists():
    with open(ENV_LOCAL) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip().strip('"\''))


def normalize_database_url(url: str) -> str:
    """Конвертирует postgresql+asyncpg:// в postgresql:// для psycopg2"""
    if url.startswith("postgresql+asyncpg://"):
        return url.replace("postgresql+asyncpg://", "postgresql://")
    return url


def apply_migration(database_url: str):
    """Применяет SQL миграцию для добавления поля telegram_id"""
    database_url = normalize_database_url(database_url)
    engine = create_engine(database_url)

    migration_sql = """
-- Добавляем поле telegram_id в таблицу users
ALTER TABLE users ADD COLUMN IF NOT EXISTS telegram_id BIGINT;

-- Уникальный индекс (WHERE telegram_id IS NOT NULL — несколько NULL допустимы)
CREATE UNIQUE INDEX IF NOT EXISTS ix_users_telegram_id ON users (telegram_id) WHERE telegram_id IS NOT NULL;

COMMENT ON COLUMN users.telegram_id IS 'Telegram user ID для привязки Telegram бота';
"""

    print("=" * 80)
    print("📝 ПРИМЕНЕНИЕ МИГРАЦИИ: добавление поля telegram_id")
    print("=" * 80)
    print()

    try:
        with engine.connect() as conn:
            print("🔄 Выполняем миграцию...")
            conn.execute(text(migration_sql))
            conn.commit()
            print("✅ Миграция успешно применена!")
            print()

            result = conn.execute(
                text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'users' AND column_name = 'telegram_id'
            """)
            )
            row = result.fetchone()

            if row:
                print("✓ Поле 'telegram_id' успешно добавлено в таблицу 'users'")
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


def main():
    import argparse

    # URL для локального Docker: postgres на localhost
    default_url = os.getenv(
        "DATABASE_URL",
        "postgresql://medhistory_user:medhistory_local_pass@localhost:5432/medhistory",
    )

    parser = argparse.ArgumentParser(
        description="Применение миграции добавления поля telegram_id"
    )
    parser.add_argument(
        "--database-url",
        default=default_url,
        help="URL базы данных PostgreSQL",
    )
    args = parser.parse_args()

    url = normalize_database_url(args.database_url)
    print(f"База данных: {url.split('@')[1] if '@' in url else 'скрыт'}")
    print()

    success = apply_migration(url)

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
