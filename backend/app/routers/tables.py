"""
Stollar API â€” QR kod generatsiya bilan
"""
import os
import uuid
import random
import qrcode
import aiofiles
from io import BytesIO
from datetime import datetime, timezone
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List, Optional

from app.core.database import get_db
from app.core.security import require_role
from app.core.config import settings
from app.models.table import Table, TableStatus
from app.models.user import User, UserRole
from app.models.order import Order, OrderItem, OrderStatus, CallStatus
from app.models.restaurant import Restaurant, RestaurantSettings
from app.models.receipt import ReceiptArchive
from app.core.printer_service import format_pre_check, print_to_windows_printer
from app.schemas.table import TableCreate, TableUpdate, TableResponse, TablePublic
from app.schemas.order import TableBillResponse, BillItemSummary
from app.websockets.manager import manager

router = APIRouter(prefix="/tables", tags=["ðŸª‘ Stollar"])


def get_qr_base_url() -> str:
    """QR uchun ishlatilgan base URL ni aniqlash.
    SERVER_ONLINE_URL.txt mavjud bo'lsa (Cloudflare tunnel aktiv), uni ishlatadi.
    Aks holda settings.QR_BASE_URL ni ishlatadi."""
    # SERVER_ONLINE_URL.txt ni 3 ta mumkin yo'ldan qidirish
    possible_paths = [
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "SERVER_ONLINE_URL.txt")),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "SERVER_ONLINE_URL.txt")),
        os.path.abspath("SERVER_ONLINE_URL.txt"),
    ]
    for p in possible_paths:
        if os.path.exists(p):
            try:
                val = open(p, "r", encoding="utf-8").read().strip()
                if val.startswith("http"):
                    return val.rstrip("/")
            except Exception:
                pass
    return settings.QR_BASE_URL.rstrip("/")


def generate_qr_image(url: str, token: str) -> str:
    """QR kod rasm yaratish va saqlash"""
    upload_dir = os.path.join(settings.UPLOAD_DIR, "qr_codes")
    os.makedirs(upload_dir, exist_ok=True)

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    file_name = f"{token}.png"
    file_path = os.path.join(upload_dir, file_name)
    img.save(file_path)

    return f"/uploads/qr_codes/{file_name}"


@router.post(
    "/",
    response_model=TableResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Yangi stol qo'shish",
)
async def create_table(
    payload: TableCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "developer")),
):
    """Yangi stol yaratish va avtomatik QR kod generatsiya"""
    result = await db.execute(
        select(Table).where(
            Table.restaurant_id == payload.restaurant_id,
            Table.number == payload.number,
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail=f"#{payload.number} raqamli stol allaqachon mavjud",
        )

    qr_token = str(uuid.uuid4())
    qr_url = f"{get_qr_base_url()}/?table={qr_token}"
    qr_image_url = generate_qr_image(qr_url, qr_token)

    table = Table(
        restaurant_id=payload.restaurant_id,
        number=payload.number,
        name=payload.name,
        room=payload.room,
        capacity=payload.capacity,
        qr_token=qr_token,
        qr_image_url=qr_image_url,
    )
    db.add(table)
    await db.flush()
    await db.refresh(table)
    return TableResponse.model_validate(table)


@router.get("/", response_model=List[TableResponse], summary="Stollar ro'yxati")
async def list_tables(
    restaurant_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "waiter", "developer")),
):
    result = await db.execute(
        select(Table)
        .where(Table.restaurant_id == restaurant_id)
        .order_by(Table.number)
    )
    tables = result.scalars().all()
    return [TableResponse.model_validate(t) for t in tables]


