"""
Bildirishnomalar modeli — Barcha xabarlar logi
"""
import enum
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime,
    Text, ForeignKey, func, Enum as SAEnum, JSON
)
from sqlalchemy.orm import relationship
from app.core.database import Base


class NotificationType(str, enum.Enum):
    # Mijozdan keluvchi
    NEW_ORDER = "new_order"           # Yangi buyurtma
    CALL_WAITER = "call_waiter"       # Ofitsiant chaqirish
    ORDER_CANCELLED = "order_cancelled"

    # Oshpazdan ofitsiantga
    ORDER_READY = "order_ready"       # Ovqat tayyor

    # Ofitsiantdan adminga
    ORDER_DELIVERED = "order_delivered"  # Yetkazib berildi ("Yetkazib berdim" bosildi)

    # Tizim
    ORDER_STATUS_CHANGED = "order_status_changed"
    SYSTEM_ALERT = "system_alert"     # Tizim xatosi


class NotificationTarget(str, enum.Enum):
    WAITER = "waiter"
    CHEF = "chef"
    ADMIN = "admin"
    ALL_STAFF = "all_staff"
    CUSTOMER = "customer"


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=False)

    # Kim uchun (foydalanuvchi yoki rol)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    target = Column(SAEnum(NotificationTarget), nullable=True)

    # Ma'lumot
    type = Column(SAEnum(NotificationType), nullable=False)
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)

    # Qo'shimcha ma'lumotlar (JSON)
    data = Column(JSON, nullable=True)  # order_id, table_id, etc.

    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="notifications")

    def __repr__(self):
        return f"<Notification {self.type} -> {self.target}>"
