"""
Stollar API — QR kod generatsiya bilan
"""
import os
import time
import uuid
import random
import logging
import qrcode
import aiofiles
from io import BytesIO
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, status, Body, Query, Request
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import List, Optional, Dict, Any

from app.core.database import get_db
from app.core.transactions import lock_rows
from app.core.deposits import set_deposit, record_movement
from app.core.security import require_role, get_optional_current_user
from app.core.config import settings
from app.core.rate_limit import RateLimiter, get_client_ip
from app.models.table import Table, TableStatus, TableZone
from app.models.user import User, UserRole
from app.models.order import Order, OrderItem, OrderStatus, CallStatus
from app.models.restaurant import Restaurant, RestaurantSettings
from app.models.receipt import ReceiptArchive
from app.core.printer_service import (
    format_pre_check, DEFAULT_FONT_SIZE,
    printer_options, receipt_title,
)
from app.core.printer_queue import enqueue_print_job, wake_printer_worker

from app.schemas.table import TableCreate, TableUpdate, TableResponse, TablePublic, TableReserveRequest
from app.schemas.order import TableBillResponse, BillItemSummary
from app.websockets.manager import manager
from app.core.disk_utils import ensure_disk_space
from app.core.audit import log_audit_event
from app.core.idempotency import get_idempotency_handler, IdempotencyHandler
from app.core.table_merge import MergeAccountsRequest, read_merge, merge_accounts

logger = logging.getLogger("tables")

router = APIRouter(prefix="/tables", tags=["🪑 Stollar"])


@router.get('/qr-image/{qr_token}')
async def qr_image(qr_token: str, base_url: str = Query(..., max_length=512), db=Depends(get_db)):
    from urllib.parse import urlparse
    parsed = urlparse(base_url)
    if parsed.scheme not in ('http', 'https') or not parsed.netloc:
        raise HTTPException(422, 'QR uchun http yoki https manzil kiriting')
    table = await db.scalar(select(Table).where(Table.qr_token == qr_token, Table.is_active == True))
    if not table:
        raise HTTPException(404, 'Stol topilmadi')
    output = BytesIO()
    qrcode.make(f'{base_url.rstrip("/")}/?table={qr_token}').save(output, format='PNG')
    output.seek(0)
    return StreamingResponse(output, media_type='image/png', headers={'Cache-Control': 'private, max-age=300'})

def scan_rate_limit_key(request: Request) -> str:
    ip = get_client_ip(request)
    qr_token = request.path_params.get("qr_token", "")
    return f"scan:{ip}:{qr_token}"

def unlock_rate_limit_key(request: Request) -> str:
    ip = get_client_ip(request)
    table_id = request.path_params.get("table_id", "")
    return f"unlock:{ip}:{table_id}"

_cached_qr_base_url: Optional[str] = None
_qr_base_url_cached_at: float = 0.0


def get_qr_base_url() -> str:
    """QR uchun ishlatilgan base URL ni aniqlash (xotirada 60 soniya keshlanadi).
    SERVER_ONLINE_URL.txt mavjud bo'lsa (Cloudflare tunnel aktiv), uni ishlatadi.
    Aks holda settings.QR_BASE_URL ni ishlatadi."""
    global _cached_qr_base_url, _qr_base_url_cached_at
    now = time.time()
    if _cached_qr_base_url and (now - _qr_base_url_cached_at < 60.0):
        return _cached_qr_base_url

    # SERVER_ONLINE_URL.txt ni mumkin bo'lgan yo'llardan qidirish
    possible_paths = [
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "SERVER_ONLINE_URL.txt")),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "SERVER_ONLINE_URL.txt")),
        os.path.abspath("SERVER_ONLINE_URL.txt"),
    ]
    resolved = settings.QR_BASE_URL.rstrip("/")
    for p in possible_paths:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    val = f.read().strip()
                if val.startswith("http"):
                    resolved = val.rstrip("/")
                    break
            except Exception:
                pass

    _cached_qr_base_url = resolved
    _qr_base_url_cached_at = now
    return resolved


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
    ensure_disk_space(required_mb=5, path=upload_dir)
    img.save(file_path)

    return f"/uploads/qr_codes/{file_name}"


def norm_zone(room: Optional[str]) -> Optional[str]:
    """Zona nomini solishtirish uchun tozalash (bo'sh -> None)"""
    v = (room or "").strip()
    return v or None


async def ensure_table_number_free(
    db: AsyncSession, restaurant_id: int, number: int,
    room: Optional[str], exclude_id: Optional[int] = None,
) -> None:
    """Stol raqami SHU ZONADA bandmi — tekshiradi.

    Raqam butun restoran bo'yicha emas, HAR ZONADA alohida yagona
    bo'lishi kerak: "Ko'cha 8" bo'lsa ham "Zal 8" qo'shsa bo'ladi.
    """
    zone = norm_zone(room)
    q = select(Table).where(
        Table.restaurant_id == restaurant_id,
        Table.number == number,
    )
    if exclude_id is not None:
        q = q.where(Table.id != exclude_id)
    res = await db.execute(q)

    for t in res.scalars().all():
        if norm_zone(t.room) == zone:
            joy = f'"{zone}" zonasida' if zone else "zonasiz stollar orasida"
            raise HTTPException(
                status_code=409,
                detail=f"#{number} raqamli stol {joy} allaqachon mavjud. "
                       f"Boshqa raqam tanlang yoki stolni boshqa zonaga qo'shing.",
            )


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
    await ensure_table_number_free(
        db, payload.restaurant_id, payload.number, payload.room
    )

    qr_token = str(uuid.uuid4())
    qr_url = f"{get_qr_base_url()}/?table={qr_token}"
    qr_image_url = generate_qr_image(qr_url, qr_token)

    table = Table(
        restaurant_id=payload.restaurant_id,
        number=payload.number,
        name=payload.name,
        room=norm_zone(payload.room),
        capacity=payload.capacity,
        qr_token=qr_token,
        qr_image_url=qr_image_url,
    )
    db.add(table)
    await db.flush()
    await db.refresh(table)
    return TableResponse.model_validate(table)


# ═══════════════════════════════════════════════════════════════
#  ZONALAR (Stol kategoriyalari): Zal, Terrassa, 2-qavat, VIP
#  DIQQAT: bu yo'llar "/{table_id}" dan OLDIN turishi shart,
#  aks holda "zones" so'zi stol ID deb o'qiladi.
# ═══════════════════════════════════════════════════════════════

class TableZoneCreate(BaseModel):
    restaurant_id: int = 1
    name: str


