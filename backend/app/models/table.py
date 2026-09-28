"""
Stollar modeli — QR kod bilan birga
"""
import enum
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime,
    ForeignKey, func, Enum as SAEnum
)
from sqlalchemy.orm import relationship
from app.core.database import Base


class TableStatus(str, enum.Enum):
    AVAILABLE = "available"       # Bo'sh
    OCCUPIED = "occupied"         # Band (mijoz bor)
    RESERVED = "reserved"         # Rezerv qilingan
    MAINTENANCE = "maintenance"   # Ta'mirat


class Table(Base):
    __tablename__ = "tables"

    id = Column(Integer, primary_key=True, index=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False)

    # Stol identifikatsiyasi
    number = Column(Integer, nullable=False)                 # Stol raqami (1, 2, 3...)
    name = Column(String(100), nullable=True)               # Masalan: "VIP Xona 1"
    room = Column(String(100), nullable=True)               # Xona nomi
    capacity = Column(Integer, default=4)                   # O'rindiqlar soni

    # QR Kod
    qr_token = Column(String(200), unique=True, nullable=False, index=True)  # Noyob token
    qr_image_url = Column(String(500), nullable=True)       # QR rasm URL

    status = Column(SAEnum(TableStatus), default=TableStatus.AVAILABLE)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    restaurant = relationship("Restaurant", back_populates="tables")
    orders = relationship("Order", back_populates="table")

    def __repr__(self):
        return f"<Table #{self.number} ({self.restaurant_id})>"
