from app.core.types import UTCDateTime
"""
RestAron — Idempotency kalitlari modeli
Takroriy so'rovlardan (duplicate order, duplicate payment) himoya
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base


class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    endpoint = Column(String(255), nullable=False, index=True)
    status_code = Column(Integer, nullable=False, default=200)
    response_json = Column(Text, nullable=False)
    request_hash = Column(String(64), nullable=True)
    created_at = Column(UTCDateTime(), default=func.now(), server_default=func.now(), index=True)

    def __repr__(self):
        return f"<IdempotencyKey {self.key} user={self.user_id} endpoint={self.endpoint}>"