class TableZoneUpdate(BaseModel):
    name: Optional[str] = None
    sort_order: Optional[int] = None


class TableZoneResponse(BaseModel):
    id: int
    restaurant_id: int
    name: str
    sort_order: int = 0
    tables_count: int = 0

    model_config = {"from_attributes": True}


async def _zone_rows(db: AsyncSession, restaurant_id: int) -> List[TableZoneResponse]:
    """Zonalar ro'yxati + har birida nechta stol borligi"""
    z_res = await db.execute(
        select(TableZone)
        .where(TableZone.restaurant_id == restaurant_id, TableZone.is_active == True)
        .order_by(TableZone.sort_order.asc(), TableZone.id.asc())
    )
    zones = z_res.scalars().all()

    cnt_res = await db.execute(
        select(Table.room, func.count(Table.id))
        .where(Table.restaurant_id == restaurant_id)
        .group_by(Table.room)
    )
    counts = {(r or "").strip(): c for r, c in cnt_res.all()}

    return [
        TableZoneResponse(
            id=z.id,
            restaurant_id=z.restaurant_id,
            name=z.name,
            sort_order=z.sort_order or 0,
            tables_count=counts.get((z.name or "").strip(), 0),
        )
        for z in zones
    ]


@router.get("/zones", response_model=List[TableZoneResponse], summary="Zonalar (stol kategoriyalari) ro'yxati")
async def list_zones(restaurant_id: int = 1, db: AsyncSession = Depends(get_db)):
    """Zonalar ro'yxati.

    Eski stollarda zona nomi faqat matn sifatida saqlangan edi. Shuning
    uchun bu yerda ular bir marta ro'yxatga ham qo'shiladi — shunda admin
    ularni panelda ko'radi va boshqara oladi. Amal takrorlansa ham yangi
    yozuv yaratmaydi.
    """
    existing_res = await db.execute(
        select(TableZone.name).where(TableZone.restaurant_id == restaurant_id)
    )
    existing = {(n or "").strip().lower() for n in existing_res.scalars().all()}

    rooms_res = await db.execute(
        select(Table.room).where(Table.restaurant_id == restaurant_id).distinct()
    )
    added = False
    for room in rooms_res.scalars().all():
        name = (room or "").strip()
        if not name or name.lower() in existing:
            continue
        db.add(TableZone(restaurant_id=restaurant_id, name=name, sort_order=0))
        existing.add(name.lower())
        added = True
    if added:
        await db.flush()

    return await _zone_rows(db, restaurant_id)


@router.post("/zones", response_model=TableZoneResponse, status_code=201, summary="Yangi zona qo'shish")
async def create_zone(
    payload: TableZoneCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "developer")),
):
    name = (payload.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Zona nomi bo'sh bo'lishi mumkin emas")
    if len(name) > 100:
        raise HTTPException(status_code=400, detail="Zona nomi juda uzun (100 belgidan ko'p)")

    dup_res = await db.execute(
        select(TableZone).where(
            TableZone.restaurant_id == payload.restaurant_id,
            func.lower(TableZone.name) == name.lower(),
        )
    )
    if dup_res.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"\"{name}\" nomli zona allaqachon mavjud")

    max_res = await db.execute(
        select(func.max(TableZone.sort_order)).where(TableZone.restaurant_id == payload.restaurant_id)
    )
    next_order = (max_res.scalar() or 0) + 1

    zone = TableZone(restaurant_id=payload.restaurant_id, name=name, sort_order=next_order)
    db.add(zone)
    await db.flush()
    return TableZoneResponse(
        id=zone.id, restaurant_id=zone.restaurant_id, name=zone.name,
        sort_order=zone.sort_order or 0, tables_count=0,
    )


@router.patch("/zones/{zone_id}", response_model=TableZoneResponse, summary="Zona nomini o'zgartirish")
async def update_zone(
    zone_id: int,
    payload: TableZoneUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "developer")),
):
    res = await db.execute(select(TableZone).where(TableZone.id == zone_id))
    zone = res.scalar_one_or_none()
    if not zone:
        raise HTTPException(status_code=404, detail="Zona topilmadi")

    if payload.name is not None:
        new_name = payload.name.strip()
        if not new_name:
            raise HTTPException(status_code=400, detail="Zona nomi bo'sh bo'lishi mumkin emas")
        dup_res = await db.execute(
            select(TableZone).where(
                TableZone.restaurant_id == zone.restaurant_id,
                func.lower(TableZone.name) == new_name.lower(),
                TableZone.id != zone.id,
            )
        )
        if dup_res.scalar_one_or_none():
            raise HTTPException(status_code=400, detail=f"\"{new_name}\" nomli zona allaqachon mavjud")

        old_name = zone.name
        zone.name = new_name
        # Shu zonadagi stollarning nomi ham yangilanadi, aks holda
        # ular zonasiz qolib ketadi.
        if old_name and old_name != new_name:
            t_res = await db.execute(
                select(Table).where(
                    Table.restaurant_id == zone.restaurant_id,
                    Table.room == old_name,
                )
            )
            for t in t_res.scalars().all():
                t.room = new_name

    if payload.sort_order is not None:
        zone.sort_order = payload.sort_order

    await db.flush()
    rows = await _zone_rows(db, zone.restaurant_id)
    for r in rows:
        if r.id == zone.id:
            return r
    return TableZoneResponse(
        id=zone.id, restaurant_id=zone.restaurant_id, name=zone.name,
        sort_order=zone.sort_order or 0, tables_count=0,
    )


@router.delete("/zones/{zone_id}", status_code=204, summary="Zonani o'chirish")
async def delete_zone(
    zone_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "developer")),
):
    res = await db.execute(select(TableZone).where(TableZone.id == zone_id))
    zone = res.scalar_one_or_none()
    if not zone:
        raise HTTPException(status_code=404, detail="Zona topilmadi")

    cnt_res = await db.execute(
        select(func.count(Table.id)).where(
            Table.restaurant_id == zone.restaurant_id,
            Table.room == zone.name,
        )
    )
    used = cnt_res.scalar() or 0
    if used > 0:
        raise HTTPException(
            status_code=400,
            detail=f"\"{zone.name}\" zonasini o'chirib bo'lmaydi: unda {used} ta stol bor. "
                   f"Avval stollarni boshqa zonaga ko'chiring yoki o'chiring.",
        )

    await db.delete(zone)
    await db.flush()
    return None


