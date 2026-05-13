import logging
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
    AnalyteCategory, AnalyteStandard, AnalyteSynonym, UserAnalyteMapping
)
from app.models.chat import ChatSession, ChatMessage  # AI assistant chat history
from app.models.mcp_oauth import (  # MCP OAuth 2.1 server (phase 2 multi-user)
    McpOAuthClient, McpAuthorizationCode, McpAccessToken, McpRefreshToken,
)
from app.models.subscription import PromoCode, PromoCodeActivation

# Import analyte normalization service
from app.services.analyte_normalization_service_db import analyte_normalization_service_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    print("🚀 Starting MedHistory API...")

    # Временная настройка логирования ассистента (отладка диалогов)
    asst_logger = logging.getLogger("medhistory.assistant")
    asst_logger.setLevel(logging.INFO)
    if not asst_logger.handlers:
        h = logging.StreamHandler()
        h.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
        asst_logger.addHandler(h)
    
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

    if settings.MCP_ENABLED:
        from mcp_server.server import mcp as mcp_instance
        async with mcp_instance.session_manager.run():
            yield
        from mcp_server.database import close_pg_pool
        await close_pg_pool()
    else:
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

# Mount MCP server (single-user remote, phase 1) — see backend/mcp_server/
if settings.MCP_ENABLED:
    if not settings.MCP_OAUTH_ENABLED and not settings.MCP_USER_ID:
        raise RuntimeError("MCP_ENABLED=true requires MCP_USER_ID (single-user) or MCP_OAUTH_ENABLED")
    from mcp_server.server import create_mcp_app
    app.mount("/mcp", create_mcp_app(settings.MCP_BEARER_TOKEN))
    if settings.MCP_OAUTH_ENABLED:
        # Rewrite root-level OAuth/discovery paths into the /mcp sub-app so that
        # strict RFC-9728 clients (claude.ai) find them at domain root in dev.
        # Prod (nginx on mcp.medhistory.ru) makes this a no-op since the proxy
        # already prepends /mcp before the request hits this layer.
        from mcp_server.oauth.well_known_proxy import WellKnownProxyMiddleware
        app.add_middleware(WellKnownProxyMiddleware, mount_prefix="/mcp")
    print(f"🔌 MCP mounted at /mcp (oauth={settings.MCP_OAUTH_ENABLED})")

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

