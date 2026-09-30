"""
Foydalanuvchilar modeli
Rollar: developer, admin, waiter, chef
"""
import enum
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Boolean, Float, DateTime,
    Enum as SAEnum, ForeignKey, func
)
from sqlalchemy.orm import relationship
from app.core.database import Base


class UserRole(str, enum.Enum):
    DEVELOPER = "developer"   # Superadmin / Dasturchi
    ADMIN = "admin"           # Restoran egasi/admin
    WAITER = "waiter"         # Ofitsiant
    CHEF = "chef"             # Oshpaz


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    full_name = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(SAEnum(UserRole), nullable=False, default=UserRole.WAITER)
    is_active = Column(Boolean, default=True)
    avatar_url = Column(String(500), nullable=True)
    # Ofitsiant xizmat haqi ulushi / komissiya foizi (masalan: 3.0%)
    commission_percent = Column(Float, default=0.0)

    # Admin va xodimlar bitta restoranga tegishli
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    restaurant = relationship("Restaurant", back_populates="users", foreign_keys=[restaurant_id])
    orders_served = relationship("Order", back_populates="waiter", foreign_keys="Order.waiter_id")
    notifications = relationship("Notification", back_populates="user")
    reviews_received = relationship("Review", back_populates="waiter", foreign_keys="Review.waiter_id")

    def __repr__(self):
        return f"<User {self.username} ({self.role})>"