@router.get("/scan/{qr_token}", response_model=TablePublic, summary="QR kodni skanerlash")
async def scan_qr(qr_token: str, db: AsyncSession = Depends(get_db)):
    # 1. QR token bo'yicha qidirish
    result = await db.execute(
        select(Table).where(Table.qr_token == qr_token, Table.is_active == True)
    )
    table = result.scalar_one_or_none()

    # 2. Agar topilmasa va raqamli bo'lsa, stol raqami yoki ID bo'yicha topish
    if not table and qr_token.isdigit():
        num = int(qr_token)
        result = await db.execute(
            select(Table).where((Table.number == num) | (Table.id == num), Table.is_active == True)
        )
        table = result.scalar_one_or_none()

    if not table:
        raise HTTPException(status_code=404, detail="QR kod yaroqsiz yoki stol faol emas")

    # Sozlamalarni tekshirish: direct_qr_access (ruxsatsiz to'g'ridan-to'g'ri kirish)
    from app.models.restaurant import RestaurantSettings
    set_res = await db.execute(select(RestaurantSettings).where(RestaurantSettings.restaurant_id == table.restaurant_id))
    settings = set_res.scalar_one_or_none()
    direct_access = getattr(settings, "direct_qr_access", True) if settings else True

    needs_broadcast = False
    if not table.is_unlocked or table.status == TableStatus.AVAILABLE or table.status == "available":
        table.status = TableStatus.OCCUPIED
        if direct_access:
            table.is_unlocked = True
        else:
            table.current_pin = f"{random.randint(1000, 9999)}"
            table.is_unlocked = False
        needs_broadcast = True

    await db.flush()
    await db.commit()

    if needs_broadcast:
        # Real-time WebSocket orqali Admin va Ofitsiantga xabar berish
        await manager.broadcast_to_roles(
            table.restaurant_id,
            ["admin", "waiter"],
            {
                "type": "table_guest_arrived",
                "table_id": table.id,
                "table_number": table.number,
                "room": table.room,
                "pin": table.current_pin,
                "message": f"ðŸ”” Stol #{table.number} ga yangi mijoz keldi! Tasdiqlash kodi: {table.current_pin}",
            },
        )
        await manager.broadcast_to_roles(
            table.restaurant_id,
            ["admin", "waiter"],
            {
                "type": "table_status_updated",
                "table_id": table.id,
                "table_number": table.number,
                "status": TableStatus.OCCUPIED.value,
                "new_status": TableStatus.OCCUPIED.value,
                "message": f"Stol #{table.number} band qilindi",
            },
        )

    res = TablePublic.model_validate(table)
    res.pin = table.current_pin
    res.current_pin = table.current_pin
    res.is_unlocked = bool(table.is_unlocked)
    return res


@router.post("/{table_id}/unlock", summary="Ofitsiant tomonidan stolni tasdiqlash / faollashtirish")
async def unlock_table(table_id: int, db: AsyncSession = Depends(get_db)):
    """Ofitsiant stolga borib kodni ko'rib stolni faollashtiradi"""
    result = await db.execute(select(Table).where(Table.id == table_id))
    table = result.scalar_one_or_none()
    if not table:
        raise HTTPException(status_code=404, detail="Stol topilmadi")

    table.is_unlocked = True
    table.status = TableStatus.OCCUPIED
    await db.flush()
    await db.commit()

    # Barcha mijoz va xodimlarga e'lon qilish
    await manager.broadcast_to_restaurant(
        table.restaurant_id,
        {
            "type": "table_unlocked",
            "table_id": table.id,
            "table_number": table.number,
            "message": f"Stol #{table.number} ofitsiant tomonidan faollashtirildi!",
        },
    )
    return {"status": "success", "message": f"Stol #{table.number} muvaffaqiyatli ochildi", "is_unlocked": True}


@router.post("/{table_id}/lock", summary="Stolni qayta qulflash va yangi PIN berish")
async def lock_table(
    table_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("waiter", "admin", "developer")),
):
    """Ofitsiant yoki Admin stolni qayta bloklaydi va yangi PIN generatsiya qiladi"""
    result = await db.execute(select(Table).where(Table.id == table_id))
    table = result.scalar_one_or_none()
    if not table:
        raise HTTPException(status_code=404, detail="Stol topilmadi")

    table.is_unlocked = False
    table.current_pin = f"{random.randint(1000, 9999)}"
    await db.flush()
    await db.commit()

    await manager.broadcast_to_restaurant(
        table.restaurant_id,
        {
            "type": "table_status_updated",
            "table_id": table.id,
            "table_number": table.number,
            "is_unlocked": False,
            "pin": table.current_pin,
            "message": f"Stol #{table.number} qayta qulflandi. Yangi kod: {table.current_pin}",
        },
    )
    return {"status": "success", "message": f"Stol #{table.number} qulflandi", "pin": table.current_pin, "is_unlocked": False}



