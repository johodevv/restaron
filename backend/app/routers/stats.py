import socket
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta, timezone

from app.core.database import get_db
from app.core.security import require_role
from app.models.order import Order, OrderItem, OrderStatus
from app.models.menu import MenuItem
from app.models.table import Table
from app.models.user import User, UserRole
from app.models.review import Review

router = APIRouter(prefix="/stats", tags=["📊 Statistika"])


@router.get("/lan-info", summary="Server tarmog'i IP manzillari")
async def get_lan_info():
    """QR kodlar telefon orqali ochilishi uchun serverning lokal IP manzillarini aniqlash"""
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
    return {
        "primary_ip": primary,
        "available_ips": ips,
        "suggested_frontend_url": f"http://{primary}:5173" if primary != "localhost" else "http://localhost:5173",
        "suggested_backend_url": f"http://{primary}:8000" if primary != "localhost" else "http://localhost:8000",
    }


@router.get("/dashboard", summary="Admin Dashboard")
async def get_dashboard(
    restaurant_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "developer")),
):
    """Asosiy statistika (kunlik)"""
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
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
    """Har kunlik daromad (grafik uchun)"""
    data = []
    for i in range(days - 1, -1, -1):
        day_start = (datetime.now(timezone.utc) - timedelta(days=i)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        day_end = day_start + timedelta(days=1)

        result = await db.execute(
            select(func.count(Order.id), func.sum(Order.total))
            .where(
                Order.restaurant_id == restaurant_id,
                Order.created_at >= day_start,
                Order.created_at < day_end,
                Order.status != OrderStatus.CANCELLED,
            )
        )
        count, revenue = result.one()
        data.append({
            "date": day_start.strftime("%Y-%m-%d"),
            "orders": count or 0,
            "revenue": round(float(revenue or 0), 2),
        })

    return data


@router.get("/waiter-performance", summary="Ofitsiantlar ko'rsatkichi")
async def get_waiter_performance(
    restaurant_id: int,
    days: int = Query(default=30),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "developer")),
):
    """Har bir ofitsiantning ishlash statistikasi"""
    since = datetime.now(timezone.utc) - timedelta(days=days)

    result = await db.execute(
        select(
            User.id,
            User.full_name,
            func.count(Order.id).label("orders_served"),
            func.sum(Order.total).label("total_revenue"),
            func.avg(Review.service_rating).label("avg_rating"),
        )
        .join(Order, Order.waiter_id == User.id, isouter=True)
        .join(Review, Review.waiter_id == User.id, isouter=True)
        .where(
            User.restaurant_id == restaurant_id,
            User.role == UserRole.WAITER,
        )
        .group_by(User.id, User.full_name)
    )

    return [
        {
            "id": row.id,
            "name": row.full_name,
            "orders_served": int(row.orders_served or 0),
            "total_revenue": round(float(row.total_revenue or 0), 2),
            "avg_rating": round(float(row.avg_rating or 0), 2),
        }
        for row in result.all()
    ]
