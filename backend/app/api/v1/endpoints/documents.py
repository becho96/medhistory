from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from io import BytesIO
import uuid
from urllib.parse import quote

from app.db.postgres import get_db
from app.models.user import User
from app.schemas.document import (
    Document as DocumentSchema,
    DocumentWithMetadata,
    DocumentUploadResponse
)
from app.services.document_service import DocumentService
from app.api.deps import get_current_user
from app.db.mongodb import document_metadata_collection

router = APIRouter()

@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Upload a new document"""
    
    try:
        document = await DocumentService.upload_document(
            file=file,
            user_id=current_user.id,
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
        user_id=current_user.id,
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
    db: AsyncSession = Depends(get_db)
):
    """Get total count of user documents with optional filters"""
    
    count = await DocumentService.get_documents_count(
        user_id=current_user.id,
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
    db: AsyncSession = Depends(get_db)
):
    """Get document by ID with MongoDB metadata"""
    
    document = await DocumentService.get_document_by_id(
        document_id=document_id,
        user_id=current_user.id,
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
    db: AsyncSession = Depends(get_db)
):
    """Download document file"""
    
    document = await DocumentService.get_document_by_id(
        document_id=document_id,
        user_id=current_user.id,
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
    db: AsyncSession = Depends(get_db)
):
    """Delete document"""
    
    success = await DocumentService.delete_document(
        document_id=document_id,
        user_id=current_user.id,
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
    db: AsyncSession = Depends(get_db),
):
    """Return extracted lab results for a document from MongoDB."""

    document = await DocumentService.get_document_by_id(
        document_id=document_id,
        user_id=current_user.id,
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
    db: AsyncSession = Depends(get_db),
):
    """Return quick summary whether labs exist and how many."""

    document = await DocumentService.get_document_by_id(
        document_id=document_id,
        user_id=current_user.id,
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
    db: AsyncSession = Depends(get_db),
):
    """Return distinct analyte names found across user's documents (from MongoDB)."""
    pipeline = [
        {"$match": {"user_id": str(current_user.id)}},
        {"$project": {"extracted_data.lab_results": 1}},
        {"$unwind": "$extracted_data.lab_results"},
        {"$group": {"_id": {"$toLower": "$extracted_data.lab_results.test_name"}, "name": {"$first": "$extracted_data.lab_results.test_name"}, "count": {"$sum": 1}}},
        {"$sort": {"name": 1}},
    ]
    cursor = document_metadata_collection.aggregate(pipeline)
    items = []
    async for doc in cursor:
        if doc.get("name"):
            items.append({"name": doc["name"], "count": doc.get("count", 0)})
    return {"analytes": items}


@router.get("/labs/timeseries")
async def get_lab_timeseries(
    analyte: str = Query(..., description="Название анализа, например: гемоглобин"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return time series for a given analyte across user's documents.

    Each point: { date, value, unit, document_id, reference_range, flag }
    """
    pipeline = [
        {"$match": {"user_id": str(current_user.id)}},
        {"$project": {"document_id": 1, "extracted_data.lab_results": 1}},
        {"$unwind": "$extracted_data.lab_results"},
        {"$match": {"extracted_data.lab_results.test_name": {"$regex": f"^{analyte}$", "$options": "i"}}},
    ]

    cursor = document_metadata_collection.aggregate(pipeline)
    points = []
    doc_ids = set()
    async for doc in cursor:
        lr = doc.get("extracted_data", {}).get("lab_results", {})
        if not isinstance(lr, dict):
            continue
        doc_id = doc.get("document_id")
        if doc_id:
            doc_ids.add(doc_id)
        points.append({
            "document_id": doc_id,
            "value": lr.get("value"),
            "unit": lr.get("unit"),
            "reference_range": lr.get("reference_range"),
            "flag": lr.get("flag"),
        })

    # Fetch dates for documents from Postgres
    if doc_ids:
        import uuid as _uuid
        from sqlalchemy import select
        from app.models.document import Document as DocumentModel
        q = select(DocumentModel.id, DocumentModel.document_date).where(DocumentModel.id.in_([_uuid.UUID(x) for x in doc_ids]))
        result = await db.execute(q)
        id_to_date = {str(r[0]): r[1] for r in result.all()}
        for p in points:
            p["date"] = id_to_date.get(p["document_id"])  # may be None

    # Keep only points with a numeric-like value
    def try_float(v):
        try:
            return float(str(v).replace(',', '.'))
        except Exception:
            return None
    series = [
        {
            **p,
            "value_num": try_float(p.get("value")),
        }
        for p in points
    ]
    series = [p for p in series if p["value_num"] is not None]

    # Sort by date if present
    series.sort(key=lambda x: (x.get("date") is None, x.get("date") or ""))

    return {"analyte": analyte, "points": series}


@router.get("/filters/values")
async def get_filter_values(
    field: str = Query(..., description="Field name: document_type, patient_name, medical_facility, specialties, document_subtype, research_area"),
    q: Optional[str] = Query(None, description="Search query to filter values"),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
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
            user_id=current_user.id,
            db=db,
            field=field,
            q=q,
            limit=limit
        )
        return {"field": field, "values": values}
    
    elif field in mongodb_fields:
        values = await DocumentService.get_distinct_mongodb_field_values(
            user_id=current_user.id,
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

