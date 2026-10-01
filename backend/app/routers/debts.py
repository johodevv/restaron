"""
Qarzlar va Nasiya Daftari API — Admin va Ofitsiant
Qarzdorlarni boshqarish, to'lov qabul qilish va SMS eslatmalar yuborish
"""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from typing import List, Optional

from app.core.database import get_db
from app.core.security import require_role
from app.models.debt import Debt
from app.models.restaurant import Restaurant, RestaurantSettings
from app.models.user import User
from app.schemas.debt import (
    DebtCreate, DebtUpdate, DebtPayment,
    DebtResponse, DebtStatsResponse, SendSMSRequest
)
from app.core.sms_telegram import send_sms

router = APIRouter(prefix="/debts", tags=["📒 Qarzlar (Nasiya Daftari)"])


@router.get("/", response_model=List[DebtResponse], summary="Qarzlar ro'yxati")
async def list_debts(
    restaurant_id: int,
    status_filter: Optional[str] = Query(None, description="unpaid, partially_paid, paid"),
    search: Optional[str] = Query(None, description="Mijoz ismi yoki telefon raqami"),
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "waiter", "developer")),
):
    """Qarzlar ro'yxatini filtrlash va qidirish bilan olish"""
    query = select(Debt).where(Debt.restaurant_id == restaurant_id)

    if status_filter:
        query = query.where(Debt.status == status_filter)

    if search:
        search_fmt = f"%{search.strip()}%"
        query = query.where(
            or_(
                Debt.customer_name.ilike(search_fmt),
                Debt.customer_phone.ilike(search_fmt)
            )
        )

    query = query.order_by(Debt.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    debts = result.scalars().all()
    return debts


@router.get("/stats", response_model=DebtStatsResponse, summary="Qarzlar bo'yicha umumiy statistika")
async def get_debt_stats(
    restaurant_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "developer")),
):
    """Umumiy qarz summasi, yig'ilgan summa va qarzdorlar soni"""
    res = await db.execute(
        select(
            func.coalesce(func.sum(Debt.amount), 0.0),
            func.coalesce(func.sum(Debt.paid_amount), 0.0),
            func.coalesce(func.sum(Debt.remaining_amount), 0.0),
            func.count(Debt.id).filter(Debt.status != "paid"),
            func.count(Debt.id).filter(Debt.status == "paid"),
        ).where(Debt.restaurant_id == restaurant_id)
    )
    total_amount, total_paid, total_remaining, unpaid_count, paid_count = res.one()

    return DebtStatsResponse(
        total_debt_amount=float(total_amount),
        total_paid_amount=float(total_paid),
        total_remaining_amount=float(total_remaining),
        unpaid_count=int(unpaid_count or 0),
        paid_count=int(paid_count or 0),
    )


@router.post("/", response_model=DebtResponse, status_code=201, summary="Yangi qarz qo'shish")
async def create_debt(
    payload: DebtCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "waiter", "developer")),
):
    """Yangi qarzdor qaydini yaratish"""
    debt = Debt(
        restaurant_id=payload.restaurant_id,
        order_id=payload.order_id,
        customer_name=payload.customer_name,
        customer_phone=payload.customer_phone,
        amount=payload.amount,
        paid_amount=0.0,
        remaining_amount=payload.amount,
        status="unpaid",
        due_date=payload.due_date,
        note=payload.note,
    )
    db.add(debt)
    await db.flush()
    await db.refresh(debt)
    return debt


@router.get("/{debt_id}", response_model=DebtResponse, summary="Alohida qarz ma'lumoti")
async def get_debt(
    debt_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "waiter", "developer")),
):
    result = await db.execute(select(Debt).where(Debt.id == debt_id))
    debt = result.scalar_one_or_none()
    if not debt:
        raise HTTPException(status_code=404, detail="Qarz topilmadi")
    return debt


