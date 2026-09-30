"""
Buyurtmalar va Buyurtma Elementlari modellari
"""
import enum
from sqlalchemy import (
    Column, Integer, String, Boolean, Float, DateTime,
    Text, ForeignKey, func, Enum as SAEnum
)
from sqlalchemy.orm import relationship
from app.core.database import Base


class OrderStatus(str, enum.Enum):
    PENDING = "pending"           # Kutilmoqda (yangi buyurtma)
    CONFIRMED = "confirmed"       # Tasdiqlangan
    PREPARING = "preparing"       # Tayyorlanmoqda (oshpazda)
    READY = "ready"               # Tayyor (ofitsiant olib borishi kerak)
    SERVED = "served"             # Berildi
    CANCELLED = "cancelled"       # Bekor qilingan
    PAID = "paid"                 # To'landi


class CallStatus(str, enum.Enum):
    """Ofitsiant chaqirish statusi"""
    PENDING = "pending"
    ACKNOWLEDGED = "acknowledged"  # Ofitsiant ko'rdi
    COMPLETED = "completed"


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    order_number = Column(String(20), unique=True, nullable=False, index=True)  # #0001

    restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=False)
    table_id = Column(Integer, ForeignKey("tables.id"), nullable=False)
    waiter_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Tayinlangan ofitsiant

    # Mijoz ma'lumoti (ixtiyoriy)
    customer_name = Column(String(100), nullable=True)
    customer_note = Column(Text, nullable=True)

    status = Column(SAEnum(OrderStatus), default=OrderStatus.PENDING, nullable=False)

    # Zakaz turi va joy (Ali Poster uslubida)
    order_type = Column(String(50), default="table")     # "table" (Столы), "takeaway" (С собой), "delivery" (Доставка)
    hall_name = Column(String(100), nullable=True)       # "Балкон", "Хона", "Тераса", "Куча", "Зал"
    kitchen_note = Column(Text, nullable=True)           # Комент. к кухне
    receipt_note = Column(Text, nullable=True)           # Комент. к чеку

    # Moliyaviy va To'lovlar
    subtotal = Column(Float, default=0.0)                # Taomlar yig'indisi (chegirmasiz)
    service_fee_percent = Column(Float, default=12.0)    # Xizmat haqi foizi (masalan 12%, 13%)
    service_fee_amount = Column(Float, default=0.0)     # Xizmat haqi summasi
    discount = Column(Float, default=0.0)                # Chegirma
    total = Column(Float, default=0.0)                   # Jami to'lov (subtotal + service_fee - discount)
    is_paid = Column(Boolean, default=False)

    # To'lov turlari (Kassa: Naqd, Karta, Click, Nasiya)
    payment_method = Column(String(50), default="cash")  # "cash", "card", "click", "debt", "mixed"
    cash_amount = Column(Float, default=0.0)            # Наличные
    card_amount = Column(Float, default=0.0)            # Карта
    click_amount = Column(Float, default=0.0)           # Click/Payme
    debt_amount = Column(Float, default=0.0)            # Nasiya / Qarz

    # Ofitsiant ulushi (KPI / Заработок)
    waiter_share_percent = Column(Float, default=0.0)
    waiter_share_amount = Column(Float, default=0.0)

    # Ofitsiant chaqirish
    call_waiter = Column(Boolean, default=False)
    call_status = Column(SAEnum(CallStatus), nullable=True)
    call_note = Column(String(300), nullable=True)  # Chaqiruv sababi

    # Vaqtlar
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    confirmed_at = Column(DateTime(timezone=True), nullable=True)
    preparing_at = Column(DateTime(timezone=True), nullable=True)
    ready_at = Column(DateTime(timezone=True), nullable=True)
    served_at = Column(DateTime(timezone=True), nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)   # Smena/Stol yopilgan vaqt
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    restaurant = relationship("Restaurant", back_populates="orders")
    table = relationship("Table", back_populates="orders")
    waiter = relationship("User", back_populates="orders_served", foreign_keys=[waiter_id])
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    reviews = relationship("Review", back_populates="order")

    def __repr__(self):
        return f"<Order {self.order_number} ({self.status})>"


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    menu_item_id = Column(Integer, ForeignKey("menu_items.id"), nullable=False)

    quantity = Column(Integer, nullable=False, default=1)
    unit_price = Column(Float, nullable=False)          # Buyurtma vaqtidagi narx
    total_price = Column(Float, nullable=False)         # quantity * unit_price

    special_note = Column(Text, nullable=True)          # Maxsus talab (masalan: "qalampir kam")
    item_time = Column(String(20), nullable=True)       # Urilgan vaqti (masalan: "19:36")

    # Oshxona yuborilganlik holati (Oshxona begunogi)
    sent_to_kitchen = Column(Boolean, default=False)
    sent_to_kitchen_at = Column(DateTime(timezone=True), nullable=True)

    # Oshpaz paneli uchun
    is_prepared = Column(Boolean, default=False)        # Tayyorlandimi
    prepared_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    order = relationship("Order", back_populates="items")
    menu_item = relationship("MenuItem", back_populates="order_items")

    def __repr__(self):
        return f"<OrderItem {self.menu_item_id} x{self.quantity}>"
