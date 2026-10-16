"""
Buyurtmalar API — Mijoz, Ofitsiant, Oshpaz, Admin
To'liq WebSocket integratsiyasi va 'Yetkazib berdim' funksiyasi bilan
"""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, update, text
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError
from typing import List, Optional

from app.core.database import get_db
from app.core.rate_limit import RateLimiter
from app.core.security import get_current_user, get_optional_current_user, require_role
from app.models.order import Order, OrderItem, OrderStatus, CallStatus
from app.models.menu import MenuItem, Category
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
    UpdateItemSizeRequest,
    UpdateItemWeightRequest,
    OrderNoteUpdate, OrderCheckoutRequest
)
from app.core.printer_service import (
    format_kitchen_ticket, format_pre_check, async_print_to_windows_printer,
    DEFAULT_FONT_SIZE, printer_options, receipt_title,
)
from app.core.printer_queue import print_with_retry, printer_queue
from app.core.sms_telegram import send_telegram_alert
from app.websockets.manager import manager

router = APIRouter(prefix="/orders", tags=["📋 Buyurtmalar"])


def generate_order_number(restaurant_id: int, count: int) -> str:
    """Buyurtma raqami formati: #R1-0001"""
    return f"#R{restaurant_id}-{count:04d}"


async def get_next_order_sequence(db: AsyncSession, restaurant_id: int) -> int:
    """
    MAX(id) asosida keyingi sequence raqamni olish.
    COUNT yerine MAX ishlatiladi: o'chirilgan buyurtmalar COUNT ni kamaytiradi,
    lekin MAX hech qachon kamaymaydi — bu race condition va duplicate ni to'liq bartaraf etadi.
    """
    result = await db.execute(
        select(func.max(Order.id)).where(Order.restaurant_id == restaurant_id)
    )
    max_id = result.scalar() or 0
    # Barcha restoran buyurtmalari uchun global max ni ham hisoblaymiz
    # chunki order_number UNIQUE constraint global (restaurant prefix bilan ajratiladi)
    return max_id + 1


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
    Eng kam faol buyurtmaga ega bo'lgan faol ofitsiantni bitta SQL query orqali tanlash
    """
    active_statuses = [
        OrderStatus.PENDING,
        OrderStatus.CONFIRMED,
        OrderStatus.PREPARING,
        OrderStatus.READY,
    ]
    query = (
        select(User)
        .outerjoin(
            Order,
            and_(
                Order.waiter_id == User.id,
                Order.status.in_(active_statuses),
            ),
        )
        .where(
            User.restaurant_id == restaurant_id,
            User.role == UserRole.WAITER,
            User.is_active == True,
        )
        .group_by(User.id)
        .order_by(func.count(Order.id).asc(), User.id.asc())
        .limit(1)
    )
    res = await db.execute(query)
    return res.scalar_one_or_none()


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


DEFAULT_SERVICE_FEE = 12.0


def order_fee_percent(order: Order, fallback: Optional[float] = None) -> float:
    """Buyurtmaning xizmat haqi foizi.

    MUHIM: 0% ham HAQIQIY qiymat. Ilgari `order.service_fee_percent or 12`
    deb yozilgandi va kassir "xizmat haqi olinmasin" deb 0% qo'yganda
    u jimgina 12% ga aylanib ketardi — mijozdan ortiqcha pul olinardi.
    """
    v = order.service_fee_percent
    if v is None:
        v = fallback if fallback is not None else DEFAULT_SERVICE_FEE
    return float(v)


def line_total(menu_item: MenuItem, quantity: int, weight: Optional[float],
               manual_price: Optional[float] = None) -> float:
    """Bitta qator summasi.

    Tortiladigan taom (baliq, go'sht) uchun ikki yo'l bor:

    1. Ofitsiant SUMMANI o'zi yozadi (`manual_price`) — asosiy yo'l.
       Tarozi pulni ko'rsatadi, ofitsiant shuni kiritadi va summa
       boshqa hech qayerda qayta hisoblanmaydi.
    2. Og'irlik (kg) kiritiladi — summa 1 kg narxiga ko'paytiriladi.

    Ikkisi ham bo'lmasa 0 qaytariladi: narxni taxmin qilib yozib qo'yish
    mijoz bilan nizoga olib keladi.
    """
    if manual_price is not None and manual_price >= 0:
        return round(float(manual_price), 2)

    price = menu_item.price or 0.0
    if getattr(menu_item, "is_weighted", False):
        if not weight or weight <= 0:
            return 0.0
        return round(price * float(weight) * max(1, quantity), 2)
    return round(price * quantity, 2)


def item_is_priced(it: OrderItem) -> bool:
    """Tortiladigan taomning narxi aniqmi (summa yoki og'irlik kiritilganmi)."""
    if it.manual_price is not None and it.manual_price >= 0:
        return True
    return bool(it.weight and it.weight > 0)


def missing_weight_items(order: Order) -> List[str]:
    """Narxi hali aniqlanmagan tortiladigan taomlar ro'yxati.

    Ofitsiant summani yozgan bo'lsa (manual_price) — taom tayyor,
    og'irlik kiritilishi SHART EMAS.
    """
    names = []
    for it in order.items:
        mi = it.menu_item
        if mi and getattr(mi, "is_weighted", False) and not item_is_priced(it):
            names.append(mi.name)
    return names


async def recalc_order_totals(db: AsyncSession, order: Order) -> None:
    """Buyurtma summalarini qatorlardan qayta hisoblash (xotiradagi items tekshiriladi)"""
    from sqlalchemy import inspect as sa_inspect
    insp = sa_inspect(order)
    if insp and "items" in insp.dict and order.items is not None:
        subtotal = sum((i.total_price or 0.0) for i in order.items)
    else:
        res = await db.execute(select(OrderItem).where(OrderItem.order_id == order.id))
        subtotal = sum((i.total_price or 0.0) for i in res.scalars().all())
    fee_pct = order_fee_percent(order)
    order.subtotal = round(subtotal, 2)
    order.service_fee_amount = round(subtotal * (fee_pct / 100.0), 2)
    order.total = round(subtotal + order.service_fee_amount - (order.discount or 0.0), 2)


def build_order_response(order: Order, table_number: Optional[int] = None, waiter_name: Optional[str] = None) -> OrderResponse:
    """OrderResponse obyektini xavfsiz va to'liq yaratish"""
    items_response = []
    for item in (order.items or []):
        menu_item = getattr(item, "menu_item", None)
        items_response.append(
            OrderItemResponse(
                id=item.id,
                menu_item_id=item.menu_item_id,
                quantity=item.quantity,
                unit_price=item.unit_price,
                total_price=item.total_price,
                special_note=item.special_note,
                portion_size=item.portion_size,
                item_time=item.item_time,
                weight=item.weight,
                manual_price=item.manual_price,
                is_weighted=bool(getattr(menu_item, "is_weighted", False)) if menu_item else False,
                unit=(getattr(menu_item, "unit", "dona") or "dona") if menu_item else "dona",
                sent_to_kitchen=bool(item.sent_to_kitchen),
                sent_to_kitchen_at=item.sent_to_kitchen_at,
                sent_quantity=int(item.sent_quantity or 0),
                is_prepared=bool(item.is_prepared),
                prepared_at=item.prepared_at,
                menu_item_name=menu_item.name if menu_item else None,
                menu_item_image=menu_item.image_url if menu_item else None,
            )
        )

    tbl = getattr(order, "table", None)
    t_num = table_number if table_number is not None else (tbl.number if tbl else None)
    t_room = tbl.room if tbl else None
    wtr = getattr(order, "waiter", None)
    w_name = waiter_name if waiter_name is not None else (
        (wtr.full_name or wtr.username) if wtr else None
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
        customer_phone=getattr(order, "customer_phone", None),
        customer_note=order.customer_note,
        delivery_address=getattr(order, "delivery_address", None),
        order_type=order.order_type or "table",
        hall_name=order.hall_name or t_room,
        kitchen_note=order.kitchen_note,
        receipt_note=order.receipt_note,
        status=order.status,
        subtotal=order.subtotal or 0.0,
        service_fee_percent=order_fee_percent(order),
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
@router.post(
    "/",
    response_model=OrderResponse,
    status_code=201,
    summary="Buyurtma berish (mijoz)",
    dependencies=[
        Depends(
            RateLimiter(
                times=5,
                seconds=60,
                detail="Qisqa vaqt ichida juda ko'p buyurtma yuborildi. Iltimos, 1 daqiqadan so'ng qayta urinib ko'ring.",
            )
        )
    ],
)
async def create_order(payload: OrderCreate, db: AsyncSession = Depends(get_db)):
    """QR orqali yoki onlayn kirgan mijoz buyurtma beradi (auth talab qilinmaydi, rate-limit va validatsiya bilan)"""
    table = None
    table_id = payload.table_id
    norm_order_type = payload.order_type or ("dine_in" if table_id else "takeaway")
    if norm_order_type == "table":
        norm_order_type = "dine_in"

    if table_id:
        result = await db.execute(select(Table).where(Table.id == table_id))
        table = result.scalar_one_or_none()
        if not table or not table.is_active:
            raise HTTPException(status_code=404, detail="Stol topilmadi yoki faol emas")
        restaurant_id = table.restaurant_id
    else:
        if not payload.restaurant_id:
            raise HTTPException(
                status_code=400,
                detail="Stolsiz buyurtma (takeaway yoki delivery) uchun restaurant_id ko'rsatilishi shart"
            )
        restaurant_id = payload.restaurant_id

    # Delivery uchun telefon va manzil tekshiruvi
    if norm_order_type == "delivery":
        if not payload.customer_phone:
            raise HTTPException(
                status_code=400,
                detail="Yetkazib berish (delivery) uchun mijoz telefon raqami kiritilishi shart"
            )
        if not payload.delivery_address:
            raise HTTPException(
                status_code=400,
                detail="Yetkazib berish (delivery) uchun yetkazish manzili kiritilishi shart"
            )

    # Restoran sozlamalarini tekshirish
    set_res = await db.execute(select(RestaurantSettings).where(RestaurantSettings.restaurant_id == restaurant_id))
    settings = set_res.scalar_one_or_none()
    if settings:
        if table:
            qr_allowed = bool(settings.allow_orders_from_qr)
            general_allowed = bool(settings.allow_orders)
            if not qr_allowed and not general_allowed:
                raise HTTPException(
                    status_code=400,
                    detail="Hurmatli mijoz! Ushbu restoranda QR orqali buyurtma berish vaqtincha to'xtatilgan. Buyurtmani ofitsiant stolingizga kelib qabul qiladi."
                )
        else:
            if not bool(settings.allow_orders):
                raise HTTPException(
                    status_code=400,
                    detail="Hurmatli mijoz! Ushbu restoranda onlayn buyurtma berish vaqtincha to'xtatilgan."
                )

    # Agar stol mavjud bo'lsa, holatini band qilish
    if table:
        table.status = TableStatus.OCCUPIED

    # Avtomatik ofitsiant tayinlash
    assigned_waiter = await auto_assign_waiter(db, restaurant_id)

    # Buyurtma raqamini aniqlash (MAX asosida, race-condition safe)
    seq = await get_next_order_sequence(db, restaurant_id)
    order_number = generate_order_number(restaurant_id, seq)

    order = Order(
        order_number=order_number,
        restaurant_id=restaurant_id,
        table_id=table.id if table else None,
        waiter_id=assigned_waiter.id if assigned_waiter else None,
        order_type=norm_order_type,
        customer_name=payload.customer_name,
        customer_phone=payload.customer_phone,
        delivery_address=payload.delivery_address,
        customer_note=payload.customer_note,
        status=OrderStatus.PENDING,
    )
    db.add(order)
    await db.flush()

    subtotal = 0.0
    items_details = []
    for item_data in payload.items:
        item_result = await db.execute(
            select(MenuItem)
            .join(Category, Category.id == MenuItem.category_id)
            .where(
                MenuItem.id == item_data.menu_item_id,
                Category.restaurant_id == restaurant_id,
                MenuItem.is_available == True,
                MenuItem.is_stop_list == False,
            )
        )
        menu_item = item_result.scalar_one_or_none()
        if not menu_item:
            raise HTTPException(
                status_code=404,
                detail=f"Taom #{item_data.menu_item_id} topilmadi, mavjud emas yoki stop-listda",
            )

        total_price = line_total(menu_item, item_data.quantity, item_data.weight)
        subtotal += total_price

        order_item = OrderItem(
            order_id=order.id,
            menu_item_id=item_data.menu_item_id,
            quantity=item_data.quantity,
            unit_price=menu_item.price,
            total_price=total_price,
            special_note=item_data.special_note,
            portion_size=(item_data.portion_size or None),
            weight=item_data.weight,
        )
        db.add(order_item)
        menu_item.total_ordered = (menu_item.total_ordered or 0) + item_data.quantity

        items_details.append({
            "name": menu_item.name,
            "quantity": item_data.quantity,
            "price": menu_item.price,
            "note": item_data.special_note,
            "size": item_data.portion_size,
        })

    order.subtotal = subtotal
    order.total = subtotal

    waiter_name = (assigned_waiter.full_name or assigned_waiter.username) if assigned_waiter else None
    order_type_label = "Yetkazib berish" if norm_order_type == "delivery" else ("Olib ketish" if norm_order_type == "takeaway" else f"Stol #{table.number if table else ''}")

    # Bildirishnoma (DB)
    await create_notification(
        db=db,
        restaurant_id=restaurant_id,
        ntype=NotificationType.NEW_ORDER,
        title=f"Yangi buyurtma — {order_type_label}",
        message=f"{order_number} buyurtma keldi. Jami: {subtotal:,.0f} so'm. Xodim: {waiter_name or 'Tayinlanmagan'}",
        target=NotificationTarget.ALL_STAFF,
        data={
            "order_id": order.id,
            "order_number": order_number,
            "table_id": table.id if table else None,
            "table_number": table.number if table else None,
            "order_type": norm_order_type,
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
        "table_id": table.id if table else None,
        "table_number": table.number if table else None,
        "order_type": norm_order_type,
        "waiter_id": assigned_waiter.id if assigned_waiter else None,
        "waiter_name": waiter_name,
        "customer_name": order.customer_name,
        "customer_phone": order.customer_phone,
        "delivery_address": order.delivery_address,
        "customer_note": order.customer_note,
        "subtotal": subtotal,
        "total": subtotal,
        "items": items_details,
        "created_at": order.created_at.isoformat() if order.created_at else datetime.now(timezone.utc).isoformat(),
    }

    # Oshpaz, Ofitsiant va Adminga
    await manager.broadcast_to_roles(restaurant_id, ["chef", "waiter", "admin"], ws_payload)

    # Agar ofitsiant biriktirilgan bo'lsa, unga maxsus shaxsiy bildirishnoma
    if assigned_waiter:
        await manager.send_to_user(
            restaurant_id,
            assigned_waiter.id,
            {
                "type": "order_assigned",
                "title": f"Sizga buyurtma tayinlandi — {order_type_label}",
                "message": f"Buyurtma {order_number} sizga biriktirildi.",
                "order_id": order.id,
                "table_id": table.id if table else None,
                "table_number": table.number if table else None,
            },
        )

    # Agar stoldan berilgan bo'lsa, stoldagi mijozga tasdiq
    if table:
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
    return build_order_response(full_order, table.number if table else None, waiter_name)


# ─── Ofitsiant / Kassa: Yangi buyurtma yaratish (Ali Poster POS) ───
@router.post("/waiter-create", response_model=OrderResponse, status_code=201, summary="Buyurtma yaratish (Ofitsiant / Kassa POS)")
async def waiter_create_order(
    payload: WaiterOrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("waiter", "admin", "developer", "cashier")),
):
    """Ofitsiant yoki kassir stol, olib ketish (s soboy) yoki yetkazish uchun buyurtma yaratadi"""
    table = None
    table_id = payload.table_id
    hall_name = payload.hall_name
    norm_order_type = payload.order_type or "dine_in"
    if norm_order_type == "table":
        norm_order_type = "dine_in"

    if table_id:
        result = await db.execute(select(Table).where(Table.id == table_id))
        table = result.scalar_one_or_none()
        if not table:
            raise HTTPException(status_code=404, detail="Stol topilmadi")
        table.status = TableStatus.OCCUPIED
        if not hall_name:
            hall_name = table.room or f"Zal"

        # Stolda allaqachon to'lanmagan faol buyurtma mavjud bo'lsa,
        # yangi dublikat hisob ochmasdan mavjud buyurtmaga biriktiramiz:
        existing_order_res = await db.execute(
            select(Order)
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
        existing_order = existing_order_res.scalars().first()
        if existing_order:
            if payload.items:
                return await waiter_add_items(
                    order_id=existing_order.id,
                    payload=WaiterAddItemsRequest(items=payload.items, send_to_kitchen_immediately=False),
                    db=db,
                    current_user=current_user,
                )
            else:
                loaded = await load_order_full(db, existing_order.id)
                return build_order_response(loaded or existing_order)
    else:
        # Takeaway va Delivery uchun avtomatik zal/manzil nomi
        if not hall_name:
            if norm_order_type == "delivery":
                hall_name = "Yetkazib berish"
            elif norm_order_type == "takeaway":
                hall_name = "Olib ketish"
            else:
                hall_name = "Kassa"

    # Restoran sozlamalarini olish (xizmat foizi)
    set_res = await db.execute(select(RestaurantSettings).where(RestaurantSettings.restaurant_id == payload.restaurant_id))
    settings = set_res.scalar_one_or_none()
    service_fee_pct = settings.service_fee_percent if settings else 12.0

    # Buyurtma raqami (Bug 1 fix: MAX asosida, race-condition safe)
    seq = await get_next_order_sequence(db, payload.restaurant_id)
    order_number = generate_order_number(payload.restaurant_id, seq)

    # Delivery/takeaway da table_id=None
    resolved_table_id = table_id if table else None

    order = Order(
        order_number=order_number,
        restaurant_id=payload.restaurant_id,
        table_id=resolved_table_id,
        waiter_id=current_user.id,
        order_type=norm_order_type,
        hall_name=hall_name,
        customer_name=payload.customer_name,
        customer_phone=payload.customer_phone,
        delivery_address=payload.delivery_address,
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
            # Bug 3 fix: continue o'rniga 404 xato — ofitsiant kamroq taomli buyurtma
            # yaratganini bilmay qoladi. Aniq xato xabar ko'rsatish to'g'riroq.
            raise HTTPException(
                status_code=404,
                detail=f"Taom #{item_data.menu_item_id} menuda topilmadi yoki mavjud emas",
            )

        tot_price = line_total(menu_item, item_data.quantity, item_data.weight)
        subtotal += tot_price

        order_item = OrderItem(
            order_id=order.id,
            menu_item_id=item_data.menu_item_id,
            quantity=item_data.quantity,
            unit_price=menu_item.price,
            total_price=tot_price,
            special_note=item_data.special_note,
            portion_size=(item_data.portion_size or None),
            weight=item_data.weight,
            item_time=now_time_str,
            sent_to_kitchen=False,
            sent_quantity=0,
        )
        db.add(order_item)
        menu_item.total_ordered = (menu_item.total_ordered or 0) + item_data.quantity
        items_details.append({
            "name": menu_item.name,
            "quantity": item_data.quantity,
            "price": menu_item.price,
            "note": item_data.special_note,
            "size": item_data.portion_size,
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
    current_user: User = Depends(require_role("waiter", "admin", "developer", "cashier")),
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

        tot_price = line_total(menu_item, item_data.quantity, item_data.weight)
        new_subtotal += tot_price

        order_item = OrderItem(
            order_id=order.id,
            menu_item_id=item_data.menu_item_id,
            quantity=item_data.quantity,
            unit_price=menu_item.price,
            total_price=tot_price,
            special_note=item_data.special_note,
            portion_size=(item_data.portion_size or None),
            weight=item_data.weight,
            item_time=now_time_str,
            sent_to_kitchen=payload.send_to_kitchen_immediately,
            sent_to_kitchen_at=datetime.now(timezone.utc) if payload.send_to_kitchen_immediately else None,
            sent_quantity=(item_data.quantity if payload.send_to_kitchen_immediately else 0),
        )
        db.add(order_item)
        menu_item.total_ordered = (menu_item.total_ordered or 0) + item_data.quantity
        added_details.append({
            "name": menu_item.name,
            "quantity": item_data.quantity,
            "price": menu_item.price,
            "note": item_data.special_note,
            "size": item_data.portion_size,
            "item_time": now_time_str,
        })

    order.subtotal = new_subtotal
    fee_pct = order_fee_percent(order)
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
    current_user: User = Depends(require_role("waiter", "admin", "developer", "cashier")),
):
    item_res = await db.execute(
        select(OrderItem).where(OrderItem.id == item_id, OrderItem.order_id == order_id)
    )
    order_item = item_res.scalar_one_or_none()
    if not order_item:
        raise HTTPException(status_code=404, detail="Taom topilmadi")

    order_item.quantity = payload.quantity
    # Tortiladigan taomda narx og'irlikka bog'liq, shuning uchun
    # oddiy "narx x soni" emas, umumiy hisoblagichdan foydalanamiz.
    mi_res = await db.execute(select(MenuItem).where(MenuItem.id == order_item.menu_item_id))
    menu_item = mi_res.scalar_one_or_none()
    if menu_item:
        order_item.total_price = line_total(
            menu_item, payload.quantity, order_item.weight, order_item.manual_price
        )
    else:
        order_item.total_price = round((order_item.unit_price or 0.0) * payload.quantity, 2)

    order_res = await db.execute(
        select(Order).options(selectinload(Order.items).selectinload(OrderItem.menu_item), selectinload(Order.table), selectinload(Order.waiter)).where(Order.id == order_id)
    )
    order = order_res.scalar_one()
    await recalc_order_totals(db, order)

    await db.flush()
    order = await load_order_full(db, order_id) or order
    return build_order_response(order)


# ─── Tortilgan ANIQ og'irlikni kiritish (baliq 1.35 kg) ────────
@router.patch("/{order_id}/items/{item_id}/weight", response_model=OrderResponse,
              summary="Tortiladigan taom narxini (summa yoki og'irlik) kiritish")
async def update_item_weight(
    order_id: int,
    item_id: int,
    payload: UpdateItemWeightRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("waiter", "admin", "developer", "cashier")),
):
    """Tortiladigan taom (baliq, go'sht) narxini belgilash.

    Asosiy yo'l — ofitsiant tarozidagi SUMMANI o'zi yozadi (`price`):
    "baliqning kg sini emas, pulini yoz". Shunda summa boshqa hech
    qayerda qayta hisoblanmaydi.

    Istasa og'irlikni ham (`weight`) kiritadi — u chekda va oshxona
    begunogida ko'rinadi. Faqat og'irlik kiritilsa, summa eski yo'l
    bilan 1 kg narxiga ko'paytiriladi.
    """
    item_res = await db.execute(
        select(OrderItem)
        .options(selectinload(OrderItem.menu_item))
        .where(OrderItem.id == item_id, OrderItem.order_id == order_id)
    )
    order_item = item_res.scalar_one_or_none()
    if not order_item:
        raise HTTPException(status_code=404, detail="Taom topilmadi")

    order = await load_order_full(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Buyurtma topilmadi")
    if order.status in (OrderStatus.PAID, OrderStatus.CANCELLED):
        raise HTTPException(status_code=400, detail="Yopilgan buyurtmani o'zgartirib bo'lmaydi")

    menu_item = order_item.menu_item
    if not menu_item:
        raise HTTPException(status_code=400, detail="Taom menyuda topilmadi")
    if not getattr(menu_item, "is_weighted", False):
        raise HTTPException(
            status_code=400,
            detail=f"\"{menu_item.name}\" tortiladigan taom emas. Uni admin panelda "
                   f"\"Tortiladigan taom\" deb belgilang.",
        )

    has_price = payload.price is not None
    has_weight = payload.weight is not None and payload.weight > 0
    if not has_price and not has_weight:
        raise HTTPException(
            status_code=400,
            detail="Summani yoki og'irlikni kiriting.",
        )

    # Ofitsiant summani o'zi yozsa — shu summa qoladi. Faqat og'irlik
    # kiritilsa, eski yo'l bilan 1 kg narxiga ko'paytiriladi.
    order_item.manual_price = round(float(payload.price), 2) if has_price else None

    if has_weight:
        order_item.weight = payload.weight
    elif has_price:
        # OG'IRLIKNI O'ZIMIZ HISOBLAYMIZ: summa / 1 kg narxi.
        # Ofitsiant 204 000 so'm desa, 120 000 so'm/kg baliq uchun
        # chekda "1.7 кг" deb chiqadi — mijoz nechchi kg olganini
        # ko'radi va narx qayerdan kelganini tushunadi.
        unit_price = menu_item.price or 0.0
        qty = max(1, order_item.quantity or 1)
        if unit_price > 0:
            order_item.weight = round(
                float(order_item.manual_price) / (unit_price * qty), 3)
        else:
            order_item.weight = None
    else:
        order_item.weight = None
    order_item.total_price = line_total(
        menu_item, order_item.quantity, order_item.weight, order_item.manual_price
    )

    await recalc_order_totals(db, order)
    await db.flush()
    order = await load_order_full(db, order_id) or order
    return build_order_response(order)


# ─── O'lchanadigan taom hajmini belgilash (1.5 L / 1.4 kg) ─────
@router.patch("/{order_id}/items/{item_id}/size", response_model=OrderResponse,
              summary="Taom hajmini (o'lchamini) belgilash")
async def update_item_size(
    order_id: int,
    item_id: int,
    payload: UpdateItemSizeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("waiter", "admin", "developer", "cashier")),
):
    """Ofitsiant o'lchanadigan taomning hajmini kiritadi: "1.5 L", "1.4 kg".

    Bu oshxona begunogida va mijoz chekida ko'rinadi — shunda oshpaz
    qaysi hajmdagi ichimlik yoki necha kilogramm baliq kerakligini biladi.
    """
    item_res = await db.execute(
        select(OrderItem).where(OrderItem.id == item_id, OrderItem.order_id == order_id)
    )
    order_item = item_res.scalar_one_or_none()
    if not order_item:
        raise HTTPException(status_code=404, detail="Taom topilmadi")

    order = await load_order_full(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Buyurtma topilmadi")
    if order.status in (OrderStatus.PAID, OrderStatus.CANCELLED):
        raise HTTPException(status_code=400, detail="Yopilgan buyurtmani o'zgartirib bo'lmaydi")

    size = (payload.portion_size or "").strip()
    order_item.portion_size = size or None

    await db.flush()
    order = await load_order_full(db, order_id) or order
    return build_order_response(order)


# ─── Taomni buyurtmadan o'chirish ──────────────────────────────
@router.delete("/{order_id}/items/{item_id}", response_model=OrderResponse, summary="Taomni buyurtmadan o'chirish")
async def delete_order_item(
    order_id: int,
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("waiter", "admin", "developer", "cashier")),
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
    fee_pct = order_fee_percent(order)
    order.service_fee_amount = subtotal * (fee_pct / 100.0)
    order.total = subtotal + order.service_fee_amount - (order.discount or 0.0)

    await db.flush()
    order = await load_order_full(db, order_id) or order
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
    reprint: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("waiter", "admin", "developer")),
):
    """
    Ofitsiant 'На кухню' tugmasini bosadi:
    1. FAQAT yangi qo'shilgan taomlarni (quantity - sent_quantity) yuboradi
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

    # Oshxonaga faqat YANGI qo'shilganlar chiqadi.
    #
    # Ofitsiant 1 somsa yuborgandan keyin yana 1 somsa qo'shsa, oshxonada
    # "1 somsa" chiqishi kerak — "2 somsa" emas, aks holda oshpaz ikkita
    # tayyorlaydi. Shuning uchun har qatorda "nechta yuborilgan"
    # (sent_quantity) saqlanadi va begunokka faqat farqi chiqadi.
    #
    # Ilgari bu yerda "yangisi bo'lmasa — hammasini chiqar" degan zahira
    # yo'l bor edi: tugma ikkinchi marta bosilganda butun buyurtma
    # qaytadan chiqib ketardi.
    pending: List[tuple] = []   # (OrderItem, shu begunokda chiqadigan yangi soni)
    for it in order.items:
        qty = it.quantity or 0
        already = it.sent_quantity or 0
        # Ofitsiant yuborgandan keyin sonini kamaytirgan bo'lsa
        # (already > qty) hisobni kamaytirmaymiz: oshxona ko'pini
        # tayyorlayotgan bo'lishi mumkin, keyin qayta qo'shilsa
        # ikkinchi marta chiqib ketmasligi kerak.
        delta = qty - already
        if delta > 0:
            pending.append((it, delta))

    if not pending and not reprint:
        # Yangi taom yo'q. Bu yerda hech narsa chop etilmaydi — ofitsiant
        # xohlasa "qayta chiqarish" bilan butun begunokni takrorlaydi.
        return {
            "success": True,
            "order_id": order.id,
            "items_count": 0,
            "nothing_new": True,
            "message": "Yangi taom yo'q — barchasi oshxonaga allaqachon yuborilgan.",
            "tickets": [],
            "raw_text": "",
        }

    if reprint:
        # Begunok printerdan chiqmagan bo'lsa ofitsiant qaytadan
        # chiqaradi: butun buyurtma chiqadi va begunok tepasida
        # "ТАКРОР" deb yoziladi — oshpaz ikkinchi marta tayyorlamasin.
        target_items = [(it, it.quantity or 0) for it in order.items if (it.quantity or 0) > 0]
    else:
        target_items = pending

    now_utc = datetime.now(timezone.utc)
    for it, _delta in pending:
        it.sent_to_kitchen = True
        it.sent_to_kitchen_at = now_utc
        it.sent_quantity = max(it.sent_quantity or 0, it.quantity or 0)

    if order.status == OrderStatus.PENDING:
        order.status = OrderStatus.PREPARING
        order.preparing_at = now_utc

    table_num = order.table.number if order.table else "—"
    room_name = order.table.room if order.table else ""
    waiter_display = current_user.full_name or current_user.username

    set_res = await db.execute(select(RestaurantSettings).where(RestaurantSettings.restaurant_id == order.restaurant_id))
    settings = set_res.scalar_one_or_none()
    paper_width = settings.printer_paper_width if settings else 80

    # Printer marshruti (stansiya -> printer):
    #   hot_kitchen  -> 1-Oshxona (qozon taomlari)
    #   cold_kitchen -> 2-Oshxona (baliq, somsa, mangal)
    #   bar          -> BAR (choy, suv, ichimliklar)
    # MUHIM: ilgari "bar" stansiyasi hech qayerda tekshirilmasdi va
    # oxirgi `else` orqali 1-OSHXONAGA tushib ketardi — shuning uchun
    # suv va ichimliklar oshxona printeridan chiqardi.
    k1_items = []
    k2_items = []
    bar_items = []
    kassa_items = []

    for it, send_qty in target_items:
        st = getattr(it.menu_item, "kitchen_station", "hot_kitchen") if it.menu_item else "hot_kitchen"
        st = (st or "hot_kitchen").lower().strip()

        dish_name = getattr(it.menu_item, "name_cyrillic", None) or (it.menu_item.name if it.menu_item else "Таом")

        item_dict = {
            "name": dish_name,
            # MUHIM: qatordagi umumiy son emas, shu begunokda oshxonaga
            # chiqayotgan YANGI son.
            "quantity": send_qty,
            "note": it.special_note,
            # O'lchanadigan taomning hajmi — oshxona nechchi litr/kg
            # ekanini begunokdan ko'rishi uchun.
            "size": it.portion_size,
            # Tortiladigan taom: begunokda "1.35 кг" yoki tortilmagan
            # bo'lsa "ТОРТИЛСИН!" deb chiqadi.
            "weight": it.weight,
            "manual_price": it.manual_price,
            "unit": (getattr(it.menu_item, "unit", None) or "kg") if it.menu_item else "kg",
            "is_weighted": bool(getattr(it.menu_item, "is_weighted", False)) if it.menu_item else False,
        }

        # Stansiya bo'yicha saralash
        if st in ["customer_only", "customer", "kassa", "bill_only"]:
            # KASSA: oshxonaga YUBORILMAYDI, lekin kassadagi (USB) printerdan
            # begunok chiqadi — kassir suv/non berib yuborishi uchun.
            # Ilgari bu yerda `continue` turardi: hech qanday chek chiqmasdi.
            kassa_items.append(item_dict)
        elif st in ["bar", "drink", "drinks", "ichimlik", "ichimliklar", "choyxona"]:
            bar_items.append(item_dict)
        elif st in ["all_kitchens", "both", "all"]:
            k1_items.append(item_dict)
            k2_items.append(item_dict)
        elif st in ["cold_kitchen", "kitchen2", "somsa", "baliq"] or any(key in st for key in ["cold", "kitchen2", "2", "baliq", "fish", "somsa", "mangal", "grill"]):
            k2_items.append(item_dict)
        else:
            k1_items.append(item_dict)

    k1_title = getattr(settings, "kitchen1_title", None) or "1-Oshxona (Qozon taomlari)"
    k2_title = getattr(settings, "kitchen2_title", None) or "2-Oshxona (Baliq / Somsa)"
    bar_title = getattr(settings, "bar_title", None) or "BAR (Ichimliklar)"
    k1_printer = getattr(settings, "printer_kitchen1_name", None) or "X-Q80A"
    k2_printer = getattr(settings, "printer_kitchen2_name", None) or "X-Q80A"
    # Bar printeri sozlanmagan bo'lsa — kassa printeriga chiqadi.
    # Oshxonaga esa HECH QACHON yuborilmaydi.
    bar_printer = (getattr(settings, "printer_bar_name", None) or "").strip() \
        or (getattr(settings, "printer_customer_name", None) or "X-Q80A")
    auto_print = getattr(settings, "auto_print_kitchen", True)
    popts = printer_options(settings)
    cp = popts["codepage"]
    fsize = popts["font_size"]

    generated_tickets = []
    combined_texts = []

    # Har bir stansiya uchun bir xil ish: begunok matni -> printer -> arxiv.
    # Ilgari bu blok har stansiya uchun qayta-qayta yozilgan edi.
    kassa_printer = getattr(settings, "printer_customer_name", None) or "X-Q80A"
    stations = [
        ("hot_kitchen", k1_title, k1_printer, k1_items, "KITCHEN1"),
        ("cold_kitchen", k2_title, k2_printer, k2_items, "KITCHEN2"),
        ("bar", bar_title, bar_printer, bar_items, "BAR"),
        ("kassa", "KASSA (Mijozga berish)", kassa_printer, kassa_items, "KASSA"),
    ]

    for station_key, station_title, station_printer, station_items, prefix in stations:
        if not station_items:
            continue

        ticket_text = format_kitchen_ticket(
            hall_name=order.hall_name or room_name,
            room_name=room_name,
            table_number=table_num,
            waiter_name=waiter_display,
            items=station_items,
            kitchen_note=order.kitchen_note,
            order_time=datetime.now(),
            paper_width=paper_width,
            station_title=station_title,
            font_size=fsize,
            char_spacing=popts["char_spacing"],
            is_reprint=bool(reprint),
        )
        combined_texts.append(ticket_text)

        print_status = False
        print_error = None
        if auto_print:
            try:
                p_res = await print_with_retry(
                    ticket_text, printer_name=station_printer, **popts
                )
                print_status = p_res.get("success", False)
                if p_res.get("queued"):
                    print_error = p_res.get("warning", "Printerga ulanib bo'lmadi (navbatga olindi)")
                elif not print_status:
                    print_error = p_res.get("error", "Chop etishda xatolik")
            except Exception as e:
                printer_queue.enqueue(
                    ticket_text, printer_name=station_printer, **popts
                )
                print_error = f"{str(e)} (navbatga qo'yildi)"
        else:
            print_error = "Avtomatik chop etish sozlamalarda o'chirilgan"

        db.add(ReceiptArchive(
            restaurant_id=order.restaurant_id,
            order_id=order.id,
            receipt_number=f"{prefix}-{order.order_number}",
            receipt_type="kitchen",
            hall_name=order.hall_name or room_name,
            table_name=f"N# {table_num} ({station_title})",
            waiter_name=waiter_display,
            subtotal=order.subtotal or 0.0,
            service_fee_percent=0.0,
            service_fee_amount=0.0,
            total_amount=order.subtotal or 0.0,
            payment_method="kitchen",
            items_json=station_items,
            notes=order.kitchen_note,
            raw_text=ticket_text,
        ))

        generated_tickets.append({
            "station": station_key,
            "station_title": station_title,
            "printer_name": station_printer,
            "items": station_items,
            "raw_text": ticket_text,
            "printed": print_status,
            "print_error": print_error,
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
        "items_count": sum(q for _it, q in target_items),
        "nothing_new": False,
        "tickets": generated_tickets,
        "raw_text": main_raw_text,
    }


# ─── To'lov va Stolni yopish (К оплате — Kassa) ───────────────
@router.post("/{order_id}/checkout", summary="To'lovni qabul qilish va hisobni yopish (К оплате)")
async def checkout_order(
    order_id: int,
    payload: OrderCheckoutRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "cashier", "developer")),
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

    # Tortiladigan taomning narxi kiritilmagan bo'lsa chek chiqarib
    # bo'lmaydi: chekda 0 so'm yoziladi va kassa kam pul oladi.
    not_weighed = missing_weight_items(order)
    if not_weighed:
        raise HTTPException(
            status_code=400,
            detail="Chek chiqarib bo'lmaydi: " + ", ".join(not_weighed) +
                   " narxi kiritilmagan. Ofitsiant panelida summasini "
                   "yozing — shundan keyin chek to'g'ri chiqadi.",
        )

    set_res = await db.execute(select(RestaurantSettings).where(RestaurantSettings.restaurant_id == order.restaurant_id))
    settings = set_res.scalar_one_or_none()

    rest_res = await db.execute(select(Restaurant).where(Restaurant.id == order.restaurant_id))
    restaurant = rest_res.scalar_one_or_none()
    rest_name = restaurant.name if restaurant else "Dunyo Choyxonasi"

    # Xizmat haqi foizi tartibi:
    #   1) to'lov oynasida ataylab boshqa foiz yuborilgan bo'lsa — o'sha;
    #   2) aks holda BUYURTMAGA qo'yilgan foiz (kassir shu stol uchun
    #      o'zgartirgan bo'lishi mumkin — masalan VIP xonaga 15%);
    #   3) ikkisi ham yo'q bo'lsa — sozlamadagi umumiy foiz.
    # Ilgari 2-qadam yo'q edi: kassir stol uchun foizni o'zgartirsa ham
    # to'lovda u 12% ga qaytib ketardi va mijozdan boshqa summa olinardi.
    if payload.service_fee_percent is not None:
        fee_pct = float(payload.service_fee_percent)
    else:
        fee_pct = order_fee_percent(
            order,
            fallback=(settings.service_fee_percent if settings else None),
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
    popts = printer_options(settings)
    fsize = popts["font_size"]

    # Delivery / Takeaway uchun stol yo'q: qiymat sifatida mijoz ismi / manzil ko'rsatiladi
    if order.table:
        table_disp = f"{order.hall_name or order.table.room or ''} N#{order.table.number}".strip()
    elif order.order_type == "delivery":
        parts = []
        if order.customer_name:
            parts.append(order.customer_name)
        if getattr(order, "delivery_address", None):
            parts.append(order.delivery_address)
        table_disp = (" — ".join(parts) or "Yetkazib berish") if parts else "Yetkazib berish"
    elif order.order_type == "takeaway":
        table_disp = f"Olib ketish: {order.customer_name or ''}" .strip().rstrip(":")
    else:
        table_disp = f"{order.hall_name or ''} N#{order.table_id or ''}".strip()
    waiter_disp = (order.waiter.full_name or order.waiter.username) if order.waiter else current_user.full_name

    items_for_receipt = [
        {
            "name": it.menu_item.name if it.menu_item else "Taom",
            "quantity": it.quantity,
            "unit_price": it.unit_price,
            "total_price": it.total_price,
            "size": it.portion_size,
            "weight": it.weight,
            "manual_price": it.manual_price,
            "unit": (getattr(it.menu_item, "unit", None) or "kg") if it.menu_item else "kg",
            "is_weighted": bool(getattr(it.menu_item, "is_weighted", False)) if it.menu_item else False,
        }
        for it in order.items
    ]

    bill_text = format_pre_check(
        restaurant_name=receipt_title(settings, restaurant, rest_name),
        # Chek sozlamasida bo'sh bo'lsa — restoran ma'lumotidan olamiz,
        # shunda telefon/manzil chekda ikki joyda sozlanmasdan ham chiqadi.
        address=(getattr(settings, "receipt_address", None) if settings else None)
                or (restaurant.address if restaurant else "Xorazm viloyati, Xiva tumani"),
        phone=(getattr(settings, "receipt_phone", None) if settings else None)
              or (restaurant.phone if restaurant else "+998884593400"),
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
        footer_text=settings.receipt_footer if (settings and settings.receipt_footer) else "Tashrifingiz uchun rahmat! Dunyo Choyxonasi (+998884593400)",
        created_at=order.created_at,
        paper_width=paper_width,
        font_size=fsize,
        char_spacing=popts["char_spacing"],
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

    # Audit log: kassir to'lovni qabul qildi
    from app.core.audit import log_audit_event
    await log_audit_event(
        db=db,
        restaurant_id=order.restaurant_id,
        action="order_checkout",
        user=current_user,
        entity_type="order",
        entity_id=order.id,
        details={
            "order_number": order.order_number,
            "total": total,
            "payment_method": order.payment_method,
            "cash": round(cash_in, 2),
            "table_id": order.table_id,
        },
    )

    # Avtomatik 1-Printer (Mijoz kassa cheki) ga asinxron chop etish (non-blocking)
    if getattr(settings, "auto_print_customer_bill", True):
        cust_printer = getattr(settings, "printer_customer_name", None) or "X-Q80A"
        try:
            await print_with_retry(bill_text, printer_name=cust_printer, **popts)
        except Exception:
            printer_queue.enqueue(bill_text, printer_name=cust_printer, **popts)

    # Faqat kassa cheklari (checkout / final bill) uchun PDF arxiv saqlash (non-blocking)
    try:
        from app.core.pdf_generator import async_save_checkout_receipt_pdf
        pdf_payload = {
            "restaurant_name": receipt_title(settings, restaurant, rest_name),
            "address": (getattr(settings, "receipt_address", None) if settings else None) or (restaurant.address if restaurant else "Xorazm viloyati, Xiva tumani"),
            "phone": (getattr(settings, "receipt_phone", None) if settings else None) or (restaurant.phone if restaurant else "+998884593400"),
            "order_number": order.order_number,
            "order_type": order.order_type or "dine_in",
            "table_name": table_disp,
            "waiter_name": waiter_disp,
            "customer_name": order.customer_name,
            "customer_phone": getattr(order, "customer_phone", None),
            "delivery_address": getattr(order, "delivery_address", None),
            "items": items_for_receipt,
            "subtotal": subtotal,
            "service_fee_percent": fee_pct,
            "service_fee_amount": fee_amount,
            "discount": discount,
            "total": total,
            "payment_method": order.payment_method,
            "cash_amount": order.cash_amount,
            "card_amount": order.card_amount,
            "click_amount": order.click_amount,
            "debt_amount": order.debt_amount,
            "receipt_note": order.receipt_note,
            "footer_text": settings.receipt_footer if (settings and settings.receipt_footer) else "Tashrifingiz uchun rahmat! Dunyo Choyxonasi (+998884593400)",
            "wifi_pass": settings.receipt_wifi_pass if settings else None,
            "created_at": order.created_at,
        }
        await async_save_checkout_receipt_pdf(pdf_payload)
    except Exception as exc:
        import logging
        logging.getLogger("orders").warning(f"Kassa PDF chekini arxivlashda xatolik: {exc}")

    status_lbl = f"Stol #{order.table.number}" if order.table else f"Buyurtma {order.order_number}"
    await manager.broadcast_to_restaurant(order.restaurant_id, {
        "type": "order_paid",
        "order_id": order.id,
        "order_number": order.order_number,
        "table_id": order.table_id,
        "table_number": order.table.number if order.table else None,
        "order_type": order.order_type,
        "total": total,
        "payment_method": order.payment_method,
        "raw_text": bill_text,
        "message": f"{status_lbl} to'landi va yopildi ✅",
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
@router.post(
    "/call-waiter",
    status_code=200,
    summary="Ofitsiant chaqirish",
    dependencies=[
        Depends(
            RateLimiter(
                times=3,
                seconds=60,
                detail="Ofitsiant chaqiruvi yuborilgan. Iltimos, xodim kelishini kuting.",
            )
        )
    ],
)
async def call_waiter(payload: CallWaiterRequest, db: AsyncSession = Depends(get_db)):
    """Mijoz stolidan ofitsiantni chaqiradi (rate-limit va spam himoyasi bilan)"""
    result = await db.execute(select(Table).where(Table.id == payload.table_id))
    table = result.scalar_one_or_none()
    if not table or not table.is_active:
        raise HTTPException(status_code=404, detail="Stol topilmadi yoki faol emas")

    set_res = await db.execute(select(RestaurantSettings).where(RestaurantSettings.restaurant_id == table.restaurant_id))
    settings = set_res.scalar_one_or_none()
    if settings and not settings.allow_call_waiter:
        raise HTTPException(status_code=400, detail="Ushbu restoranda ofitsiant chaqirish xizmati faol emas")

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

    # Agar bu stol uchun chaqiruv allaqachon kutish holatida bo'lsa, spam bildirishnoma yaratmaslik
    if active_order and active_order.call_waiter and active_order.call_status == CallStatus.PENDING:
        return {
            "success": True,
            "message": f"Stol #{table.number} uchun ofitsiant allaqachon chaqirilgan. Xodim tez orada stolingizga keladi.",
            "notification_id": None,
        }

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
    # Bug 5 fix: `or 1` o'chirildi — developer user restaurant_id=None bo'lsa
    # `None or 1` → 1 (noto'g'ri restoran) o'rniga, to'g'ri qiymat keyin aniqlanadi.
    restaurant_id = current_user.restaurant_id  # None bo'lishi mumkin, keyinroq aniqlanadi

    # Bug 6 fix: 100000 magic number o'chirildi.
    # Yangi strategiya: avval Notification jadvalidan qidiramiz (call_id = notif.id),
    # topilmasa Order jadvalidan qidiramiz (call_id = order.id).
    # Bu yondashuv 100,000+ buyurtmada ham to'g'ri ishlaydi.
    notif_res = await db.execute(
        select(Notification).where(Notification.id == call_id)
    )
    notif = notif_res.scalar_one_or_none()

    if notif:
        # Notification orqali topildi
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
        # Notification topilmadi — Order.id sifatida urinib ko'ramiz
        o_res = await db.execute(
            select(Order).options(selectinload(Order.table)).where(Order.id == call_id)
        )
        o = o_res.scalar_one_or_none()
        if o:
            o.call_waiter = False
            o.call_status = CallStatus.COMPLETED
            restaurant_id = o.restaurant_id
            table_id = o.table_id
            table_num = o.table.number if o.table else o.table_id

    # restaurant_id hali ham None bo'lsa (developer user + notif ham topilmasa) — xato
    if restaurant_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Chaqiruv #{call_id} topilmadi yoki restaurant aniqlanmadi",
        )

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

    # Bug 2 fix: flush() va commit() olib tashlandi — get_db dependency
    # har bir request oxirida commit() ni o'zi chaqiradi.
    # Bu yerda commit() chaqirilsa transaction ikki marta yopiladi va SQLAlchemy xatosi chiqadi.

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
@router.get(
    "/table/{table_id}/active",
    response_model=List[OrderResponse],
    summary="Stolning faol buyurtmalari",
    dependencies=[
        Depends(
            RateLimiter(
                times=60,
                seconds=60,
                detail="So'rovlar soni me'yordan oshdi. Iltimos biroz kuting.",
            )
        )
    ],
)
async def get_table_active_orders(
    table_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """Mijoz yoki xodim ushbu stoldagi barcha faol (to'lanmagan) buyurtmalarni ko'radi"""
    tbl_res = await db.execute(select(Table).where(Table.id == table_id))
    tbl = tbl_res.scalar_one_or_none()
    if not tbl or not tbl.is_active:
        raise HTTPException(status_code=404, detail="Stol topilmadi yoki faol emas")

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
    resp_list = []
    for o in orders:
        ord_resp = build_order_response(o)
        if not current_user:
            ord_resp.waiter_share_amount = 0.0
        resp_list.append(ord_resp)
    return resp_list



# ─── Buyurtmalar ro'yxati ─────────────────────────────────
@router.get("/", response_model=List[OrderSummary], summary="Buyurtmalar ro'yxati (pagination bilan)")
async def list_orders(
    restaurant_id: int,
    status: Optional[OrderStatus] = None,
    table_id: Optional[int] = None,
    order_type: Optional[str] = None,
    limit: int = Query(default=100, ge=1, le=500, description="Qaytariladigan buyurtmalar soni"),
    offset: int = Query(default=0, ge=0, description="O'tkazib yuboriladigan buyurtmalar soni"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "waiter", "chef", "developer")),
):
    query = (
        select(Order)
        .options(
            selectinload(Order.table),
            selectinload(Order.waiter),
            selectinload(Order.items).selectinload(OrderItem.menu_item),
        )
        .where(Order.restaurant_id == restaurant_id)
    )

    if status:
        query = query.where(Order.status == status)
    if table_id:
        query = query.where(Order.table_id == table_id)
    if order_type:
        query = query.where(Order.order_type == order_type)

    # Ofitsiant faqat o'ziga tayinlangan yoki tayinlanmagan buyurtmalarni ko'rishi mumkin
    if current_user.role == UserRole.WAITER:
        query = query.where(
            (Order.waiter_id == current_user.id) | (Order.waiter_id == None)
        )

    query = query.order_by(Order.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    orders = result.scalars().all()

    summaries = []
    for order in orders:
        items_count = len(order.items) if order.items else 0
        table_num = order.table.number if order.table else None
        waiter_name = None
        if order.waiter:
            waiter_name = order.waiter.full_name or order.waiter.username

        items_resp = []
        for it in (order.items or []):
            m_item = getattr(it, "menu_item", None)
            items_resp.append(
                OrderItemResponse(
                    id=it.id,
                    menu_item_id=it.menu_item_id,
                    quantity=it.quantity,
                    unit_price=it.unit_price,
                    total_price=it.total_price,
                    special_note=it.special_note,
                    portion_size=it.portion_size,
                    item_time=it.item_time,
                    weight=it.weight,
                    manual_price=it.manual_price,
                    is_weighted=bool(getattr(m_item, "is_weighted", False)) if m_item else False,
                    unit=(getattr(m_item, "unit", "dona") or "dona") if m_item else "dona",
                    sent_to_kitchen=bool(it.sent_to_kitchen),
                    sent_to_kitchen_at=it.sent_to_kitchen_at,
                    sent_quantity=int(it.sent_quantity or 0),
                    is_prepared=bool(it.is_prepared),
                    prepared_at=it.prepared_at,
                    menu_item_name=m_item.name if m_item else None,
                    menu_item_image=m_item.image_url if m_item else None,
                )
            )

        summaries.append(
            OrderSummary(
                id=order.id,
                order_number=order.order_number,
                order_type=order.order_type or "dine_in",
                customer_name=order.customer_name,
                customer_phone=getattr(order, "customer_phone", None),
                delivery_address=getattr(order, "delivery_address", None),
                kitchen_note=getattr(order, "kitchen_note", None),
                table_id=order.table_id,
                table_number=table_num,
                waiter_id=order.waiter_id,
                waiter_name=waiter_name,
                status=order.status,
                total=order.total,
                items_count=items_count,
                items=items_resp,
                is_paid=bool(order.is_paid),
                payment_method=order.payment_method or "cash",
                call_waiter=bool(order.call_waiter),
                call_status=order.call_status,
                call_note=order.call_note,
                created_at=order.created_at,
                ready_at=order.ready_at,
                served_at=order.served_at,
            )
        )
    return summaries


@router.get(
    "/{order_id}",
    response_model=OrderResponse,
    summary="Buyurtma tafsiloti",
    dependencies=[
        Depends(
            RateLimiter(
                times=60,
                seconds=60,
                detail="So'rovlar soni me'yordan oshdi. Iltimos biroz kuting.",
            )
        )
    ],
)
async def get_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
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

    # Autentifikatsiyasiz mijoz faqat o'zining so'nggi 24 soat ichidagi yoki faol buyurtmasini ko'ra oladi
    if not current_user:
        now = datetime.now(timezone.utc)
        order_time = order.created_at if (order.created_at and order.created_at.tzinfo) else (
            order.created_at.replace(tzinfo=timezone.utc) if order.created_at else now
        )
        age_seconds = (now - order_time).total_seconds()
        if order.is_paid and age_seconds > 86400:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tarixiy yopilgan buyurtmalarni faqat xodimlar ko'rishi mumkin",
            )

    resp = build_order_response(order)
    if not current_user:
        resp.waiter_share_amount = 0.0
    return resp


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
    elif payload.status == OrderStatus.CANCELLED:
        from app.core.audit import log_audit_event
        await log_audit_event(
            db=db,
            restaurant_id=order.restaurant_id,
            action="order_cancelled",
            user=current_user,
            entity_type="order",
            entity_id=order.id,
            details={"order_number": order.order_number, "note": payload.note},
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
