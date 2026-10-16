"""
RestAron — Audit Log Helper
Kassir va xodimlar harakatlarini jurnalga qayd qilish yordamchi funksiyalari.
"""
import logging
from typing import Optional, Any, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Request
from app.models.audit_log import AuditLog
from app.models.user import User

logger = logging.getLogger("audit")


async def log_audit_event(
    db: AsyncSession,
    restaurant_id: int,
    action: str,
    user: Optional[User] = None,
    user_id: Optional[int] = None,
    user_name: Optional[str] = None,
    user_role: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[Any] = None,
    details: Optional[Dict[str, Any]] = None,
    request: Optional[Request] = None,
    ip_address: Optional[str] = None,
) -> Optional[AuditLog]:
    """
    Muhim amallarni AuditLog jadvaliga yozish.
    Xatolik yuz bersa asosiy tranzaksiyani to'xtatmaydi, logga yozadi.
    """
    try:
        ip = ip_address
        if not ip and request:
            from app.core.rate_limit import get_client_ip
            ip = get_client_ip(request)

        final_user_name = user_name or "System"
        final_user_role = user_role or "system"
        final_user_id = user_id

        if user:
            final_user_id = user.id
            final_user_name = user.full_name or user.username
            final_user_role = user.role.value if hasattr(user.role, "value") else str(user.role)

        audit_entry = AuditLog(
            restaurant_id=restaurant_id,
            user_id=final_user_id,
            user_name=final_user_name,
            user_role=final_user_role,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id is not None else None,
            details=details or {},
            ip_address=ip,
        )
        db.add(audit_entry)
        await db.flush()
        return audit_entry
    except Exception as e:
        logger.error(f"Audit log yozishda xatolik: {e}")
        return None
