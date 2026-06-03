from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Dict, Any
from io import BytesIO
import uuid
import logging
from urllib.parse import quote
from datetime import datetime

logger = logging.getLogger(__name__)

from app.db.postgres import get_db
from sqlalchemy import select
from app.models.user import User
from app.models.document import Document as DocumentModel
from app.schemas.document import (
    Document as DocumentSchema,
    DocumentContentResponse,
    DocumentWithMetadata,
    DocumentUploadResponse,
    DocumentOrderStatusUpdateRequest,
)
from app.services.document_service import DocumentService
from app.services.document_search_service import search_documents_semantic
from app.services.embeddings_client import EmbeddingsError
from app.services.document_download_token import verify_download_token
from app.services.unit_normalization_service import unit_normalization_service
from app.services.analyte_normalization_service_db import analyte_normalization_service_db
from app.services.subscription_service import SubscriptionService, QuotaExceededError
from app.api.deps import get_current_user, get_profile_user_id
from app.core.config import settings
from app.db.minio_client import minio_client
from app.db.mongodb import document_metadata_collection

router = APIRouter()

ORDER_TARGET_TYPES = {
    "lab": "Результаты анализа",
    "analysis": "Результаты анализа",
    "instrumental": "Инструментальное исследование",
    "imaging": "Инструментальное исследование",
    "functional": "Функциональная диагностика",
}

FOLLOW_UP_DOCUMENT_TYPES = set(ORDER_TARGET_TYPES.values())
MANUAL_ORDER_STATUSES = {"pending", "completed", "not_required", "incorrect"}

ORDER_KEYWORDS = [
    ("Результаты анализа", None, ["анализ", "кров", "моч", "кал", "гормон", "биохим", "бактериолог", "серолог"]),
    ("Инструментальное исследование", "УЗИ", ["узи", "эхо"]),
    ("Инструментальное исследование", "МРТ", ["мрт", "магнитно"]),
    ("Инструментальное исследование", "КТ", ["кт", "компьютерн"]),
    ("Инструментальное исследование", "Рентген", ["рентген", "флюорограф"]),
    ("Функциональная диагностика", "ЭКГ (электрокардиография)", ["экг", "электрокардиограф"]),
    ("Функциональная диагностика", "ЭЭГ (электроэнцефалография)", ["ээг", "электроэнцефалограф"]),
    ("Функциональная диагностика", "Холтер-мониторирование", ["холтер"]),
    ("Функциональная диагностика", "Спирометрия", ["спирометр"]),
    ("Функциональная диагностика", "ФГДС (фиброгастродуоденоскопия)", ["фгдс", "гастроскоп"]),
    ("Функциональная диагностика", "Колоноскопия", ["колоноскоп"]),
]


def _normalize_text(value: Optional[str]) -> str:
    return (value or "").strip().lower()


def _infer_order_target(order: Dict[str, Any]) -> tuple[Optional[str], Optional[str]]:
    target_type = order.get("target_document_type")
    target_subtype = order.get("target_document_subtype")
    order_type = _normalize_text(order.get("order_type"))
    title = _normalize_text(order.get("title"))

    if not target_type and order_type in ORDER_TARGET_TYPES:
        target_type = ORDER_TARGET_TYPES[order_type]

    for doc_type, subtype, keywords in ORDER_KEYWORDS:
        if any(keyword in title for keyword in keywords):
            target_type = target_type or doc_type
            if target_type == doc_type:
                target_subtype = target_subtype or subtype
            break

    return target_type, target_subtype


def _order_matches_candidate(order: Dict[str, Any], candidate: Dict[str, Any]) -> bool:
    target_type, target_subtype = _infer_order_target(order)
    if not target_type or candidate.get("document_type") != target_type:
        return False

    target_subtype_norm = _normalize_text(target_subtype)
    candidate_subtype_norm = _normalize_text(candidate.get("document_subtype"))
    if (
        target_subtype_norm
        and candidate_subtype_norm
        and target_subtype_norm != candidate_subtype_norm
        and target_subtype_norm not in candidate_subtype_norm
        and candidate_subtype_norm not in target_subtype_norm
    ):
        return False

    target_research_area = _normalize_text(order.get("target_research_area"))
    candidate_research_area = _normalize_text(candidate.get("research_area"))
    if (
        target_research_area
        and candidate_research_area
        and target_research_area != candidate_research_area
        and target_research_area not in candidate_research_area
        and candidate_research_area not in target_research_area
    ):
        return False

    return True


