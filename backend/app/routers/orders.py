"""
Buyurtmalar API — Mijoz, Ofitsiant, Oshpaz, Admin
To'liq WebSocket integratsiyasi va 'Yetkazib berdim' funksiyasi bilan
"""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, update
from sqlalchemy.orm import selectinload
from typing import List, Optional

from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.models.order import Order, OrderItem, OrderStatus, CallStatus
from app.models.menu import MenuItem
from app.models.table import Table, TableStatus
from app.models.user import User, UserRole
from app.models.restaurant import Restaurant, RestaurantSettings
from app.models.debt import Debt
from app.models.receipt import ReceiptArchive
from app.models.notification import Notification, NotificationType, NotificationTarget
from app.schemas.order import (
    OrderCreate, OrderResponse, OrderSummary,
    OrderStatusUpdate, CallWaiterRequest, OrderDeliverRequest,
    OrderItemResponse, WaiterCallResponse,
    WaiterOrderCreate, WaiterAddItemsRequest, UpdateItemQtyRequest,
    OrderNoteUpdate, OrderCheckoutRequest
)
from app.core.printer_service import format_kitchen_ticket, format_pre_check, print_to_windows_printer
from app.core.sms_telegram import send_telegram_alert
from app.websockets.manager import manager

router = APIRouter(prefix="/orders", tags=["📋 Buyurtmalar"])


def generate_order_number(restaurant_id: int, count: int) -> str:
    """Buyurtma raqami formati: #R1-0001"""
    return f"#R{restaurant_id}-{count:04d}"


async def create_notification(
    db: AsyncSession,
    restaurant_id: int,
    ntype: NotificationType,
    title: str,
    message: str,
    target: NotificationTarget,
    data: dict = None,
    user_id: int = None,
) -> Notification:
    """Ma'lumotlar bazasida bildirishnoma yaratish"""
    notif = Notification(
        restaurant_id=restaurant_id,
        type=ntype,
        title=title,
        message=message,
        target=target,
        data=data or {},
        user_id=user_id,
    )
    db.add(notif)
    return notif


async def auto_assign_waiter(db: AsyncSession, restaurant_id: int) -> Optional[User]:
    """
    Eng kam faol buyurtmaga ega bo'lgan faol ofitsiantni avtomatik tanlash
    """
    waiters_res = await db.execute(
        select(User).where(
            User.restaurant_id == restaurant_id,
            User.role == UserRole.WAITER,
            User.is_active == True,
        )
    )
    waiters = waiters_res.scalars().all()
    if not waiters:
        return None

    # Faol buyurtmalar soni bo'yicha eng bo'sh ofitsiantni topish
    best_waiter = None
    min_count = float("inf")

    for waiter in waiters:
        count_res = await db.execute(
            select(func.count(Order.id)).where(
                Order.waiter_id == waiter.id,
                Order.status.in_([
                    OrderStatus.PENDING,
                    OrderStatus.CONFIRMED,
                    OrderStatus.PREPARING,
                    OrderStatus.READY,
                ]),
            )
        )
        active_count = count_res.scalar() or 0
        if active_count < min_count:
            min_count = active_count
            best_waiter = waiter

    return best_waiter


async def load_order_full(db: AsyncSession, order_id: int) -> Optional[Order]:
    """
    Buyurtmani barcha bog'liqliklari bilan to'liq yuklab oladi.

    MUHIM: `db.refresh(order)` bog'liqliklarni (items -> menu_item, table, waiter)
    "expired" holatga o'tkazadi. Keyin ularga murojaat qilish async kontekstda
    lazy-load'ni ishga tushiradi va SQLAlchemy `MissingGreenlet` xatosi bilan
    500 qaytaradi. Shuning uchun refresh o'rniga doim selectinload bilan
    qaytadan yuklaymiz.
    """
    res = await db.execute(
        select(Order)
        .options(
            selectinload(Order.items).selectinload(OrderItem.menu_item),
            selectinload(Order.table),
            selectinload(Order.waiter),
        )
        .where(Order.id == order_id)
    )
    return res.scalar_one_or_none()


def build_order_response(order: Order, table_number: Optional[int] = None, waiter_name: Optional[str] = None) -> OrderResponse:
    """OrderResponse obyektini xavfsiz va to'liq yaratish"""
    items_response = []
    for item in order.items:
        items_response.append(
            OrderItemResponse(
                id=item.id,
                menu_item_id=item.menu_item_id,
                quantity=item.quantity,
                unit_price=item.unit_price,
                total_price=item.total_price,
                special_note=item.special_note,
                item_time=item.item_time,
                sent_to_kitchen=bool(item.sent_to_kitchen),
                sent_to_kitchen_at=item.sent_to_kitchen_at,
                is_prepared=bool(item.is_prepared),
                prepared_at=item.prepared_at,
                menu_item_name=item.menu_item.name if item.menu_item else None,
                menu_item_image=item.menu_item.image_url if item.menu_item else None,
            )
        )

    t_num = table_number if table_number is not None else (order.table.number if order.table else None)
    t_room = order.table.room if order.table else None
    w_name = waiter_name if waiter_name is not None else (
        (order.waiter.full_name or order.waiter.username) if order.waiter else None
    )

    return OrderResponse(
        id=order.id,
        order_number=order.order_number,
        restaurant_id=order.restaurant_id,
        table_id=order.table_id,
        table_number=t_num,
        room=t_room,
        waiter_id=order.waiter_id,
        waiter_name=w_name,
        customer_name=order.customer_name,
        customer_note=order.customer_note,
        order_type=order.order_type or "table",
        hall_name=order.hall_name or t_room,
        kitchen_note=order.kitchen_note,
        receipt_note=order.receipt_note,
        status=order.status,
        subtotal=order.subtotal or 0.0,
        service_fee_percent=order.service_fee_percent or 12.0,
        service_fee_amount=order.service_fee_amount or 0.0,
        discount=order.discount or 0.0,
        total=order.total or 0.0,
        is_paid=bool(order.is_paid),
        payment_method=order.payment_method or "cash",
        cash_amount=order.cash_amount or 0.0,
        card_amount=order.card_amount or 0.0,
        click_amount=order.click_amount or 0.0,
        debt_amount=order.debt_amount or 0.0,
        waiter_share_amount=order.waiter_share_amount or 0.0,
        call_waiter=bool(order.call_waiter),
        call_status=order.call_status,
        call_note=order.call_note,
        items=items_response,
        created_at=order.created_at,
        preparing_at=order.preparing_at,
        ready_at=order.ready_at,
        served_at=order.served_at,
        closed_at=order.closed_at,
        updated_at=order.updated_at,
    )