@router.get("/", response_model=List[TableResponse], summary="Stollar ro'yxati")
async def list_tables(
    restaurant_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "waiter", "developer", "cashier")),
):
    result = await db.execute(
        select(Table)
        .where(Table.restaurant_id == restaurant_id)
        .order_by(Table.number)
    )
    tables = result.scalars().all()
    return [TableResponse.model_validate(t) for t in tables]


@router.get(
    "/scan/{qr_token}",
    response_model=TablePublic,
    summary="QR kodni skanerlash",
    dependencies=[
        Depends(
            RateLimiter(
                times=30,
                seconds=60,
                key_func=scan_rate_limit_key,
                detail="QR skanerlash bo'yicha so'rovlar limiti oshdi. Birozdan so'ng qayta urinib ko'ring.",
            )
        )
    ],
)
async def scan_qr(qr_token: str, db: AsyncSession = Depends(get_db)):
    # Faqat noyob UUID qr_token bo'yicha qidirish (raqam bilan skan qilish xavfsizlik sababli o'chirildi)
    result = await db.execute(
        select(Table).where(Table.qr_token == qr_token, Table.is_active == True)
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
                "message": f"🔔 Stol #{table.number} ga yangi mijoz keldi! Tasdiqlash kodi: {table.current_pin}",
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
    # PIN mijozga qaytarilmaydi — faqat ofitsiant POS / WebSocket orqali ko'radi
    res.pin = None
    res.current_pin = None
    res.is_unlocked = bool(table.is_unlocked)
    return res


@router.post(
    "/{table_id}/unlock",
    summary="Ofitsiant tomonidan stolni tasdiqlash / faollashtirish",
    dependencies=[
        Depends(
            RateLimiter(
                times=20,
                seconds=60,
                key_func=unlock_rate_limit_key,
                detail="Stolni ochish bo'yicha so'rovlar limiti oshdi. Birozdan so'ng qayta urinib ko'ring.",
            )
        )
    ],
)
async def unlock_table(
    table_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("waiter", "admin", "cashier", "developer")),
):
    """Ofitsiant stolga borib kodni ko'rib stolni faollashtiradi"""
    result = await db.execute(select(Table).where(Table.id == table_id))
    table = result.scalar_one_or_none()
    if not table:
        raise HTTPException(status_code=404, detail="Stol topilmadi")

    # Stol va foydalanuvchi restorani mos bo'lsin (developer istisno)
    user_role = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)
    if user_role != "developer" and table.restaurant_id != current_user.restaurant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Boshqa restoranning stolini ochishga ruxsat yo'q",
        )

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
async def get_table_bill(
    table_id: int,
    qr_token: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """Mijoz, Ofitsiant yoki Admin stol hisobi va chekini ko'radi"""
    result = await db.execute(
        select(Table)
        .options(selectinload(Table.restaurant))
        .where(Table.id == table_id)
    )
    table = result.scalar_one_or_none()
    if not table:
        raise HTTPException(status_code=404, detail="Stol topilmadi")

    # Xodim bo'lmasa -> ?qr_token= shu stolning qr_token iga teng bo'lishi shart
    if not current_user:
        if not qr_token or qr_token != table.qr_token:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Ushbu stol hisobini ko'rish uchun yaroqli qr_token talab qilinadi",
            )

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

    # Agar to'lanmagan faol buyurtma bo'lmasa, so'nggi sessiya buyurtmalarini
    # ko'rsatamiz — LEKIN faqat stol hali bo'shatilmagan bo'lsa.
    #
    # Stol bo'shatilgandan keyin hisob BO'SH bo'lishi kerak. Aks holda
    # "To'landi & Stolni Bo'shatish" bosilgandan keyin ham yopilgan chek
    # ekranda qolib ketadi (va uni qayta-qayta to'lash mumkin bo'lib qoladi).
    session_open = table.status != TableStatus.AVAILABLE
    if not orders and session_open:
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
    # "Faol hisob" = kamida bitta to'lanmagan buyurtma. To'langan buyurtma
    # faqat ko'rish (arxiv) uchun qaytariladi, u stolni band qilmaydi.
    has_open_bill = any(not o.is_paid for o in orders)

    for o in orders:
        order_numbers.append(o.order_number)
        if o.waiter:
            waiter_names.add(o.waiter.full_name or o.waiter.username)
        if not earliest_time or (o.created_at and o.created_at < earliest_time):
            earliest_time = o.created_at

        for item in o.items:
            m_id = item.menu_item_id
            name = item.name_snapshot or (item.menu_item.name if item.menu_item else f"Taom #{m_id}")
            size = (item.portion_size or "").strip() or None
            wt = item.weight if (item.weight and item.weight > 0) else None
            unit = (getattr(item.menu_item, "unit", None) or "dona") if item.menu_item else "dona"
            weighed = bool(getattr(item.menu_item, "is_weighted", False)) if item.menu_item else False
            # Hajmi har xil bo'lgan taomlar (1 L va 1.5 L kola) alohida
            # qatorda turadi. Tortiladigan taom esa HECH QACHON
            # birlashtirilmaydi — har bir baliqning o'z og'irligi bor va
            # kassir uni alohida tuzata olishi kerak.
            key = ("w", item.id) if weighed else (m_id, name, size, wt)
            if key not in items_map:
                items_map[key] = {
                    "menu_item_id": m_id,
                    "name": name,
                    "portion_size": size,
                    "weight": wt,
                    "manual_price": item.manual_price,
                    "unit": unit,
                    "is_weighted": weighed,
                    "order_id": o.id,
                    "order_item_id": item.id,
                    # Bir xil taom bir nechta qatorda bo'lishi mumkin
                    # (2 marta alohida buyurtma qilingan). Mijoz taomni
                    # qaytarsa qaysi qatordan olib tashlashni bilish uchun
                    # HAMMA qator raqamlari saqlanadi.
                    "order_item_ids": [],
                    "quantity": 0,
                    "unit_price": item.unit_price,
                    "total_price": 0.0,
                    "special_notes": [],
                }
            items_map[key]["order_item_ids"].append(item.id)
            items_map[key]["quantity"] += item.quantity
            items_map[key]["total_price"] += item.total_price
            if item.special_note:
                items_map[key]["special_notes"].append(item.special_note)
            subtotal += item.total_price

    # Xizmat haqi foizi buyurtmaning o'zidan olinadi. Ilgari bu yerda 10%
    # qattiq yozilgan edi: ofitsiant panelida 12%, chekda 10% chiqib,
    # ikki xil summa ko'rinardi (masalan 705 600 va 693 000).
    fee_candidates = [o.service_fee_percent for o in orders if o.service_fee_percent is not None]
    if fee_candidates:
        service_fee_percent = fee_candidates[0]
    else:
        set_res = await db.execute(
            select(RestaurantSettings).where(RestaurantSettings.restaurant_id == table.restaurant_id)
        )
        rsettings = set_res.scalar_one_or_none()
        # 0% ham haqiqiy qiymat — `or 12.0` yozilsa restoran xizmat
        # haqini butunlay o'chirganda ham 12% chiqib ketardi.
        cfg = rsettings.service_fee_percent if rsettings else None
        service_fee_percent = 12.0 if cfg is None else float(cfg)

    service_fee_amount = round(sum(round(sum(i.total_price or 0 for i in o.items) *
        ((o.service_fee_percent if o.service_fee_percent is not None else service_fee_percent) / 100), 2) for o in orders), 2)
    discount = sum(o.discount or 0 for o in orders)
    grand_total = round(subtotal + service_fee_amount - discount, 2)
    advance = (table.deposit_amount or 0) if has_open_bill else sum(o.advance_amount or 0 for o in orders)

    restaurant = table.restaurant
    restaurant_name = restaurant.name if restaurant else "Dunyo Choyxonasi"
    restaurant_phone = restaurant.phone if restaurant else "+998884593400"
    restaurant_address = restaurant.address if restaurant else "Xorazm viloyati, Xiva tumani"

    items_list = [BillItemSummary(**v) for v in items_map.values()]
    # Mehmon (xodimsiz) ko'rinishidan ichki id lar olib tashlansin
    if not current_user:
        for it in items_list:
            it.order_id = None
            it.order_item_id = None
            it.order_item_ids = []

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
        discount=discount,
        grand_total=grand_total,
        advance_amount=advance,
        amount_due=max(0, grand_total - advance),
        has_active_orders=has_open_bill,
        is_paid=is_all_paid,
        created_at=earliest_time or table.created_at,
    )


