from app.core.types import UTCDateTime
"""
RestAron — PrintJob modeli
Chop etish navbati va uning holati (server o'chib-yonsa ham yo'qolmaydi)
"""
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime,
    ForeignKey, Index, JSON, func
)
from sqlalchemy.orm import relationship
from app.core.database import Base


class PrintJob(Base):
    __tablename__ = "print_jobs"

    id = Column(Integer, primary_key=True, index=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False, index=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="SET NULL"), nullable=True, index=True)
    # Turlari: kitchen/bar/kassa/bill/cancel/test
    ticket_type = Column(String(30), nullable=False, default="kitchen")
    printer_name = Column(String(255), nullable=False)
    raw_text = Column(Text, nullable=False)
    options = Column(JSON, nullable=True)
    # Holatlari: pending/printing/done/cancelled
    status = Column(String(20), nullable=False, default="pending", index=True)
    attempts = Column(Integer, nullable=False, default=0)
    next_attempt_at = Column(UTCDateTime(), nullable=False, default=func.now(), server_default=func.now())
    last_error = Column(Text, nullable=True)
    alerted = Column(Boolean, nullable=False, default=False)
    created_at = Column(UTCDateTime(), nullable=False, default=func.now(), server_default=func.now())
    printed_at = Column(UTCDateTime(), nullable=True)

    __table_args__ = (
        Index("ix_print_jobs_status_next_attempt_at", "status", "next_attempt_at"),
    )

    # Relationships
    restaurant = relationship("Restaurant")
    order = relationship("Order")

    def __repr__(self):
        return f"<PrintJob id={self.id} printer='{self.printer_name}' type='{self.ticket_type}' status='{self.status}' attempts={self.attempts}>"
