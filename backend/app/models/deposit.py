from datetime import datetime, timezone
from app.core.types import UTCDateTime
"""Append-only movements: balance changes are separate from cash received."""
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, func
from app.core.database import Base


class DepositMovement(Base):
    __tablename__ = 'deposit_movements'
    id = Column(Integer, primary_key=True)
    restaurant_id = Column(Integer, ForeignKey('restaurants.id'), nullable=False, index=True)
    table_id = Column(Integer, ForeignKey('tables.id'), nullable=False, index=True)
    order_id = Column(Integer, ForeignKey('orders.id'), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    kind = Column(String(30), nullable=False)
    amount = Column(Float, nullable=False)
    cash_amount = Column(Float, nullable=False, default=0)
    created_at = Column(UTCDateTime(), default=lambda: datetime.now(timezone.utc), server_default=func.now(), index=True)
