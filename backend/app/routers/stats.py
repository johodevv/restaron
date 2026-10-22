import os
import socket
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any

UZ_TZ = timezone(timedelta(hours=5))

from app.core.database import get_db
from app.core.security import require_role
from app.models.order import Order, OrderItem, OrderStatus
from app.models.menu import MenuItem
from app.models.table import Table
from app.models.user import User, UserRole
from app.models.review import Review

router = APIRouter(prefix="/stats", tags=["📊 Statistika"])



import time

_cached_lan_info = None
_cached_lan_info_time = 0.0

@router.get("/lan-info", summary="Server tarmog'i IP manzillari")
async def get_lan_info():
    """QR kodlar telefon orqali ochilishi uchun serverning lokal va internet manzillarini aniqlash"""
    global _cached_lan_info, _cached_lan_info_time
    now = time.time()
    if _cached_lan_info and (now - _cached_lan_info_time < 60.0):
        return _cached_lan_info

    # 1. Server public (Cloudflare tunnel) manzilini tekshirish
    public_url = None
    possible_paths = [
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "SERVER_ONLINE_URL.txt")),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "SERVER_ONLINE_URL.txt")),
        os.path.abspath("SERVER_ONLINE_URL.txt"),
    ]
    for p in possible_paths:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    val = f.read().strip()
                    if val.startswith("http"):
                        public_url = val
                        break
            except Exception:
                pass

    if not public_url and os.environ.get("PUBLIC_SERVER_URL"):
        public_url = os.environ["PUBLIC_SERVER_URL"].strip()

    ips = []
    try:
        hostname = socket.gethostname()
        for ip in socket.gethostbyname_ex(hostname)[2]:
            if not ip.startswith("127.") and not ip.startswith("169.254"):
                ips.append(ip)
    except Exception:
        pass

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        primary_ip = s.getsockname()[0]
        s.close()
        if primary_ip and primary_ip not in ips:
            ips.insert(0, primary_ip)
    except Exception:
        pass

    primary = ips[0] if ips else "localhost"
    local_url = f"http://{primary}:8000" if primary != "localhost" else "http://localhost:8000"
    suggested = public_url if public_url else local_url

    res = {
        "primary_ip": primary,
        "available_ips": ips,
        "public_url": public_url,
        "local_url": local_url,
        "suggested_frontend_url": suggested,
        "suggested_backend_url": suggested,
        "mode": "internet" if public_url else "local_wifi",
    }
    _cached_lan_info = res
    _cached_lan_info_time = now
    return res


@router.get("/dashboard", summary="Admin Dashboard")
async def get_dashboard(
    restaurant_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "developer")),
):
    """Asosiy statistika (kunlik)"""
    today_start = datetime.now(UZ_TZ).replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)

    # Bugungi buyurtmalar
    today_orders = await db.execute(
        select(func.count(Order.id), func.sum(Order.total))
        .where(
            Order.restaurant_id == restaurant_id,
            Order.created_at >= today_start,
            Order.created_at < today_end,
            Order.status != OrderStatus.CANCELLED,
        )
    )
    orders_count, total_revenue = today_orders.one()
    total_revenue = total_revenue or 0.0

    # Aktiv buyurtmalar (hozir)
    active_orders = await db.execute(
        select(func.count(Order.id)).where(
            Order.restaurant_id == restaurant_id,
            Order.status.in_([OrderStatus.PENDING, OrderStatus.CONFIRMED, OrderStatus.PREPARING]),
        )
    )
    active_count = active_orders.scalar()

    # Tayyor buyurtmalar
    ready_orders = await db.execute(
        select(func.count(Order.id)).where(
            Order.restaurant_id == restaurant_id,
            Order.status == OrderStatus.READY,
        )
    )
    ready_count = ready_orders.scalar()

    # Jami stollar
    tables_count = await db.execute(
        select(func.count(Table.id)).where(Table.restaurant_id == restaurant_id)
    )

    return {
        "today": {
            "orders_count": orders_count or 0,
            "total_revenue": round(total_revenue, 2),
            "active_orders": active_count or 0,
            "ready_orders": ready_count or 0,
        },
        "tables_total": tables_count.scalar() or 0,
    }