@router.get("/{table_id}/bill", response_model=TableBillResponse, summary="Stol hisobi (Chek)")
async def get_table_bill(table_id: int, db: AsyncSession = Depends(get_db)):
    """Mijoz, Ofitsiant yoki Admin stol hisobi va chekini ko'radi"""
    result = await db.execute(
        select(Table)
        .options(selectinload(Table.restaurant))
        .where(Table.id == table_id)
    )
    table = result.scalar_one_or_none()
    if not table:
        raise HTTPException(status_code=404, detail="Stol topilmadi")

    # Ushbu stoldagi faol / so'nggi to'lanmagan buyurtmalar (yoki joriy sessiya)
    order_res = await db.execute(
        select(Order)
        .options(
            selectinload(Order.items).selectinload(OrderItem.menu_item),
            selectinload(Order.waiter),
        )
        .where(
            Order.table_id == table.id,
            Order.status != OrderStatus.CANCELLED,
            Order.is_paid == False,
        )
        .order_by(Order.created_at.asc())
    )
    orders = order_res.scalars().all()

    # Agar to'lanmagan faol buyurtma bo'lmasa, so'nggi sessiya buyurtmalarini ko'rsatish
    if not orders:
        recent_res = await db.execute(
            select(Order)
            .options(
                selectinload(Order.items).selectinload(OrderItem.menu_item),
                selectinload(Order.waiter),
            )
            .where(
                Order.table_id == table.id,
                Order.status != OrderStatus.CANCELLED,
            )
            .order_by(Order.created_at.desc())
            .limit(1)
        )
        last_order = recent_res.scalars().first()
        if last_order:
            orders = [last_order]

    # Itemlarni guruhlash
    items_map = {}
    subtotal = 0.0
    order_numbers = []
    waiter_names = set()
    earliest_time = None
    is_all_paid = len(orders) > 0 and all(o.is_paid for o in orders)

    for o in orders:
        order_numbers.append(o.order_number)
        if o.waiter:
            waiter_names.add(o.waiter.full_name or o.waiter.username)
        if not earliest_time or (o.created_at and o.created_at < earliest_time):
            earliest_time = o.created_at

        for item in o.items:
            m_id = item.menu_item_id
            name = item.menu_item.name if item.menu_item else f"Taom #{m_id}"
            if m_id not in items_map:
                items_map[m_id] = {
                    "menu_item_id": m_id,
                    "name": name,
                    "quantity": 0,
                    "unit_price": item.unit_price,
                    "total_price": 0.0,
                    "special_notes": [],
                }
            items_map[m_id]["quantity"] += item.quantity
            items_map[m_id]["total_price"] += item.total_price
            if item.special_note:
                items_map[m_id]["special_notes"].append(item.special_note)
            subtotal += item.total_price

    service_fee_percent = 10.0
    service_fee_amount = round(subtotal * (service_fee_percent / 100.0), 2)
    grand_total = subtotal + service_fee_amount

    restaurant = table.restaurant
    restaurant_name = restaurant.name if restaurant else "RestAron"
    restaurant_phone = restaurant.phone if restaurant else None
    restaurant_address = restaurant.address if restaurant else None

    items_list = [BillItemSummary(**v) for v in items_map.values()]
    waiter_display = ", ".join(waiter_names) if waiter_names else None

    return TableBillResponse(
        table_id=table.id,
        table_number=table.number,
        room=table.room,
        restaurant_name=restaurant_name,
        restaurant_phone=restaurant_phone,
        restaurant_address=restaurant_address,
        status=table.status.value if hasattr(table.status, "value") else str(table.status),
        waiter_name=waiter_display,
        orders_count=len(orders),
        order_numbers=order_numbers,
        items=items_list,
        subtotal=subtotal,
        service_fee_percent=service_fee_percent,
        service_fee_amount=service_fee_amount,
        discount=0.0,
        grand_total=grand_total,
        has_active_orders=len(orders) > 0,
        is_paid=is_all_paid,
        created_at=earliest_time or table.created_at,
    )


class TableCheckoutRequest(BaseModel):
    """Stolni yopishda to'lov turi (ko'rsatilmasa — naqd)"""
    payment_method: str = "cash"


