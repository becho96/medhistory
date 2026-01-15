#!/usr/bin/env python3
"""
Умный скрипт добавления синонимов с учетом единиц измерения.
Анализирует единицы измерения в MongoDB для правильного сопоставления.
"""

import os
import sys
import asyncio
from pathlib import Path
from typing import Dict, List, Set, Tuple
import subprocess
import time
import signal
import uuid
import re

import asyncpg
from motor import motor_asyncio
from dotenv import load_dotenv


class Colors:
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    OKCYAN = '\033[96m'
    BOLD = '\033[1m'
    ENDC = '\033[0m'


def print_success(text: str):
    print(f"{Colors.OKGREEN}✓ {text}{Colors.ENDC}")


def print_info(text: str):
    print(f"{Colors.OKCYAN}ℹ {text}{Colors.ENDC}")


def print_warning(text: str):
    print(f"{Colors.WARNING}⚠ {text}{Colors.ENDC}")


def print_error(text: str):
    print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")


class SSHTunnel:
    def __init__(self, ssh_host, ssh_user, remote_host, remote_port, local_port, name):
        self.ssh_host = ssh_host
        self.ssh_user = ssh_user
        self.remote_host = remote_host
        self.remote_port = remote_port
        self.local_port = local_port
        self.name = name
        self.process = None
    
    def start(self):
        print_info(f"SSH туннель {self.name}...")
        cmd = ['ssh', '-N', '-L', f'{self.local_port}:{self.remote_host}:{self.remote_port}',
               f'{self.ssh_user}@{self.ssh_host}', '-o', 'StrictHostKeyChecking=no',
               '-o', 'ServerAliveInterval=60']
        self.process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        time.sleep(2)
        if self.process.poll() is not None:
            raise Exception(f"SSH туннель {self.name} не удался")
        print_success(f"SSH туннель {self.name} установлен")
    
    def stop(self):
        if self.process:
            self.process.send_signal(signal.SIGTERM)
            try:
                self.process.wait(timeout=3)
            except:
                self.process.kill()


async def get_analytes_with_synonyms(db_url: str) -> Dict[str, Tuple[str, Set[str]]]:
    """Возвращает: canonical_name_lower -> (analyte_id, set(existing_synonyms_lower))"""
    db_url = db_url.replace('postgresql+asyncpg://', 'postgresql://')
    conn = await asyncpg.connect(db_url)
    
    try:
        # Получаем все анализы
        query = """
            SELECT id, LOWER(canonical_name) as canonical_name_lower
            FROM analyte_standards
            WHERE is_active = TRUE
        """
        rows = await conn.fetch(query)
        analytes = {row['canonical_name_lower']: (str(row['id']), set()) for row in rows}
        
        # Получаем существующие синонимы
        syn_query = """
            SELECT a.canonical_name, s.synonym_lower
            FROM analyte_synonyms s
            JOIN analyte_standards a ON a.id = s.analyte_id
        """
        syn_rows = await conn.fetch(syn_query)
        for row in syn_rows:
            canonical_lower = row['canonical_name'].lower()
            if canonical_lower in analytes:
                analytes[canonical_lower][1].add(row['synonym_lower'])
        
        print_success(f"Загружено {len(analytes)} анализов с синонимами")
        return analytes
        
    finally:
        await conn.close()


async def get_mongodb_data(mongo_url: str) -> List[Dict]:
    """Получает названия с единицами измерения"""
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
                        "name_lower": {"$toLower": "$extracted_data.lab_results.test_name"},
                        "unit": "$extracted_data.lab_results.unit"
                    },
                    "name": {"$first": "$extracted_data.lab_results.test_name"},
                    "unit": {"$first": "$extracted_data.lab_results.unit"},
                    "count": {"$sum": 1}
                }
            },
            {"$sort": {"count": -1}},
        ]
        
        data = []
        async for doc in collection.aggregate(pipeline):
            name = doc.get("name", "")
            name_lower = doc.get("_id", {}).get("name_lower", "").strip()
            unit = doc.get("unit", "") or ""
            count = doc.get("count", 0)
            
            if name_lower:
                data.append({
                    "name": name,
                    "name_lower": name_lower,
                    "unit": unit,
                    "count": count
                })
        
        print_success(f"Загружено {len(data)} комбинаций название+единица из MongoDB")
        return data
        
    finally:
        client.close()


