"""
Test suite for VAZIFA 9A: Stol ochish himoyasi (unlock, scan_qr, rate limiting).
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.database import Base, engine, AsyncSessionLocal
from app.models.restaurant import Restaurant
from app.models.table import Table, TableStatus
from app.models.user import User, UserRole
from app.core.security import create_access_token, get_password_hash
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

        # Create Table 501 for rest 1
        res = await session.execute(select(Table).where(Table.id == 501))
        t1 = res.scalar_one_or_none()
        if not t1:
            t1 = Table(
                id=501,
                restaurant_id=1,
                number=50,
                qr_token="qr-token-501",
                status=TableStatus.AVAILABLE,
                is_unlocked=False,
            )
            session.add(t1)

        # Create Table 502 for rest 2
        res2 = await session.execute(select(Table).where(Table.id == 502))
        t2 = res2.scalar_one_or_none()
        if not t2:
            t2 = Table(
                id=502,
                restaurant_id=2,
                number=50,
                qr_token="qr-token-502",
                status=TableStatus.AVAILABLE,
                is_unlocked=False,
            )
            session.add(t2)

        # Waiter for Rest 1
        res_u1 = await session.execute(select(User).where(User.username == "waiter_rest1_9a"))
        u1 = res_u1.scalar_one_or_none()
        if not u1:
            u1 = User(
                username="waiter_rest1_9a",
                full_name="Waiter Rest 1",
                hashed_password=get_password_hash("pass123"),
                role=UserRole.WAITER,
                restaurant_id=1,
                is_active=True,
                is_approved=True,
            )
            session.add(u1)

        # Waiter for Rest 2
        res_u2 = await session.execute(select(User).where(User.username == "waiter_rest2_9a"))
        u2 = res_u2.scalar_one_or_none()
        if not u2:
            u2 = User(
                username="waiter_rest2_9a",
                full_name="Waiter Rest 2",
                hashed_password=get_password_hash("pass123"),
                role=UserRole.WAITER,
                restaurant_id=2,
                is_active=True,
                is_approved=True,
            )
            session.add(u2)

        await session.commit()
    yield


@pytest.mark.anyio
async def test_unlock_table_requires_auth():
    """POST /tables/{id}/unlock tokensiz 401 berishi kerak"""
    client = TestClient(app)
    resp = client.post("/api/v1/tables/501/unlock")
    assert resp.status_code in (401, 403)


@pytest.mark.anyio
async def test_unlock_table_restaurant_mismatch_forbidden():
    """Boshqa restoran xodimi ochishga urinsa 403 berishi kerak"""
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(User).where(User.username == "waiter_rest2_9a"))
        user = res.scalar_one()
        token = create_access_token(
            data={"sub": str(user.id), "role": user.role.value if hasattr(user.role, "value") else str(user.role), "restaurant_id": user.restaurant_id}
        )

    client = TestClient(app)
    # waiter from Rest 2 trying to unlock table 501 (Rest 1)
    resp = client.post(
        "/api/v1/tables/501/unlock",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403
    assert "Boshqa restoran" in resp.json()["detail"]


@pytest.mark.anyio
async def test_unlock_table_success_matching_restaurant():
    """Shu restoran ofitsianti ochsa muvaffaqiyatli 200 bo'lishi kerak"""
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(User).where(User.username == "waiter_rest1_9a"))
        user = res.scalar_one()
        token = create_access_token(
            data={"sub": str(user.id), "role": user.role.value if hasattr(user.role, "value") else str(user.role), "restaurant_id": user.restaurant_id}
        )

    client = TestClient(app)
    resp = client.post(
        "/api/v1/tables/501/unlock",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["is_unlocked"] is True


@pytest.mark.anyio
async def test_scan_qr_only_uuid_token_no_digit():
    """scan/{x} faqat UUID qr_token bilan ishlashi kerak, oddiy raqam (number) 404 berishi kerak"""
    client = TestClient(app)
    # 1. Oddiy raqam 50 bilan kirish 404 berishi kerak
    resp_digit = client.get("/api/v1/tables/scan/50")
    assert resp_digit.status_code == 404

    # 2. Haqiqiy qr_token bilan kirish 200 berishi kerak va PIN mijozga qaytmasligi kerak
    resp_token = client.get("/api/v1/tables/scan/qr-token-501")
    assert resp_token.status_code == 200
    data = resp_token.json()
    assert data["number"] == 50
    assert data.get("pin") is None
    assert data.get("current_pin") is None