@router.post("/{table_id}/checkout", response_model=TableResponse, summary="Stolni hisob-kitob qilish va bo'shatish")
async def checkout_table(
    table_id: int,
    payload: Optional[TableCheckoutRequest] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("waiter", "admin", "developer")),
):
    """Admin yoki ofitsiant stol hisobini yopadi, buyurtmalarni to'langan deb belgilaydi va stolni bo'shatadi"""
    result = await db.execute(select(Table).where(Table.id == table_id))
    table = result.scalar_one_or_none()
    if not table:
        raise HTTPException(status_code=404, detail="Stol topilmadi")

    method = (payload.payment_method if payload else "cash") or "cash"
    if method not in ("cash", "card", "click"):
        raise HTTPException(
            status_code=400,
            detail="Stolni yopishda faqat naqd, karta yoki Click qabul qilinadi. "
                   "Nasiya uchun buyurtma kassasidan (checkout) foydalaning.",
        )

    set_res = await db.execute(
        select(RestaurantSettings).where(RestaurantSettings.restaurant_id == table.restaurant_id)
    )
    rest_settings = set_res.scalar_one_or_none()
    default_fee = rest_settings.service_fee_percent if rest_settings else 12.0

    # Ushbu stoldagi barcha to'lanmagan faol buyurtmalarni PAID qilish
    orders_res = await db.execute(
        select(Order)
        .options(selectinload(Order.items))
        .where(
            Order.table_id == table.id,
            Order.is_paid == False,
            Order.status != OrderStatus.CANCELLED,
        )
    )
    active_orders = orders_res.scalars().all()
    closed_at = datetime.now(timezone.utc)
    for o in active_orders:
        # Summalarni qayta hisoblaymiz — hisobot va kassa mos kelishi uchun
        subtotal = sum(i.total_price or 0.0 for i in o.items)
        fee_pct = o.service_fee_percent if o.service_fee_percent is not None else default_fee
        fee_amount = round(subtotal * ((fee_pct or 0.0) / 100.0), 2)
        total = round(max(0.0, subtotal + fee_amount - (o.discount or 0.0)), 2)

        o.subtotal = subtotal
        o.service_fee_percent = fee_pct
        o.service_fee_amount = fee_amount
        o.total = total

        # To'lovni kassaga yozamiz — aks holda buyurtma "to'langan" bo'lib
        # ko'rinadi, lekin to'lovlar hisobotida 0 so'm bo'lib qoladi.
        o.payment_method = method
        o.cash_amount = total if method == "cash" else 0.0
        o.card_amount = total if method == "card" else 0.0
        o.click_amount = total if method == "click" else 0.0
        o.debt_amount = 0.0

        o.is_paid = True
        o.status = OrderStatus.PAID
        o.closed_at = closed_at
        if o.call_waiter:
            o.call_waiter = False
            o.call_status = CallStatus.COMPLETED

    table.status = TableStatus.AVAILABLE
    table.is_unlocked = False
    table.current_pin = None
    await db.flush()
    await db.commit()

    # Real-time WebSocket orqali xabar
    await manager.broadcast_to_restaurant(
        table.restaurant_id,
        {
            "type": "table_cleared",
            "table_id": table.id,
            "table_number": table.number,
            "status": TableStatus.AVAILABLE.value,
            "new_status": TableStatus.AVAILABLE.value,
            "message": f"Stol #{table.number} hisobi yopildi va bo'shatildi",
        },
    )

    # Mijoz stoliga xabar
    await manager.broadcast_to_table(
        table.restaurant_id,
        table.id,
        {
            "type": "bill_paid",
            "table_id": table.id,
            "table_number": table.number,
            "message": "To'lovingiz qabul qilindi. Tashrifingiz uchun rahmat!",
        },
    )

    return TableResponse.model_validate(table)