async def open_orders_count(db: AsyncSession, table_id: int) -> int:
    """Ochiq (is_paid=False, status CANCELLED/PAID emas) buyurtmalar soni"""
    res = await db.execute(
        select(func.count(Order.id)).where(
            Order.table_id == table_id,
            Order.is_paid == False,
            Order.status.notin_([OrderStatus.PAID, OrderStatus.CANCELLED]),
        )
    )
    return res.scalar() or 0


async def get_open_orders(db: AsyncSession, table_id: int) -> List[Order]:
    """Ochiq (is_paid=False, status CANCELLED/PAID emas) buyurtmalar ro'yxati"""
    res = await db.execute(
        select(Order).where(
            Order.table_id == table_id,
            Order.is_paid == False,
            Order.status.notin_([OrderStatus.PAID, OrderStatus.CANCELLED]),
        )
    )
    return res.scalars().all()


class TableCheckoutRequest(BaseModel):
    """Stolni yopishda to'lov turi (ko'rsatilmasa — naqd)"""
    payment_method: str = "cash"


@router.post("/{table_id}/checkout", response_model=TableResponse, summary="Stolni hisob-kitob qilish va bo'shatish")
async def checkout_table(
    table_id: int,
    payload: Optional[TableCheckoutRequest] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "cashier", "developer")),
):
    from app.routers.orders import checkout_order
    from app.schemas.order import OrderCheckoutRequest
    from app.core.idempotency import IdempotencyHandler
    await lock_rows(db, Table, [table_id])
    table = await db.scalar(select(Table).where(Table.id == table_id))
    if not table:
        raise HTTPException(404, 'Stol topilmadi')
    active_orders = await get_open_orders(db, table_id)
    if not active_orders:
        raise HTTPException(409, "Stolda yopiladigan ochiq hisob yo'q")
    if len(active_orders) != 1:
        raise HTTPException(409, "Stolda bir nechta eski hisob bor; kassa oynasida har birini alohida yoping")
    method = (payload.payment_method if payload else 'cash') or 'cash'
    await checkout_order(active_orders[0].id, OrderCheckoutRequest(payment_method=method),
                         db, current_user, IdempotencyHandler(None, '', db))
    await db.refresh(table)
    return TableResponse.model_validate(table)


class RemoveBillItemsRequest(BaseModel):
    """Hisobdan taomni olib tashlash (mijoz qaytarib berdi)"""
    order_item_ids: List[int] = Field(..., min_length=1)
    quantity: Optional[int] = Field(default=None, ge=1)


