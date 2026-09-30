"""
Cheklar Arxivi (3 yilgacha saqlash) va Smena Hisobotlari (X/Z Report) API
Xprinter uchun chek formatlash va qayta chop etish
"""
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from typing import List, Optional

from app.core.database import get_db
from app.core.security import require_role
from app.models.receipt import ReceiptArchive, ShiftReport
from app.models.order import Order, OrderStatus
from app.models.restaurant import Restaurant, RestaurantSettings
from app.models.user import User, UserRole
from app.schemas.receipt import (
    ReceiptArchiveResponse, ShiftReportCreate, ShiftReportResponse
)
from app.core.printer_service import (
    format_kitchen_ticket, format_pre_check, format_shift_report
)

router = APIRouter(prefix="/receipts", tags=["🖨️ Cheklar Arxivi va Kassa Hisobotlari"])


@router.get("/", response_model=List[ReceiptArchiveResponse], summary="Cheklar arxivi ro'yxati (3 yil)")
async def list_receipts(
    restaurant_id: int,
    receipt_type: Optional[str] = Query(None, description="kitchen, pre_check, final_bill"),
    payment_method: Optional[str] = Query(None, description="cash, card, click, debt"),
    search: Optional[str] = Query(None, description="Chek raqami, stol yoki ofitsiant ismi"),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "waiter", "developer")),
):
    """Arxivdagi cheklarni qidirish va filtrlash"""
    query = select(ReceiptArchive).where(ReceiptArchive.restaurant_id == restaurant_id)

    if receipt_type:
        query = query.where(ReceiptArchive.receipt_type == receipt_type)

    if payment_method:
        query = query.where(ReceiptArchive.payment_method == payment_method)

    if start_date:
        query = query.where(ReceiptArchive.created_at >= start_date)

    if end_date:
        query = query.where(ReceiptArchive.created_at <= end_date)

    if search:
        s_fmt = f"%{search.strip()}%"
        query = query.where(
            or_(
                ReceiptArchive.receipt_number.ilike(s_fmt),
                ReceiptArchive.table_name.ilike(s_fmt),
                ReceiptArchive.waiter_name.ilike(s_fmt),
                ReceiptArchive.hall_name.ilike(s_fmt),
            )
        )

    query = query.order_by(ReceiptArchive.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    receipts = result.scalars().all()
    return receipts


@router.get("/{receipt_id}", response_model=ReceiptArchiveResponse, summary="Alohida chek tafsilotlari")
async def get_receipt(
    receipt_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "waiter", "developer")),
):
    result = await db.execute(select(ReceiptArchive).where(ReceiptArchive.id == receipt_id))
    r = result.scalar_one_or_none()
    if not r:
        raise HTTPException(status_code=404, detail="Chek topilmadi")
    return r


@router.post("/{receipt_id}/reprint", summary="Chekni qayta chop etish (Xprinter matni)")
async def reprint_receipt(
    receipt_id: int,
    paper_width: Optional[int] = Query(None, description="58 yoki 80 mm"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "waiter", "developer")),
):
    """Xprinter uchun chek matnini qayta yuklab berish"""
    result = await db.execute(select(ReceiptArchive).where(ReceiptArchive.id == receipt_id))
    r = result.scalar_one_or_none()
    if not r:
        raise HTTPException(status_code=404, detail="Chek topilmadi")

    return {
        "receipt_id": r.id,
        "receipt_number": r.receipt_number,
        "receipt_type": r.receipt_type,
        "raw_text": r.raw_text,
        "items": r.items_json,
        "total": r.total_amount,
        "created_at": r.created_at,
    }