@router.post("/{table_id}/print-bill", summary="Stol hisob chekini Printer 1 ga chop etish (Kassa / Mijoz)")
async def print_table_bill(
    table_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("waiter", "admin", "developer")),
):
    """Admin yoki ofitsiant stol hisob chekini (1-Printer: Mijoz cheki) to'g'ridan-to'g'ri chop etadi"""
    result = await db.execute(
        select(Table)
        .options(selectinload(Table.restaurant))
        .where(Table.id == table_id)
    )
    table = result.scalar_one_or_none()
    if not table:
        raise HTTPException(status_code=404, detail="Stol topilmadi")

    # Sozlamalarni olish
    s_res = await db.execute(
        select(RestaurantSettings).where(RestaurantSettings.restaurant_id == table.restaurant_id)
    )
    settings = s_res.scalar_one_or_none()
    cust_printer = getattr(settings, "printer_customer_name", None) or "X-Q80A"
    cp = getattr(settings, "printer_codepage", None) or 17
    paper_width = getattr(settings, "printer_paper_width", 80) or 80

    # Buyurtmalarni olish
    orders_res = await db.execute(
        select(Order)
        .options(
            selectinload(Order.items).selectinload(OrderItem.menu_item),
            selectinload(Order.waiter),
        )
        .where(
            Order.table_id == table.id,
            Order.status != OrderStatus.CANCELLED,
        )
        .order_by(Order.created_at.desc())
    )
    orders = orders_res.scalars().all()
    if not orders:
        raise HTTPException(status_code=400, detail="Ushbu stolda hali buyurtma yo'q")

    active_orders = [o for o in orders if not o.is_paid]
    target_orders = active_orders if active_orders else [orders[0]]

    items_for_receipt = []
    subtotal = 0.0
    waiter_names = set()
    order_nums = []

    for ord in target_orders:
        order_nums.append(ord.order_number)
        if ord.waiter:
            waiter_names.add(ord.waiter.full_name or ord.waiter.username)
        for it in ord.items:
            dish_name = getattr(it.menu_item, "name_cyrillic", None) or (it.menu_item.name if it.menu_item else "Таом")
            items_for_receipt.append({
                "name": dish_name,
                "quantity": it.quantity,
                "unit_price": it.unit_price,
                "total_price": it.total_price,
            })
            subtotal += it.total_price

    fee_pct = getattr(settings, "service_fee_percent", 12.0) or 12.0
    fee_amount = round(subtotal * (fee_pct / 100.0), 2)
    grand_total = subtotal + fee_amount
    rest_name = settings.receipt_header if (settings and settings.receipt_header) else (table.restaurant.name if table.restaurant else "RestAron")
    table_disp = f"{table.room or 'Zal'} N#{table.number}".strip()
    waiter_disp = ", ".join(waiter_names) if waiter_names else (current_user.full_name or current_user.username)

    bill_text = format_pre_check(
        restaurant_name=rest_name,
        address=settings.receipt_address if settings else None,
        phone=settings.receipt_phone if settings else None,
        table_name=table_disp,
        waiter_name=waiter_disp,
        order_number=", ".join(order_nums),
        items=items_for_receipt,
        subtotal=subtotal,
        service_fee_percent=fee_pct,
        service_fee_amount=fee_amount,
        discount=0.0,
        total=grand_total,
        receipt_note=target_orders[0].receipt_note if target_orders else None,
        footer_text=settings.receipt_footer if settings else "Ташрифингиз учун раҳмат! Яна келинг!",
        wifi_pass=settings.receipt_wifi_pass if settings else None,
        paper_width=paper_width,
    )

    # 1-Printer (USB yoki LAN IP) ga chop etish
    p_res = print_to_windows_printer(bill_text, printer_name=cust_printer, codepage=cp)

    archive = ReceiptArchive(
        restaurant_id=table.restaurant_id,
        order_id=target_orders[0].id if target_orders else None,
        receipt_number=f"BILL-{table.number}-{order_nums[0] if order_nums else '0'}",
        receipt_type="pre_check",
        hall_name=table.room,
        table_name=table_disp,
        waiter_name=waiter_disp,
        subtotal=subtotal,
        service_fee_percent=fee_pct,
        service_fee_amount=fee_amount,
        total_amount=grand_total,
        payment_method="pre_check",
        items_json=items_for_receipt,
        raw_text=bill_text,
    )
    db.add(archive)
    await db.commit()

    printed_ok = bool(p_res.get("success", False))
    return {
        "success": printed_ok,
        "printer_name": cust_printer,
        "message": (
            f"Chek {cust_printer} printeriga yuborildi"
            if printed_ok else
            f"Printerga ({cust_printer}) yuborib bo'lmadi: "
            f"{p_res.get('message') or p_res.get('error') or 'printer topilmadi'}. "
            f"Chek matni ekranda ko'rsatildi."
        ),
        "raw_text": bill_text,
        "total": grand_total,
    }


