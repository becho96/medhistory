from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from io import BytesIO
import uuid
import logging
from urllib.parse import quote

logger = logging.getLogger(__name__)

from app.db.postgres import get_db
from app.models.user import User
from app.schemas.document import (
    Document as DocumentSchema,
    DocumentWithMetadata,
    DocumentUploadResponse
)
from app.services.document_service import DocumentService
from app.services.unit_normalization_service import unit_normalization_service
from app.services.analyte_normalization_service_db import analyte_normalization_service_db
from app.api.deps import get_current_user, get_profile_user_id
from app.db.mongodb import document_metadata_collection

router = APIRouter()

@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    profile_user_id: uuid.UUID = Depends(get_profile_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Upload a new document
    
    Use X-Profile-Id header to upload to a family member's profile.
    """
    
    try:
        document = await DocumentService.upload_document(
            file=file,
            user_id=profile_user_id,
            db=db
        )
        
        return DocumentUploadResponse(
            document_id=document.id,
            status=document.processing_status,
            message="Документ успешно загружен и обрабатывается"
        )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при загрузке документа: {str(e)}"
        )

@router.get("/", response_model=List[DocumentWithMetadata])
async def get_documents(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=10000),  # Increased for timeline support
    document_type: Optional[List[str]] = Query(None),
    patient_name: Optional[List[str]] = Query(None),
    medical_facility: Optional[List[str]] = Query(None),
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    created_from: Optional[str] = None,
    created_to: Optional[str] = None,
    sort_by: str = Query("document_date", regex="^(document_date|created_at)$"),
    # MongoDB filters
    specialties: Optional[List[str]] = Query(None),
    document_subtype: Optional[List[str]] = Query(None),
    research_area: Optional[List[str]] = Query(None),
    current_user: User = Depends(get_current_user),
    profile_user_id: uuid.UUID = Depends(get_profile_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Get user documents with optional filters
    
    Supports filtering by both PostgreSQL and MongoDB fields:
    
    PostgreSQL filters:
    - document_type: filter by document types (multiple values supported)
    - patient_name: filter by patient names (multiple values supported)
    - medical_facility: filter by medical facilities (multiple values supported)
    - date_from/date_to: filter by document_date (date on the medical document)
    - created_from/created_to: filter by created_at (upload date to system)
    - sort_by: "document_date" (default) or "created_at"
    
    MongoDB filters:
    - specialties: filter by specialties (for "Прием врача" documents)
    - document_subtype: filter by document subtype
    - research_area: filter by research area (for "Инструментальное исследование")
    """
    
    documents = await DocumentService.get_documents(
        user_id=profile_user_id,
        db=db,
        skip=skip,
        limit=limit,
        document_type=document_type,
        patient_name=patient_name,
        medical_facility=medical_facility,
        date_from=date_from,
        date_to=date_to,
        created_from=created_from,
        created_to=created_to,
        sort_by=sort_by,
        specialties=specialties,
        document_subtype=document_subtype,
        research_area=research_area
    )
    
    # Enrich documents with MongoDB metadata
    if documents:
        doc_ids = [str(doc.id) for doc in documents if doc.mongodb_metadata_id]
        metadata_by_doc_id = {}
        
        if doc_ids:
            cursor = document_metadata_collection.find({
                "document_id": {"$in": doc_ids}
            }, {
                "document_id": 1,
                "classification.specialties": 1,
                "classification.document_subtype": 1,
                "classification.research_area": 1,
                "extracted_data.summary": 1
            })
            mongo_docs = await cursor.to_list(length=len(doc_ids))
            
            for m in mongo_docs:
                doc_id = m.get("document_id")
                metadata_by_doc_id[doc_id] = {
                    "specialties": m.get("classification", {}).get("specialties"),
                    "document_subtype": m.get("classification", {}).get("document_subtype"),
                    "research_area": m.get("classification", {}).get("research_area"),
                    "summary": m.get("extracted_data", {}).get("summary")
                }
        
        # Build response with metadata
        result = []
        for doc in documents:
            doc_dict = {
                **doc.__dict__,
            }
            
            # Add MongoDB metadata if available
            metadata = metadata_by_doc_id.get(str(doc.id), {})
            specialties = metadata.get("specialties")
            doc_dict["specialty"] = ", ".join(specialties) if specialties else None
            doc_dict["document_subtype"] = metadata.get("document_subtype")
            doc_dict["research_area"] = metadata.get("research_area")
            doc_dict["summary"] = metadata.get("summary")
            
            result.append(DocumentWithMetadata(**doc_dict))
        
        return result
    
    return []

@router.get("/count/total")
async def get_documents_count(
    document_type: Optional[List[str]] = Query(None),
    patient_name: Optional[List[str]] = Query(None),
    medical_facility: Optional[List[str]] = Query(None),
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    created_from: Optional[str] = None,
    created_to: Optional[str] = None,
    # MongoDB filters
    specialties: Optional[List[str]] = Query(None),
    document_subtype: Optional[List[str]] = Query(None),
    research_area: Optional[List[str]] = Query(None),
    current_user: User = Depends(get_current_user),
    profile_user_id: uuid.UUID = Depends(get_profile_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Get total count of user documents with optional filters"""
    
    count = await DocumentService.get_documents_count(
        user_id=profile_user_id,
        db=db,
        document_type=document_type,
        patient_name=patient_name,
        medical_facility=medical_facility,
        date_from=date_from,
        date_to=date_to,
        created_from=created_from,
        created_to=created_to,
        specialties=specialties,
        document_subtype=document_subtype,
        research_area=research_area
    )
    
    return {"total": count}

@router.get("/{document_id}", response_model=DocumentWithMetadata)
async def get_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    profile_user_id: uuid.UUID = Depends(get_profile_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Get document by ID with MongoDB metadata"""
    
    document = await DocumentService.get_document_by_id(
        document_id=document_id,
        user_id=profile_user_id,
        db=db
    )
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Документ не найден"
        )
    
    # Enrich with MongoDB metadata
    doc_dict = {
        "id": document.id,
        "user_id": document.user_id,
        "original_filename": document.original_filename,
        "file_size": document.file_size,
        "file_type": document.file_type,
        "file_url": document.file_url,
        "document_type": document.document_type,
        "document_date": document.document_date,
        "patient_name": document.patient_name,
        "medical_facility": document.medical_facility,
        "processing_status": document.processing_status,
        "mongodb_metadata_id": document.mongodb_metadata_id,
        "created_at": document.created_at,
        "updated_at": document.updated_at,
        "specialty": None,
        "document_subtype": None,
        "research_area": None,
        "summary": None
    }
    
    # Load MongoDB metadata if available
    if document.mongodb_metadata_id:
        mongo_doc = await document_metadata_collection.find_one({
            "document_id": str(document.id)
        })
        
        if mongo_doc:
            classification = mongo_doc.get("classification", {})
            extracted_data = mongo_doc.get("extracted_data", {})
            
            specialties = classification.get("specialties")
            doc_dict["specialty"] = ", ".join(specialties) if specialties else None
            doc_dict["document_subtype"] = classification.get("document_subtype")
            doc_dict["research_area"] = classification.get("research_area")
            doc_dict["summary"] = extracted_data.get("summary")
    
    return DocumentWithMetadata(**doc_dict)

@router.get("/{document_id}/file")
async def download_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    profile_user_id: uuid.UUID = Depends(get_profile_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Download document file"""
    
    document = await DocumentService.get_document_by_id(
        document_id=document_id,
        user_id=profile_user_id,
        db=db
    )
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Документ не найден"
        )
    
    # Get file from MinIO
    try:
        print(f"📥 Downloading file: {document.file_url}")
        print(f"   Document ID: {document.id}")
        print(f"   Filename: {document.original_filename}")
        
        file_content = DocumentService.get_file_from_minio(document.file_url)
        
        print(f"   ✅ File downloaded: {len(file_content)} bytes")
        
        # Determine content type
        content_types = {
            'pdf': 'application/pdf',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        }
        
        content_type = content_types.get(document.file_type, 'application/octet-stream')
        
        print(f"   Content-Type: {content_type}")
        print(f"   Creating StreamingResponse...")
        
        # Encode filename for Content-Disposition header (RFC 5987)
        # This supports UTF-8 filenames including Cyrillic
        encoded_filename = quote(document.original_filename)
        
        return StreamingResponse(
            BytesIO(file_content),
            media_type=content_type,
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"
            }
        )
    
    except Exception as e:
        print(f"❌ Error downloading file:")
        print(f"   Document ID: {document_id}")
        print(f"   File URL: {document.file_url if document else 'N/A'}")
        print(f"   Error: {str(e)}")
        import traceback
        traceback.print_exc()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при скачивании файла: {str(e)}"
        )

@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    profile_user_id: uuid.UUID = Depends(get_profile_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Delete document"""
    
    success = await DocumentService.delete_document(
        document_id=document_id,
        user_id=profile_user_id,
        db=db
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Документ не найден"
        )
    
    return None


@router.get("/{document_id}/labs")
async def get_document_labs(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    profile_user_id: uuid.UUID = Depends(get_profile_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Return extracted lab results for a document from MongoDB."""

    document = await DocumentService.get_document_by_id(
        document_id=document_id,
        user_id=profile_user_id,
        db=db,
    )

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Документ не найден",
        )

    mongo_doc = await document_metadata_collection.find_one({
        "document_id": str(document_id)
    })

    lab_results = (mongo_doc or {}).get("extracted_data", {}).get("lab_results", [])

    return {
        "document_id": str(document_id),
        "lab_results": lab_results,
    }


@router.get("/{document_id}/labs/summary")
async def get_document_labs_summary(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    profile_user_id: uuid.UUID = Depends(get_profile_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Return quick summary whether labs exist and how many."""

    document = await DocumentService.get_document_by_id(
        document_id=document_id,
        user_id=profile_user_id,
        db=db,
    )

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Документ не найден",
        )

    mongo_doc = await document_metadata_collection.find_one({
        "document_id": str(document_id)
    }, {"extracted_data.lab_results": 1})

    lab_results = (mongo_doc or {}).get("extracted_data", {}).get("lab_results", [])
    count = len(lab_results or [])

    return {
        "document_id": str(document_id),
        "has_labs": count > 0,
        "count": count,
    }


@router.get("/labs/analytes")
async def list_available_analytes(
    current_user: User = Depends(get_current_user),
    profile_user_id: uuid.UUID = Depends(get_profile_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Return distinct analyte names grouped by categories with standard units.
    
    Response format:
    {
        "categories": [
            {
                "name": "Общий анализ крови",
                "analytes": [
                    {"canonical_name": "Гемоглобин", "standard_unit": "г/л", "count": 5},
                    ...
                ]
            },
            ...
        ]
    }
    """
    # Проверяем, загружен ли справочник. Если нет — загружаем (в т.ч. после invalidate_cache)
    if not analyte_normalization_service_db.is_loaded:
        logger.warning("⚠️ Справочник анализов не загружен, пробуем загрузить...")
        try:
            await analyte_normalization_service_db.load_from_db(db, force=True)
            logger.info(f"✅ Справочник загружен: {analyte_normalization_service_db.get_stats()}")
        except Exception as e:
            logger.error(f"❌ Не удалось загрузить справочник: {e}")
    
    # Получаем все уникальные комбинации названий анализов и единиц из MongoDB
    # Группируем по (test_name, unit) чтобы различать например "Лимфоциты %" и "Лимфоциты абс"
    pipeline = [
        {"$match": {"user_id": str(profile_user_id)}},
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
        {"$sort": {"name": 1}},
    ]
    
    cursor = document_metadata_collection.aggregate(pipeline)
    
    # Собираем анализы и группируем по каноническим названиям
    canonical_analytes = {}  # canonical_name -> {count, standard_unit, category}
    unknown_analytes = []  # Анализы без канонического названия
    
    async for doc in cursor:
        original_name = doc.get("name", "")
        unit = doc.get("unit", "")
        count = doc.get("count", 0)
        
        if not original_name:
            continue
        
        # Пытаемся найти каноническое название с учётом единицы измерения
        canonical_name = analyte_normalization_service_db.get_canonical_name(original_name, unit)
        
        if canonical_name:
            analyte_data = analyte_normalization_service_db.get_analyte(canonical_name)
            
            if canonical_name in canonical_analytes:
                # Суммируем count для синонимов
                canonical_analytes[canonical_name]["count"] += count
            else:
                canonical_analytes[canonical_name] = {
                    "canonical_name": canonical_name,
                    "standard_unit": analyte_data.standard_unit if analyte_data else None,
                    "category": analyte_data.category_name if analyte_data else "Другие анализы",
                    "count": count
                }
        else:
            # Неизвестный анализ - группируем по оригинальному названию
            # Используем комбинацию name+unit как ключ для избежания дубликатов
            unknown_key = f"{original_name}|{unit or ''}"
            existing = next((a for a in unknown_analytes if f"{a['canonical_name']}|{a.get('_unit', '')}" == unknown_key), None)
            if existing:
                existing["count"] += count
            else:
                unknown_analytes.append({
                    "canonical_name": original_name,  # Используем оригинальное название
                    "standard_unit": unit,
                    "category": "Другие анализы",
                    "count": count,
                    "_unit": unit  # Временное поле для группировки
                })
    
    # Объединяем все анализы
    all_analytes = list(canonical_analytes.values()) + unknown_analytes
    
    # Группируем по категориям
    categories_dict = {}
    for analyte in all_analytes:
        category = analyte.get("category", "Другое")
        if category not in categories_dict:
            categories_dict[category] = []
        categories_dict[category].append({
            "canonical_name": analyte["canonical_name"],
            "standard_unit": analyte["standard_unit"],
            "count": analyte["count"]
        })
    
    # Сортируем категории по порядку из БД
    db_categories = analyte_normalization_service_db.get_all_categories()
    category_order = [c["name"] for c in db_categories]
    result_categories = []
    
    for category_name in category_order:
        if category_name in categories_dict:
            result_categories.append({
                "name": category_name,
                "analytes": sorted(
                    categories_dict[category_name],
                    key=lambda x: x["canonical_name"]
                )
            })
    
    # Добавляем категории, которых нет в порядке (неизвестные)
    for category_name, analytes_list in categories_dict.items():
        if category_name not in category_order:
            result_categories.append({
                "name": category_name,
                "analytes": sorted(analytes_list, key=lambda x: x["canonical_name"])
            })
    
    return {"categories": result_categories}


@router.get("/labs/analytes/debug")
async def debug_analytes_mapping(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Debug endpoint to check analyte normalization service status."""
    stats = analyte_normalization_service_db.get_stats()
    
    # Тестовые примеры маппинга
    test_names = ["Лимфоциты", "Гемоглобин", "Hemoglobin", "HGB", "Глюкоза"]
    test_results = {}
    for name in test_names:
        canonical = analyte_normalization_service_db.get_canonical_name(name)
        test_results[name] = canonical
    
    return {
        "service_stats": stats,
        "test_mappings": test_results,
        "all_categories": analyte_normalization_service_db.get_all_categories(),
    }


@router.get("/labs/timeseries")
async def get_lab_timeseries(
    analyte: str = Query(..., description="Каноническое название анализа, например: Гемоглобин"),
    current_user: User = Depends(get_current_user),
    profile_user_id: uuid.UUID = Depends(get_profile_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Return time series for a given analyte across user's documents.
    
    All values are converted to standard units automatically.
    
    Response:
    {
        "analyte": "Гемоглобин",
        "standard_unit": "г/л",
        "category": "Общий анализ крови",
        "reference_min": 120.0,
        "reference_max": 160.0,
        "points": [
            {
                "date": "2024-01-15",
                "value_num": 145.0,
                "unit": "г/л",
                "document_id": "...",
                "reference_range": "120-160",
                "flag": "N"
            }
        ]
    }
    """
    # Получаем информацию о пользователе (для определения пола)
    from sqlalchemy import select as sql_select
    user_query = sql_select(User).where(User.id == profile_user_id)
    user_result = await db.execute(user_query)
    profile_user = user_result.scalar_one_or_none()
    
    # Получаем данные анализа из справочника
    analyte_data = analyte_normalization_service_db.get_analyte(analyte)
    
    # Определяем, это процентный или абсолютный вариант анализа
    # Названия в БД с пробелом: "Лимфоциты (%)", "Лимфоциты (абс)"
    is_percentage_analyte = analyte.endswith(" (%)")
    is_absolute_analyte = analyte.endswith(" (абс)")
    
    # Собираем все синонимы для поиска
    if analyte_data:
        synonyms = list(analyte_data.synonyms) if analyte_data.synonyms else [analyte]
        standard_unit = analyte_data.standard_unit
        category = analyte_data.category_name
        
        # Для анализов с двойными версиями (% и абс) добавляем синонимы парного анализа
        # Это нужно потому что в MongoDB может быть "Нейтрофилы" с unit="%" 
        # а не "Нейтрофилы %" как синоним
        dual_pairs = {
            "Лимфоциты (%)": "Лимфоциты (абс)",
            "Лимфоциты (абс)": "Лимфоциты (%)",
            "Нейтрофилы (%)": "Нейтрофилы (абс)",
            "Нейтрофилы (абс)": "Нейтрофилы (%)",
            "Моноциты (%)": "Моноциты (абс)",
            "Моноциты (абс)": "Моноциты (%)",
            "Эозинофилы (%)": "Эозинофилы (абс)",
            "Эозинофилы (абс)": "Эозинофилы (%)",
            "Базофилы (%)": "Базофилы (абс)",
            "Базофилы (абс)": "Базофилы (%)",
        }
        
        if analyte in dual_pairs:
            paired_analyte = dual_pairs[analyte]
            paired_data = analyte_normalization_service_db.get_analyte(paired_analyte)
            if paired_data and paired_data.synonyms:
                # Добавляем синонимы парного анализа для расширенного поиска
                synonyms.extend(paired_data.synonyms)
                # Убираем дубликаты
                synonyms = list(set(synonyms))
    else:
        # Если анализ не в справочнике, ищем по точному совпадению
        synonyms = [analyte]
        standard_unit = None
        category = "Другие анализы"
    
    # Синонимы в CachedAnalyte хранятся как "название [единица]" (например "Лимфоциты [10*9/л]").
    # Для поиска в MongoDB нужны только имена без суффикса с единицей.
    synonyms = list(set(s.split(' [')[0] for s in synonyms))

    # Строим regex для поиска всех синонимов
    # Экранируем специальные символы в названиях
    import re
    escaped_synonyms = [re.escape(s) for s in synonyms]
    regex_pattern = f"^({'|'.join(escaped_synonyms)})$"
    
    pipeline = [
        {"$match": {"user_id": str(profile_user_id)}},
        {"$project": {"document_id": 1, "extracted_data.lab_results": 1}},
        {"$unwind": "$extracted_data.lab_results"},
        {"$match": {"extracted_data.lab_results.test_name": {"$regex": regex_pattern, "$options": "i"}}},
    ]

    cursor = document_metadata_collection.aggregate(pipeline)
    points = []
    doc_ids = set()
    
    async for doc in cursor:
        lr = doc.get("extracted_data", {}).get("lab_results", {})
        if not isinstance(lr, dict):
            continue
        
        doc_id = doc.get("document_id")
        original_value = lr.get("value")
        original_unit = lr.get("unit") or ""
        
        # Фильтрация по типу анализа (процентный/абсолютный)
        # Если запрошен процентный анализ - берём только записи с unit содержащим %
        # Если запрошен абсолютный анализ - пропускаем записи с unit содержащим %
        unit_has_percent = "%" in original_unit
        
        if is_percentage_analyte and not unit_has_percent:
            # Запрошен процентный, но unit не содержит % - пропускаем
            continue
        if is_absolute_analyte and unit_has_percent:
            # Запрошен абсолютный, но unit содержит % - пропускаем
            continue
        
        # Конвертируем значение в стандартную единицу
        if analyte_data:
            converted_value, converted_unit = analyte_normalization_service_db.convert_value(
                original_value, original_unit, analyte
            )
        else:
            # Для неизвестных анализов - просто парсим число
            try:
                converted_value = float(str(original_value).replace(',', '.').strip())
            except (ValueError, TypeError):
                converted_value = None
            converted_unit = original_unit
        
        if converted_value is None:
            continue
        
        if doc_id:
            doc_ids.add(doc_id)
            
        points.append({
            "document_id": doc_id,
            "value_num": converted_value,
            "unit": converted_unit or standard_unit,
            "original_value": original_value,
            "original_unit": original_unit,
            "reference_range": lr.get("reference_range"),
            "flag": lr.get("flag"),
        })

    # Fetch dates for documents from Postgres
    if doc_ids:
        import uuid as _uuid
        from sqlalchemy import select
        from app.models.document import Document as DocumentModel
        q = select(DocumentModel.id, DocumentModel.document_date).where(
            DocumentModel.id.in_([_uuid.UUID(x) for x in doc_ids])
        )
        result = await db.execute(q)
        id_to_date = {str(r[0]): r[1] for r in result.all()}
        for p in points:
            p["date"] = id_to_date.get(p["document_id"])

    # Sort by date
    points.sort(key=lambda x: (x.get("date") is None, x.get("date") or ""))

    # Получаем референсные значения из analyte_standards
    reference_min = None
    reference_max = None
    
    if analyte_data:
        from sqlalchemy import select as sql_select
        from app.models.analyte import AnalyteStandard
        
        # Получаем запись из analyte_standards
        analyte_standard_query = sql_select(AnalyteStandard).where(
            AnalyteStandard.canonical_name == analyte
        )
        analyte_standard_result = await db.execute(analyte_standard_query)
        analyte_standard = analyte_standard_result.scalar_one_or_none()
        
        if analyte_standard:
            # Выбираем референсные значения в зависимости от пола.
            # Для гендер-нейтральных анализов референсы хранятся только в male_*-колонках,
            # female_*-колонки оставлены NULL — для female-пользователя fallback'имся на male.
            male_min = float(analyte_standard.reference_male_min) if analyte_standard.reference_male_min is not None else None
            male_max = float(analyte_standard.reference_male_max) if analyte_standard.reference_male_max is not None else None
            female_min = float(analyte_standard.reference_female_min) if analyte_standard.reference_female_min is not None else None
            female_max = float(analyte_standard.reference_female_max) if analyte_standard.reference_female_max is not None else None

            if profile_user and profile_user.gender and profile_user.gender.value == "female":
                reference_min = female_min if female_min is not None else male_min
                reference_max = female_max if female_max is not None else male_max
            else:
                # male или пол не указан → берём male; если male пуст, fallback на female
                reference_min = male_min if male_min is not None else female_min
                reference_max = male_max if male_max is not None else female_max

    return {
        "analyte": analyte,
        "standard_unit": standard_unit,
        "category": category,
        "reference_min": reference_min,
        "reference_max": reference_max,
        "points": points
    }


@router.get("/filters/values")
async def get_filter_values(
    field: str = Query(..., description="Field name: document_type, patient_name, medical_facility, specialties, document_subtype, research_area"),
    q: Optional[str] = Query(None, description="Search query to filter values"),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    profile_user_id: uuid.UUID = Depends(get_profile_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get distinct values for filter fields.
    
    Supports both PostgreSQL fields (document_type, patient_name, medical_facility)
    and MongoDB fields (specialties, document_subtype, research_area).
    
    Query parameter 'q' can be used to search/filter the values.
    """
    
    # PostgreSQL fields
    postgres_fields = {"document_type", "patient_name", "medical_facility"}
    # MongoDB fields
    mongodb_fields = {"specialties", "document_subtype", "research_area"}
    
    if field in postgres_fields:
        values = await DocumentService.get_distinct_field_values(
            user_id=profile_user_id,
            db=db,
            field=field,
            q=q,
            limit=limit
        )
        return {"field": field, "values": values}
    
    elif field in mongodb_fields:
        values = await DocumentService.get_distinct_mongodb_field_values(
            user_id=profile_user_id,
            field=field,
            q=q,
            limit=limit
        )
        return {"field": field, "values": values}
    
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid field: {field}. Allowed fields: {', '.join(postgres_fields | mongodb_fields)}"
        )

