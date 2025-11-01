"""
Custom Prometheus Exporter для бизнес-метрик медицинского сервиса
"""
import os
import time
import asyncio
import httpx
from prometheus_client import start_http_server, Gauge, Counter, Info
from prometheus_client.core import GaugeMetricFamily, REGISTRY
from typing import Dict, Any

# Конфигурация
BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")
METRICS_ENDPOINT = f"{BACKEND_URL}/api/v1/metrics/business"
SCRAPE_INTERVAL = int(os.getenv("SCRAPE_INTERVAL", "30"))  # секунды
EXPORTER_PORT = int(os.getenv("EXPORTER_PORT", "9100"))

# Метрики Prometheus
# Пользователи
users_total = Gauge('medhistory_users_total', 'Общее количество пользователей')
users_active_30d = Gauge('medhistory_users_active_30d', 'Активные пользователи за 30 дней')
users_new_30d = Gauge('medhistory_users_new_30d', 'Новые пользователи за 30 дней')

# Документы
documents_total = Gauge('medhistory_documents_total', 'Общее количество документов')
documents_new_30d = Gauge('medhistory_documents_new_30d', 'Новые документы за 30 дней')
documents_by_type = Gauge('medhistory_documents_by_type', 'Документы по типам', ['document_type'])

# Интерпретации AI
interpretations_total = Gauge('medhistory_interpretations_total', 'Общее количество интерпретаций')
interpretations_success = Gauge('medhistory_interpretations_success_total', 'Успешные интерпретации')
interpretations_failed = Gauge('medhistory_interpretations_failed_total', 'Неудачные интерпретации')
interpretations_new_30d = Gauge('medhistory_interpretations_new_30d', 'Новые интерпретации за 30 дней')

# Отчеты
reports_total = Gauge('medhistory_reports_total', 'Общее количество отчетов')
reports_new_30d = Gauge('medhistory_reports_new_30d', 'Новые отчеты за 30 дней')

# Хранилище
storage_bytes = Gauge('medhistory_storage_bytes', 'Использование хранилища в байтах')
storage_objects = Gauge('medhistory_storage_objects', 'Количество объектов в хранилище')

# Счетчики для мониторинга работы экспортера
scrape_success = Counter('medhistory_exporter_scrape_success_total', 'Успешные сборы метрик')
scrape_errors = Counter('medhistory_exporter_scrape_errors_total', 'Ошибки при сборе метрик')
scrape_duration = Gauge('medhistory_exporter_scrape_duration_seconds', 'Длительность сбора метрик')

# Информация о экспортере
exporter_info = Info('medhistory_exporter', 'Информация о экспортере')
exporter_info.info({
    'version': '1.0.0',
    'backend_url': BACKEND_URL,
    'scrape_interval': str(SCRAPE_INTERVAL)
})


async def fetch_metrics() -> Dict[str, Any]:
    """
    Получить метрики из Backend API
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(METRICS_ENDPOINT)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            print(f"❌ HTTP Error fetching metrics: {e}")
            raise
        except Exception as e:
            print(f"❌ Error fetching metrics: {e}")
            raise


def update_metrics(data: Dict[str, Any]):
    """
    Обновить метрики Prometheus на основе полученных данных
    """
    try:
        # Пользователи
        users_data = data.get('users', {})
        users_total.set(users_data.get('total', 0))
        users_active_30d.set(users_data.get('active_30d', 0))
        users_new_30d.set(users_data.get('new_30d', 0))
        
        # Документы
        documents_data = data.get('documents', {})
        documents_total.set(documents_data.get('total', 0))
        documents_new_30d.set(documents_data.get('new_30d', 0))
        
        # Документы по типам
        by_type = documents_data.get('by_type', {})
        for doc_type, count in by_type.items():
            documents_by_type.labels(document_type=doc_type).set(count)
        
        # Интерпретации
        interpretations_data = data.get('interpretations', {})
        interpretations_total.set(interpretations_data.get('total', 0))
        interpretations_success.set(interpretations_data.get('success', 0))
        interpretations_failed.set(interpretations_data.get('failed', 0))
        interpretations_new_30d.set(interpretations_data.get('new_30d', 0))
        
        # Отчеты
        reports_data = data.get('reports', {})
        reports_total.set(reports_data.get('total', 0))
        reports_new_30d.set(reports_data.get('new_30d', 0))
        
        # Хранилище
        storage_data = data.get('storage', {})
        storage_bytes.set(storage_data.get('bytes', 0))
        storage_objects.set(storage_data.get('objects', 0))
        
        print(f"✅ Metrics updated successfully at {time.strftime('%Y-%m-%d %H:%M:%S')}")
        
    except Exception as e:
        print(f"❌ Error updating metrics: {e}")
        raise


async def collect_metrics_loop():
    """
    Основной цикл сбора метрик
    """
    print(f"🚀 Starting metrics collection loop (interval: {SCRAPE_INTERVAL}s)")
    
    while True:
        start_time = time.time()
        
        try:
            # Получить метрики из API
            data = await fetch_metrics()
            
            # Обновить метрики Prometheus
            update_metrics(data)
            
            # Записать успешный сбор
            scrape_success.inc()
            
        except Exception as e:
            print(f"❌ Error in metrics collection: {e}")
            scrape_errors.inc()
        
        finally:
            # Записать длительность сбора
            duration = time.time() - start_time
            scrape_duration.set(duration)
        
        # Подождать до следующего сбора
        await asyncio.sleep(SCRAPE_INTERVAL)


def main():
    """
    Главная функция экспортера
    """
    print("=" * 60)
    print("🏥 MedHistory Custom Metrics Exporter")
    print("=" * 60)
    print(f"📊 Exporter Port: {EXPORTER_PORT}")
    print(f"🔗 Backend URL: {BACKEND_URL}")
    print(f"⏱️  Scrape Interval: {SCRAPE_INTERVAL}s")
    print("=" * 60)
    
    # Запустить HTTP сервер для Prometheus
    start_http_server(EXPORTER_PORT)
    print(f"✅ Prometheus metrics server started on port {EXPORTER_PORT}")
    print(f"📈 Metrics available at http://localhost:{EXPORTER_PORT}/metrics")
    
    # Запустить цикл сбора метрик
    try:
        asyncio.run(collect_metrics_loop())
    except KeyboardInterrupt:
        print("\n🛑 Exporter stopped by user")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        raise


if __name__ == "__main__":
    main()

