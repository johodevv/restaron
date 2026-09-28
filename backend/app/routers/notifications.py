"""
Bildirishnomalar API
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from typing import List, Optional
from datetime import datetime, timezone

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.notification import Notification, NotificationTarget
from app.models.user import User, UserRole

router = APIRouter(prefix="/notifications", tags=["🔔 Bildirishnomalar"])


@router.get("/", summary="Bildirishnomalar ro'yxati")
async def list_notifications(
    restaurant_id: int,
    unread_only: bool = False,
    limit: int = Query(default=50, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Notification).where(
        Notification.restaurant_id == restaurant_id
    )

    # Rol bo'yicha filtr
    if current_user.role == UserRole.WAITER:
        query = query.where(
            Notification.target.in_([
                NotificationTarget.WAITER,
                NotificationTarget.ALL_STAFF,
            ])
        )
    elif current_user.role == UserRole.CHEF:
        query = query.where(
            Notification.target.in_([
                NotificationTarget.CHEF,
                NotificationTarget.ALL_STAFF,
            ])
        )

    if unread_only:
        query = query.where(Notification.is_read == False)

    query = query.order_by(Notification.created_at.desc()).limit(limit)
    result = await db.execute(query)
    notifications = result.scalars().all()

    return [
        {
            "id": n.id,
            "type": n.type,
            "title": n.title,
            "message": n.message,
            "data": n.data,
            "is_read": n.is_read,
            "created_at": n.created_at,
        }
        for n in notifications
    ]


@router.patch("/{notification_id}/read", summary="O'qildi deb belgilash")
async def mark_read(
    notification_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await db.execute(
        update(Notification)
        .where(Notification.id == notification_id)
        .values(is_read=True, read_at=datetime.now(timezone.utc))
    )
    return {"success": True}


@router.patch("/mark-all-read", summary="Hammasini o'qildi belgilash")
async def mark_all_read(
    restaurant_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await db.execute(
        update(Notification)
        .where(
            Notification.restaurant_id == restaurant_id,
            Notification.is_read == False,
        )
        .values(is_read=True, read_at=datetime.now(timezone.utc))
    )
    return {"success": True}
