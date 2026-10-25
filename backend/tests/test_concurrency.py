"""
RestAron - VAZIFA 16: Poyga holatlari testlari (Concurrency Test Suite)
Fayl: backend/tests/test_concurrency.py

Qamrab olingan holatlar:
a) bir stolga 20 ta bir vaqtdagi waiter-create -> shu stolda aynan 1 ta ochiq buyurtma, taomlar yig'indisi to'g'ri;
b) 20 ta bir vaqtdagi delta=+1 -> miqdor aynan +20;
c) 5 ta bir vaqtdagi send-to-kitchen -> har taom uchun bitta print_job;
d) 5 ta bir vaqtdagi checkout -> faqat bittasi 200, qolganlari 409, bitta Debt;
e) waiter token bilan status=paid -> 400/403;
f) waiter bilan /tables/{id}/clear (ochiq hisob bor) -> 409;
g) tokensiz WebSocket restoran kanalida order xabarini OLMASLIGI.
"""
import pytest
import asyncio
from datetime import datetime, timezone
import httpx
from httpx import AsyncClient, ASGITransport
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from sqlalchemy import select, func, and_

from app.core.database import Base, engine, AsyncSessionLocal
from app.models.restaurant import Restaurant, RestaurantSettings
from app.models.user import User, UserRole
from app.models.table import Table, TableStatus
from app.models.menu import Category, MenuItem
from app.models.order import Order, OrderItem, OrderStatus
from app.models.debt import Debt
from app.models.print_job import PrintJob
from app.core.security import create_access_token, get_password_hash
from app.websockets.manager import manager
from app.main import app


