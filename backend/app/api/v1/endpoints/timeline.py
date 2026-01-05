from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import date
import uuid

from app.db.postgres import get_db
from app.models.user import User
from app.schemas.document import TimelineResponse, TimelineEvent
from app.services.document_service import DocumentService
from app.db.mongodb import document_metadata_collection
from app.api.deps import get_current_user, get_profile_user_id

router = APIRouter()

@router.get("/", response_model=TimelineResponse)
async def get_timeline(
    document_type: Optional[str] = None,
    specialty: Optional[str] = None,
    patient_name: Optional[str] = None,
    medical_facility: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    profile_user_id: uuid.UUID = Depends(get_profile_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Get timeline events for user documents
    
    Specialty filtering is done via MongoDB integration in DocumentService.
    """
    
    # Get documents with filters
    # Convert string filters to lists for DocumentService compatibility
    documents = await DocumentService.get_documents(
        user_id=profile_user_id,
        db=db,
        document_type=[document_type] if document_type else None,
        patient_name=[patient_name] if patient_name else None,
        medical_facility=[medical_facility] if medical_facility else None,
        specialties=[specialty] if specialty else None,
        date_from=date_from,
        date_to=date_to,
        limit=1000  # Get more documents for timeline
    )
    
    # Convert to timeline events
    events = []
    date_range = None
    
    if documents:
        # Preload summaries, specialties and document_subtype from MongoDB for all documents in one query
        doc_ids = [str(doc.id) for doc in documents if doc.mongodb_metadata_id]
        summaries_by_doc_id = {}
        specialties_by_doc_id = {}
        document_subtype_by_doc_id = {}
        if doc_ids:
            cursor = document_metadata_collection.find({
                "document_id": {"$in": doc_ids}
            }, {
                "document_id": 1,
                "extracted_data.summary": 1,
                "classification.specialties": 1,
                "classification.document_subtype": 1
            })
            mongo_docs = await cursor.to_list(length=len(doc_ids))
            for m in mongo_docs:
                doc_id = m.get("document_id")
                if m.get("extracted_data"):
                    summaries_by_doc_id[doc_id] = m["extracted_data"].get("summary")
                if m.get("classification"):
                    specialties = m["classification"].get("specialties")
                    if specialties:
                        # Join specialties array into a string for display
                        specialties_by_doc_id[doc_id] = ", ".join(specialties)
                    document_subtype = m["classification"].get("document_subtype")
                    if document_subtype:
                        document_subtype_by_doc_id[doc_id] = document_subtype
        
        # Define color mapping for document types (using new 5 types)
        color_map = {
            'прием врача': '#10B981',
            'результаты анализа': '#EF4444',
            'инструментальное исследование': '#3B82F6',
            'функциональная диагностика': '#8B5CF6',
            'другое': '#6B7280'
        }
        
        # Define icon mapping
        icon_map = {
            'прием врача': 'doctor',
            'результаты анализа': 'test-tube',
            'инструментальное исследование': 'scan',
            'функциональная диагностика': 'activity',
            'другое': 'document'
        }
        
        for doc in documents:
            doc_type_lower = (doc.document_type or '').lower()
            
            # Get specialty and document_subtype from MongoDB for this document
            specialty_str = specialties_by_doc_id.get(str(doc.id))
            document_subtype_str = document_subtype_by_doc_id.get(str(doc.id))
            
            # Build title with specialty or document_subtype
            title = f"{doc.document_type or 'Документ'}"
            if specialty_str:
                title += f" - {specialty_str}"
            elif document_subtype_str:
                title += f" - {document_subtype_str}"
            
            event = TimelineEvent(
                document_id=doc.id,
                date=doc.document_date,
                document_type=doc.document_type,
                document_subtype=document_subtype_str,  # From MongoDB, can be None
                specialty=specialty_str,  # From MongoDB, can be None
                title=title,
                medical_facility=doc.medical_facility,
                icon=icon_map.get(doc_type_lower, 'document'),
                color=color_map.get(doc_type_lower, '#6B7280'),
                file_url=doc.file_url,
                original_filename=doc.original_filename,
                summary=summaries_by_doc_id.get(str(doc.id))
            )
            events.append(event)
        
        # Calculate date range
        dates = [doc.document_date for doc in documents if doc.document_date]
        if dates:
            date_range = {
                "start": min(dates).isoformat(),
                "end": max(dates).isoformat()
            }
    
    return TimelineResponse(
        total_count=len(events),
        date_range=date_range,
        events=events
    )

@router.get("/stats")
async def get_timeline_stats(
    current_user: User = Depends(get_current_user),
    profile_user_id: uuid.UUID = Depends(get_profile_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Get timeline statistics
    
    Note: Specialty statistics are now computed from MongoDB since specialties
    are stored as arrays in the classification object.
    """
    
    documents = await DocumentService.get_documents(
        user_id=profile_user_id,
        db=db,
        limit=10000
    )
    
    # Calculate statistics
    total_documents = len(documents)
    
    # Count by type and facility (from PostgreSQL)
    by_type = {}
    by_facility = {}
    
    for doc in documents:
        if doc.document_type:
            by_type[doc.document_type] = by_type.get(doc.document_type, 0) + 1
        
        if doc.medical_facility:
            by_facility[doc.medical_facility] = by_facility.get(doc.medical_facility, 0) + 1
    
    # Count by specialty (from MongoDB)
    by_specialty = {}
    cursor = document_metadata_collection.find({
        "user_id": str(profile_user_id),
        "classification.specialties": {"$exists": True, "$ne": None}
    }, {
        "classification.specialties": 1
    })
    
    async for mongo_doc in cursor:
        specialties = mongo_doc.get("classification", {}).get("specialties", [])
        if specialties:
            for specialty in specialties:
                by_specialty[specialty] = by_specialty.get(specialty, 0) + 1
    
    return {
        "total_documents": total_documents,
        "by_type": by_type,
        "by_specialty": by_specialty,
        "by_facility": by_facility
    }

@router.get("/suggestions")
async def get_suggestions(
    field: str = Query(..., description="Field to suggest: document_type, patient_name, medical_facility"),
    q: Optional[str] = Query(None, description="Search substring for suggestions"),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    profile_user_id: uuid.UUID = Depends(get_profile_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Get distinct value suggestions for autocomplete filters.
    
    Note: 'specialty' field is no longer supported as it's moved to MongoDB.
    For specialty suggestions, use a separate MongoDB aggregation endpoint.
    """
    values = await DocumentService.get_distinct_field_values(
        user_id=profile_user_id,
        db=db,
        field=field,
        q=q,
        limit=limit,
    )
    return {"values": values}

