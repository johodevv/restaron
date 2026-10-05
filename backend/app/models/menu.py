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

    name = Column(String(100), nullable=False)          # O'zbek (lotin)
    name_ru = Column(String(100), nullable=True)          # Rus tili
    name_en = Column(String(100), nullable=True)          # Ingliz tili
    name_cyrillic = Column(String(100), nullable=True)    # O'zbek kirill (Ўзбекча)
    description = Column(Text, nullable=True)
    icon = Column(String(100), nullable=True)       # Emoji yoki icon nomi
    image_url = Column(String(500), nullable=True)
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    # Bosh sahifadagi (choyxona) menyuda shu kategoriya ko'rsatiladimi.
    # QR orqali ochilgan menyuda esa barcha kategoriyalar chiqaveradi.
    show_on_landing = Column(Boolean, default=True, nullable=False)

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

    name = Column(String(200), nullable=False)            # O'zbek (lotin)
    name_ru = Column(String(200), nullable=True)          # Rus tili
    name_en = Column(String(200), nullable=True)          # Ingliz tili
    name_cyrillic = Column(String(200), nullable=True)    # O'zbek kirill
    description = Column(Text, nullable=True)
    description_ru = Column(Text, nullable=True)
    description_en = Column(Text, nullable=True)
    description_cyrillic = Column(Text, nullable=True)    # Tavsif (kirill)

    price = Column(Float, nullable=False)
    image_url = Column(String(500), nullable=True)

    # Tortiladigan (o'lchanadigan) taom: baliq, go'sht, tovuq.
    # is_weighted=True bo'lsa `price` — 1 BIRLIK narxi (masalan 1 kg narxi),
    # va chek summasi aniq tortilgan og'irlikka ko'paytiriladi.
    is_weighted = Column(Boolean, default=False, nullable=False)
    unit = Column(String(10), default="dona", nullable=False)   # "kg", "l", "dona"

    # Sozlamalar
    is_available = Column(Boolean, default=True)      # Mavjudmi
    is_stop_list = Column(Boolean, default=False)     # Stop-List (1 bosish bilan to'xtatish)
    is_featured = Column(Boolean, default=False)      # Eng mashhur
    show_price = Column(Boolean, default=True)        # Narxni ko'rsatish (admin sozlamasi)

    # Taom ma'lumotlari
    prep_time_minutes = Column(Integer, default=15)   # Tayyorlash vaqti (minut)
    calories = Column(Integer, nullable=True)
    weight_grams = Column(Integer, nullable=True)     # Gramm

    # Oshxona stansiyasi (printer routing uchun)
    # hot_kitchen = 1-oshxona (qozonda pishadigan), cold_kitchen = 2-oshxona (baliq, somsa)
    # bar = Bar, customer = faqat mijozlar chekiga, other = boshqa
    kitchen_station = Column(String(50), default="hot_kitchen", nullable=False)

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
