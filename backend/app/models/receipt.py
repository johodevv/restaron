"""
Cheklar Arxivi va Smena Hisobotlari (X/Z Report) modellari
Xprinter uchun barcha ma'lumotlar 3 yilgacha saqlanadi
"""
from sqlalchemy import (
    Column, Integer, String, Boolean, Float, DateTime,
    Text, ForeignKey, func, JSON
)
from sqlalchemy.orm import relationship
from app.core.database import Base


class ReceiptArchive(Base):
    """
    3 yilgacha arxivda saqlanadigan cheklar snapshot'i
    """
    __tablename__ = "receipt_archives"

    id = Column(Integer, primary_key=True, index=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False, index=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="SET NULL"), nullable=True)

    receipt_number = Column(String(50), nullable=False, index=True)
    # Turlari: 'kitchen' (oshxona begunogi), 'pre_check' (mijoz hisob cheki), 'final_bill', 'x_report', 'z_report'
    receipt_type = Column(String(30), default="final_bill", index=True)

    # Joy va xodim
    hall_name = Column(String(100), nullable=True)    # "Балкон", "Хона", "Тераса"
    table_name = Column(String(100), nullable=True)   # "N# 30"
    waiter_name = Column(String(100), nullable=True)  # "Зафарбек"

    # Moliyaviy ko'rsatkichlar
    subtotal = Column(Float, default=0.0)
    service_fee_percent = Column(Float, default=12.0)
    service_fee_amount = Column(Float, default=0.0)
    total_amount = Column(Float, default=0.0)

    # To'lov turlari
    payment_method = Column(String(50), default="cash")  # "cash", "card", "click", "debt", "mixed"
    cash_amount = Column(Float, default=0.0)
    card_amount = Column(Float, default=0.0)
    click_amount = Column(Float, default=0.0)
    debt_amount = Column(Float, default=0.0)

    # Mahsulotlar (JSON formatida to'liq nusxasi)
    items_json = Column(JSON, nullable=True)

    notes = Column(Text, nullable=True)
    # Xprinter uchun tayyorlangan matn (58mm/80mm format)
    raw_text = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Relationships
    restaurant = relationship("Restaurant", back_populates="receipt_archives")
    order = relationship("Order")

    def __repr__(self):
        return f"<ReceiptArchive #{self.receipt_number} ({self.receipt_type}): {self.total_amount}>"


class ShiftReport(Base):
    """
    Smena hisoboti (X-Hisobot va Z-Hisobot — Kassa yopilishi)
    """
    __tablename__ = "shift_reports"

    id = Column(Integer, primary_key=True, index=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False, index=True)
    cashier_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    shift_number = Column(Integer, default=1)
    report_type = Column(String(20), default="z_report")  # "x_report" yoki "z_report"

    opened_at = Column(DateTime(timezone=True), nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)

    total_orders = Column(Integer, default=0)
    total_sales = Column(Float, default=0.0)
    total_cash = Column(Float, default=0.0)
    total_card = Column(Float, default=0.0)
    total_click = Column(Float, default=0.0)
    total_debt = Column(Float, default=0.0)
    total_service_fee = Column(Float, default=0.0)
    total_waiter_earnings = Column(Float, default=0.0)

    # Ofitsiantlar va taomlar bo'yicha tahlil (JSON)
    waiter_breakdown = Column(JSON, nullable=True)
    items_breakdown = Column(JSON, nullable=True)

    is_closed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    restaurant = relationship("Restaurant", back_populates="shift_reports")
    cashier = relationship("User")

    def __repr__(self):
        return f"<ShiftReport #{self.shift_number} ({self.report_type}): {self.total_sales}>"
