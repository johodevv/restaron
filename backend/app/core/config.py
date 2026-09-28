from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/restaron_db"
    SYNC_DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/restaron_db"

    # JWT
    SECRET_KEY: str = "your-super-secret-key-change-in-production-min-32-chars"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 soat

    # App
    APP_NAME: str = "RestAron"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    DEBUG: bool = True

    # CORS
    FRONTEND_URL: str = "http://localhost:5173"

    # QR Code
    QR_BASE_URL: str = "http://localhost:5173"

    # Upload
    UPLOAD_DIR: str = "uploads"

    # Developer commission (%)
    COMMISSION_PERCENT: float = 5.0

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
