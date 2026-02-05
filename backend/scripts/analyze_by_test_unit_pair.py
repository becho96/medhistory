#!/usr/bin/env python3
"""
Скрипт для анализа анализов по уникальным парам (название + единица измерения).
"""

import subprocess
import time
from pymongo import MongoClient
from collections import defaultdict
import csv
import argparse
import getpass
from urllib.parse import quote_plus


# Конфигурация
PROD_SERVER = "yc-user@93.77.182.26"
MONGO_PORT = 27017
LOCAL_MONGO_PORT = 27018


def create_ssh_tunnel():
    """Создает SSH туннель к MongoDB"""
    cmd = [
        "ssh", "-L", f"{LOCAL_MONGO_PORT}:localhost:{MONGO_PORT}",
        "-N", "-f", PROD_SERVER
    ]
    
    try:
        check_cmd = ["pgrep", "-f", f"ssh.*{LOCAL_MONGO_PORT}:localhost:{MONGO_PORT}"]
        result = subprocess.run(check_cmd, capture_output=True, text=True)
        
        if result.stdout.strip():
            print(f"✅ SSH туннель уже активен")
            return True
        
        subprocess.run(cmd, check=True)
        time.sleep(1)
        print(f"✅ SSH туннель создан")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка: {e}")
        return False


def close_ssh_tunnel():
    """Закрывает SSH туннель"""
    try:
        check_cmd = ["pgrep", "-f", f"ssh.*{LOCAL_MONGO_PORT}:localhost:{MONGO_PORT}"]
        result = subprocess.run(check_cmd, capture_output=True, text=True)
        
        if result.stdout.strip():
            pid = result.stdout.strip()
            subprocess.run(["kill", pid], check=True)
            print(f"✅ SSH туннель закрыт")
    except Exception as e:
        print(f"⚠️  Ошибка: {e}")


def analyze_by_test_unit_pairs(mongo_client, user_id=None):
    """
    Анализирует анализы по уникальным парам (test_name, unit).
    """
    db = mongo_client['medhistory']
    metadata_collection = db['document_metadata']
    
    print("🔍 Поиск документов с результатами анализов...")
    
    query = {
        'extracted_data.lab_results': {'$exists': True, '$ne': []}
    }
    
    if user_id:
        query['user_id'] = user_id
    
    documents = metadata_collection.find(query)
    
    # Структура: { (test_name, unit): set(reference_ranges) }
    test_unit_data = defaultdict(lambda: {
        'reference_ranges': set(),
        'count': 0
    })
    
    total_docs = 0
    total_results = 0
    
    print("📊 Обработка документов...")
    
    for doc in documents:
        total_docs += 1
        
        if total_docs % 10 == 0:
            print(f"   Обработано документов: {total_docs}")
        
        lab_results = doc.get('extracted_data', {}).get('lab_results', [])
        
        for result in lab_results:
            total_results += 1
            
            test_name = result.get('test_name')
            unit = result.get('unit')
            reference_range = result.get('reference_range')
            
            if not test_name:
                continue
            
            test_name = test_name.strip()
            
            # Если нет единицы, используем пустую строку
            unit_str = unit.strip() if unit else "Нет данных"
            
            # Ключ - пара (название, единица)
            key = (test_name, unit_str)
            
            test_unit_data[key]['count'] += 1
            
            if reference_range:
                test_unit_data[key]['reference_ranges'].add(reference_range.strip())
    
    print()
    print(f"✅ Обработано документов: {total_docs}")
    print(f"✅ Найдено результатов анализов: {total_results}")
    print(f"✅ Уникальных пар (анализ + единица): {len(test_unit_data)}")
    print()
    
    # Конвертируем sets в списки
    result_data = {}
    for (test_name, unit), data in test_unit_data.items():
        result_data[(test_name, unit)] = {
            'reference_ranges': sorted(list(data['reference_ranges'])),
            'count': data['count']
        }
    
    return result_data


def save_to_csv(test_unit_data, filename='test_unit_reference_ranges.csv'):
    """Сохраняет данные в CSV файл"""
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        
        # Заголовки
        writer.writerow([
            'Анализ (единица измерения)',
            'Диапазоны нормальных значений'
        ])
        
        # Сортируем по названию анализа, затем по единице
        sorted_data = sorted(
            test_unit_data.items(),
            key=lambda x: (x[0][0], x[0][1])  # сортировка по test_name, потом по unit
        )
        
        for (test_name, unit), data in sorted_data:
            # Формируем название с единицей
            if unit == "Нет данных":
                display_name = test_name
            else:
                display_name = f"{test_name} ({unit})"
            
            # Форматируем диапазоны
            ranges = data['reference_ranges']
            if not ranges:
                ranges_str = "Нет данных"
            else:
                ranges_str = "; ".join(ranges)
            
            writer.writerow([
                display_name,
                ranges_str
            ])
    
    print(f"✅ Данные сохранены в CSV: {filename}")


def main():
    parser = argparse.ArgumentParser(
        description='Анализ анализов по парам (название + единица)'
    )
    parser.add_argument('--mongo-user', default='admin')
    parser.add_argument('--mongo-password')
    parser.add_argument('--user-id')
    parser.add_argument('--output', default='test_unit_reference_ranges.csv')
    
    args = parser.parse_args()
    
    mongo_password = args.mongo_password or getpass.getpass(f"MongoDB password: ")
    mongo_uri = f"mongodb://{quote_plus(args.mongo_user)}:{quote_plus(mongo_password)}@localhost:{LOCAL_MONGO_PORT}/medhistory?authSource=admin"
    
    print("=" * 80)
    print("🔬 АНАЛИЗ ПО ПАРАМ (АНАЛИЗ + ЕДИНИЦА ИЗМЕРЕНИЯ)")
    print("=" * 80)
    print()
    
    if not create_ssh_tunnel():
        return
    
    try:
        print(f"🔌 Подключение к MongoDB...")
        mongo_client = MongoClient(mongo_uri)
        
        test_unit_data = analyze_by_test_unit_pairs(mongo_client, user_id=args.user_id)
        
        save_to_csv(test_unit_data, args.output)
        
        # Выводим первые 20 для примера
        print()
        print("=" * 80)
        print("📋 ПРИМЕРЫ (первые 20):")
        print("=" * 80)
        
        sorted_data = sorted(
            test_unit_data.items(),
            key=lambda x: (x[0][0], x[0][1])
        )
        
        for i, ((test_name, unit), data) in enumerate(sorted_data[:20], 1):
            if unit == "Нет данных":
                display_name = test_name
            else:
                display_name = f"{test_name} ({unit})"
            
            ranges = data['reference_ranges']
            ranges_str = "; ".join(ranges) if ranges else "Нет данных"
            
            print(f"{i}. {display_name}")
            print(f"   {ranges_str}")
            print()
        
        if len(sorted_data) > 20:
            print(f"... и еще {len(sorted_data) - 20} пар")
        
    finally:
        close_ssh_tunnel()
    
    print()
    print("✅ Готово!")


if __name__ == "__main__":
    main()
