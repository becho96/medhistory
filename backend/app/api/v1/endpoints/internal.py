"""
Internal endpoints for service-to-service communication.
Used by db-viewer for cache invalidation after analyte mapping changes.
"""
from fastapi import APIRouter

from app.services.analyte_normalization_service_db import analyte_normalization_service_db

router = APIRouter()


@router.post("/analytes/reload")
async def reload_analytes_cache():
    """
    Invalidate the analyte normalization cache.
    Called by db-viewer after adding new synonym mappings.
    Next request to /documents/labs/analytes will trigger a fresh DB load.
    """
    analyte_normalization_service_db.invalidate_cache()
    return {"status": "ok", "message": "Cache invalidated"}
