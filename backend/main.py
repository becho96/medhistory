from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from prometheus_fastapi_instrumentator import Instrumentator

from app.api.v1.router import api_router
from app.core.config import settings
from app.db.postgres import engine, Base, AsyncSessionLocal
from app.db.mongodb import mongodb_client
from app.db.minio_client import minio_client, ensure_bucket_exists

# Import models to register them with SQLAlchemy
from app.models.user import User
from app.models.family import FamilyRelation, FamilyInvite
from app.models.document import Document, Tag, DocumentTag, Specialty, DocumentType
from app.models.report import Report
from app.models.analyte import (
    AnalyteCategory, AnalyteStandard, AnalyteSynonym, 
    UnitConversion, UserAnalyteMapping
)

# Import analyte normalization service
from app.services.analyte_normalization_service_db import analyte_normalization_service_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    print("🚀 Starting MedHistory API...")
    
    # Create database tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Initialize MinIO bucket
    ensure_bucket_exists()
    
    # Load analyte normalization data from DB
    try:
        async with AsyncSessionLocal() as db:
            await analyte_normalization_service_db.load_from_db(db)
            stats = analyte_normalization_service_db.get_stats()
            if stats["categories_count"] > 0:
                print(f"✅ Справочник анализов загружен: {stats['categories_count']} категорий, "
                      f"{stats['analytes_count']} анализов, {stats['synonyms_count']} синонимов")
            else:
                print("⚠️ Справочник анализов пуст! Выполните: python scripts/seed_analyte_mappings.py")
    except Exception as e:
        print(f"⚠️ Не удалось загрузить справочник анализов: {e}")
        print("   Выполните миграцию и seed: python scripts/seed_analyte_mappings.py")
    
    print("✅ Database and storage initialized")
    
    yield
    
    # Shutdown
    print("🛑 Shutting down MedHistory API...")
    mongodb_client.close()

app = FastAPI(
    title="MedHistory API",
    description="Персональная система управления медицинской историей",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
# Parse CORS origins from environment variable (comma-separated)
cors_origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix="/api/v1")

# Prometheus metrics instrumentation
Instrumentator().instrument(app).expose(app, endpoint="/metrics")

@app.get("/")
async def root():
    return {
        "message": "MedHistory API",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "database": "connected",
        "storage": "connected"
    }