# ─── Mijoz: Buyurtma berish ────────────────────────────────
@router.post("/", response_model=OrderResponse, status_code=201, summary="Buyurtma berish (mijoz)")
async def create_order(payload: OrderCreate, db: AsyncSession = Depends(get_db)):
    """QR orqali kirgan mijoz buyurtma beradi (auth talab qilinmaydi)"""
    result = await db.execute(select(Table).where(Table.id == payload.table_id))
    table = result.scalar_one_or_none()
    if not table:
        raise HTTPException(status_code=404, detail="Stol topilmadi")

    # Sozlamalarni tekshirish: mijozga saytdan to'g'ridan-to'g'ri buyurtma berish ruxsat etilganmi?
    set_res = await db.execute(select(RestaurantSettings).where(RestaurantSettings.restaurant_id == table.restaurant_id))
    settings = set_res.scalar_one_or_none()
    if settings and not settings.allow_orders_from_qr and not settings.allow_orders:
        raise HTTPException(
            status_code=400,
            detail="Hurmatli mijoz! Buyurtmani ofitsiant stolingizga kelib qabul qiladi. Iltimos menyuni ko'rib chiqing va 'Ofitsiantni chaqirish' tugmasini bosing."
        )

    # Stol holatini band qilish
    table.status = TableStatus.OCCUPIED

    # Avtomatik ofitsiant tayinlash
    assigned_waiter = await auto_assign_waiter(db, table.restaurant_id)

    # Buyurtma raqamini aniqlash
    count_result = await db.execute(
        select(func.count(Order.id)).where(Order.restaurant_id == table.restaurant_id)
    )
    count = count_result.scalar() + 1
    order_number = generate_order_number(table.restaurant_id, count)

    order = Order(
        order_number=order_number,
        restaurant_id=table.restaurant_id,
        table_id=payload.table_id,
        waiter_id=assigned_waiter.id if assigned_waiter else None,
        customer_name=payload.customer_name,
        customer_note=payload.customer_note,
        status=OrderStatus.PENDING,
    )
    db.add(order)
    await db.flush()

    subtotal = 0.0
    items_details = []
    for item_data in payload.items:
        item_result = await db.execute(
            select(MenuItem).where(MenuItem.id == item_data.menu_item_id, MenuItem.is_available == True)
        )
        menu_item = item_result.scalar_one_or_none()
        if not menu_item:
            raise HTTPException(
                status_code=404,
                detail=f"Taom #{item_data.menu_item_id} topilmadi yoki mavjud emas",
            )

        total_price = menu_item.price * item_data.quantity
        subtotal += total_price

        order_item = OrderItem(
            order_id=order.id,
            menu_item_id=item_data.menu_item_id,
            quantity=item_data.quantity,
            unit_price=menu_item.price,
            total_price=total_price,
            special_note=item_data.special_note,
        )
        db.add(order_item)
        menu_item.total_ordered += item_data.quantity

        items_details.append({
            "name": menu_item.name,
            "quantity": item_data.quantity,
            "price": menu_item.price,
            "note": item_data.special_note,
        })

    order.subtotal = subtotal
    order.total = subtotal

    waiter_name = (assigned_waiter.full_name or assigned_waiter.username) if assigned_waiter else None

    # Bildirishnoma (DB)
    await create_notification(
        db=db,
        restaurant_id=table.restaurant_id,
        ntype=NotificationType.NEW_ORDER,
        title=f"Yangi buyurtma — Stol #{table.number}",
        message=f"{order_number} buyurtma keldi. Jami: {subtotal:,.0f} so'm. Ofitsiant: {waiter_name or 'Tayinlanmagan'}",
        target=NotificationTarget.ALL_STAFF,
        data={
            "order_id": order.id,
            "order_number": order_number,
            "table_id": table.id,
            "table_number": table.number,
            "waiter_id": assigned_waiter.id if assigned_waiter else None,
            "waiter_name": waiter_name,
            "total": subtotal,
        },
    )

    await db.flush()

    # Real-time WebSocket xabarlari tarqatish
    ws_payload = {
        "type": "new_order",
        "order_id": order.id,
        "order_number": order.order_number,
        "table_id": table.id,
        "table_number": table.number,
        "waiter_id": assigned_waiter.id if assigned_waiter else None,
        "waiter_name": waiter_name,
        "customer_name": order.customer_name,
        "customer_note": order.customer_note,
        "subtotal": subtotal,
        "total": subtotal,
        "items": items_details,
        "created_at": order.created_at.isoformat() if order.created_at else datetime.now(timezone.utc).isoformat(),
    }

    # Oshpaz, Ofitsiant va Adminga
    await manager.broadcast_to_roles(table.restaurant_id, ["chef", "waiter", "admin"], ws_payload)

    # Agar ofitsiant biriktirilgan bo'lsa, unga maxsus shaxsiy bildirishnoma
    if assigned_waiter:
        await manager.send_to_user(
            table.restaurant_id,
            assigned_waiter.id,
            {
                "type": "order_assigned",
                "title": f"Sizga buyurtma tayinlandi — Stol #{table.number}",
                "message": f"Buyurtma {order_number} sizga biriktirildi.",
                "order_id": order.id,
                "table_id": table.id,
                "table_number": table.number,
            },
        )

    # Stoldagi mijozga tasdiq
    await manager.broadcast_to_table(
        table.restaurant_id,
        table.id,
        {
            "type": "order_placed",
            "order_id": order.id,
            "order_number": order.order_number,
            "status": "pending",
            "message": "Buyurtmangiz qabul qilindi va oshxonaga uzatildi!",
        },
    )

    # To'liq qayta yuklash
    refreshed = await db.execute(
        select(Order)
        .options(
            selectinload(Order.items).selectinload(OrderItem.menu_item),
            selectinload(Order.table),
            selectinload(Order.waiter),
        )
        .where(Order.id == order.id)
    )
    full_order = refreshed.scalar_one()
    return build_order_response(full_order, table.number, waiter_name)


# ─── Ofitsiant / Kassa: Yangi buyurtma yaratish (Ali Poster POS) ───
@router.post("/waiter-create", response_model=OrderResponse, status_code=201, summary="Buyurtma yaratish (Ofitsiant / Kassa POS)")
async def waiter_create_order(
    payload: WaiterOrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("waiter", "admin", "developer")),
):
    """Ofitsiant yoki kassir stol, olib ketish (s soboy) yoki yetkazish uchun buyurtma yaratadi"""
    table = None
    table_id = payload.table_id
    hall_name = payload.hall_name

    if table_id:
        result = await db.execute(select(Table).where(Table.id == table_id))
        table = result.scalar_one_or_none()
        if not table:
            raise HTTPException(status_code=404, detail="Stol topilmadi")
        table.status = TableStatus.OCCUPIED
        if not hall_name:
            hall_name = table.room or f"Zal"

    # Restoran sozlamalarini olish (xizmat foizi)
    set_res = await db.execute(select(RestaurantSettings).where(RestaurantSettings.restaurant_id == payload.restaurant_id))
    settings = set_res.scalar_one_or_none()
    service_fee_pct = settings.service_fee_percent if settings else 12.0

    count_result = await db.execute(
        select(func.count(Order.id)).where(Order.restaurant_id == payload.restaurant_id)
    )
    count = (count_result.scalar() or 0) + 1
    order_number = generate_order_number(payload.restaurant_id, count)

    order = Order(
        order_number=order_number,
        restaurant_id=payload.restaurant_id,
        table_id=table_id if table else (payload.table_id or 1),
        waiter_id=current_user.id,
        order_type=payload.order_type,
        hall_name=hall_name,
        customer_name=payload.customer_name,
        kitchen_note=payload.kitchen_note,
        receipt_note=payload.receipt_note,
        service_fee_percent=service_fee_pct,
        status=OrderStatus.PENDING,
    )
    db.add(order)
    await db.flush()

    subtotal = 0.0
    now_time_str = datetime.now().strftime("%H:%M")
    items_details = []

    for item_data in payload.items:
        item_res = await db.execute(select(MenuItem).where(MenuItem.id == item_data.menu_item_id))
        menu_item = item_res.scalar_one_or_none()
        if not menu_item:
            continue

        tot_price = menu_item.price * item_data.quantity
        subtotal += tot_price

        order_item = OrderItem(
            order_id=order.id,
            menu_item_id=item_data.menu_item_id,
            quantity=item_data.quantity,
            unit_price=menu_item.price,
            total_price=tot_price,
            special_note=item_data.special_note,
            item_time=now_time_str,
            sent_to_kitchen=False,
        )
        db.add(order_item)
        menu_item.total_ordered += item_data.quantity
        items_details.append({
            "name": menu_item.name,
            "quantity": item_data.quantity,
            "price": menu_item.price,
            "note": item_data.special_note,
            "item_time": now_time_str,
        })

    fee_amount = subtotal * (service_fee_pct / 100.0)
    order.subtotal = subtotal
    order.service_fee_amount = fee_amount
    order.total = subtotal + fee_amount

    if current_user.commission_percent and current_user.commission_percent > 0:
        order.waiter_share_percent = current_user.commission_percent
        order.waiter_share_amount = subtotal * (current_user.commission_percent / 100.0)

    await db.flush()

    waiter_name = current_user.full_name or current_user.username
    ws_payload = {
        "type": "new_order",
        "order_id": order.id,
        "order_number": order.order_number,
        "table_id": order.table_id,
        "table_number": table.number if table else None,
        "room": hall_name,
        "waiter_id": current_user.id,
        "waiter_name": waiter_name,
        "order_type": order.order_type,
        "subtotal": subtotal,
        "service_fee_percent": service_fee_pct,
        "total": order.total,
        "items": items_details,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await manager.broadcast_to_roles(payload.restaurant_id, ["waiter", "admin", "chef"], ws_payload)

    refreshed = await db.execute(
        select(Order)
        .options(
            selectinload(Order.items).selectinload(OrderItem.menu_item),
            selectinload(Order.table),
            selectinload(Order.waiter),
        )
        .where(Order.id == order.id)
    )
    full_order = refreshed.scalar_one()
    return build_order_response(full_order, table.number if table else None, waiter_name)


# ─── Ochiq stolga taom qo'shish (Dozakaz) ───────────────────────
@router.post("/{order_id}/add-items", response_model=OrderResponse, summary="Stolga taom qo'shish (Dozakaz)")
async def waiter_add_items(
    order_id: int,
    payload: WaiterAddItemsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("waiter", "admin", "developer")),
):
    """Ofitsiant faol buyurtmaga qo'shimcha taomlar qo'shadi"""
    res = await db.execute(
        select(Order)
        .options(
            selectinload(Order.items).selectinload(OrderItem.menu_item),
            selectinload(Order.table),
            selectinload(Order.waiter),
        )
        .where(Order.id == order_id)
    )
    order = res.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Buyurtma topilmadi")

    if order.status in [OrderStatus.PAID, OrderStatus.CANCELLED]:
        raise HTTPException(status_code=400, detail="Ushbu buyurtma yopilgan yoki bekor qilingan")

    now_time_str = datetime.now().strftime("%H:%M")
    new_subtotal = order.subtotal or 0.0
    added_details = []

    for item_data in payload.items:
        item_res = await db.execute(select(MenuItem).where(MenuItem.id == item_data.menu_item_id))
        menu_item = item_res.scalar_one_or_none()
        if not menu_item:
            continue

        tot_price = menu_item.price * item_data.quantity
        new_subtotal += tot_price

        order_item = OrderItem(
            order_id=order.id,
            menu_item_id=item_data.menu_item_id,
            quantity=item_data.quantity,
            unit_price=menu_item.price,
            total_price=tot_price,
            special_note=item_data.special_note,
            item_time=now_time_str,
            sent_to_kitchen=payload.send_to_kitchen_immediately,
            sent_to_kitchen_at=datetime.now(timezone.utc) if payload.send_to_kitchen_immediately else None,
        )
        db.add(order_item)
        menu_item.total_ordered += item_data.quantity
        added_details.append({
            "name": menu_item.name,
            "quantity": item_data.quantity,
            "price": menu_item.price,
            "note": item_data.special_note,
            "item_time": now_time_str,
        })

    order.subtotal = new_subtotal
    fee_pct = order.service_fee_percent or 12.0
    order.service_fee_amount = new_subtotal * (fee_pct / 100.0)
    order.total = new_subtotal + order.service_fee_amount - (order.discount or 0.0)

    if current_user.commission_percent and current_user.commission_percent > 0:
        order.waiter_share_amount = new_subtotal * (current_user.commission_percent / 100.0)

    await db.flush()

    await manager.broadcast_to_restaurant(order.restaurant_id, {
        "type": "order_updated",
        "order_id": order.id,
        "order_number": order.order_number,
        "table_id": order.table_id,
        "table_number": order.table.number if order.table else None,
        "total": order.total,
        "subtotal": order.subtotal,
        "added_items": added_details,
    })

    order = await load_order_full(db, order.id) or order
    return build_order_response(order)


