"""
Test suite for VAZIFA 9B:
1. GET /orders/{id}, GET /orders/table/{id}/active, GET /tables/{id}/bill:
   - Staff token: returns full response as before.
   - Guest without valid ?qr_token=: 403 Forbidden.
   - Guest with valid ?qr_token=: 200 OK with sensitive customer/staff/internal data sanitized.
2. call_waiter rate limits:
   - Key: 'call:{table_id}' (1 call / 20 seconds).
   - IP ceiling: 30 / minute.
   - Message: 'Ofitsiant chaqirildi, biroz kuting.'
3. Real IP (TRUSTED_PROXY_IPS):
   - X-Forwarded-For and CF-Connecting-IP only trusted when request arrives from TRUSTED_PROXY_IPS.
4. Login rate limit:
   - 10 attempts per minute per IP + username.
"""
import pytest
from starlette.requests import Request
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.database import Base, engine, AsyncSessionLocal
from app.core.config import settings
from app.core.rate_limit import get_client_ip, rate_limiter_storage
from app.models.restaurant import Restaurant, RestaurantSettings
from app.models.table import Table, TableStatus
from app.models.user import User, UserRole
from app.models.order import Order, OrderItem, OrderStatus
from app.models.menu import MenuItem, Category
from app.core.security import create_access_token, get_password_hash
from app.main import app


def create_fake_request(client_host: str, headers: dict = None) -> Request:
    header_list = []
    if headers:
        for k, v in headers.items():
            header_list.append((k.lower().encode("latin-1"), v.encode("latin-1")))
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/test",
        "headers": header_list,
        "client": (client_host, 12345),
        "server": ("testserver", 80),
    }
    return Request(scope)


@pytest.mark.anyio
async def test_real_ip_trusted_proxies():
    """Haqiqiy IP: X-Forwarded-For va CF-Connecting-IP FAQAT TRUSTED_PROXY_IPS dan kelganda ishlatiladi."""
    # 1. Untrusted client directly connecting from internet
    untrusted_req = create_fake_request(
        client_host="203.0.113.195",
        headers={
            "X-Forwarded-For": "1.1.1.1, 10.0.0.1",
            "CF-Connecting-IP": "8.8.8.8",
        },
    )
    # Headers should be completely ignored!
    assert get_client_ip(untrusted_req) == "203.0.113.195"

    # 2. Trusted proxy connecting (127.0.0.1) with CF-Connecting-IP
    trusted_cf_req = create_fake_request(
        client_host="127.0.0.1",
        headers={
            "CF-Connecting-IP": "198.51.100.42",
            "X-Forwarded-For": "198.51.100.42, 127.0.0.1",
        },
    )
    assert get_client_ip(trusted_cf_req) == "198.51.100.42"

    # 3. Trusted proxy connecting (127.0.0.1) with X-Forwarded-For only
    trusted_xff_req = create_fake_request(
        client_host="127.0.0.1",
        headers={
            "X-Forwarded-For": "198.51.100.99, 10.0.0.1",
        },
    )
    assert get_client_ip(trusted_xff_req) == "198.51.100.99"

    # 4. Trusted proxy IPv6 (::1)
    trusted_ipv6_req = create_fake_request(
        client_host="::1",
        headers={
            "CF-Connecting-IP": "203.0.113.77",
        },
    )
    assert get_client_ip(trusted_ipv6_req) == "203.0.113.77"


