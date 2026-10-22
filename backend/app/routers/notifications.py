"""
Bildirishnomalar API
"""
from fastapi import APIRouter, Depends, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from typing import List, Optional
from datetime import datetime, timezone, timedelta

from app.core.database import get_db, AsyncSessionLocal
from app.core.security import get_current_user
from app.models.notification import Notification, NotificationTarget
from app.models.user import User, UserRole

router = APIRouter(prefix="/notifications", tags=["🔔 Bildirishnomalar"])

# -------------------------------------------------------------------
# 🧹 YORDAMCHI: Eski bildirishnomalarni o'chirish (Problem 10)
# -------------------------------------------------------------------
async def _cleanup_old_notifications(
    restaurant_id: int,
    days: int = 7,
) -> int:
    """
    O'qilgan va `days` kundan oshgan bildirishnomalarni bazadan o'chiradi.
    Bu funksiya BackgroundTasks orqali chaqiriladi — alohida AsyncSessionLocal ochadi.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    async with AsyncSessionLocal() as bg_db:
        result = await bg_db.execute(
            delete(Notification).where(
                Notification.restaurant_id == restaurant_id,
                Notification.is_read == True,
                Notification.created_at < cutoff,
            )
        )
        await bg_db.commit()
        return result.rowcount


# Har 50-so'rovdan birida eski bildirishnomalarni tozalash uchun counter
import random

@router.get("/", summary="Bildirishnomalar ro'yxati")
async def list_notifications(
    restaurant_id: int,
    background_tasks: BackgroundTasks,
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

    # 🧹 Avtomatik tozalash: har ~50-so'rovdan birida (2% ehtimollik)
    # Response ni bloklamaydi — fon jarayonida ishlaydi
    if random.random() < 0.02:
        background_tasks.add_task(_cleanup_old_notifications, restaurant_id)

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


@router.delete("/cleanup", summary="Eski bildirishnomalarni tozalash (Admin)")
async def cleanup_old_notifications(
    restaurant_id: int,
    days: int = Query(default=7, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Admin uchun: O'qilgan va `days` kundan oshgan bildirishnomalarni bazadan o'chiradi.
    Default: 7 kun. Max: 365 kun.
    Faqat admin yoki manager roli uchun.
    """
    if current_user.role not in (UserRole.ADMIN, UserRole.DEVELOPER):
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Faqat admin yoki manager tozalash huquqiga ega",
        )

    deleted_count = await _cleanup_old_notifications(restaurant_id, db, days=days)
    return {
        "success": True,
        "deleted": deleted_count,
        "message": f"{deleted_count} ta eski bildirishnoma o'chirildi",
    }