# ─── Smena hisoboti (X-Report va Z-Report) ──────────────────────
@router.post("/shift-report", response_model=ShiftReportResponse, summary="Kassa smena hisobotini yaratish (X/Z Report)")
async def create_shift_report(
    payload: ShiftReportCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "developer")),
):
    """
    X-Report: Joriy smenadagi oraliq hisobot
    Z-Report: Kunlik kassani yopish va Z-hisobot chekini chiqarish
    """
    restaurant_id = payload.restaurant_id

    # Restoran ma'lumotlarini olish
    rest_res = await db.execute(select(Restaurant).where(Restaurant.id == restaurant_id))
    restaurant = rest_res.scalar_one_or_none()
    rest_name = restaurant.name if restaurant else "RestAron"

    set_res = await db.execute(select(RestaurantSettings).where(RestaurantSettings.restaurant_id == restaurant_id))
    settings = set_res.scalar_one_or_none()
    paper_width = settings.printer_paper_width if settings else 80

    # Oxirgi yopilgan Z-Reportni topish (smena ochilgan vaqtini aniqlash uchun)
    last_z = await db.execute(
        select(ShiftReport)
        .where(ShiftReport.restaurant_id == restaurant_id, ShiftReport.report_type == "z_report", ShiftReport.is_closed == True)
        .order_by(ShiftReport.created_at.desc())
    )
    prev_shift = last_z.scalars().first()
    opened_at = prev_shift.closed_at if prev_shift else datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    now_dt = datetime.now(timezone.utc)

    # Smena soni
    shift_count_res = await db.execute(
        select(func.count(ShiftReport.id)).where(ShiftReport.restaurant_id == restaurant_id, ShiftReport.report_type == "z_report")
    )
    shift_number = (shift_count_res.scalar() or 0) + 1

    # Ushbu smenada yopilgan buyurtmalarni olish
    orders_res = await db.execute(
        select(Order).where(
            Order.restaurant_id == restaurant_id,
            Order.status.in_([OrderStatus.PAID, OrderStatus.SERVED]),
            Order.created_at >= opened_at,
        )
    )
    orders = orders_res.scalars().all()

    total_orders = len(orders)
    total_sales = 0.0
    total_cash = 0.0
    total_card = 0.0
    total_click = 0.0
    total_debt = 0.0
    total_service_fee = 0.0
    total_waiter_earnings = 0.0

    waiter_map = {}
    items_map = {}

    for o in orders:
        total_sales += o.total or 0.0
        total_cash += o.cash_amount or 0.0
        total_card += o.card_amount or 0.0
        total_click += o.click_amount or 0.0
        total_debt += o.debt_amount or 0.0
        total_service_fee += o.service_fee_amount or 0.0
        total_waiter_earnings += o.waiter_share_amount or 0.0

        if o.waiter_id:
            w_id = o.waiter_id
            if w_id not in waiter_map:
                waiter_map[w_id] = {
                    "waiter_id": w_id,
                    "name": o.waiter.full_name if o.waiter else f"Ofitsiant #{w_id}",
                    "sales": 0.0,
                    "orders_count": 0,
                    "earning": 0.0,
                }
            waiter_map[w_id]["sales"] += o.total or 0.0
            waiter_map[w_id]["orders_count"] += 1
            waiter_map[w_id]["earning"] += o.waiter_share_amount or 0.0

    waiter_breakdown = list(waiter_map.values())

    # Xprinter uchun hisobot chekini formatlash
    raw_text = format_shift_report(
        report_type=payload.report_type,
        restaurant_name=rest_name,
        shift_number=shift_number,
        cashier_name=current_user.full_name or current_user.username,
        opened_at=opened_at,
        closed_at=now_dt,
        total_orders=total_orders,
        total_sales=total_sales,
        total_cash=total_cash,
        total_card=total_card,
        total_click=total_click,
        total_debt=total_debt,
        total_service_fee=total_service_fee,
        total_waiter_earnings=total_waiter_earnings,
        waiter_breakdown=waiter_breakdown,
        paper_width=paper_width,
    )

    shift_report = ShiftReport(
        restaurant_id=restaurant_id,
        cashier_user_id=current_user.id,
        shift_number=shift_number,
        report_type=payload.report_type,
        opened_at=opened_at,
        closed_at=now_dt if payload.close_shift else None,
        total_orders=total_orders,
        total_sales=total_sales,
        total_cash=total_cash,
        total_card=total_card,
        total_click=total_click,
        total_debt=total_debt,
        total_service_fee=total_service_fee,
        total_waiter_earnings=total_waiter_earnings,
        waiter_breakdown=waiter_breakdown,
        items_breakdown=items_map,
        is_closed=payload.close_shift,
    )
    db.add(shift_report)
    await db.flush()
    await db.refresh(shift_report)

    # Shuningdek cheklar arxiviga ham kiritish
    rec_archive = ReceiptArchive(
        restaurant_id=restaurant_id,
        receipt_number=f"SHIFT-{payload.report_type.upper()}-{shift_number}",
        receipt_type=payload.report_type,
        waiter_name=current_user.full_name,
        subtotal=total_sales - total_service_fee,
        service_fee_percent=0.0,
        service_fee_amount=total_service_fee,
        total_amount=total_sales,
        payment_method="summary",
        cash_amount=total_cash,
        card_amount=total_card,
        click_amount=total_click,
        debt_amount=total_debt,
        items_json={"waiters": waiter_breakdown},
        raw_text=raw_text,
    )
    db.add(rec_archive)
    await db.flush()

    res = ShiftReportResponse.model_validate(shift_report)
    res.raw_text = raw_text
    return res


@router.get("/shift-reports/all", response_model=List[ShiftReportResponse], summary="Barcha smena hisobotlari")
async def list_shift_reports(
    restaurant_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "developer")),
):
    result = await db.execute(
        select(ShiftReport)
        .where(ShiftReport.restaurant_id == restaurant_id)
        .order_by(ShiftReport.created_at.desc())
        .limit(30)
    )
    return result.scalars().all()
