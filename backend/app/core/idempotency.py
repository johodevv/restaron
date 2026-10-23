"""Reserve operation keys and persist responses in the business transaction."""
import hashlib
import json
from datetime import datetime, timezone, timedelta
from typing import Optional, Any
from fastapi import Header, Request, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select, delete, text
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.idempotency import IdempotencyKey


class IdempotencyHandler:
    def __init__(self, key: Optional[str], endpoint: str, db: AsyncSession, request_hash: str = ''):
        self.key = key.strip() if key else None
        if self.key and len(self.key) > 100:
            raise HTTPException(400, 'Idempotency-Key 100 belgidan oshmasligi kerak')
        self.endpoint = endpoint
        self.db = db
        self.request_hash = request_hash
        self.record = None
        self.claimed = False

    async def get_cached_response(self, user_id: Optional[int]) -> Optional[Any]:
        if not self.key or self.claimed:
            return None
        scoped_key = hashlib.sha256(f'{user_id}:{self.endpoint}:{self.key}'.encode()).hexdigest()
        legacy = await self.db.scalar(select(IdempotencyKey).where(
            IdempotencyKey.key == self.key, IdempotencyKey.user_id == user_id,
            IdempotencyKey.endpoint == self.endpoint,
        ))
        if legacy is None:
            dialect = self.db.bind.dialect.name
            if dialect == 'sqlite':
                from sqlalchemy.dialects.sqlite import insert
            elif dialect == 'postgresql':
                from sqlalchemy.dialects.postgresql import insert
            else:
                raise RuntimeError('Unsupported idempotency database')
            result = await self.db.execute(insert(IdempotencyKey).values(
                key=scoped_key, user_id=user_id, endpoint=self.endpoint,
                status_code=102, response_json='null', request_hash=self.request_hash,
            ).on_conflict_do_nothing(index_elements=['key']))
            self.claimed = result.rowcount == 1
            self.record = await self.db.scalar(select(IdempotencyKey).where(IdempotencyKey.key == scoped_key))
        else:
            self.record = legacy
        if self.record.request_hash and self.record.request_hash != self.request_hash:
            raise HTTPException(409, "Bu amal kaliti boshqa so'rov uchun ishlatilgan")
        if self.claimed:
            return None
        if self.record.status_code == 102:
            raise HTTPException(409, 'Amal hali yakunlanmagan; aynan shu kalit bilan keyinroq tekshiring')
        return json.loads(self.record.response_json)

    async def save_response(self, user_id: Optional[int], response_data: Any, status_code: int = 200):
        if not self.key:
            return
        if self.record is None:
            raise RuntimeError('Idempotency response saved without reserving its key')
        self.record.status_code = status_code
        self.record.response_json = json.dumps(jsonable_encoder(response_data), ensure_ascii=False)
        await self.db.flush()


async def get_idempotency_handler(
    request: Request, db: AsyncSession = Depends(get_db),
    idempotency_key: Optional[str] = Header(None, alias='Idempotency-Key'),
) -> IdempotencyHandler:
    body = await request.body()
    digest = hashlib.sha256(request.method.encode() + b'\n' + request.url.query.encode() + b'\n' + body).hexdigest()
    return IdempotencyHandler(idempotency_key, request.url.path, db, digest)


def cleanup_expired_idempotency_keys_sync(sync_conn):
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    sync_conn.execute(text('DELETE FROM idempotency_keys WHERE created_at < :cutoff'),
                      {'cutoff': cutoff.strftime('%Y-%m-%d %H:%M:%S')})


async def cleanup_expired_idempotency_keys(db: AsyncSession):
    await db.execute(delete(IdempotencyKey).where(
        IdempotencyKey.created_at < datetime.now(timezone.utc) - timedelta(hours=24)))
    await db.commit()