def match_analyte(mongo_name: str, mongo_unit: str, analytes: Dict) -> Tuple[str, str, float]:
    """
    Сопоставляет название из MongoDB с анализом из справочника.
    Возвращает: (canonical_name_lower, analyte_id, confidence_score)
    """
    mongo_name_clean = mongo_name.lower().strip()
    mongo_unit_clean = (mongo_unit or "").lower().strip()
    has_percent = '%' in mongo_unit_clean
    
    best_match = None
    best_score = 0.0
    
    for canonical_lower, (analyte_id, _) in analytes.items():
        score = 0.0
        canonical_clean = canonical_lower.strip()
        
        # Проверяем базовые совпадения
        base_mongo = re.sub(r'\([^)]*\)', '', mongo_name_clean).strip()
        base_canonical = re.sub(r'\([^)]*\)', '', canonical_clean).strip()
        
        # Точное совпадение базовых названий
        if base_mongo == base_canonical:
            score = 0.9
            # Дополнительная проверка для % vs абс
            if '(абс)' in canonical_clean or '(%)' in canonical_clean:
                if has_percent and '(%)' in canonical_clean:
                    score = 1.0
                elif not has_percent and '(абс)' in canonical_clean:
                    score = 1.0
                else:
                    score = 0.5  # Не та версия
        # Частичное совпадение
        elif base_mongo in base_canonical or base_canonical in base_mongo:
            score = 0.7
            # Проверка на % vs абс
            if '(абс)' in canonical_clean or '(%)' in canonical_clean:
                if has_percent and '(%)' in canonical_clean:
                    score = 0.9
                elif not has_percent and '(абс)' in canonical_clean:
                    score = 0.9
                else:
                    score = 0.4
        
        # Проверяем особые случаи
        # ТТГ
        if 'ттг' in mongo_name_clean and 'ттг' in canonical_clean:
            score = max(score, 0.95)
        # Т4
        if ('т4' in mongo_name_clean or 'тироксин' in mongo_name_clean) and 'т4' in canonical_clean:
            score = max(score, 0.9)
        # Т3
        if ('т3' in mongo_name_clean or 'трийодтиронин' in mongo_name_clean) and 'т3' in canonical_clean:
            score = max(score, 0.9)
        # АЛТ/Аланинаминотрансфераза
        if ('алт' in mongo_name_clean or 'аланинаминотрансфераза' in mongo_name_clean) and 'алт' in canonical_clean:
            score = max(score, 0.95)
        # АСТ/Аспартатаминотрансфераза
        if ('аст' in mongo_name_clean or 'аспартатаминотрансфераза' in mongo_name_clean) and 'аст' in canonical_clean:
            score = max(score, 0.95)
        
        if score > best_score:
            best_score = score
            best_match = (canonical_lower, analyte_id)
    
    if best_match and best_score >= 0.7:
        return (best_match[0], best_match[1], best_score)
    return (None, None, 0.0)


async def add_synonyms(db_url: str, synonyms: List[Tuple[str, str, str]]):
    """Добавляет синонимы: [(analyte_id, synonym, synonym_lower), ...]"""
    db_url = db_url.replace('postgresql+asyncpg://', 'postgresql://')
    conn = await asyncpg.connect(db_url)
    
    try:
        added = 0
        for analyte_id, synonym, synonym_lower in synonyms:
            try:
                await conn.execute("""
                    INSERT INTO analyte_synonyms (id, analyte_id, synonym, synonym_lower, source, is_primary, created_at)
                    VALUES ($1, $2, $3, $4, 'smart_import', false, NOW())
                    ON CONFLICT DO NOTHING
                """, str(uuid.uuid4()), analyte_id, synonym, synonym_lower)
                added += 1
            except:
                pass
        
        print_success(f"Добавлено {added} синонимов")
        return added
        
    finally:
        await conn.close()