@router.post("/{table_id}/remove-items", summary="Hisobdan taomni olib tashlash (qaytarilgan taom)")
async def remove_bill_items(
    table_id: int,
    payload: RemoveBillItemsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "developer")),
):
    """Mijoz taomni qaytarib bersa — uni hisobdan olib tashlash.

    `quantity` berilmasa qator butunlay o'chiriladi. Berilsa shuncha
    dona olib tashlanadi (masalan 3 somsadan 1 tasi qaytarildi).

    Bir xil taom bir nechta buyurtma qatorida bo'lishi mumkin, shuning
    uchun `order_item_ids` ro'yxati yuboriladi va kerakli soni
    oxirgisidan boshlab ayriladi.
    """
    await lock_rows(db, Table, [table_id])
    res = await db.execute(select(Table).where(Table.id == table_id))
    table = res.scalar_one_or_none()
    if not table:
        raise HTTPException(status_code=404, detail="Stol topilmadi")

    items_res = await db.execute(
        select(OrderItem)
        .options(selectinload(OrderItem.menu_item))
        .join(Order, Order.id == OrderItem.order_id)
        .where(
            OrderItem.id.in_(payload.order_item_ids),
            Order.table_id == table_id,
            Order.is_paid == False,
        )
        .order_by(OrderItem.id.desc())
    )
    items = items_res.scalars().all()
    if not items:
        raise HTTPException(
            status_code=404,
            detail="Taom topilmadi — hisob allaqachon yopilgan bo'lishi mumkin.",
        )

    available = sum((i.quantity or 0) for i in items)
    to_remove = payload.quantity if payload.quantity is not None else available
    if to_remove > available:
        raise HTTPException(
            status_code=400,
            detail=f"Hisobda bu taomdan {available} ta bor — {to_remove} tasini olib bo'lmaydi.",
        )

    from app.routers.orders import _send_cancellation_receipt, load_order_full
    rsettings = await db.scalar(select(RestaurantSettings).where(RestaurantSettings.restaurant_id == table.restaurant_id))
    removed_name = items[0].name_snapshot or (items[0].menu_item.name if items[0].menu_item else "Taom")
    removed = 0
    touched_orders = set()

    for it in items:
        if removed >= to_remove:
            break
        touched_orders.add(it.order_id)
        qty = it.quantity or 0
        take = min(qty, to_remove - removed)
        removed += take
        cancelled_qty = max(0, min(it.sent_quantity or 0, qty) - (qty - take))
        if cancelled_qty:
            full_order = await load_order_full(db, it.order_id)
            await _send_cancellation_receipt(db, full_order, it.menu_item, cancelled_qty,
                current_user.full_name or current_user.username, rsettings)
            await log_audit_event(db=db, restaurant_id=table.restaurant_id, action='remove_kitchen_bill_item',
                user=current_user, entity_type='order_item', entity_id=it.id,
                details={'order_id':it.order_id,'cancelled_qty':cancelled_qty,'name':it.name_snapshot})
        if take >= qty:
            full_order = await load_order_full(db, it.order_id)
            full_order.items = [row for row in full_order.items if row.id != it.id]
            await db.delete(it)
        else:
            it.quantity = qty - take
            it.prepared_quantity = min(it.prepared_quantity or 0, it.quantity)
            # Oshxonaga yuborilgan son ham kamayishi kerak, aks holda
            # qolgan qism keyin "yangi" bo'lib begunokdan qayta chiqadi.
            it.sent_quantity = min(it.sent_quantity or 0, it.quantity)
            mi = it.menu_item
            if it.manual_price is not None:
                # Qo'lda yozilgan summa — bu aniq shu baliqning puli,
                # soniga bog'liq emas, o'zgarmaydi.
                it.total_price = round(float(it.manual_price), 2)
            elif mi and getattr(mi, "is_weighted", False) and it.weight:
                it.total_price = round(
                    (it.unit_price or 0.0) * float(it.weight) * max(1, it.quantity), 2)
            else:
                it.total_price = round((it.unit_price or 0.0) * it.quantity, 2)

    await db.flush()

    # Tegilgan buyurtmalarning summalarini qayta hisoblaymiz
    ord_res = await db.execute(
        select(Order).options(selectinload(Order.items)).where(Order.id.in_(touched_orders)).execution_options(populate_existing=True)
    )
    orders = ord_res.scalars().all()
    set_res = await db.execute(
        select(RestaurantSettings).where(RestaurantSettings.restaurant_id == table.restaurant_id)
    )
    rsettings = set_res.scalar_one_or_none()
    _cfg = getattr(rsettings, "service_fee_percent", None)
    cfg_fee = 12.0 if _cfg is None else float(_cfg)

    for o in orders:
        subtotal = sum((i.total_price or 0.0) for i in o.items)
        pct = o.service_fee_percent if o.service_fee_percent is not None else cfg_fee
        o.subtotal = round(subtotal, 2)
        o.service_fee_percent = pct
        o.service_fee_amount = round(subtotal * (float(pct) / 100.0), 2)
        o.total = round(max(0.0, subtotal + o.service_fee_amount - (o.discount or 0.0)), 2)
        if not o.items:
            o.status = OrderStatus.CANCELLED

    remaining = await db.scalar(select(func.count(Order.id)).where(Order.table_id == table_id,
        Order.is_paid == False, Order.status.notin_([OrderStatus.PAID, OrderStatus.CANCELLED])))
    if not remaining:
        table.status = TableStatus.RESERVED if table.deposit_amount else TableStatus.AVAILABLE
        table.is_occupied = False

    await db.flush()
    await db.commit()
    wake_printer_worker()

    await manager.broadcast_to_restaurant(table.restaurant_id, {
        "type": "order_updated",
        "table_id": table_id,
        "table_number": table.number,
        "removed_item": removed_name,
        "removed_quantity": removed,
    })

    return {
        "success": True,
        "removed_name": removed_name,
        "removed_quantity": removed,
        "message": f"{removed_name} — {removed} ta hisobdan olib tashlandi.",
    }


class TableServiceFeeRequest(BaseModel):
    """Shu stol hisobidagi xizmat haqi foizini o'zgartirish"""
    percent: float = Field(..., ge=0, le=100)


@router.patch("/{table_id}/service-fee", summary="Stol hisobidagi xizmat haqi foizini o'zgartirish")
async def set_table_service_fee(
    table_id: int,
    payload: TableServiceFeeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "cashier", "developer")),
):
    """Shu stolning OCHIQ hisobiga boshqa xizmat haqi foizini qo'yish.

    Har stol uchun har xil foiz kerak bo'ladi (masalan VIP xonaga 15%,
    ko'chaga 0%). Sukut bo'yicha sozlamalardagi foiz (12%) ishlatiladi —
    kassir hech narsa qilmasa shu qoladi. O'zgartirsa esa shu stolning
    hisobida ham, chekda ham aynan shu foiz chiqadi.

    Restoranning umumiy sozlamasiga TEGILMAYDI: boshqa stollar
    avvalgidek ishlayveradi.
    """
    await lock_rows(db, Table, [table_id])
    res = await db.execute(select(Table).where(Table.id == table_id))
    table = res.scalar_one_or_none()
    if not table:
        raise HTTPException(status_code=404, detail="Stol topilmadi")

    current_role = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)
    if current_role != "developer" and current_user.restaurant_id and table.restaurant_id != current_user.restaurant_id:
        raise HTTPException(status_code=403, detail="Bu stol sizning restoraningizga tegishli emas")

    orders_res = await db.execute(
        select(Order)
        .options(selectinload(Order.items))
        .where(
            Order.table_id == table_id,
            Order.is_paid == False,
            Order.status.notin_([OrderStatus.CANCELLED, OrderStatus.PAID]),
        )
    )
    orders = orders_res.scalars().all()
    if not orders:
        raise HTTPException(
            status_code=400,
            detail=f"Stol #{table.number} da ochiq hisob yo'q — foizni o'zgartirib bo'lmaydi.",
        )

    old_percent = orders[0].service_fee_percent if orders else None
    pct = round(float(payload.percent), 2)
    from app.core.money import money_sum, percent
    for o in orders:
        subtotal = sum((i.total_price or 0.0) for i in o.items)
        o.service_fee_percent = pct
        o.subtotal = round(subtotal, 2)
        o.service_fee_amount = percent(o.subtotal, pct)
        o.total = money_sum([o.subtotal, o.service_fee_amount, -(o.discount or 0)])

    await db.flush()

    await log_audit_event(
        db=db,
        restaurant_id=table.restaurant_id,
        action="service_fee_changed",
        user=current_user,
        entity_type="table",
        entity_id=table.id,
        details={
            "table_number": table.number,
            "old_percent": old_percent,
            "new_percent": pct,
            "orders_count": len(orders),
        },
    )

    await db.commit()

    total = round(sum((o.total or 0.0) for o in orders), 2)
    await manager.broadcast_to_restaurant(table.restaurant_id, {
        "type": "order_updated",
        "table_id": table_id,
        "table_number": table.number,
        "service_fee_percent": pct,
        "total": total,
    })

    return {
        "success": True,
        "table_id": table_id,
        "service_fee_percent": pct,
        "orders_updated": len(orders),
        "total": total,
    }