# ─── Taom sonini o'zgartirish [- 1 +] ──────────────────────────
@router.patch("/{order_id}/items/{item_id}/quantity", response_model=OrderResponse, summary="Taom sonini o'zgartirish")
async def update_item_quantity(
    order_id: int,
    item_id: int,
    payload: UpdateItemQtyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("waiter", "admin", "developer")),
):
    item_res = await db.execute(
        select(OrderItem).where(OrderItem.id == item_id, OrderItem.order_id == order_id)
    )
    order_item = item_res.scalar_one_or_none()
    if not order_item:
        raise HTTPException(status_code=404, detail="Taom topilmadi")

    order_item.quantity = payload.quantity
    order_item.total_price = order_item.unit_price * payload.quantity

    all_items_res = await db.execute(select(OrderItem).where(OrderItem.order_id == order_id))
    all_items = all_items_res.scalars().all()
    subtotal = sum(i.total_price for i in all_items)

    order_res = await db.execute(
        select(Order).options(selectinload(Order.items).selectinload(OrderItem.menu_item), selectinload(Order.table), selectinload(Order.waiter)).where(Order.id == order_id)
    )
    order = order_res.scalar_one()
    order.subtotal = subtotal
    fee_pct = order.service_fee_percent or 12.0
    order.service_fee_amount = subtotal * (fee_pct / 100.0)
    order.total = subtotal + order.service_fee_amount - (order.discount or 0.0)

    await db.flush()
    order = await load_order_full(db, order.id) or order
    return build_order_response(order)


# ─── Taomni buyurtmadan o'chirish ──────────────────────────────
@router.delete("/{order_id}/items/{item_id}", response_model=OrderResponse, summary="Taomni buyurtmadan o'chirish")
async def delete_order_item(
    order_id: int,
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("waiter", "admin", "developer")),
):
    item_res = await db.execute(
        select(OrderItem).where(OrderItem.id == item_id, OrderItem.order_id == order_id)
    )
    order_item = item_res.scalar_one_or_none()
    if not order_item:
        raise HTTPException(status_code=404, detail="Taom topilmadi")

    await db.delete(order_item)
    await db.flush()

    all_items_res = await db.execute(select(OrderItem).where(OrderItem.order_id == order_id))
    all_items = all_items_res.scalars().all()
    subtotal = sum(i.total_price for i in all_items)

    order_res = await db.execute(
        select(Order).options(selectinload(Order.items).selectinload(OrderItem.menu_item), selectinload(Order.table), selectinload(Order.waiter)).where(Order.id == order_id)
    )
    order = order_res.scalar_one()
    order.subtotal = subtotal
    fee_pct = order.service_fee_percent or 12.0
    order.service_fee_amount = subtotal * (fee_pct / 100.0)
    order.total = subtotal + order.service_fee_amount - (order.discount or 0.0)

    await db.flush()
    order = await load_order_full(db, order.id) or order
    return build_order_response(order)


# ─── Oshxona va chek izohlarini yangilash ─────────────────────
@router.patch("/{order_id}/notes", response_model=OrderResponse, summary="Izohlarni yangilash (Oshxona / Chek)")
async def update_order_notes(
    order_id: int,
    payload: OrderNoteUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("waiter", "admin", "developer")),
):
    order_res = await db.execute(
        select(Order).options(selectinload(Order.items).selectinload(OrderItem.menu_item), selectinload(Order.table), selectinload(Order.waiter)).where(Order.id == order_id)
    )
    order = order_res.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Buyurtma topilmadi")

    if payload.kitchen_note is not None:
        order.kitchen_note = payload.kitchen_note
    if payload.receipt_note is not None:
        order.receipt_note = payload.receipt_note

    await db.flush()
    order = await load_order_full(db, order.id) or order
    return build_order_response(order)


