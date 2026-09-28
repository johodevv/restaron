"""
Baholash va Izohlar modeli
"""
from sqlalchemy import (
    Column, Integer, String, Boolean, Float, DateTime,
    Text, ForeignKey, func
)
from sqlalchemy.orm import relationship
from app.core.database import Base


class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)

    # Taom bahosi (ixtiyoriy)
    menu_item_id = Column(Integer, ForeignKey("menu_items.id"), nullable=True)
    food_rating = Column(Integer, nullable=True)          # 1-5 yulduz
    food_comment = Column(Text, nullable=True)

    # Ofitsiant bahosi (ixtiyoriy)
    waiter_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    service_rating = Column(Integer, nullable=True)       # 1-5 yulduz
    service_comment = Column(Text, nullable=True)

    # Umumiy baho
    overall_rating = Column(Float, nullable=True)

    # Mijoz ma'lumoti
    customer_name = Column(String(100), nullable=True)    # Ixtiyoriy

    is_published = Column(Boolean, default=True)          # Admin moderatsiyasi

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    order = relationship("Order", back_populates="reviews")
    menu_item = relationship("MenuItem", back_populates="reviews")
    waiter = relationship("User", back_populates="reviews_received", foreign_keys=[waiter_id])

    def __repr__(self):
        return f"<Review food={self.food_rating} service={self.service_rating}>"
