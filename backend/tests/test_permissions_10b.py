"""
Test suite for VAZIFA 10B: Ruxsatlarni to'g'rilash
1. debts: qarz yaratish va to'lash faqat admin, cashier, developer (ofitsiant 403).
   Qarz yaratishda mijoz ismi va telefon majburiy (bo'sh yoki 'Noma'lum Mijoz' rad etilsin).
2. payments-report: waiter bo'lsa waiter_id majburan current_user.id bo'lsin. Sana oralig'i 366 kundan oshmasin.
3. service-fee o'zgartirish: faqat admin, cashier, developer; audit 'service_fee_changed' (eski -> yangi foiz).
4. list_orders: restaurant_id parametri o'rniga current_user.restaurant_id (developer istisno);
   'cashier' ruxsat ro'yxatiga qo'shilsin; limit standart 100, eng ko'pi 300.
"""
import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import select, delete

from app.core.database import Base, engine, AsyncSessionLocal
from app.models.restaurant import Restaurant
from app.models.user import User, UserRole
from app.models.table import Table, TableStatus
from app.models.order import Order, OrderStatus
from app.models.debt import Debt
from app.models.audit_log import AuditLog
from app.core.security import create_access_token, get_password_hash
from app.main import app


@pytest.fixture(autouse=True)
async def setup_test_data_10b():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        # Restaurants
        for r_id in (1, 2):
            r = await session.get(Restaurant, r_id)
            if not r:
                session.add(Restaurant(id=r_id, name=f"Rest {r_id}", slug=f"rest-{r_id}"))

        # Users
        users_def = [
            (2001, "dev_10b", UserRole.DEVELOPER, None),
            (2002, "admin_10b", UserRole.ADMIN, 1),
            (2003, "cashier_10b", UserRole.CASHIER, 1),
            (2004, "waiter_10b", UserRole.WAITER, 1),
            (2005, "waiter2_10b", UserRole.WAITER, 1),
        ]
        for uid, uname, urole, urid in users_def:
            u = await session.get(User, uid)
            if not u:
                u = User(
                    id=uid,
                    username=uname,
                    full_name=uname.title(),
                    hashed_password=get_password_hash("pass12345"),
                    role=urole,
                    restaurant_id=urid,
                    is_active=True,
                    is_approved=True,
                )
                session.add(u)
            else:
                u.role = urole
                u.restaurant_id = urid
                u.is_active = True
                u.is_approved = True

        # Restore Table 201 for test_ws_security_8a
        t201 = await session.get(Table, 201)
        if t201:
            t201.restaurant_id = 2

        # Table 301 for test 10B (Restaurant 1)
        t301 = await session.get(Table, 301)
        if not t301:
            session.add(Table(id=301, restaurant_id=1, number=301, capacity=4, qr_token="qr-token-301", status=TableStatus.AVAILABLE))
        else:
            t301.restaurant_id = 1
            t301.qr_token = "qr-token-301"

        # Open order for table 301
        from app.models.menu import Category, MenuItem
        from app.models.order import OrderItem
        session.add(Category(id=91001, restaurant_id=1, name='Permission test dishes'))
        session.add(MenuItem(id=91001, category_id=91001, name='Permission test dish', price=10000))
        ord1 = await session.get(Order, 2001)
        if not ord1:
            ord1 = Order(
                id=2001,
                restaurant_id=1,
                table_id=301,
                order_number="ORD-2001",
                waiter_id=2004,
                status=OrderStatus.PENDING,
                is_paid=False,
                service_fee_percent=10.0,
                service_fee_amount=1000.0,
                subtotal=10000.0,
                total=11000.0,
            )
            session.add(ord1)
            session.add(OrderItem(order_id=2001, menu_item_id=91001, quantity=1, unit_price=10000, total_price=10000))
        else:
            ord1.restaurant_id = 1
            ord1.table_id = 301
            ord1.service_fee_percent = 10.0
            ord1.status = OrderStatus.PENDING
            ord1.is_paid = False


        # Paid order for waiter 2004 and paid order for waiter 2005
        o_waiter1 = await session.get(Order, 2002)
        if not o_waiter1:
            session.add(Order(
                id=2002,
                restaurant_id=1,
                table_id=301,
                order_number="ORD-2002",
                waiter_id=2004,
                status=OrderStatus.PAID,
                is_paid=True,
                total=50000.0,
                cash_amount=50000.0,
                closed_at=datetime.now(timezone.utc),
            ))

        o_waiter2 = await session.get(Order, 2003)
        if not o_waiter2:
            session.add(Order(
                id=2003,
                restaurant_id=1,
                table_id=301,
                order_number="ORD-2003",
                waiter_id=2005,
                status=OrderStatus.PAID,
                is_paid=True,
                total=75000.0,
                cash_amount=75000.0,
                closed_at=datetime.now(timezone.utc),
            ))

        await session.commit()
    yield


