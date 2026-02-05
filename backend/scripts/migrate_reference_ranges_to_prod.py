#!/usr/bin/env python3
"""
Скрипт для миграции референсных значений из локальной БД в production
Переносит значения полей reference_male_min, reference_male_max, 
reference_female_min, reference_female_max из локальной таблицы 
analyte_standards в production среду.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from decimal import Decimal
import json

# Загрузить .env файл если есть
env_path = Path(__file__).parent.parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)

from sqlalchemy import create_engine, text
import paramiko

# Конфигурация SSH для production (как в db-viewer/app.py)
SSH_CONFIG = {
    'host': os.getenv('PROD_SSH_HOST', '93.77.182.26'),
    'port': int(os.getenv('PROD_SSH_PORT', '22')),
    'username': os.getenv('PROD_SSH_USER', 'yc-user'),
    'key_path': os.path.expanduser(os.getenv('PROD_SSH_KEY', '~/.ssh/id_rsa')),
}

def normalize_database_url(url: str) -> str:
    """Конвертирует postgresql+asyncpg:// в postgresql:// для psycopg2"""
    if url.startswith('postgresql+asyncpg://'):
        return url.replace('postgresql+asyncpg://', 'postgresql://')
    return url

def get_local_database_url():
    """Получить URL локальной БД"""
    # Попробовать из env
    database_url = os.getenv('DATABASE_URL', 'postgresql://medhistory_user:medhistory_local_pass@localhost:5432/medhistory')
    return normalize_database_url(database_url)

