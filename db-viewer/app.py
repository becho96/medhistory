"""
DB Viewer для просмотра содержимого PostgreSQL и MongoDB
"""
import os
import json
from datetime import datetime, date
from flask import Flask, render_template_string, request, jsonify
import psycopg2
from psycopg2.extras import RealDictCursor
from pymongo import MongoClient
from bson import ObjectId, json_util

app = Flask(__name__)

# Конфигурация PostgreSQL
PG_CONFIG = {
    'host': os.getenv('PG_HOST', 'localhost'),
    'port': os.getenv('PG_PORT', '5432'),
    'database': os.getenv('PG_DB', 'medhistory'),
    'user': os.getenv('PG_USER', 'medhistory_user'),
    'password': os.getenv('PG_PASSWORD', 'medhistory_local_pass'),
}

# Конфигурация MongoDB
MONGO_CONFIG = {
    'host': os.getenv('MONGO_HOST', 'localhost'),
    'port': int(os.getenv('MONGO_PORT', '27017')),
    'username': os.getenv('MONGO_USER', 'admin'),
    'password': os.getenv('MONGO_PASSWORD', 'mongodb_secure_pass'),
    'database': os.getenv('MONGO_DB', 'medhistory'),
}

# ============== PostgreSQL ==============

def get_pg_connection():
    return psycopg2.connect(**PG_CONFIG)

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

def get_mongo_client():
    return MongoClient(
        host=MONGO_CONFIG['host'],
        port=MONGO_CONFIG['port'],
        username=MONGO_CONFIG['username'],
        password=MONGO_CONFIG['password'],
        authSource='admin'
    )

def get_mongo_collections():
    try:
        client = get_mongo_client()
        db = client[MONGO_CONFIG['database']]
        collections = db.list_collection_names()
        client.close()
        return sorted(collections)
    except Exception as e:
        print(f"MongoDB error: {e}")
        return []

def get_mongo_collection_data(collection_name, limit=100, offset=0):
    try:
        client = get_mongo_client()
        db = client[MONGO_CONFIG['database']]
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
    </style>
</head>
<body>
    <div class="container">
        <aside class="sidebar">
            <div class="sidebar-header">
                <h1>DB Viewer</h1>
                <p>MedHistory Databases</p>
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
    
    <script>
        let currentTable = null;
        let currentDbType = null; // 'postgres' or 'mongo'
        let currentOffset = 0;
        let totalRows = 0;
        const limit = 100;
        
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
            }
        }
        
        // Выбрать таблицу/коллекцию
        async function selectTable(name, dbType) {
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
        
        // Загрузить данные
        async function loadData() {
            const endpoint = currentDbType === 'postgres' 
                ? `/api/postgres/table/${currentTable}/data?limit=${limit}&offset=${currentOffset}`
                : `/api/mongo/collection/${currentTable}/data?limit=${limit}&offset=${currentOffset}`;
            
            const res = await fetch(endpoint);
            const data = await res.json();
            totalRows = data.total;
            
            // Обновить заголовок
            const badge = currentDbType === 'postgres' 
                ? '<span class="badge postgres">PostgreSQL</span>'
                : '<span class="badge mongo">MongoDB</span>';
            document.getElementById('header').querySelector('h2').innerHTML = `${badge} ${currentTable}`;
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
            
            // Отобразить данные
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
            
            // Собрать все уникальные ключи для MongoDB
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
            
            // Обновить пагинацию
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
        
        // Сохраняем данные для модального окна
        let currentData = [];
        
        // Обновляем loadData для сохранения данных
        const originalLoadData = loadData;
        loadData = async function() {
            const endpoint = currentDbType === 'postgres' 
                ? `/api/postgres/table/${currentTable}/data?limit=${limit}&offset=${currentOffset}`
                : `/api/mongo/collection/${currentTable}/data?limit=${limit}&offset=${currentOffset}`;
            
            const res = await fetch(endpoint);
            const data = await res.json();
            currentData = data.rows;
            totalRows = data.total;
            
            // Обновить заголовок
            const badge = currentDbType === 'postgres' 
                ? '<span class="badge postgres">PostgreSQL</span>'
                : '<span class="badge mongo">MongoDB</span>';
            document.getElementById('header').querySelector('h2').innerHTML = `${badge} ${currentTable}`;
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
        };
        
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
            if (e.key === 'Escape') closeModal();
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

if __name__ == '__main__':
    print("=" * 60)
    print("DB Viewer для MedHistory")
    print("=" * 60)
    print(f"PostgreSQL: {PG_CONFIG['host']}:{PG_CONFIG['port']}/{PG_CONFIG['database']}")
    print(f"MongoDB:    {MONGO_CONFIG['host']}:{MONGO_CONFIG['port']}/{MONGO_CONFIG['database']}")
    print()
    print("Откройте в браузере: http://localhost:5050")
    print("=" * 60)
    app.run(host='0.0.0.0', port=5050, debug=True)
