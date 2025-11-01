from fastapi import APIRouter

from app.api.v1.endpoints import auth, documents, timeline, reports, interpretations, metrics

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(documents.router, prefix="/documents", tags=["Documents"])
api_router.include_router(timeline.router, prefix="/timeline", tags=["Timeline"])
api_router.include_router(reports.router, prefix="/reports", tags=["Reports"])
api_router.include_router(interpretations.router, prefix="/interpretations", tags=["Interpretations"])
api_router.include_router(metrics.router, prefix="/metrics", tags=["Metrics"])