def get_local_reference_data():
    """Получить референсные значения из локальной БД"""
    database_url = get_local_database_url()
    engine = create_engine(database_url)
    
    print("=" * 80)
    print("📥 ЗАГРУЗКА ДАННЫХ ИЗ ЛОКАЛЬНОЙ БД")
    print("=" * 80)
    print(f"База данных: {database_url.split('@')[1] if '@' in database_url else 'локальная'}")
    print()
    
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT 
                    canonical_name,
                    reference_male_min,
                    reference_male_max,
                    reference_female_min,
                    reference_female_max
                FROM analyte_standards
                WHERE reference_male_min IS NOT NULL 
                   OR reference_female_min IS NOT NULL
                ORDER BY canonical_name
            """)
            
            result = conn.execute(query)
            rows = result.fetchall()
            
            print(f"✓ Найдено записей с референсными значениями: {len(rows)}")
            
            data = []
            for row in rows:
                data.append({
                    'canonical_name': row[0],
                    'reference_male_min': float(row[1]) if row[1] is not None else None,
                    'reference_male_max': float(row[2]) if row[2] is not None else None,
                    'reference_female_min': float(row[3]) if row[3] is not None else None,
                    'reference_female_max': float(row[4]) if row[4] is not None else None
                })
            
            return data
            
    except Exception as e:
        print(f"❌ Ошибка при загрузке данных из локальной БД: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        engine.dispose()

def execute_ssh_command(command):
    """Выполнить команду через SSH"""
    key_path = SSH_CONFIG['key_path']
    
    if not os.path.exists(key_path):
        print(f"❌ SSH ключ не найден: {key_path}")
        return None, None, -1
    
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        key = paramiko.RSAKey.from_private_key_file(key_path)
        
        print(f"🔌 Подключение к {SSH_CONFIG['username']}@{SSH_CONFIG['host']}...")
        ssh.connect(
            hostname=SSH_CONFIG['host'],
            port=SSH_CONFIG['port'],
            username=SSH_CONFIG['username'],
            pkey=key,
            timeout=10
        )
        
        stdin, stdout, stderr = ssh.exec_command(command)
        exit_status = stdout.channel.recv_exit_status()
        output = stdout.read().decode('utf-8')
        error = stderr.read().decode('utf-8')
        
        ssh.close()
        
        return output, error, exit_status
        
    except Exception as e:
        return None, str(e), -1

def migrate_to_production(data):
    """Мигрировать данные в production БД"""
    print()
    print("=" * 80)
    print("📤 МИГРАЦИЯ ДАННЫХ В PRODUCTION")
    print("=" * 80)
    print(f"Сервер: {SSH_CONFIG['username']}@{SSH_CONFIG['host']}")
    print()
    
    if not data:
        print("⚠️  Нет данных для миграции")
        return False
    
    # Подготавливаем SQL команды для каждой записи
    updates = []
    
    for item in data:
        # Экранируем одинарные кавычки в названии
        canonical_name = item['canonical_name'].replace("'", "''")
        
        values = []
        if item['reference_male_min'] is not None:
            values.append(f"reference_male_min = {item['reference_male_min']}")
        if item['reference_male_max'] is not None:
            values.append(f"reference_male_max = {item['reference_male_max']}")
        if item['reference_female_min'] is not None:
            values.append(f"reference_female_min = {item['reference_female_min']}")
        if item['reference_female_max'] is not None:
            values.append(f"reference_female_max = {item['reference_female_max']}")
        
        if values:
            update_sql = f"""
                UPDATE analyte_standards 
                SET {', '.join(values)}
                WHERE canonical_name = '{canonical_name}';
            """
            updates.append(update_sql)
    
    if not updates:
        print("⚠️  Нет данных для обновления")
        return False
    
    # Выполняем обновления через отдельные команды для каждой записи
    # Это более надежно чем heredoc через SSH
    print(f"🔄 Обновление {len(updates)} записей...")
    
    successful = 0
    failed = 0
    
    for i, update_sql in enumerate(updates, 1):
        # Убираем лишние пробелы и переносы строк
        sql_command = ' '.join(update_sql.strip().split())
        
        # Экранируем кавычки для bash
        escaped_sql = sql_command.replace('"', '\\"').replace('$', '\\$')
        
        # Выполняем через psql -c
        command = f'docker exec medhistory-postgres-1 psql -U medhistory_user -d medhistory -c "{escaped_sql}"'
        
        output, error, exit_status = execute_ssh_command(command)
        
        if exit_status == 0:
            successful += 1
            if i % 10 == 0:
                print(f"  ✓ Обновлено {i}/{len(updates)} записей...")
        else:
            failed += 1
            print(f"  ⚠️  Ошибка обновления записи {i}: {error or output[:100]}")
    
    print(f"\n✓ Успешно обновлено: {successful}/{len(updates)}")
    if failed > 0:
        print(f"⚠️  Ошибок: {failed}/{len(updates)}")
    
    exit_status = 0 if failed == 0 else 1
    output = f"Обновлено {successful} из {len(updates)} записей"
    
    if exit_status == 0:
        print("✅ Данные успешно обновлены в production БД!")
        return True
    else:
        print(f"⚠️  Обновление завершено с ошибками: {failed} записей не обновлено")
        return successful > 0  # Возвращаем True, если хотя бы что-то обновилось

def verify_production_data(data):
    """Проверить, что данные успешно мигрированы"""
    print()
    print("=" * 80)
    print("🔍 ПРОВЕРКА ДАННЫХ В PRODUCTION")
    print("=" * 80)
    
    # Проверяем количество записей с reference значениями
    command = """docker exec medhistory-postgres-1 psql -U medhistory_user -d medhistory -t -c "SELECT COUNT(*) FROM analyte_standards WHERE reference_male_min IS NOT NULL OR reference_female_min IS NOT NULL;" """
    
    output, error, exit_status = execute_ssh_command(command)
    
    if exit_status == 0 and output:
        count = int(output.strip())
        expected = len(data)
        print(f"✓ Записей с референсными значениями в production: {count} (ожидалось: {expected})")
        
        if count == expected:
            print("✅ Количество записей совпадает!")
            return True
        else:
            print(f"⚠️  Количество записей не совпадает")
            return False
    else:
        print(f"❌ Ошибка при проверке данных: {error or output}")
        return False

def main():
    """Основная функция"""
    print("=" * 80)
    print("🚀 МИГРАЦИЯ РЕФЕРЕНСНЫХ ЗНАЧЕНИЙ В PRODUCTION")
    print("=" * 80)
    print()
    
    # 1. Загрузить данные из локальной БД
    data = get_local_reference_data()
    
    if not data:
        print("\n❌ Не удалось загрузить данные из локальной БД")
        sys.exit(1)
    
    print(f"\n📋 Подготовлено к миграции {len(data)} записей:")
    for i, item in enumerate(data[:5], 1):
        print(f"  {i}. {item['canonical_name']}")
    if len(data) > 5:
        print(f"  ... и ещё {len(data) - 5} записей")
    
    # 2. Мигрировать в production
    success = migrate_to_production(data)
    
    if not success:
        print("\n❌ Ошибка при миграции данных")
        sys.exit(1)
    
    # 3. Проверить результат
    verify_success = verify_production_data(data)
    
    print()
    print("=" * 80)
    if verify_success:
        print("✅ МИГРАЦИЯ ЗАВЕРШЕНА УСПЕШНО!")
    else:
        print("⚠️  МИГРАЦИЯ ЗАВЕРШЕНА, НО ТРЕБУЕТСЯ ПРОВЕРКА")
    print("=" * 80)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Прервано пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Неожиданная ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