@router.post("/{table_id}/print-bill", summary="Stol hisob chekini Printer 1 ga chop etish (Kassa / Mijoz)")
async def print_table_bill(
    table_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("waiter", "admin", "developer", "cashier")),
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
    cust_printer = (getattr(settings, "printer_customer_name", None) or "").strip()
    if not cust_printer:
        raise HTTPException(
            status_code=400,
            detail="Printer sozlanmagan: Mijoz kassa cheki (printer_customer_name)",
        )
    paper_width = getattr(settings, "printer_paper_width", 80) or 80
    popts = printer_options(settings)
    cp = popts["codepage"]
    fsize = popts["font_size"]

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

    # Tortiladigan taom tortilmagan bo'lsa chek chiqarilmaydi — aks holda
    # chekda "1 kg" yozilib, aslida 1.35 kg berilgan bo'lib chiqadi.
    not_weighed = []
    for o in orders:
        if o.is_paid:
            continue
        for it in o.items:
            mi = it.menu_item
            priced = (it.manual_price is not None and it.manual_price >= 0) or \
                     bool(it.weight and it.weight > 0)
            if mi and getattr(mi, "is_weighted", False) and not priced:
                not_weighed.append(mi.name)
    if not_weighed:
        raise HTTPException(
            status_code=400,
            detail="Chek chiqarib bo'lmaydi: " + ", ".join(sorted(set(not_weighed))) +
                   " narxi kiritilmagan. Ofitsiant panelida summasini yozing.",
        )

    active_orders = [o for o in orders if not o.is_paid]
    if active_orders:
        target_orders = active_orders
    elif table.status != TableStatus.AVAILABLE:
        # Stol hali band — to'langan chekning nusxasini chiqarishga ruxsat
        target_orders = [orders[0]]
    else:
        # Stol bo'shatilgan: yopilgan chekni qayta chiqarish kassada
        # chalkashlik va ikki marta to'lovga olib keladi.
        raise HTTPException(
            status_code=400,
            detail=f"Stol #{table.number} da ochiq hisob yo'q — stol allaqachon "
                   f"bo'shatilgan. Eski cheklarni 'Cheklar arxivi' bo'limidan ko'rish mumkin.",
        )

    items_for_receipt = []
    subtotal = 0.0
    waiter_names = set()
    order_nums = []

    for ord in target_orders:
        order_nums.append(ord.order_number)
        if ord.waiter:
            waiter_names.add(ord.waiter.full_name or ord.waiter.username)
        for it in ord.items:
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

    # Xizmat haqi foizi BUYURTMADAN olinadi. Kassir shu stol uchun
    # foizni o'zgartirgan bo'lsa (masalan VIP xonaga 15%), chekda ham
    # aynan shu foiz chiqishi kerak — aks holda ekranda bir summa,
    # qog'ozda boshqa summa bo'lib qoladi.
    fee_candidates = [o.service_fee_percent for o in target_orders
                      if o.service_fee_percent is not None]
    _cfg = getattr(settings, "service_fee_percent", None)
    fee_pct = fee_candidates[0] if fee_candidates else (12.0 if _cfg is None else float(_cfg))
    fee_amount = round(subtotal * (fee_pct / 100.0), 2)
    grand_total = subtotal + fee_amount
    rest_name = receipt_title(settings, table.restaurant)
    table_disp = f"{table.room or 'Zal'} N#{table.number}".strip()
    waiter_disp = ", ".join(waiter_names) if waiter_names else (current_user.full_name or current_user.username)

    bill_text = format_pre_check(
        restaurant_name=rest_name,
        # Chek sozlamasida bo'sh bo'lsa — restoran ma'lumotidan olamiz.
        address=(getattr(settings, "receipt_address", None) if settings else None)
                or (table.restaurant.address if table.restaurant else None),
        phone=(getattr(settings, "receipt_phone", None) if settings else None)
              or (table.restaurant.phone if table.restaurant else None),
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
        font_size=fsize,
        char_spacing=popts["char_spacing"],
    )

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

    target_order_id = target_orders[0].id if target_orders else None
    job = await enqueue_print_job(
        db,
        restaurant_id=table.restaurant_id,
        order_id=target_order_id,
        ticket_type="bill",
        printer_name=cust_printer,
        raw_text=bill_text,
        options=popts,
    )
    await db.commit()
    wake_printer_worker()

    return {
        "success": True,
        "job_id": job.id,
        "status": "queued",
        "printed": False,
        "queued": True,
        "printer_name": cust_printer,
        "message": f"Chek {cust_printer} printeri navbatiga qo'shildi",
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
    await lock_rows(db, Table, [table_id])
    result = await db.execute(select(Table).where(Table.id == table_id))
    table = result.scalar_one_or_none()
    if not table:
        raise HTTPException(status_code=404, detail="Stol topilmadi")

    data = payload.model_dump(exclude_unset=True)
    if any(data.get(field, True) is None for field in ('number', 'capacity', 'is_active', 'status')):
        raise HTTPException(422, "Stol raqami, sig'imi va holati bo'sh bo'lishi mumkin emas")
    if await open_orders_count(db, table.id):
        if data.get('is_active') is False or ('status' in data and data['status'] != TableStatus.OCCUPIED):
            raise HTTPException(409, "Ochiq hisob bor stolni yashirish yoki bo'shatish mumkin emas")
    if data.get('is_active') is False and (table.deposit_amount or 0) > 0:
        raise HTTPException(409, "Avansi bor stolni yashirish mumkin emas")
    if "room" in data:
        data["room"] = norm_zone(data["room"])

    # Raqam yoki zona o'zgarsa — yangi joyda bo'sh ekanini tekshiramiz
    if "number" in data or "room" in data:
        await ensure_table_number_free(
            db,
            table.restaurant_id,
            data.get("number", table.number),
            data.get("room", table.room),
            exclude_id=table.id,
        )

    if 'deposit_amount' in data:
        await set_deposit(db, table, current_user, data.pop('deposit_amount'))
    for field, value in data.items():
        setattr(table, field, value)

    await db.flush()
    await db.refresh(table)
    return TableResponse.model_validate(table)


@router.post("/{table_id}/reserve", response_model=TableResponse, summary="Stolni bron qilish (Zakalat/Avans bilan)")
async def reserve_table(
    table_id: int,
    payload: TableReserveRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("waiter", "admin", "developer", "cashier")),
):
    """Stolni bron qilish va mijoz ma'lumotlari hamda zakalat summasini saqlash"""
    await lock_rows(db, Table, [table_id])
    result = await db.execute(select(Table).where(Table.id == table_id))
    table = result.scalar_one_or_none()
    if not table:
        raise HTTPException(status_code=404, detail="Stol topilmadi")

    if await open_orders_count(db, table.id):
        raise HTTPException(409, "Ochiq hisob bor stolni bron qilib bo'lmaydi")
    await set_deposit(db, table, current_user, float(payload.deposit_amount or 0))
    table.status = TableStatus.RESERVED
    c_name = payload.reserved_by_name or payload.name
    table.reserved_by_name = c_name.strip() if c_name else None
    c_phone = payload.reserved_by_phone or payload.phone
    table.reserved_by_phone = c_phone.strip() if c_phone else None
    c_time = payload.reserved_time or payload.time
    table.reserved_time = c_time.strip() if c_time else None
    table.reserved_guests = payload.reserved_guests if payload.reserved_guests is not None else payload.guests
    c_note = payload.reservation_note or payload.note
    table.reservation_note = c_note.strip() if c_note else None

    await db.flush()
    await db.commit()

    await manager.broadcast_to_restaurant(
        table.restaurant_id,
        {
            "type": "table_status_updated",
            "table_id": table.id,
            "table_number": table.number,
            "status": TableStatus.RESERVED.value,
            "new_status": TableStatus.RESERVED.value,
            "reserved_time": table.reserved_time,
            "deposit_amount": table.deposit_amount,
            "reserved_by_name": table.reserved_by_name,
            "reserved_by_phone": table.reserved_by_phone,
        },
    )
    return TableResponse.model_validate(table)


