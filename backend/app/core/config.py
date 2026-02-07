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
    
    # OpenRouter AI
    OPENROUTER_API_KEY: str
    OPENROUTER_MODEL: str = "anthropic/claude-3.5-sonnet"  # Можно также использовать claude-sonnet-4 или claude-sonnet-4.5
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

