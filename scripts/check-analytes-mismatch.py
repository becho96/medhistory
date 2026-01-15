#!/usr/bin/env python3
"""
Скрипт для проверки соответствия названий анализов в MongoDB и PostgreSQL справочнике.

Выявляет анализы, которые есть в MongoDB, но не имеют синонимов в справочнике,
что приводит к проблеме "Нет данных для отображения" на графиках.
"""

import os
import sys
import asyncio
from pathlib import Path
from typing import Dict, List, Set
from collections import defaultdict
import subprocess
import time
import signal

import asyncpg
from motor import motor_asyncio
from dotenv import load_dotenv


class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 70}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 70}{Colors.ENDC}\n")


def print_success(text: str):
    print(f"{Colors.OKGREEN}✓ {text}{Colors.ENDC}")


def print_info(text: str):
    print(f"{Colors.OKCYAN}ℹ {text}{Colors.ENDC}")


def print_warning(text: str):
    print(f"{Colors.WARNING}⚠ {text}{Colors.ENDC}")


def print_error(text: str):
    print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")


class SSHTunnel:
    """Управление SSH туннелем"""
    
    def __init__(self, ssh_host: str, ssh_user: str, remote_host: str, remote_port: int, local_port: int, name: str = "tunnel"):
        self.ssh_host = ssh_host
        self.ssh_user = ssh_user
        self.remote_host = remote_host
        self.remote_port = remote_port
        self.local_port = local_port
        self.name = name
        self.process = None
    
    def start(self):
        """Запускает SSH туннель"""
        print_info(f"Создание SSH туннеля {self.name}: localhost:{self.local_port} -> {self.ssh_host}:{self.remote_port}")
        
        cmd = [
            'ssh',
            '-N',
            '-L', f'{self.local_port}:{self.remote_host}:{self.remote_port}',
            f'{self.ssh_user}@{self.ssh_host}',
            '-o', 'StrictHostKeyChecking=no',
            '-o', 'ServerAliveInterval=60'
        ]
        
        self.process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        print_info(f"Ожидание установки туннеля {self.name}...")
        time.sleep(2)
        
        if self.process.poll() is not None:
            _, stderr = self.process.communicate()
            raise Exception(f"Не удалось создать SSH туннель {self.name}: {stderr.decode()}")
        
        print_success(f"SSH туннель {self.name} установлен")
    
    def stop(self):
        """Останавливает SSH туннель"""
        if self.process:
            print_info(f"Закрытие SSH туннеля {self.name}...")
            self.process.send_signal(signal.SIGTERM)
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            print_success(f"SSH туннель {self.name} закрыт")


async def get_synonyms_from_db(db_url: str) -> Dict[str, Set[str]]:
    """Получает все синонимы из PostgreSQL"""
    print_info("Загрузка синонимов из PostgreSQL...")
    
    db_url = db_url.replace('postgresql+asyncpg://', 'postgresql://')
    conn = await asyncpg.connect(db_url)
    
    try:
        # Получаем все синонимы с их каноническими названиями
        query = """
            SELECT 
                a.canonical_name,
                s.synonym_lower
            FROM analyte_standards a
            JOIN analyte_synonyms s ON s.analyte_id = a.id
            WHERE a.is_active = TRUE
        """
        rows = await conn.fetch(query)
        
        # canonical_name -> set of synonyms (lowercase)
        synonyms_map = defaultdict(set)
        all_synonyms = set()
        
        for row in rows:
            canonical = row['canonical_name']
            synonym = row['synonym_lower']
            synonyms_map[canonical].add(synonym)
            all_synonyms.add(synonym)
        
        print_success(f"Загружено {len(synonyms_map)} анализов с {len(all_synonyms)} синонимами")
        
        return dict(synonyms_map), all_synonyms
        
    finally:
        await conn.close()


async def get_analytes_from_mongodb(mongo_url: str) -> List[Dict]:
    """Получает уникальные названия анализов из MongoDB"""
    print_info("Загрузка названий анализов из MongoDB...")
    
    client = motor_asyncio.AsyncIOMotorClient(mongo_url)
    db = client.get_database('medhistory')
    collection = db.get_collection('document_metadata')
    
    try:
        pipeline = [
            {"$project": {"extracted_data.lab_results": 1}},
            {"$unwind": "$extracted_data.lab_results"},
            {
                "$group": {
                    "_id": {
                        "name_lower": {"$toLower": "$extracted_data.lab_results.test_name"}
                    },
                    "name": {"$first": "$extracted_data.lab_results.test_name"},
                    "count": {"$sum": 1}
                }
            },
            {"$sort": {"count": -1}},
        ]
        
        analytes = []
        async for doc in collection.aggregate(pipeline):
            name = doc.get("name", "")
            name_lower = doc.get("_id", {}).get("name_lower", "").strip()
            count = doc.get("count", 0)
            
            if name_lower:
                analytes.append({
                    "name": name,
                    "name_lower": name_lower,
                    "count": count
                })
        
        print_success(f"Найдено {len(analytes)} уникальных названий анализов в MongoDB")
        
        return analytes
        
    finally:
        client.close()


