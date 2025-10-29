import uuid
from datetime import datetime
from typing import Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.db.mongodb import document_metadata_collection
from app.services.ai_service import ai_service
from app.core.config import settings
from app.db.minio_client import minio_client


class LabAnalysisService:
    @staticmethod
    async def analyze_labs_for_document(
        document: Document,
        file_bytes: bytes,
        file_ext: str,
        db: AsyncSession,
    ) -> dict:
        """Run LLM extraction of lab results and store them in MongoDB.

        Returns a summary dict with counts.
        """

        results = await ai_service.extract_lab_results(
            file_bytes,
            file_ext,
            document.original_filename,
        )

        # Upsert into MongoDB under extracted_data.lab_results
        now = datetime.utcnow()

        update_doc = {
            "$set": {
                "document_id": str(document.id),
                "user_id": str(document.user_id),
                "updated_at": now,
                "ai_response_labs.model": settings.OPENROUTER_MODEL,
                "ai_response_labs.count": len(results.get("lab_results", []) or []),
                "ai_response_labs.updated_at": now,
            },
            "$setOnInsert": {
                "created_at": now,
            },
            "$push": {
                # Keep history of lab extraction runs
                "extraction_history": {
                    "type": "labs",
                    "count": len(results.get("lab_results", []) or []),
                    "timestamp": now,
                }
            },
        }

        # Store standardized lab results under extracted_data.lab_results
        update_doc["$set"]["extracted_data.lab_results"] = results.get("lab_results", [])

        await document_metadata_collection.update_one(
            {"document_id": str(document.id)}, update_doc, upsert=True
        )

        return {
            "lab_results_count": len(results.get("lab_results", []) or []),
        }


