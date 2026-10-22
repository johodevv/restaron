"""
Unit & Integration tests for VAZIFA 12 (Gigiena):
1. Testlar HAQIQIY bazaga ('restaron.db') yozmasligi (conftest.py tekshiruvi)
2. cleanup_test_data.py vositasi (--dry-run va --apply)
3. tables.py va loyihadagi mojibake ('ðŸ') yo'qligi
4. GET /orders/stale endpointi (12 soatdan beri ochiq buyurtmalar, ruxsatlar)
5. Stol raqamlari (zal ustuni 'room' va takrorlar yo'qligi)
"""
import os
import sys
import tempfile
import sqlite3
import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.security import create_access_token, get_password_hash
from app.models.user import User, UserRole
from app.models.table import Table, TableStatus
from app.models.order import Order, OrderStatus
from app.models.restaurant import Restaurant
from app.core.database import AsyncSessionLocal, engine, Base
from app.main import app


@pytest.fixture(autouse=True)
async def setup_hygiene_db():
    """Vaqtinchalik test bazasida jadvallarni yaratish va test ma'lumotlarini yuklash"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        # Restaurant 1
        r = await session.get(Restaurant, 1)
        if not r:
            session.add(Restaurant(id=1, name="Gigiena Test Rest", slug="gigiena-rest"))

        # Users
        users_to_add = [
            (3001, "admin_h12", UserRole.ADMIN, 1),
            (3002, "cashier_h12", UserRole.CASHIER, 1),
            (3003, "waiter_h12", UserRole.WAITER, 1),
        ]
        for uid, uname, urole, urid in users_to_add:
            u = await session.get(User, uid)
            if not u:
                session.add(
                    User(
                        id=uid,
                        username=uname,
                        full_name=f"User {uname}",
                        hashed_password=get_password_hash("pass12345"),
                        role=urole,
                        restaurant_id=urid,
                        is_active=True,
                        is_approved=True,
                    )
                )

        # Table 77
        t77 = await session.get(Table, 777)
        if not t77:
            session.add(
                Table(
                    id=777,
                    restaurant_id=1,
                    number=77,
                    name="Zal 77",
                    room="Asosiy Zal",
                    capacity=4,
                    qr_token="qr_test_h12_77",
                    status=TableStatus.OCCUPIED,
                )
            )

        # Orders for stale endpoint test:
        # 1. Stale order: 15h ago, unpaid, pending
        ord_stale = await session.get(Order, 3101)
        if not ord_stale:
            session.add(
                Order(
                    id=3101,
                    restaurant_id=1,
                    table_id=777,
                    waiter_id=3003,
                    order_number="#STALE-3101",
                    status=OrderStatus.PENDING,
                    total=125000.0,
                    is_paid=False,
                    created_at=datetime.now(timezone.utc) - timedelta(hours=15, minutes=10),
                )
            )

        # 2. Fresh order: 2h ago, unpaid
        ord_fresh = await session.get(Order, 3102)
        if not ord_fresh:
            session.add(
                Order(
                    id=3102,
                    restaurant_id=1,
                    table_id=777,
                    waiter_id=3003,
                    order_number="#FRESH-3102",
                    status=OrderStatus.PENDING,
                    total=50000.0,
                    is_paid=False,
                    created_at=datetime.now(timezone.utc) - timedelta(hours=2),
                )
            )

        # 3. Paid order: 20h ago, but paid
        ord_paid = await session.get(Order, 3103)
        if not ord_paid:
            session.add(
                Order(
                    id=3103,
                    restaurant_id=1,
                    table_id=777,
                    waiter_id=3003,
                    order_number="#PAID-3103",
                    status=OrderStatus.SERVED,
                    total=90000.0,
                    is_paid=True,
                    created_at=datetime.now(timezone.utc) - timedelta(hours=20),
                )
            )

        # 4. Cancelled order: 18h ago, but cancelled
        ord_canc = await session.get(Order, 3104)
        if not ord_canc:
            session.add(
                Order(
                    id=3104,
                    restaurant_id=1,
                    table_id=777,
                    waiter_id=3003,
                    order_number="#CANC-3104",
                    status=OrderStatus.CANCELLED,
                    total=40000.0,
                    is_paid=False,
                    created_at=datetime.now(timezone.utc) - timedelta(hours=18),
                )
            )

        await session.commit()
    yield


@pytest.mark.anyio
async def test_1_database_url_is_isolated():
    """1. Testlar vaqtinchalik bazaga ulangan, 'restaron.db' ga emas"""
    assert "restaron.db" not in settings.DATABASE_URL
    assert "restaron.db" not in os.environ.get("DATABASE_URL", "")
    assert "restaron_test_" in settings.DATABASE_URL


@pytest.mark.anyio
async def test_2_tables_py_and_project_no_mojibake():
    """2. tables.py va backend/app ichida mojibake ('ðŸ') yo'qligini tekshirish"""
    backend_app_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app"))
    for root, dirs, files in os.walk(backend_app_dir):
        for f in files:
            if f.endswith(".py"):
                fpath = os.path.join(root, f)
                with open(fpath, "r", encoding="utf-8") as fp:
                    content = fp.read()
                    assert "ðŸ" not in content, f"Mojibake found in {fpath}"