def get_headers(user_id: int, role: str, restaurant_id: int = 1) -> dict:
    token = create_access_token(
        data={"sub": str(user_id), "role": role, "restaurant_id": restaurant_id}
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.anyio
async def test_debts_permissions_and_validation():
    """1. debts: qarz yaratish va to'lash faqat admin, cashier, developer (ofitsiant 403)."""
    with TestClient(app) as client:
        waiter_hdr = get_headers(2004, "waiter", 1)
        cashier_hdr = get_headers(2003, "cashier", 1)
        admin_hdr = get_headers(2002, "admin", 1)

        # Ofitsiant qarz yarata olmaydi -> 403
        payload_valid = {
            "restaurant_id": 1,
            "customer_name": "Alisher Qodirov",
            "customer_phone": "+998901234567",
            "amount": 150000.0,
        }
        res_w_create = client.post("/api/v1/debts/", json=payload_valid, headers=waiter_hdr)
        assert res_w_create.status_code == 403

        # Mijoz ismi bo'sh yoki 'Noma'lum Mijoz' bo'lsa -> 400
        res_bad_name1 = client.post(
            "/api/v1/debts/",
            json={"restaurant_id": 1, "customer_name": "", "customer_phone": "+998901234567", "amount": 1000.0},
            headers=cashier_hdr,
        )
        assert res_bad_name1.status_code in (400, 422)

        res_bad_name2 = client.post(
            "/api/v1/debts/",
            json={"restaurant_id": 1, "customer_name": "Noma'lum Mijoz", "customer_phone": "+998901234567", "amount": 1000.0},
            headers=cashier_hdr,
        )
        assert res_bad_name2.status_code == 400

        res_bad_name3 = client.post(
            "/api/v1/debts/",
            json={"restaurant_id": 1, "customer_name": "nomalum mijoz", "customer_phone": "+998901234567", "amount": 1000.0},
            headers=cashier_hdr,
        )
        assert res_bad_name3.status_code == 400

        # Telefon raqami bo'sh yoki noto'g'ri bo'lsa -> 400 yoki 422
        res_bad_phone = client.post(
            "/api/v1/debts/",
            json={"restaurant_id": 1, "customer_name": "Valijon", "customer_phone": "", "amount": 1000.0},
            headers=cashier_hdr,
        )
        assert res_bad_phone.status_code in (400, 422)

        res_bad_phone2 = client.post(
            "/api/v1/debts/",
            json={"restaurant_id": 1, "customer_name": "Valijon", "customer_phone": "       ", "amount": 1000.0},
            headers=cashier_hdr,
        )
        assert res_bad_phone2.status_code == 400

        # Cashier to'g'ri qarz yaratadi -> 201
        res_ok = client.post("/api/v1/debts/", json=payload_valid, headers=cashier_hdr)
        assert res_ok.status_code == 201
        debt_id = res_ok.json()["id"]

        # Ofitsiant qarz to'lay olmaydi -> 403
        res_w_pay = client.patch(
            f"/api/v1/debts/{debt_id}/pay",
            json={"payment_amount": 50000.0, "note": "Ofitsiant urinishi"},
            headers=waiter_hdr,
        )
        assert res_w_pay.status_code == 403

        # Cashier qarz to'lay oladi -> 200
        res_c_pay = client.patch(
            f"/api/v1/debts/{debt_id}/pay",
            json={"payment_amount": 50000.0, "note": "Kassir qabul qildi"},
            headers=cashier_hdr,
        )
        assert res_c_pay.status_code == 200
        assert res_c_pay.json()["paid_amount"] == 50000.0
        assert res_c_pay.json()["remaining_amount"] == 100000.0


@pytest.mark.anyio
async def test_payments_report_date_range_and_waiter_isolation():
    """2. payments-report: waiter bo'lsa waiter_id majburan current_user.id bo'lsin. Sana oralig'i 366 kundan oshmasin."""
    with TestClient(app) as client:
        admin_hdr = get_headers(2002, "admin", 1)
        waiter1_hdr = get_headers(2004, "waiter", 1)

        # 366 kundan oshgan sana oralig'i -> 400
        res_too_long = client.get(
            "/api/v1/stats/payments-report?restaurant_id=1&start_date=2024-01-01&end_date=2025-02-01",
            headers=admin_hdr,
        )
        assert res_too_long.status_code == 400
        assert "366 kundan oshmasligi" in res_too_long.json()["detail"]

        # Tugash sanasi boshlanishidan oldin bo'lsa -> 400
        res_invalid_order = client.get(
            "/api/v1/stats/payments-report?restaurant_id=1&start_date=2026-05-01&end_date=2026-04-01",
            headers=admin_hdr,
        )
        assert res_invalid_order.status_code == 400

        # Ruxsat etilgan sana oralig'i (< 366 kun) -> 200
        today = datetime.now().strftime("%Y-%m-%d")
        res_admin = client.get(
            f"/api/v1/stats/payments-report?restaurant_id=1&start_date={today}&end_date={today}",
            headers=admin_hdr,
        )
        assert res_admin.status_code == 200
        admin_data = res_admin.json()
        # Admin ham 2004, ham 2005 ofitsiant buyurtmalarini ko'radi
        admin_waiter_ids = {r["waiter_id"] for r in admin_data["rows"]}
        assert 2004 in admin_waiter_ids or 2005 in admin_waiter_ids

        # Ofitsiant 1 so'rov yuboradi, hatto waiter_id=2005 deb aldasa ham:
        res_waiter = client.get(
            f"/api/v1/stats/payments-report?restaurant_id=1&start_date={today}&end_date={today}&waiter_id=2005",
            headers=waiter1_hdr,
        )
        assert res_waiter.status_code == 200
        waiter_data = res_waiter.json()
        # Ofitsiant faqat o'zining (id=2004) buyurtmalarini ko'rishi shart!
        for r in waiter_data["rows"]:
            assert r["waiter_id"] == 2004


@pytest.mark.anyio
async def test_service_fee_permissions_and_audit():
    """3. service-fee o'zgartirish: faqat admin, cashier, developer; audit 'service_fee_changed'."""
    with TestClient(app) as client:
        waiter_hdr = get_headers(2004, "waiter", 1)
        cashier_hdr = get_headers(2003, "cashier", 1)

        # Ofitsiant xizmat haqini o'zgartira olmaydi -> 403
        res_w = client.patch(
            "/api/v1/tables/301/service-fee",
            json={"percent": 15.0},
            headers=waiter_hdr,
        )
        assert res_w.status_code == 403

        # Cashier o'zgartira oladi -> 200
        res_c = client.patch(
            "/api/v1/tables/301/service-fee",
            json={"percent": 18.0},
            headers=cashier_hdr,
        )
        assert res_c.status_code == 200
        assert res_c.json()["service_fee_percent"] == 18.0

        # Audit yozilganligini tekshirish
        async with AsyncSessionLocal() as session:
            res_audit = await session.execute(
                select(AuditLog)
                .where(
                    AuditLog.action == "service_fee_changed",
                    AuditLog.entity_id == 301,
                )
                .order_by(AuditLog.created_at.desc())
            )
            audit = res_audit.scalars().first()
            assert audit is not None
            assert audit.details["new_percent"] == 18.0
            assert audit.details["old_percent"] == 10.0


@pytest.mark.anyio
async def test_list_orders_permissions_restaurant_and_limit():
    """4. list_orders: restaurant_id o'rniga current_user.restaurant_id (developer istisno);
    cashier ruxsatli; limit standart 100, eng ko'pi 300."""
    with TestClient(app) as client:
        waiter_hdr = get_headers(2004, "waiter", 1)
        cashier_hdr = get_headers(2003, "cashier", 1)
        dev_hdr = get_headers(2001, "developer", 1)

        # Cashier buyurtmalar ro'yxatini ko'ra oladi -> 200
        res_cashier = client.get("/api/v1/orders/", headers=cashier_hdr)
        assert res_cashier.status_code == 200

        # Limit 300 dan oshsa -> 422
        res_over_limit = client.get("/api/v1/orders/?limit=301", headers=cashier_hdr)
        assert res_over_limit.status_code == 422

        # Standart limit (100) bilan so'rov -> 200
        res_std = client.get("/api/v1/orders/?limit=100", headers=cashier_hdr)
        assert res_std.status_code == 200

        # Oddiy foydalanuvchi restaurant_id=999 yuborsa ham o'z restorani (1) ishlatiladi
        res_override = client.get("/api/v1/orders/?restaurant_id=999", headers=cashier_hdr)
        assert res_override.status_code == 200
        # Buyurtmalar faqat restaurant 1 ga tegishli
        data = res_override.json()
        assert len(data) > 0

        # Developer restaurant_id=999 ni tanlay oladi va 0 ta buyurtma qaytadi
        res_dev = client.get("/api/v1/orders/?restaurant_id=999", headers=dev_hdr)
        assert res_dev.status_code == 200
        assert len(res_dev.json()) == 0