@pytest.fixture(autouse=True)
async def setup_test_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        r1 = await session.get(Restaurant, 1)
        if not r1:
            r1 = Restaurant(id=1, name="Rest 1", slug="rest-1")
            session.add(r1)

        set1 = await session.get(RestaurantSettings, 1)
        if not set1:
            set1 = RestaurantSettings(restaurant_id=1, allow_call_waiter=True)
            session.add(set1)
        else:
            set1.allow_call_waiter = True

        cat1 = await session.get(Category, 1)
        if not cat1:
            cat1 = Category(id=1, restaurant_id=1, name="Osh")
            session.add(cat1)

        m1 = await session.get(MenuItem, 1)
        if not m1:
            m1 = MenuItem(id=1, category_id=1, name="Palov", price=45000.0)
            session.add(m1)

        # Table 601
        res = await session.execute(select(Table).where(Table.id == 601))
        t1 = res.scalar_one_or_none()
        if not t1:
            t1 = Table(
                id=601,
                restaurant_id=1,
                number=61,
                qr_token="qr-token-601",
                status=TableStatus.OCCUPIED,
                is_active=True,
            )
            session.add(t1)

        # Table 602
        res2 = await session.execute(select(Table).where(Table.id == 602))
        t2 = res2.scalar_one_or_none()
        if not t2:
            t2 = Table(
                id=602,
                restaurant_id=1,
                number=62,
                qr_token="qr-token-602",
                status=TableStatus.OCCUPIED,
                is_active=True,
            )
            session.add(t2)

        # Waiter user
        res_u = await session.execute(select(User).where(User.username == "waiter_user_9b"))
        u = res_u.scalar_one_or_none()
        if not u:
            u = User(
                id=699,
                username="waiter_user_9b",
                hashed_password=get_password_hash("pass123"),
                full_name="Waiter 9B",
                role=UserRole.WAITER,
                restaurant_id=1,
                is_active=True,
                is_approved=True,
            )
            session.add(u)

        # Order 901
        res_o = await session.execute(select(Order).where(Order.id == 901))
        o = res_o.scalar_one_or_none()
        if not o:
            o = Order(
                id=901,
                order_number="ORD-901",
                restaurant_id=1,
                table_id=601,
                waiter_id=699,
                customer_name="Alisher",
                customer_phone="+998901234567",
                delivery_address="Mustaqillik ko'chasi 15",
                status=OrderStatus.PREPARING,
                subtotal=45000.0,
                total=45000.0,
                waiter_share_amount=5000.0,
                is_paid=False,
            )
            session.add(o)

            oi = OrderItem(
                id=9001,
                order_id=901,
                menu_item_id=1,
                quantity=1,
                unit_price=45000.0,
                total_price=45000.0,
            )
            session.add(oi)

        await session.commit()
    yield


@pytest.mark.anyio
async def test_order_and_bill_endpoints_guest_vs_staff():
    """GET /orders/{id}, GET /orders/table/{id}/active, GET /tables/{id}/bill himoyasi va tozalanishi."""
    client = TestClient(app)
    staff_token = create_access_token({"sub": "699", "role": "waiter"})
    headers_staff = {"Authorization": f"Bearer {staff_token}"}

    # ─────────────────────────────────────────────────────────
    # 1. GET /orders/{order_id}
    # ─────────────────────────────────────────────────────────
    # A. Mehmon tokenlarsiz va qr_token siz -> 403
    r = client.get("/api/v1/orders/901")
    assert r.status_code == 403

    # B. Mehmon noto'g'ri qr_token bilan -> 403
    r = client.get("/api/v1/orders/901?qr_token=wrong_token")
    assert r.status_code == 403

    # C. Mehmon to'g'ri qr_token bilan -> 200, shaxsiy va ichki ma'lumotlar tozalangan
    r = client.get("/api/v1/orders/901?qr_token=qr-token-601")
    assert r.status_code == 200
    data = r.json()
    assert data["order_number"] == "ORD-901"
    assert data["customer_phone"] is None
    assert data["delivery_address"] is None
    assert data["waiter_share_amount"] == 0.0
    assert data["waiter_id"] is None

    # D. Xodim tokeni bilan -> 200, to'liq ma'lumotlar mavjud
    r = client.get("/api/v1/orders/901", headers=headers_staff)
    assert r.status_code == 200
    staff_data = r.json()
    assert staff_data["customer_phone"] == "+998901234567"
    assert staff_data["delivery_address"] == "Mustaqillik ko'chasi 15"
    assert staff_data["waiter_share_amount"] == 5000.0
    assert staff_data["waiter_id"] == 699

    # ─────────────────────────────────────────────────────────
    # 2. GET /orders/table/{table_id}/active
    # ─────────────────────────────────────────────────────────
    # A. Mehmon tokenlarsiz va qr_token siz -> 403
    r = client.get("/api/v1/orders/table/601/active")
    assert r.status_code == 403

    # B. Mehmon noto'g'ri qr_token bilan -> 403
    r = client.get("/api/v1/orders/table/601/active?qr_token=wrong_token")
    assert r.status_code == 403

    # C. Mehmon to'g'ri qr_token bilan -> 200, tozalangan
    r = client.get("/api/v1/orders/table/601/active?qr_token=qr-token-601")
    assert r.status_code == 200
    orders = r.json()
    assert len(orders) >= 1
    o_guest = orders[0]
    assert o_guest["customer_phone"] is None
    assert o_guest["delivery_address"] is None
    assert o_guest["waiter_share_amount"] == 0.0
    assert o_guest["waiter_id"] is None

    # D. Xodim tokeni bilan -> 200, to'liq
    r = client.get("/api/v1/orders/table/601/active", headers=headers_staff)
    assert r.status_code == 200
    o_staff = r.json()[0]
    assert o_staff["customer_phone"] == "+998901234567"
    assert o_staff["waiter_share_amount"] == 5000.0

    # ─────────────────────────────────────────────────────────
    # 3. GET /tables/{table_id}/bill
    # ─────────────────────────────────────────────────────────
    # A. Mehmon qr_token siz -> 403
    r = client.get("/api/v1/tables/601/bill")
    assert r.status_code == 403

    # B. Mehmon noto'g'ri qr_token bilan -> 403
    r = client.get("/api/v1/tables/601/bill?qr_token=wrong_token")
    assert r.status_code == 403

    # C. Mehmon to'g'ri qr_token bilan -> 200, ichki id lar tozalangan
    r = client.get("/api/v1/tables/601/bill?qr_token=qr-token-601")
    assert r.status_code == 200
    bill = r.json()
    assert len(bill["items"]) >= 1
    b_item = bill["items"][0]
    assert b_item["order_id"] is None
    assert b_item["order_item_id"] is None
    assert b_item["order_item_ids"] == []

    # D. Xodim tokeni bilan -> 200, ichki id lar mavjud (kassir tuzatishi uchun)
    r = client.get("/api/v1/tables/601/bill", headers=headers_staff)
    assert r.status_code == 200
    staff_bill = r.json()
    sb_item = staff_bill["items"][0]
    assert sb_item["order_id"] == 901
    assert sb_item["order_item_id"] == 9001