@pytest.mark.anyio
async def test_3_tables_room_column_no_duplicates():
    """3. Table modelidagi zal ustuni 'room' ekanligi va dublikatlar yo'qligi"""
    assert hasattr(Table, "room")
    assert Table.room.key == "room"

    # Haqiqiy restaron.db faylidagi dublikatlarni tekshirish
    real_db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "restaron.db"))
    if os.path.exists(real_db_path):
        conn = sqlite3.connect(real_db_path)
        c = conn.cursor()
        c.execute("""
            SELECT restaurant_id, coalesce(room, ''), number, count(*) as cnt
            FROM tables
            GROUP BY restaurant_id, coalesce(room, ''), number
            HAVING cnt > 1
        """)
        duplicates = c.fetchall()
        conn.close()
        assert len(duplicates) == 0, f"Found table duplicates: {duplicates}"


@pytest.mark.anyio
async def test_4_cleanup_test_data_script():
    """4. cleanup_test_data.py skripti dry-run va apply rejimlarida to'g'ri ishlashi"""
    from tools.cleanup_test_data import find_test_data, apply_cleanup

    temp_db = os.path.join(tempfile.gettempdir(), f"cleanup_unit_test_{datetime.now().strftime('%f')}.db")
    conn = sqlite3.connect(temp_db)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE orders (
            id INTEGER PRIMARY KEY,
            order_number TEXT,
            restaurant_id INTEGER,
            table_id INTEGER,
            waiter_id INTEGER,
            customer_name TEXT,
            status TEXT,
            total REAL,
            is_paid BOOLEAN,
            created_at TIMESTAMP
        )
    """)
    c.execute("""
        CREATE TABLE order_items (
            id INTEGER PRIMARY KEY,
            order_id INTEGER,
            menu_item_id INTEGER,
            quantity REAL,
            total_price REAL
        )
    """)
    c.execute("""
        CREATE TABLE receipt_archives (
            id INTEGER PRIMARY KEY,
            order_id INTEGER,
            receipt_number TEXT,
            total_amount REAL,
            created_at TIMESTAMP
        )
    """)
    c.execute("""
        CREATE TABLE print_jobs (
            id INTEGER PRIMARY KEY,
            order_id INTEGER
        )
    """)

    # Test va haqiqiy ma'lumotlar
    c.execute("INSERT INTO orders VALUES (101, '#T-TEST-123', 1, 1, 1, 'Test Mijoz', 'pending', 50000, 0, '2026-10-20 10:00:00')")
    c.execute("INSERT INTO orders VALUES (102, '#R1-0102', 1, 1, 1, 'Haqiqiy Mijoz', 'closed', 80000, 1, '2026-10-20 11:00:00')")
    c.execute("INSERT INTO order_items VALUES (1, 101, 5, 2, 50000)")
    c.execute("INSERT INTO order_items VALUES (2, 102, 6, 1, 80000)")
    c.execute("INSERT INTO receipt_archives VALUES (1, 101, 'BILL_TEST-123', 50000, '2026-10-20 10:05:00')")
    c.execute("INSERT INTO receipt_archives VALUES (2, 102, 'BILL_REAL-102', 80000, '2026-10-20 11:05:00')")
    conn.commit()

    # Dry-run qidiruv
    data = find_test_data(conn)
    assert len(data["orders"]) == 1
    assert data["orders"][0][0] == 101
    assert data["items_count"] == 1
    assert len(data["receipts"]) == 1
    assert data["receipts"][0][0] == 1

    # Apply o'chirish
    del_orders, del_items, del_receipts = apply_cleanup(conn, data)
    assert del_orders == 1
    assert del_items == 1
    assert del_receipts == 1

    # Haqiqiy ma'lumotlar qolganligini tekshirish
    c.execute("SELECT count(*) FROM orders")
    assert c.fetchone()[0] == 1
    c.execute("SELECT id FROM orders")
    assert c.fetchone()[0] == 102

    conn.close()
    if os.path.exists(temp_db):
        os.remove(temp_db)


@pytest.mark.anyio
async def test_5_stale_orders_endpoint():
    """5. GET /api/v1/orders/stale endpointi, ruxsatlar va yosh hisoblash"""
    admin_token = create_access_token({"sub": "3001", "role": "admin", "restaurant_id": 1})
    cashier_token = create_access_token({"sub": "3002", "role": "cashier", "restaurant_id": 1})
    waiter_token = create_access_token({"sub": "3003", "role": "waiter", "restaurant_id": 1})

    with TestClient(app) as client:
        # 1. Waiter -> 403
        r_waiter = client.get("/api/v1/orders/stale", headers={"Authorization": f"Bearer {waiter_token}"})
        assert r_waiter.status_code == 403

        # 2. Cashier -> 200
        r_cashier = client.get("/api/v1/orders/stale", headers={"Authorization": f"Bearer {cashier_token}"})
        assert r_cashier.status_code == 200

        # 3. Admin -> 200
        r_admin = client.get("/api/v1/orders/stale", headers={"Authorization": f"Bearer {admin_token}"})
        assert r_admin.status_code == 200
        stale_data = r_admin.json()

        stale_numbers = [item["order_number"] for item in stale_data]
        assert "#STALE-3101" in stale_numbers
        assert "#FRESH-3102" not in stale_numbers
        assert "#PAID-3103" not in stale_numbers
        assert "#CANC-3104" not in stale_numbers

        # Maydonlar tekshiruvi: id, order_number, stol, ofitsiant, summa, yoshi
        item = next(x for x in stale_data if x["order_number"] == "#STALE-3101")
        assert item["id"] == 3101
        assert item["stol"] == "77"
        assert item["ofitsiant"] == "User waiter_h12"
        assert item["summa"] == 125000.0
        assert "15 soat" in item["yoshi"]
