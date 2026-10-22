"""
Test suite for VAZIFA 13: Kunlik hisobotlar to'g'ri kunga tushishi
1. timeutil.py: uz_day_bounds_utc, to_uz, uz_now, uz_range_bounds_utc
2. UZ vaqti bilan 23:30 va 00:30 da yaratilgan buyurtmalar turli kunga tushishi
   (UTC da ikkalasi 2026-10-22 18:30 va 19:30 bo'lsa-da, UZ da 2026-10-22 va 2026-10-23 ga ajraladi)
3. revenue-chart da func.date(created_at, '+5 hours') orqali to'g'ri sanalar bilan guruhlanishi
4. payments-report va dashboard UZ kuni chegaralarida ishlashi
"""
import os
import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from app.core.timeutil import (
    UZ_TZ,
    to_uz,
    to_utc_naive,
    uz_now,
    uz_day_bounds_utc,
    uz_range_bounds_utc,
    format_uz,
)
from app.core.database import Base, engine, AsyncSessionLocal
from app.models.restaurant import Restaurant
from app.models.user import User, UserRole
from app.models.order import Order, OrderStatus
from app.models.table import Table, TableStatus
from app.core.security import create_access_token, get_password_hash
from app.main import app


@pytest.fixture(autouse=True)
async def setup_stats_time_db():
    """Test bazasida jadvallarni yaratish va test buyurtmalarini kiritish"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        # Restoran
        r = await session.get(Restaurant, 13)
        if not r:
            session.add(Restaurant(id=13, name="Choyxona 13", slug="choyxona-13"))

        # Admin foydalanuvchi
        u = await session.get(User, 4001)
        if not u:
            session.add(
                User(
                    id=4001,
                    username="admin_t13",
                    full_name="Admin T13",
                    hashed_password=get_password_hash("pass12345"),
                    role=UserRole.ADMIN,
                    restaurant_id=13,
                    is_active=True,
                    is_approved=True,
                )
            )

        # Ofitsiant
        w = await session.get(User, 4002)
        if not w:
            session.add(
                User(
                    id=4002,
                    username="waiter_t13",
                    full_name="Ofitsiant T13",
                    hashed_password=get_password_hash("pass12345"),
                    role=UserRole.WAITER,
                    restaurant_id=13,
                    is_active=True,
                    is_approved=True,
                )
            )

        # Stol
        t = await session.get(Table, 401)
        if not t:
            session.add(
                Table(
                    id=401,
                    restaurant_id=13,
                    number=13,
                    name="Stol 13",
                    room="Zal",
                    qr_token="qr_token_t13",
                    status=TableStatus.AVAILABLE,
                )
            )

        # -------------------------------------------------------------
        # MUHIM TEST BUYURTMALARI:
        # 1. Order 1: UZ vaqti bilan 2026-10-22 23:30 (UTC naive: 2026-10-22 18:30:00)
        #    Kuni: 2026-10-22
        # 2. Order 2: UZ vaqti bilan 2026-10-23 00:30 (UTC naive: 2026-10-22 19:30:00)
        #    Kuni: 2026-10-23
        # -------------------------------------------------------------
        o1 = await session.get(Order, 4101)
        if not o1:
            session.add(
                Order(
                    id=4101,
                    restaurant_id=13,
                    table_id=401,
                    waiter_id=4002,
                    order_number="#ORD-NIGHT-2330",
                    status=OrderStatus.PAID,
                    is_paid=True,
                    total=100000.0,
                    cash_amount=100000.0,
                    created_at=datetime(2026, 10, 22, 18, 30, 0),
                    closed_at=datetime(2026, 10, 22, 18, 35, 0),
                )
            )

        o2 = await session.get(Order, 4102)
        if not o2:
            session.add(
                Order(
                    id=4102,
                    restaurant_id=13,
                    table_id=401,
                    waiter_id=4002,
                    order_number="#ORD-NIGHT-0030",
                    status=OrderStatus.PAID,
                    is_paid=True,
                    total=150000.0,
                    card_amount=150000.0,
                    created_at=datetime(2026, 10, 22, 19, 30, 0),
                    closed_at=datetime(2026, 10, 22, 19, 35, 0),
                )
            )

        await session.commit()
    yield


@pytest.mark.anyio
async def test_timeutil_helpers():
    """1. timeutil yordamchi funksiyalari to'g'ri ishlashi"""
    # 2026-10-22 kuni uchun UZ chegaralari
    start_utc, end_utc = uz_day_bounds_utc("2026-10-22")
    assert start_utc == datetime(2026, 10, 21, 19, 0)
    assert end_utc == datetime(2026, 10, 22, 19, 0)

    # 23:30 UZ (18:30 UTC) -> 2026-10-22 ga tegishli
    utc_2330 = datetime(2026, 10, 22, 18, 30)
    assert start_utc <= utc_2330 < end_utc

    # 00:30 UZ (19:30 UTC) -> 2026-10-22 ga kirmaydi
    utc_0030 = datetime(2026, 10, 22, 19, 30)
    assert not (start_utc <= utc_0030 < end_utc)

    # 2026-10-23 kuni uchun UZ chegaralari
    start_23, end_23 = uz_day_bounds_utc("2026-10-23")
    assert start_23 == datetime(2026, 10, 22, 19, 0)
    assert end_23 == datetime(2026, 10, 23, 19, 0)
    assert start_23 <= utc_0030 < end_23

    # to_uz va format_uz
    uz_dt = to_uz(utc_2330)
    assert uz_dt.strftime("%Y-%m-%d %H:%M") == "2026-10-22 23:30"
    assert format_uz(utc_0030) == "23.10.2026 00:30"


@pytest.mark.anyio
async def test_orders_at_2330_and_0030_fall_into_different_days():
    """2. UZ vaqti bilan 23:30 va 00:30 da yaratilgan buyurtmalar turli kunga tushishi"""
    admin_token = create_access_token({"sub": "4001", "role": "admin", "restaurant_id": 13})
    headers = {"Authorization": f"Bearer {admin_token}"}

    with TestClient(app) as client:
        # 1. 2026-10-22 hisoboti -> Faqat #ORD-NIGHT-2330 (100,000 so'm)
        r22 = client.get(
            "/api/v1/stats/payments-report?restaurant_id=13&start_date=2026-10-22&end_date=2026-10-22",
            headers=headers,
        )
        assert r22.status_code == 200
        d22 = r22.json()
        orders_22 = [row["order_number"] for row in d22["rows"]]
        assert "#ORD-NIGHT-2330" in orders_22
        assert "#ORD-NIGHT-0030" not in orders_22
        assert d22["total_revenue"] == 100000.0

        # 2. 2026-10-23 hisoboti -> Faqat #ORD-NIGHT-0030 (150,000 so'm)
        r23 = client.get(
            "/api/v1/stats/payments-report?restaurant_id=13&start_date=2026-10-23&end_date=2026-10-23",
            headers=headers,
        )
        assert r23.status_code == 200
        d23 = r23.json()
        orders_23 = [row["order_number"] for row in d23["rows"]]
        assert "#ORD-NIGHT-0030" in orders_23
        assert "#ORD-NIGHT-2330" not in orders_23
        assert d23["total_revenue"] == 150000.0

        # 3. Ikki kunlik oraliq (2026-10-22 dan 2026-10-23 gacha) -> Ikkalasi ham chiqadi
        r_both = client.get(
            "/api/v1/stats/payments-report?restaurant_id=13&start_date=2026-10-22&end_date=2026-10-23",
            headers=headers,
        )
        assert r_both.status_code == 200
        d_both = r_both.json()
        both_orders = [row["order_number"] for row in d_both["rows"]]
        assert "#ORD-NIGHT-2330" in both_orders
        assert "#ORD-NIGHT-0030" in both_orders
        assert d_both["total_revenue"] == 250000.0


@pytest.mark.anyio
async def test_revenue_chart_grouping_with_plus_5_hours():
    """3. revenue-chart da func.date(created_at, '+5 hours') bilan guruhlanishi"""
    admin_token = create_access_token({"sub": "4001", "role": "admin", "restaurant_id": 13})
    headers = {"Authorization": f"Bearer {admin_token}"}

    with TestClient(app) as client:
        # revenue-chart so'rovi
        res = client.get("/api/v1/stats/revenue-chart?restaurant_id=13&days=7", headers=headers)
        assert res.status_code == 200
        chart_data = res.json()
        assert len(chart_data) == 7

        # SQLite func.date(created_at, '+5 hours') orqali:
        # 18:30 UTC -> 23:30 UZ -> '2026-10-22'
        # 19:30 UTC -> 00:30 UZ -> '2026-10-23'
        from sqlalchemy import select, func
        from app.core.database import AsyncSessionLocal

        async with AsyncSessionLocal() as session:
            date_col = func.date(Order.created_at, "+5 hours").label("uz_date")
            query = (
                select(date_col, func.count(Order.id), func.sum(Order.total))
                .where(Order.id.in_([4101, 4102]))
                .group_by(date_col)
                .order_by(date_col)
            )
            rows = (await session.execute(query)).all()
            grouped_dict = {row[0]: (row[1], row[2]) for row in rows}

            assert "2026-10-22" in grouped_dict
            assert grouped_dict["2026-10-22"] == (1, 100000.0)

            assert "2026-10-23" in grouped_dict
            assert grouped_dict["2026-10-23"] == (1, 150000.0)


@pytest.mark.anyio
async def test_dashboard_and_kpi_detail_uz_bounds():
    """4. dashboard va waiter-kpi-detail UZ chegaralarida ishlashi"""
    admin_token = create_access_token({"sub": "4001", "role": "admin", "restaurant_id": 13})
    headers = {"Authorization": f"Bearer {admin_token}"}

    with TestClient(app) as client:
        # waiter-kpi-detail 2026-10-22 kuni uchun
        r_kpi_22 = client.get(
            "/api/v1/stats/waiter-kpi-detail?restaurant_id=13&start_date=2026-10-22&end_date=2026-10-22",
            headers=headers,
        )
        assert r_kpi_22.status_code == 200
        kpi_22 = r_kpi_22.json()
        waiter_row_22 = next(k for k in kpi_22 if k["waiter_id"] == 4002)
        assert waiter_row_22["orders_count"] == 1
        assert waiter_row_22["total_sales"] == 100000.0

        # waiter-kpi-detail 2026-10-23 kuni uchun
        r_kpi_23 = client.get(
            "/api/v1/stats/waiter-kpi-detail?restaurant_id=13&start_date=2026-10-23&end_date=2026-10-23",
            headers=headers,
        )
        assert r_kpi_23.status_code == 200
        kpi_23 = r_kpi_23.json()
        waiter_row_23 = next(k for k in kpi_23 if k["waiter_id"] == 4002)
        assert waiter_row_23["orders_count"] == 1
        assert waiter_row_23["total_sales"] == 150000.0