# ─── Oshxonaga yuborish (На кухню — Begunok) ───────────────────
@router.post("/{order_id}/send-to-kitchen", summary="Oshxonaga yuborish (Xprinter Begunok)")
async def send_to_kitchen(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("waiter", "admin", "developer")),
):
    """
    Ofitsiant 'На кухню' tugmasini bosadi:
    1. Yuborilmagan taomlarni sent_to_kitchen = True qiladi
    2. Xprinter uchun oshxona begunogi matnini formatlaydi (Rasm 1 dagidek)
    3. ReceiptArchive ga 'kitchen' sifatida saqlaydi
    4. Oshpaz KDS ekraniga WebSocket xabar beradi
    """
    res = await db.execute(
        select(Order)
        .options(
            selectinload(Order.items).selectinload(OrderItem.menu_item),
            selectinload(Order.table),
            selectinload(Order.waiter),
        )
        .where(Order.id == order_id)
    )
    order = res.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Buyurtma topilmadi")

    unsent_items = [i for i in order.items if not i.sent_to_kitchen]
    target_items = unsent_items if unsent_items else order.items

    now_utc = datetime.now(timezone.utc)
    for it in target_items:
        it.sent_to_kitchen = True
        it.sent_to_kitchen_at = now_utc

    if order.status == OrderStatus.PENDING:
        order.status = OrderStatus.PREPARING
        order.preparing_at = now_utc

    table_num = order.table.number if order.table else "—"
    room_name = order.table.room if order.table else ""
    waiter_display = current_user.full_name or current_user.username

    set_res = await db.execute(select(RestaurantSettings).where(RestaurantSettings.restaurant_id == order.restaurant_id))
    settings = set_res.scalar_one_or_none()
    paper_width = settings.printer_paper_width if settings else 80

    # 3-Printer Routing:
    # 1-Oshxona (Qozon taomlari) -> hot_kitchen
    # 2-Oshxona (Baliq, Somsa, va h.k.) -> cold_kitchen / fish / somsa
    k1_items = []
    k2_items = []

    for it in target_items:
        st = getattr(it.menu_item, "kitchen_station", "hot_kitchen") if it.menu_item else "hot_kitchen"
        st = (st or "hot_kitchen").lower().strip()

        dish_name = getattr(it.menu_item, "name_cyrillic", None) or (it.menu_item.name if it.menu_item else "Таом")

        item_dict = {
            "name": dish_name,
            "quantity": it.quantity,
            "note": it.special_note,
        }

        # Stansiya bo'yicha saralash
        if st in ["customer_only", "customer", "kassa", "bill_only"]:
            # Faqat mijoz kassa hisob chekida chiqadi, oshxonaga kirmaydi
            continue
        elif st in ["all_kitchens", "both", "all"]:
            k1_items.append(item_dict)
            k2_items.append(item_dict)
        elif st in ["cold_kitchen", "kitchen2", "somsa", "baliq"] or any(key in st for key in ["cold", "kitchen2", "2", "baliq", "fish", "somsa", "mangal", "grill"]):
            k2_items.append(item_dict)
        else:
            k1_items.append(item_dict)

    k1_title = getattr(settings, "kitchen1_title", "1-Oshxona (Qozon taomlari)") or "1-Oshxona (Qozon taomlari)"
    k2_title = getattr(settings, "kitchen2_title", "2-Oshxona (Baliq / Somsa)") or "2-Oshxona (Baliq / Somsa)"
    k1_printer = getattr(settings, "printer_kitchen1_name", None) or "192.168.1.201"
    k2_printer = getattr(settings, "printer_kitchen2_name", None) or "192.168.1.202"
    auto_print = getattr(settings, "auto_print_kitchen", True)

    generated_tickets = []
    combined_texts = []

    # 1-Oshxona (Qozon taomlari)
    if k1_items:
        k1_text = format_kitchen_ticket(
            hall_name=order.hall_name or room_name,
            room_name=room_name,
            table_number=table_num,
            waiter_name=waiter_display,
            items=k1_items,
            kitchen_note=order.kitchen_note,
            order_time=datetime.now(),
            paper_width=paper_width,
            station_title=k1_title,
        )
        combined_texts.append(k1_text)
        print_status = False
        if auto_print:
            try:
                p_res = print_to_windows_printer(k1_text, printer_name=k1_printer)
                print_status = p_res.get("success", False)
            except Exception:
                pass

        archive1 = ReceiptArchive(
            restaurant_id=order.restaurant_id,
            order_id=order.id,
            receipt_number=f"KITCHEN1-{order.order_number}",
            receipt_type="kitchen",
            hall_name=order.hall_name or room_name,
            table_name=f"N# {table_num} ({k1_title})",
            waiter_name=waiter_display,
            subtotal=order.subtotal or 0.0,
            service_fee_percent=0.0,
            service_fee_amount=0.0,
            total_amount=order.subtotal or 0.0,
            payment_method="kitchen",
            items_json=k1_items,
            notes=order.kitchen_note,
            raw_text=k1_text,
        )
        db.add(archive1)
        generated_tickets.append({
            "station": "hot_kitchen",
            "station_title": k1_title,
            "printer_name": k1_printer,
            "items": k1_items,
            "raw_text": k1_text,
            "printed": print_status,
        })

    # 2-Oshxona (Baliq / Somsa)
    if k2_items:
        k2_text = format_kitchen_ticket(
            hall_name=order.hall_name or room_name,
            room_name=room_name,
            table_number=table_num,
            waiter_name=waiter_display,
            items=k2_items,
            kitchen_note=order.kitchen_note,
            order_time=datetime.now(),
            paper_width=paper_width,
            station_title=k2_title,
        )
        combined_texts.append(k2_text)
        print_status = False
        if auto_print:
            try:
                p_res = print_to_windows_printer(k2_text, printer_name=k2_printer)
                print_status = p_res.get("success", False)
            except Exception:
                pass

        archive2 = ReceiptArchive(
            restaurant_id=order.restaurant_id,
            order_id=order.id,
            receipt_number=f"KITCHEN2-{order.order_number}",
            receipt_type="kitchen",
            hall_name=order.hall_name or room_name,
            table_name=f"N# {table_num} ({k2_title})",
            waiter_name=waiter_display,
            subtotal=order.subtotal or 0.0,
            service_fee_percent=0.0,
            service_fee_amount=0.0,
            total_amount=order.subtotal or 0.0,
            payment_method="kitchen",
            items_json=k2_items,
            notes=order.kitchen_note,
            raw_text=k2_text,
        )
        db.add(archive2)
        generated_tickets.append({
            "station": "cold_kitchen",
            "station_title": k2_title,
            "printer_name": k2_printer,
            "items": k2_items,
            "raw_text": k2_text,
            "printed": print_status,
        })

    await db.flush()

    main_raw_text = "\n------------------------------------------\n".join(combined_texts) if combined_texts else ""

    await manager.broadcast_to_roles(
        order.restaurant_id,
        ["chef", "admin"],
        {
            "type": "kitchen_ticket",
            "order_id": order.id,
            "order_number": order.order_number,
            "table_number": table_num,
            "hall_name": order.hall_name or room_name,
            "waiter_name": waiter_display,
            "tickets": generated_tickets,
            "raw_text": main_raw_text,
            "message": f"🔔 Yangi oshxona begunogi: Stol #{table_num}",
        }
    )

    return {
        "success": True,
        "order_id": order.id,
        "items_count": len(target_items),
        "tickets": generated_tickets,
        "raw_text": main_raw_text,
    }


