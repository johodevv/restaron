"""
Qarzlar va Nasiya Daftari modeli
"""
from sqlalchemy import (
    Column, Integer, String, Boolean, Float, DateTime,
    Text, ForeignKey, func
)
from sqlalchemy.orm import relationship
from app.core.database import Base


class Debt(Base):
    __tablename__ = "debts"

    id = Column(Integer, primary_key=True, index=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="SET NULL"), nullable=True)

    # Qarzdor mijoz ma'lumotlari
    customer_name = Column(String(150), nullable=False, index=True)
    customer_phone = Column(String(50), nullable=False, index=True)

    # Moliyaviy miqdorlar
    amount = Column(Float, nullable=False)             # Umumiy qarz summasi
    paid_amount = Column(Float, default=0.0)          # Qaytarilgan summa
    remaining_amount = Column(Float, default=0.0)       # Qolgan summa

    # Status: 'unpaid' (to'lanmagan), 'partially_paid' (qisman), 'paid' (to'liq yopilgan)
    status = Column(String(30), default="unpaid", index=True)

    # Muddat va izoh
    due_date = Column(DateTime(timezone=True), nullable=True)
    note = Column(Text, nullable=True)

    # SMS eslatmalar
    last_sms_sent_at = Column(DateTime(timezone=True), nullable=True)
    sms_count = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    restaurant = relationship("Restaurant", back_populates="debts")
    order = relationship("Order")

    def __repr__(self):
        return f"<Debt {self.customer_name}: {self.remaining_amount} so'm ({self.status})>"
