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

    # Moliyaviy
    subtotal = Column(Float, default=0.0)       # Jami (chegirmasiz)
    discount = Column(Float, default=0.0)       # Chegirma
    total = Column(Float, default=0.0)          # Jami to'lov
    is_paid = Column(Boolean, default=False)

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

    # Oshpaz paneli uchun
    is_prepared = Column(Boolean, default=False)        # Tayyorlandimi
    prepared_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    order = relationship("Order", back_populates="items")
    menu_item = relationship("MenuItem", back_populates="order_items")

    def __repr__(self):
        return f"<OrderItem {self.menu_item_id} x{self.quantity}>"