@router.get("/top-items", summary="Eng ko'p buyurtma qilingan taomlar")
async def get_top_items(
    restaurant_id: int,
    limit: int = Query(default=10, le=50),
    days: int = Query(default=30, description="Necha kunlik hisobot"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "developer")),
):
    """Qaysi taomdan ko'p sotilyapti"""
    since = datetime.now(timezone.utc) - timedelta(days=days)

    result = await db.execute(
        select(
            MenuItem.id,
            MenuItem.name,
            MenuItem.price,
            MenuItem.image_url,
            func.sum(OrderItem.quantity).label("total_quantity"),
            func.sum(OrderItem.total_price).label("total_revenue"),
        )
        .join(OrderItem, OrderItem.menu_item_id == MenuItem.id)
        .join(Order, Order.id == OrderItem.order_id)
        .where(
            Order.restaurant_id == restaurant_id,
            Order.created_at >= since,
            Order.status != OrderStatus.CANCELLED,
        )
        .group_by(MenuItem.id, MenuItem.name, MenuItem.price, MenuItem.image_url)
        .order_by(func.sum(OrderItem.quantity).desc())
        .limit(limit)
    )

    return [
        {
            "id": row.id,
            "name": row.name,
            "price": row.price,
            "image_url": row.image_url,
            "total_quantity": int(row.total_quantity or 0),
            "total_revenue": round(float(row.total_revenue or 0), 2),
        }
        for row in result.all()
    ]


@router.get("/revenue-chart", summary="Daromad grafigi")
async def get_revenue_chart(
    restaurant_id: int,
    days: int = Query(default=7, description="Necha kunlik"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "developer")),
):
    """Har kunlik daromad (grafik uchun bitta SQL so'rov bilan)"""
    start_date = (datetime.now(timezone.utc) - timedelta(days=days - 1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    date_col = func.date(Order.created_at).label("order_date")
    result = await db.execute(
        select(date_col, func.count(Order.id), func.sum(Order.total))
        .where(
            Order.restaurant_id == restaurant_id,
            Order.created_at >= start_date,
            Order.status != OrderStatus.CANCELLED,
        )
        .group_by(date_col)
    )
    daily_stats = {
        str(row[0]): {"orders": row[1] or 0, "revenue": round(float(row[2] or 0), 2)}
        for row in result.all()
    }

    data = []
    for i in range(days - 1, -1, -1):
        day_str = (datetime.now(timezone.utc) - timedelta(days=i)).strftime("%Y-%m-%d")
        stats = daily_stats.get(day_str, {"orders": 0, "revenue": 0.0})
        data.append({
            "date": day_str,
            "orders": stats["orders"],
            "revenue": stats["revenue"],
        })

    return data


@router.get("/waiter-performance", summary="Ofitsiantlar ko'rsatkichi")
async def get_waiter_performance(
    restaurant_id: int,
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "developer")),
):
    """Har bir ofitsiantning ishlash statistikasi (tanlangan davr bo'yicha)"""
    since = datetime.now(timezone.utc) - timedelta(days=days)

    # Bug 8 fix: Sana filtri JOIN ON shartida to'g'ri qo'llanilgan.
    # OUTER JOIN bilan bu shunday ishlaydi: sana filtridan tashqaridagi buyurtmalar
    # NULL qaytaradi va count(Order.id) ularni 0 sifatida hisoblaydi — BU TO'G'RI.
    # Qo'shimcha tuzatishlar:
    #   1) Order.status filtri — faqat SERVED/PAID buyurtmalar hisoblansin (bekor qilinganlar emas)
    #   2) Review uchun ham sana filtri to'g'ri qo'llanilgan (allaqachon bor edi)
    completed_statuses = ["served", "paid"]

    result = await db.execute(
        select(
            User.id,
            User.full_name,
            User.username,
            func.count(Order.id).label("orders_served"),
            func.coalesce(func.sum(Order.total), 0.0).label("total_revenue"),
            func.coalesce(func.avg(Review.service_rating), 0.0).label("avg_rating"),
        )
        .outerjoin(
            Order,
            and_(
                Order.waiter_id == User.id,
                Order.restaurant_id == restaurant_id,
                Order.created_at >= since,
                Order.status.in_(completed_statuses),  # Faqat yakunlangan buyurtmalar
            ),
        )
        .outerjoin(
            Review,
            and_(
                Review.waiter_id == User.id,
                Review.created_at >= since,
            ),
        )
        .where(
            User.restaurant_id == restaurant_id,
            User.role == UserRole.WAITER,
            User.is_active == True,  # Faqat faol ofitsiantlar
        )
        .group_by(User.id, User.full_name, User.username)
        .order_by(func.count(Order.id).desc())
    )

    return [
        {
            "id": row.id,
            "name": row.full_name or row.username,
            "orders_served": int(row.orders_served or 0),
            "total_revenue": round(float(row.total_revenue or 0), 2),
            "avg_rating": round(float(row.avg_rating or 0), 2),
            "period_days": days,
        }
        for row in result.all()
    ]


