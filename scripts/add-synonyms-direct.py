#!/usr/bin/env python3
"""
Скрипт для прямого добавления синонимов к существующим анализам.
Использует маппинг MongoDB название → PostgreSQL canonical_name.
"""

import os
import sys
import asyncio
from pathlib import Path
import subprocess
import time
import signal
import uuid

import asyncpg
from dotenv import load_dotenv


class Colors:
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    OKCYAN = '\033[96m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_success(text: str):
    print(f"{Colors.OKGREEN}✓ {text}{Colors.ENDC}")


def print_info(text: str):
    print(f"{Colors.OKCYAN}ℹ {text}{Colors.ENDC}")


def print_warning(text: str):
    print(f"{Colors.WARNING}⚠ {text}{Colors.ENDC}")


def print_error(text: str):
    print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")


class SSHTunnel:
    def __init__(self, ssh_host: str, ssh_user: str, remote_port: int, local_port: int, name: str):
        self.ssh_host = ssh_host
        self.ssh_user = ssh_user
        self.remote_port = remote_port
        self.local_port = local_port
        self.name = name
        self.process = None
    
    def start(self):
        cmd = ['ssh', '-N', '-L', f'{self.local_port}:localhost:{self.remote_port}',
               f'{self.ssh_user}@{self.ssh_host}', '-o', 'StrictHostKeyChecking=no']
        self.process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        time.sleep(2)
        if self.process.poll() is not None:
            raise Exception(f"Туннель {self.name} не удалось создать")
        print_success(f"SSH туннель {self.name} установлен")
    
    def stop(self):
        if self.process:
            self.process.send_signal(signal.SIGTERM)
            try:
                self.process.wait(timeout=5)
            except:
                self.process.kill()


# Маппинг: MongoDB название → (canonical_name, категория)
SYNONYM_MAPPINGS = {
    # Общий анализ крови
    "Гемоглобин": ("Гемоглобин", "Общий анализ крови"),
    "Эритроциты": ("Эритроциты", "Общий анализ крови"),
    "Лейкоциты": ("Лейкоциты", "Общий анализ крови"),
    "Тромбоциты": ("Тромбоциты", "Общий анализ крови"),
    "Гематокрит": ("Гематокрит", "Общий анализ крови"),
    "СОЭ": ("СОЭ", "Общий анализ крови"),
    "Нейтрофилы": ("Нейтрофилы (%)", "Общий анализ крови"),
    "Лимфоциты": ("Лимфоциты (%)", "Общий анализ крови"),
    "Моноциты": ("Моноциты (%)", "Общий анализ крови"),
    "Эозинофилы": ("Эозинофилы (%)", "Общий анализ крови"),
    "Базофилы": ("Базофилы (%)", "Общий анализ крови"),
    "Средний объем эритроцита": ("MCV (средний объем эритроцита)", "Общий анализ крови"),
    "Ср.объем эритроцита": ("MCV (средний объем эритроцита)", "Общий анализ крови"),
    "Среднее содержание гемоглобина в эритроците": ("MCH (среднее содержание Hb)", "Общий анализ крови"),
    "Средняя концентрация гемоглобина в эритроците": ("MCHC (средняя концентрация Hb)", "Общий анализ крови"),
    "Ср. концентрация гемоглобина в эритроците": ("MCHC (средняя концентрация Hb)", "Общий анализ крови"),
    "Ширина распределения эритроцитов": ("RDW (ширина распределения эритроцитов)", "Общий анализ крови"),
    "Средний объем тромбоцитов": ("MPV (средний объем тромбоцитов)", "Общий анализ крови"),
    "Ширина распределения тромбоцитов по объему": ("PDW (ширина распределения тромбоцитов)", "Общий анализ крови"),
    "Процент крупных тромбоцитов": ("P-LCR (процент крупных тромбоцитов)", "Общий анализ крови"),
    "Тромбоцитокрит": ("PCT (тромбоцитокрит)", "Общий анализ крови"),
    "Тромбокрит": ("PCT (тромбоцитокрит)", "Общий анализ крови"),
    "Общий объем тромбоцитов в крови": ("PCT (тромбоцитокрит)", "Общий анализ крови"),
    "Нормобласты": ("Нормобласты", "Общий анализ крови"),
    "Отн количество нормобластов": ("Нормобласты", "Общий анализ крови"),
    "Абс количество нормобластов": ("Нормобласты", "Общий анализ крови"),
    
    # Гормоны
    "Тиреотропный гормон (ТТГ)": ("ТТГ", "Гормоны"),
    "ТТГ": ("ТТГ", "Гормоны"),
    "Тироксин свободный (Т4)": ("Т4 свободный", "Гормоны"),
    "Т4 свободный": ("Т4 свободный", "Гормоны"),
    "Трийодтиронин свободный (Т3)": ("Т3 свободный", "Гормоны"),
    "Трийодтиронин свободный (Т3 св.)": ("Т3 свободный", "Гормоны"),
    "Т3 свободный": ("Т3 свободный", "Гормоны"),
    "АТ-ТПО": ("АТ-ТПО", "Гормоны"),
    
    # Биохимия
    "Глюкоза": ("Глюкоза", "Биохимия крови"),
    "Общий белок": ("Общий белок", "Биохимия крови"),
    "Билирубин общий": ("Билирубин общий", "Биохимия крови"),
    "Билирубин прямой": ("Билирубин прямой", "Биохимия крови"),
    "Аланинаминотрансфераза": ("АЛТ", "Биохимия крови"),
    "Аспартатаминотрансфераза": ("АСТ", "Биохимия крови"),
    "Креатинин": ("Креатинин", "Биохимия крови"),
    "Магний": ("Магний", "Витамины и микроэлементы"),
    "Липаза": ("Липаза", "Биохимия крови"),
    
    # Липидный профиль
    "Холестерин общий": ("Холестерин общий", "Липидный профиль"),
    "Холестерин-неЛПВП": ("Холестерин-неЛПВП", "Липидный профиль"),
    
    # Маркеры воспаления
    "С-реактивный белок": ("С-реактивный белок", "Маркеры воспаления"),
    
    # Другое
    "Латентная железосвязывающая способность": ("ЛЖСС", "Биохимия крови"),
    "Энтерококки": ("Энтерококки", "Микробиология"),
    "E.coli гемолитические": ("E.coli гемолитические", "Микробиология"),
    "Антитела к эндомизию IgA": ("Антитела к эндомизию IgA", "Аутоиммунные маркеры"),
}


