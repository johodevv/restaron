"""
Buyurtmalar API — Mijoz, Ofitsiant, Oshpaz, Admin
To'liq WebSocket integratsiyasi va 'Yetkazib berdim' funksiyasi bilan
"""
import asyncio
import uuid
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, update, text
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.exc import IntegrityError
from typing import List, Optional, Any, Set
from app.core.money import money, money_sum, percent, decimal

from app.core.database import get_db
from app.core.transactions import lock_rows
from app.core.rate_limit import RateLimiter, get_client_ip
from app.core.security import get_current_user, get_optional_current_user, require_role
from app.core.kitchen_permissions import kitchen_sent_quantity, require_kitchen_admin
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
    UpdateItemDeltaRequest,
    PrepareItemRequest,
    UpdateItemSizeRequest,
    UpdateItemWeightRequest,
    OrderNoteUpdate, OrderCheckoutRequest,
    StaleOrderResponse
)
from app.core.printer_service import (
    format_kitchen_ticket, format_pre_check,
    DEFAULT_FONT_SIZE, printer_options, receipt_title,
)
import logging
from app.core.printer_queue import (
    enqueue_print_job,
    wake_printer_worker,
)

from app.core.sms_telegram import send_telegram_alert
from app.websockets.manager import manager
from app.core.idempotency import IdempotencyHandler, get_idempotency_handler

router = APIRouter(prefix="/orders", tags=["📋 Buyurtmalar"])

UZ_TZ = timezone(timedelta(hours=5))
logger = logging.getLogger("orders")

# ─── Fon vazifalarini kuzatish (Garbage collection'dan himoya) ───────
_bg_tasks: Set[asyncio.Task] = set()

def create_bg_task(coro) -> asyncio.Task:
    task = asyncio.create_task(coro)
    _bg_tasks.add(task)
    def _done_callback(t: asyncio.Task):
        _bg_tasks.discard(t)
        try:
            if not t.cancelled() and t.exception():
                logger.error(f"Fon vazifasida xatolik: {t.exception()}", exc_info=t.exception())
        except Exception as e:
            logger.error(f"Fon vazifasi istisnosini tekshirishda xatolik: {e}")
    task.add_done_callback(_done_callback)
    return task


KITCHEN_STATION_MAP = {
    # Hot kitchen (1-oshxona: qozon taomlari)
    "hot_kitchen": "hot_kitchen",
    "hot": "hot_kitchen",
    "kitchen1": "hot_kitchen",
    "qozon": "hot_kitchen",
    # Cold kitchen (2-oshxona: baliq, somsa, shashlik/mangal)
    "cold_kitchen": "cold_kitchen",
    "cold": "cold_kitchen",
    "kitchen2": "cold_kitchen",
    "somsa": "cold_kitchen",
    "baliq": "cold_kitchen",
    "mangal": "cold_kitchen",
    "grill": "cold_kitchen",
    "fish": "cold_kitchen",
    # Bar (ichimliklar, choy, suv)
    "bar": "bar",
    "drink": "bar",
    "drinks": "bar",
    "ichimlik": "bar",
    "ichimliklar": "bar",
    "choyxona": "bar",
    # Kassa (mijozga berish, USB printer)
    "customer_only": "kassa",
    "customer": "kassa",
    "kassa": "kassa",
    "bill_only": "kassa",
    # Ikkala oshxona
    "all_kitchens": "all",
    "both": "all",
    "all": "all",
}


def resolve_kitchen_station(st_raw: Optional[str]) -> str:
    if not st_raw:
        return "hot_kitchen"
    st = str(st_raw).lower().strip()
    station = KITCHEN_STATION_MAP.get(st)
    if not station:
        logger.warning(f"Noma'lum kitchen_station: '{st_raw}', hot_kitchen ga yo'naltirilmoqda")
        return "hot_kitchen"
    return station


async def _send_cancellation_receipt(
    db: AsyncSession,
    order: Order,
    menu_item: Optional[MenuItem],
    cancelled_qty: int,
    waiter_name: str,
    settings: Optional[RestaurantSettings],
):
    if not getattr(settings, 'auto_print_kitchen', True) and getattr(settings, 'enable_chef_kds', False):
        return
    station = resolve_kitchen_station(getattr(menu_item, 'kitchen_station', 'hot_kitchen'))
    customer = (getattr(settings, 'printer_customer_name', '') or '').strip()
    printers = {
        'hot_kitchen': (getattr(settings, 'printer_kitchen1_name', '') or '').strip(),
        'cold_kitchen': (getattr(settings, 'printer_kitchen2_name', '') or '').strip(),
        'bar': customer, 'kassa': customer,
    }
    targets = ['hot_kitchen', 'cold_kitchen'] if station == 'all' else [station]
    if any(not printers.get(target) for target in targets):
        raise HTTPException(400, "Bekor qilish chekini yuborish uchun oshxona printerini sozlang")
    dish_name = getattr(menu_item, 'name_cyrillic', None) or getattr(menu_item, 'name', 'Taom')
    text = ("*** BEKOR QILINDI (OTMENA) ***\n"
            f"Stol: #{order.table.number if order.table else order.order_number}\n"
            f"Ofitsiant: {waiter_name}\nTaom: {dish_name} (-{cancelled_qty} ta)\n"
            f"Vaqt: {datetime.now(UZ_TZ).strftime('%d.%m.%Y %H:%M')}\n\n\n")
    for target in targets:
        await enqueue_print_job(db, restaurant_id=order.restaurant_id, order_id=order.id,
            ticket_type='cancel', printer_name=printers[target], raw_text=text, options=printer_options(settings))



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
    500 qaytaradi. Shuning uchun refresh o'rniga bog'lanishlarni joinedload bilan
    qaytadan yuklaymiz.
    """
    res = await db.execute(
        select(Order)
        .options(
            joinedload(Order.items).joinedload(OrderItem.menu_item),
            joinedload(Order.table),
            joinedload(Order.waiter),
        )
        .where(Order.id == order_id)
    )
    return res.unique().scalar_one_or_none()


DEFAULT_SERVICE_FEE = 12.0


def _safe_get_attr(instance: Any, attr_name: str, default: Any = None) -> Any:
    """SQLAlchemy async da MissingGreenlet xatosini 100% oldini olish:
    Lazy-load yoki expired attribute loaderni chaqirmasdan xotiradan oladi."""
    if instance is None:
        return default
    try:
        from sqlalchemy import inspect as sa_inspect
        insp = sa_inspect(instance)
        if hasattr(insp, "dict") and attr_name in insp.dict:
            val = insp.dict[attr_name]
            return val if val is not None else default
    except Exception:
        pass
    d = getattr(instance, "__dict__", {})
    if attr_name in d:
        val = d[attr_name]
        return val if val is not None else default
    return default


def order_fee_percent(order: Order, fallback: Optional[float] = None) -> float:
    """Buyurtmaning xizmat haqi foizi.

    MUHIM: 0% ham HAQIQIY qiymat. Ilgari `order.service_fee_percent or 12`
    deb yozilgandi va kassir "xizmat haqi olinmasin" deb 0% qo'yganda
    u jimgina 12% ga aylanib ketardi — mijozdan ortiqcha pul olinardi.
    """
    v = _safe_get_attr(order, "service_fee_percent")
    if v is None:
        v = fallback if fallback is not None else DEFAULT_SERVICE_FEE
    return float(v)


def line_total(menu_item: MenuItem, quantity: int, weight: Optional[float],
               manual_price: Optional[float] = None, unit_price: Optional[float] = None) -> float:
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
        return money(manual_price)

    price = menu_item.price if unit_price is None else unit_price
    price = price or 0.0
    if getattr(menu_item, "is_weighted", False):
        if not weight or weight <= 0:
            return 0.0
        return money(decimal(price) * decimal(weight) * max(1, quantity))
    return money(decimal(price) * quantity)


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
    order.subtotal = money(subtotal)
    order.service_fee_amount = percent(order.subtotal, fee_pct)
    order.total = money_sum([order.subtotal, order.service_fee_amount, -(order.discount or 0)])
    if order.waiter_share_percent and order.waiter_share_percent > 0:
        order.waiter_share_amount = round(order.subtotal * (order.waiter_share_percent / 100.0), 2)


def _safe_get_rel(instance: Any, rel_name: str) -> Any:
    """SQLAlchemy async da MissingGreenlet xatosini oldini olish:
    Lazy-load ni chaqirmasdan faqat xotiradagi yuklangan atribut/munosabatni oladi."""
    if instance is None:
        return None
    try:
        from sqlalchemy import inspect as sa_inspect
        insp = sa_inspect(instance)
        if hasattr(insp, "dict") and rel_name in insp.dict:
            return insp.dict[rel_name]
    except Exception:
        pass
    return getattr(instance, "__dict__", {}).get(rel_name, None)


def build_order_response(order: Order, table_number: Optional[int] = None, waiter_name: Optional[str] = None) -> OrderResponse:
    """OrderResponse obyektini xavfsiz va to'liq yaratish (MissingGreenlet dan 100% himoyalangan)"""
    items_response = []
    order_items = _safe_get_rel(order, "items")
    if order_items is None:
        order_items = getattr(order, "__dict__", {}).get("items", None)
    if order_items is None:
        try:
            order_items = order.items
        except Exception:
            order_items = []

    for item in (order_items or []):
        menu_item = _safe_get_rel(item, "menu_item")
        m_name = _safe_get_attr(item, 'name_snapshot') or (_safe_get_rel(menu_item, "name") if menu_item else None)
        m_img = _safe_get_rel(menu_item, "image_url") if menu_item else None
        m_weighted = bool(_safe_get_rel(menu_item, "is_weighted") or False) if menu_item else False
        m_unit = str(_safe_get_rel(menu_item, "unit") or "dona") if menu_item else "dona"

        items_response.append(
            OrderItemResponse(
                id=_safe_get_attr(item, "id"),
                menu_item_id=_safe_get_attr(item, "menu_item_id"),
                quantity=_safe_get_attr(item, "quantity", 1),
                unit_price=_safe_get_attr(item, "unit_price", 0.0),
                total_price=_safe_get_attr(item, "total_price", 0.0),
                special_note=_safe_get_attr(item, "special_note"),
                portion_size=_safe_get_attr(item, "portion_size"),
                item_time=_safe_get_attr(item, "item_time"),
                weight=_safe_get_attr(item, "weight"),
                manual_price=_safe_get_attr(item, "manual_price"),
                is_weighted=m_weighted,
                unit=m_unit,
                sent_to_kitchen=bool(_safe_get_attr(item, "sent_to_kitchen", False)),
                sent_to_kitchen_at=_safe_get_attr(item, "sent_to_kitchen_at"),
                sent_quantity=int(_safe_get_attr(item, "sent_quantity", 0) or 0),
                is_prepared=bool(_safe_get_attr(item, "is_prepared", False)),
                prepared_quantity=min(int(_safe_get_attr(item, 'prepared_quantity', 0) or 0), int(_safe_get_attr(item, 'sent_quantity', 0) or 0)),
                kitchen_pending_quantity=max(0, int(_safe_get_attr(item, 'sent_quantity', 0) or 0) - int(_safe_get_attr(item, 'prepared_quantity', 0) or 0)),
                prepared_at=_safe_get_attr(item, "prepared_at"),
                menu_item_name=m_name,
                menu_item_image=m_img,
                kitchen_station=getattr(menu_item, 'kitchen_station', None) or 'hot_kitchen',
            )
        )

    tbl = _safe_get_rel(order, "table")
    t_num = table_number if table_number is not None else (_safe_get_rel(tbl, "number") if tbl else None)
    t_room = _safe_get_rel(tbl, "room") if tbl else None
    wtr = _safe_get_rel(order, "waiter")
    w_name = waiter_name if waiter_name is not None else (
        ((_safe_get_rel(wtr, "full_name") or _safe_get_rel(wtr, "username"))) if wtr else None
    )

    return OrderResponse(
        integrity_warning=("Eski hisob summasi taomlar yig‘indisiga mos emas. Admin tekshiruvi kerak."
                           if order_items is not None and abs(sum(item.total_price or 0 for item in items_response) - (_safe_get_attr(order, 'subtotal', 0) or 0)) > .01 else None),
        id=_safe_get_attr(order, "id"),
        version=_safe_get_attr(order, 'version', 1),
        order_number=_safe_get_attr(order, "order_number"),
        restaurant_id=_safe_get_attr(order, "restaurant_id", 1),
        table_id=_safe_get_attr(order, "table_id"),
        table_number=t_num,
        room=t_room,
        waiter_id=_safe_get_attr(order, "waiter_id"),
        waiter_name=w_name,
        customer_name=_safe_get_attr(order, "customer_name"),
        customer_phone=_safe_get_attr(order, "customer_phone"),
        customer_note=_safe_get_attr(order, "customer_note"),
        delivery_address=_safe_get_attr(order, "delivery_address"),
        order_type=_safe_get_attr(order, "order_type", "table"),
        hall_name=_safe_get_attr(order, "hall_name") or t_room,
        kitchen_note=_safe_get_attr(order, "kitchen_note"),
        receipt_note=_safe_get_attr(order, "receipt_note"),
        status=_safe_get_attr(order, "status", OrderStatus.PENDING),
        subtotal=_safe_get_attr(order, "subtotal", 0.0),
        service_fee_percent=order_fee_percent(order),
        service_fee_amount=_safe_get_attr(order, "service_fee_amount", 0.0),
        discount=_safe_get_attr(order, "discount", 0.0),
        total=_safe_get_attr(order, "total", 0.0),
        is_paid=bool(_safe_get_attr(order, "is_paid", False)),
        payment_method=_safe_get_attr(order, "payment_method", "cash"),
        cash_amount=_safe_get_attr(order, "cash_amount", 0.0),
        card_amount=_safe_get_attr(order, "card_amount", 0.0),
        click_amount=_safe_get_attr(order, "click_amount", 0.0),
        debt_amount=_safe_get_attr(order, "debt_amount", 0.0),
        advance_amount=(_safe_get_attr(order, 'advance_amount', 0.0) or 0.0)
                       if _safe_get_attr(order, 'is_paid', False) else (getattr(tbl, 'deposit_amount', 0.0) or 0.0),
        amount_due=max(0.0, (_safe_get_attr(order, 'total', 0.0) or 0.0) -
                       ((_safe_get_attr(order, 'advance_amount', 0.0) or 0.0)
                        if _safe_get_attr(order, 'is_paid', False) else (getattr(tbl, 'deposit_amount', 0.0) or 0.0))),
        waiter_share_amount=_safe_get_attr(order, "waiter_share_amount", 0.0),
        call_waiter=bool(_safe_get_attr(order, "call_waiter", False)),
        call_status=_safe_get_attr(order, "call_status"),
        call_note=_safe_get_attr(order, "call_note"),
        items=items_response,
        created_at=_safe_get_attr(order, "created_at"),
        preparing_at=_safe_get_attr(order, "preparing_at"),
        ready_at=_safe_get_attr(order, "ready_at"),
        served_at=_safe_get_attr(order, "served_at"),
        closed_at=_safe_get_attr(order, "closed_at"),
        updated_at=_safe_get_attr(order, "updated_at"),
    )


