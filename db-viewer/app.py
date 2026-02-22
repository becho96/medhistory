"""
DB Viewer для просмотра содержимого PostgreSQL и MongoDB
Поддержка локального и production окружения через SSH туннель
"""
import os
import json
import threading
from datetime import datetime, date
from pathlib import Path

# Загрузить .env файл если есть
from dotenv import load_dotenv
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    load_dotenv(env_path)

from flask import Flask, render_template_string, request, jsonify, session
import psycopg2
from psycopg2.extras import RealDictCursor
from pymongo import MongoClient
from bson import ObjectId, json_util

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'db-viewer-secret-key-change-in-production')

# ============== Конфигурации ==============

ENVIRONMENTS = {
    'local': {
        'name': 'Локальная разработка',
        'description': 'Подключение к локальным Docker контейнерам',
        'backend_url': os.getenv('BACKEND_URL', 'http://backend:8000'),
        'postgres': {
            'host': os.getenv('PG_HOST', 'localhost'),
            'port': int(os.getenv('PG_PORT', '5432')),
            'database': os.getenv('PG_DB', 'medhistory'),
            'user': os.getenv('PG_USER', 'medhistory_user'),
            'password': os.getenv('PG_PASSWORD', 'medhistory_local_pass'),
        },
        'mongo': {
            'host': os.getenv('MONGO_HOST', 'localhost'),
            'port': int(os.getenv('MONGO_PORT', '27017')),
            'username': os.getenv('MONGO_USER', 'admin'),
            'password': os.getenv('MONGO_PASSWORD', 'mongodb_secure_pass'),
            'database': os.getenv('MONGO_DB', 'medhistory'),
        },
        'ssh': None
    },
    'production': {
        'name': 'Production (Yandex Cloud)',
        'description': 'Подключение к серверу 93.77.182.26 через SSH туннель',
        'backend_url': os.getenv('PROD_BACKEND_URL', ''),  # например http://93.77.182.26 или https://your-domain
        'postgres': {
            'host': 'localhost',  # Через SSH туннель
            'port': 15432,  # Локальный порт туннеля
            'database': os.getenv('PROD_PG_DB', 'medhistory'),
            'user': os.getenv('PROD_PG_USER', 'medhistory_user'),
            'password': os.getenv('PROD_PG_PASSWORD', ''),
        },
        'mongo': {
            'host': 'localhost',  # Через SSH туннель
            'port': 17017,  # Локальный порт туннеля
            'username': os.getenv('PROD_MONGO_USER', 'admin'),
            'password': os.getenv('PROD_MONGO_PASSWORD', ''),
            'database': os.getenv('PROD_MONGO_DB', 'medhistory'),
        },
        'ssh': {
            'host': os.getenv('PROD_SSH_HOST', '93.77.182.26'),
            'port': int(os.getenv('PROD_SSH_PORT', '22')),
            'username': os.getenv('PROD_SSH_USER', 'yc-user'),
            'key_path': os.path.expanduser(os.getenv('PROD_SSH_KEY', '~/.ssh/id_rsa')),
        }
    }
}

# Текущее окружение и туннели
current_env = 'local'
ssh_tunnels = {}
tunnel_lock = threading.Lock()

# ============== SSH Tunnel Management ==============

def create_ssh_tunnel(env_name):
    """Создать SSH туннель для production окружения"""
    global ssh_tunnels
    
    if env_name != 'production':
        return True, "SSH туннель не требуется для локального окружения"
    
    env_config = ENVIRONMENTS[env_name]
    if not env_config.get('ssh'):
        return False, "SSH конфигурация не найдена"
    
    try:
        from sshtunnel import SSHTunnelForwarder
    except ImportError:
        return False, "Библиотека sshtunnel не установлена. Выполните: pip install sshtunnel"
    
    ssh_config = env_config['ssh']
    key_path = ssh_config['key_path']
    
    if not os.path.exists(key_path):
        return False, f"SSH ключ не найден: {key_path}"
    
    with tunnel_lock:
        # Закрыть существующие туннели
        if env_name in ssh_tunnels:
            try:
                ssh_tunnels[env_name].stop()
            except:
                pass
        
        try:
            # Создать туннель для обеих баз данных
            tunnel = SSHTunnelForwarder(
                (ssh_config['host'], ssh_config['port']),
                ssh_username=ssh_config['username'],
                ssh_pkey=key_path,
                remote_bind_addresses=[
                    ('localhost', 5432),   # PostgreSQL на сервере
                    ('localhost', 27017),  # MongoDB на сервере
                ],
                local_bind_addresses=[
                    ('localhost', env_config['postgres']['port']),  # 15432
                    ('localhost', env_config['mongo']['port']),      # 17017
                ]
            )
            tunnel.start()
            ssh_tunnels[env_name] = tunnel
            return True, f"SSH туннель установлен к {ssh_config['host']}"
        except Exception as e:
            return False, f"Ошибка создания SSH туннеля: {str(e)}"

def close_ssh_tunnel(env_name):
    """Закрыть SSH туннель"""
    global ssh_tunnels
    
    with tunnel_lock:
        if env_name in ssh_tunnels:
            try:
                ssh_tunnels[env_name].stop()
                del ssh_tunnels[env_name]
                return True, "SSH туннель закрыт"
            except Exception as e:
                return False, f"Ошибка закрытия туннеля: {str(e)}"
    return True, "Туннель не был открыт"

def get_tunnel_status():
    """Получить статус SSH туннелей"""
    status = {}
    with tunnel_lock:
        for env_name, tunnel in ssh_tunnels.items():
            status[env_name] = {
                'active': tunnel.is_active if hasattr(tunnel, 'is_active') else True,
                'local_ports': {
                    'postgres': ENVIRONMENTS[env_name]['postgres']['port'],
                    'mongo': ENVIRONMENTS[env_name]['mongo']['port']
                }
            }
    return status

# ============== PostgreSQL ==============

def get_pg_config():
    """Получить текущую конфигурацию PostgreSQL"""
    return ENVIRONMENTS[current_env]['postgres']

def get_pg_connection():
    config = get_pg_config()
    return psycopg2.connect(
        host=config['host'],
        port=config['port'],
        database=config['database'],
        user=config['user'],
        password=config['password']
    )

def get_pg_tables():
    with get_pg_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name
            """)
            return [row[0] for row in cur.fetchall()]

def get_pg_table_info(table_name):
    with get_pg_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = %s
                ORDER BY ordinal_position
            """, (table_name,))
            return cur.fetchall()