# ─── To'lov va Stolni yopish (К оплате — Kassa) ───────────────
@router.post("/{order_id}/checkout", summary="To'lovni qabul qilish va hisobni yopish (К оплате)")
async def checkout_order(
    order_id: int,
    payload: OrderCheckoutRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("waiter", "admin", "developer")),
):
    """
    1. To'lov turlarini hisoblaydi (Naqd, Karta, Click, Nasiya)
    2. Agar Nasiya bo'lsa -> Debt jadvalida qarzdor yozuvini yaratadi
    3. Stolni bo'shatadi (AVAILABLE)
    4. Xprinter uchun mijoz hisob cheki (Bill / Pre-check) yaratadi
    5. ReceiptArchive ga 3 yilga saqlaydi
    6. WebSocket orqali barchaga hisob yopilganini e'lon qiladi
    """
    res = await db.execute(
        select(Order)
        .options(
            selectinload(Order.items).selectinload(OrderItem.menu_item),
            selectinload(Order.table),
            selectinload(Order.waiter),
        )
        .where(Order.id == order_id)
    )
    order = res.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Buyurtma topilmadi")

    set_res = await db.execute(select(RestaurantSettings).where(RestaurantSettings.restaurant_id == order.restaurant_id))
    settings = set_res.scalar_one_or_none()

    rest_res = await db.execute(select(Restaurant).where(Restaurant.id == order.restaurant_id))
    restaurant = rest_res.scalar_one_or_none()
    rest_name = restaurant.name if restaurant else "RestAron"

    fee_pct = payload.service_fee_percent if payload.service_fee_percent is not None else (
        settings.service_fee_percent if settings else 12.0
    )
    subtotal = sum(i.total_price for i in order.items)
    fee_amount = subtotal * (fee_pct / 100.0)
    discount = payload.discount
    total = max(0.0, subtotal + fee_amount - discount)

    order.subtotal = subtotal
    order.service_fee_percent = fee_pct
    order.service_fee_amount = fee_amount
    order.discount = discount
    order.total = total
    order.is_paid = True
    order.status = OrderStatus.PAID
    order.closed_at = datetime.now(timezone.utc)

    order.payment_method = payload.payment_method

    # ─── To'lov summalarini tekshirish va kassaga to'g'ri yozish ───
    # Kassir faqat to'lov turini tanlab, summani kiritmasligi mumkin —
    # bunday holda butun summa o'sha tur bo'yicha yoziladi.
    cash_in = max(0.0, payload.cash_amount or 0.0)
    card_in = max(0.0, payload.card_amount or 0.0)
    click_in = max(0.0, payload.click_amount or 0.0)
    debt_in = max(0.0, payload.debt_amount or 0.0)

    if (cash_in + card_in + click_in + debt_in) == 0.0:
        if payload.payment_method == "cash":
            cash_in = total
        elif payload.payment_method == "card":
            card_in = total
        elif payload.payment_method == "click":
            click_in = total
        elif payload.payment_method == "debt":
            debt_in = total

    # Naqd pul mijozdan ortig'i bilan olinishi mumkin (qaytim beriladi),
    # lekin karta / Click / nasiya summasi hisobdan oshib ketmasligi kerak.
    non_cash = card_in + click_in + debt_in
    if non_cash - total > 0.01:
        raise HTTPException(
            status_code=400,
            detail=(
                f"To'lov summasi hisobdan oshib ketdi: "
                f"{non_cash:,.0f} so'm kiritildi, hisob {total:,.0f} so'm."
            ),
        )

    tendered = cash_in + non_cash
    if tendered + 0.01 < total:
        raise HTTPException(
            status_code=400,
            detail=(
                f"To'lov to'liq emas: {tendered:,.0f} so'm kiritildi, "
                f"hisob {total:,.0f} so'm. Yetishmayotgan summa: {total - tendered:,.0f} so'm. "
                f"Qolgan qismini nasiya (qarz) sifatida rasmiylashtiring."
            ),
        )

    # Kassaga faqat haqiqiy tushum yoziladi — naqd ortiqchasi qaytim sifatida
    # qaytariladi va hisobotlarni shishirmaydi.
    change_amount = round(max(0.0, tendered - total), 2)
    order.card_amount = card_in
    order.click_amount = click_in
    order.debt_amount = debt_in
    order.cash_amount = round(max(0.0, cash_in - change_amount), 2)

    debt_obj = None
    if order.debt_amount > 0 or payload.payment_method == "debt":
        cust_name = payload.debt_customer_name or order.customer_name or "Noma'lum Mijoz"
        cust_phone = payload.debt_customer_phone or "—"
        debt_obj = Debt(
            restaurant_id=order.restaurant_id,
            order_id=order.id,
            customer_name=cust_name,
            customer_phone=cust_phone,
            amount=order.debt_amount if order.debt_amount > 0 else total,
            paid_amount=0.0,
            remaining_amount=order.debt_amount if order.debt_amount > 0 else total,
            status="unpaid",
            due_date=payload.debt_due_date,
            note=payload.debt_note or f"Buyurtma {order.order_number} uchun qarz",
        )
        db.add(debt_obj)

    waiter_user = order.waiter or current_user
    if waiter_user and waiter_user.commission_percent and waiter_user.commission_percent > 0:
        order.waiter_share_percent = waiter_user.commission_percent
        order.waiter_share_amount = subtotal * (waiter_user.commission_percent / 100.0)

    if order.table:
        order.table.status = TableStatus.AVAILABLE
        order.table.current_pin = None
        order.table.is_unlocked = False

    paper_width = settings.printer_paper_width if settings else 80
    table_disp = f"{order.hall_name or (order.table.room if order.table else '')} N#{order.table.number if order.table else ''}".strip()
    waiter_disp = (order.waiter.full_name or order.waiter.username) if order.waiter else current_user.full_name

    items_for_receipt = [
        {
            "name": it.menu_item.name if it.menu_item else "Taom",
            "quantity": it.quantity,
            "unit_price": it.unit_price,
            "total_price": it.total_price,
        }
        for it in order.items
    ]

    bill_text = format_pre_check(
        restaurant_name=settings.receipt_header if (settings and settings.receipt_header) else rest_name,
        address=settings.receipt_address if settings else None,
        phone=settings.receipt_phone if settings else None,
        table_name=table_disp,
        waiter_name=waiter_disp,
        order_number=order.order_number,
        items=items_for_receipt,
        subtotal=subtotal,
        service_fee_percent=fee_pct,
        service_fee_amount=fee_amount,
        discount=discount,
        total=total,
        receipt_note=order.receipt_note,
        footer_text=settings.receipt_footer if settings else "Tashrifingiz uchun rahmat!",
        created_at=order.created_at,
        paper_width=paper_width,
    )

    archive = ReceiptArchive(
        restaurant_id=order.restaurant_id,
        order_id=order.id,
        receipt_number=order.order_number,
        receipt_type="final_bill",
        hall_name=order.hall_name,
        table_name=table_disp,
        waiter_name=waiter_disp,
        subtotal=subtotal,
        service_fee_percent=fee_pct,
        service_fee_amount=fee_amount,
        total_amount=total,
        payment_method=order.payment_method,
        cash_amount=order.cash_amount,
        card_amount=order.card_amount,
        click_amount=order.click_amount,
        debt_amount=order.debt_amount,
        items_json=items_for_receipt,
        notes=order.receipt_note,
        raw_text=bill_text,
    )
    db.add(archive)
    await db.flush()

    # Avtomatik 1-Printer (Mijoz kassa cheki) ga chop etish
    if getattr(settings, "auto_print_customer_bill", True):
        cust_printer = getattr(settings, "printer_customer_name", None) or "X-Q80A"
        try:
            print_to_windows_printer(bill_text, printer_name=cust_printer)
        except Exception:
            pass

    await manager.broadcast_to_restaurant(order.restaurant_id, {
        "type": "order_paid",
        "order_id": order.id,
        "order_number": order.order_number,
        "table_id": order.table_id,
        "table_number": order.table.number if order.table else None,
        "total": total,
        "payment_method": order.payment_method,
        "raw_text": bill_text,
        "message": f"Stol #{order.table.number if order.table else ''} to'landi va yopildi ✅",
    })

    if order.table:
        await manager.broadcast_to_roles(order.restaurant_id, ["waiter", "admin"], {
            "type": "table_status_updated",
            "table_id": order.table.id,
            "table_number": order.table.number,
            "status": TableStatus.AVAILABLE.value,
            "new_status": TableStatus.AVAILABLE.value,
        })

    order = await load_order_full(db, order.id) or order
    return {
        "success": True,
        "order_id": order.id,
        "order_number": order.order_number,
        "total": total,
        "payment_method": order.payment_method,
        "cash_received": round(cash_in, 2),
        "change_amount": change_amount,
        "raw_text": bill_text,
        "debt_created": bool(debt_obj),
        "order": build_order_response(order),
    }