async def _build_orders_summary_map(
    user_id: uuid.UUID,
    documents: List[DocumentModel],
    metadata_by_doc_id: Dict[str, Dict[str, Any]],
    db: AsyncSession,
) -> Dict[str, Dict[str, Any]]:
    source_docs = [
        doc for doc in documents
        if (metadata_by_doc_id.get(str(doc.id), {}).get("orders") or [])
    ]
    if not source_docs:
        return {}

    candidate_query = (
        select(DocumentModel)
        .where(
            DocumentModel.user_id == user_id,
            DocumentModel.document_type.in_(list(FOLLOW_UP_DOCUMENT_TYPES)),
            DocumentModel.processing_status == "completed",
        )
    )
    result = await db.execute(candidate_query)
    candidate_docs = result.scalars().all()
    candidate_ids = [str(doc.id) for doc in candidate_docs if doc.mongodb_metadata_id]

    candidate_metadata_by_doc_id: Dict[str, Dict[str, Any]] = {}
    if candidate_ids:
        cursor = document_metadata_collection.find(
            {"document_id": {"$in": candidate_ids}},
            {
                "document_id": 1,
                "classification.document_subtype": 1,
                "classification.research_area": 1,
            },
        )
        mongo_docs = await cursor.to_list(length=len(candidate_ids))
        for m in mongo_docs:
            classification = m.get("classification", {}) or {}
            candidate_metadata_by_doc_id[m.get("document_id")] = {
                "document_subtype": classification.get("document_subtype"),
                "research_area": classification.get("research_area"),
            }

    candidates = []
    for candidate_doc in candidate_docs:
        candidate_meta = candidate_metadata_by_doc_id.get(str(candidate_doc.id), {})
        candidates.append({
            "id": candidate_doc.id,
            "document_type": candidate_doc.document_type,
            "document_date": candidate_doc.document_date,
            "created_at": candidate_doc.created_at,
            "title": candidate_doc.original_filename,
            "document_subtype": candidate_meta.get("document_subtype"),
            "research_area": candidate_meta.get("research_area"),
        })

    summaries: Dict[str, Dict[str, Any]] = {}
    for source_doc in source_docs:
        source_id = str(source_doc.id)
        source_date = source_doc.document_date
        orders = metadata_by_doc_id.get(source_id, {}).get("orders") or []
        items = []

        for order_index, raw_order in enumerate(orders):
            if not isinstance(raw_order, dict):
                continue

            target_type, target_subtype = _infer_order_target(raw_order)
            title = raw_order.get("title") or target_subtype or target_type or "Назначение"
            matched = None
            manual_status = raw_order.get("manual_status")

            if manual_status not in MANUAL_ORDER_STATUSES:
                for candidate in candidates:
                    if candidate["id"] == source_doc.id:
                        continue

                    candidate_date = candidate.get("document_date")
                    candidate_created = candidate.get("created_at")
                    if source_date:
                        if candidate_date and candidate_date < source_date:
                            continue
                        if not candidate_date and candidate_created and candidate_created.date() < source_date:
                            continue

                    if _order_matches_candidate({**raw_order, "target_document_type": target_type, "target_document_subtype": target_subtype}, candidate):
                        matched = candidate
                        break

            computed_status = "completed" if matched else "pending"
            final_status = manual_status if manual_status in MANUAL_ORDER_STATUSES else computed_status
            status_source = "manual" if manual_status in MANUAL_ORDER_STATUSES else "auto"

            item = {
                "order_index": order_index,
                "title": title,
                "order_type": raw_order.get("order_type"),
                "target_document_type": target_type,
                "target_document_subtype": target_subtype,
                "target_research_area": raw_order.get("target_research_area"),
                "status": final_status,
                "status_source": status_source,
                "is_active": final_status == "pending",
                "matched_document_id": matched["id"] if matched else None,
                "matched_document_date": matched.get("document_date") if matched else None,
                "matched_document_title": matched.get("title") if matched else None,
            }
            items.append(item)

        if items:
            completed = sum(1 for item in items if item["status"] == "completed")
            pending = sum(1 for item in items if item["status"] == "pending")
            dismissed = sum(1 for item in items if item["status"] in {"not_required", "incorrect"})
            summaries[source_id] = {
                "total": len(items),
                "completed": completed,
                "pending": pending,
                "dismissed": dismissed,
                "items": items,
            }

    return summaries

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
        await SubscriptionService.assert_can_upload(profile_user_id, db)
    except QuotaExceededError as e:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "code": "quota_exceeded",
                "used": e.used,
                "limit": e.limit,
                "tier": e.tier,
                "reset_at": e.reset_at.isoformat(),
            },
        )

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
                "extracted_data.summary": 1,
                "extracted_data.orders": 1
            })
            mongo_docs = await cursor.to_list(length=len(doc_ids))
            
            for m in mongo_docs:
                doc_id = m.get("document_id")
                extracted_data = m.get("extracted_data", {}) or {}
                metadata_by_doc_id[doc_id] = {
                    "specialties": m.get("classification", {}).get("specialties"),
                    "document_subtype": m.get("classification", {}).get("document_subtype"),
                    "research_area": m.get("classification", {}).get("research_area"),
                    "summary": extracted_data.get("summary"),
                    "orders": extracted_data.get("orders") or [],
                }

        orders_summary_by_doc_id = await _build_orders_summary_map(
            user_id=profile_user_id,
            documents=documents,
            metadata_by_doc_id=metadata_by_doc_id,
            db=db,
        )
        
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
            doc_dict["orders_summary"] = orders_summary_by_doc_id.get(str(doc.id))
            
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


class DocumentSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    limit: int = Field(20, ge=1, le=100)


@router.post("/search")
async def search_documents(
    body: DocumentSearchRequest,
    current_user: User = Depends(get_current_user),
    profile_user_id: uuid.UUID = Depends(get_profile_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Semantic search over the user's document summaries.

    Uses multilingual-e5-base embeddings + pgvector cosine similarity.
    Returns documents ranked by relevance (higher score = better match).
    """
    try:
        hits = await search_documents_semantic(
            user_id=profile_user_id,
            query=body.query,
            db=db,
            limit=body.limit,
        )
    except EmbeddingsError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Сервис поиска временно недоступен: {e}",
        )
    return {"results": hits, "total": len(hits)}


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
        "summary": None,
        "orders_summary": None
    }
    metadata_by_doc_id: Dict[str, Dict[str, Any]] = {}
    
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
            metadata_by_doc_id[str(document.id)] = {
                "specialties": specialties,
                "document_subtype": classification.get("document_subtype"),
                "research_area": classification.get("research_area"),
                "summary": extracted_data.get("summary"),
                "orders": extracted_data.get("orders") or [],
            }

    orders_summary_by_doc_id = await _build_orders_summary_map(
        user_id=profile_user_id,
        documents=[document],
        metadata_by_doc_id=metadata_by_doc_id,
        db=db,
    )
    doc_dict["orders_summary"] = orders_summary_by_doc_id.get(str(document.id))
    
    return DocumentWithMetadata(**doc_dict)


@router.get("/{document_id}/content", response_model=DocumentContentResponse)
async def get_document_content(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    profile_user_id: uuid.UUID = Depends(get_profile_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Return rich extracted content for a single document.

    This is intentionally separate from list/get metadata endpoints because
    full_text can be large.
    """
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

    mongo_doc = await document_metadata_collection.find_one(
        {"document_id": str(document_id)},
        {
            "extracted_data.summary": 1,
            "extracted_data.full_text": 1,
            "extracted_data.full_text_source": 1,
            "extracted_data.tables": 1,
            "extracted_data.lab_results": 1,
        },
    )
    extracted_data = (mongo_doc or {}).get("extracted_data", {}) or {}

    return DocumentContentResponse(
        document_id=document_id,
        summary=extracted_data.get("summary"),
        full_text=extracted_data.get("full_text"),
        full_text_source=extracted_data.get("full_text_source"),
        tables=extracted_data.get("tables") or [],
        lab_results=extracted_data.get("lab_results") or [],
    )


@router.patch("/{document_id}/orders/{order_index}/status")
async def update_document_order_status(
    document_id: uuid.UUID,
    order_index: int,
    body: DocumentOrderStatusUpdateRequest,
    current_user: User = Depends(get_current_user),
    profile_user_id: uuid.UUID = Depends(get_profile_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Manually override status for an extracted referral/order.

    Manual status has priority over automatic matching. Any status except
    "pending" removes the order from active patient reminders.
    """

    if order_index < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Некорректный номер назначения",
        )

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

    mongo_doc = await document_metadata_collection.find_one(
        {"document_id": str(document_id)},
        {"extracted_data.orders": 1},
    )
    orders = (mongo_doc or {}).get("extracted_data", {}).get("orders") or []

    if order_index >= len(orders):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Назначение не найдено",
        )

    now = datetime.utcnow()
    update_result = await document_metadata_collection.update_one(
        {"document_id": str(document_id)},
        {
            "$set": {
                f"extracted_data.orders.{order_index}.manual_status": body.status,
                f"extracted_data.orders.{order_index}.manual_status_updated_at": now,
                "updated_at": now,
            }
        },
    )

    if update_result.matched_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Метаданные документа не найдены",
        )

    return {
        "document_id": str(document_id),
        "order_index": order_index,
        "status": body.status,
    }

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

_DOWNLOAD_CONTENT_TYPES = {
    "pdf": "application/pdf",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


@router.get("/{document_id}/download")
async def download_document_with_token(
    document_id: uuid.UUID,
    token: str = Query(..., description="Short-lived signed download token"),
    db: AsyncSession = Depends(get_db),
):
    """Stream an original document by short-lived token.

    Token-authenticated alternative to `/{document_id}/file` — used by the MCP
    `get_document_original` tool so external clients (LLM sandboxes, curl) can
    fetch the file without a session bearer.
    """
    user_id = verify_download_token(token, str(document_id))
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired download token",
        )

    try:
        owner_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token subject",
        )

    document = await DocumentService.get_document_by_id(
        document_id=document_id,
        user_id=owner_uuid,
        db=db,
    )
    if not document or not document.file_url:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Документ не найден")

    prefix = f"s3://{settings.MINIO_BUCKET}/"
    if not document.file_url.startswith(prefix):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Файл недоступен")
    object_name = document.file_url[len(prefix):]

    response = minio_client.get_object(settings.MINIO_BUCKET, object_name)

    def iter_file():
        try:
            for chunk in response.stream(64 * 1024):
                yield chunk
        finally:
            response.close()
            response.release_conn()

    content_type = _DOWNLOAD_CONTENT_TYPES.get(
        (document.file_type or "").lower(), "application/octet-stream"
    )
    headers = {
        "Content-Disposition": (
            f"attachment; filename*=UTF-8''{quote(document.original_filename or 'document')}"
        ),
    }
    if document.file_size:
        headers["Content-Length"] = str(document.file_size)

    return StreamingResponse(iter_file(), media_type=content_type, headers=headers)


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

    if not analyte_normalization_service_db.is_loaded:
        try:
            await analyte_normalization_service_db.load_from_db(db, force=True)
        except Exception as e:
            logger.error(f"❌ Не удалось загрузить справочник анализов: {e}")

    enriched_results = [
        {
            **result,
            "canonical_name": analyte_normalization_service_db.get_canonical_name(
                result.get("test_name", ""),
                result.get("unit"),
            ),
        }
        for result in (lab_results or [])
    ]

    return {
        "document_id": str(document_id),
        "lab_results": enriched_results,
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