@pytest.fixture(autouse=True)
async def setup_concurrency_data():
    """Test ma'lumotlarini tayyorlash"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        # 1. Restoran va sozlamalar
        rest = await session.get(Restaurant, 1)
        if not rest:
            rest = Restaurant(id=1, name="Dunyo Choyxonasi Concurrency", slug="dunyo-conc")
            session.add(rest)

        settings = await session.get(RestaurantSettings, 1)
        if not settings:
            settings = RestaurantSettings(
                restaurant_id=1,
                service_fee_percent=10.0,
                printer_kitchen1_name="XP-Kitchen1",
                printer_kitchen2_name="XP-Kitchen2",
                printer_bar_name="XP-Bar",
                printer_customer_name="XP-Customer",
                auto_print_kitchen=True,
                auto_print_customer_bill=True,
            )
            session.add(settings)
        else:
            settings.printer_kitchen1_name = "XP-Kitchen1"
            settings.printer_kitchen2_name = "XP-Kitchen2"
            settings.printer_bar_name = "XP-Bar"
            settings.printer_customer_name = "XP-Customer"
            settings.auto_print_kitchen = True

        # 2. Foydalanuvchilar (waiter, admin, cashier)
        users_def = [
            (3001, "waiter_conc", UserRole.WAITER, 1),
            (3002, "admin_conc", UserRole.ADMIN, 1),
            (3003, "cashier_conc", UserRole.CASHIER, 1),
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

        # 3. Kategoriya va Menyudagi taomlar
        cat = await session.get(Category, 301)
        if not cat:
            cat = Category(id=301, restaurant_id=1, name="Milliy Taomlar", sort_order=1)
            session.add(cat)

        dish1 = await session.get(MenuItem, 3001)
        if not dish1:
            dish1 = MenuItem(
                id=3001,
                category_id=301,
                name="Tandir Somsa",
                name_cyrillic="Тандир Сомса",
                price=15000.0,
                is_available=True,
                kitchen_station="hot_kitchen",
            )
            session.add(dish1)
        else:
            dish1.is_available = True
            dish1.is_stop_list = False
            dish1.kitchen_station = "hot_kitchen"

        dish2 = await session.get(MenuItem, 3002)
        if not dish2:
            dish2 = MenuItem(
                id=3002,
                category_id=301,
                name="Moxito Bar",
                name_cyrillic="Мохито Бар",
                price=20000.0,
                is_available=True,
                kitchen_station="bar",
            )
            session.add(dish2)
        else:
            dish2.is_available = True
            dish2.is_stop_list = False
            dish2.kitchen_station = "bar"

        # 4. Sinov stollari (301..307)
        for tbl_id in range(301, 308):
            tbl = await session.get(Table, tbl_id)
            if not tbl:
                tbl = Table(
                    id=tbl_id,
                    restaurant_id=1,
                    number=tbl_id,
                    capacity=4,
                    room="Asosiy Zal",
                    qr_token=f"qr-conc-{tbl_id}",
                    status=TableStatus.AVAILABLE,
                )
                session.add(tbl)
            else:
                tbl.status = TableStatus.AVAILABLE
                tbl.restaurant_id = 1

        await session.commit()
    yield
    await engine.dispose()


@pytest.mark.anyio
async def test_a_concurrent_waiter_create_single_order_and_correct_sum():
    """
    a) Bir stolga 20 ta bir vaqtdagi waiter-create:
       - Shu stolda aynan 1 ta ochiq buyurtma qolishi kerak (dublikat buyurtma yaratilmasin).
       - Buyurtmadagi taomlar yig'indisi aynan 20 ta bo'lishi kerak.
    """
    table_id = 301
    waiter_token = create_access_token({"sub": "3001", "role": "waiter"})
    headers = {"Authorization": f"Bearer {waiter_token}"}
    payload = {
        "restaurant_id": 1,
        "table_id": table_id,
        "order_type": "dine_in",
        "items": [{"menu_item_id": 3001, "quantity": 1}],
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 20 ta parallel waiter-create so'rovi
        tasks = [
            client.post("/api/v1/orders/waiter-create", json=payload, headers=headers)
            for _ in range(20)
        ]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

    # Barcha so'rovlar muvaffaqiyatli (200 yoki 201) yakunlanganligini tekshiramiz
    success_codes = [r.status_code for r in responses if isinstance(r, httpx.Response)]
    assert len(success_codes) == 20, f"Barcha so'rovlar javob berishi kerak: {responses}"
    assert all(code in (200, 201) for code in success_codes), f"Xato kodlar: {success_codes}"

    # Bazani tekshirish:
    async with AsyncSessionLocal() as session:
        # 1. Shu stolda aynan 1 ta ochiq (to'lanmagan) buyurtma bo'lishi shart
        res = await session.execute(
            select(Order).where(
                Order.table_id == table_id,
                Order.is_paid == False,
                Order.status.notin_([OrderStatus.PAID, OrderStatus.CANCELLED]),
            )
        )
        open_orders = res.scalars().all()
        assert len(open_orders) == 1, (
            f"Kutilgan 1 ta ochiq buyurtma, lekin {len(open_orders)} ta ochilgan! (Order IDs: {[o.id for o in open_orders]})"
        )

        the_order = open_orders[0]

        # 2. Taomlar yig'indisi aynan 20 ta bo'lishi shart
        items_res = await session.execute(
            select(OrderItem).where(OrderItem.order_id == the_order.id)
        )
        order_items = items_res.scalars().all()
        total_quantity = sum(item.quantity for item in order_items)
        assert total_quantity == 20, (
            f"Taomlar yig'indisi 20 bo'lishi kerak, ammo {total_quantity} bo'ldi! "
            f"Items: {[(i.menu_item_id, i.quantity) for i in order_items]}"
        )


@pytest.mark.anyio
async def test_b_concurrent_delta_plus_one_exact_quantity():
    """
    b) 20 ta bir vaqtdagi delta=+1 so'rovi:
       - Boshlang'ich miqdor = 1.
       - 20 ta bir vaqtdagi delta=+1 dan keyin yakuniy miqdor aynan 21 (+20) bo'lishi shart.
    """
    table_id = 302
    waiter_token = create_access_token({"sub": "3001", "role": "waiter"})
    headers = {"Authorization": f"Bearer {waiter_token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Boshlang'ich buyurtma ochamiz
        init_resp = await client.post(
            "/api/v1/orders/waiter-create",
            json={
                "restaurant_id": 1,
                "table_id": table_id,
                "order_type": "dine_in",
                "items": [{"menu_item_id": 3001, "quantity": 1}],
            },
            headers=headers,
        )
        assert init_resp.status_code in (200, 201)
        order_data = init_resp.json()
        order_id = order_data["id"]
        item_id = order_data["items"][0]["id"]

        # 20 ta bir vaqtdagi delta=+1 so'rovi
        tasks = [
            client.patch(
                f"/api/v1/orders/{order_id}/items/{item_id}/delta",
                json={"delta": 1},
                headers=headers,
            )
            for _ in range(20)
        ]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

    for idx, r in enumerate(responses):
        if isinstance(r, Exception):
            print(f"Task {idx} EXCEPTION: {type(r).__name__}: {r}")
        elif r.status_code != 200:
            print(f"Task {idx} HTTP {r.status_code}: {r.text}")

    success_codes = [r.status_code for r in responses if isinstance(r, httpx.Response) and r.status_code == 200]
    assert len(success_codes) == 20, f"20 tadan {len(success_codes)} tasi muvaffaqiyatli bo'ldi. Responses: {responses}"

    # Baza holatini tekshirish
    async with AsyncSessionLocal() as session:
        it = await session.get(OrderItem, item_id)
        assert it is not None
        assert it.quantity == 21, f"Miqdor 21 bo'lishi kerak, lekin {it.quantity} chiqdi!"


@pytest.mark.anyio
async def test_c_concurrent_send_to_kitchen_single_print_job_per_station():
    """
    c) 5 ta bir vaqtdagi send-to-kitchen:
       - Oshxonaga yuborishda poyga holati bo'lmasligi kerak.
       - Har bir taom / stansiya uchun ortiqcha dublikat emas, aynan 1 ta chop etish vazifasi (print_job) yaratiladi.
    """
    table_id = 303
    waiter_token = create_access_token({"sub": "3001", "role": "waiter"})
    headers = {"Authorization": f"Bearer {waiter_token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 2 ta taom bilan buyurtma ochamiz: biri oshxona (3001), biri bar (3002)
        init_resp = await client.post(
            "/api/v1/orders/waiter-create",
            json={
                "restaurant_id": 1,
                "table_id": table_id,
                "order_type": "dine_in",
                "items": [
                    {"menu_item_id": 3001, "quantity": 2},
                    {"menu_item_id": 3002, "quantity": 1},
                ],
            },
            headers=headers,
        )
        assert init_resp.status_code in (200, 201)
        order_id = init_resp.json()["id"]

        # 5 ta bir vaqtdagi send-to-kitchen so'rovi
        tasks = [
            client.post(f"/api/v1/orders/{order_id}/send-to-kitchen", headers=headers)
            for _ in range(5)
        ]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

    success_codes = [r.status_code for r in responses if isinstance(r, httpx.Response)]
    assert len(success_codes) == 5
    assert all(code == 200 for code in success_codes)

    # PrintJob larni tekshirish:
    # 2 ta stansiya (kitchen va bar) mavjud, har biri uchun aynan 1 tadan jami 2 ta print_job bo'lishi shart
    async with AsyncSessionLocal() as session:
        pj_res = await session.execute(
            select(PrintJob).where(PrintJob.order_id == order_id)
        )
        jobs = pj_res.scalars().all()
        # Dublikat bo'lmasligi kerak (5 x 2 = 10 emas, aynan 2 ta!)
        assert len(jobs) == 2, f"Dublikat print_job lar paydo bo'ldi! Kutilgan 2, topilgan: {len(jobs)}"
        ticket_types = {j.ticket_type for j in jobs}
        assert "kitchen" in ticket_types or "bar" in ticket_types


@pytest.mark.anyio
async def test_d_concurrent_checkout_one_succeeds_four_conflict_and_single_debt():
    """
    d) 5 ta bir vaqtdagi checkout (nasiya / qarz to'lovi):
       - Faqat bittasi 200 OK qaytarishi kerak.
       - Qolgan 4 tasi 409 Conflict qaytarishi kerak ("allaqachon to'langan").
       - Bazada aynan bitta Debt (qarz) yozuvi yaratilishi shart.
    """
    table_id = 304
    cashier_token = create_access_token({"sub": "3003", "role": "cashier"})
    headers = {"Authorization": f"Bearer {cashier_token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Buyurtma yaratamiz
        init_resp = await client.post(
            "/api/v1/orders/waiter-create",
            json={
                "restaurant_id": 1,
                "table_id": table_id,
                "order_type": "dine_in",
                "items": [{"menu_item_id": 3001, "quantity": 2}],
            },
            headers=headers,
        )
        assert init_resp.status_code in (200, 201)
        order_id = init_resp.json()["id"]

        checkout_payload = {
            "payment_method": "debt",
            "debt_customer_name": "Qarzdor Bobur",
            "debt_customer_phone": "+998901234567",
            "debt_amount": 33000.0,
            "debt_note": "Nasiya tekshiruvi",
        }

        # 5 ta bir vaqtdagi checkout so'rovi
        tasks = [
            client.post(
                f"/api/v1/orders/{order_id}/checkout",
                json=checkout_payload,
                headers=headers,
            )
            for _ in range(5)
        ]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

    status_codes = [r.status_code for r in responses if isinstance(r, httpx.Response)]
    assert len(status_codes) == 5

    count_200 = status_codes.count(200)
    count_409 = status_codes.count(409)

    assert count_200 == 1, f"Faqat bitta checkout 200 qaytarishi kerak, ammo {count_200} ta 200 bo'ldi! Kodlar: {status_codes}"
    assert count_409 == 4, f"Qolgan 4 tasi 409 Conflict qaytarishi kerak, ammo {count_409} ta 409 bo'ldi! Kodlar: {status_codes}"

    # Bazada qarz va buyurtma holatini tekshirish
    async with AsyncSessionLocal() as session:
        debt_res = await session.execute(
            select(Debt).where(Debt.order_id == order_id)
        )
        debts = debt_res.scalars().all()
        assert len(debts) == 1, f"Aynan 1 ta Debt yaratilishi kerak, topilgan: {len(debts)}"

        order = await session.get(Order, order_id)
        assert order.is_paid is True
        assert order.status == OrderStatus.PAID


@pytest.mark.anyio
async def test_e_waiter_token_cannot_set_status_paid():
    """
    e) Ofitsiant tokeni bilan status=paid so'rovi:
       - Buyurtma statusini ofitsiant 'paid' ga o'zgartira olmasligi kerak (400 yoki 403 qaytishi shart).
    """
    table_id = 305
    waiter_token = create_access_token({"sub": "3001", "role": "waiter"})
    headers = {"Authorization": f"Bearer {waiter_token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        init_resp = await client.post(
            "/api/v1/orders/waiter-create",
            json={
                "restaurant_id": 1,
                "table_id": table_id,
                "order_type": "dine_in",
                "items": [{"menu_item_id": 3001, "quantity": 1}],
            },
            headers=headers,
        )
        assert init_resp.status_code in (200, 201)
        order_id = init_resp.json()["id"]

        resp = await client.patch(
            f"/api/v1/orders/{order_id}/status",
            json={"status": "paid"},
            headers=headers,
        )
        assert resp.status_code in (400, 403), f"Kutilgan 400 yoki 403, lekin {resp.status_code} qaytdi: {resp.text}"

    # Baza holatini tekshirish
    async with AsyncSessionLocal() as session:
        order = await session.get(Order, order_id)
        assert order.is_paid is False
        assert order.status != OrderStatus.PAID


@pytest.mark.anyio
async def test_f_waiter_cannot_clear_table_with_open_orders():
    """
    f) Ofitsiant bilan /tables/{id}/clear chaqirilganda, agar stolda ochiq hisob bo'lsa:
       - 409 Conflict qaytarishi shart ("Stolda ochiq hisob bor").
    """
    table_id = 306
    waiter_token = create_access_token({"sub": "3001", "role": "waiter"})
    headers = {"Authorization": f"Bearer {waiter_token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Stolda ochiq buyurtma ochamiz
        init_resp = await client.post(
            "/api/v1/orders/waiter-create",
            json={
                "restaurant_id": 1,
                "table_id": table_id,
                "order_type": "dine_in",
                "items": [{"menu_item_id": 3001, "quantity": 1}],
            },
            headers=headers,
        )
        assert init_resp.status_code in (200, 201)

        # Ofitsiant stolni majburiy tozalashga urinadi
        clear_resp = await client.post(
            f"/api/v1/tables/{table_id}/clear",
            headers=headers,
        )
        assert clear_resp.status_code == 409, f"Kutilgan 409, lekin {clear_resp.status_code} qaytdi: {clear_resp.text}"
        detail = clear_resp.json().get("detail", "")
        assert "ochiq hisob" in detail.lower() or "409" in str(clear_resp.status_code)


@pytest.mark.anyio
async def test_g_tokenless_websocket_never_receives_restaurant_order_broadcast():
    """
    g) Tokensiz WebSocket ulanish:
       - Tokensiz va table_id siz restoran kanaliga ulanish darhol 4403 bilan rad etiladi.
       - Faqat table_id bilan ulangan tokensiz guest restoranga yoki ofitsiantlarga
         yuborilgan buyurtma ('new_order' / 'order_created') xabarlarini UMUMAN OLMASLIGI shart.
    """
    client = TestClient(app)

    # 1. Tokensiz restoran kanaliga ulanishga urinish -> 4403 bilan yopilishi shart
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/api/v1/ws/1") as rejected:
            rejected.receive_json()
    assert exc_info.value.code == 4403

    # 2. Stol orqali tokensiz guest sifatida ulanish
    with client.websocket_connect("/api/v1/ws/1?table_id=307") as guest_ws:
        init_msg = guest_ws.receive_json()
        assert init_msg["type"] == "connection_established"
        assert init_msg["role"] == "guest"

        # Restoranga va xodimlarga maxfiy buyurtma xabarlarini yuboramiz
        await manager.broadcast_to_restaurant(
            1,
            {"type": "new_order", "order_id": 8888, "info": "Ichki buyurtma"}
        )
        await manager.broadcast_to_roles(
            1,
            ["waiter", "admin", "chef"],
            {"type": "order_created", "order_id": 8888, "items": ["Somsa"]}
        )

        # Faqat shu stolga tegishli xabar yuboramiz
        await manager.broadcast_to_table(
            1,
            307,
            {"type": "table_notice", "message": "Sizning buyurtmangiz qabul qilindi"}
        )

        # Guest ga faqat stol xabari kelishi shart, restoran yoki xodimlar buyurtmasi EMAS!
        received = guest_ws.receive_json()
        assert received["type"] == "table_notice", (
            f"Tokensiz mijoz restoran xabarini oldi! Qabul qilingan xabar: {received}"
        )
        assert received["message"] == "Sizning buyurtmangiz qabul qilindi"
