"""
Test suite for VAZIFA 8A: WebSocket Security
"""
import pytest
import asyncio
from datetime import timedelta
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from sqlalchemy import select

from app.core.database import Base, engine, AsyncSessionLocal
from app.models.restaurant import Restaurant
from app.models.table import Table, TableStatus
from app.models.user import User, UserRole
from app.core.security import create_access_token, get_password_hash
from app.websockets.manager import manager
from app.main import app


@pytest.fixture(autouse=True)
async def setup_test_data():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        r1 = await session.get(Restaurant, 1)
        if not r1:
            r1 = Restaurant(id=1, name="Rest 1", slug="rest-1")
            session.add(r1)
        r2 = await session.get(Restaurant, 2)
        if not r2:
            r2 = Restaurant(id=2, name="Rest 2", slug="rest-2")
            session.add(r2)

        # Create Table 101 for rest 1
        res = await session.execute(select(Table).where(Table.id == 101))
        t1 = res.scalar_one_or_none()
        if not t1:
            t1 = Table(
                id=101,
                restaurant_id=1,
                number=1,
                qr_token="qr-token-101",
                status=TableStatus.AVAILABLE,
            )
            session.add(t1)

        # Create Table 201 for rest 2
        res2 = await session.execute(select(Table).where(Table.id == 201))
        t2 = res2.scalar_one_or_none()
        if not t2:
            t2 = Table(
                id=201,
                restaurant_id=2,
                number=1,
                qr_token="qr-token-201",
                status=TableStatus.AVAILABLE,
            )
            session.add(t2)

        # Create Waiter User in Rest 1
        res_u = await session.execute(select(User).where(User.username == "waiter_ws_test"))
        u_waiter = res_u.scalar_one_or_none()
        if not u_waiter:
            u_waiter = User(
                username="waiter_ws_test",
                full_name="Waiter WS Test",
                hashed_password=get_password_hash("pass123"),
                role=UserRole.WAITER,
                restaurant_id=1,
                is_active=True,
            )
            session.add(u_waiter)

        # Create Developer User
        res_dev = await session.execute(select(User).where(User.username == "dev_ws_test"))
        u_dev = res_dev.scalar_one_or_none()
        if not u_dev:
            u_dev = User(
                username="dev_ws_test",
                full_name="Dev WS Test",
                hashed_password=get_password_hash("pass123"),
                role=UserRole.DEVELOPER,
                restaurant_id=None,
                is_active=True,
            )
            session.add(u_dev)

        await session.commit()
    yield


@pytest.mark.anyio
async def test_invalid_token_closes_4401():
    """1: Yaroqsiz yoki muddati o'tgan token guest sifatida ulanmasdan 4401 bilan yopilishi"""
    client = TestClient(app)
    # 1a. Noto'g'ri token
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/api/v1/ws/1?token=invalid_jwt_token_123"):
            pass
    assert exc_info.value.code == 4401

    # 1b. Muddati o'tgan token
    expired_token = create_access_token(
        {"sub": "9999", "role": "waiter"},
        expires_delta=timedelta(seconds=-10),
    )
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect(f"/api/v1/ws/1?token={expired_token}"):
            pass
    assert exc_info.value.code == 4401


@pytest.mark.anyio
async def test_guest_missing_table_id_closes_4403():
    """3: Guest uchun table_id majburiy, aks holda 4403 bilan yopilishi"""
    client = TestClient(app)
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/api/v1/ws/1"):
            pass
    assert exc_info.value.code == 4403


@pytest.mark.anyio
async def test_guest_wrong_restaurant_table_closes_4403():
    """3: Stol boshqa restoranga tegishli bo'lsa 4403 bilan yopilishi"""
    client = TestClient(app)
    # Stol 201 restoran 2 ga tegishli, lekin restoran 1 ga ulanmoqchi
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/api/v1/ws/1?table_id=201"):
            pass
    assert exc_info.value.code == 4403

    # Mavjud bo'lmagan stol
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/api/v1/ws/1?table_id=9999"):
            pass
    assert exc_info.value.code == 4403


