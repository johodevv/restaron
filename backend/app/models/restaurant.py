"""
Restoran, Sozlamalar va Dizayn Temalari modellari
"""
import enum
from sqlalchemy import (
    Column, Integer, String, Boolean, Float, DateTime,
    Text, ForeignKey, func, JSON
)
from sqlalchemy.orm import relationship
from app.core.database import Base


class Restaurant(Base):
    __tablename__ = "restaurants"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)  # URL uchun
    description = Column(Text, nullable=True)
    logo_url = Column(String(500), nullable=True)
    address = Column(String(500), nullable=True)
    phone = Column(String(20), nullable=True)
    email = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)

    # Developer komissiyasi
    commission_percent = Column(Float, default=5.0)
    total_revenue = Column(Float, default=0.0)       # Umumiy daromad
    total_commission = Column(Float, default=0.0)    # To'langan komissiya

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    users = relationship("User", back_populates="restaurant", foreign_keys="User.restaurant_id")
    tables = relationship("Table", back_populates="restaurant", cascade="all, delete-orphan")
    categories = relationship("Category", back_populates="restaurant", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="restaurant")
    settings = relationship("RestaurantSettings", back_populates="restaurant", uselist=False,
                           cascade="all, delete-orphan")
    themes = relationship("RestaurantTheme", back_populates="restaurant", cascade="all, delete-orphan")
    commission_logs = relationship("CommissionLog", back_populates="restaurant")

    def __repr__(self):
        return f"<Restaurant {self.name}>"


class RestaurantSettings(Base):
    __tablename__ = "restaurant_settings"

    id = Column(Integer, primary_key=True, index=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id", ondelete="CASCADE"),
                          unique=True, nullable=False)

    # Narxlarni ko'rsatish/yashirish
    show_prices = Column(Boolean, default=True)

    # Buyurtma berish imkoni
    allow_orders = Column(Boolean, default=True)

    # Ofitsiant chaqirish imkoni
    allow_call_waiter = Column(Boolean, default=True)

    # Izoh qoldirish imkoni
    allow_reviews = Column(Boolean, default=True)

    # Til sozlamasi
    language = Column(String(10), default="uz")

    # Qo'shimcha sozlamalar (JSON)
    extra_settings = Column(JSON, nullable=True)

    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    restaurant = relationship("Restaurant", back_populates="settings")


class Theme(Base):
    """Mavjud dizayn temalari (tizimda oldindan yuklangan)"""
    __tablename__ = "themes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    slug = Column(String(50), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    preview_url = Column(String(500), nullable=True)  # Preview rasm

    # Tema konfiguratsiyasi (ranglar, font, stil)
    config = Column(JSON, nullable=False, default={})

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    restaurant_themes = relationship("RestaurantTheme", back_populates="theme")


class RestaurantTheme(Base):
    """Admin tanlagan 2 ta tema"""
    __tablename__ = "restaurant_themes"

    id = Column(Integer, primary_key=True, index=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False)
    theme_id = Column(Integer, ForeignKey("themes.id"), nullable=False)
    slot = Column(Integer, nullable=False)  # 1 yoki 2 (admin 2 ta tanlaydi)
    is_default = Column(Boolean, default=False)  # Default tema

    # Relationships
    restaurant = relationship("Restaurant", back_populates="themes")
    theme = relationship("Theme", back_populates="restaurant_themes")
