import os
import re
from pydantic_settings import BaseSettings
from typing import Optional

# backend/ papkasining absolyut yo'li (bu fayl: backend/app/core/config.py)
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./restaron.db"
    SYNC_DATABASE_URL: str = "sqlite:///./restaron.db"

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
        env_file = os.path.join(BACKEND_DIR, ".env")
        env_file_encoding = "utf-8"


def _absolutize_sqlite(url: str) -> str:
    """
    SQLite yo'lini ABSOLYUT qiladi.

    MUHIM: sukut bo'yicha yo'l nisbiy edi ("sqlite:///./restaron.db").
    Server Windows'da xizmat (Scheduled Task) sifatida ishga tushganda ish
    papkasi C:\\Windows\\System32 bo'ladi — natijada o'sha yerda BO'SH yangi
    baza yaratilib, restoranning barcha ma'lumotlari yo'qolgandek ko'rinardi.
    Shuning uchun yo'lni doim backend/ papkasiga bog'laymiz.
    """
    m = re.match(r"^(sqlite(?:\+\w+)?:///)(?!/)(.*)$", url)
    if not m:
        return url
    prefix, path = m.group(1), m.group(2)
    if not path or os.path.isabs(path):
        return url
    abs_path = os.path.normpath(os.path.join(BACKEND_DIR, path))
    return prefix + abs_path.replace("\\", "/")


settings = Settings()

settings.DATABASE_URL = _absolutize_sqlite(settings.DATABASE_URL)
settings.SYNC_DATABASE_URL = _absolutize_sqlite(settings.SYNC_DATABASE_URL)

# Yuklanmalar (QR kodlar, rasmlar) ham absolyut papkada saqlanishi kerak
if not os.path.isabs(settings.UPLOAD_DIR):
    settings.UPLOAD_DIR = os.path.join(BACKEND_DIR, settings.UPLOAD_DIR)
