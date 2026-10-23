from sqlalchemy import Column, String, Float
from app.core.database import Base


class TokenRevocation(Base):
    __tablename__ = 'token_revocations'
    jti = Column(String(100), primary_key=True)
    expires_at = Column(Float, nullable=False, index=True)
