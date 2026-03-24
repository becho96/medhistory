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
    
    # Authentication
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    
    # Google OAuth
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:5173/auth/google/callback"
    
    # Telegram Bot
    BOT_SECRET: str = ""  # Shared secret between n8n and backend for bot API auth

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