async def main():
    print_header("🔍 Проверка соответствия названий анализов (через SSH)")
    
    # Загружаем .env.production
    project_root = Path(__file__).parent.parent
    env_prod = project_root / '.env.production'
    
    if not env_prod.exists():
        print_error(f"Файл {env_prod} не найден!")
        sys.exit(1)
    
    load_dotenv(env_prod)
    
    # Получаем параметры подключения
    postgres_user = os.getenv('POSTGRES_USER')
    postgres_password = os.getenv('POSTGRES_PASSWORD')
    postgres_db = os.getenv('POSTGRES_DB', 'medhistory')
    
    mongo_user = os.getenv('MONGO_INITDB_ROOT_USERNAME', 'admin')
    mongo_password = os.getenv('MONGO_PASSWORD')
    mongo_db = os.getenv('MONGO_INITDB_DATABASE', 'medhistory')
    
    if not all([postgres_user, postgres_password, mongo_password]):
        print_error("Не все параметры подключения найдены в .env.production!")
        sys.exit(1)
    
    # Параметры SSH
    ssh_host = '158.160.99.232'
    ssh_user = 'yc-user'
    
    # Локальные порты для туннелей
    postgres_local_port = 15432
    mongo_local_port = 27018
    
    # URL для подключения через туннели
    postgres_url = f"postgresql://{postgres_user}:{postgres_password}@localhost:{postgres_local_port}/{postgres_db}"
    mongo_url = f"mongodb://{mongo_user}:{mongo_password}@localhost:{mongo_local_port}/{mongo_db}?authSource=admin"
    
    print_info(f"PostgreSQL: через SSH туннель на {ssh_host}:5432")
    print_info(f"MongoDB: через SSH туннель на {ssh_host}:27017")
    
    # Создаем SSH туннели
    print()
    postgres_tunnel = SSHTunnel(
        ssh_host=ssh_host,
        ssh_user=ssh_user,
        remote_host='localhost',
        remote_port=5432,
        local_port=postgres_local_port,
        name='PostgreSQL'
    )
    
    mongo_tunnel = SSHTunnel(
        ssh_host=ssh_host,
        ssh_user=ssh_user,
        remote_host='localhost',
        remote_port=27017,
        local_port=mongo_local_port,
        name='MongoDB'
    )
    
    try:
        postgres_tunnel.start()
        mongo_tunnel.start()
        
        # Получаем данные из обеих БД
        print()
        synonyms_map, all_synonyms = await get_synonyms_from_db(postgres_url)
        mongo_analytes = await get_analytes_from_mongodb(mongo_url)
        
        # Анализируем соответствия
        print()
        print_header("📊 Анализ соответствий")
        
        matched = []
        unmatched = []
        
        for analyte in mongo_analytes:
            name_lower = analyte["name_lower"]
            
            if name_lower in all_synonyms:
                matched.append(analyte)
            else:
                unmatched.append(analyte)
        
        # Статистика
        total_count = sum(a["count"] for a in mongo_analytes)
        matched_count = sum(a["count"] for a in matched)
        unmatched_count = sum(a["count"] for a in unmatched)
        
        print_success(f"Найдены синонимы: {len(matched)} названий ({matched_count} измерений, {matched_count/total_count*100:.1f}%)")
        
        if unmatched:
            print_warning(f"Не найдены синонимы: {len(unmatched)} названий ({unmatched_count} измерений, {unmatched_count/total_count*100:.1f}%)")
            print()
            print_header("❌ Названия без синонимов (топ-50)")
            
            print(f"{'Название':<50} {'Кол-во':<10}")
            print("-" * 62)
            
            for analyte in unmatched[:50]:
                name = analyte["name"][:47] + "..." if len(analyte["name"]) > 50 else analyte["name"]
                count = analyte["count"]
                print(f"{name:<50} {count:<10}")
            
            if len(unmatched) > 50:
                print(f"\n... и ещё {len(unmatched) - 50} названий")
        else:
            print_success("Все названия из MongoDB имеют синонимы в справочнике!")
        
        # Рекомендации
        print()
        print_header("💡 Рекомендации")
        
        if unmatched:
            print_warning("Необходимо добавить синонимы для отсутствующих названий:")
            print_info("1. Создайте SQL скрипт для добавления синонимов")
            print_info("2. Или используйте административный интерфейс для добавления")
            print_info("3. После добавления синонимов перезапустите backend для обновления кэша")
            
            # Генерируем пример SQL для топ-20
            print()
            print_info("Пример SQL для добавления синонимов (топ-20):")
            print()
            print("```sql")
            for analyte in unmatched[:20]:
                name = analyte["name"]
                name_lower = analyte["name_lower"]
                # Пытаемся найти похожее каноническое название
                possible_canonical = name.split("(")[0].strip() if "(" in name else name
                print(f"-- {name} ({analyte['count']} измерений)")
                print(f"-- TODO: Найти canonical_name для этого анализа")
                print(f"-- INSERT INTO analyte_synonyms (analyte_id, synonym, synonym_lower, source)")
                print(f"-- SELECT id, '{name}', '{name_lower}', 'import'")
                print(f"-- FROM analyte_standards WHERE canonical_name = 'TODO: canonical_name';")
                print()
            print("```")
        
    except Exception as e:
        print_error(f"Ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        # Закрываем SSH туннели
        print()
        mongo_tunnel.stop()
        postgres_tunnel.stop()


if __name__ == "__main__":
    asyncio.run(main())