@router.patch("/{table_id}/status", response_model=TableResponse, summary="Stol holatini o'zgartirish")
async def update_table_status(
    table_id: int,
    table_status: Optional[str] = Query(None),
    payload: Optional[Dict[str, Any]] = Body(None),
    force: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("waiter", "admin", "developer", "cashier")),
):
    """Ofitsiant yoki Admin stol holatini (available, occupied, reserved) o'zgartiradi"""
    await lock_rows(db, Table, [table_id])
    result = await db.execute(select(Table).where(Table.id == table_id))
    table = result.scalar_one_or_none()
    if not table:
        raise HTTPException(status_code=404, detail="Stol topilmadi")

    raw_status = None
    if payload and isinstance(payload, dict):
        raw_status = payload.get("status") or payload.get("table_status")
    if not raw_status and table_status:
        raw_status = table_status

    if not raw_status or not str(raw_status).strip():
        raise HTTPException(status_code=400, detail="Stol statusi ko'rsatilmadi")

    status_str = str(raw_status).lower().strip()
    try:
        new_enum_status = TableStatus(status_str)
    except ValueError:
        valid_statuses = [s.value for s in TableStatus]
        raise HTTPException(
            status_code=400,
            detail=f"Noto'g'ri status: '{raw_status}'. Ruxsat etilgan statuslar: {valid_statuses}",
        )

    if new_enum_status == TableStatus.AVAILABLE:
        open_count = await open_orders_count(db, table.id)
        if open_count > 0:
            user_role_str = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)
            if force and user_role_str in ("admin", "developer"):
                open_orders = await get_open_orders(db, table.id)
                await log_audit_event(
                    db=db,
                    restaurant_id=table.restaurant_id,
                    action="table_force_cleared",
                    user=current_user,
                    entity_type="table",
                    entity_id=table.id,
                    details={
                        "table_number": table.number,
                        "source": "update_table_status",
                        "order_numbers": [o.order_number for o in open_orders],
                        "open_orders_count": open_count,
                    },
                )
            else:
                raise HTTPException(status_code=409, detail="Stolda ochiq hisob bor")

    old_status = table.status.value if hasattr(table.status, "value") else str(table.status)
    table.status = new_enum_status

    if new_enum_status == TableStatus.AVAILABLE:
        if table.deposit_amount:
            raise HTTPException(409, "Avansni hisobga o'tkazing yoki bron oynasida qaytaring")
        table.reserved_by_name = None
        table.reserved_by_phone = None
        table.reserved_time = None
        table.reserved_guests = None
        table.deposit_amount = 0.0
        table.reservation_note = None
        table.current_pin = None
        table.is_unlocked = False

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


@router.get('/{from_table_id}/merge-preview/{to_table_id}')
async def preview_table_merge(from_table_id: int, to_table_id: int, db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role('waiter', 'admin', 'developer', 'cashier'))):
    return (await read_merge(db, from_table_id, to_table_id, user))[-1]


@router.post('/{from_table_id}/merge/{to_table_id}')
async def merge_table_accounts(from_table_id: int, to_table_id: int, payload: MergeAccountsRequest,
    db: AsyncSession = Depends(get_db), user: User = Depends(require_role('waiter', 'admin', 'developer', 'cashier')),
    idempotency: IdempotencyHandler = Depends(get_idempotency_handler)):
    return await merge_accounts(db, from_table_id, to_table_id, payload, user, idempotency)