# ─── Ofitsiant chaqirish ────────────────────────────────────
@router.post("/call-waiter", status_code=200, summary="Ofitsiant chaqirish")
async def call_waiter(payload: CallWaiterRequest, db: AsyncSession = Depends(get_db)):
    """Mijoz stolidan ofitsiantni chaqiradi"""
    result = await db.execute(select(Table).where(Table.id == payload.table_id))
    table = result.scalar_one_or_none()
    if not table:
        raise HTTPException(status_code=404, detail="Stol topilmadi")

    # Ushbu stolda faol buyurtma bormi?
    order_res = await db.execute(
        select(Order)
        .where(
            Order.table_id == table.id,
            Order.status.in_([
                OrderStatus.PENDING,
                OrderStatus.CONFIRMED,
                OrderStatus.PREPARING,
                OrderStatus.READY,
                OrderStatus.SERVED,
            ]),
        )
        .order_by(Order.created_at.desc())
    )
    active_order = order_res.scalars().first()

    assigned_waiter_id = None
    if active_order:
        active_order.call_waiter = True
        active_order.call_status = CallStatus.PENDING
        active_order.call_note = payload.note
        assigned_waiter_id = active_order.waiter_id

    # Bildirishnoma DB da saqlanadi
    notif = await create_notification(
        db=db,
        restaurant_id=table.restaurant_id,
        ntype=NotificationType.CALL_WAITER,
        title=f"Ofitsiant chaqirildi — Stol #{table.number}",
        message=payload.note or f"Stol #{table.number} da ofitsiant yordami so'ralmoqda",
        target=NotificationTarget.WAITER,
        data={
            "table_id": table.id,
            "table_number": table.number,
            "room": table.room,
            "note": payload.note,
            "order_id": active_order.id if active_order else None,
        },
        user_id=assigned_waiter_id,
    )
    await db.flush()
    await db.commit()

    # Real-time WebSocket xabari
    call_msg = {
        "id": notif.id,
        "type": "call_waiter",
        "table_id": table.id,
        "table_number": table.number,
        "room": table.room,
        "note": payload.note or "Ofitsiant yordami kerak",
        "order_id": active_order.id if active_order else None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    await manager.broadcast_to_roles(table.restaurant_id, ["waiter", "admin"], call_msg)

    # Telegram orqali xodimlar guruhiga bildirishnoma
    set_res = await db.execute(select(RestaurantSettings).where(RestaurantSettings.restaurant_id == table.restaurant_id))
    settings = set_res.scalar_one_or_none()
    if settings and settings.enable_telegram_notifications and settings.telegram_bot_token and settings.telegram_chat_id:
        tg_text = (
            f"🔔 <b>Ofitsiant chaqirildi!</b>\n"
            f"📍 <b>Joy:</b> {table.room or 'Zal'} — Stol #{table.number}\n"
            f"💬 <b>Izoh:</b> {payload.note or 'Yordam kerak'}\n"
            f"⏰ <b>Vaqt:</b> {datetime.now().strftime('%H:%M')}"
        )
        await send_telegram_alert(settings.telegram_bot_token, settings.telegram_chat_id, tg_text)

    # Mijozga qabul qilinganligi xabari
    await manager.broadcast_to_table(
        table.restaurant_id,
        table.id,
        {
            "type": "waiter_called",
            "message": "Ofitsiantga xabar berildi, tez orada yetib keladi!",
        },
    )

    return {"success": True, "call_id": notif.id, "message": f"Stol #{table.number} uchun ofitsiant chaqirildi"}


# ─── Faol chaqiruvlar ro'yxati (Ofitsiant & Admin) ─────────────
@router.get("/calls", response_model=List[WaiterCallResponse], summary="Faol chaqiruvlar ro'yxati")
async def list_waiter_calls(
    restaurant_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("waiter", "admin", "developer")),
):
    """Ofitsiant va Admin uchun barcha faol (o'qilmagan / yakunlanmagan) chaqiruvlar"""
    notif_res = await db.execute(
        select(Notification)
        .where(
            Notification.restaurant_id == restaurant_id,
            Notification.type == NotificationType.CALL_WAITER,
            Notification.is_read == False,
        )
        .order_by(Notification.created_at.desc())
    )
    notifications = notif_res.scalars().all()

    calls = []
    seen_table_ids = set()

    for n in notifications:
        data = n.data or {}
        table_id = data.get("table_id")
        table_number = data.get("table_number")
        room = data.get("room")
        note = data.get("note") or n.message
        order_id = data.get("order_id")

        if not table_number and table_id:
            t_res = await db.execute(select(Table).where(Table.id == table_id))
            t = t_res.scalar_one_or_none()
            if t:
                table_number = t.number
                room = t.room

        calls.append(
            WaiterCallResponse(
                id=n.id,
                type="call_waiter",
                table_id=table_id or 0,
                table_number=table_number or 0,
                room=room,
                note=note,
                order_id=order_id,
                created_at=n.created_at,
                is_resolved=False,
            )
        )
        if table_id:
            seen_table_ids.add(table_id)

    # Shuningdek order.call_waiter == True bo'lgan lekin yuqorida chiqmagan bo'lsa
    order_res = await db.execute(
        select(Order)
        .options(selectinload(Order.table))
        .where(
            Order.restaurant_id == restaurant_id,
            Order.call_waiter == True,
            Order.status.in_([
                OrderStatus.PENDING,
                OrderStatus.CONFIRMED,
                OrderStatus.PREPARING,
                OrderStatus.READY,
                OrderStatus.SERVED,
            ]),
        )
    )
    call_orders = order_res.scalars().all()
    for o in call_orders:
        if o.table_id not in seen_table_ids:
            calls.append(
                WaiterCallResponse(
                    id=100000 + o.id,
                    type="call_waiter",
                    table_id=o.table_id,
                    table_number=o.table.number if o.table else o.table_id,
                    room=o.table.room if o.table else None,
                    note=o.call_note or "Ofitsiant yordami kerak",
                    order_id=o.id,
                    created_at=o.updated_at or o.created_at,
                    is_resolved=False,
                )
            )

    return calls


# ─── Chaqiruvni yakunlash (Bordim) ───────────────────────────
@router.post("/calls/{call_id}/resolve", summary="Ofitsiant chaqiruvini yakunlash")
async def resolve_waiter_call(
    call_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("waiter", "admin", "developer")),
):
    """Ofitsiant yoki Admin chaqiruv bo'yicha mijozga xizmat ko'rsatganini tasdiqlaydi"""
    table_id = None
    table_num = None
    restaurant_id = current_user.restaurant_id or 1

    if call_id < 100000:
        notif_res = await db.execute(
            select(Notification).where(Notification.id == call_id)
        )
        notif = notif_res.scalar_one_or_none()
        if notif:
            notif.is_read = True
            notif.read_at = datetime.now(timezone.utc)
            restaurant_id = notif.restaurant_id
            data = notif.data or {}
            table_id = data.get("table_id")
            table_num = data.get("table_number")
            order_id = data.get("order_id")
            if order_id:
                o_res = await db.execute(select(Order).where(Order.id == order_id))
                o = o_res.scalar_one_or_none()
                if o:
                    o.call_waiter = False
                    o.call_status = CallStatus.COMPLETED
    else:
        order_id = call_id - 100000
        o_res = await db.execute(
            select(Order).options(selectinload(Order.table)).where(Order.id == order_id)
        )
        o = o_res.scalar_one_or_none()
        if o:
            o.call_waiter = False
            o.call_status = CallStatus.COMPLETED
            restaurant_id = o.restaurant_id
            table_id = o.table_id
            table_num = o.table.number if o.table else o.table_id

    if table_id:
        await db.execute(
            update(Notification)
            .where(
                Notification.restaurant_id == restaurant_id,
                Notification.type == NotificationType.CALL_WAITER,
                Notification.is_read == False,
            )
            .values(is_read=True, read_at=datetime.now(timezone.utc))
        )
        st_orders = await db.execute(
            select(Order).where(Order.table_id == table_id, Order.call_waiter == True)
        )
        for st_o in st_orders.scalars().all():
            st_o.call_waiter = False
            st_o.call_status = CallStatus.COMPLETED

    await db.flush()
    await db.commit()

    waiter_display = current_user.full_name or current_user.username
    await manager.broadcast_to_roles(
        restaurant_id,
        ["waiter", "admin"],
        {
            "type": "call_completed",
            "call_id": call_id,
            "table_id": table_id,
            "table_number": table_num,
            "waiter_name": waiter_display,
            "message": f"Stol #{table_num or ''} chaqiruvi {waiter_display} tomonidan yakunlandi",
        },
    )

    return {"success": True, "message": "Chaqiruv yakunlandi"}


