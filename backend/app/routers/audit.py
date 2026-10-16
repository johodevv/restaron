"""
Audit Log API — Xodimlar va tizim harakatlari jurnali (Admin / Developer)
"""
from datetime import datetime
from typing import List, Optional, Any, Dict
from pydantic import BaseModel
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.core.security import require_role
from app.models.user import User
from app.models.audit_log import AuditLog

router = APIRouter(prefix="/audit-logs", tags=["📜 Audit Log"])


class AuditLogResponse(BaseModel):
    id: int
    restaurant_id: int
    user_id: Optional[int] = None
    user_name: Optional[str] = None
    user_role: Optional[str] = None
    action: str
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/", response_model=List[AuditLogResponse], summary="Audit loglar ro'yxati (filtrlash va pagination bilan)")
async def list_audit_logs(
    restaurant_id: int,
    action: Optional[str] = None,
    entity_type: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "developer")),
):
    """
    Kassir va xodimlar bajargan barcha amallar (to'lovlar, bekor qilishlar, o'zgartirishlar) jurnali.
    """
    query = (
        select(AuditLog)
        .where(AuditLog.restaurant_id == restaurant_id)
    )

    if action:
        query = query.where(AuditLog.action == action)
    if entity_type:
        query = query.where(AuditLog.entity_type == entity_type)

    query = query.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()
