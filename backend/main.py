from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from prometheus_fastapi_instrumentator import Instrumentator

from app.api.v1.router import api_router
from app.core.config import settings
from app.db.postgres import engine, Base
from app.db.mongodb import mongodb_client
from app.db.minio_client import minio_client, ensure_bucket_exists

# Import models to register them with SQLAlchemy
from app.models.user import User
from app.models.document import Document, Tag, DocumentTag, Specialty, DocumentType
from app.models.report import Report

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