def sanitize_order_response_for_guest(resp: OrderResponse) -> OrderResponse:
    """Mehmon ko'rinishi uchun mijoz shaxsiy va ichki xodim ma'lumotlarini tozalash"""
    resp.customer_phone = None
    resp.delivery_address = None
    resp.waiter_share_amount = 0.0
    resp.waiter_id = None
    return resp



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
async def create_order(payload: OrderCreate, db: AsyncSession = Depends(get_db),
                       idempotency: IdempotencyHandler = Depends(get_idempotency_handler)):
    """QR orqali yoki onlayn kirgan mijoz buyurtma beradi (auth talab qilinmaydi, rate-limit va validatsiya bilan)"""
    cached = await idempotency.get_cached_response(None)
    if cached is not None:
        return cached
    table = None
    table_id = payload.table_id
    norm_order_type = payload.order_type or ("dine_in" if table_id else "takeaway")
    if norm_order_type == "table":
        norm_order_type = "dine_in"

    if table_id:
        await lock_rows(db, Table, [table_id])
        result = await db.execute(select(Table).where(Table.id == table_id))
        table = result.scalar_one_or_none()
        if not table or not table.is_active:
            raise HTTPException(status_code=404, detail="Stol topilmadi yoki faol emas")
        if not payload.qr_token or payload.qr_token != table.qr_token:
            raise HTTPException(403, 'Stol QR kodi yaroqsiz')
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
            if not qr_allowed:
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

        # Stolda allaqachon to'lanmagan faol buyurtma mavjud bo'lsa,
        # yangi dublikat hisob ochmasdan mavjud buyurtmaga qo'shamiz (1.5.3)
        existing_order_res = await db.execute(
            select(Order)
            .options(selectinload(Order.items).selectinload(OrderItem.menu_item), selectinload(Order.waiter))
            .where(
                Order.table_id == table.id,
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
        existing_orders = existing_order_res.scalars().all()
        if len(existing_orders) > 1:
            raise HTTPException(409, "Stolda bir nechta eski hisob bor. Ofitsiantni chaqiring")
        existing_order = existing_orders[0] if existing_orders else None
        if existing_order:
            item_ids = [item_data.menu_item_id for item_data in payload.items]
            items_result = await db.execute(
                select(MenuItem)
                .join(Category, Category.id == MenuItem.category_id)
                .where(
                    MenuItem.id.in_(item_ids),
                    Category.restaurant_id == restaurant_id,
                )
            )
            menu_items_map = {mi.id: mi for mi in items_result.scalars().all()}
            now_time_str = datetime.now().strftime("%H:%M")
            new_subtotal = existing_order.subtotal or 0.0
            added_details = []

            for item_data in payload.items:
                menu_item = menu_items_map.get(item_data.menu_item_id)
                if not menu_item:
                    raise HTTPException(status_code=404, detail=f"Taom #{item_data.menu_item_id} topilmadi")
                if menu_item.is_deleted or not menu_item.is_available or menu_item.is_stop_list:
                    raise HTTPException(status_code=400, detail=f"'{menu_item.name}' hozirda stop-listda (tugagan)")

                existing_line = next(
                    (it for it in existing_order.items if it.menu_item_id == item_data.menu_item_id
                     and (it.special_note or None) == (item_data.special_note or None)
                     and (it.portion_size or None) == (item_data.portion_size or None)
                     and not menu_item.is_weighted
                     and it.unit_price == menu_item.price
                     and (it.name_snapshot or menu_item.name) == menu_item.name),
                    None
                )

                if existing_line:
                    existing_line.quantity += item_data.quantity
                    existing_line.total_price = line_total(
                        menu_item, existing_line.quantity, existing_line.weight, existing_line.manual_price, existing_line.unit_price
                    )
                    order_item = existing_line
                else:
                    tot_price = line_total(menu_item, item_data.quantity, item_data.weight)
                    order_item = OrderItem(
                        order_id=existing_order.id,
                        menu_item_id=item_data.menu_item_id,
                name_snapshot=menu_item.name,
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
                    order_item.menu_item = menu_item
                    db.add(order_item)
                    existing_order.items.append(order_item)

                menu_item.total_ordered = (menu_item.total_ordered or 0) + item_data.quantity
                added_details.append({
                    "name": menu_item.name,
                    "quantity": item_data.quantity,
                    "price": menu_item.price,
                    "note": item_data.special_note,
                    "size": item_data.portion_size,
                    "item_time": now_time_str,
                })

            await recalc_order_totals(db, existing_order)
            await db.flush()

            full_existing = await load_order_full(db, existing_order.id)
            if not full_existing:
                full_existing = existing_order
            resp = build_order_response(full_existing, table.number if table else None)
            resp_dict = resp.model_dump() if hasattr(resp, "model_dump") else resp.dict()
            await idempotency.save_response(None, resp_dict, 201)
            await db.commit()
            rest_id = resp_dict.get("restaurant_id", 1)

            await manager.broadcast_to_restaurant(rest_id, {
                "type": "order_updated",
                "order": resp_dict,
                "order_id": resp_dict.get("id", existing_order.id),
                "order_number": resp_dict.get("order_number", ""),
                "table_id": resp_dict.get("table_id"),
                "table_number": table.number if table else None,
                "items": added_details,
                "total": resp_dict.get("total", 0.0),
            })
            return resp

    # Avtomatik ofitsiant tayinlash
    assigned_waiter = await auto_assign_waiter(db, restaurant_id)

    # Buyurtma raqami: avval TMP berib flush qilamiz, so'ng DB ID orqali noyob raqam (1.5.4)
    tmp_order_number = f"#TMP-{uuid.uuid4().hex[:6]}"

    order = Order(
        order_number=tmp_order_number,
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

    order_number = f"#R{restaurant_id}-{order.id:04d}"
    order.order_number = order_number

    # Barcha taomlarni bitta SQL so'rovda olish (N+1 Query optimizatsiyasi 1.5.1)
    item_ids = [item_data.menu_item_id for item_data in payload.items]
    items_result = await db.execute(
        select(MenuItem)
        .join(Category, Category.id == MenuItem.category_id)
        .where(
            MenuItem.id.in_(item_ids),
            Category.restaurant_id == restaurant_id,
        )
    )
    menu_items_map = {mi.id: mi for mi in items_result.scalars().all()}

    subtotal = 0.0
    items_details = []
    now_time_str = datetime.now().strftime("%H:%M")
    for item_data in payload.items:
        menu_item = menu_items_map.get(item_data.menu_item_id)
        if not menu_item:
            raise HTTPException(
                status_code=404,
                detail=f"Taom #{item_data.menu_item_id} topilmadi",
            )
        # Stop-list tekshiruvi (1.5.2)
        if menu_item.is_deleted or not menu_item.is_available or menu_item.is_stop_list:
            raise HTTPException(
                status_code=400,
                detail=f"'{menu_item.name}' hozirda stop-listda (tugagan)",
            )

        total_price = line_total(menu_item, item_data.quantity, item_data.weight)
        subtotal += total_price

        order_item = OrderItem(
            order_id=order.id,
            menu_item_id=item_data.menu_item_id,
                name_snapshot=menu_item.name,
            quantity=item_data.quantity,
            unit_price=menu_item.price,
            total_price=total_price,
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
    response = build_order_response(await load_order_full(db, order.id), table.number if table else None, waiter_name)
    await idempotency.save_response(None, response.model_dump(), 201)
    await db.commit()

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

    return response


@router.post("/waiter-create", response_model=OrderResponse, status_code=201, summary="Buyurtma yaratish (Ofitsiant / Kassa POS)")
async def waiter_create_order(
    payload: WaiterOrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("waiter", "admin", "developer", "cashier")),
    idempotency: IdempotencyHandler = Depends(get_idempotency_handler),
):
    """Ofitsiant yoki kassir stol, olib ketish (s soboy) yoki yetkazish uchun buyurtma yaratadi"""
    cached = await idempotency.get_cached_response(current_user.id)
    if cached is not None:
        return cached

    if not payload.items and not payload.draft:
        raise HTTPException(422, "Bo'sh buyurtma uchun draft=true aniq ko'rsatilishi kerak")

    table = None
    table_id = payload.table_id
    hall_name = payload.hall_name
    norm_order_type = payload.order_type or "dine_in"
    if norm_order_type == "table":
        norm_order_type = "dine_in"

    if table_id:
        # 1. table_id bor bo'lsa, funksiya boshida stol qatorini qulflash (race condition oldini olish)
        await db.execute(update(Table).where(Table.id == table_id).values(status=Table.status))

        result = await db.execute(select(Table).where(Table.id == table_id))
        table = result.scalar_one_or_none()
        if not table:
            raise HTTPException(status_code=404, detail="Stol topilmadi")

        # 4. Stol va foydalanuvchi restorani mosligini tekshirish (developer istisno)
        user_role = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)
        if user_role != "developer" and table.restaurant_id != current_user.restaurant_id:
            raise HTTPException(status_code=403, detail="Ushbu stol boshqa restoranga tegishli")

        table.status = TableStatus.OCCUPIED
        if not hall_name:
            hall_name = table.room or f"Zal"

        # Stolda allaqachon to'lanmagan faol buyurtma mavjud bo'lsa,
        # yangi dublikat hisob ochmasdan mavjud buyurtmaga biriktiramiz:
        # 2. .scalars().first() ishlatamiz (bir nechta bo'lsa ham 500 bermaslik uchun)
        existing_order_id_res = await db.execute(
            select(Order.id)
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
        existing_ids = existing_order_id_res.scalars().all()
        if len(existing_ids) > 1:
            raise HTTPException(409, "Stolda bir nechta eski hisob bor. Kassir hisoblarni alohida tekshirsin")
        existing_order_id = existing_ids[0] if existing_ids else None
        if existing_order_id:
            if payload.items:
                delegated = await waiter_add_items(
                    order_id=existing_order_id,
                    payload=WaiterAddItemsRequest(items=payload.items, send_to_kitchen_immediately=False),
                    db=db,
                    current_user=current_user,
                    idempotency=idempotency,
                )
                await idempotency.save_response(current_user.id, delegated, status_code=201)
                return delegated
            else:
                loaded = await load_order_full(db, existing_order_id)
                if not loaded:
                    raise HTTPException(status_code=404, detail="Buyurtma topilmadi")
                existing_resp = build_order_response(loaded)
                await idempotency.save_response(current_user.id, existing_resp, status_code=201)
                return existing_resp
    else:
        # Takeaway va Delivery uchun avtomatik zal/manzil nomi
        if not hall_name:
            if norm_order_type == "delivery":
                hall_name = "Yetkazib berish"
            elif norm_order_type == "takeaway":
                hall_name = "Olib ketish"
            else:
                hall_name = "Kassa"

    # 4. Buyurtma restaurant_id sini payload'dan emas, stoldan (yoki current_user dan) olish
    restaurant_id = table.restaurant_id if table else (current_user.restaurant_id or payload.restaurant_id or 1)

    # Restoran sozlamalarini olish (xizmat foizi)
    set_res = await db.execute(select(RestaurantSettings).where(RestaurantSettings.restaurant_id == restaurant_id))
    settings = set_res.scalar_one_or_none()
    service_fee_pct = settings.service_fee_percent if settings else 12.0

    # Buyurtma raqami: avval TMP berib flush qilamiz, so'ng DB ID orqali noyob raqam (1.5.4)
    tmp_order_number = f"#TMP-{uuid.uuid4().hex[:6]}"

    # Delivery/takeaway da table_id=None
    resolved_table_id = table_id if table else None

    order = Order(
        order_number=tmp_order_number,
        restaurant_id=restaurant_id,
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
    # 3. Order qo'shilgandagi flush IntegrityError bersa (unikal indeks poygasi):
    # rollback, mavjud ochiq buyurtmani qayta top va taomlarni unga waiter_add_items orqali qo'sh
    try:
        async with db.begin_nested():
            db.add(order)
            await db.flush()
    except IntegrityError:
        if resolved_table_id:
            existing_order_id_res = await db.execute(
                select(Order.id)
                .where(
                    Order.table_id == resolved_table_id,
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
            existing_order_id = existing_order_id_res.scalars().first()
            if existing_order_id:
                if payload.items:
                    delegated = await waiter_add_items(
                        order_id=existing_order_id,
                        payload=WaiterAddItemsRequest(items=payload.items, send_to_kitchen_immediately=False),
                        db=db,
                        current_user=current_user,
                        idempotency=idempotency,
                    )
                    await idempotency.save_response(current_user.id, delegated, status_code=201)
                    return delegated
                else:
                    loaded = await load_order_full(db, existing_order_id)
                    if not loaded:
                        raise HTTPException(status_code=404, detail="Buyurtma topilmadi")
                    existing_resp = build_order_response(loaded)
                    await idempotency.save_response(current_user.id, existing_resp, status_code=201)
                    return existing_resp
        raise

    order_number = f"#R{restaurant_id}-{order.id:04d}"
    order.order_number = order_number

    # Barcha taomlarni bitta SQL so'rovda olish (N+1 Query optimizatsiyasi 1.5.1)
    item_ids = [item_data.menu_item_id for item_data in payload.items]
    items_res = await db.execute(select(MenuItem).where(MenuItem.id.in_(item_ids)))
    menu_items_map = {mi.id: mi for mi in items_res.scalars().all()}

    subtotal = 0.0
    now_time_str = datetime.now().strftime("%H:%M")
    items_details = []

    for item_data in payload.items:
        menu_item = menu_items_map.get(item_data.menu_item_id)
        if not menu_item:
            raise HTTPException(
                status_code=404,
                detail=f"Taom #{item_data.menu_item_id} menuda topilmadi yoki mavjud emas",
            )
        # Stop-list tekshiruvi (1.5.2)
        if menu_item.is_deleted or not menu_item.is_available or menu_item.is_stop_list:
            raise HTTPException(
                status_code=400,
                detail=f"'{menu_item.name}' hozirda stop-listda (tugagan)",
            )

        tot_price = line_total(menu_item, item_data.quantity, item_data.weight)
        subtotal += tot_price

        order_item = OrderItem(
            order_id=order.id,
            menu_item_id=item_data.menu_item_id,
                name_snapshot=menu_item.name,
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

    subtotal = money(subtotal)
    fee_amount = percent(subtotal, service_fee_pct)
    order.subtotal = subtotal
    order.service_fee_amount = fee_amount
    order.total = money_sum([subtotal, fee_amount])

    if current_user.commission_percent and current_user.commission_percent > 0:
        order.waiter_share_percent = current_user.commission_percent
        order.waiter_share_amount = subtotal * (current_user.commission_percent / 100.0)

    await db.flush()
    full_order = await load_order_full(db, order.id)
    if not full_order:
        full_order = order

    waiter_name = current_user.full_name or current_user.username
    order_resp = build_order_response(full_order, table.number if table else None, waiter_name)
    await idempotency.save_response(current_user.id, order_resp, status_code=201)
    await db.commit()
    order_dict = order_resp.model_dump() if hasattr(order_resp, "model_dump") else order_resp.dict()

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
        "order": order_dict,
    }
    await manager.broadcast_to_roles(restaurant_id, ["waiter", "admin", "chef"], ws_payload)

    return order_resp


# ─── Ochiq stolga taom qo'shish (Dozakaz) ───────────────────────
@router.post("/{order_id}/add-items", response_model=OrderResponse, summary="Stolga taom qo'shish (Dozakaz)")
async def waiter_add_items(
    order_id: int,
    payload: WaiterAddItemsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("waiter", "admin", "developer", "cashier")),
    idempotency: IdempotencyHandler = Depends(get_idempotency_handler),
):
    """Ofitsiant faol buyurtmaga qo'shimcha taomlar qo'shadi"""
    cached = await idempotency.get_cached_response(current_user.id)
    if cached is not None:
        return cached

    # 1. Buyurtma qatorini qulflash (race condition oldini olish)
    await lock_rows(db, Order, [order_id])

    order = await load_order_full(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Buyurtma topilmadi")

    if order.is_paid or order.status in [OrderStatus.PAID, OrderStatus.CANCELLED]:
        raise HTTPException(status_code=400, detail="Ushbu buyurtma yopilgan yoki bekor qilingan")

    # Barcha taomlarni bitta SQL so'rovda olish (1.5.1)
    item_ids = [item_data.menu_item_id for item_data in payload.items]
    items_res = await db.execute(select(MenuItem).where(MenuItem.id.in_(item_ids)))
    menu_items_map = {mi.id: mi for mi in items_res.scalars().all()}

    now_time_str = datetime.now().strftime("%H:%M")
    new_subtotal = order.subtotal or 0.0
    added_details = []

    for item_data in payload.items:
        menu_item = menu_items_map.get(item_data.menu_item_id)
        if not menu_item:
            raise HTTPException(status_code=404, detail="Taom topilmadi")

        # Stop-list tekshiruvi (1.5.2)
        if menu_item.is_deleted or not menu_item.is_available or menu_item.is_stop_list:
            raise HTTPException(400, f"'{menu_item.name}' hozirda stop-listda (tugagan)")

        # Bir xil taomlar alohida yangi qator bo'lib ko'paymasdan,
        # mavjud qatorning soni (quantity) oshiriladi.
        existing_line = next(
            (it for it in order.items if it.menu_item_id == item_data.menu_item_id
             and (it.special_note or None) == (item_data.special_note or None)
                     and (it.portion_size or None) == (item_data.portion_size or None)
                     and not menu_item.is_weighted
                     and it.unit_price == menu_item.price
                     and (it.name_snapshot or menu_item.name) == menu_item.name),
            None
        )

        if existing_line:
            existing_line.quantity += item_data.quantity
            existing_line.total_price = line_total(
                menu_item, existing_line.quantity, existing_line.weight, existing_line.manual_price, existing_line.unit_price
            )
            order_item = existing_line
        else:
            tot_price = line_total(menu_item, item_data.quantity, item_data.weight)
            order_item = OrderItem(
                order_id=order.id,
                menu_item_id=item_data.menu_item_id,
                name_snapshot=menu_item.name,
                quantity=item_data.quantity,
                unit_price=menu_item.price,
                total_price=tot_price,
                special_note=item_data.special_note,
                portion_size=(item_data.portion_size or None),
                weight=item_data.weight,
                item_time=now_time_str,
                sent_to_kitchen=False,
                sent_to_kitchen_at=None,
                sent_quantity=0,
            )
            order_item.menu_item = menu_item
            db.add(order_item)
            order.items.append(order_item)

        menu_item.total_ordered = (menu_item.total_ordered or 0) + item_data.quantity
        added_details.append({
            "name": menu_item.name,
            "quantity": item_data.quantity,
            "price": menu_item.price,
            "note": item_data.special_note,
            "size": item_data.portion_size,
            "item_time": now_time_str,
        })

    await recalc_order_totals(db, order)

    if current_user.commission_percent and current_user.commission_percent > 0:
        order.waiter_share_amount = (order.subtotal or 0.0) * (current_user.commission_percent / 100.0)

    await db.flush()
    if payload.send_to_kitchen_immediately:
        await _send_to_kitchen(order_id, False, db, current_user,
                               IdempotencyHandler(None, '', db), finalize=False)
    full_order = await load_order_full(db, order_id)
    if not full_order:
        full_order = order
    resp = build_order_response(full_order)
    await idempotency.save_response(current_user.id, resp)
    await db.commit()
    wake_printer_worker()
    resp_dict = resp.model_dump() if hasattr(resp, "model_dump") else resp.dict()
    rest_id = resp_dict.get("restaurant_id", 1)
    ord_id = resp_dict.get("id", order_id)
    ord_num = resp_dict.get("order_number", "")
    tbl_id = resp_dict.get("table_id")
    ord_tot = resp_dict.get("total", 0.0)
    ord_sub = resp_dict.get("subtotal", 0.0)
    table_num = resp_dict.get("table_number")

    await manager.broadcast_to_restaurant(rest_id, {
        "type": "order_updated",
        "order": resp_dict,
        "order_id": ord_id,
        "order_number": ord_num,
        "table_id": tbl_id,
        "table_number": table_num,
        "total": ord_tot,
        "subtotal": ord_sub,
        "added_items": added_details,
    })

    return resp


# ─── Taom sonini o'zgartirish [- 1 +] ──────────────────────────
@router.patch("/{order_id}/items/{item_id}/quantity", response_model=OrderResponse, summary="Taom sonini o'zgartirish")
async def update_item_quantity(
    order_id: int,
    item_id: int,
    payload: UpdateItemQtyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("waiter", "admin", "developer", "cashier")),
):
    # 1. Buyurtma qatorini qulflash (race condition oldini olish)
    await lock_rows(db, Order, [order_id])

    order = await load_order_full(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Buyurtma topilmadi")

    if order.status in (OrderStatus.PAID, OrderStatus.CANCELLED) or order.is_paid:
        raise HTTPException(status_code=400, detail="Yopilgan yoki bekor qilingan buyurtmani o'zgartirib bo'lmaydi")

    order_item = next((it for it in order.items if it.id == item_id), None)
    if not order_item:
        raise HTTPException(status_code=404, detail="Taom topilmadi")

    if payload.quantity > order_item.quantity and (not order_item.menu_item or
            order_item.menu_item.is_deleted or not order_item.menu_item.is_available or order_item.menu_item.is_stop_list):
        raise HTTPException(400, "Bu taom hozir mavjud emas yoki stop-listda")

    # Oshxonaga ketgan taom tekshiruvi:
    sent_qty = kitchen_sent_quantity(order_item)
    if payload.quantity < sent_qty:
        require_kitchen_admin(current_user)

        # Admin oshxonaga ketgan taom sonini kamaytirsa
        cancelled_qty = sent_qty - payload.quantity
        from app.core.audit import log_audit_event
        await log_audit_event(
            db=db,
            restaurant_id=order.restaurant_id,
            action="cancel_kitchen_item_qty",
            user=current_user,
            entity_type="order_item",
            entity_id=order_item.id,
            details={
                "order_id": order.id,
                "dish_name": order_item.menu_item.name if order_item.menu_item else "Taom",
                "cancelled_qty": cancelled_qty,
                "new_qty": payload.quantity,
                "table": order.table.number if order.table else None,
            },
        )
        set_res = await db.execute(select(RestaurantSettings).where(RestaurantSettings.restaurant_id == order.restaurant_id))
        settings = set_res.scalar_one_or_none()
        waiter_name = (order.waiter.full_name or order.waiter.username) if order.waiter else (current_user.full_name or current_user.username)
        await _send_cancellation_receipt(db, order, order_item.menu_item, cancelled_qty, waiter_name, settings)
        order_item.sent_quantity = payload.quantity

    order_item.quantity = payload.quantity
    order_item.prepared_quantity = min(order_item.prepared_quantity or 0, payload.quantity)
    menu_item = order_item.menu_item
    if menu_item:
        order_item.total_price = line_total(
            menu_item, payload.quantity, order_item.weight, order_item.manual_price, order_item.unit_price
        )
    else:
        order_item.total_price = round((order_item.unit_price or 0.0) * payload.quantity, 2)

    await recalc_order_totals(db, order)
    await db.flush()
    await db.commit()
    wake_printer_worker()


    full_order = await load_order_full(db, order_id)
    if not full_order:
        full_order = order
    resp = build_order_response(full_order)
    resp_dict = resp.model_dump() if hasattr(resp, "model_dump") else resp.dict()
    rest_id = resp_dict.get("restaurant_id", 1)
    ord_id = resp_dict.get("id", order_id)
    tbl_id = resp_dict.get("table_id")
    tbl_num = resp_dict.get("table_number")
    tbl_status = "occupied"
    tbl_occ = True
    has_table = tbl_id is not None

    await manager.broadcast_to_restaurant(
        rest_id,
        {
            "type": "order_updated",
            "order": resp_dict,
            "order_id": ord_id,
        }
    )
    if has_table and tbl_id:
        await manager.broadcast_to_restaurant(
            rest_id,
            {
                "type": "table_status_updated",
                "table_id": tbl_id,
                "table_number": tbl_num,
                "status": tbl_status,
                "is_occupied": tbl_occ,
                "active_order_id": ord_id,
            }
        )

    return resp


# ─── Taom miqdorini nisbiy o'zgartirish (Delta) ───────────────────
@router.patch("/{order_id}/items/{item_id}/delta", response_model=OrderResponse, summary="Taom miqdorini nisbiy o'zgartirish (+1, -1, delta)")
async def update_item_delta(
    order_id: int,
    item_id: int,
    payload: UpdateItemDeltaRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("waiter", "admin", "developer", "cashier")),
    idempotency: IdempotencyHandler = Depends(get_idempotency_handler),
):
    """Taom sonini delta bo'yicha o'zgartirish (+1, -1 va h.k.). Agar natija <= 0 bo'lsa o'chiriladi."""
    cached = await idempotency.get_cached_response(current_user.id)
    if cached is not None:
        return cached
    # 1. Buyurtma qatorini qulflash
    await lock_rows(db, Order, [order_id])

    order = await load_order_full(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Buyurtma topilmadi")

    if order.status in (OrderStatus.PAID, OrderStatus.CANCELLED) or order.is_paid:
        raise HTTPException(status_code=400, detail="Yopilgan yoki bekor qilingan buyurtmani o'zgartirib bo'lmaydi")

    order_item = next((it for it in order.items if it.id == item_id), None)
    if not order_item:
        raise HTTPException(status_code=404, detail="Taom topilmadi")

    new_quantity = order_item.quantity + payload.delta
    if payload.delta > 0 and (not order_item.menu_item or
            order_item.menu_item.is_deleted or not order_item.menu_item.is_available or order_item.menu_item.is_stop_list):
        raise HTTPException(400, "Bu taom hozir mavjud emas yoki stop-listda")

    # Natija 0 yoki undan kam bo'lsa -> delete_order_item mantiqi
    if new_quantity <= 0:
        if kitchen_sent_quantity(order_item):
            require_kitchen_admin(current_user)

            cancelled_qty = kitchen_sent_quantity(order_item)
            from app.core.audit import log_audit_event
            await log_audit_event(
                db=db,
                restaurant_id=order.restaurant_id,
                action="delete_kitchen_item",
                user=current_user,
                entity_type="order_item",
                entity_id=order_item.id,
                details={
                    "order_id": order.id,
                    "dish_name": order_item.menu_item.name if order_item.menu_item else "Taom",
                    "cancelled_qty": cancelled_qty,
                    "table": order.table.number if order.table else None,
                },
            )
            set_res = await db.execute(select(RestaurantSettings).where(RestaurantSettings.restaurant_id == order.restaurant_id))
            settings = set_res.scalar_one_or_none()
            waiter_name = (order.waiter.full_name or order.waiter.username) if order.waiter else (current_user.full_name or current_user.username)
            await _send_cancellation_receipt(db, order, order_item.menu_item, cancelled_qty, waiter_name, settings)

        if order.items:
            order.items = [i for i in order.items if i.id != item_id]
        await db.delete(order_item)
        await db.flush()

        # Agar taom o'chirilgandan keyin buyurtmada boshqa taom qolmasa
        if not order.items:
            order.status = OrderStatus.CANCELLED
            if order.table:
                other_open_res = await db.execute(
                    select(func.count(Order.id)).where(
                        Order.table_id == order.table_id,
                        Order.id != order.id,
                        Order.is_paid == False,
                        Order.status.notin_([OrderStatus.PAID, OrderStatus.CANCELLED]),
                    )
                )
                other_cnt = other_open_res.scalar() or 0
                if other_cnt == 0:
                    order.table.status = TableStatus.AVAILABLE
                    order.table.is_occupied = False
    else:
        # new_quantity > 0: update_item_quantity mantiqi
        if new_quantity > 500:
            raise HTTPException(status_code=400, detail="Taom miqdori 500 dan oshishi mumkin emas")

        sent_qty = kitchen_sent_quantity(order_item)
        if new_quantity < sent_qty:
            require_kitchen_admin(current_user)

            cancelled_qty = sent_qty - new_quantity
            from app.core.audit import log_audit_event
            await log_audit_event(
                db=db,
                restaurant_id=order.restaurant_id,
                action="cancel_kitchen_item_qty",
                user=current_user,
                entity_type="order_item",
                entity_id=order_item.id,
                details={
                    "order_id": order.id,
                    "dish_name": order_item.menu_item.name if order_item.menu_item else "Taom",
                    "cancelled_qty": cancelled_qty,
                    "new_qty": new_quantity,
                    "table": order.table.number if order.table else None,
                },
            )
            set_res = await db.execute(select(RestaurantSettings).where(RestaurantSettings.restaurant_id == order.restaurant_id))
            settings = set_res.scalar_one_or_none()
            waiter_name = (order.waiter.full_name or order.waiter.username) if order.waiter else (current_user.full_name or current_user.username)
            await _send_cancellation_receipt(db, order, order_item.menu_item, cancelled_qty, waiter_name, settings)
            order_item.sent_quantity = new_quantity

        order_item.quantity = new_quantity
        order_item.prepared_quantity = min(order_item.prepared_quantity or 0, new_quantity)
        menu_item = order_item.menu_item
        if menu_item:
            order_item.total_price = line_total(
                menu_item, new_quantity, order_item.weight, order_item.manual_price, order_item.unit_price
            )
        else:
            order_item.total_price = round((order_item.unit_price or 0.0) * new_quantity, 2)

    await recalc_order_totals(db, order)
    await db.flush()
    full_order = await load_order_full(db, order_id) or order
    resp = build_order_response(full_order)
    await idempotency.save_response(current_user.id, resp)
    await db.commit()
    wake_printer_worker()

    # expire_on_commit=False: the response already contains the committed state.
    resp_dict = resp.model_dump() if hasattr(resp, "model_dump") else resp.dict()
    rest_id = resp_dict.get("restaurant_id", 1)
    ord_id = resp_dict.get("id", order_id)
    tbl_id = resp_dict.get("table_id")
    tbl_num = resp_dict.get("table_number")
    has_table = tbl_id is not None

    await manager.broadcast_to_restaurant(
        rest_id,
        {
            "type": "order_updated",
            "order": resp_dict,
            "order_id": ord_id,
        }
    )
    if has_table and tbl_id and order.table:
        await manager.broadcast_to_restaurant(
            rest_id,
            {
                "type": "table_status_updated",
                "table_id": tbl_id,
                "table_number": tbl_num,
                "status": order.table.status.value if hasattr(order.table.status, "value") else str(order.table.status),
                "is_occupied": order.table.status == TableStatus.OCCUPIED,
                "active_order_id": ord_id if order.table.status == TableStatus.OCCUPIED else None,
            }
        )

    return resp


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

    Ofitsiant oshxonaga yuborilgandan keyin ham tarozidagi yakuniy
    summa yoki og'irlikni tuzatadi. Summa berilsa og'irlik undan olinadi;
    faqat og'irlik berilsa summa hisoblanadi. Dona soni o'zgarmaydi.
    """
    await lock_rows(db, Order, [order_id])
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
    if order.is_paid or order.status in (OrderStatus.PAID, OrderStatus.CANCELLED):
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

    old_total = order_item.total_price or 0
    old_weight = order_item.weight
    old_manual_price = order_item.manual_price
    was_sent = kitchen_sent_quantity(order_item) > 0
    unit_price = order_item.unit_price or 0.0
    qty = max(1, order_item.quantity or 1)
    if unit_price <= 0:
        raise HTTPException(400, "Bir kilogramm yoki litr narxi belgilanmagan. Avval admin narxni tekshirsin.")
    # One input is authoritative. Derive the other, including for older clients
    # that send both fields; never retain an old weight with a new amount.
    order_item.manual_price = round(float(payload.price), 2) if has_price else None
    if has_price:
        order_item.weight = round(float(order_item.manual_price) / (unit_price * qty), 3)
    else:
        order_item.weight = payload.weight
    order_item.total_price = line_total(
        menu_item, order_item.quantity, order_item.weight, order_item.manual_price, order_item.unit_price
    )

    if was_sent and (old_total != order_item.total_price or old_weight != order_item.weight or old_manual_price != order_item.manual_price):
        from app.core.audit import log_audit_event
        await log_audit_event(db=db, restaurant_id=order.restaurant_id, action="edit_kitchen_item_price",
            user=current_user, entity_type="order_item", entity_id=order_item.id,
            details={"order_id": order.id, "old_total": old_total, "new_total": order_item.total_price,
                     "old_weight": old_weight, "new_weight": order_item.weight,
                     "quantity": order_item.quantity, "unit_price": unit_price,
                     "input": "price" if has_price else "weight"})

    await recalc_order_totals(db, order)
    await db.flush()
    await db.commit()
    full_order = await load_order_full(db, order_id) or order
    resp = build_order_response(full_order)
    resp_dict = resp.model_dump() if hasattr(resp, "model_dump") else resp.dict()
    await manager.broadcast_to_restaurant(
        resp_dict.get("restaurant_id", 1),
        {"type": "order_updated", "order": resp_dict, "order_id": resp_dict.get("id", order_id)}
    )
    return resp


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
    await lock_rows(db, Order, [order_id])
    item_res = await db.execute(
        select(OrderItem).where(OrderItem.id == item_id, OrderItem.order_id == order_id)
    )
    order_item = item_res.scalar_one_or_none()
    if not order_item:
        raise HTTPException(status_code=404, detail="Taom topilmadi")

    order = await load_order_full(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Buyurtma topilmadi")
    if order.is_paid or order.status in (OrderStatus.PAID, OrderStatus.CANCELLED):
        raise HTTPException(status_code=400, detail="Yopilgan buyurtmani o'zgartirib bo'lmaydi")

    size = (payload.portion_size or "").strip()
    if kitchen_sent_quantity(order_item) > 0 and size != (order_item.portion_size or ""):
        raise HTTPException(409, "Taom oshxonaga yuborilgan. Hajmni almashtirish uchun eski taomni bekor qilib, yangisini qo'shing")
    order_item.portion_size = size or None

    await db.flush()
    await db.commit()
    full_order = await load_order_full(db, order_id) or order
    resp = build_order_response(full_order)
    resp_dict = resp.model_dump() if hasattr(resp, "model_dump") else resp.dict()
    await manager.broadcast_to_restaurant(
        resp_dict.get("restaurant_id", 1),
        {"type": "order_updated", "order": resp_dict, "order_id": resp_dict.get("id", order_id)}
    )
    return resp


# ─── Taomni buyurtmadan o'chirish ──────────────────────────────
@router.delete("/{order_id}/items/{item_id}", response_model=OrderResponse, summary="Taomni buyurtmadan o'chirish")
async def delete_order_item(
    order_id: int,
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("waiter", "admin", "developer", "cashier")),
):
    await lock_rows(db, Order, [order_id])
    order_res = await db.execute(
        select(Order)
        .options(
            selectinload(Order.items).selectinload(OrderItem.menu_item),
            selectinload(Order.table),
            selectinload(Order.waiter),
        )
        .where(Order.id == order_id)
    )
    order = order_res.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Buyurtma topilmadi")

    if order.status in (OrderStatus.PAID, OrderStatus.CANCELLED) or order.is_paid:
        raise HTTPException(status_code=400, detail="Yopilgan yoki bekor qilingan buyurtmani o'zgartirib bo'lmaydi")

    order_item = next((it for it in order.items if it.id == item_id), None)
    if not order_item:
        raise HTTPException(status_code=404, detail="Taom topilmadi")

    if kitchen_sent_quantity(order_item):
        require_kitchen_admin(current_user)

        cancelled_qty = kitchen_sent_quantity(order_item)
        from app.core.audit import log_audit_event
        await log_audit_event(
            db=db,
            restaurant_id=order.restaurant_id,
            action="delete_kitchen_item",
            user=current_user,
            entity_type="order_item",
            entity_id=order_item.id,
            details={
                "order_id": order.id,
                "dish_name": order_item.menu_item.name if order_item.menu_item else "Taom",
                "cancelled_qty": cancelled_qty,
                "table": order.table.number if order.table else None,
            },
        )
        set_res = await db.execute(select(RestaurantSettings).where(RestaurantSettings.restaurant_id == order.restaurant_id))
        settings = set_res.scalar_one_or_none()
        waiter_name = (order.waiter.full_name or order.waiter.username) if order.waiter else (current_user.full_name or current_user.username)
        await _send_cancellation_receipt(db, order, order_item.menu_item, cancelled_qty, waiter_name, settings)

    if order.items:
        order.items = [i for i in order.items if i.id != item_id]
    await db.delete(order_item)
    await db.flush()

    # Agar taom o'chirilgandan keyin len(order.items) == 0 bo'lsa, order.status = CANCELLED va table.status = AVAILABLE
    table_freed = False
    if not order.items:
        order.status = OrderStatus.CANCELLED
        if order.table:
            order.table.status = TableStatus.AVAILABLE
            order.table.is_occupied = False
            table_freed = True

    await recalc_order_totals(db, order)
    await db.flush()
    await db.commit()
    wake_printer_worker()


    full_order = await load_order_full(db, order_id)
    if not full_order:
        full_order = order
    resp = build_order_response(full_order)
    resp_dict = resp.model_dump() if hasattr(resp, "model_dump") else resp.dict()
    rest_id = resp_dict.get("restaurant_id", 1)
    ord_id = resp_dict.get("id", order_id)
    tbl_id = resp_dict.get("table_id")
    tbl_num = resp_dict.get("table_number")
    has_table = tbl_id is not None

    await manager.broadcast_to_restaurant(
        rest_id,
        {
            "type": "order_updated",
            "order": resp_dict,
            "order_id": ord_id,
            "table_id": tbl_id,
        }
    )
    if has_table and tbl_id:
        await manager.broadcast_to_restaurant(
            rest_id,
            {
                "type": "table_status_updated",
                "table_id": tbl_id,
                "table_number": tbl_num,
                "status": "available" if table_freed else "occupied",
                "is_occupied": not table_freed,
                "active_order_id": None if table_freed else ord_id,
            }
        )

    return resp


# ─── Oshxona va chek izohlarini yangilash ─────────────────────
@router.patch("/{order_id}/notes", response_model=OrderResponse, summary="Izohlarni yangilash (Oshxona / Chek)")
async def update_order_notes(
    order_id: int,
    payload: OrderNoteUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("waiter", "admin", "developer", "cashier")),
):
    await lock_rows(db, Order, [order_id])
    order_res = await db.execute(
        select(Order).options(selectinload(Order.items).selectinload(OrderItem.menu_item), selectinload(Order.table), selectinload(Order.waiter)).where(Order.id == order_id)
    )
    order = order_res.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Buyurtma topilmadi")

    if order.is_paid or order.status == OrderStatus.CANCELLED:
        raise HTTPException(409, "Yopilgan buyurtmani o'zgartirib bo'lmaydi")

    if payload.kitchen_note is not None:
        order.kitchen_note = payload.kitchen_note
    if payload.receipt_note is not None:
        order.receipt_note = payload.receipt_note

    await db.flush()
    order = await load_order_full(db, order.id) or order
    return build_order_response(order)


@router.post("/{order_id}/print-bill", summary="Buyurtma hisob chekini chiqarish (Kassa / Mijoz)")
async def print_order_bill(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("waiter", "admin", "developer", "cashier")),
    idempotency: IdempotencyHandler = Depends(get_idempotency_handler),
):
    """Buyurtma hisob chekini (1-Printer: Mijoz cheki) chop etish"""
    cached = await idempotency.get_cached_response(current_user.id)
    if cached is not None: return cached
    await lock_rows(db, Order, [order_id])
    order = await load_order_full(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Buyurtma topilmadi")
    if missing_weight_items(order):
        raise HTTPException(400, "Vaznli taom narxini kiriting")

    s_res = await db.execute(
        select(RestaurantSettings).where(RestaurantSettings.restaurant_id == order.restaurant_id)
    )
    settings = s_res.scalar_one_or_none()
    cust_printer = (getattr(settings, "printer_customer_name", None) or "").strip()
    if not cust_printer:
        raise HTTPException(
            status_code=400,
            detail="Printer sozlanmagan: Mijoz kassa cheki (printer_customer_name)",
        )
    popts = printer_options(settings)

    items_for_receipt = []
    subtotal = 0.0
    for it in order.items:
        dish_name = it.name_snapshot or (it.menu_item.name if it.menu_item else "Таом")
        items_for_receipt.append({
            "name": dish_name,
            "quantity": it.quantity,
            "unit_price": it.unit_price,
            "total_price": it.total_price,
            "size": it.portion_size,
            "weight": it.weight,
            "manual_price": it.manual_price,
            "unit": (getattr(it.menu_item, "unit", None) or "kg") if it.menu_item else "kg",
            "is_weighted": bool(getattr(it.menu_item, "is_weighted", False)) if it.menu_item else False,
        })
        subtotal += it.total_price

    fee_pct = order.service_fee_percent if order.service_fee_percent is not None else 12.0
    fee_amount = order.service_fee_amount if order.service_fee_amount is not None else round(subtotal * (fee_pct / 100.0), 2)
    grand_total = round(subtotal + fee_amount - (order.discount or 0.0), 2)

    rest_res = await db.execute(select(Restaurant).where(Restaurant.id == order.restaurant_id))
    restaurant = rest_res.scalar_one_or_none()

    rest_name = receipt_title(settings, restaurant)
    table_disp = f"Stol #{order.table.number}" if order.table else (order.hall_name or "Olib ketish / Dastavka")
    waiter_disp = (order.waiter.full_name or order.waiter.username) if order.waiter else (current_user.full_name or current_user.username)

    bill_text = format_pre_check(
        restaurant_name=rest_name,
        address=(getattr(settings, "receipt_address", None) if settings else None) or (restaurant.address if restaurant else None),
        phone=(getattr(settings, "receipt_phone", None) if settings else None) or (restaurant.phone if restaurant else None),
        table_name=table_disp,
        waiter_name=waiter_disp,
        order_number=order.order_number,
        items=items_for_receipt,
        subtotal=subtotal,
        service_fee_percent=fee_pct,
        service_fee_amount=fee_amount,
        total=grand_total,
        discount=order.discount or 0,
        advance_amount=(order.advance_amount or 0) if order.is_paid else ((order.table.deposit_amount or 0) if order.table else 0),
        created_at=order.created_at,
        paper_width=getattr(settings, "printer_paper_width", 80) or 80,
        font_size=popts["font_size"],
        char_spacing=popts["char_spacing"],
        wifi_pass=getattr(settings, "receipt_wifi_pass", None) if settings else None,
        footer_text=getattr(settings, "receipt_footer", None) if settings else "Tashrifingiz uchun rahmat!",
    )

    job = None
    if cust_printer:
        job = await enqueue_print_job(
            db,
            restaurant_id=order.restaurant_id,
            order_id=order.id,
            ticket_type="bill",
            printer_name=cust_printer,
            raw_text=bill_text,
            options=popts,
        )

    response = {
        "success": True,
        "order_id": order.id,
        "order_number": order.order_number,
        "raw_text": bill_text,
        "job_id": job.id if job else None,
        "status": "queued" if job else "skipped",
        "printed": False,
        "queued": True if job else False,
        "print_error": None if (job or not getattr(settings, "auto_print_customer_bill", True)) else "Printer sozlanmagan",
    }



# ─── Oshxonaga yuborish (На кухню — Begunok) ───────────────────
    await idempotency.save_response(current_user.id, response)
    await db.commit()
    wake_printer_worker()
    return response

@router.post("/{order_id}/send-to-kitchen", summary="Oshxonaga yuborish (Xprinter Begunok)")
async def send_to_kitchen(
    order_id: int, reprint: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("waiter", "admin", "developer", "cashier")),
    idempotency: IdempotencyHandler = Depends(get_idempotency_handler),
):
    return await _send_to_kitchen(order_id, reprint, db, current_user, idempotency)


async def _send_to_kitchen(order_id, reprint, db, current_user, idempotency, *, finalize=True):
    """
    Ofitsiant 'На кухню' tugmasini bosadi:
    1. FAQAT yangi qo'shilgan taomlarni (quantity - sent_quantity) yuboradi
    2. Xprinter uchun oshxona begunogi matnini formatlaydi (Rasm 1 dagidek)
    3. ReceiptArchive ga 'kitchen' sifatida saqlaydi
    4. Oshpaz KDS ekraniga WebSocket xabar beradi
    """
    cached = await idempotency.get_cached_response(current_user.id)
    if cached is not None:
        return cached

    # 0. SQLite'da ikkita bir vaqtdagi so'rov race condition bo'lmasligi uchun qatorni qulflaymiz:
    await lock_rows(db, Order, [order_id])

    order = await load_order_full(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Buyurtma topilmadi")

    if order.status == OrderStatus.CANCELLED or (order.is_paid and not reprint):
        raise HTTPException(409, "Yopilgan buyurtmani oshxonaga yuborib bo'lmaydi")
    if order.is_paid and reprint and current_user.role not in ('admin', 'cashier', 'developer'):
        raise HTTPException(403, "Yopilgan hisobni faqat kassir qayta chiqarishi mumkin")

    # Oshxonaga faqat YANGI qo'shilganlar chiqadi.
    pending: List[tuple] = []   # (OrderItem, shu begunokda chiqadigan yangi soni)
    for it in order.items:
        qty = it.quantity or 0
        already = it.sent_quantity or 0
        delta = qty - already
        if delta > 0:
            pending.append((it, delta))

    if not pending and not reprint:
        # Yangi taom yo'q. Bu yerda hech narsa chop etilmaydi — ofitsiant
        # xohlasa "qayta chiqarish" bilan butun begunokni takrorlaydi.
        response = {
            "success": True,
            "order_id": order.id,
            "items_count": 0,
            "nothing_new": True,
            "message": "Yangi taom yo'q — barchasi oshxonaga allaqachon yuborilgan.",
            "tickets": [],
            "raw_text": "",
        }
        await idempotency.save_response(current_user.id, response)
        return response

    if reprint:
        from app.models.print_job import PrintJob
        outstanding = await db.scalar(select(func.count(PrintJob.id)).where(
            PrintJob.order_id == order_id, PrintJob.ticket_type.in_(['kitchen', 'bar']),
            PrintJob.status.in_(['pending', 'printing', 'uncertain'])))
        if outstanding:
            raise HTTPException(409, "Chek hali navbatda yoki natijasi noaniq. Printer holatini tekshiring")

    if reprint:
        target_items = [(it, it.quantity or 0) for it in order.items if (it.quantity or 0) > 0]
    else:
        target_items = pending

    now_utc = datetime.now(timezone.utc)
    for it, _delta in pending:
        it.is_prepared = False
        it.prepared_at = None
        it.sent_to_kitchen = True
        it.sent_to_kitchen_at = now_utc
        it.sent_quantity = max(it.sent_quantity or 0, it.quantity or 0)

    if pending and order.status in (OrderStatus.PENDING, OrderStatus.CONFIRMED, OrderStatus.READY, OrderStatus.SERVED):
        order.status = OrderStatus.PREPARING
        order.preparing_at = now_utc
        order.ready_at = None

    table_num = order.table.number if order.table else "—"
    room_name = order.table.room if order.table else ""
    waiter_display = current_user.full_name or current_user.username

    set_res = await db.execute(select(RestaurantSettings).where(RestaurantSettings.restaurant_id == order.restaurant_id))
    settings = set_res.scalar_one_or_none()
    paper_width = settings.printer_paper_width if settings else 80

    k1_items = []
    k2_items = []
    bar_items = []
    kassa_items = []

    for it, send_qty in target_items:
        st_raw = getattr(it.menu_item, "kitchen_station", None) if it.menu_item else None
        station = resolve_kitchen_station(st_raw)

        dish_name = it.name_snapshot or (it.menu_item.name if it.menu_item else "Таом")

        item_dict = {
            "name": dish_name,
            "quantity": send_qty,
            "note": it.special_note,
            "size": it.portion_size,
            "weight": it.weight,
            "manual_price": it.manual_price,
            "unit": (getattr(it.menu_item, "unit", None) or "kg") if it.menu_item else "kg",
            "is_weighted": bool(getattr(it.menu_item, "is_weighted", False)) if it.menu_item else False,
        }

        # Stansiya bo'yicha saralash
        if station == "kassa":
            kassa_items.append(item_dict)
        elif station == "bar":
            bar_items.append(item_dict)
        elif station == "cold_kitchen":
            k2_items.append(item_dict)
        elif station == "all":
            k1_items.append(item_dict)
            k2_items.append(item_dict)
        else:
            k1_items.append(item_dict)

    k1_title = (getattr(settings, "kitchen1_title", None) or "").strip() or "1-Oshxona (Qozon taomlari)"
    k2_title = (getattr(settings, "kitchen2_title", None) or "").strip() or "2-Oshxona (Baliq / Somsa)"
    bar_title = (getattr(settings, "bar_title", None) or "").strip() or "BAR (Ichimliklar)"
    kassa_title = "KASSA (Mijozga berish)"

    k1_printer = (getattr(settings, "printer_kitchen1_name", None) or "").strip()
    k2_printer = (getattr(settings, "printer_kitchen2_name", None) or "").strip()
    kassa_printer = (getattr(settings, "printer_customer_name", None) or "").strip()
    # Bar printeri sozlanmagan bo'lsa — kassa printeriga chiqadi.
    bar_printer = kassa_printer

    auto_print = getattr(settings, "auto_print_kitchen", True)
    popts = printer_options(settings)
    cp = popts["codepage"]
    fsize = popts["font_size"]

    stations = [
        ("hot_kitchen", k1_title, k1_printer, k1_items, "KITCHEN1"),
        ("cold_kitchen", k2_title, k2_printer, k2_items, "KITCHEN2"),
        ("bar", bar_title, bar_printer, bar_items, "BAR"),
        ("kassa", kassa_title, kassa_printer, kassa_items, "KASSA"),
    ]

    if not auto_print and not getattr(settings, 'enable_chef_kds', False):
        raise HTTPException(400, "Oshxona printeri yoki KDS ekranini yoqing")
    if auto_print:
        missing_printers = [title for _, title, printer, items, _ in stations if items and not printer]
        if missing_printers:
            raise HTTPException(400, "Printer sozlanmagan: " + ", ".join(missing_printers))

    prepared_tickets = []
    combined_texts = []

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
            order_time=datetime.now(timezone.utc),
            paper_width=paper_width,
            station_title=station_title,
            font_size=fsize,
            char_spacing=popts["char_spacing"],
            is_reprint=bool(reprint),
        )
        combined_texts.append(ticket_text)

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

        prepared_tickets.append({
            "station": station_key,
            "station_title": station_title,
            "printer_name": station_printer,
            "items": station_items,
            "ticket_text": ticket_text,
        })

    generated_tickets = []
    for item_data in prepared_tickets:
        st_key = item_data["station"]
        st_title = item_data["station_title"]
        st_printer = item_data["printer_name"]
        st_items = item_data["items"]
        ticket_text = item_data["ticket_text"]

        job = None
        print_error = None

        if not st_printer:
            print_error = f"Printer sozlanmagan: {st_title}"
            logger.warning(f"send_to_kitchen: {print_error} (order_id={order.id})")
        elif auto_print:
            t_type = "bar" if st_key == "bar" else "kitchen"
            job = await enqueue_print_job(
                db,
                restaurant_id=order.restaurant_id,
                order_id=order.id,
                ticket_type=t_type,
                printer_name=st_printer,
                raw_text=ticket_text,
                options=popts,
            )
        else:
            print_error = None  # Explicit KDS-only delivery mode.

        generated_tickets.append({
            "station": st_key,
            "station_title": st_title,
            "printer_name": st_printer,
            "items": st_items,
            "raw_text": ticket_text,
            "job_id": job.id if job else None,
            "status": "queued" if job else "display",
            "printed": False,
            "queued": True if job is not None else False,
            "print_error": print_error,
        })

    res = {
        "success": True,
        "order_id": order.id,
        "items_count": sum(q for _it, q in target_items),
        "nothing_new": False,
        "tickets": generated_tickets,
        "raw_text": "\n------------------------------------------\n".join(combined_texts),
    }
    await idempotency.save_response(current_user.id, res)
    # Order, print jobs and replay response commit atomically.
    if finalize:
        await db.commit()
        wake_printer_worker()


    main_raw_text = "\n------------------------------------------\n".join(combined_texts) if combined_texts else ""

    if finalize:
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

    res = {
        "success": True,
        "order_id": order.id,
        "items_count": sum(q for _it, q in target_items),
        "nothing_new": False,
        "tickets": generated_tickets,
        "raw_text": main_raw_text,
    }
    return res


# ─── To'lov va Stolni yopish (К оплате — Kassa) ───────────────
@router.post("/{order_id}/checkout", summary="To'lovni qabul qilish va hisobni yopish (К оплате)")
async def checkout_order(
    order_id: int,
    payload: OrderCheckoutRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "cashier", "developer")),
    idempotency: IdempotencyHandler = Depends(get_idempotency_handler),
):
    """
    1. To'lov turlarini hisoblaydi (Naqd, Karta, Click, Nasiya)
    2. Agar Nasiya bo'lsa -> Debt jadvalida qarzdor yozuvini yaratadi
    3. Stolni bo'shatadi (AVAILABLE) faqat boshqa ochiq buyurtma bo'lmasa
    4. Xprinter uchun mijoz hisob cheki (Bill / Pre-check) yaratadi
    5. ReceiptArchive ga 3 yilga saqlaydi
    6. WebSocket orqali barchaga hisob yopilganini e'lon qiladi
    """
    cached = await idempotency.get_cached_response(current_user.id)
    if cached is not None:
        return cached

    # 0. SQLite'da ikkita bir vaqtdagi to'lov ketma-ket bajarilishi va race condition
    # bo'lmasligi uchun tranzaksiyaning eng boshida qatorni qulflaymiz
    await lock_rows(db, Order, [order_id])

    order = await load_order_full(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Buyurtma topilmadi")

    if order.is_paid or order.status == OrderStatus.PAID:
        raise HTTPException(status_code=409, detail="Ushbu buyurtma allaqachon to'langan va yopilgan")
    if order.status == OrderStatus.CANCELLED:
        raise HTTPException(status_code=400, detail="Bekor qilingan buyurtmani to'lab bo'lmaydi")
    if payload.expected_version is not None and payload.expected_version != order.version:
        raise HTTPException(409, "Buyurtma o'zgargan. Kassa oynasini qayta ochib, yangi hisobni tekshiring")

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

    # Bo'sh buyurtma (taom yo'q yoki subtotal == 0) to'lanmasin: 400
    subtotal = money_sum(i.total_price for i in order.items)
    if not order.items or subtotal <= 0:
        raise HTTPException(status_code=400, detail="Bo'sh buyurtmani to'lab bo'lmaydi")

    from app.core.config import settings as app_settings

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
    if payload.service_fee_percent is not None:
        fee_pct = float(payload.service_fee_percent)
    else:
        fee_pct = order_fee_percent(
            order,
            fallback=(settings.service_fee_percent if settings else None),
        )
    fee_amount = percent(subtotal, fee_pct)
    discount = money(payload.discount)

    # discount > subtotal + service_fee bo'lsa 400
    if discount > (subtotal + fee_amount):
        raise HTTPException(
            status_code=400,
            detail="Chegirma summasi buyurtma jami summasidan oshib ketishi mumkin emas",
        )

    # Chegirma subtotal'ning MAX_CASHIER_DISCOUNT_PERCENT foizidan oshsa va foydalanuvchi cashier bo'lsa 403
    discount_pct = (discount / subtotal * 100.0) if subtotal > 0 else 0.0
    user_role = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)
    max_cashier_discount = getattr(app_settings, "MAX_CASHIER_DISCOUNT_PERCENT", 10.0)
    if user_role == "cashier" and discount_pct > max_cashier_discount:
        raise HTTPException(
            status_code=403,
            detail=f"Kassir uchun ruxsat etilgan maksimal chegirma {max_cashier_discount}% (kiritilgan: {round(discount_pct, 1)}%)",
        )

    total = max(0.0, money_sum([subtotal, fee_amount, -discount]))

    advance = round((order.table.deposit_amount or 0) if order.table else 0, 2)
    if advance > total:
        raise HTTPException(409, "Avans hisobdan ko'p. Ortiqchasini bron oynasida qaytarib, so'ng hisobni yoping")
    amount_due = round(total - advance, 2)
    order.advance_amount = advance
    if advance:
        from app.core.deposits import record_movement
        await record_movement(db, order.table, current_user, -advance, 'applied', order_id=order.id)
        order.table.deposit_amount = 0

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
    cash_in = money(payload.cash_amount)
    card_in = money(payload.card_amount)
    click_in = money(payload.click_amount)
    debt_in = money(payload.debt_amount)

    if (cash_in + card_in + click_in + debt_in) == 0.0:
        if payload.payment_method == "cash":
            cash_in = amount_due
        elif payload.payment_method == "card":
            card_in = amount_due
        elif payload.payment_method == "click":
            click_in = amount_due
        elif payload.payment_method == "debt":
            debt_in = amount_due

    # Naqd pul mijozdan ortig'i bilan olinishi mumkin (qaytim beriladi),
    # lekin karta / Click / nasiya summasi hisobdan oshib ketmasligi kerak.
    if debt_in > 0 and settings is not None and not settings.allow_debt_payment:
        raise HTTPException(400, "Nasiya to'lovi sozlamalarda o'chirilgan")
    non_cash = card_in + click_in + debt_in
    if non_cash - amount_due > 0.01:
        raise HTTPException(
            status_code=400,
            detail=(
                f"To'lov summasi hisobdan oshib ketdi: "
                f"{non_cash:,.0f} so'm kiritildi, hisob {amount_due:,.0f} so'm."
            ),
        )

    tendered = cash_in + non_cash
    if tendered + 0.01 < amount_due:
        raise HTTPException(
            status_code=400,
            detail=(
                f"To'lov to'liq emas: {tendered:,.0f} so'm kiritildi, "
                f"hisob {amount_due:,.0f} so'm. Yetishmayotgan summa: {amount_due - tendered:,.0f} so'm. "
                f"Qolgan qismini nasiya (qarz) sifatida rasmiylashtiring."
            ),
        )

    # Kassaga faqat haqiqiy tushum yoziladi — naqd ortiqchasi qaytim sifatida
    # qaytariladi va hisobotlarni shishirmaydi.
    change_amount = round(max(0.0, tendered - amount_due), 2)
    order.card_amount = card_in
    order.click_amount = click_in
    order.debt_amount = debt_in
    order.cash_amount = round(max(0.0, cash_in - change_amount), 2)

    debt_obj = None
    if order.debt_amount > 0:
        # Shu order_id uchun Debt allaqachon bor bo'lsa ikkinchisini yaratma
        existing_debt_res = await db.execute(
            select(Debt).where(Debt.order_id == order.id)
        )
        debt_obj = existing_debt_res.scalar_one_or_none()
        if debt_obj and (debt_obj.restaurant_id != order.restaurant_id or
                abs(debt_obj.amount - order.debt_amount) > 0.01 or
                (debt_obj.paid_amount or 0) != 0 or
                abs(debt_obj.remaining_amount - order.debt_amount) > 0.01):
            raise HTTPException(409, "Mavjud qarz ushbu hisobga mos emas. Nasiya yozuvini tekshiring")
        if not debt_obj:
            from app.routers.debts import validate_debt_customer
            cust_name, cust_phone = validate_debt_customer(
                payload.debt_customer_name or order.customer_name, payload.debt_customer_phone)
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

    # Kitchen tickets and payment must succeed or roll back together. A separate
    # no-key handler prevents the nested send from overwriting checkout replay.
    kitchen_result = None
    if any((it.sent_quantity or 0) < it.quantity for it in order.items):
        order.is_paid = False
        order.status = OrderStatus.PENDING
        await db.flush()
        kitchen_result = await _send_to_kitchen(order.id, False, db, current_user,
            IdempotencyHandler(None, "checkout-kitchen", db), finalize=False)
        order.is_paid = True
        order.status = OrderStatus.PAID

    waiter_user = order.waiter or current_user
    if waiter_user and waiter_user.commission_percent and waiter_user.commission_percent > 0:
        order.waiter_share_percent = waiter_user.commission_percent
        order.waiter_share_amount = subtotal * (waiter_user.commission_percent / 100.0)

    # Stol faqat shu stolda boshqa ochiq buyurtma qolmaganda AVAILABLE bo'lsin
    table_became_available = False
    if order.table_id:
        other_open_orders_res = await db.execute(
            select(func.count(Order.id)).where(
                Order.table_id == order.table_id,
                Order.id != order.id,
                Order.is_paid == False,
                Order.status.notin_([OrderStatus.PAID, OrderStatus.CANCELLED]),
            )
        )
        other_open_orders_count = other_open_orders_res.scalar() or 0
        if other_open_orders_count == 0 and order.table:
            order.table.status = TableStatus.AVAILABLE
            order.table.current_pin = None
            order.table.is_unlocked = False
            order.table.reserved_by_name = None
            order.table.reserved_by_phone = None
            order.table.reserved_time = None
            order.table.reserved_guests = None
            order.table.deposit_amount = 0.0
            order.table.reservation_note = None
            table_became_available = True

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
            "name": it.name_snapshot or (it.menu_item.name if it.menu_item else "Taom"),
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
        advance_amount=advance,
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
        advance_amount=advance,
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
    audit_details = {
        "order_number": order.order_number,
        "total": total,
        "payment_method": order.payment_method,
        "cash": round(cash_in, 2),
        "table_id": order.table_id,
    }
    if discount > 0:
        audit_details["discount"] = discount
        audit_details["discount_percent"] = round(discount_pct, 2)

    await log_audit_event(
        db=db,
        restaurant_id=order.restaurant_id,
        action="order_checkout",
        user=current_user,
        entity_type="order",
        entity_id=order.id,
        details=audit_details,
    )

    if payload.print_receipt and getattr(settings, "auto_print_customer_bill", True):
        cust_printer = (getattr(settings, "printer_customer_name", None) or "").strip()
        if cust_printer:
            await enqueue_print_job(
                db,
                restaurant_id=order.restaurant_id,
                order_id=order.id,
                ticket_type="kassa",
                printer_name=cust_printer,
                raw_text=bill_text,
                options=popts,
            )
        else:
            logger.warning("checkout_order: Mijoz kassa cheki navbatga qo'yilmadi — printer sozlanmagan (printer_customer_name)")

    full_order = await load_order_full(db, order.id) or order
    res = {
        "success": True,
        "order_id": order.id,
        "order_number": order.order_number,
        "total": total,
        "payment_method": order.payment_method,
        "cash_received": round(cash_in, 2),
        "change_amount": change_amount,
        "advance_amount": advance,
        "amount_due": amount_due,
        "raw_text": bill_text,
        "debt_created": bool(debt_obj),
        "kitchen": kitchen_result,
        "order": build_order_response(full_order),
    }
    await idempotency.save_response(current_user.id, res)
    # Order, payment, receipt, jobs and replay response commit atomically.
    await db.commit()
    wake_printer_worker()

    # Faqat kassa cheklari (checkout / final bill) uchun PDF arxiv saqlash (commit'dan keyin, non-blocking)
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
            "advance_amount": advance,
            "amount_due": amount_due,
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
        create_bg_task(async_save_checkout_receipt_pdf(pdf_payload))
    except Exception as exc:
        import logging
        logging.getLogger("orders").warning(f"Kassa PDF chekini arxivlashda xatolik: {exc}")


    # WebSocket xabarlari (commit'dan keyin)
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

    if order.table and table_became_available:
        await manager.broadcast_to_roles(order.restaurant_id, ["waiter", "admin"], {
            "type": "table_status_updated",
            "table_id": order.table.id,
            "table_number": order.table.number,
            "status": TableStatus.AVAILABLE.value,
            "new_status": TableStatus.AVAILABLE.value,
        })

    return res



# ─── Ofitsiant chaqirish ────────────────────────────────────
async def call_waiter_table_key(request: Request) -> str:
    try:
        body = await request.json()
        table_id = body.get("table_id") if isinstance(body, dict) else ""
    except Exception:
        table_id = ""
    return f"call:{table_id}"


def call_waiter_ip_key(request: Request) -> str:
    ip = get_client_ip(request)
    return f"call_ip:{ip}"


@router.post(
    "/call-waiter",
    status_code=200,
    summary="Ofitsiant chaqirish",
    dependencies=[
        Depends(
            RateLimiter(
                times=1,
                seconds=20,
                key_func=call_waiter_table_key,
                detail="Ofitsiant chaqirildi, biroz kuting.",
            )
        ),
        Depends(
            RateLimiter(
                times=30,
                seconds=60,
                key_func=call_waiter_ip_key,
                detail="Ofitsiant chaqirildi, biroz kuting.",
            )
        ),
    ],
)
async def call_waiter(payload: CallWaiterRequest, db: AsyncSession = Depends(get_db)):
    """Mijoz stolidan ofitsiantni chaqiradi (rate-limit va spam himoyasi bilan)"""
    # Serialize call creation/resolution for this table across PostgreSQL workers.
    # SQLite write requests already hold BEGIN IMMEDIATE.
    result = await db.execute(select(Table).where(Table.id == payload.table_id).with_for_update())
    table = result.scalar_one_or_none()
    if not table or not table.is_active:
        raise HTTPException(status_code=404, detail="Stol topilmadi yoki faol emas")

    if not payload.qr_token or payload.qr_token != table.qr_token:
        raise HTTPException(403, "Ofitsiant chaqirish uchun stol QR kodini oching")

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

    pending_notification = await db.scalar(select(Notification).where(
        Notification.restaurant_id == table.restaurant_id,
        Notification.type == NotificationType.CALL_WAITER,
        Notification.is_read == False,
        Notification.data["table_id"].as_integer() == table.id,
    ).order_by(Notification.id.desc()).limit(1))
    if pending_notification:
        return {"success": True, "call_id": pending_notification.id,
                "message": f"Stol #{table.number} uchun ofitsiant allaqachon chaqirilgan"}

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
        create_bg_task(send_telegram_alert(settings.telegram_bot_token, settings.telegram_chat_id, tg_text))


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
        if table_id and table_id in seen_table_ids:
            continue
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
                    # Negative order IDs cannot collide with notification IDs.
                    id=-o.id,
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
            seen_table_ids.add(o.table_id)

    return calls


async def _finish_table_calls(db, restaurant_id, table_id):
    """Keep the two historical call stores consistent in one transaction."""
    notifications = (await db.scalars(select(Notification).where(
        Notification.restaurant_id == restaurant_id,
        Notification.type == NotificationType.CALL_WAITER,
        Notification.is_read == False,
        Notification.data["table_id"].as_integer() == table_id,
    ))).all()
    for notification in notifications:
        notification.is_read = True
        notification.read_at = datetime.now(timezone.utc)
    orders = (await db.scalars(select(Order).where(
        Order.restaurant_id == restaurant_id, Order.table_id == table_id,
        Order.call_waiter == True,
    ))).all()
    for order in orders:
        order.call_waiter = False
        order.call_status = CallStatus.COMPLETED
    return [notification.id for notification in notifications]


# ─── Chaqiruvni yakunlash (Bordim) ───────────────────────────
@router.post("/calls/{call_id}/resolve", summary="Ofitsiant chaqiruvini yakunlash")
async def resolve_waiter_call(
    call_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("waiter", "admin", "developer")),
):
    """Ofitsiant yoki Admin chaqiruv bo'yicha mijozga xizmat ko'rsatganini tasdiqlaydi"""
    notif = await db.scalar(select(Notification).where(
        Notification.id == call_id, Notification.type == NotificationType.CALL_WAITER,
    )) if call_id > 0 else None
    order = None
    if notif is not None:
        table_id = (notif.data or {}).get("table_id")
        restaurant_id = notif.restaurant_id
    else:
        # Support IDs emitted by old clients as well as the unambiguous new IDs.
        order_id = -call_id if call_id < 0 else call_id - 100000 if call_id > 100000 else call_id
        order = await db.scalar(select(Order).where(Order.id == order_id))
        if order is None:
            raise HTTPException(404, "Chaqiruv topilmadi")
        table_id, restaurant_id = order.table_id, order.restaurant_id
    table = await db.scalar(select(Table).where(
        Table.id == table_id, Table.restaurant_id == restaurant_id,
    ).with_for_update())
    if table is None:
        raise HTTPException(404, "Chaqiruv stoli topilmadi")

    if notif is not None:
        await db.refresh(notif)
        if notif.is_read:
            # A retry of an old call must never acknowledge a newer call.
            return {"success": True, "already_resolved": True, "message": "Chaqiruv avval yakunlangan"}
    else:
        await db.refresh(order)
        if not order.call_waiter:
            return {"success": True, "already_resolved": True, "message": "Chaqiruv avval yakunlangan"}
        newer_call = await db.scalar(select(Notification.id).where(
            Notification.restaurant_id == restaurant_id,
            Notification.type == NotificationType.CALL_WAITER,
            Notification.is_read == False,
            Notification.data["table_id"].as_integer() == table_id,
        ).limit(1))
        if newer_call is not None:
            raise HTTPException(409, "Chaqiruv yangilangan. Ro'yxatni yangilab, qayta qabul qiling")

    resolved_ids = await _finish_table_calls(db, restaurant_id, table_id)
    table_num = table.number

    await db.flush()
    await db.commit()

    waiter_display = current_user.full_name or current_user.username
    await manager.broadcast_to_roles(
        restaurant_id,
        ["waiter", "admin"],
        {
            "type": "call_completed",
            "call_id": call_id,
            "resolved_call_ids": resolved_ids,
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
    qr_token: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """Mijoz yoki xodim ushbu stoldagi barcha faol (to'lanmagan) buyurtmalarni ko'radi"""
    tbl_res = await db.execute(select(Table).where(Table.id == table_id))
    tbl = tbl_res.scalar_one_or_none()
    if not tbl or not tbl.is_active:
        raise HTTPException(status_code=404, detail="Stol topilmadi yoki faol emas")

    # Xodim bo'lmasa -> qr_token shu stolning qr_token iga teng bo'lishi shart
    if not current_user:
        if not qr_token or qr_token != tbl.qr_token:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Ushbu stol buyurtmalarini ko'rish uchun yaroqli qr_token talab qilinadi",
            )

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
            ord_resp = sanitize_order_response_for_guest(ord_resp)
        resp_list.append(ord_resp)
    return resp_list



# ─── Buyurtmalar ro'yxati ─────────────────────────────────
@router.get("/", response_model=List[OrderSummary], summary="Buyurtmalar ro'yxati (pagination bilan)")
async def list_orders(
    restaurant_id: Optional[int] = Query(None, description="Restoran ID (faqat developer uchun)"),
    status: Optional[OrderStatus] = None,
    table_id: Optional[int] = None,
    order_type: Optional[str] = None,
    active_only: bool = Query(False),
    ready_for_delivery: bool = Query(False),
    limit: int = Query(default=100, ge=1, le=300, description="Qaytariladigan buyurtmalar soni"),
    offset: int = Query(default=0, ge=0, description="O'tkazib yuboriladigan buyurtmalar soni"),
    include_items: bool = Query(default=False, description="Tarkibidagi taomlar ro'yxatini ham yuklash"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "cashier", "waiter", "chef", "developer")),
):
    current_role = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)
    if current_role == "developer":
        effective_restaurant_id = restaurant_id or current_user.restaurant_id
    else:
        effective_restaurant_id = current_user.restaurant_id or 1

    query = (
        select(Order)
        .options(
            selectinload(Order.table),
            selectinload(Order.waiter),
        )
    )
    if include_items:
        query = query.options(selectinload(Order.items).selectinload(OrderItem.menu_item))

    if effective_restaurant_id is not None:
        query = query.where(Order.restaurant_id == effective_restaurant_id)

    if active_only:
        query = query.where(Order.is_paid == False, Order.status.notin_([OrderStatus.PAID, OrderStatus.CANCELLED]))
    if ready_for_delivery:
        query = query.where(Order.ready_at.is_not(None), Order.served_at.is_(None),
            Order.status != OrderStatus.CANCELLED)
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

    item_counts = {}
    if not include_items and orders:
        order_ids = [o.id for o in orders]
        count_q = (
            select(OrderItem.order_id, func.count(OrderItem.id))
            .where(OrderItem.order_id.in_(order_ids))
            .group_by(OrderItem.order_id)
        )
        count_res = await db.execute(count_q)
        item_counts = dict(count_res.all())

    summaries = []
    for order in orders:
        table_num = order.table.number if order.table else None
        waiter_name = None
        if order.waiter:
            waiter_name = order.waiter.full_name or order.waiter.username

        items_resp = []
        if include_items:
            items_count = len(order.items) if order.items else 0
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
                        menu_item_name=it.name_snapshot or (m_item.name if m_item else None),
                        menu_item_image=m_item.image_url if m_item else None,
                    )
                )
        else:
            items_count = item_counts.get(order.id, 0)

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
    "/stale",
    response_model=List[StaleOrderResponse],
    summary="12 soatdan beri ochiq qolgan buyurtmalar ro'yxati",
)
async def get_stale_orders(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "cashier", "developer")),
):
    """
    12 soatdan beri ochiq (is_paid=False, status != CANCELLED) qolgan buyurtmalar ro'yxati.
    Faqat admin, cashier va developer rollari uchun.
    """
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=12)

    query = (
        select(Order)
        .options(
            selectinload(Order.table),
            selectinload(Order.waiter),
        )
        .where(
            or_(Order.is_paid == False, Order.is_paid.is_(None)),
            Order.status != OrderStatus.CANCELLED,
            Order.created_at <= cutoff,
        )
    )

    if current_user.role != UserRole.DEVELOPER:
        query = query.where(Order.restaurant_id == current_user.restaurant_id)

    query = query.order_by(Order.created_at.asc())
    result = await db.execute(query)
    orders = result.scalars().all()

    stale_list = []
    for o in orders:
        # Stol ma'lumotini aniqlash
        stol_str = None
        if o.table:
            stol_str = str(o.table.number) if o.table.number is not None else (o.table.name or None)
        elif o.table_id:
            stol_str = str(o.table_id)

        # Ofitsiant nomi
        waiter_name = None
        if o.waiter:
            waiter_name = o.waiter.full_name or o.waiter.username

        # Yoshini hisoblash
        if o.created_at:
            created = o.created_at
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            delta = now - created
            total_seconds = max(0, int(delta.total_seconds()))
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            yoshi = f"{hours} soat {minutes} daqiqa"
        else:
            yoshi = "Noma'lum"

        stale_list.append(
            StaleOrderResponse(
                id=o.id,
                order_number=o.order_number,
                stol=stol_str,
                ofitsiant=waiter_name,
                summa=float(o.total or 0.0),
                yoshi=yoshi,
            )
        )

    return stale_list


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
    qr_token: Optional[str] = Query(None),
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

    # Autentifikatsiyasiz mijoz (token yo'q bo'lsa)
    if not current_user:
        # ?qr_token= shu stolning qr_token iga teng bo'lishi shart, aks holda 403
        if not order.table or not order.table.qr_token or not qr_token or qr_token != order.table.qr_token:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Ushbu buyurtmani ko'rish uchun yaroqli qr_token talab qilinadi",
            )

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
        resp = sanitize_order_response_for_guest(resp)
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
    await lock_rows(db, Order, [order_id])
    order = await load_order_full(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Buyurtma topilmadi")

    if order.status == OrderStatus.SERVED or order.served_at is not None:
        raise HTTPException(status_code=400, detail="Bu buyurtma allaqachon yetkazib berilgan")

    if (order.is_paid or order.status == OrderStatus.PAID) and order.ready_at is None:
        raise HTTPException(409, "Oldindan to'langan taomni tayyor bo'lgach yetkazib bering")

    if order.status == OrderStatus.CANCELLED:
        raise HTTPException(status_code=400, detail="Bekor qilingan buyurtmani yetkazib bo'lmaydi")

    now = datetime.now(timezone.utc)
    old_status = order.status
    if not order.is_paid:
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
    await db.commit()

    # 2. Real-time WebSocket: Adminga va xodimlarga
    delivered_event = {
        "type": "order_delivered",
        "order_id": order.id,
        "order_number": order.order_number,
        "table_id": order.table_id,
        "table_number": table_num,
        "waiter_id": current_user.id,
        "waiter_name": waiter_display,
        "status": order.status,
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
    current_user: User = Depends(require_role("admin", "waiter", "chef", "developer", "cashier")),
):
    await lock_rows(db, Order, [order_id])
    if payload.status == OrderStatus.PAID:
        raise HTTPException(
            status_code=400,
            detail="To'lov faqat /checkout orqali qabul qilinadi",
        )

    order = await load_order_full(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Buyurtma topilmadi")

    if order.status in (OrderStatus.PAID, OrderStatus.CANCELLED) or order.is_paid:
        raise HTTPException(
            status_code=400,
            detail=f"Buyurtma allaqachon {order.status.value} holatida, uni o'zgartirib bo'lmaydi",
        )

    user_role = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)
    ALLOWED_STATUSES_BY_ROLE = {
        "chef": {OrderStatus.PREPARING, OrderStatus.READY},
        "waiter": {OrderStatus.CONFIRMED, OrderStatus.SERVED},
        "admin": {OrderStatus.CONFIRMED, OrderStatus.PREPARING, OrderStatus.READY, OrderStatus.SERVED, OrderStatus.CANCELLED},
        "developer": {OrderStatus.CONFIRMED, OrderStatus.PREPARING, OrderStatus.READY, OrderStatus.SERVED, OrderStatus.CANCELLED},
        "cashier": {OrderStatus.CONFIRMED, OrderStatus.PREPARING, OrderStatus.READY, OrderStatus.SERVED, OrderStatus.CANCELLED},
    }
    allowed_for_user = ALLOWED_STATUSES_BY_ROLE.get(user_role, set())
    if payload.status not in allowed_for_user:
        raise HTTPException(
            status_code=403,
            detail=f"Sizning rolingiz ({user_role}) ushbu statusga ({payload.status.value}) o'zgartirish huquqiga ega emas",
        )

    if payload.status == OrderStatus.CANCELLED:
        if any(kitchen_sent_quantity(item) for item in order.items):
            require_kitchen_admin(current_user)
        if not payload.note or len(payload.note.strip()) < 3:
            raise HTTPException(
                status_code=400,
                detail="Buyurtmani bekor qilish uchun sabab (note) kiritilishi shart (kamida 3 belgi)",
            )

    old_status = order.status
    order.status = payload.status
    now = datetime.now(timezone.utc)
    table_num = order.table.number if order.table else order.table_id

    status_broadcast_tasks = []

    # Vaqtlarni yangilash
    if payload.status == OrderStatus.CONFIRMED:
        order.confirmed_at = now
    elif payload.status == OrderStatus.PREPARING:
        order.preparing_at = now
        # Mijoz stoliga xabar (commit'dan keyin yuboriladi)
        status_broadcast_tasks.append(
            lambda: manager.broadcast_to_table(
                order.restaurant_id,
                order.table_id,
                {
                    "type": "order_status",
                    "order_id": order.id,
                    "status": "preparing",
                    "message": "Oshpaz taomingizni tayyorlashni boshladi 👨‍🍳",
                },
            )
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

        # Agar tayinlangan ofitsiant bo'lsa, unga bevosita (commit'dan keyin)
        if order.waiter_id:
            status_broadcast_tasks.append(
                lambda: manager.send_to_user(order.restaurant_id, order.waiter_id, ready_msg)
            )
        # Barcha ofitsiantlar va adminlarga (commit'dan keyin)
        status_broadcast_tasks.append(
            lambda: manager.broadcast_to_roles(order.restaurant_id, ["waiter", "admin"], ready_msg)
        )

        # Mijoz stoliga (commit'dan keyin)
        status_broadcast_tasks.append(
            lambda: manager.broadcast_to_table(
                order.restaurant_id,
                order.table_id,
                {
                    "type": "order_ready",
                    "order_id": order.id,
                    "status": "ready",
                    "message": "Taomingiz tayyor bo'ldi, ofitsiant yo'lda! 🚀",
                },
            )
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
        sent_items = [i for i in (order.items or []) if kitchen_sent_quantity(i) > 0]
        sent_items_count = len(sent_items)

        if sent_items_count > 0:
            set_res = await db.execute(
                select(RestaurantSettings).where(RestaurantSettings.restaurant_id == order.restaurant_id)
            )
            settings = set_res.scalar_one_or_none()
            waiter_name = (order.waiter.full_name or order.waiter.username) if order.waiter else (current_user.full_name or current_user.username)
            for item in sent_items:
                await _send_cancellation_receipt(db, order, item.menu_item, kitchen_sent_quantity(item), waiter_name, settings)

        from app.core.audit import log_audit_event
        await log_audit_event(
            db=db,
            restaurant_id=order.restaurant_id,
            action="order_cancelled",
            user=current_user,
            entity_type="order",
            entity_id=order.id,
            details={
                "order_number": order.order_number,
                "note": payload.note.strip(),
                "sent_items": sent_items_count,
            },
        )

        if order.table_id:
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
    await db.commit()
    wake_printer_worker()

    for task_fn in status_broadcast_tasks:
        await task_fn()

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
    payload: PrepareItemRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("chef", "admin")),
):
    await lock_rows(db, Order, [order_id])
    order = await db.scalar(select(Order).where(Order.id == order_id))
    if not order:
        raise HTTPException(404, "Buyurtma topilmadi")
    if order.status == OrderStatus.CANCELLED:
        raise HTTPException(409, "Yopilgan buyurtmani tayyorlab bo'lmaydi")
    settings = await db.scalar(select(RestaurantSettings).where(RestaurantSettings.restaurant_id == order.restaurant_id))
    if current_user.role == 'chef' and not getattr(settings, 'enable_chef_kds', False):
        raise HTTPException(403, "Oshpaz ekrani admin tomonidan o'chirilgan")
    result = await db.execute(
        select(OrderItem).where(OrderItem.id == item_id, OrderItem.order_id == order_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Element topilmadi")

    if not item.sent_quantity:
        raise HTTPException(409, "Bu taom hali oshxonaga yuborilmagan")
    if payload.expected_sent_quantity is not None and payload.expected_sent_quantity != item.sent_quantity:
        raise HTTPException(409, 'Taom soni o‘zgargan. Oshpaz ekranini yangilang')
    item.prepared_quantity = item.sent_quantity
    item.is_prepared = True
    item.prepared_at = datetime.now(timezone.utc)

    # Buyurtmadagi barcha elementlar tayyormi?
    all_result = await db.execute(
        select(OrderItem).where(OrderItem.order_id == order_id)
    )
    all_items = all_result.scalars().all()

    all_ready = all((i.prepared_quantity or 0) >= i.quantity and (i.sent_quantity or 0) >= i.quantity for i in all_items)
    order_ready_now = False

    if all_ready:
        order_result = await db.execute(
            select(Order)
            .options(selectinload(Order.table), selectinload(Order.waiter))
            .where(Order.id == order_id)
        )
        order = order_result.scalar_one_or_none()
        if order and not order.ready_at and (order.is_paid or order.status in [OrderStatus.PENDING, OrderStatus.CONFIRMED, OrderStatus.PREPARING]):
            if not order.is_paid:
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
    await db.flush()
    await db.commit()

    if order_ready_now:
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

    await db.execute(select(Table.id).where(Table.id == order.table_id).with_for_update())
    resolved_ids = await _finish_table_calls(db, order.restaurant_id, order.table_id)

    await db.flush()
    await db.commit()

    table_num = order.table.number if order.table else order.table_id

    await manager.broadcast_to_roles(
        order.restaurant_id,
        ["waiter", "admin"],
        {
            "type": "call_completed",
            "order_id": order.id,
            "resolved_call_ids": resolved_ids,
            "table_id": order.table_id,
            "table_number": table_num,
            "waiter_name": current_user.full_name or current_user.username,
        },
    )

    return {"success": True, "message": "Chaqiruv yakunlandi"}
