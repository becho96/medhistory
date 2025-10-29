import uuid
import hashlib
from datetime import datetime
from io import BytesIO
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from fastapi import UploadFile
from dateutil import parser as date_parser

from app.models.document import Document
from app.db.minio_client import minio_client
from app.db.mongodb import document_metadata_collection
from app.services.ai_service import ai_service
from app.core.config import settings

class DocumentService:
    
    @staticmethod
    def _calculate_file_hash(file_content: bytes) -> str:
        """Calculate SHA256 hash of file content"""
        return hashlib.sha256(file_content).hexdigest()
    
    @staticmethod
    async def _check_duplicate(
        file_hash: str,
        user_id: uuid.UUID,
        db: AsyncSession
    ) -> Optional[Document]:
        """Check if file with same hash already exists for this user"""
        query = select(Document).where(
            and_(
                Document.user_id == user_id,
                Document.file_hash == file_hash
            )
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    @staticmethod
    async def upload_document(
        file: UploadFile,
        user_id: uuid.UUID,
        db: AsyncSession
    ) -> Document:
        """Upload document and create database record"""
        
        # Read file content
        file_content = await file.read()
        file_size = len(file_content)
        
        # Validate file
        if file_size > settings.MAX_FILE_SIZE:
            raise ValueError(f"File size exceeds maximum allowed size of {settings.MAX_FILE_SIZE} bytes")
        
        # Get file extension
        file_ext = file.filename.split('.')[-1].lower()
        if f".{file_ext}" not in settings.ALLOWED_EXTENSIONS:
            raise ValueError(f"File type .{file_ext} is not allowed")
        
        # Calculate file hash
        file_hash = DocumentService._calculate_file_hash(file_content)
        
        # Check for duplicates
        duplicate = await DocumentService._check_duplicate(file_hash, user_id, db)
        if duplicate:
            raise ValueError(
                f"Файл '{file.filename}' уже был загружен ранее "
                f"({duplicate.original_filename}, {duplicate.created_at.strftime('%d.%m.%Y %H:%M')})"
            )
        
        # Generate unique file ID
        file_id = str(uuid.uuid4())
        object_name = f"{user_id}/{file_id}.{file_ext}"
        
        # Upload to MinIO
        minio_client.put_object(
            bucket_name=settings.MINIO_BUCKET,
            object_name=object_name,
            data=BytesIO(file_content),
            length=file_size,
            content_type=file.content_type
        )
        
        file_url = f"s3://{settings.MINIO_BUCKET}/{object_name}"
        
        # Create database record
        document = Document(
            user_id=user_id,
            original_filename=file.filename,
            file_size=file_size,
            file_type=file_ext,
            file_url=file_url,
            file_hash=file_hash,
            processing_status="pending"
        )
        
        db.add(document)
        await db.commit()
        await db.refresh(document)
        
        # Trigger async AI processing (don't wait for it)
        # In production, this would be done via a task queue (Celery, RQ)
        # For MVP, we'll process it synchronously but mark as processing
        try:
            await DocumentService._process_document_ai(document, file_content, file_ext, db)
        except Exception as e:
            print(f"❌ AI processing failed for document {document.id}: {str(e)}")
            document.processing_status = "failed"
            await db.commit()
        
        return document
    
    @staticmethod
    async def _process_document_ai(
        document: Document,
        file_content: bytes,
        file_ext: str,
        db: AsyncSession
    ):
        """Process document with AI and update metadata"""
        
        # Update status to processing
        document.processing_status = "processing"
        await db.commit()
        
        # Analyze document with AI
        metadata = await ai_service.analyze_document(
            file_content,
            file_ext,
            document.original_filename
        )
        
        # Update PostgreSQL record (minimal fields only)
        document.document_type = metadata.document_type
        document.document_date = metadata.document_date
        document.patient_name = metadata.patient_name
        document.medical_facility = metadata.medical_facility
        document.processing_status = "completed"
        
        # Save extended metadata to MongoDB (classification + extracted_data)
        mongo_doc = {
            "document_id": str(document.id),
            "user_id": str(document.user_id),
            "classification": {
                "document_subtype": metadata.document_subtype,
                "research_area": metadata.research_area,
                "specialties": metadata.specialties,  # Array or null
                "document_language": metadata.document_language,
                "confidence": metadata.confidence
            },
            "extracted_data": {
                "summary": metadata.summary,
            },
            "ai_response": {
                "model": settings.OPENROUTER_MODEL,
                "confidence": metadata.confidence,
            },
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        result = await document_metadata_collection.insert_one(mongo_doc)
        document.mongodb_metadata_id = str(result.inserted_id)
        
        await db.commit()
        await db.refresh(document)
        
        # If document is classified as "Результаты анализа", automatically extract lab results
        if document.document_type == "Результаты анализа":
            try:
                print(f"🧪 Document classified as lab results, starting automatic lab extraction for {document.id}")
                from app.services.lab_analysis_service import LabAnalysisService
                
                lab_result = await LabAnalysisService.analyze_labs_for_document(
                    document=document,
                    file_bytes=file_content,
                    file_ext=file_ext,
                    db=db,
                )
                print(f"✅ Automatic lab extraction completed for {document.id}: {lab_result.get('lab_results_count', 0)} results found")
            except Exception as e:
                print(f"⚠️ Warning: Automatic lab extraction failed for {document.id}: {str(e)}")
                # Don't fail the entire document processing if lab extraction fails
                # The document is still successfully classified
    
    @staticmethod
    async def get_documents(
        user_id: uuid.UUID,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        document_type: Optional[list[str]] = None,
        patient_name: Optional[list[str]] = None,
        medical_facility: Optional[list[str]] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        created_from: Optional[str] = None,
        created_to: Optional[str] = None,
        sort_by: str = "document_date",
        # MongoDB filters
        specialties: Optional[list[str]] = None,
        document_subtype: Optional[list[str]] = None,
        research_area: Optional[list[str]] = None,
    ) -> list[Document]:
        """Get user documents with filters
        
        Supports filtering by both PostgreSQL and MongoDB fields.
        MongoDB filters (specialties, document_subtype, research_area) are applied first
        to get matching document IDs, then PostgreSQL filters are applied.
        """
        
        # First, apply MongoDB filters if any
        mongodb_document_ids = None
        if specialties or document_subtype or research_area:
            mongodb_document_ids = await DocumentService.filter_documents_by_mongodb_fields(
                user_id=user_id,
                specialties=specialties,
                document_subtype=document_subtype,
                research_area=research_area
            )
            
            # If MongoDB filters returned no results, return empty list
            if not mongodb_document_ids:
                return []
            
            # Convert to UUIDs
            mongodb_document_ids = [uuid.UUID(doc_id) for doc_id in mongodb_document_ids]
        
        # Build PostgreSQL query
        query = select(Document).where(Document.user_id == user_id)
        
        # If we have MongoDB filters, restrict to those document IDs
        if mongodb_document_ids is not None:
            query = query.where(Document.id.in_(mongodb_document_ids))
        
        if document_type:
            # Support multiple document types
            query = query.where(Document.document_type.in_(document_type))

        if patient_name:
            # Support multiple patient names
            query = query.where(Document.patient_name.in_(patient_name))

        if medical_facility:
            # Support multiple medical facilities
            query = query.where(Document.medical_facility.in_(medical_facility))
        
        if date_from:
            # Parse date string to datetime if it's a string
            date_from_dt = date_parser.parse(date_from) if isinstance(date_from, str) else date_from
            query = query.where(Document.document_date >= date_from_dt)
        
        if date_to:
            # Parse date string to datetime if it's a string
            date_to_dt = date_parser.parse(date_to) if isinstance(date_to, str) else date_to
            query = query.where(Document.document_date <= date_to_dt)
        
        if created_from:
            # Parse date string to datetime if it's a string
            created_from_dt = date_parser.parse(created_from) if isinstance(created_from, str) else created_from
            query = query.where(Document.created_at >= created_from_dt)
        
        if created_to:
            # Parse date string to datetime if it's a string
            created_to_dt = date_parser.parse(created_to) if isinstance(created_to, str) else created_to
            query = query.where(Document.created_at <= created_to_dt)
        
        # Sort by specified field
        if sort_by == "created_at":
            query = query.order_by(Document.created_at.desc()).offset(skip).limit(limit)
        else:
            query = query.order_by(Document.document_date.desc()).offset(skip).limit(limit)
        
        result = await db.execute(query)
        documents = result.scalars().all()
        
        return list(documents)
    
    @staticmethod
    async def get_documents_count(
        user_id: uuid.UUID,
        db: AsyncSession,
        document_type: Optional[list[str]] = None,
        patient_name: Optional[list[str]] = None,
        medical_facility: Optional[list[str]] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        created_from: Optional[str] = None,
        created_to: Optional[str] = None,
        # MongoDB filters
        specialties: Optional[list[str]] = None,
        document_subtype: Optional[list[str]] = None,
        research_area: Optional[list[str]] = None,
    ) -> int:
        """Get total count of user documents with filters
        
        Uses the same filtering logic as get_documents but returns count instead.
        """
        from sqlalchemy import func
        
        # First, apply MongoDB filters if any
        mongodb_document_ids = None
        if specialties or document_subtype or research_area:
            mongodb_document_ids = await DocumentService.filter_documents_by_mongodb_fields(
                user_id=user_id,
                specialties=specialties,
                document_subtype=document_subtype,
                research_area=research_area
            )
            
            # If MongoDB filters returned no results, return 0
            if not mongodb_document_ids:
                return 0
            
            # Convert to UUIDs
            mongodb_document_ids = [uuid.UUID(doc_id) for doc_id in mongodb_document_ids]
        
        # Build PostgreSQL query for count
        query = select(func.count(Document.id)).where(Document.user_id == user_id)
        
        # If we have MongoDB filters, restrict to those document IDs
        if mongodb_document_ids is not None:
            query = query.where(Document.id.in_(mongodb_document_ids))
        
        if document_type:
            query = query.where(Document.document_type.in_(document_type))

        if patient_name:
            query = query.where(Document.patient_name.in_(patient_name))

        if medical_facility:
            query = query.where(Document.medical_facility.in_(medical_facility))
        
        if date_from:
            date_from_dt = date_parser.parse(date_from) if isinstance(date_from, str) else date_from
            query = query.where(Document.document_date >= date_from_dt)
        
        if date_to:
            date_to_dt = date_parser.parse(date_to) if isinstance(date_to, str) else date_to
            query = query.where(Document.document_date <= date_to_dt)
        
        if created_from:
            created_from_dt = date_parser.parse(created_from) if isinstance(created_from, str) else created_from
            query = query.where(Document.created_at >= created_from_dt)
        
        if created_to:
            created_to_dt = date_parser.parse(created_to) if isinstance(created_to, str) else created_to
            query = query.where(Document.created_at <= created_to_dt)
        
        result = await db.execute(query)
        count = result.scalar_one()
        
        return count
    
    @staticmethod
    async def get_document_by_id(
        document_id: uuid.UUID,
        user_id: uuid.UUID,
        db: AsyncSession
    ) -> Optional[Document]:
        """Get document by ID"""
        
        query = select(Document).where(
            and_(
                Document.id == document_id,
                Document.user_id == user_id
            )
        )
        
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_distinct_field_values(
        user_id: uuid.UUID,
        db: AsyncSession,
        field: str,
        q: Optional[str] = None,
        limit: int = 20
    ) -> list[str]:
        """Return distinct values for a given document field for the user.

        Supports prefix/substring search via ILIKE when q is provided.
        
        Note: 'specialty' field is no longer supported as it's moved to MongoDB.
        """
        allowed_fields = {
            "document_type",
            "patient_name",
            "medical_facility",
        }
        if field not in allowed_fields:
            return []

        column = getattr(Document, field)

        query = select(column).where(Document.user_id == user_id)

        if q:
            query = query.where(column.ilike(f"%{q}%"))

        # Exclude NULL/empty values
        query = query.where(column.is_not(None)).where(column != "")

        query = query.distinct().order_by(column).limit(limit)

        result = await db.execute(query)
        values = [v for v, in result.all()]
        return values
    
    @staticmethod
    async def get_distinct_mongodb_field_values(
        user_id: uuid.UUID,
        field: str,
        q: Optional[str] = None,
        limit: int = 50
    ) -> list[str]:
        """Return distinct values for MongoDB classification fields.
        
        Supports:
        - specialties (array field - unwinds and returns unique values)
        - document_subtype
        - research_area
        """
        allowed_fields = {
            "specialties": "classification.specialties",
            "document_subtype": "classification.document_subtype",
            "research_area": "classification.research_area",
        }
        
        if field not in allowed_fields:
            return []
        
        mongo_field = allowed_fields[field]
        
        # For array fields (specialties), we need to unwind
        if field == "specialties":
            pipeline = [
                {"$match": {"user_id": str(user_id)}},
                {"$unwind": f"${mongo_field}"},
                {"$group": {"_id": f"${mongo_field}"}},
                {"$match": {"_id": {"$ne": None, "$ne": ""}}},
            ]
            
            if q:
                pipeline.append({
                    "$match": {"_id": {"$regex": q, "$options": "i"}}
                })
            
            pipeline.extend([
                {"$sort": {"_id": 1}},
                {"$limit": limit}
            ])
        else:
            # For regular fields
            pipeline = [
                {"$match": {"user_id": str(user_id)}},
                {"$group": {"_id": f"${mongo_field}"}},
                {"$match": {"_id": {"$ne": None, "$ne": ""}}},
            ]
            
            if q:
                pipeline.append({
                    "$match": {"_id": {"$regex": q, "$options": "i"}}
                })
            
            pipeline.extend([
                {"$sort": {"_id": 1}},
                {"$limit": limit}
            ])
        
        cursor = document_metadata_collection.aggregate(pipeline)
        values = []
        async for doc in cursor:
            if doc.get("_id"):
                values.append(doc["_id"])
        
        return values
    
    @staticmethod
    async def filter_documents_by_mongodb_fields(
        user_id: uuid.UUID,
        specialties: Optional[list[str]] = None,
        document_subtype: Optional[list[str]] = None,
        research_area: Optional[list[str]] = None,
    ) -> list[str]:
        """Filter documents by MongoDB classification fields.
        
        Returns list of document_ids that match the criteria.
        """
        match_conditions = {"user_id": str(user_id)}
        
        if specialties:
            # Match any of the provided specialties
            match_conditions["classification.specialties"] = {"$in": specialties}
        
        if document_subtype:
            # Match any of the provided subtypes
            match_conditions["classification.document_subtype"] = {"$in": document_subtype}
        
        if research_area:
            # Match any of the provided research areas
            match_conditions["classification.research_area"] = {"$in": research_area}
        
        # Query MongoDB for matching documents
        cursor = document_metadata_collection.find(
            match_conditions,
            {"document_id": 1}
        )
        
        document_ids = []
        async for doc in cursor:
            if doc.get("document_id"):
                document_ids.append(doc["document_id"])
        
        return document_ids
    
    @staticmethod
    async def delete_document(
        document_id: uuid.UUID,
        user_id: uuid.UUID,
        db: AsyncSession
    ) -> bool:
        """Delete document and all associated data"""
        
        document = await DocumentService.get_document_by_id(document_id, user_id, db)
        
        if not document:
            return False
        
        # Delete from MinIO
        try:
            object_name = document.file_url.replace(f"s3://{settings.MINIO_BUCKET}/", "")
            minio_client.remove_object(settings.MINIO_BUCKET, object_name)
        except Exception as e:
            print(f"Warning: Failed to delete file from MinIO: {e}")
        
        # Delete from MongoDB
        if document.mongodb_metadata_id:
            try:
                await document_metadata_collection.delete_one({
                    "document_id": str(document_id)
                })
            except Exception as e:
                print(f"Warning: Failed to delete from MongoDB: {e}")
        
        # Delete from PostgreSQL
        await db.delete(document)
        await db.commit()
        
        return True
    
    @staticmethod
    def get_file_from_minio(file_url: str) -> bytes:
        """Get file content from MinIO"""
        
        object_name = file_url.replace(f"s3://{settings.MINIO_BUCKET}/", "")
        
        response = minio_client.get_object(settings.MINIO_BUCKET, object_name)
        file_content = response.read()
        response.close()
        response.release_conn()
        
        return file_content