@router.post("/{from_table_id}/transfer/{to_table_id}", summary="Stolni boshqa stolga ko'chirish (Transfer)")
async def transfer_table(
    from_table_id: int,
    to_table_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("waiter", "admin", "developer", "cashier")),
):
    """Buyurtmalarni boshqa stolga ko'chirish va stollar holatini sinxronlash"""
    await lock_rows(db, Table, [from_table_id, to_table_id])
    if from_table_id == to_table_id:
        raise HTTPException(
            status_code=400,
            detail="Boshlang'ich va maqsad stol bir xil bo'lishi mumkin emas",
        )

    from_res = await db.execute(select(Table).where(Table.id == from_table_id))
    from_table = from_res.scalar_one_or_none()
    to_res = await db.execute(select(Table).where(Table.id == to_table_id))
    to_table = to_res.scalar_one_or_none()

    if not from_table or not to_table:
        raise HTTPException(status_code=404, detail="Stol topilmadi")

    if from_table.restaurant_id != to_table.restaurant_id:
        raise HTTPException(403, "Boshqa restoranga ko'chirib bo'lmaydi")
    if to_table.deposit_amount or to_table.status == TableStatus.RESERVED:
        raise HTTPException(409, "Maqsad stol bron qilingan; bo'sh stol tanlang")
    to_open_count = await open_orders_count(db, to_table_id)
    if to_open_count > 0:
        raise HTTPException(
            status_code=409,
            detail=f"Maqsad stol #{to_table.number} da ochiq buyurtmalar mavjud. Bo'sh stolni tanlang",
        )

    active_orders = await get_open_orders(db, from_table_id)
    if not active_orders:
        raise HTTPException(
            status_code=409,
            detail=f"Stol #{from_table.number} da ko'chiriladigan ochiq buyurtma topilmadi",
        )

    for ord in active_orders:
        ord.table_id = to_table.id
        ord.hall_name = to_table.room or f"Zal #{to_table.number}"

    # Eski stolni bo'shatamiz, yangi stolni band qilamiz
    from_table.status = TableStatus.AVAILABLE
    from_table.is_unlocked = False
    from_table.current_pin = None

    to_table.status = TableStatus.OCCUPIED

    # Zakalat bo'lsa yangi stolga o'tkazish
    if (from_table.deposit_amount or 0.0) > 0:
        amount = from_table.deposit_amount
        await record_movement(db, from_table, current_user, -amount, 'transfer_out')
        await record_movement(db, to_table, current_user, amount, 'transfer_in')
        to_table.deposit_amount = (to_table.deposit_amount or 0.0) + (from_table.deposit_amount or 0.0)
        to_table.reserved_by_name = to_table.reserved_by_name or from_table.reserved_by_name
        to_table.reserved_by_phone = to_table.reserved_by_phone or from_table.reserved_by_phone
        to_table.reserved_time = to_table.reserved_time or from_table.reserved_time
        to_table.reservation_note = to_table.reservation_note or from_table.reservation_note

    from_table.reserved_by_name = None
    from_table.reserved_by_phone = None
    from_table.reserved_time = None
    from_table.reserved_guests = None
    from_table.deposit_amount = 0.0
    from_table.reservation_note = None

    await log_audit_event(
        db=db,
        restaurant_id=from_table.restaurant_id,
        action="table_transfer",
        user=current_user,
        entity_type="table",
        entity_id=from_table.id,
        details={
            "from_table_id": from_table.id,
            "from_table_number": from_table.number,
            "to_table_id": to_table.id,
            "to_table_number": to_table.number,
            "transferred_orders_count": len(active_orders),
            "order_numbers": [o.order_number for o in active_orders],
        },
    )

    await db.flush()
    await db.commit()

    # WebSocket orqali stollar va buyurtmalar yangilanganini e'lon qilish
    await manager.broadcast_to_restaurant(
        from_table.restaurant_id,
        {
            "type": "table_status_updated",
            "table_id": from_table.id,
            "table_number": from_table.number,
            "status": TableStatus.AVAILABLE.value,
            "new_status": TableStatus.AVAILABLE.value,
        },
    )
    await manager.broadcast_to_restaurant(
        to_table.restaurant_id,
        {
            "type": "table_status_updated",
            "table_id": to_table.id,
            "table_number": to_table.number,
            "status": TableStatus.OCCUPIED.value,
            "new_status": TableStatus.OCCUPIED.value,
            "deposit_amount": to_table.deposit_amount,
        },
    )
    for ord in active_orders:
        await manager.broadcast_to_restaurant(
            to_table.restaurant_id,
            {
                "type": "order_updated",
                "order_id": ord.id,
                "order_number": ord.order_number,
                "table_id": to_table.id,
                "table_number": to_table.number,
            },
        )

    return {
        "success": True,
        "message": f"Buyurtmalar Stol #{from_table.number} dan Stol #{to_table.number} ga muvaffaqiyatli ko'chirildi",
        "transferred_orders_count": len(active_orders),
    }


@router.post("/{table_id}/clear", response_model=TableResponse, summary="Stolni tozalash / bo'shatish")
async def clear_table(
    table_id: int,
    force: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("waiter", "admin", "developer", "cashier")),
):
    """Mijoz ketganidan keyin stolni bo'sh deb belgilash"""
    await lock_rows(db, Table, [table_id])
    result = await db.execute(select(Table).where(Table.id == table_id))
    table = result.scalar_one_or_none()
    if not table:
        raise HTTPException(status_code=404, detail="Stol topilmadi")

    open_count = await open_orders_count(db, table.id)
    if open_count > 0:
        user_role_str = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)
        if force and user_role_str in ("admin", "developer"):
            open_orders = await get_open_orders(db, table.id)
            await log_audit_event(
                db=db,
                restaurant_id=table.restaurant_id,
                action="table_force_cleared",
                user=current_user,
                entity_type="table",
                entity_id=table.id,
                details={
                    "table_number": table.number,
                    "source": "clear_table",
                    "order_numbers": [o.order_number for o in open_orders],
                    "open_orders_count": open_count,
                },
            )
        else:
            raise HTTPException(status_code=409, detail="Stolda ochiq hisob bor")

    if table.deposit_amount:
        raise HTTPException(409, "Avans bor: avval uni hisobga o'tkazing yoki bron oynasida qaytaring")
    table.status = TableStatus.AVAILABLE
    table.is_unlocked = False
    table.current_pin = None
    table.reserved_by_name = None
    table.reserved_by_phone = None
    table.reserved_time = None
    table.reserved_guests = None
    table.deposit_amount = 0.0
    table.reservation_note = None
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

    # MUHIM: buyurtmalar -- moliyaviy yozuvlar, ular O'CHIRILMASLIGI kerak.
    # Ilgari stolni o'chirishga urinilganda SQLAlchemy bog'liq buyurtmalarning
    # table_id sini NULL qilishga harakat qilardi va server 500 qaytarardi:
    #   IntegrityError: NOT NULL constraint failed: orders.table_id
    # Endi bunday stolni o'chirmaymiz, faqat NOFAOL qilishni taklif qilamiz.
    cnt_res = await db.execute(
        select(func.count(Order.id)).where(Order.table_id == table.id)
    )
    orders_count = cnt_res.scalar() or 0
    if orders_count > 0:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Stol #{table.number} ni o'chirib bo'lmaydi: unga bog'liq "
                f"{orders_count} ta buyurtma bor va ular cheklar arxivi uchun "
                f"saqlanishi kerak. Stolni ro'yxatdan yashirish uchun uni "
                f"NOFAOL qiling (is_active = false)."
            ),
        )

    await db.delete(table)


