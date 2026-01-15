#!/usr/bin/env python3
"""
Скрипт для автоматического добавления недостающих синонимов анализов.

Сопоставляет названия из MongoDB с каноническими названиями в PostgreSQL
и добавляет недостающие синонимы.
"""

import os
import sys
import asyncio
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict
import subprocess
import time
import signal
import uuid

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
        print_info(f"Создание SSH туннеля {self.name}: localhost:{self.local_port} -> {self.ssh_host}:{self.remote_port}")
        
        cmd = [
            'ssh', '-N',
            '-L', f'{self.local_port}:{self.remote_host}:{self.remote_port}',
            f'{self.ssh_user}@{self.ssh_host}',
            '-o', 'StrictHostKeyChecking=no',
            '-o', 'ServerAliveInterval=60'
        ]
        
        self.process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        time.sleep(2)
        
        if self.process.poll() is not None:
            _, stderr = self.process.communicate()
            raise Exception(f"Не удалось создать SSH туннель {self.name}: {stderr.decode()}")
        
        print_success(f"SSH туннель {self.name} установлен")
    
    def stop(self):
        if self.process:
            print_info(f"Закрытие SSH туннеля {self.name}...")
            self.process.send_signal(signal.SIGTERM)
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            print_success(f"SSH туннель {self.name} закрыт")


def fuzzy_match(name1: str, name2: str) -> float:
    """Простое нечеткое сопоставление названий (0.0 - 1.0)"""
    n1 = name1.lower().strip()
    n2 = name2.lower().strip()
    
    # Точное совпадение
    if n1 == n2:
        return 1.0
    
    # Убираем скобки и содержимое
    import re
    n1_clean = re.sub(r'\([^)]*\)', '', n1).strip()
    n2_clean = re.sub(r'\([^)]*\)', '', n2).strip()
    
    if n1_clean == n2_clean:
        return 0.95
    
    # Проверяем вхождение
    if n1_clean in n2_clean or n2_clean in n1_clean:
        return 0.85
    
    # Проверяем первые слова
    words1 = n1_clean.split()
    words2 = n2_clean.split()
    
    if words1 and words2 and words1[0] == words2[0]:
        common = set(words1) & set(words2)
        if len(common) >= min(len(words1), len(words2)) * 0.7:
            return 0.75
    
    return 0.0


async def get_analytes_from_db(db_url: str) -> Dict[str, Tuple[str, str]]:
    """Получает анализы из PostgreSQL: canonical_name -> (id, category_name)"""
    print_info("Загрузка анализов из PostgreSQL...")
    
    db_url = db_url.replace('postgresql+asyncpg://', 'postgresql://')
    conn = await asyncpg.connect(db_url)
    
    try:
        query = """
            SELECT 
                a.id,
                a.canonical_name,
                c.name as category_name
            FROM analyte_standards a
            JOIN analyte_categories c ON c.id = a.category_id
            WHERE a.is_active = TRUE
        """
        rows = await conn.fetch(query)
        
        analytes = {}
        for row in rows:
            analytes[row['canonical_name']] = (str(row['id']), row['category_name'])
        
        print_success(f"Загружено {len(analytes)} анализов")
        return analytes
        
    finally:
        await conn.close()


async def get_existing_synonyms(db_url: str) -> Set[str]:
    """Получает существующие синонимы (lowercase)"""
    print_info("Загрузка существующих синонимов...")
    
    db_url = db_url.replace('postgresql+asyncpg://', 'postgresql://')
    conn = await asyncpg.connect(db_url)
    
    try:
        query = "SELECT synonym_lower FROM analyte_synonyms"
        rows = await conn.fetch(query)
        
        synonyms = set(row['synonym_lower'] for row in rows)
        print_success(f"Загружено {len(synonyms)} существующих синонимов")
        return synonyms
        
    finally:
        await conn.close()


async def get_mongodb_names(mongo_url: str) -> List[Dict]:
    """Получает уникальные названия из MongoDB"""
    print_info("Загрузка названий из MongoDB...")
    
    client = motor_asyncio.AsyncIOMotorClient(mongo_url)
    db = client.get_database('medhistory')
    collection = db.get_collection('document_metadata')
    
    try:
        pipeline = [
            {"$project": {"extracted_data.lab_results": 1}},
            {"$unwind": "$extracted_data.lab_results"},
            {
                "$group": {
                    "_id": {"name_lower": {"$toLower": "$extracted_data.lab_results.test_name"}},
                    "name": {"$first": "$extracted_data.lab_results.test_name"},
                    "count": {"$sum": 1}
                }
            },
            {"$sort": {"count": -1}},
        ]
        
        names = []
        async for doc in collection.aggregate(pipeline):
            name = doc.get("name", "")
            name_lower = doc.get("_id", {}).get("name_lower", "").strip()
            count = doc.get("count", 0)
            
            if name_lower:
                names.append({"name": name, "name_lower": name_lower, "count": count})
        
        print_success(f"Найдено {len(names)} названий в MongoDB")
        return names
        
    finally:
        client.close()