@router.get("/payments-report", summary="To'lovlar bo'yicha hisobot (Ali Poster uslubida)")
async def get_payments_report(
    restaurant_id: int,
    start_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    waiter_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "developer", "waiter")),
):
    """
    Kassa to'lovlar hisoboti (Ali Poster 'Отчет по оплатам' oynasining to'liq analogi):
    Stol, Chek #, Naqd, Karta, Click, Nasiya, Sana, Ofitsiant, Ulush va Jami.
    """
    from sqlalchemy.orm import selectinload

    if start_date:
        try:
            dt_start = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=UZ_TZ)
        except ValueError:
            dt_start = datetime.now(UZ_TZ).replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        dt_start = datetime.now(UZ_TZ).replace(hour=0, minute=0, second=0, microsecond=0)

    if end_date:
        try:
            dt_end = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59, tzinfo=UZ_TZ)
        except ValueError:
            dt_end = dt_start + timedelta(days=1)
    else:
        dt_end = dt_start + timedelta(days=1)

    query = (
        select(Order)
        .options(selectinload(Order.table), selectinload(Order.waiter))
        .where(
            Order.restaurant_id == restaurant_id,
            func.coalesce(Order.closed_at, Order.created_at) >= dt_start,
            func.coalesce(Order.closed_at, Order.created_at) <= dt_end,
            Order.status != OrderStatus.CANCELLED,
            # Faqat yopilgan (to'langan) buyurtmalar — bu kassa tushumi hisoboti.
            # Ochiq stollar qo'shilsa "Jami Tushum" naqd/karta/nasiya yig'indisiga
            # teng kelmay qoladi va kassani solishtirib bo'lmaydi.
            Order.is_paid == True,
        )
    )

    if waiter_id:
        query = query.where(Order.waiter_id == waiter_id)

    query = query.order_by(Order.created_at.desc())
    res = await db.execute(query)
    orders = res.scalars().all()

    rows = []
    total_sales = 0.0
    total_cash = 0.0
    total_card = 0.0
    total_click = 0.0
    total_debt = 0.0
    total_waiter_earnings = 0.0

    for o in orders:
        tot = float(o.total or 0.0)
        c_cash = float(o.cash_amount or 0.0)
        c_card = float(o.card_amount or 0.0)
        c_click = float(o.click_amount or 0.0)
        c_debt = float(o.debt_amount or 0.0)
        w_earn = float(o.waiter_share_amount or 0.0)

        total_sales += tot
        total_cash += c_cash
        total_card += c_card
        total_click += c_click
        total_debt += c_debt
        total_waiter_earnings += w_earn

        t_name = o.hall_name or ""
        if o.table:
            t_room = o.table.room or ""
            t_num = o.table.number
            t_name = f"{t_name or t_room} #{t_num}".strip()
        else:
            t_name = o.order_type or "Olib ketish"

        w_name = (o.waiter.full_name or o.waiter.username) if o.waiter else "—"

        rows.append({
            "order_id": o.id,
            "order_number": o.order_number,
            "table_name": t_name,
            "cash_amount": c_cash,
            "card_amount": c_card,
            "click_amount": c_click,
            "debt_amount": c_debt,
            "created_at": o.created_at.strftime("%d.%m.%Y %H:%M") if o.created_at else "—",
            "closed_at": o.closed_at.strftime("%d.%m.%Y %H:%M") if o.closed_at else "Еще не завершен",
            "total": tot,
            "waiter_name": w_name,
            "waiter_id": o.waiter_id,
            "waiter_earning": w_earn,
            "status": o.status.value if hasattr(o.status, "value") else str(o.status),
            "is_paid": bool(o.is_paid),
        })

    return {
        "start_date": dt_start.strftime("%Y-%m-%d"),
        "end_date": dt_end.strftime("%Y-%m-%d"),
        "orders_count": len(rows),
        "total_revenue": round(total_sales, 2),
        "total_cash": round(total_cash, 2),
        "total_card": round(total_card, 2),
        "total_click": round(total_click, 2),
        "total_debt": round(total_debt, 2),
        "total_waiter_earnings": round(total_waiter_earnings, 2),
        "rows": rows,
    }


