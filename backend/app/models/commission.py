"""
Developer komissiya hisoboti modeli
"""
from sqlalchemy import (
    Column, Integer, String, Float, DateTime,
    Text, ForeignKey, func, Boolean
)
from sqlalchemy.orm import relationship
from app.core.database import Base


class CommissionLog(Base):
    __tablename__ = "commission_logs"

    id = Column(Integer, primary_key=True, index=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=False)

    # Hisobot davri
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)

    # Moliyaviy
    total_revenue = Column(Float, nullable=False)           # Ushbu davrda daromad
    commission_percent = Column(Float, nullable=False)       # Foiz (o'sha vaqtdagi)
    commission_amount = Column(Float, nullable=False)        # To'lash kerak bo'lgan summa
    total_orders = Column(Integer, nullable=False)           # Buyurtmalar soni

    # To'lov holati
    is_paid = Column(Boolean, default=False)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    payment_note = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    restaurant = relationship("Restaurant", back_populates="commission_logs")

    def __repr__(self):
        return f"<CommissionLog restaurant={self.restaurant_id} amount={self.commission_amount}>"