async def add_synonyms(db_url: str, synonyms_to_add: List[Tuple[str, str, str]]):
    """Добавляет синонимы в БД: [(analyte_id, synonym, synonym_lower), ...]"""
    if not synonyms_to_add:
        print_info("Нет синонимов для добавления")
        return
    
    print_info(f"Добавление {len(synonyms_to_add)} синонимов...")
    
    db_url = db_url.replace('postgresql+asyncpg://', 'postgresql://')
    conn = await asyncpg.connect(db_url)
    
    try:
        added = 0
        for analyte_id, synonym, synonym_lower in synonyms_to_add:
            try:
                await conn.execute("""
                    INSERT INTO analyte_synonyms (id, analyte_id, synonym, synonym_lower, source, is_primary, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6, NOW())
                """, str(uuid.uuid4()), analyte_id, synonym, synonym_lower, 'auto_import', False)
                added += 1
            except Exception as e:
                print_warning(f"  Не удалось добавить '{synonym}': {e}")
        
        print_success(f"Добавлено {added} синонимов")
        
    finally:
        await conn.close()


async def main():
    print_header("🔧 Автоматическое добавление синонимов")
    
    project_root = Path(__file__).parent.parent
    env_prod = project_root / '.env.production'
    
    if not env_prod.exists():
        print_error(f"Файл {env_prod} не найден!")
        sys.exit(1)
    
    load_dotenv(env_prod)
    
    postgres_user = os.getenv('POSTGRES_USER')
    postgres_password = os.getenv('POSTGRES_PASSWORD')
    postgres_db = os.getenv('POSTGRES_DB', 'medhistory')
    
    mongo_user = os.getenv('MONGO_INITDB_ROOT_USERNAME', 'admin')
    mongo_password = os.getenv('MONGO_PASSWORD')
    mongo_db = os.getenv('MONGO_INITDB_DATABASE', 'medhistory')
    
    if not all([postgres_user, postgres_password, mongo_password]):
        print_error("Не все параметры найдены в .env.production!")
        sys.exit(1)
    
    ssh_host = '158.160.99.232'
    ssh_user = 'yc-user'
    postgres_local_port = 15432
    mongo_local_port = 27018
    
    postgres_url = f"postgresql://{postgres_user}:{postgres_password}@localhost:{postgres_local_port}/{postgres_db}"
    mongo_url = f"mongodb://{mongo_user}:{mongo_password}@localhost:{mongo_local_port}/{mongo_db}?authSource=admin"
    
    postgres_tunnel = SSHTunnel(ssh_host, ssh_user, 'localhost', 5432, postgres_local_port, 'PostgreSQL')
    mongo_tunnel = SSHTunnel(ssh_host, ssh_user, 'localhost', 27017, mongo_local_port, 'MongoDB')
    
    try:
        postgres_tunnel.start()
        mongo_tunnel.start()
        
        print()
        
        # Получаем данные
        analytes_map = await get_analytes_from_db(postgres_url)
        existing_synonyms = await get_existing_synonyms(postgres_url)
        mongodb_names = await get_mongodb_names(mongo_url)
        
        # Анализируем и сопоставляем
        print()
        print_header("🔍 Сопоставление названий")
        
        to_add = []
        unmatched = []
        
        for mongo_name in mongodb_names:
            name = mongo_name["name"]
            name_lower = mongo_name["name_lower"]
            count = mongo_name["count"]
            
            # Пропускаем, если синоним уже есть
            if name_lower in existing_synonyms:
                continue
            
            # Ищем лучшее совпадение
            best_match = None
            best_score = 0.0
            
            for canonical, (analyte_id, category) in analytes_map.items():
                score = fuzzy_match(name, canonical)
                if score > best_score:
                    best_score = score
                    best_match = (canonical, analyte_id, category)
            
            # Если совпадение хорошее - добавляем
            if best_score >= 0.75:
                canonical, analyte_id, category = best_match
                to_add.append((analyte_id, name, name_lower, canonical, best_score, count))
                print_success(f"  '{name}' → '{canonical}' (score: {best_score:.2f}, {count} изм.)")
            else:
                unmatched.append((name, count, best_score))
        
        if to_add:
            print()
            print_header(f"📝 Добавление {len(to_add)} синонимов")
            
            print_warning("Будут добавлены следующие синонимы:")
            for _, synonym, _, canonical, score, count in to_add[:20]:
                print(f"  • '{synonym}' → '{canonical}' ({count} изм.)")
            
            if len(to_add) > 20:
                print(f"  ... и ещё {len(to_add) - 20} синонимов")
            
            print()
            response = input(f"{Colors.BOLD}Добавить синонимы? (yes/no): {Colors.ENDC}").strip().lower()
            
            if response in ['yes', 'y', 'да']:
                synonyms_data = [(aid, syn, syn_lower) for aid, syn, syn_lower, _, _, _ in to_add]
                await add_synonyms(postgres_url, synonyms_data)
                
                print()
                print_success(f"✅ Добавлено {len(synonyms_data)} синонимов!")
                print_warning("⚠️  Перезапустите backend для обновления кэша:")
                print_info("  ssh yc-user@158.160.99.232 'cd ~/medhistory && docker compose restart backend'")
            else:
                print_info("Отменено пользователем")
        else:
            print_warning("Нет синонимов для автоматического добавления")
        
        if unmatched:
            print()
            print_header(f"❌ Не удалось сопоставить ({len(unmatched)} названий)")
            print_warning("Эти названия требуют ручного добавления:")
            for name, count, score in unmatched[:10]:
                print(f"  • '{name}' ({count} изм., best score: {score:.2f})")
            if len(unmatched) > 10:
                print(f"  ... и ещё {len(unmatched) - 10} названий")
    
    except Exception as e:
        print_error(f"Ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        print()
        mongo_tunnel.stop()
        postgres_tunnel.stop()


if __name__ == "__main__":
    asyncio.run(main())
