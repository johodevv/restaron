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
from app.models.notification import Notification, NotificationType, NotificationTarget
from app.schemas.order import (
    OrderCreate, OrderResponse, OrderSummary,
    OrderStatusUpdate, CallWaiterRequest, OrderDeliverRequest,
    OrderItemResponse, WaiterCallResponse
)
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
                is_prepared=item.is_prepared,
                prepared_at=item.prepared_at,
                menu_item_name=item.menu_item.name if item.menu_item else None,
                menu_item_image=item.menu_item.image_url if item.menu_item else None,
            )
        )

    t_num = table_number if table_number is not None else (order.table.number if order.table else None)
    w_name = waiter_name if waiter_name is not None else (
        (order.waiter.full_name or order.waiter.username) if order.waiter else None
    )

    return OrderResponse(
        id=order.id,
        order_number=order.order_number,
        restaurant_id=order.restaurant_id,
        table_id=order.table_id,
        table_number=t_num,
        waiter_id=order.waiter_id,
        waiter_name=w_name,
        customer_name=order.customer_name,
        customer_note=order.customer_note,
        status=order.status,
        subtotal=order.subtotal,
        discount=order.discount,
        total=order.total,
        is_paid=order.is_paid,
        call_waiter=order.call_waiter,
        call_status=order.call_status,
        call_note=order.call_note,
        items=items_response,
        created_at=order.created_at,
        preparing_at=order.preparing_at,
        ready_at=order.ready_at,
        served_at=order.served_at,
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

    await db.refresh(order)
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

    await db.refresh(order)
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