@pytest.mark.anyio
async def test_staff_restaurant_mismatch_closes_4403():
    """2: Xodim tokeni uchun user.restaurant_id yo'ldagi restaurant_id ga teng bo'lishi shart, aks holda 4403"""
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(User).where(User.username == "waiter_ws_test"))
        u = res.scalar_one()
        token = create_access_token({"sub": str(u.id), "role": u.role.value})

    client = TestClient(app)
    # Restoran 2 ga ulanishga urinadi (xodim esa restoran 1 da)
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect(f"/api/v1/ws/2?token={token}"):
            pass
    assert exc_info.value.code == 4403

    # O'z restoraniga ulanish muvaffaqiyatli
    with client.websocket_connect(f"/api/v1/ws/1?token={token}") as ws:
        msg = ws.receive_json()
        assert msg["type"] == "connection_established"
        assert msg["role"] == "waiter"


@pytest.mark.anyio
async def test_developer_restaurant_bypass():
    """2: Developer har qanday restaurant_id ga ulanishi mumkin"""
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(User).where(User.username == "dev_ws_test"))
        u = res.scalar_one()
        token = create_access_token({"sub": str(u.id), "role": u.role.value})

    client = TestClient(app)
    with client.websocket_connect(f"/api/v1/ws/999?token={token}") as ws:
        msg = ws.receive_json()
        assert msg["type"] == "connection_established"
        assert msg["role"] == "developer"


@pytest.mark.anyio
async def test_guest_never_receives_broadcast_to_restaurant_or_roles():
    """4: broadcast_to_restaurant va broadcast_to_roles guest ulanishlariga HECH QACHON yubormasin"""
    client = TestClient(app)

    with client.websocket_connect("/api/v1/ws/1?table_id=101") as guest_ws:
        init_msg = guest_ws.receive_json()
        assert init_msg["type"] == "connection_established"
        assert init_msg["role"] == "guest"

        # 1. broadcast_to_restaurant yuborish
        await manager.broadcast_to_restaurant(1, {"type": "secret_internal_info", "data": 123})

        # 2. broadcast_to_roles yuborish
        await manager.broadcast_to_roles(1, ["waiter", "admin"], {"type": "waiter_task", "data": 456})

        # 3. broadcast_to_table yuborish (bu kelishi kerak!)
        await manager.broadcast_to_table(1, 101, {"type": "table_notice", "msg": "Salom"})

        # Guest ga birinchi kelgan xabar table_notice bo'lishi kerak!
        received = guest_ws.receive_json()
        assert received["type"] == "table_notice"
        assert received["msg"] == "Salom"


@pytest.mark.anyio
async def test_broadcast_to_table_sanitizes_sensitive_keys():
    """5: broadcast_to_table da telefon, ofitsiant ulushi, pin va mijoz ma'lumotlari filtrlanishi"""
    client = TestClient(app)

    with client.websocket_connect("/api/v1/ws/1?table_id=101") as guest_ws:
        init_msg = guest_ws.receive_json()
        assert init_msg["type"] == "connection_established"

        # Maxfiy kalitlar bilan xabar
        await manager.broadcast_to_table(1, 101, {
            "type": "order_delivered",
            "order_id": 42,
            "message": "Yetkazildi",
            "phone": "+998901234567",
            "customer_phone": "+998907654321",
            "commission": 15.0,
            "waiter_share": 10000,
            "current_pin": "5432",
            "pin": "9999",
            "customer_name": "Maxfiy Mijoz",
            "nested": {
                "safe_info": "ok",
                "phone": "+998990001122",
                "tip": 5000,
            }
        })

        received = guest_ws.receive_json()
        assert received["type"] == "order_delivered"
        assert received["order_id"] == 42
        assert received["message"] == "Yetkazildi"

        # Maxfiy kalitlar o'chirilgan bo'lishi shart
        assert "phone" not in received
        assert "customer_phone" not in received
        assert "commission" not in received
        assert "waiter_share" not in received
        assert "current_pin" not in received
        assert "pin" not in received
        assert "customer_name" not in received

        # Ichki lug'at ham tozalangan bo'lishi shart
        assert received["nested"]["safe_info"] == "ok"
        assert "phone" not in received["nested"]
        assert "tip" not in received["nested"]
