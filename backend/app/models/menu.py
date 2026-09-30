"""
Menyu: Kategoriyalar va Taomlar modellari
"""
from sqlalchemy import (
    Column, Integer, String, Boolean, Float, DateTime,
    Text, ForeignKey, func
)
from sqlalchemy.orm import relationship
from app.core.database import Base


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False)

    name = Column(String(100), nullable=False)
    name_ru = Column(String(100), nullable=True)   # Rus tili
    name_en = Column(String(100), nullable=True)   # Ingliz tili
    description = Column(Text, nullable=True)
    icon = Column(String(100), nullable=True)       # Emoji yoki icon nomi
    image_url = Column(String(500), nullable=True)
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    restaurant = relationship("Restaurant", back_populates="categories")
    items = relationship("MenuItem", back_populates="category", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Category {self.name}>"


class MenuItem(Base):
    __tablename__ = "menu_items"

    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="CASCADE"), nullable=False)

    name = Column(String(200), nullable=False)
    name_ru = Column(String(200), nullable=True)
    name_en = Column(String(200), nullable=True)
    description = Column(Text, nullable=True)
    description_ru = Column(Text, nullable=True)
    description_en = Column(Text, nullable=True)

    price = Column(Float, nullable=False)
    image_url = Column(String(500), nullable=True)

    # Sozlamalar
    is_available = Column(Boolean, default=True)      # Mavjudmi
    is_stop_list = Column(Boolean, default=False)     # Stop-List (1 bosish bilan to'xtatish)
    is_featured = Column(Boolean, default=False)      # Eng mashhur
    show_price = Column(Boolean, default=True)        # Narxni ko'rsatish (admin sozlamasi)

    # Taom ma'lumotlari
    prep_time_minutes = Column(Integer, default=15)   # Tayyorlash vaqti (minut)
    calories = Column(Integer, nullable=True)
    weight_grams = Column(Integer, nullable=True)     # Gramm

    # Statistika
    total_ordered = Column(Integer, default=0)        # Necha marta buyurtma qilingan
    avg_rating = Column(Float, default=0.0)           # O'rtacha baho
    rating_count = Column(Integer, default=0)         # Baholashlar soni

    sort_order = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    category = relationship("Category", back_populates="items")
    order_items = relationship("OrderItem", back_populates="menu_item")
    reviews = relationship("Review", back_populates="menu_item")

    def __repr__(self):
        return f"<MenuItem {self.name} ({self.price} so'm)>"
