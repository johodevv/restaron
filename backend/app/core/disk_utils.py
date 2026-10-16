"""
RestAron — Disk xotirasini tekshirish va xavfsiz fayl yozish (Disk Full Protection)
Server diskida joy yetarli bo'lmaganda (ENOSPC) operatsiyalarni to'xtatib,
tizimni 507 Insufficient Storage xatosi bilan himoyalash.
"""
import os
import shutil
import logging
from typing import Optional
from fastapi import HTTPException, status
from app.core.config import settings

logger = logging.getLogger("disk_utils")

# Minimal zaruriy bo'sh joy (MB)
MIN_FREE_DISK_MB = 50


def get_free_disk_mb(path: Optional[str] = None) -> float:
    """Belgilangan yo'ldagi bo'sh disk xotirasini megabaytda qaytarish"""
    target_path = path or settings.UPLOAD_DIR
    if not os.path.exists(target_path):
        target_path = os.path.dirname(target_path) or "."
    try:
        total, used, free = shutil.disk_usage(target_path)
        return free / (1024 * 1024)
    except Exception as e:
        logger.warning(f"Disk hajmini aniqlashda xatolik: {e}")
        return 999999.0  # Aniqlab bo'lmasa o'tkazib yuborish


def ensure_disk_space(required_mb: int = MIN_FREE_DISK_MB, path: Optional[str] = None) -> None:
    """
    Diskda yetarli bo'sh joy borligini tekshiradi.
    Agar bo'sh joy `required_mb` dan kam bo'lsa, HTTPException(507) chiqaradi.
    """
    free_mb = get_free_disk_mb(path)
    if free_mb < required_mb:
        logger.critical(
            f"DIQQAT: Server diskida joy tugadi! Bo'sh joy: {free_mb:.1f} MB (talab: {required_mb} MB)"
        )
        raise HTTPException(
            status_code=status.HTTP_507_INSUFFICIENT_STORAGE,
            detail=f"Server disk xotirasi to'lgan ({free_mb:.1f} MB bo'sh). Fayl yoki chekni saqlab bo'lmadi.",
        )


async def safe_write_upload(file_path: str, content: bytes) -> None:
    """
    Faylni diskka xavfsiz yozish.
    Disk to'lib qolishi (OSError / ENOSPC) holatlarini ushlab, to'g'ri xato qaytaradi.
    """
    ensure_disk_space(required_mb=len(content) // (1024 * 1024) + 10, path=os.path.dirname(file_path))
    try:
        import aiofiles
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)
    except OSError as exc:
        logger.error(f"Fayl yozishda disk/OS xatosi: {exc}")
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass
        raise HTTPException(
            status_code=status.HTTP_507_INSUFFICIENT_STORAGE,
            detail=f"Disk to'lganligi sababli faylni saqlash muvaffaqiyatsiz bo'ldi: {str(exc)}",
        )