async def main():
    print("\n" + "="*70)
    print("🧠 Умное добавление синонимов с анализом единиц измерения")
    print("="*70 + "\n")
    
    project_root = Path(__file__).parent.parent
    env_prod = project_root / '.env.production'
    
    if not env_prod.exists():
        print_error("Файл .env.production не найден!")
        sys.exit(1)
    
    load_dotenv(env_prod)
    
    postgres_user = os.getenv('POSTGRES_USER')
    postgres_password = os.getenv('POSTGRES_PASSWORD')
    postgres_db = os.getenv('POSTGRES_DB', 'medhistory')
    mongo_user = os.getenv('MONGO_INITDB_ROOT_USERNAME', 'admin')
    mongo_password = os.getenv('MONGO_PASSWORD')
    mongo_db = os.getenv('MONGO_INITDB_DATABASE', 'medhistory')
    
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
        
        analytes = await get_analytes_with_synonyms(postgres_url)
        mongodb_data = await get_mongodb_data(mongo_url)
        
        print("\n" + "="*70)
        print("🔍 Сопоставление с учетом единиц измерения")
        print("="*70 + "\n")
        
        to_add = []
        matched = 0
        unmatched = []
        
        for item in mongodb_data:
            name = item["name"]
            name_lower = item["name_lower"]
            unit = item["unit"]
            count = item["count"]
            
            # Проверяем, есть ли уже этот синоним
            already_exists = False
            for canonical_lower, (_, existing_synonyms) in analytes.items():
                if name_lower in existing_synonyms:
                    already_exists = True
                    break
            
            if already_exists:
                matched += 1
                continue
            
            # Ищем соответствие
            canonical_lower, analyte_id, score = match_analyte(name, unit, analytes)
            
            if canonical_lower and score >= 0.7:
                to_add.append((analyte_id, name, name_lower, canonical_lower, score, count, unit))
                print_success(f"'{name}' [{unit}] → '{canonical_lower}' (score: {score:.2f}, {count} изм.)")
                matched += 1
            else:
                unmatched.append((name, unit, count))
        
        print(f"\n✓ Уже есть синонимы: {matched - len(to_add)}")
        print(f"✓ Найдено новых соответствий: {len(to_add)}")
        print(f"⚠ Не удалось сопоставить: {len(unmatched)}\n")
        
        if to_add:
            print("="*70)
            print(f"Будет добавлено {len(to_add)} синонимов:")
            print("="*70)
            for _, syn, _, canonical, score, count, unit in to_add[:15]:
                print(f"  • '{syn}' [{unit}] → '{canonical}' ({count} изм.)")
            if len(to_add) > 15:
                print(f"  ... и ещё {len(to_add) - 15}")
            
            print()
            response = input(f"{Colors.BOLD}Добавить синонимы? (yes/no): {Colors.ENDC}").strip().lower()
            
            if response in ['yes', 'y', 'да']:
                synonyms_data = [(aid, syn, syn_lower) for aid, syn, syn_lower, _, _, _, _ in to_add]
                added = await add_synonyms(postgres_url, synonyms_data)
                
                print()
                print_success(f"✅ Добавлено {added} синонимов!")
                print_warning("\n⚠️  ВАЖНО: Перезапустите backend!")
                print_info("  ssh yc-user@158.160.99.232 'cd ~/medhistory && docker compose restart backend'")
            else:
                print_info("Отменено")
        
        if unmatched:
            print(f"\n⚠ Требуют ручного добавления ({len(unmatched)}):")
            for name, unit, count in unmatched[:10]:
                print(f"  • '{name}' [{unit}] ({count} изм.)")
    
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
