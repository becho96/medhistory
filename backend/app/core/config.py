from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # App
    APP_NAME: str = "MedHistory"
    ENVIRONMENT: str = "development"
    
    # Database
    DATABASE_URL: str
    MONGODB_URL: str
    
    # MinIO
    MINIO_ENDPOINT: str
    MINIO_ACCESS_KEY: str
    MINIO_SECRET_KEY: str
    MINIO_BUCKET: str = "medhistory-files"
    MINIO_SECURE: bool = False
    
    # OpenRouter AI (модель задаётся через OPENROUTER_MODEL в .env)
    OPENROUTER_API_KEY: str
    OPENROUTER_MODEL: str = "google/gemini-2.5-flash"  # Рекомендуется: быстрее, без geo-ограничений
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1/chat/completions"
    # Output cap for extraction calls. Must fit the largest analysis JSON
    # (multi-page lab reports can have 50+ analytes) — too low truncates the
    # JSON and the parse falls back to an empty result.
    OPENROUTER_MAX_TOKENS: int = 8000
    
    # Authentication
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # Telegram bot
    BOT_SECRET: str = ""           # shared secret for trusted bot↔backend calls (X-Bot-Secret)
    TELEGRAM_BOT_TOKEN: str = ""   # used to validate Mini App initData HMAC signature
    
    # AI Assistant — Anthropic (primary provider for assistant)
    ANTHROPIC_API_KEY: str = ""

    # Assistant model defaults (can be overridden per session)
    ASSISTANT_PROVIDER: str = "anthropic"           # "anthropic" | "openrouter"
    ASSISTANT_MODEL: str = "claude-sonnet-4-6"      # model id within the provider

    # Chat history: how many past messages to include as context
    CHAT_HISTORY_LIMIT: int = 20

    # Assistant data retrieval limits (документы из медкарты)
    ASSISTANT_LAB_RESULTS_LIMIT: int = 200      # Результаты анализа
    ASSISTANT_DOCTOR_VISITS_LIMIT: int = 100    # Прием врача
    ASSISTANT_INTERPRETATIONS_LIMIT: int = 20
    ASSISTANT_HEALTH_EVENTS_LIMIT: int = 100
    ASSISTANT_STUDIES_LIMIT: int = 100          # Инструментальные исследования + Функциональная диагностика
    
    # Public base URL of the API (used to build self-contained download URLs
    # served back through the proxy /api/v1/documents/{id}/download endpoint,
    # e.g. by the MCP get_document_original tool).
    # Local: http://localhost:8000   Prod: https://medhistory.ru
    PUBLIC_BASE_URL: str = "http://localhost:8000"

    # MCP server
    MCP_ENABLED: bool = False
    # Phase 1 (single-user) — bearer token + hardcoded user_id. Kept as fallback
    # when MCP_OAUTH_ENABLED=false; ignored otherwise.
    MCP_BEARER_TOKEN: str = ""
    MCP_USER_ID: str = ""
    # Phase 2 (multi-user OAuth) — when true, MCP server runs as a real OAuth 2.1
    # authorization server with Dynamic Client Registration. user_id is resolved
    # from the bearer token's auth context, not from MCP_USER_ID.
    MCP_OAUTH_ENABLED: bool = False
    # Public URL of the MCP server (used as OAuth issuer + resource server URL).
    # Local: http://localhost:8000   Prod: https://mcp.medhistory.ru
    MCP_PUBLIC_URL: str = "http://localhost:8000"
    # Frontend consent page URL (where the user reviews and approves the request).
    # Local: http://localhost:5173/oauth/consent
    # Prod:  https://medhistory.ru/oauth/consent
    MCP_CONSENT_URL: str = "http://localhost:5173/oauth/consent"

    # Embeddings sidecar (multilingual-e5-base over HTTP)
    EMBEDDINGS_URL: str = "http://embeddings:8001"
    EMBEDDINGS_TIMEOUT: float = 30.0

    # CORS
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"  # Comma-separated list
    
    # File upload limits
    MAX_FILE_SIZE: int = 20 * 1024 * 1024  # 20 MB
    ALLOWED_EXTENSIONS: set = {".pdf", ".jpg", ".jpeg", ".png", ".docx"}
    
    class Config:
        # Переменные окружения передаются через docker-compose из .env.local/.env.staging/.env.production
        # Для локальной разработки без Docker создайте .env.local и запустите: source .env.local
        case_sensitive = True

settings = Settings()