async def main():
    print(f"\n{Colors.BOLD}🔧 Прямое добавление синонимов{Colors.ENDC}\n")
    
    project_root = Path(__file__).parent.parent
    env_prod = project_root / '.env.production'
    
    if not env_prod.exists():
        print_error("Файл .env.production не найден!")
        sys.exit(1)
    
    load_dotenv(env_prod)
    
    postgres_user = os.getenv('POSTGRES_USER')
    postgres_password = os.getenv('POSTGRES_PASSWORD')
    postgres_db = os.getenv('POSTGRES_DB', 'medhistory')
    
    if not postgres_user or not postgres_password:
        print_error("Параметры PostgreSQL не найдены!")
        sys.exit(1)
    
    ssh_host = '158.160.99.232'
    ssh_user = 'yc-user'
    local_port = 15432
    
    postgres_url = f"postgresql://{postgres_user}:{postgres_password}@localhost:{local_port}/{postgres_db}"
    
    tunnel = SSHTunnel(ssh_host, ssh_user, 5432, local_port, 'PostgreSQL')
    
    try:
        tunnel.start()
        print()
        
        conn = await asyncpg.connect(postgres_url)
        
        try:
            # Получаем все канонические названия
            query = """
                SELECT a.id, a.canonical_name, c.name as category_name
                FROM analyte_standards a
                JOIN analyte_categories c ON c.id = a.category_id
                WHERE a.is_active = TRUE
            """
            analytes = await conn.fetch(query)
            analytes_map = {row['canonical_name']: (str(row['id']), row['category_name']) for row in analytes}
            
            # Получаем существующие синонимы
            existing_query = "SELECT synonym_lower FROM analyte_synonyms"
            existing = await conn.fetch(existing_query)
            existing_set = set(row['synonym_lower'] for row in existing)
            
            print_info(f"Найдено {len(analytes_map)} анализов в справочнике")
            print_info(f"Существует {len(existing_set)} синонимов")
            print()
            
            # Готовим данные для добавления
            to_add = []
            not_found = []
            
            for synonym, (canonical, expected_cat) in SYNONYM_MAPPINGS.items():
                synonym_lower = synonym.lower()
                
                # Пропускаем уже существующие
                if synonym_lower in existing_set:
                    continue
                
                # Проверяем, есть ли канонический анализ
                if canonical in analytes_map:
                    analyte_id, category = analytes_map[canonical]
                    to_add.append((analyte_id, synonym, synonym_lower, canonical, category))
                else:
                    not_found.append((synonym, canonical, expected_cat))
            
            if to_add:
                print_warning(f"Будет добавлено {len(to_add)} синонимов:")
                print()
                
                # Группируем по категориям
                by_category = {}
                for _, syn, _, can, cat in to_add:
                    if cat not in by_category:
                        by_category[cat] = []
                    by_category[cat].append((syn, can))
                
                for category, items in sorted(by_category.items()):
                    print(f"  {category}:")
                    for syn, can in items[:5]:
                        print(f"    • '{syn}' → '{can}'")
                    if len(items) > 5:
                        print(f"    ... и ещё {len(items) - 5}")
                    print()
                
                response = input(f"{Colors.BOLD}Добавить синонимы? (yes/no): {Colors.ENDC}").strip().lower()
                
                if response in ['yes', 'y', 'да']:
                    added = 0
                    for analyte_id, synonym, synonym_lower, _, _ in to_add:
                        try:
                            await conn.execute("""
                                INSERT INTO analyte_synonyms (id, analyte_id, synonym, synonym_lower, source, is_primary, created_at)
                                VALUES ($1, $2, $3, $4, $5, $6, NOW())
                            """, str(uuid.uuid4()), analyte_id, synonym, synonym_lower, 'manual_import', False)
                            added += 1
                        except Exception as e:
                            print_warning(f"  Не удалось добавить '{synonym}': {e}")
                    
                    print()
                    print_success(f"✅ Добавлено {added} синонимов!")
                    print()
                    print_warning("⚠️  ВАЖНО: Перезапустите backend для обновления кэша:")
                    print_info("  ssh yc-user@158.160.99.232 'cd ~/medhistory && docker compose restart backend'")
                else:
                    print_info("Отменено")
            else:
                print_success("Все синонимы уже добавлены!")
            
            if not_found:
                print()
                print_error(f"⚠️ Не найдены канонические анализы ({len(not_found)}):")
                for syn, can, cat in not_found[:10]:
                    print(f"  • '{syn}' → ожидался '{can}' в категории '{cat}'")
                if len(not_found) > 10:
                    print(f"  ... и ещё {len(not_found) - 10}")
                print()
                print_info("Эти анализы нужно сначала добавить в справочник")
        
        finally:
            await conn.close()
    
    except Exception as e:
        print_error(f"Ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        print()
        tunnel.stop()


if __name__ == "__main__":
    asyncio.run(main())
