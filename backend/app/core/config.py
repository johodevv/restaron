import os
import re
import secrets
from pydantic_settings import BaseSettings
from typing import Optional

# backend/ papkasining absolyut yo'li (bu fayl: backend/app/core/config.py)
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./restaron.db"
    SYNC_DATABASE_URL: str = "sqlite:///./restaron.db"

    # Database Pool (PostgreSQL Production)
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800

    # JWT
    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 soat

    # App
    APP_NAME: str = "RestAron"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    # Restoranda server 24/7 ishlaydi. DEBUG=True bo'lsa HAR BIR SQL
    # so'rov jurnalga yoziladi va fayl gigabaytlarga o'sib diskni
    # to'ldiradi. Shuning uchun sukut bo'yicha O'CHIRILGAN.
    # Nosozlikni qidirish uchun .env da DEBUG=True qilinadi.
    DEBUG: bool = False
    ENABLE_DOCS: bool = False

    # CORS
    FRONTEND_URL: str = "http://localhost:5173"
    ALLOWED_ORIGINS: str = ""  # Vergul bilan ajratilgan qo'shimcha domenlar

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

DEFAULT_INSECURE_SECRET = "your-super-secret-key-change-in-production-min-32-chars"


def _ensure_secret_key(secret: str) -> str:
    """Xavfsiz JWT SECRET_KEY kafolati. Agar bo'sh yoki default bo'lsa, avtomatik generatsiya qilinadi."""
    if secret and secret != DEFAULT_INSECURE_SECRET and len(secret) >= 32:
        return secret

    env_path = os.path.join(BACKEND_DIR, ".env")
    new_secret = secrets.token_hex(32)
    try:
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                content = f.read()
            if "SECRET_KEY=" in content:
                content = re.sub(r"SECRET_KEY=.*", f"SECRET_KEY={new_secret}", content)
            else:
                content += f"\nSECRET_KEY={new_secret}\n"
            with open(env_path, "w", encoding="utf-8") as f:
                f.write(content)
        else:
            with open(env_path, "w", encoding="utf-8") as f:
                f.write(f"# RestAron xavfsizlik sozlamalari\nSECRET_KEY={new_secret}\nDEBUG=False\n")
    except Exception as e:
        print(f"[WARN] .env fayliga SECRET_KEY yozishda xatolik: {e}")
    return new_secret


settings.SECRET_KEY = _ensure_secret_key(settings.SECRET_KEY)
settings.DATABASE_URL = _absolutize_sqlite(settings.DATABASE_URL)
settings.SYNC_DATABASE_URL = _absolutize_sqlite(settings.SYNC_DATABASE_URL)

# Yuklanmalar (QR kodlar, rasmlar) ham absolyut papkada saqlanishi kerak
if not os.path.isabs(settings.UPLOAD_DIR):
    settings.UPLOAD_DIR = os.path.join(BACKEND_DIR, settings.UPLOAD_DIR)
