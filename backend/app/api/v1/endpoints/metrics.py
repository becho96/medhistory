from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from datetime import datetime, timedelta
from typing import Dict, Any
import asyncio

from app.db.postgres import get_db
from app.db.mongodb import mongodb
from app.db.minio_client import minio_client
from app.models.user import User
from app.models.document import Document
from app.models.interpretation import Interpretation

router = APIRouter()

@router.get("/business")
async def get_business_metrics(
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Получить бизнес-метрики для мониторинга
    
    Возвращает:
    - Статистику по пользователям
    - Статистику по документам
    - Статистику по интерпретациям
    - Статистику по отчетам
    - Использование хранилища
    """
    
    # Дата 30 дней назад для расчета активности
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    
    # Запросы к PostgreSQL
    try:
        # Общее количество пользователей
        users_total_query = select(func.count(User.id))
        users_total_result = await db.execute(users_total_query)
        users_total = users_total_result.scalar() or 0
        
        # Новые пользователи за 30 дней
        users_new_query = select(func.count(User.id)).where(
            User.created_at >= thirty_days_ago
        )
        users_new_result = await db.execute(users_new_query)
        users_new_30d = users_new_result.scalar() or 0
        
        # Активные пользователи за 30 дней (у кого есть документы за последние 30 дней)
        users_active_query = select(func.count(func.distinct(Document.user_id))).where(
            Document.created_at >= thirty_days_ago
        )
        users_active_result = await db.execute(users_active_query)
        users_active_30d = users_active_result.scalar() or 0
        
        # Общее количество документов
        documents_total_query = select(func.count(Document.id))
        documents_total_result = await db.execute(documents_total_query)
        documents_total = documents_total_result.scalar() or 0
        
        # Документы по типам
        documents_by_type_query = select(
            Document.document_type,
            func.count(Document.id)
        ).group_by(Document.document_type)
        documents_by_type_result = await db.execute(documents_by_type_query)
        documents_by_type = {
            row[0] or "unknown": row[1] 
            for row in documents_by_type_result.fetchall()
        }
        
        # Новые документы за 30 дней
        documents_new_query = select(func.count(Document.id)).where(
            Document.created_at >= thirty_days_ago
        )
        documents_new_result = await db.execute(documents_new_query)
        documents_new_30d = documents_new_result.scalar() or 0
        
        # Общее количество интерпретаций
        interpretations_total_query = select(func.count(Interpretation.id))
        interpretations_total_result = await db.execute(interpretations_total_query)
        interpretations_total = interpretations_total_result.scalar() or 0
        
        # Успешные интерпретации (где status = completed)
        interpretations_success_query = select(func.count(Interpretation.id)).where(
            Interpretation.status == "completed"
        )
        interpretations_success_result = await db.execute(interpretations_success_query)
        interpretations_success = interpretations_success_result.scalar() or 0
        
        # Неудачные интерпретации
        interpretations_failed = interpretations_total - interpretations_success
        
        # Новые интерпретации за 30 дней
        interpretations_new_query = select(func.count(Interpretation.id)).where(
            Interpretation.created_at >= thirty_days_ago
        )
        interpretations_new_result = await db.execute(interpretations_new_query)
        interpretations_new_30d = interpretations_new_result.scalar() or 0
        
    except Exception as e:
        print(f"Error fetching PostgreSQL metrics: {e}")
        # Возвращаем нулевые значения в случае ошибки
        users_total = users_new_30d = users_active_30d = 0
        documents_total = documents_new_30d = 0
        documents_by_type = {}
        interpretations_total = interpretations_success = interpretations_failed = 0
        interpretations_new_30d = 0
    
    # Запросы к MongoDB (для отчетов)
    reports_total = 0
    reports_new_30d = 0
    try:
        reports_collection = mongodb.get_collection("reports")
        
        # Общее количество отчетов
        reports_total = await reports_collection.count_documents({})
        
        # Новые отчеты за 30 дней
        reports_new_30d = await reports_collection.count_documents({
            "created_at": {"$gte": thirty_days_ago}
        })
    except Exception as e:
        print(f"Error fetching MongoDB metrics: {e}")
    
    # Использование хранилища MinIO
    storage_bytes = 0
    storage_objects = 0
    try:
        bucket_name = "medhistory-documents"
        
        # Получаем список всех объектов
        objects = minio_client.list_objects(bucket_name, recursive=True)
        
        for obj in objects:
            storage_bytes += obj.size
            storage_objects += 1
    except Exception as e:
        print(f"Error fetching MinIO metrics: {e}")
    
    # Формируем ответ
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "users": {
            "total": users_total,
            "active_30d": users_active_30d,
            "new_30d": users_new_30d
        },
        "documents": {
            "total": documents_total,
            "new_30d": documents_new_30d,
            "by_type": documents_by_type
        },
        "interpretations": {
            "total": interpretations_total,
            "success": interpretations_success,
            "failed": interpretations_failed,
            "new_30d": interpretations_new_30d
        },
        "reports": {
            "total": reports_total,
            "new_30d": reports_new_30d
        },
        "storage": {
            "bytes": storage_bytes,
            "objects": storage_objects
        }
    }

@router.get("/health")
async def health_check() -> Dict[str, str]:
    """
    Проверка здоровья API для мониторинга
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }

