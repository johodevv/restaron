"""
Restoran CRUD va sozlamalar API
"""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from pydantic import BaseModel, Field
from typing import Optional, List

from app.core.database import get_db
from app.core.security import require_role
from app.models.restaurant import Restaurant, RestaurantSettings, Theme, RestaurantTheme
from app.models.commission import CommissionLog
from app.models.order import Order, OrderStatus
from app.models.user import User

router = APIRouter(prefix="/restaurants", tags=["🏪 Restoran"])


class RestaurantCreate(BaseModel):
    name: str = Field(..., min_length=2)
    slug: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None


class RestaurantUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    logo_url: Optional[str] = None
    is_active: Optional[bool] = None


class SettingsUpdate(BaseModel):
    show_prices: Optional[bool] = None
    allow_orders: Optional[bool] = None
    allow_orders_from_qr: Optional[bool] = None
    allow_call_waiter: Optional[bool] = None
    allow_reviews: Optional[bool] = None
    language: Optional[str] = None
    service_fee_percent: Optional[float] = None
    receipt_header: Optional[str] = None
    receipt_footer: Optional[str] = None
    receipt_address: Optional[str] = None
    receipt_phone: Optional[str] = None
    receipt_wifi_pass: Optional[str] = None
    printer_paper_width: Optional[int] = None
    archive_retention_years: Optional[int] = None
    allow_debt_payment: Optional[bool] = None
    enable_telegram_notifications: Optional[bool] = None
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    enable_sms_reminders: Optional[bool] = None
    sms_provider_api_key: Optional[str] = None
    sms_template: Optional[str] = None



class ThemeSelect(BaseModel):
    theme_id: int
    slot: int = Field(..., ge=1, le=2)
    is_default: bool = False


@router.post("/", status_code=201, summary="Yangi restoran yaratish")
async def create_restaurant(
    payload: RestaurantCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("developer")),
):
    """Faqat developer yangi restoran qo'sha oladi"""
    # Slug tekshirish
    result = await db.execute(select(Restaurant).where(Restaurant.slug == payload.slug))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Bu slug allaqachon mavjud")

    restaurant = Restaurant(**payload.model_dump())
    db.add(restaurant)
    await db.flush()

    # Default sozlamalar
    settings_obj = RestaurantSettings(restaurant_id=restaurant.id)
    db.add(settings_obj)

    await db.flush()
    await db.refresh(restaurant)
    return {"id": restaurant.id, "name": restaurant.name, "slug": restaurant.slug}


@router.get("/", summary="Restoranlar ro'yxati")
async def list_restaurants(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("developer")),
):
    result = await db.execute(select(Restaurant).order_by(Restaurant.created_at.desc()))
    restaurants = result.scalars().all()
    return [
        {
            "id": r.id,
            "name": r.name,
            "slug": r.slug,
            "is_active": r.is_active,
            "total_revenue": r.total_revenue,
            "commission_percent": r.commission_percent,
            "created_at": r.created_at,
        }
        for r in restaurants
    ]


@router.get("/{restaurant_id}", summary="Restoran ma'lumoti")
async def get_restaurant(
    restaurant_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "developer")),
):
    result = await db.execute(
        select(Restaurant)
        .options(selectinload(Restaurant.settings))
        .where(Restaurant.id == restaurant_id)
    )
    r = result.scalar_one_or_none()
    if not r:
        raise HTTPException(status_code=404, detail="Restoran topilmadi")
    return r


@router.patch("/{restaurant_id}", summary="Restoran ma'lumotlarini yangilash")
async def update_restaurant(
    restaurant_id: int,
    payload: RestaurantUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "developer")),
):
    result = await db.execute(select(Restaurant).where(Restaurant.id == restaurant_id))
    r = result.scalar_one_or_none()
    if not r:
        raise HTTPException(status_code=404, detail="Restoran topilmadi")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(r, field, value)
    await db.flush()
    return {"success": True}


@router.patch("/{restaurant_id}/settings", summary="Restoran sozlamalari")
async def update_settings(
    restaurant_id: int,
    payload: SettingsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "developer")),
):
    result = await db.execute(
        select(RestaurantSettings).where(RestaurantSettings.restaurant_id == restaurant_id)
    )
    settings = result.scalar_one_or_none()
    if not settings:
        raise HTTPException(status_code=404, detail="Sozlamalar topilmadi")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(settings, field, value)
    await db.flush()
    return {"success": True}


