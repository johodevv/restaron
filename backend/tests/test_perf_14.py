import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from app.core.database import AsyncSessionLocal
from app.core.security import create_access_token, get_password_hash
from app.models.user import User, UserRole
from app.models.restaurant import Restaurant
from app.models.table import Table
from app.models.order import Order, OrderItem, OrderStatus
from app.models.menu import MenuItem, Category
from app.main import app

client = TestClient(app)


def get_auth_header(user_id: int, role: str, restaurant_id: int = 1) -> dict:
    token = create_access_token(
        data={"sub": str(user_id), "role": role, "restaurant_id": restaurant_id}
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
async def setup_perf_data():
    async with AsyncSessionLocal() as session:
        rest = await session.get(Restaurant, 1)
        if not rest:
            rest = Restaurant(id=1, name="Perf Restaron", slug="perf-restaron", address="Xiva", phone="+998901234567")
            session.add(rest)

        # Users: admin (id 7001), waiter (id 7002)
        admin = await session.get(User, 7001)
        if not admin:
            admin = User(
                id=7001,
                username="perf_admin",
                full_name="Perf Admin",
                hashed_password=get_password_hash("pass123"),
                role=UserRole.ADMIN,
                restaurant_id=1,
                is_active=True,
                is_approved=True,
            )
            session.add(admin)

        waiter = await session.get(User, 7002)
        if not waiter:
            waiter = User(
                id=7002,
                username="perf_waiter",
                full_name="Perf Waiter",
                hashed_password=get_password_hash("pass123"),
                role=UserRole.WAITER,
                restaurant_id=1,
                is_active=True,
                is_approved=True,
            )
            session.add(waiter)

        tbl = await session.get(Table, 701)
        if not tbl:
            tbl = Table(id=701, restaurant_id=1, number=701, capacity=4, qr_token="qr-perf-701")
            session.add(tbl)

        cat = await session.get(Category, 701)
        if not cat:
            cat = Category(id=701, restaurant_id=1, name="Milliy Taomlar")
            session.add(cat)

        m1 = await session.get(MenuItem, 701)
        if not m1:
            m1 = MenuItem(id=701, category_id=701, name="Xiva Oshi", price=35000.0, is_available=True)
            session.add(m1)

        now_utc = datetime.now(timezone.utc).replace(tzinfo=None)

        # Order 7001: Closed, is_paid=True
        ord1 = await session.get(Order, 7001)
        if not ord1:
            ord1 = Order(
                id=7001,
                restaurant_id=1,
                table_id=701,
                waiter_id=7002,
                order_number="ORD-P-7001",
                order_type="dine_in",
                status=OrderStatus.PAID,
                total=70000.0,
                cash_amount=50000.0,
                card_amount=20000.0,
                click_amount=0.0,
                debt_amount=0.0,
                waiter_share_amount=7000.0,
                is_paid=True,
                created_at=now_utc - timedelta(hours=2),
                closed_at=now_utc - timedelta(hours=1),
            )
            session.add(ord1)
            await session.flush()

            it1 = OrderItem(order_id=7001, menu_item_id=701, quantity=2, unit_price=35000.0, total_price=70000.0)
            session.add(it1)

        # Order 7002: Closed, is_paid=True
        ord2 = await session.get(Order, 7002)
        if not ord2:
            ord2 = Order(
                id=7002,
                restaurant_id=1,
                table_id=701,
                waiter_id=7002,
                order_number="ORD-P-7002",
                order_type="dine_in",
                status=OrderStatus.PAID,
                total=35000.0,
                cash_amount=0.0,
                card_amount=0.0,
                click_amount=25000.0,
                debt_amount=10000.0,
                waiter_share_amount=3500.0,
                is_paid=True,
                created_at=now_utc - timedelta(minutes=45),
                closed_at=now_utc - timedelta(minutes=15),
            )
            session.add(ord2)
            await session.flush()

            it2 = OrderItem(order_id=7002, menu_item_id=701, quantity=1, unit_price=35000.0, total_price=35000.0)
            session.add(it2)

        # Orders 7003, 7004, 7005 to ensure list_orders payload is > 1024 bytes
        for oid in (7003, 7004, 7005):
            o = await session.get(Order, oid)
            if not o:
                session.add(
                    Order(
                        id=oid,
                        restaurant_id=1,
                        table_id=701,
                        waiter_id=7002,
                        order_number=f"ORD-P-{oid}",
                        order_type="dine_in",
                        status=OrderStatus.PAID,
                        total=50000.0,
                        cash_amount=50000.0,
                        is_paid=True,
                        created_at=now_utc - timedelta(minutes=oid % 60),
                        closed_at=now_utc,
                    )
                )

        await session.commit()
    yield


@pytest.mark.anyio
async def test_gzip_middleware_compresses_large_responses():
    """GZipMiddleware minimum_size=1024 dan katta javoblarni siqadi, kichiklarini o'zgarishsiz qoldiradi"""
    # 1. /health javobi kichik (<1024 bayt) -> siqilmaydi
    res_small = client.get("/health", headers={"Accept-Encoding": "gzip"})
    assert res_small.status_code == 200
    assert int(res_small.headers.get("content-length", 0)) < 1024
    assert res_small.headers.get("content-encoding") is None

    # 2. 5 ta buyurtmali ro'yxat (>1024 bayt) -> GZipMiddleware orqali gzip bilan siqiladi
    headers = get_auth_header(7001, "admin", 1)
    headers["Accept-Encoding"] = "gzip"
    res_large = client.get("/api/v1/orders/?limit=100", headers=headers)
    assert res_large.status_code == 200
    assert res_large.headers.get("content-encoding") == "gzip"

    # 3. Accept-Encoding: identity (siqish so'ralmagan) -> siqilmaydi
    headers_no_gzip = get_auth_header(7001, "admin", 1)
    headers_no_gzip["Accept-Encoding"] = "identity"
    res_raw = client.get("/api/v1/orders/?limit=100", headers=headers_no_gzip)
    assert res_raw.status_code == 200
    assert res_raw.headers.get("content-encoding") is None


@pytest.mark.anyio
async def test_payments_report_sql_aggregation():
    """payments-report SQL agregatsiyasi bilan hisoblanadi va to'liq shaklni saqlaydi"""
    headers = get_auth_header(7001, "admin", 1)
    res = client.get("/api/v1/stats/payments-report?restaurant_id=1", headers=headers)
    assert res.status_code == 200
    payload = res.json()

    # Schemani tekshirish
    assert "start_date" in payload
    assert "end_date" in payload
    assert "orders_count" in payload
    assert "total_revenue" in payload
    assert "total_cash" in payload
    assert "total_card" in payload
    assert "total_click" in payload
    assert "total_debt" in payload
    assert "total_waiter_earnings" in payload
    assert "rows" in payload

    # Qiymatlarni tekshirish (70000 + 35000 = 105000)
    assert payload["orders_count"] >= 2
    assert payload["total_revenue"] >= 105000.0
    assert payload["total_cash"] >= 50000.0
    assert payload["total_card"] >= 20000.0
    assert payload["total_click"] >= 25000.0
    assert payload["total_debt"] >= 10000.0

    # Row strukturasini tekshirish
    assert len(payload["rows"]) >= 2
    row = next(r for r in payload["rows"] if r["order_id"] == 7001)
    assert row["order_number"] == "ORD-P-7001"
    assert row["cash_amount"] == 50000.0
    assert row["card_amount"] == 20000.0
    assert row["total"] == 70000.0
    assert row["waiter_id"] == 7002
    assert row["waiter_earning"] == 7000.0
    assert row["is_paid"] is True


@pytest.mark.anyio
async def test_list_orders_conditional_items_loading():
    """list_orders include_items=False (standart) bo'lganda items yuklanmaydi, items_count SQL bilan hisoblanadi"""
    headers = get_auth_header(7001, "admin", 1)

    # 1. Standart so'rov (include_items=False)
    res_default = client.get("/api/v1/orders/?limit=100", headers=headers)
    assert res_default.status_code == 200
    orders_default = res_default.json()

    ord1 = next(o for o in orders_default if o["id"] == 7001)
    ord2 = next(o for o in orders_default if o["id"] == 7002)

    assert ord1["items_count"] == 1
    assert ord2["items_count"] == 1
    # items bo'sh yoki yuklanmagan
    assert ord1["items"] == [] or ord1["items"] is None

    # 2. include_items=True so'rov
    res_items = client.get("/api/v1/orders/?limit=100&include_items=true", headers=headers)
    assert res_items.status_code == 200
    orders_items = res_items.json()

    ord1_with_items = next(o for o in orders_items if o["id"] == 7001)
    assert len(ord1_with_items["items"]) == 1
    assert ord1_with_items["items"][0]["menu_item_name"] == "Xiva Oshi"


@pytest.mark.anyio
async def test_server_health_non_blocking_cpu():
    """server-health endpointi interval=None bilan tez va to'siqsiz ishlaydi"""
    headers = get_auth_header(7001, "admin", 1)
    res = client.get("/api/v1/stats/server-health", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "cpu_usage_percent" in data
    assert isinstance(data["cpu_usage_percent"], (int, float))