@router.get("/waiter-kpi-detail", summary="Ofitsiantlar KPI va foiz daromadi batafsil")
async def get_waiter_kpi_detail(
    restaurant_id: int,
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "developer")),
):
    """Ofitsiantlarning aniq savdosi, xizmat haqi va daromadlari tahlili (bitta SQL query bilan)"""
    dt_start = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=UZ_TZ) if start_date else datetime.now(UZ_TZ).replace(hour=0, minute=0, second=0, microsecond=0)
    dt_end = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59, tzinfo=UZ_TZ) if end_date else dt_start + timedelta(days=1)

    query = (
        select(
            User.id,
            User.username,
            User.full_name,
            User.commission_percent,
            func.count(Order.id).label("orders_count"),
            func.coalesce(func.sum(Order.total), 0.0).label("total_sales"),
            func.coalesce(func.sum(Order.service_fee_amount), 0.0).label("total_service_fee"),
            func.coalesce(func.sum(Order.waiter_share_amount), 0.0).label("earned_share"),
        )
        .outerjoin(
            Order,
            and_(
                Order.waiter_id == User.id,
                func.coalesce(Order.closed_at, Order.created_at) >= dt_start,
                func.coalesce(Order.closed_at, Order.created_at) <= dt_end,
                Order.status.in_([OrderStatus.PAID, OrderStatus.SERVED]),
            ),
        )
        .where(
            User.restaurant_id == restaurant_id,
            User.role == UserRole.WAITER,
        )
        .group_by(User.id)
        .order_by(User.id)
    )
    res = await db.execute(query)

    kpi_list = []
    for row in res.all():
        kpi_list.append({
            "waiter_id": row[0],
            "username": row[1],
            "full_name": row[2],
            "commission_percent": row[3] or 0.0,
            "orders_count": int(row[4] or 0),
            "total_sales": float(row[5] or 0.0),
            "total_service_fee": float(row[6] or 0.0),
            "earned_share": float(row[7] or 0.0),
        })

    return kpi_list


@router.get("/server-health", summary="Server salomatligi va monitoringi")
async def get_server_health(
    current_user: User = Depends(require_role("developer", "admin")),
):
    import shutil
    import ctypes
    from app.websockets.manager import manager as ws_manager
    from app.core.disk_utils import get_free_disk_mb

    cpu_usage = 12.5
    ram_percent = 35.0
    ram_total_gb = 8.0
    ram_used_gb = 2.8
    ram_free_gb = 5.2

    psutil_available = False
    try:
        import psutil
        psutil_available = True
    except (ImportError, Exception):
        psutil_available = False

    if psutil_available:
        try:
            cpu_usage = psutil.cpu_percent(interval=0.1)
            ram = psutil.virtual_memory()
            ram_percent = round(ram.percent, 1)
            ram_total_gb = round(ram.total / (1024 ** 3), 2)
            ram_used_gb = round(ram.used / (1024 ** 3), 2)
            ram_free_gb = round(ram.available / (1024 ** 3), 2)
        except Exception:
            psutil_available = False

    if not psutil_available:
        try:
            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]
            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            if hasattr(ctypes, "windll") and hasattr(ctypes.windll, "kernel32"):
                ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
                total_bytes = stat.ullTotalPhys
                avail_bytes = stat.ullAvailPhys
                used_bytes = total_bytes - avail_bytes
                ram_total_gb = round(total_bytes / (1024 ** 3), 2)
                ram_free_gb = round(avail_bytes / (1024 ** 3), 2)
                ram_used_gb = round(used_bytes / (1024 ** 3), 2)
                ram_percent = round((used_bytes / total_bytes) * 100, 1) if total_bytes > 0 else 35.0
        except Exception:
            pass

    # Disk bo'sh joyi
    free_mb = get_free_disk_mb()
    try:
        total_disk, used_disk, free_disk = shutil.disk_usage(".")
        disk_percent = round((used_disk / total_disk) * 100, 1)
        disk_total_gb = round(total_disk / (1024 ** 3), 2)
        disk_free_gb = round(free_disk / (1024 ** 3), 2)
    except Exception:
        disk_percent = 0.0
        disk_total_gb = 0.0
        disk_free_gb = round(free_mb / 1024, 2)

    # Faol WebSocket ulanishlar
    active_ws_count = len(getattr(ws_manager, "_connection_meta", {}))

    # Oxirgi 20 ta xato logi
    error_logs = []
    log_candidates = [
        "error.log",
        os.path.join(os.path.dirname(__file__), "..", "..", "error.log"),
        "server.log",
        os.path.join(os.path.dirname(__file__), "..", "..", "server.log"),
    ]
    for log_path in log_candidates:
        if os.path.exists(log_path):
            try:
                with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                    lines = [l.strip() for l in f.readlines() if l.strip()]
                    error_logs = lines[-20:]
                    if error_logs:
                        break
            except Exception:
                pass

    status_level = "healthy"
    if cpu_usage > 85 or ram_percent > 90 or disk_free_gb < 1:
        status_level = "critical"
    elif cpu_usage > 65 or ram_percent > 75 or disk_free_gb < 5:
        status_level = "warning"

    return {
        "status": status_level,
        "cpu_usage_percent": cpu_usage,
        "ram": {
            "percent": ram_percent,
            "total_gb": ram_total_gb,
            "used_gb": ram_used_gb,
            "free_gb": ram_free_gb,
        },
        "disk": {
            "percent": disk_percent,
            "total_gb": disk_total_gb,
            "free_gb": disk_free_gb,
            "free_mb": round(free_mb, 1),
        },
        "active_websockets": active_ws_count,
        "recent_errors": error_logs,
        "timestamp": datetime.now(UZ_TZ).strftime("%Y-%m-%d %H:%M:%S"),
    }

