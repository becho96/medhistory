"""
Скрипт инициализации библиотеки параметров здоровья в MongoDB
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from pymongo import MongoClient
from app.core.config import settings
from datetime import datetime

# 20 базовых параметров здоровья
HEALTH_PARAMETERS = [
    # 7 основных параметров (is_primary: True)
    {
        "key": "general_state",
        "label_ru": "Общее состояние",
        "type": "scale",
        "config": {
            "options": [
                {"value": "excellent", "label": "Отлично"},
                {"value": "good", "label": "Хорошо"},
                {"value": "satisfactory", "label": "Удовлетворительно"},
                {"value": "poor", "label": "Плохо"}
            ]
        },
        "is_primary": True,
        "sort_order": 1
    },
    {
        "key": "temperature",
        "label_ru": "Температура тела",
        "type": "number",
        "config": {
            "unit": "°C",
            "min": 35.0,
            "max": 42.0,
            "step": 0.1
        },
        "is_primary": True,
        "sort_order": 2
    },
    {
        "key": "blood_pressure",
        "label_ru": "Артериальное давление",
        "type": "text",
        "config": {
            "placeholder": "120/80",
            "pattern": "\\d{2,3}/\\d{2,3}"
        },
        "is_primary": True,
        "sort_order": 3
    },
    {
        "key": "pulse",
        "label_ru": "Пульс",
        "type": "number",
        "config": {
            "unit": "уд/мин",
            "min": 40,
            "max": 200
        },
        "is_primary": True,
        "sort_order": 4
    },
    {
        "key": "weakness_level",
        "label_ru": "Уровень слабости",
        "type": "scale",
        "config": {
            "options": [
                {"value": "none", "label": "Нет"},
                {"value": "mild", "label": "Легкая"},
                {"value": "moderate", "label": "Средняя"},
                {"value": "severe", "label": "Сильная"}
            ]
        },
        "is_primary": True,
        "sort_order": 5
    },
    {
        "key": "pain_intensity",
        "label_ru": "Интенсивность боли",
        "type": "scale",
        "config": {
            "min": 0,
            "max": 10,
            "labels": {
                "0": "Нет боли",
                "5": "Средняя",
                "10": "Невыносимая"
            }
        },
        "is_primary": True,
        "sort_order": 6
    },
    {
        "key": "sleep_quality",
        "label_ru": "Качество сна",
        "type": "scale",
        "config": {
            "options": [
                {"value": "excellent", "label": "Отличный"},
                {"value": "good", "label": "Хороший"},
                {"value": "poor", "label": "Плохой"},
                {"value": "insomnia", "label": "Бессонница"}
            ]
        },
        "is_primary": True,
        "sort_order": 7
    },
    
    # 13 дополнительных параметров (is_primary: False)
    {
        "key": "pain_location",
        "label_ru": "Локализация боли",
        "type": "text",
        "config": {
            "placeholder": "Где болит?"
        },
        "is_primary": False,
        "sort_order": 8
    },
    {
        "key": "appetite",
        "label_ru": "Аппетит",
        "type": "scale",
        "config": {
            "options": [
                {"value": "normal", "label": "Нормальный"},
                {"value": "increased", "label": "Повышенный"},
                {"value": "decreased", "label": "Сниженный"},
                {"value": "absent", "label": "Отсутствует"}
            ]
        },
        "is_primary": False,
        "sort_order": 9
    },
    {
        "key": "nausea",
        "label_ru": "Тошнота",
        "type": "boolean",
        "config": {},
        "is_primary": False,
        "sort_order": 10
    },
    {
        "key": "vomiting",
        "label_ru": "Рвота",
        "type": "boolean",
        "config": {},
        "is_primary": False,
        "sort_order": 11
    },
    {
        "key": "dizziness",
        "label_ru": "Головокружение",
        "type": "boolean",
        "config": {},
        "is_primary": False,
        "sort_order": 12
    },
    {
        "key": "cough",
        "label_ru": "Кашель",
        "type": "scale",
        "config": {
            "options": [
                {"value": "none", "label": "Нет"},
                {"value": "dry", "label": "Сухой"},
                {"value": "wet", "label": "Влажный"},
                {"value": "severe", "label": "Сильный"}
            ]
        },
        "is_primary": False,
        "sort_order": 13
    },
    {
        "key": "breathing_difficulty",
        "label_ru": "Затрудненное дыхание",
        "type": "boolean",
        "config": {},
        "is_primary": False,
        "sort_order": 14
    },
    {
        "key": "mood",
        "label_ru": "Настроение",
        "type": "scale",
        "config": {
            "options": [
                {"value": "excellent", "label": "Отличное"},
                {"value": "good", "label": "Хорошее"},
                {"value": "neutral", "label": "Нейтральное"},
                {"value": "bad", "label": "Плохое"},
                {"value": "depressed", "label": "Подавленное"}
            ]
        },
        "is_primary": False,
        "sort_order": 15
    },
    {
        "key": "energy_level",
        "label_ru": "Уровень энергии",
        "type": "scale",
        "config": {
            "options": [
                {"value": "high", "label": "Высокий"},
                {"value": "normal", "label": "Нормальный"},
                {"value": "low", "label": "Низкий"},
                {"value": "exhausted", "label": "Изнеможение"}
            ]
        },
        "is_primary": False,
        "sort_order": 16
    },
    {
        "key": "stool",
        "label_ru": "Стул",
        "type": "scale",
        "config": {
            "options": [
                {"value": "normal", "label": "Нормальный"},
                {"value": "diarrhea", "label": "Диарея"},
                {"value": "constipation", "label": "Запор"}
            ]
        },
        "is_primary": False,
        "sort_order": 17
    },
    {
        "key": "urination_frequency",
        "label_ru": "Частота мочеиспускания",
        "type": "scale",
        "config": {
            "options": [
                {"value": "normal", "label": "Нормальная"},
                {"value": "frequent", "label": "Частая"},
                {"value": "rare", "label": "Редкая"}
            ]
        },
        "is_primary": False,
        "sort_order": 18
    },
    {
        "key": "skin_condition",
        "label_ru": "Состояние кожи",
        "type": "text",
        "config": {
            "placeholder": "Высыпания, покраснения..."
        },
        "is_primary": False,
        "sort_order": 19
    },
    {
        "key": "swelling",
        "label_ru": "Отеки",
        "type": "text",
        "config": {
            "placeholder": "Где заметили отеки?"
        },
        "is_primary": False,
        "sort_order": 20
    }
]


def init_health_parameters():
    """Initialize health parameter definitions in MongoDB"""
    print("Connecting to MongoDB...")
    client = MongoClient(settings.MONGODB_URL)
    db = client.medhistory
    collection = db.health_parameter_definitions
    
    # Check if parameters already exist
    existing_count = collection.count_documents({})
    if existing_count > 0:
        print(f"Found {existing_count} existing parameters. Clearing...")
        collection.delete_many({})
    
    # Add created_at timestamp to each parameter
    now = datetime.utcnow()
    for param in HEALTH_PARAMETERS:
        param["created_at"] = now
    
    # Insert parameters
    print(f"Inserting {len(HEALTH_PARAMETERS)} health parameters...")
    result = collection.insert_many(HEALTH_PARAMETERS)
    
    # Create index on key for fast lookups
    collection.create_index("key", unique=True)
    collection.create_index([("is_primary", 1), ("sort_order", 1)])
    
    print(f"✓ Successfully inserted {len(result.inserted_ids)} parameters")
    print(f"✓ Created indexes on 'key' and 'is_primary, sort_order'")
    
    # Display summary
    primary_count = sum(1 for p in HEALTH_PARAMETERS if p["is_primary"])
    secondary_count = len(HEALTH_PARAMETERS) - primary_count
    print(f"\nSummary:")
    print(f"  Primary parameters: {primary_count}")
    print(f"  Secondary parameters: {secondary_count}")
    print(f"  Total: {len(HEALTH_PARAMETERS)}")
    
    client.close()


if __name__ == "__main__":
    init_health_parameters()
