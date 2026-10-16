"""
RestAron — Audit Log modeli (Audit trail)
Kassir va xodimlar harakatlari, to'lovlar, buyurtma o'zgarishlari va tizim
amallarini to'liq kuzatib borish uchun xavfsizlik jurnali.
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from app.core.database import Base


class AuditLog(Base):
    """Barcha muhim moliyaviy va ma'muriy operatsiyalar jurnali"""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    user_name = Column(String(100), nullable=True)
    user_role = Column(String(50), nullable=True)

    # Amal turi: order_checkout, order_cancelled, item_removed, debt_repaid, user_login, settings_changed
    action = Column(String(100), nullable=False, index=True)

    # Qaysi obyektga tegishli: "order", "table", "menu_item", "debt", "user"
    entity_type = Column(String(50), nullable=True, index=True)
    entity_id = Column(String(100), nullable=True)

    # Batafsil ma'lumotlar (JSON formatida: eski summa, yangi summa, sabab, to'lov usuli va b.)
    details = Column(JSON, nullable=True)

    # IP manzil
    ip_address = Column(String(50), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    def __repr__(self):
        return f"<AuditLog #{self.id} {self.action} by {self.user_name}>"