@router.patch("/{debt_id}/pay", response_model=DebtResponse, summary="Qarzni to'lash (qisman yoki to'liq)")
async def pay_debt(
    debt_id: int,
    payload: DebtPayment,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "waiter", "developer")),
):
    """Qarzga to'lov kiritish"""
    result = await db.execute(select(Debt).where(Debt.id == debt_id))
    debt = result.scalar_one_or_none()
    if not debt:
        raise HTTPException(status_code=404, detail="Qarz topilmadi")

    if debt.status == "paid":
        raise HTTPException(status_code=400, detail="Bu qarz allaqachon to'liq yopilgan")

    # Qarzdan ortiq to'lovni qabul qilmaymiz — aks holda `paid_amount`
    # qarz summasidan oshib ketadi va nasiya kitobi hisobotlari buziladi.
    outstanding = max(0.0, (debt.amount or 0.0) - (debt.paid_amount or 0.0))
    if payload.payment_amount - outstanding > 0.01:
        raise HTTPException(
            status_code=400,
            detail=(
                f"To'lov qarzdan ko'p: {payload.payment_amount:,.0f} so'm kiritildi, "
                f"qolgan qarz {outstanding:,.0f} so'm."
            ),
        )

    debt.paid_amount = round(min(debt.amount or 0.0, (debt.paid_amount or 0.0) + payload.payment_amount), 2)
    debt.remaining_amount = round(max(0.0, (debt.amount or 0.0) - debt.paid_amount), 2)

    if debt.remaining_amount <= 0:
        debt.status = "paid"
    else:
        debt.status = "partially_paid"

    if payload.note:
        old_note = debt.note or ""
        debt.note = f"{old_note} | To'lov: +{payload.payment_amount:,.0f} ({payload.note})"

    await db.flush()
    await db.refresh(debt)
    return debt


@router.post("/{debt_id}/send-sms", summary="Qarzdorga SMS eslatma yuborish")
async def send_debt_sms(
    debt_id: int,
    payload: Optional[SendSMSRequest] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "developer")),
):
    """Admin qarzdorning telefon raqamiga eslatma SMS yuboradi"""
    result = await db.execute(select(Debt).where(Debt.id == debt_id))
    debt = result.scalar_one_or_none()
    if not debt:
        raise HTTPException(status_code=404, detail="Qarz topilmadi")

    # Restoran sozlamalarini olish (SMS shabloni va API kaliti)
    set_res = await db.execute(
        select(RestaurantSettings).where(RestaurantSettings.restaurant_id == debt.restaurant_id)
    )
    settings = set_res.scalar_one_or_none()

    rest_res = await db.execute(select(Restaurant).where(Restaurant.id == debt.restaurant_id))
    restaurant = rest_res.scalar_one_or_none()
    rest_name = restaurant.name if restaurant else "RestAron"

    # SMS matnini shakllantirish
    if payload and payload.custom_message:
        sms_text = payload.custom_message
    elif settings and settings.sms_template:
        due_str = debt.due_date.strftime("%d.%m.%Y") if debt.due_date else "eng qisqa vaqt"
        sms_text = settings.sms_template.format(
            name=debt.customer_name,
            restaurant=rest_name,
            amount=f"{debt.remaining_amount:,.0f}".replace(",", " "),
            due_date=due_str,
        )
    else:
        sms_text = f"Hurmatli {debt.customer_name}, {rest_name} restoranidagi {debt.remaining_amount:,.0f} so'm qarzingizni to'lashingizni so'raymiz."

    api_key = settings.sms_provider_api_key if settings else None
    sms_res = await send_sms(phone=debt.customer_phone, message=sms_text, api_key=api_key)

    debt.last_sms_sent_at = datetime.now(timezone.utc)
    debt.sms_count = (debt.sms_count or 0) + 1
    await db.flush()

    return {
        "success": sms_res.get("success", True),
        "phone": debt.customer_phone,
        "sms_count": debt.sms_count,
        "message_sent": sms_text,
        "details": sms_res,
    }


@router.delete("/{debt_id}", status_code=204, summary="Qarzni o'chirish")
async def delete_debt(
    debt_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "developer")),
):
    result = await db.execute(select(Debt).where(Debt.id == debt_id))
    debt = result.scalar_one_or_none()
    if not debt:
        raise HTTPException(status_code=404, detail="Qarz topilmadi")
    await db.delete(debt)