@router.get("/{table_id}", response_model=TableResponse, summary="Stol ma'lumoti")
async def get_table(
    table_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "waiter", "developer")),
):
    result = await db.execute(select(Table).where(Table.id == table_id))
    table = result.scalar_one_or_none()
    if not table:
        raise HTTPException(status_code=404, detail="Stol topilmadi")
    return TableResponse.model_validate(table)


@router.patch("/{table_id}", response_model=TableResponse, summary="Stolni yangilash")
async def update_table(
    table_id: int,
    payload: TableUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "developer")),
):
    result = await db.execute(select(Table).where(Table.id == table_id))
    table = result.scalar_one_or_none()
    if not table:
        raise HTTPException(status_code=404, detail="Stol topilmadi")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(table, field, value)

    await db.flush()
    await db.refresh(table)
    return TableResponse.model_validate(table)


@router.patch("/{table_id}/status", response_model=TableResponse, summary="Stol holatini o'zgartirish")
async def update_table_status(
    table_id: int,
    table_status: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("waiter", "admin", "developer")),
):
    """Ofitsiant yoki Admin stol holatini (available, occupied, reserved) o'zgartiradi"""
    result = await db.execute(select(Table).where(Table.id == table_id))
    table = result.scalar_one_or_none()
    if not table:
        raise HTTPException(status_code=404, detail="Stol topilmadi")

    status_str = table_status.lower()
    try:
        new_enum_status = TableStatus(status_str)
    except ValueError:
        new_enum_status = TableStatus.AVAILABLE

    old_status = table.status.value if hasattr(table.status, "value") else str(table.status)
    table.status = new_enum_status
    await db.flush()
    await db.commit()

    # Real-time WebSocket orqali xabar tarqatish
    await manager.broadcast_to_restaurant(
        table.restaurant_id,
        {
            "type": "table_status_updated",
            "table_id": table.id,
            "table_number": table.number,
            "old_status": old_status,
            "status": new_enum_status.value,
            "new_status": new_enum_status.value,
        },
    )

    return TableResponse.model_validate(table)


@router.post("/{table_id}/clear", response_model=TableResponse, summary="Stolni tozalash / bo'shatish")
async def clear_table(
    table_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("waiter", "admin", "developer")),
):
    """Mijoz ketganidan keyin stolni bo'sh deb belgilash"""
    result = await db.execute(select(Table).where(Table.id == table_id))
    table = result.scalar_one_or_none()
    if not table:
        raise HTTPException(status_code=404, detail="Stol topilmadi")

    table.status = TableStatus.AVAILABLE
    table.is_unlocked = False
    table.current_pin = None
    await db.flush()
    await db.commit()

    await manager.broadcast_to_restaurant(
        table.restaurant_id,
        {
            "type": "table_cleared",
            "table_id": table.id,
            "table_number": table.number,
            "status": TableStatus.AVAILABLE.value,
            "new_status": TableStatus.AVAILABLE.value,
        },
    )

    return TableResponse.model_validate(table)


@router.post("/{table_id}/regenerate-qr", response_model=TableResponse, summary="QR kodni yangilash")
async def regenerate_qr(
    table_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "developer")),
):
    """Stol uchun yangi QR kod generatsiya"""
    result = await db.execute(select(Table).where(Table.id == table_id))
    table = result.scalar_one_or_none()
    if not table:
        raise HTTPException(status_code=404, detail="Stol topilmadi")

    qr_token = str(uuid.uuid4())
    qr_url = f"{get_qr_base_url()}/?table={qr_token}"
    qr_image_url = generate_qr_image(qr_url, qr_token)

    table.qr_token = qr_token
    table.qr_image_url = qr_image_url

    await db.flush()
    await db.refresh(table)
    return TableResponse.model_validate(table)


@router.delete("/{table_id}", status_code=204, summary="Stolni o'chirish")
async def delete_table(
    table_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "developer")),
):
    result = await db.execute(select(Table).where(Table.id == table_id))
    table = result.scalar_one_or_none()
    if not table:
        raise HTTPException(status_code=404, detail="Stol topilmadi")
    await db.delete(table)


