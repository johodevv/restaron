"""
RestAron — Idempotency mexanizmi
Takroriy so'rovlar (duplicate requests) va poyga holatlaridan himoya
"""
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Any
from fastapi import Header, Request, Depends
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select, delete, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.core.database import get_db
from app.models.idempotency import IdempotencyKey

logger = logging.getLogger("idempotency")


class IdempotencyHandler:
    def __init__(self, key: Optional[str], endpoint: str, db: AsyncSession):
        self.key = key.strip() if key else None
        self.endpoint = endpoint
        self.db = db

    async def get_cached_response(self, user_id: Optional[int]) -> Optional[Any]:
        """Agar shu user + endpoint + key uchun avval saqlangan javob bo'lsa, uni qaytaradi"""
        if not self.key:
            return None
        try:
            stmt = select(IdempotencyKey).where(
                IdempotencyKey.key == self.key,
                IdempotencyKey.user_id == user_id,
                IdempotencyKey.endpoint == self.endpoint,
            )
            res = await self.db.execute(stmt)
            record = res.scalar_one_or_none()
            if record:
                logger.info(
                    "Idempotent so'rov ushlandi (key=%s, user=%s, endpoint=%s). Saqlangan javob qaytarilmoqda.",
                    self.key,
                    user_id,
                    self.endpoint,
                )
                return json.loads(record.response_json)
        except Exception as e:
            logger.warning("Idempotency keshini o'qishda xatolik: %s", e)
        return None

    async def save_response(self, user_id: Optional[int], response_data: Any, status_code: int = 200):
        """Muvaffaqiyatli bajarilgan so'rov natijasini idempotency_keys jadvaliga saqlaydi"""
        if not self.key:
            return
        try:
            encoded = jsonable_encoder(response_data)
            json_str = json.dumps(encoded, ensure_ascii=False)
            new_record = IdempotencyKey(
                key=self.key,
                user_id=user_id,
                endpoint=self.endpoint,
                status_code=status_code,
                response_json=json_str,
            )
            self.db.add(new_record)
            await self.db.commit()
            logger.info(
                "Idempotency javobi saqlandi (key=%s, user=%s, endpoint=%s)",
                self.key,
                user_id,
                self.endpoint,
            )
        except IntegrityError:
            await self.db.rollback()
            logger.warning("Idempotency kaliti allaqachon mavjud (key=%s)", self.key)
        except Exception as e:
            await self.db.rollback()
            logger.warning("Idempotency javobini saqlashda xatolik: %s", e)


async def get_idempotency_handler(
    request: Request,
    db: AsyncSession = Depends(get_db),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
) -> IdempotencyHandler:
    """FastAPI Dependency: Idempotency-Key sarlavhasi va joriy endpointni bog'laydi"""
    return IdempotencyHandler(
        key=idempotency_key,
        endpoint=request.url.path,
        db=db,
    )


def cleanup_expired_idempotency_keys_sync(sync_conn):
    """Server ishga tushganda 24 soatdan eski idempotency yozuvlarini tozalaydi (sync)"""
    try:
        # SQLite va PostgreSQL uchun universal vaqt hisobi
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        deleted = sync_conn.execute(
            text("DELETE FROM idempotency_keys WHERE created_at < :cutoff"),
            {"cutoff": cutoff.strftime("%Y-%m-%d %H:%M:%S")},
        )
        logger.info("Eski idempotency kalitlari tozalandi (24+ soat). O'chirilgan qatorlar soni: %s", deleted.rowcount)
    except Exception as e:
        logger.warning("Eski idempotency kalitlarini tozalashda xatolik: %s", e)


async def cleanup_expired_idempotency_keys(db: AsyncSession):
    """Server ishga tushganda 24 soatdan eski idempotency yozuvlarini tozalaydi (async)"""
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        stmt = delete(IdempotencyKey).where(IdempotencyKey.created_at < cutoff)
        result = await db.execute(stmt)
        await db.commit()
        logger.info("Eski idempotency kalitlari tozalandi (24+ soat): %s ta", result.rowcount)
    except Exception as e:
        await db.rollback()
        logger.warning("Eski idempotency kalitlarini tozalashda xatolik (async): %s", e)