@pytest.mark.anyio
async def test_call_waiter_rate_limiting():
    """call_waiter: 'call:{table_id}' bo'yicha 1 chaqiruv / 20s; chegaradan oshganda 'Ofitsiant chaqirildi, biroz kuting.'"""
    client = TestClient(app)
    # Storage ni tozalash
    rate_limiter_storage._records.clear()

    # Birinchi chaqiruv stol 601 uchun -> 200 OK
    r1 = client.post("/api/v1/orders/call-waiter", json={"table_id": 601, "qr_token": "qr-token-601"})
    assert r1.status_code == 200

    # 20 soniya ichida takroriy chaqiruv -> 429
    r2 = client.post("/api/v1/orders/call-waiter", json={"table_id": 601, "qr_token": "qr-token-601"})
    assert r2.status_code == 429
    assert "Ofitsiant chaqirildi, biroz kuting." in r2.json()["detail"]

    # Boshqa stol 602 uchun chaqiruv bloklanmasligi kerak -> 200 OK
    r3 = client.post("/api/v1/orders/call-waiter", json={"table_id": 602, "qr_token": "qr-token-602"})
    assert r3.status_code == 200


@pytest.mark.anyio
async def test_login_rate_limiting():
    """Login limiti: IP + username bo'yicha daqiqada 10 urinish."""
    client = TestClient(app)
    rate_limiter_storage._records.clear()

    # 10 ta muvaffaqiyatsiz urinish (401)
    for i in range(10):
        r = client.post("/api/v1/auth/login", json={"username": "user_limit_9b", "password": "wrong"})
        assert r.status_code == 401

    # 11-chi urinish -> 429
    r_limited = client.post("/api/v1/auth/login", json={"username": "user_limit_9b", "password": "wrong"})
    assert r_limited.status_code == 429

    # Boshqa username dan urinish bloklanmagan bo'lishi kerak
    r_diff_user = client.post("/api/v1/auth/login", json={"username": "different_user_9b", "password": "wrong"})
    assert r_diff_user.status_code == 401