def get_pg_table_data(table_name, limit=100, offset=0):
    with get_pg_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name = %s
            """, (table_name,))
            if not cur.fetchone():
                return [], 0
            
            cur.execute(f'SELECT COUNT(*) FROM "{table_name}"')
            total = cur.fetchone()['count']
            
            cur.execute(f'SELECT * FROM "{table_name}" LIMIT %s OFFSET %s', (limit, offset))
            rows = cur.fetchall()
            return rows, total

# ============== MongoDB ==============

def get_mongo_config():
    """Получить текущую конфигурацию MongoDB"""
    return ENVIRONMENTS[current_env]['mongo']

def get_mongo_client():
    config = get_mongo_config()
    return MongoClient(
        host=config['host'],
        port=config['port'],
        username=config['username'],
        password=config['password'],
        authSource='admin'
    )

def get_mongo_collections():
    try:
        client = get_mongo_client()
        db = client[get_mongo_config()['database']]
        collections = db.list_collection_names()
        client.close()
        return sorted(collections)
    except Exception as e:
        print(f"MongoDB error: {e}")
        return []

def get_mongo_collection_data(collection_name, limit=100, offset=0):
    try:
        client = get_mongo_client()
        db = client[get_mongo_config()['database']]
        collection = db[collection_name]
        
        total = collection.count_documents({})
        docs = list(collection.find().skip(offset).limit(limit))
        
        client.close()
        return docs, total
    except Exception as e:
        print(f"MongoDB error: {e}")
        return [], 0

def mongo_to_json(obj):
    """Конвертировать MongoDB объекты в JSON-сериализуемый формат"""
    if isinstance(obj, ObjectId):
        return str(obj)
    elif isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, date):
        return obj.isoformat()
    elif isinstance(obj, bytes):
        return obj.decode('utf-8', errors='replace')
    elif isinstance(obj, dict):
        return {k: mongo_to_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [mongo_to_json(i) for i in obj]
    return obj

# ============== Analyte Mapping (Admin) ==============

def get_existing_synonym_lower_set():
    """Получить множество synonym_lower из analyte_synonyms для фильтрации"""
    with get_pg_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT synonym_lower FROM analyte_synonyms")
            return {row[0] for row in cur.fetchall()}

def get_unmapped_analytes():
    """Получить список немапленных анализов: distinct (test_name, unit) из MongoDB, не в analyte_synonyms"""
    try:
        client = get_mongo_client()
        db = client[get_mongo_config()['database']]
        coll = db['document_metadata']
        
        pipeline = [
            {"$match": {"extracted_data.lab_results": {"$exists": True, "$ne": []}}},
            {"$project": {"extracted_data.lab_results": 1}},
            {"$unwind": "$extracted_data.lab_results"},
            {
                "$group": {
                    "_id": {
                        "name_lower": {"$toLower": {"$ifNull": ["$extracted_data.lab_results.test_name", ""]}},
                        "unit": {"$ifNull": ["$extracted_data.lab_results.unit", ""]}
                    },
                    "name": {"$first": "$extracted_data.lab_results.test_name"},
                    "unit": {"$first": "$extracted_data.lab_results.unit"},
                    "count": {"$sum": 1}
                }
            },
            {"$sort": {"name": 1}},
        ]
        
        cursor = coll.aggregate(pipeline)
        rows = list(cursor)
        client.close()
        
        # Фильтруем: оставляем только те, у которых name_lower нет в analyte_synonyms
        existing = get_existing_synonym_lower_set()
        result = []
        for r in rows:
            name = (r.get("name") or "").strip()
            unit = r.get("unit") or ""
            name_lower = (name or "").lower().strip()
            if not name_lower:
                continue
            if name_lower not in existing:
                result.append({
                    "original_name": name,
                    "unit": unit,
                    "count": r.get("count", 0)
                })
        
        return result
    except Exception as e:
        print(f"get_unmapped_analytes error: {e}")
        return []

def get_analyte_standards():
    """Получить список стандартных анализов с категориями"""
    with get_pg_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT a.id, a.canonical_name, a.standard_unit, c.name as category_name
                FROM analyte_standards a
                JOIN analyte_categories c ON c.id = a.category_id
                WHERE a.is_active = TRUE AND c.is_active = TRUE
                ORDER BY c.sort_order, a.sort_order, a.canonical_name
            """)
            return [dict(row) for row in cur.fetchall()]

