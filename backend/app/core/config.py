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
    
    # File upload limits
    MAX_FILE_SIZE: int = 20 * 1024 * 1024  # 20 MB
    ALLOWED_EXTENSIONS: set = {".pdf", ".jpg", ".jpeg", ".png", ".docx"}
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()