@router.post("/{restaurant_id}/themes", summary="Tema tanlash")
async def select_theme(
    restaurant_id: int,
    payload: ThemeSelect,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "developer")),
):
    """Admin 2 ta slot uchun tema tanlaydi"""
    # Avvalgi slot tozalash
    result = await db.execute(
        select(RestaurantTheme).where(
            RestaurantTheme.restaurant_id == restaurant_id,
            RestaurantTheme.slot == payload.slot,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        await db.delete(existing)

    rt = RestaurantTheme(
        restaurant_id=restaurant_id,
        theme_id=payload.theme_id,
        slot=payload.slot,
        is_default=payload.is_default,
    )
    db.add(rt)
    await db.flush()
    return {"success": True, "slot": payload.slot, "theme_id": payload.theme_id}


# ─── Barcha Temalar ────────────────────────────────────
@router.get("/themes/all", summary="Mavjud temalar ro'yxati")
async def list_themes(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Theme).where(Theme.is_active == True))
    themes = result.scalars().all()
    return [
        {
            "id": t.id,
            "name": t.name,
            "slug": t.slug,
            "description": t.description,
            "preview_url": t.preview_url,
            "config": t.config,
        }
        for t in themes
    ]


# ─── Developer: Komissiya va Platforma Monitoringi ─────────
class CommissionPayRequest(BaseModel):
    amount: float
    note: Optional[str] = None


class CommissionRateUpdate(BaseModel):
    commission_percent: float = Field(..., ge=0.0, le=100.0)


@router.get("/commissions/summary", summary="Platforma komissiyalari xulosasi (Developer)")
async def get_commissions_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("developer")),
):
    """Barcha restoranlar bo'yicha umumiy aylanma va komissiyalar hisoboti"""
    restaurants_res = await db.execute(select(Restaurant).order_by(Restaurant.created_at.desc()))
    restaurants = restaurants_res.scalars().all()

    total_platform_revenue = 0.0
    total_platform_commission = 0.0
    total_paid_commission = 0.0

    breakdown = []
    for r in restaurants:
        # Ushbu restoran uchun buyurtmalar summasi
        rev_res = await db.execute(
            select(
                func.coalesce(func.sum(Order.total), 0.0),
                func.count(Order.id)
            ).where(
                Order.restaurant_id == r.id,
                Order.status.in_([OrderStatus.SERVED, OrderStatus.PAID]),
            )
        )
        rev_row = rev_res.first()
        r_revenue = float(rev_row[0]) if rev_row else 0.0
        r_orders = int(rev_row[1]) if rev_row else 0

        # Hisoblangan komissiya
        r_commission = r_revenue * (r.commission_percent / 100.0)

        # To'langan komissiya
        paid_res = await db.execute(
            select(func.coalesce(func.sum(CommissionLog.commission_amount), 0.0)).where(
                CommissionLog.restaurant_id == r.id,
                CommissionLog.is_paid == True
            )
        )
        r_paid = float(paid_res.scalar() or 0.0)

        total_platform_revenue += r_revenue
        total_platform_commission += r_commission
        total_paid_commission += r_paid

        breakdown.append({
            "id": r.id,
            "name": r.name,
            "slug": r.slug,
            "address": r.address,
            "phone": r.phone,
            "is_active": r.is_active,
            "commission_percent": r.commission_percent,
            "total_orders": r_orders,
            "total_revenue": r_revenue,
            "total_commission": r_commission,
            "paid_commission": r_paid,
            "pending_commission": max(0.0, r_commission - r_paid),
            "created_at": r.created_at,
        })

    return {
        "total_restaurants": len(restaurants),
        "total_platform_revenue": total_platform_revenue,
        "total_platform_commission": total_platform_commission,
        "total_paid_commission": total_paid_commission,
        "total_pending_commission": max(0.0, total_platform_commission - total_paid_commission),
        "restaurants": breakdown,
    }


@router.post("/{restaurant_id}/commission/pay", summary="Komissiya to'lovini qayd etish (Developer)")
async def record_commission_payment(
    restaurant_id: int,
    payload: CommissionPayRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("developer")),
):
    """Restoran dasturchiga komissiya to'laganini qayd qilish"""
    result = await db.execute(select(Restaurant).where(Restaurant.id == restaurant_id))
    restaurant = result.scalar_one_or_none()
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restoran topilmadi")

    now = datetime.now(timezone.utc)
    log = CommissionLog(
        restaurant_id=restaurant_id,
        period_start=restaurant.created_at or now,
        period_end=now,
        total_revenue=restaurant.total_revenue or 0.0,
        commission_percent=restaurant.commission_percent,
        commission_amount=payload.amount,
        total_orders=0,
        is_paid=True,
        paid_at=now,
        payment_note=payload.note or "Komissiya to'lovi qabul qilindi",
    )
    db.add(log)
    restaurant.total_commission = (restaurant.total_commission or 0.0) + payload.amount
    await db.flush()
    return {"success": True, "message": "Komissiya to'lovi muvaffaqiyatli qayd etildi"}


@router.patch("/{restaurant_id}/commission-rate", summary="Komissiya foizini o'zgartirish (Developer)")
async def update_commission_rate(
    restaurant_id: int,
    payload: CommissionRateUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("developer")),
):
    result = await db.execute(select(Restaurant).where(Restaurant.id == restaurant_id))
    restaurant = result.scalar_one_or_none()
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restoran topilmadi")

    restaurant.commission_percent = payload.commission_percent
    await db.flush()
    return {
        "success": True,
        "restaurant_id": restaurant_id,
        "new_commission_percent": payload.commission_percent
    }


@router.patch("/{restaurant_id}/toggle-status", summary="Restoran holatini yoqish/o'chirish (Developer)")
async def toggle_restaurant_status(
    restaurant_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("developer")),
):
    result = await db.execute(select(Restaurant).where(Restaurant.id == restaurant_id))
    restaurant = result.scalar_one_or_none()
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restoran topilmadi")

    restaurant.is_active = not restaurant.is_active
    await db.flush()
    return {
        "success": True,
        "restaurant_id": restaurant_id,
        "is_active": restaurant.is_active
    }