def create_analyte_synonym(synonym: str, analyte_id: str):
    """Добавить синоним в analyte_synonyms. Возвращает (success, error_message)"""
    import uuid
    synonym = (synonym or "").strip()
    synonym_lower = synonym.lower()
    if not synonym or not analyte_id:
        return False, "synonym и analyte_id обязательны"
    try:
        with get_pg_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO analyte_synonyms (id, analyte_id, synonym, synonym_lower)
                    VALUES (%s, %s, %s, %s)
                """, (str(uuid.uuid4()), analyte_id, synonym, synonym_lower))
            conn.commit()
        return True, None
    except psycopg2.IntegrityError as e:
        if "ix_analyte_synonyms_synonym_lower_unique" in str(e) or "duplicate key" in str(e).lower():
            return False, "Этот синоним уже существует в маппинге"
        raise
    except Exception as e:
        return False, str(e)

def call_backend_reload():
    """Вызвать backend текущего окружения для инвалидации кэша нормализации"""
    env_config = ENVIRONMENTS[current_env]
    backend_url = env_config.get('backend_url', '')
    if not backend_url and current_env == 'production':
        # Fallback: http://PROD_SSH_HOST (без порта — nginx на 80)
        host = env_config.get('ssh', {}).get('host', '')
        backend_url = f"http://{host}" if host else ''
    if not backend_url:
        backend_url = os.getenv('BACKEND_URL', 'http://backend:8000')
    url = f"{backend_url.rstrip('/')}/api/v1/internal/analytes/reload"
    try:
        import requests
        r = requests.post(url, timeout=10)
        return r.status_code == 200, r.text
    except Exception as e:
        return False, str(e)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DB Viewer - MedHistory</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        :root {
            --bg-primary: #0d1117;
            --bg-secondary: #161b22;
            --bg-tertiary: #21262d;
            --border-color: #30363d;
            --text-primary: #c9d1d9;
            --text-secondary: #8b949e;
            --accent: #58a6ff;
            --accent-hover: #79b8ff;
            --success: #3fb950;
            --warning: #d29922;
            --danger: #f85149;
            --mongo: #00ed64;
            --postgres: #336791;
            --production: #f97316;
            --local: #22c55e;
        }
        
        body {
            font-family: 'SF Mono', 'Cascadia Code', 'Fira Code', 'JetBrains Mono', monospace;
            background: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
            font-size: 13px;
        }
        
        .container {
            display: flex;
            height: 100vh;
        }
        
        /* Сайдбар */
        .sidebar {
            width: 300px;
            background: var(--bg-secondary);
            border-right: 1px solid var(--border-color);
            display: flex;
            flex-direction: column;
            flex-shrink: 0;
        }
        
        .sidebar-header {
            padding: 20px;
            border-bottom: 1px solid var(--border-color);
        }
        
        .sidebar-header h1 {
            font-size: 16px;
            font-weight: 600;
            color: var(--text-primary);
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .sidebar-header h1::before {
            content: '◉';
            color: var(--success);
        }
        
        .sidebar-header p {
            color: var(--text-secondary);
            font-size: 11px;
            margin-top: 6px;
        }
        
        /* Environment Switcher */
        .env-switcher {
            padding: 12px 16px;
            border-bottom: 1px solid var(--border-color);
            background: var(--bg-tertiary);
        }
        
        .env-switcher-label {
            font-size: 10px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: var(--text-secondary);
            margin-bottom: 8px;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        
        .env-buttons {
            display: flex;
            gap: 8px;
        }
        
        .env-btn {
            flex: 1;
            padding: 10px 12px;
            border: 1px solid var(--border-color);
            border-radius: 8px;
            background: var(--bg-secondary);
            color: var(--text-secondary);
            font-size: 11px;
            cursor: pointer;
            transition: all 0.2s ease;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 4px;
        }
        
        .env-btn:hover {
            border-color: var(--text-secondary);
            color: var(--text-primary);
        }
        
        .env-btn.active {
            border-color: var(--accent);
            background: rgba(88, 166, 255, 0.1);
            color: var(--text-primary);
        }
        
        .env-btn.active.local {
            border-color: var(--local);
            background: rgba(34, 197, 94, 0.1);
        }
        
        .env-btn.active.production {
            border-color: var(--production);
            background: rgba(249, 115, 22, 0.1);
        }
        
        .env-btn .env-icon {
            font-size: 16px;
        }
        
        .env-btn .env-name {
            font-weight: 600;
        }
        
        .env-status {
            padding: 8px 16px;
            font-size: 11px;
            background: var(--bg-secondary);
            border-bottom: 1px solid var(--border-color);
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .env-status.loading {
            color: var(--warning);
        }
        
        .env-status.connected {
            color: var(--success);
        }
        
        .env-status.error {
            color: var(--danger);
        }
        
        .env-status .spinner-small {
            width: 12px;
            height: 12px;
            border: 2px solid var(--border-color);
            border-top-color: var(--warning);
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        
        .db-section {
            border-bottom: 1px solid var(--border-color);
        }
        
        .db-section-header {
            padding: 12px 16px;
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: var(--text-secondary);
            cursor: pointer;
            transition: background 0.15s ease;
        }
        
        .db-section-header:hover {
            background: var(--bg-tertiary);
        }
        
        .db-section-header .db-icon {
            width: 18px;
            height: 18px;
            border-radius: 4px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 10px;
            font-weight: bold;
        }
        
        .db-icon.postgres {
            background: var(--postgres);
            color: white;
        }
        
        .db-icon.mongo {
            background: var(--mongo);
            color: #001e2b;
        }
        
        .db-section-header .count {
            margin-left: auto;
            background: var(--bg-tertiary);
            padding: 2px 8px;
            border-radius: 10px;
        }
        
        .tables-list {
            max-height: 300px;
            overflow-y: auto;
            padding: 8px 12px;
        }
        
        .table-item {
            padding: 8px 12px;
            margin-bottom: 2px;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.15s ease;
            display: flex;
            align-items: center;
            gap: 8px;
            color: var(--text-secondary);
            font-size: 12px;
        }
        
        .table-item:hover {
            background: var(--bg-tertiary);
            color: var(--text-primary);
        }
        
        .table-item.active {
            background: rgba(88, 166, 255, 0.15);
            color: var(--accent);
        }
        
        .table-item.active.mongo {
            background: rgba(0, 237, 100, 0.15);
            color: var(--mongo);
        }
        
        .table-item::before {
            content: '▦';
            font-size: 12px;
        }
        
        .table-item.mongo::before {
            content: '◈';
        }
        
        .table-count {
            margin-left: auto;
            background: var(--bg-tertiary);
            padding: 2px 6px;
            border-radius: 8px;
            font-size: 10px;
        }
        
        .table-item.active .table-count {
            background: rgba(88, 166, 255, 0.2);
        }
        
        .table-item.active.mongo .table-count {
            background: rgba(0, 237, 100, 0.2);
        }
        
        /* Основной контент */
        .main {
            flex: 1;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }
        
        .header {
            padding: 16px 24px;
            border-bottom: 1px solid var(--border-color);
            background: var(--bg-secondary);
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        
        .header h2 {
            font-size: 15px;
            font-weight: 500;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .header h2 .badge {
            font-size: 10px;
            padding: 3px 8px;
            border-radius: 4px;
            font-weight: 600;
        }
        
        .header h2 .badge.postgres {
            background: var(--postgres);
            color: white;
        }
        
        .header h2 .badge.mongo {
            background: var(--mongo);
            color: #001e2b;
        }
        
        .header h2 .badge.env-local {
            background: var(--local);
            color: white;
            margin-left: 8px;
        }
        
        .header h2 .badge.env-production {
            background: var(--production);
            color: white;
            margin-left: 8px;
        }
        
        .header-info {
            color: var(--text-secondary);
            font-size: 12px;
        }
        
        /* Панель информации о таблице */
        .table-info {
            padding: 16px 24px;
            background: var(--bg-secondary);
            border-bottom: 1px solid var(--border-color);
        }
        
        .columns-grid {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }
        
        .column-badge {
            background: var(--bg-tertiary);
            border: 1px solid var(--border-color);
            padding: 6px 12px;
            border-radius: 4px;
            font-size: 11px;
        }
        
        .column-badge .name {
            color: var(--accent);
        }
        
        .column-badge.mongo .name {
            color: var(--mongo);
        }
        
        .column-badge .type {
            color: var(--text-secondary);
            margin-left: 6px;
        }
        
        /* Таблица данных */
        .data-container {
            flex: 1;
            overflow: auto;
            padding: 20px 24px;
        }
        
        .data-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 12px;
        }
        
        .data-table th {
            background: var(--bg-tertiary);
            padding: 10px 12px;
            text-align: left;
            font-weight: 500;
            color: var(--text-secondary);
            border-bottom: 2px solid var(--border-color);
            position: sticky;
            top: 0;
            white-space: nowrap;
        }
        
        .data-table td {
            padding: 10px 12px;
            border-bottom: 1px solid var(--border-color);
            max-width: 400px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        
        .data-table tr:hover td {
            background: var(--bg-secondary);
        }
        
        .cell-null {
            color: var(--text-secondary);
            font-style: italic;
        }
        
        .cell-uuid, .cell-objectid {
            color: var(--warning);
            font-size: 11px;
        }
        
        .cell-date {
            color: var(--success);
        }
        
        .cell-bool-true {
            color: var(--success);
        }
        
        .cell-bool-false {
            color: var(--danger);
        }
        
        .cell-object {
            color: var(--accent);
            cursor: pointer;
        }
        
        .cell-object:hover {
            text-decoration: underline;
        }
        
        /* Пагинация */
        .pagination {
            padding: 16px 24px;
            border-top: 1px solid var(--border-color);
            background: var(--bg-secondary);
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        
        .pagination-info {
            color: var(--text-secondary);
            font-size: 12px;
        }
        
        .pagination-buttons {
            display: flex;
            gap: 8px;
        }
        
        .btn {
            background: var(--bg-tertiary);
            border: 1px solid var(--border-color);
            color: var(--text-primary);
            padding: 8px 16px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 12px;
            transition: all 0.15s ease;
        }
        
        .btn:hover:not(:disabled) {
            background: var(--bg-primary);
            border-color: var(--accent);
        }
        
        .btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        
        /* Пустое состояние */
        .empty-state {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            height: 100%;
            color: var(--text-secondary);
        }
        
        .empty-state-icon {
            font-size: 48px;
            margin-bottom: 16px;
            opacity: 0.5;
        }
        
        .empty-state p {
            font-size: 14px;
        }
        
        /* Загрузка */
        .loading {
            display: flex;
            align-items: center;
            justify-content: center;
            height: 100%;
        }
        
        .spinner {
            width: 32px;
            height: 32px;
            border: 3px solid var(--border-color);
            border-top-color: var(--accent);
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        
        /* Модальное окно для JSON */
        .modal-overlay {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.7);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 1000;
        }
        
        .modal {
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            width: 90%;
            max-width: 800px;
            max-height: 80vh;
            display: flex;
            flex-direction: column;
        }
        
        .modal-header {
            padding: 16px 20px;
            border-bottom: 1px solid var(--border-color);
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        
        .modal-header h3 {
            font-size: 14px;
            font-weight: 500;
        }
        
        .modal-close {
            background: none;
            border: none;
            color: var(--text-secondary);
            cursor: pointer;
            font-size: 20px;
            padding: 4px 8px;
        }
        
        .modal-close:hover {
            color: var(--text-primary);
        }
        
        .modal-body {
            flex: 1;
            overflow: auto;
            padding: 20px;
        }
        
        .json-viewer {
            font-size: 12px;
            line-height: 1.6;
            white-space: pre-wrap;
            word-break: break-all;
        }
        
        .json-key {
            color: var(--accent);
        }
        
        .json-string {
            color: var(--success);
        }
        
        .json-number {
            color: var(--warning);
        }
        
        .json-bool {
            color: var(--danger);
        }
        
        .json-null {
            color: var(--text-secondary);
        }
        
        /* Скроллбар */
        ::-webkit-scrollbar {
            width: 8px;
            height: 8px;
        }
        
        ::-webkit-scrollbar-track {
            background: var(--bg-primary);
        }
        
        ::-webkit-scrollbar-thumb {
            background: var(--border-color);
            border-radius: 4px;
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: var(--text-secondary);
        }
        
        /* Connection status */
        .connection-status {
            padding: 8px 16px;
            font-size: 11px;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        
        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
        }
        
        .status-dot.connected {
            background: var(--success);
        }
        
        .status-dot.disconnected {
            background: var(--danger);
        }
        
        /* SSH Info Panel */
        .ssh-info {
            padding: 12px 16px;
            background: rgba(249, 115, 22, 0.1);
            border-bottom: 1px solid var(--border-color);
            font-size: 11px;
            color: var(--text-secondary);
        }
        
        .ssh-info.hidden {
            display: none;
        }
        
        .ssh-info-title {
            color: var(--production);
            font-weight: 600;
            margin-bottom: 4px;
        }
        
        .ssh-info code {
            background: var(--bg-tertiary);
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 10px;
        }
        
        /* Маппинг анализов */
        .mapping-header {
            cursor: pointer;
        }
        .mapping-header:hover {
            background: var(--bg-tertiary);
        }
        .mapping-header.active {
            background: rgba(88, 166, 255, 0.15);
        }
        .mapping-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 10px 12px;
            border-bottom: 1px solid var(--border-color);
        }
        .mapping-row:hover {
            background: var(--bg-secondary);
        }
        .mapping-form select {
            background: var(--bg-tertiary);
            border: 1px solid var(--border-color);
            color: var(--text-primary);
            padding: 8px 12px;
            border-radius: 6px;
            width: 100%;
            font-size: 13px;
        }
        .mapping-form .form-row {
            margin-bottom: 12px;
        }
        .mapping-form label {
            display: block;
            margin-bottom: 4px;
            font-size: 11px;
            color: var(--text-secondary);
        }
    </style>
</head>
<body>
    <div class="container">
        <aside class="sidebar">
            <div class="sidebar-header">
                <h1>DB Viewer</h1>
                <p>MedHistory Databases</p>
            </div>
            
            <!-- Environment Switcher -->
            <div class="env-switcher">
                <div class="env-switcher-label">
                    <span>🌍</span> Окружение
                </div>
                <div class="env-buttons">
                    <button class="env-btn local active" onclick="switchEnvironment('local')">
                        <span class="env-icon">🏠</span>
                        <span class="env-name">Local</span>
                    </button>
                    <button class="env-btn production" onclick="switchEnvironment('production')">
                        <span class="env-icon">☁️</span>
                        <span class="env-name">Production</span>
                    </button>
                </div>
            </div>
            
            <div class="env-status connected" id="envStatus">
                <span>✓</span> Локальное окружение
            </div>
            
            <!-- SSH Info (показывается только для production) -->
            <div class="ssh-info hidden" id="sshInfo">
                <div class="ssh-info-title">SSH Туннель</div>
                <div>Сервер: <code id="sshHost">93.77.182.26</code></div>
                <div>PG порт: <code id="sshPgPort">15432</code> → <code>5432</code></div>
                <div>Mongo порт: <code id="sshMongoPort">17017</code> → <code>27017</code></div>
            </div>
            
            <!-- Маппинг анализов -->
            <div class="db-section">
                <div class="db-section-header mapping-header" onclick="selectMapping()">
                    <span class="db-icon" style="background: var(--accent); color: white;">A</span>
                    Маппинг анализов
                </div>
                <div class="connection-status" id="mappingStatus" style="display: none;">
                    <span class="status-dot connected"></span>
                    <span>Сопоставление синонимов с эталонными анализами</span>
                </div>
            </div>
            
            <!-- PostgreSQL -->
            <div class="db-section">
                <div class="db-section-header">
                    <span class="db-icon postgres">P</span>
                    PostgreSQL
                    <span class="count" id="pgCount">0</span>
                </div>
                <div class="connection-status" id="pgStatus">
                    <span class="status-dot"></span>
                    <span>Проверка...</span>
                </div>
                <div class="tables-list" id="pgTablesList"></div>
            </div>
            
            <!-- MongoDB -->
            <div class="db-section">
                <div class="db-section-header">
                    <span class="db-icon mongo">M</span>
                    MongoDB
                    <span class="count" id="mongoCount">0</span>
                </div>
                <div class="connection-status" id="mongoStatus">
                    <span class="status-dot"></span>
                    <span>Проверка...</span>
                </div>
                <div class="tables-list" id="mongoCollectionsList"></div>
            </div>
        </aside>
        
        <main class="main">
            <div class="header" id="header">
                <h2>Выберите таблицу или коллекцию</h2>
                <span class="header-info" id="headerInfo"></span>
                <div id="headerActions"></div>
            </div>
            
            <div class="table-info" id="tableInfo" style="display: none;">
                <div class="columns-grid" id="columnsGrid"></div>
            </div>
            
            <div class="data-container" id="dataContainer">
                <div class="empty-state">
                    <div class="empty-state-icon">◫</div>
                    <p>Выберите таблицу PostgreSQL или коллекцию MongoDB</p>
                </div>
            </div>
            
            <div class="pagination" id="pagination" style="display: none;">
                <span class="pagination-info" id="paginationInfo"></span>
                <div class="pagination-buttons">
                    <button class="btn" id="prevBtn" onclick="prevPage()">← Назад</button>
                    <button class="btn" id="nextBtn" onclick="nextPage()">Вперёд →</button>
                </div>
            </div>
        </main>
    </div>
    
    <!-- Модальное окно для JSON -->
    <div class="modal-overlay" id="modalOverlay" style="display: none;" onclick="closeModal(event)">
        <div class="modal" onclick="event.stopPropagation()">
            <div class="modal-header">
                <h3 id="modalTitle">JSON Data</h3>
                <button class="modal-close" onclick="closeModal()">&times;</button>
            </div>
            <div class="modal-body">
                <div class="json-viewer" id="jsonViewer"></div>
            </div>
        </div>
    </div>
    
    <!-- Модальное окно для добавления маппинга -->
    <div class="modal-overlay" id="mappingModalOverlay" style="display: none;" onclick="closeMappingModal(event)">
        <div class="modal" onclick="event.stopPropagation()">
            <div class="modal-header">
                <h3>Добавить маппинг</h3>
                <button class="modal-close" onclick="closeMappingModal()">&times;</button>
            </div>
            <div class="modal-body">
                <div class="mapping-form">
                    <div class="form-row">
                        <label>Синоним (название из документа)</label>
                        <input type="text" id="mappingSynonymInput" readonly style="background: var(--bg-tertiary); border: 1px solid var(--border-color); color: var(--text-primary); padding: 8px 12px; border-radius: 6px; width: 100%; font-size: 13px;">
                    </div>
                    <div class="form-row">
                        <label>Сопоставить с эталонным анализом</label>
                        <select id="mappingStandardSelect"></select>
                    </div>
                    <div id="mappingError" style="color: var(--danger); font-size: 12px; margin-bottom: 8px; display: none;"></div>
                    <button class="btn" onclick="saveMapping()">Сохранить</button>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        let currentTable = null;
        let currentDbType = null; // 'postgres', 'mongo', or 'mapping'
        let currentOffset = 0;
        let totalRows = 0;
        let currentEnv = 'local';
        const limit = 100;
        let mappingStandards = [];
        let mappingCurrentUnmapped = null;
        
        // Переключить окружение
        async function switchEnvironment(env) {
            if (env === currentEnv) return;
            
            // Обновить UI кнопок
            document.querySelectorAll('.env-btn').forEach(btn => {
                btn.classList.remove('active');
            });
            document.querySelector(`.env-btn.${env}`).classList.add('active');
            
            // Показать статус загрузки
            const envStatus = document.getElementById('envStatus');
            envStatus.className = 'env-status loading';
            envStatus.innerHTML = '<div class="spinner-small"></div> Переключение...';
            
            // Показать/скрыть SSH info
            const sshInfo = document.getElementById('sshInfo');
            if (env === 'production') {
                sshInfo.classList.remove('hidden');
            } else {
                sshInfo.classList.add('hidden');
            }
            
            try {
                const response = await fetch('/api/environment/switch', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ environment: env })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    currentEnv = env;
                    envStatus.className = 'env-status connected';
                    envStatus.innerHTML = `<span>✓</span> ${data.message}`;
                    
                    // Сбросить текущую выборку
                    currentTable = null;
                    currentDbType = null;
                    document.querySelector('.mapping-header')?.classList.remove('active');
                    document.getElementById('tableInfo').style.display = 'none';
                    document.getElementById('pagination').style.display = 'none';
                    document.getElementById('dataContainer').innerHTML = `
                        <div class="empty-state">
                            <div class="empty-state-icon">◫</div>
                            <p>Выберите таблицу PostgreSQL или коллекцию MongoDB</p>
                        </div>
                    `;
                    document.getElementById('header').querySelector('h2').innerHTML = 'Выберите таблицу или коллекцию';
                    document.getElementById('headerInfo').textContent = '';
                    document.getElementById('headerActions').innerHTML = '';
                    
                    // Обновить списки таблиц
                    await Promise.all([loadPostgres(), loadMongo()]);
                } else {
                    envStatus.className = 'env-status error';
                    envStatus.innerHTML = `<span>✗</span> ${data.error}`;
                    
                    // Вернуть кнопку в предыдущее состояние
                    document.querySelectorAll('.env-btn').forEach(btn => {
                        btn.classList.remove('active');
                    });
                    document.querySelector(`.env-btn.${currentEnv}`).classList.add('active');
                    
                    if (currentEnv !== 'production') {
                        sshInfo.classList.add('hidden');
                    }
                }
            } catch (e) {
                envStatus.className = 'env-status error';
                envStatus.innerHTML = `<span>✗</span> Ошибка подключения`;
                
                // Вернуть кнопку в предыдущее состояние
                document.querySelectorAll('.env-btn').forEach(btn => {
                    btn.classList.remove('active');
                });
                document.querySelector(`.env-btn.${currentEnv}`).classList.add('active');
            }
        }
        
        // Загрузить данные PostgreSQL
        async function loadPostgres() {
            try {
                const res = await fetch('/api/postgres/tables');
                const data = await res.json();
                
                document.getElementById('pgCount').textContent = data.tables.length;
                document.getElementById('pgStatus').innerHTML = `
                    <span class="status-dot connected"></span>
                    <span>Подключено</span>
                `;
                
                const list = document.getElementById('pgTablesList');
                list.innerHTML = data.tables.map(t => `
                    <div class="table-item" onclick="selectTable('${t.name}', 'postgres')">
                        ${t.name}
                        <span class="table-count">${t.count}</span>
                    </div>
                `).join('');
            } catch (e) {
                document.getElementById('pgStatus').innerHTML = `
                    <span class="status-dot disconnected"></span>
                    <span>Ошибка подключения</span>
                `;
                document.getElementById('pgTablesList').innerHTML = '';
                document.getElementById('pgCount').textContent = '0';
            }
        }
        
        // Загрузить данные MongoDB
        async function loadMongo() {
            try {
                const res = await fetch('/api/mongo/collections');
                const data = await res.json();
                
                document.getElementById('mongoCount').textContent = data.collections.length;
                document.getElementById('mongoStatus').innerHTML = `
                    <span class="status-dot connected"></span>
                    <span>Подключено</span>
                `;
                
                const list = document.getElementById('mongoCollectionsList');
                list.innerHTML = data.collections.map(c => `
                    <div class="table-item mongo" onclick="selectTable('${c.name}', 'mongo')">
                        ${c.name}
                        <span class="table-count">${c.count}</span>
                    </div>
                `).join('');
            } catch (e) {
                document.getElementById('mongoStatus').innerHTML = `
                    <span class="status-dot disconnected"></span>
                    <span>Ошибка подключения</span>
                `;
                document.getElementById('mongoCollectionsList').innerHTML = '';
                document.getElementById('mongoCount').textContent = '0';
            }
        }
        
        // Маппинг анализов
        async function selectMapping() {
            document.querySelectorAll('.table-item').forEach(el => el.classList.remove('active'));
            document.querySelector('.mapping-header')?.classList.add('active');
            document.getElementById('mappingStatus').style.display = 'flex';
            currentTable = '__mapping__';
            currentDbType = 'mapping';
            currentOffset = 0;
            document.getElementById('tableInfo').style.display = 'none';
            document.getElementById('pagination').style.display = 'none';
            document.getElementById('dataContainer').innerHTML = '<div class="loading"><div class="spinner"></div></div>';
            document.getElementById('header').querySelector('h2').innerHTML = '<span class="badge" style="background: var(--accent); color: white;">Маппинг</span> Анализы без сопоставления';
            document.getElementById('headerInfo').textContent = '';
            document.getElementById('headerActions').innerHTML = '<button class="btn" id="reloadCacheBtn" onclick="reloadBackendCache()">Обновить кэш backend</button>';
            await loadMappingView();
        }
        
        async function loadMappingView() {
            try {
                const [unmappedRes, standardsRes] = await Promise.all([
                    fetch('/api/analytes/unmapped'),
                    fetch('/api/analytes/standards')
                ]);
                const unmappedData = await unmappedRes.json();
                const standardsData = await standardsRes.json();
                const unmapped = unmappedData.unmapped || [];
                mappingStandards = standardsData.standards || [];
                
                document.getElementById('headerInfo').textContent = unmapped.length + ' немапленных';
                
                if (unmapped.length === 0) {
                    document.getElementById('dataContainer').innerHTML = `
                        <div class="empty-state">
                            <div class="empty-state-icon">✓</div>
                            <p>Все анализы из документов имеют маппинг</p>
                        </div>
                    `;
                    return;
                }
                
                document.getElementById('dataContainer').innerHTML = `
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>Название (из документа)</th>
                                <th>Единица</th>
                                <th>Кол-во</th>
                                <th></th>
                            </tr>
                        </thead>
                        <tbody>
                            ${unmapped.map((u, i) => `
                                <tr class="mapping-row">
                                    <td>${escapeHtml(u.original_name)}</td>
                                    <td>${escapeHtml(u.unit || '—')}</td>
                                    <td>${u.count}</td>
                                    <td><button class="btn" data-name="${escapeHtml(u.original_name)}" data-unit="${escapeHtml(u.unit || '')}" onclick="openMappingModalFromBtn(this)">Добавить маппинг</button></td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                `;
            } catch (e) {
                document.getElementById('dataContainer').innerHTML = `
                    <div class="empty-state">
                        <div class="empty-state-icon">✗</div>
                        <p>Ошибка загрузки: ${escapeHtml(String(e))}</p>
                    </div>
                `;
            }
        }
        
        function escapeHtml(s) {
            if (!s) return '';
            const d = document.createElement('div');
            d.textContent = s;
            return d.innerHTML;
        }
        
        function openMappingModalFromBtn(btn) {
            openMappingModal(btn.dataset.name || '', btn.dataset.unit || '');
        }
        
        function openMappingModal(originalName, unit) {
            mappingCurrentUnmapped = { original_name: originalName, unit: unit };
            document.getElementById('mappingSynonymInput').value = originalName + (unit ? ' (' + unit + ')' : '');
            const select = document.getElementById('mappingStandardSelect');
            select.innerHTML = '<option value="">— Выберите эталонный анализ —</option>' +
                mappingStandards.map(s => `<option value="${s.id}">${escapeHtml(s.canonical_name)} (${escapeHtml(s.standard_unit)}) — ${escapeHtml(s.category_name)}</option>`).join('');
            document.getElementById('mappingError').style.display = 'none';
            document.getElementById('mappingModalOverlay').style.display = 'flex';
        }
        
        function closeMappingModal(event) {
            if (!event || event.target === document.getElementById('mappingModalOverlay')) {
                document.getElementById('mappingModalOverlay').style.display = 'none';
                mappingCurrentUnmapped = null;
            }
        }
        
        async function saveMapping() {
            const analyteId = document.getElementById('mappingStandardSelect').value;
            const synonym = mappingCurrentUnmapped?.original_name || '';
            const errEl = document.getElementById('mappingError');
            if (!analyteId || !synonym) {
                errEl.textContent = 'Выберите эталонный анализ';
                errEl.style.display = 'block';
                return;
            }
            errEl.style.display = 'none';
            try {
                const res = await fetch('/api/analytes/mappings', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ synonym, analyte_id: analyteId })
                });
                const data = await res.json();
                if (data.success) {
                    closeMappingModal();
                    await loadMappingView();
                    if (data.warning) alert(data.warning);
                } else {
                    errEl.textContent = data.error || 'Ошибка';
                    errEl.style.display = 'block';
                }
            } catch (e) {
                errEl.textContent = 'Ошибка: ' + e.message;
                errEl.style.display = 'block';
            }
        }
        
        async function reloadBackendCache() {
            const btn = document.getElementById('reloadCacheBtn');
            if (btn) btn.disabled = true;
            try {
                const res = await fetch('/api/analytes/reload-cache', { method: 'POST' });
                const data = await res.json();
                if (data.success) {
                    alert('Кэш обновлён. Обновите страницу Анализов (F5) в основном приложении.');
                } else {
                    alert('Ошибка: ' + (data.error || res.statusText) + '\\n\\nПроверьте, что backend запущен и BACKEND_URL в db-viewer указывает на него (http://backend:8000 в Docker).');
                }
            } catch (e) {
                alert('Ошибка: ' + e.message);
            }
            if (btn) btn.disabled = false;
        }
        
        // Выбрать таблицу/коллекцию
        async function selectTable(name, dbType) {
            document.querySelector('.mapping-header')?.classList.remove('active');
            document.getElementById('mappingStatus').style.display = 'none';
            document.getElementById('headerActions').innerHTML = '';
            currentTable = name;
            currentDbType = dbType;
            currentOffset = 0;
            
            // Обновить активный элемент
            document.querySelectorAll('.table-item').forEach(el => {
                const isActive = el.textContent.includes(name) && 
                    ((dbType === 'mongo' && el.classList.contains('mongo')) ||
                     (dbType === 'postgres' && !el.classList.contains('mongo')));
                el.classList.toggle('active', isActive);
            });
            
            // Показать загрузку
            document.getElementById('dataContainer').innerHTML = '<div class="loading"><div class="spinner"></div></div>';
            
            if (dbType === 'postgres') {
                // Загрузить информацию о колонках PostgreSQL
                const infoRes = await fetch(`/api/postgres/table/${name}/info`);
                const info = await infoRes.json();
                
                const columnsGrid = document.getElementById('columnsGrid');
                columnsGrid.innerHTML = info.columns.map(c => `
                    <div class="column-badge">
                        <span class="name">${c[0]}</span>
                        <span class="type">${c[1]}</span>
                    </div>
                `).join('');
                document.getElementById('tableInfo').style.display = 'block';
            } else {
                // Для MongoDB показываем поля из первого документа
                document.getElementById('tableInfo').style.display = 'none';
            }
            
            await loadData();
        }
        
        // Сохраняем данные для модального окна
        let currentData = [];
        
        // Загрузить данные
        async function loadData() {
            const endpoint = currentDbType === 'postgres' 
                ? `/api/postgres/table/${currentTable}/data?limit=${limit}&offset=${currentOffset}`
                : `/api/mongo/collection/${currentTable}/data?limit=${limit}&offset=${currentOffset}`;
            
            const res = await fetch(endpoint);
            const data = await res.json();
            currentData = data.rows;
            totalRows = data.total;
            
            // Обновить заголовок с бейджем окружения
            const dbBadge = currentDbType === 'postgres' 
                ? '<span class="badge postgres">PostgreSQL</span>'
                : '<span class="badge mongo">MongoDB</span>';
            const envBadge = currentEnv === 'local'
                ? '<span class="badge env-local">Local</span>'
                : '<span class="badge env-production">Production</span>';
            document.getElementById('header').querySelector('h2').innerHTML = `${dbBadge} ${currentTable} ${envBadge}`;
            document.getElementById('headerInfo').textContent = `${totalRows} записей`;
            
            // Для MongoDB показываем поля из данных
            if (currentDbType === 'mongo' && data.rows.length > 0) {
                const allKeys = new Set();
                data.rows.forEach(row => Object.keys(row).forEach(k => allKeys.add(k)));
                
                const columnsGrid = document.getElementById('columnsGrid');
                columnsGrid.innerHTML = Array.from(allKeys).map(k => `
                    <div class="column-badge mongo">
                        <span class="name">${k}</span>
                    </div>
                `).join('');
                document.getElementById('tableInfo').style.display = 'block';
            }
            
            const container = document.getElementById('dataContainer');
            
            if (data.rows.length === 0) {
                container.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-state-icon">∅</div>
                        <p>Нет данных</p>
                    </div>
                `;
                document.getElementById('pagination').style.display = 'none';
                return;
            }
            
            const columns = currentDbType === 'mongo'
                ? Array.from(new Set(data.rows.flatMap(r => Object.keys(r))))
                : Object.keys(data.rows[0]);
            
            container.innerHTML = `
                <table class="data-table">
                    <thead>
                        <tr>${columns.map(c => `<th>${c}</th>`).join('')}</tr>
                    </thead>
                    <tbody>
                        ${data.rows.map((row, idx) => `
                            <tr>${columns.map(c => `<td>${formatCell(row[c], c, idx)}</td>`).join('')}</tr>
                        `).join('')}
                    </tbody>
                </table>
            `;
            
            const pagination = document.getElementById('pagination');
            pagination.style.display = 'flex';
            document.getElementById('paginationInfo').textContent = 
                `Показано ${currentOffset + 1}-${Math.min(currentOffset + limit, totalRows)} из ${totalRows}`;
            document.getElementById('prevBtn').disabled = currentOffset === 0;
            document.getElementById('nextBtn').disabled = currentOffset + limit >= totalRows;
        }
        
        // Форматирование ячейки
        function formatCell(value, column, rowIdx) {
            if (value === null || value === undefined) {
                return '<span class="cell-null">NULL</span>';
            }
            if (value === true) return '<span class="cell-bool-true">true</span>';
            if (value === false) return '<span class="cell-bool-false">false</span>';
            
            // Объекты и массивы
            if (typeof value === 'object') {
                const json = JSON.stringify(value);
                const preview = json.length > 30 ? json.substring(0, 30) + '...' : json;
                return `<span class="cell-object" onclick="showJson('${column}', ${rowIdx})" title="Нажмите для просмотра">${preview}</span>`;
            }
            
            const strValue = String(value);
            
            // ObjectId
            if (/^[0-9a-f]{24}$/i.test(strValue)) {
                return `<span class="cell-objectid" title="${strValue}">${strValue.substring(0, 8)}...</span>`;
            }
            
            // UUID
            if (/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(strValue)) {
                return `<span class="cell-uuid" title="${strValue}">${strValue.substring(0, 8)}...</span>`;
            }
            
            // Даты
            if (column.includes('_at') || column.includes('date') || column === 'created' || column === 'updated') {
                const date = new Date(strValue);
                if (!isNaN(date.getTime()) && strValue.includes('T')) {
                    return `<span class="cell-date">${date.toLocaleString('ru-RU')}</span>`;
                }
            }
            
            // Обрезать длинные строки
            if (strValue.length > 60) {
                return `<span title="${strValue.replace(/"/g, '&quot;')}">${strValue.substring(0, 60)}...</span>`;
            }
            
            return strValue;
        }
        
        // Показать JSON в модальном окне
        function showJson(column, rowIdx) {
            const value = currentData[rowIdx][column];
            document.getElementById('modalTitle').textContent = `${column} (строка ${rowIdx + 1})`;
            document.getElementById('jsonViewer').innerHTML = syntaxHighlight(JSON.stringify(value, null, 2));
            document.getElementById('modalOverlay').style.display = 'flex';
        }
        
        // Подсветка JSON
        function syntaxHighlight(json) {
            return json.replace(/("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g, function (match) {
                let cls = 'json-number';
                if (/^"/.test(match)) {
                    if (/:$/.test(match)) {
                        cls = 'json-key';
                    } else {
                        cls = 'json-string';
                    }
                } else if (/true|false/.test(match)) {
                    cls = 'json-bool';
                } else if (/null/.test(match)) {
                    cls = 'json-null';
                }
                return '<span class="' + cls + '">' + match + '</span>';
            });
        }
        
        // Закрыть модальное окно
        function closeModal(event) {
            if (!event || event.target === document.getElementById('modalOverlay')) {
                document.getElementById('modalOverlay').style.display = 'none';
            }
        }
        
        function prevPage() {
            currentOffset = Math.max(0, currentOffset - limit);
            loadData();
        }
        
        function nextPage() {
            currentOffset += limit;
            loadData();
        }
        
        // Клавиша Escape для закрытия модального окна
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                if (document.getElementById('mappingModalOverlay').style.display === 'flex') {
                    closeMappingModal();
                } else {
                    closeModal();
                }
            }
        });
        
        // Инициализация
        loadPostgres();
        loadMongo();
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

# ============== Environment API ==============

@app.route('/api/environment/current')
def api_get_environment():
    """Получить текущее окружение"""
    env_config = ENVIRONMENTS[current_env]
    return jsonify({
        'environment': current_env,
        'name': env_config['name'],
        'description': env_config['description'],
        'ssh_required': env_config.get('ssh') is not None,
        'tunnel_status': get_tunnel_status()
    })

@app.route('/api/environment/list')
def api_list_environments():
    """Список доступных окружений"""
    result = []
    for env_name, config in ENVIRONMENTS.items():
        result.append({
            'id': env_name,
            'name': config['name'],
            'description': config['description'],
            'ssh_required': config.get('ssh') is not None
        })
    return jsonify({'environments': result})

@app.route('/api/environment/switch', methods=['POST'])
def api_switch_environment():
    """Переключить окружение"""
    global current_env
    
    data = request.get_json()
    new_env = data.get('environment')
    
    if new_env not in ENVIRONMENTS:
        return jsonify({
            'success': False,
            'error': f'Неизвестное окружение: {new_env}'
        }), 400
    
    if new_env == current_env:
        return jsonify({
            'success': True,
            'message': f'Уже подключено к {ENVIRONMENTS[current_env]["name"]}'
        })
    
    # Если переключаемся на production - создать SSH туннель
    if new_env == 'production':
        success, message = create_ssh_tunnel('production')
        if not success:
            return jsonify({
                'success': False,
                'error': message
            }), 500
    
    # Если переключаемся с production - закрыть туннель
    if current_env == 'production':
        close_ssh_tunnel('production')
    
    # Проверить подключение к новому окружению
    old_env = current_env
    current_env = new_env
    
    # Тест подключения к PostgreSQL
    try:
        conn = get_pg_connection()
        conn.close()
    except Exception as e:
        current_env = old_env
        if new_env == 'production':
            close_ssh_tunnel('production')
        return jsonify({
            'success': False,
            'error': f'Ошибка подключения к PostgreSQL: {str(e)}'
        }), 500
    
    # Тест подключения к MongoDB
    try:
        client = get_mongo_client()
        client.admin.command('ping')
        client.close()
    except Exception as e:
        current_env = old_env
        if new_env == 'production':
            close_ssh_tunnel('production')
        return jsonify({
            'success': False,
            'error': f'Ошибка подключения к MongoDB: {str(e)}'
        }), 500
    
    return jsonify({
        'success': True,
        'message': f'Подключено к {ENVIRONMENTS[current_env]["name"]}',
        'environment': current_env
    })

# ============== PostgreSQL API ==============

@app.route('/api/postgres/tables')
def api_pg_tables():
    try:
        tables = get_pg_tables()
        result = []
        for table in tables:
            try:
                _, total = get_pg_table_data(table, limit=1, offset=0)
                result.append({'name': table, 'count': total})
            except:
                result.append({'name': table, 'count': 0})
        return jsonify({'tables': result})
    except Exception as e:
        return jsonify({'error': str(e), 'tables': []}), 500

@app.route('/api/postgres/table/<table_name>/info')
def api_pg_table_info(table_name):
    info = get_pg_table_info(table_name)
    return jsonify({'columns': info})

@app.route('/api/postgres/table/<table_name>/data')
def api_pg_table_data(table_name):
    limit = request.args.get('limit', 100, type=int)
    offset = request.args.get('offset', 0, type=int)
    rows, total = get_pg_table_data(table_name, limit, offset)
    
    serializable_rows = []
    for row in rows:
        sr = {}
        for k, v in row.items():
            if hasattr(v, 'isoformat'):
                sr[k] = v.isoformat()
            elif hasattr(v, 'hex'):
                sr[k] = str(v)
            else:
                sr[k] = v
        serializable_rows.append(sr)
    return jsonify({'rows': serializable_rows, 'total': total})

# ============== MongoDB API ==============

@app.route('/api/mongo/collections')
def api_mongo_collections():
    try:
        collections = get_mongo_collections()
        result = []
        for coll in collections:
            try:
                _, total = get_mongo_collection_data(coll, limit=1, offset=0)
                result.append({'name': coll, 'count': total})
            except:
                result.append({'name': coll, 'count': 0})
        return jsonify({'collections': result})
    except Exception as e:
        return jsonify({'error': str(e), 'collections': []}), 500

@app.route('/api/mongo/collection/<collection_name>/data')
def api_mongo_collection_data(collection_name):
    limit = request.args.get('limit', 100, type=int)
    offset = request.args.get('offset', 0, type=int)
    docs, total = get_mongo_collection_data(collection_name, limit, offset)
    
    serializable_docs = [mongo_to_json(doc) for doc in docs]
    return jsonify({'rows': serializable_docs, 'total': total})

# ============== Analyte Mapping API ==============

@app.route('/api/analytes/unmapped')
def api_analytes_unmapped():
    try:
        unmapped = get_unmapped_analytes()
        return jsonify({'unmapped': unmapped})
    except Exception as e:
        return jsonify({'error': str(e), 'unmapped': []}), 500

@app.route('/api/analytes/standards')
def api_analytes_standards():
    try:
        standards = get_analyte_standards()
        return jsonify({'standards': standards})
    except Exception as e:
        return jsonify({'error': str(e), 'standards': []}), 500

@app.route('/api/analytes/mappings', methods=['POST'])
def api_analytes_create_mapping():
    data = request.get_json() or {}
    synonym = data.get('synonym', '').strip()
    analyte_id = data.get('analyte_id', '').strip()
    if not synonym or not analyte_id:
        return jsonify({'success': False, 'error': 'synonym и analyte_id обязательны'}), 400
    success, err = create_analyte_synonym(synonym, analyte_id)
    if not success:
        return jsonify({'success': False, 'error': err or 'Ошибка создания маппинга'}), 400
    # Инвалидировать кэш в backend
    ok, msg = call_backend_reload()
    if not ok:
        return jsonify({'success': True, 'warning': f'Маппинг добавлен, но кэш backend не обновлён. Нажмите «Обновить кэш»: {msg}'})
    return jsonify({'success': True})


@app.route('/api/analytes/reload-cache', methods=['POST'])
def api_analytes_reload_cache():
    """Ручная инвалидация кэша backend — после добавления маппингов обновите страницу Labs."""
    ok, msg = call_backend_reload()
    if ok:
        return jsonify({'success': True, 'message': 'Кэш backend обновлён. Обновите страницу Анализов.'})
    return jsonify({'success': False, 'error': msg}), 502

if __name__ == '__main__':
    print("=" * 60)
    print("DB Viewer для MedHistory")
    print("=" * 60)
    print()
    print("Доступные окружения:")
    for env_name, config in ENVIRONMENTS.items():
        print(f"  • {env_name}: {config['name']}")
        if config.get('ssh'):
            print(f"    SSH: {config['ssh']['username']}@{config['ssh']['host']}")
    print()
    print("Откройте в браузере: http://localhost:5050")
    print("=" * 60)
    app.run(host='0.0.0.0', port=5050, debug=True, use_reloader=False)