# ─── Stolning faol buyurtmalari (Mijoz & Xodimlar) ─────────────
@router.get("/table/{table_id}/active", response_model=List[OrderResponse], summary="Stolning faol buyurtmalari")
async def get_table_active_orders(
    table_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Mijoz yoki xodim ushbu stoldagi barcha faol (to'lanmagan) buyurtmalarni ko'radi"""
    result = await db.execute(
        select(Order)
        .options(
            selectinload(Order.items).selectinload(OrderItem.menu_item),
            selectinload(Order.table),
            selectinload(Order.waiter),
        )
        .where(
            Order.table_id == table_id,
            Order.is_paid == False,
            Order.status.in_([
                OrderStatus.PENDING,
                OrderStatus.CONFIRMED,
                OrderStatus.PREPARING,
                OrderStatus.READY,
                OrderStatus.SERVED,
            ]),
        )
        .order_by(Order.created_at.desc())
    )
    orders = result.scalars().all()
    return [build_order_response(o) for o in orders]



# ─── Buyurtmalar ro'yxati ─────────────────────────────────
@router.get("/", response_model=List[OrderSummary], summary="Buyurtmalar ro'yxati")
async def list_orders(
    restaurant_id: int,
    status: Optional[OrderStatus] = None,
    table_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "waiter", "chef", "developer")),
):
    query = select(Order).where(Order.restaurant_id == restaurant_id)

    if status:
        query = query.where(Order.status == status)
    if table_id:
        query = query.where(Order.table_id == table_id)

    # Ofitsiant faqat o'ziga tayinlangan yoki tayinlanmagan buyurtmalarni ko'rishi mumkin
    if current_user.role == UserRole.WAITER:
        query = query.where(
            (Order.waiter_id == current_user.id) | (Order.waiter_id == None)
        )

    query = query.order_by(Order.created_at.desc())
    result = await db.execute(query)
    orders = result.scalars().all()

    summaries = []
    for order in orders:
        items_result = await db.execute(
            select(func.count(OrderItem.id)).where(OrderItem.order_id == order.id)
        )
        items_count = items_result.scalar() or 0

        table_result = await db.execute(select(Table).where(Table.id == order.table_id))
        table = table_result.scalar_one_or_none()

        waiter_name = None
        if order.waiter_id:
            w_res = await db.execute(select(User).where(User.id == order.waiter_id))
            w = w_res.scalar_one_or_none()
            if w:
                waiter_name = w.full_name or w.username

        summaries.append(
            OrderSummary(
                id=order.id,
                order_number=order.order_number,
                table_id=order.table_id,
                table_number=table.number if table else None,
                waiter_id=order.waiter_id,
                waiter_name=waiter_name,
                status=order.status,
                total=order.total,
                items_count=items_count,
                created_at=order.created_at,
                ready_at=order.ready_at,
                served_at=order.served_at,
            )
        )
    return summaries


@router.get("/{order_id}", response_model=OrderResponse, summary="Buyurtma tafsiloti")
async def get_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Buyurtma holatini ko'rish (mijoz va xodimlar uchun)"""
    result = await db.execute(
        select(Order)
        .options(
            selectinload(Order.items).selectinload(OrderItem.menu_item),
            selectinload(Order.table),
            selectinload(Order.waiter),
        )
        .where(Order.id == order_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Buyurtma topilmadi")

    return build_order_response(order)


# ─── OFITSIANT: 'Yetkazib berdim' tugmasi ─────────────────
@router.patch("/{order_id}/deliver", response_model=OrderResponse, summary="Yetkazib berdim (Ofitsiant)")
async def deliver_order(
    order_id: int,
    payload: Optional[OrderDeliverRequest] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("waiter", "admin", "developer")),
):
    """
    Ofitsiant buyurtma qilingan mahsulotni olib borib bergandan keyin
    'Yetkazib berdim' tugmasini bosadi.
    - Status SERVED ga o'tadi
    - served_at vaqti saqlanadi
    - Agar ofitsiant belgilanmagan bo'lsa, hozirgi ofitsiant belgilanadi
    - Adminga bildirishnoma yuboriladi (DB + WebSocket)
    - Oshpaz, boshqa ofitsiantlar va mijozga WebSocket xabari uzatiladi
    """
    result = await db.execute(
        select(Order)
        .options(
            selectinload(Order.items).selectinload(OrderItem.menu_item),
            selectinload(Order.table),
            selectinload(Order.waiter),
        )
        .where(Order.id == order_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Buyurtma topilmadi")

    if order.status == OrderStatus.SERVED:
        raise HTTPException(status_code=400, detail="Bu buyurtma allaqachon yetkazib berilgan")

    if order.status == OrderStatus.CANCELLED:
        raise HTTPException(status_code=400, detail="Bekor qilingan buyurtmani yetkazib bo'lmaydi")

    now = datetime.now(timezone.utc)
    old_status = order.status
    order.status = OrderStatus.SERVED
    order.served_at = now

    # Agar ofitsiant tayinlanmagan bo'lsa, yetkazib bergan xodim tayinlanadi
    if not order.waiter_id and current_user.role == UserRole.WAITER:
        order.waiter_id = current_user.id

    # Agar stolda chaqiruv bo'lsa, yakunlangan deb belgilanadi
    if order.call_waiter:
        order.call_waiter = False
        order.call_status = CallStatus.COMPLETED

    waiter_display = current_user.full_name or current_user.username
    table_num = order.table.number if order.table else order.table_id

    # 1. Adminga bildirishnoma yaratish (DB)
    await create_notification(
        db=db,
        restaurant_id=order.restaurant_id,
        ntype=NotificationType.ORDER_DELIVERED,
        title=f"Yetkazib berildi — Stol #{table_num}",
        message=f"Ofitsiant {waiter_display} {order.order_number} buyurtmani stolga yetkazib berdi.",
        target=NotificationTarget.ADMIN,
        data={
            "order_id": order.id,
            "order_number": order.order_number,
            "table_id": order.table_id,
            "table_number": table_num,
            "waiter_id": current_user.id,
            "waiter_name": waiter_display,
            "served_at": now.isoformat(),
            "note": payload.note if payload else None,
        },
    )

    await db.flush()

    # 2. Real-time WebSocket: Adminga va xodimlarga
    delivered_event = {
        "type": "order_delivered",
        "order_id": order.id,
        "order_number": order.order_number,
        "table_id": order.table_id,
        "table_number": table_num,
        "waiter_id": current_user.id,
        "waiter_name": waiter_display,
        "status": OrderStatus.SERVED,
        "served_at": now.isoformat(),
        "note": payload.note if payload else None,
        "message": f"{order.order_number} stolga yetkazildi ({waiter_display})",
    }
    await manager.broadcast_to_roles(order.restaurant_id, ["admin", "chef", "waiter"], delivered_event)

    # 3. Real-time WebSocket: Mijoz stoliga
    await manager.broadcast_to_table(
        order.restaurant_id,
        order.table_id,
        {
            "type": "order_delivered",
            "order_id": order.id,
            "order_number": order.order_number,
            "status": "served",
            "title": "Taomingiz yetkazib berildi! 🍽️",
            "message": "Ofitsiant taomingizni yetkazib berdi. Yoqimli ishtaha!",
        },
    )

    order = await load_order_full(db, order.id) or order
    return build_order_response(order, table_num, waiter_display)


# ─── Status yangilash (Oshpaz + Ofitsiant + Admin) ─────────
@router.patch("/{order_id}/status", response_model=OrderResponse, summary="Status yangilash")
async def update_order_status(
    order_id: int,
    payload: OrderStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "waiter", "chef", "developer")),
):
    result = await db.execute(
        select(Order)
        .options(
            selectinload(Order.items).selectinload(OrderItem.menu_item),
            selectinload(Order.table),
            selectinload(Order.waiter),
        )
        .where(Order.id == order_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Buyurtma topilmadi")

    old_status = order.status
    order.status = payload.status
    now = datetime.now(timezone.utc)
    table_num = order.table.number if order.table else order.table_id

    # Vaqtlarni yangilash
    if payload.status == OrderStatus.CONFIRMED:
        order.confirmed_at = now
    elif payload.status == OrderStatus.PREPARING:
        order.preparing_at = now
        # Mijoz stoliga xabar
        await manager.broadcast_to_table(
            order.restaurant_id,
            order.table_id,
            {
                "type": "order_status",
                "order_id": order.id,
                "status": "preparing",
                "message": "Oshpaz taomingizni tayyorlashni boshladi 👨‍🍳",
            },
        )
    elif payload.status == OrderStatus.READY:
        order.ready_at = now
        # Oshpaz 'Tayyor' tugmasini bosdi -> Ofitsiant va Adminga bildirishnoma
        await create_notification(
            db=db,
            restaurant_id=order.restaurant_id,
            ntype=NotificationType.ORDER_READY,
            title=f"Ovqat tayyor — Stol #{table_num}",
            message=f"{order.order_number} buyurtmasi tayyor bo'ldi. Stol #{table_num} ga olib boring!",
            target=NotificationTarget.WAITER,
            data={
                "order_id": order.id,
                "order_number": order.order_number,
                "table_id": order.table_id,
                "table_number": table_num,
                "waiter_id": order.waiter_id,
            },
            user_id=order.waiter_id,
        )

        ready_msg = {
            "type": "order_ready",
            "order_id": order.id,
            "order_number": order.order_number,
            "table_id": order.table_id,
            "table_number": table_num,
            "waiter_id": order.waiter_id,
            "title": f"Ovqat tayyor! Stol #{table_num}",
            "message": f"{order.order_number} buyurtmasi tayyor. Mijozga yetkazing!",
        }

        # Agar tayinlangan ofitsiant bo'lsa, unga bevosita
        if order.waiter_id:
            await manager.send_to_user(order.restaurant_id, order.waiter_id, ready_msg)
        # Barcha ofitsiantlar va adminlarga
        await manager.broadcast_to_roles(order.restaurant_id, ["waiter", "admin"], ready_msg)

        # Mijoz stoliga
        await manager.broadcast_to_table(
            order.restaurant_id,
            order.table_id,
            {
                "type": "order_ready",
                "order_id": order.id,
                "status": "ready",
                "message": "Taomingiz tayyor bo'ldi, ofitsiant yo'lda! 🚀",
            },
        )

    elif payload.status == OrderStatus.SERVED:
        order.served_at = now
        # Yetkazildi xabari
        await create_notification(
            db=db,
            restaurant_id=order.restaurant_id,
            ntype=NotificationType.ORDER_DELIVERED,
            title=f"Yetkazib berildi — Stol #{table_num}",
            message=f"{order.order_number} buyurtma stolga yetkazildi.",
            target=NotificationTarget.ADMIN,
            data={"order_id": order.id, "table_id": order.table_id, "table_number": table_num},
        )
    elif payload.status == OrderStatus.PAID:
        order.is_paid = True
        # Tekshirish: stolda boshqa to'lanmagan buyurtmalar bormi?
        other_orders_res = await db.execute(
            select(func.count(Order.id)).where(
                Order.table_id == order.table_id,
                Order.id != order.id,
                Order.is_paid == False,
                Order.status != OrderStatus.CANCELLED,
            )
        )
        remaining = other_orders_res.scalar() or 0
        if remaining == 0 and order.table:
            order.table.status = TableStatus.AVAILABLE

    # Umumiy status o'zgarishi haqida adminga bildirishnoma
    await create_notification(
        db=db,
        restaurant_id=order.restaurant_id,
        ntype=NotificationType.ORDER_STATUS_CHANGED,
        title="Buyurtma holati o'zgardi",
        message=f"{order.order_number}: {old_status} → {payload.status}",
        target=NotificationTarget.ADMIN,
        data={"order_id": order.id, "old_status": old_status, "new_status": payload.status},
    )

    await db.flush()

    # WebSocket orqali status yangilanishini tarqatish
    await manager.broadcast_to_restaurant(
        order.restaurant_id,
        {
            "type": "order_status_updated",
            "order_id": order.id,
            "order_number": order.order_number,
            "old_status": old_status,
            "new_status": payload.status,
            "table_id": order.table_id,
            "table_number": table_num,
        },
    )

    order = await load_order_full(db, order.id) or order
    return build_order_response(order)


# ─── Oshpaz: alohida elementni tayyorlash ─────────────────
@router.patch("/{order_id}/items/{item_id}/prepared", summary="Element tayyor (Oshpaz)")
async def mark_item_prepared(
    order_id: int,
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("chef", "admin")),
):
    result = await db.execute(
        select(OrderItem).where(OrderItem.id == item_id, OrderItem.order_id == order_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Element topilmadi")

    item.is_prepared = True
    item.prepared_at = datetime.now(timezone.utc)

    # Buyurtmadagi barcha elementlar tayyormi?
    all_result = await db.execute(
        select(OrderItem).where(OrderItem.order_id == order_id)
    )
    all_items = all_result.scalars().all()

    all_ready = all(i.is_prepared for i in all_items)
    order_ready_now = False

    if all_ready:
        order_result = await db.execute(
            select(Order)
            .options(selectinload(Order.table), selectinload(Order.waiter))
            .where(Order.id == order_id)
        )
        order = order_result.scalar_one_or_none()
        if order and order.status in [OrderStatus.PENDING, OrderStatus.CONFIRMED, OrderStatus.PREPARING]:
            order.status = OrderStatus.READY
            order.ready_at = datetime.now(timezone.utc)
            order_ready_now = True

            table_num = order.table.number if order.table else order.table_id

            # Bildirishnoma DB
            await create_notification(
                db=db,
                restaurant_id=order.restaurant_id,
                ntype=NotificationType.ORDER_READY,
                title=f"Barcha taomlar tayyor — Stol #{table_num}",
                message=f"{order.order_number} ning barcha taomlari tayyor. Stol #{table_num} ga yetkazing!",
                target=NotificationTarget.WAITER,
                data={
                    "order_id": order.id,
                    "order_number": order.order_number,
                    "table_id": order.table_id,
                    "table_number": table_num,
                    "waiter_id": order.waiter_id,
                },
                user_id=order.waiter_id,
            )

            ready_msg = {
                "type": "order_ready",
                "order_id": order.id,
                "order_number": order.order_number,
                "table_id": order.table_id,
                "table_number": table_num,
                "waiter_id": order.waiter_id,
                "title": f"Barcha taomlar tayyor! Stol #{table_num}",
                "message": f"{order.order_number} to'liq tayyor bo'ldi. Olib boring!",
            }
            if order.waiter_id:
                await manager.send_to_user(order.restaurant_id, order.waiter_id, ready_msg)
            await manager.broadcast_to_roles(order.restaurant_id, ["waiter", "admin"], ready_msg)

            await manager.broadcast_to_table(
                order.restaurant_id,
                order.table_id,
                {
                    "type": "order_ready",
                    "order_id": order.id,
                    "status": "ready",
                    "message": "Barcha taomlaringiz tayyor bo'ldi! Ofitsiant yo'lda.",
                },
            )

    await db.flush()
    return {
        "success": True,
        "item_id": item_id,
        "is_prepared": True,
        "order_ready": order_ready_now,
    }


# ─── Ofitsiant chaqiruvini yakunlash ──────────────────────
@router.patch("/{order_id}/call/complete", summary="Chaqiruvni yakunlash")
async def complete_waiter_call(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("waiter", "admin")),
):
    """Ofitsiant chaqiruv bo'yicha mijoz oldiga bordi va yordam berdi"""
    result = await db.execute(
        select(Order).options(selectinload(Order.table)).where(Order.id == order_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Buyurtma topilmadi")

    order.call_waiter = False
    order.call_status = CallStatus.COMPLETED

    table_num = order.table.number if order.table else order.table_id

    await manager.broadcast_to_roles(
        order.restaurant_id,
        ["waiter", "admin"],
        {
            "type": "call_completed",
            "order_id": order.id,
            "table_id": order.table_id,
            "table_number": table_num,
            "waiter_name": current_user.full_name or current_user.username,
        },
    )

    return {"success": True, "message": "Chaqiruv yakunlandi"}
