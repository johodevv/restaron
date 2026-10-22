"""
Test suite for VAZIFA 10A: Foydalanuvchilar boshqaruvi
1. create_user: admin faqat waiter, chef, cashier yarata olsin. 'admin' va 'developer' faqat developer (aks holda 403).
2. get/update/delete/approve: admin faqat o'z restorani (user.restaurant_id == current_user.restaurant_id); developer hammasi. Admin developer ga tegolmasin (403).
3. PATCH /users/{id}/password: body {new_password: str, min_length=8}; admin (o'z restorani) yoki developer; parol xeshlansin; tokenlar bekor qilinsin (revoke_user_tokens); audit 'user_password_reset'. Parol hech qayerda log qilinmasin.
4. delete_user: qattiq o'chirish o'rniga is_active=False va tokenlarni bekor qil; javob: Foydalanuvchi nofaol qilindi. Oxirgi faol adminni nofaol qilishga yo'l qo'yma (400). O'zini o'zi nofaol qila olmasin (400).
5. Login: nofaol foydalanuvchi kira olmasin (403).
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, delete

from app.core.database import Base, engine, AsyncSessionLocal
from app.models.restaurant import Restaurant
from app.models.user import User, UserRole
from app.core.security import create_access_token, get_password_hash, _user_revocation_timestamps
from app.main import app


@pytest.fixture(autouse=True)
async def setup_test_users_data():
    _user_revocation_timestamps.clear()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        # Tozalash: sinov foydalanuvchilari
        await session.execute(
            delete(User).where(
                User.username.in_([
                    "new_waiter_by_admin",
                    "new_cashier_by_admin",
                    "new_chef_by_admin",
                    "illegal_admin",
                    "illegal_dev",
                    "legit_admin_by_dev",
                    "legit_dev_by_dev",
                ])
            )
        )

        # Restaurants
        for r_id in (1, 2):
            r = await session.get(Restaurant, r_id)
            if not r:
                session.add(Restaurant(id=r_id, name=f"Rest {r_id}", slug=f"rest-{r_id}"))

        # Developer (id=1001)
        res_dev = await session.execute(select(User).where(User.username == "dev_user_10a"))
        dev_u = res_dev.scalar_one_or_none()
        if not dev_u:
            dev_u = User(
                id=1001,
                username="dev_user_10a",
                full_name="Developer 10A",
                hashed_password=get_password_hash("pass12345"),
                role=UserRole.DEVELOPER,
                restaurant_id=None,
                is_active=True,
                is_approved=True,
            )
            session.add(dev_u)
        else:
            dev_u.is_active = True
            dev_u.hashed_password = get_password_hash("pass12345")

        # Admin for Rest 1 (id=1002)
        res_adm1 = await session.execute(select(User).where(User.username == "admin_r1_10a"))
        adm1 = res_adm1.scalar_one_or_none()
        if not adm1:
            adm1 = User(
                id=1002,
                username="admin_r1_10a",
                full_name="Admin R1",
                hashed_password=get_password_hash("pass12345"),
                role=UserRole.ADMIN,
                restaurant_id=1,
                is_active=True,
                is_approved=True,
            )
            session.add(adm1)
        else:
            adm1.is_active = True
            adm1.hashed_password = get_password_hash("pass12345")

        # Admin for Rest 2 (id=1003)
        res_adm2 = await session.execute(select(User).where(User.username == "admin_r2_10a"))
        adm2 = res_adm2.scalar_one_or_none()
        if not adm2:
            adm2 = User(
                id=1003,
                username="admin_r2_10a",
                full_name="Admin R2",
                hashed_password=get_password_hash("pass12345"),
                role=UserRole.ADMIN,
                restaurant_id=2,
                is_active=True,
                is_approved=True,
            )
            session.add(adm2)
        else:
            adm2.is_active = True
            adm2.hashed_password = get_password_hash("pass12345")

        # Waiter for Rest 1 (id=1004)
        res_w1 = await session.execute(select(User).where(User.username == "waiter_r1_10a"))
        w1 = res_w1.scalar_one_or_none()
        if not w1:
            w1 = User(
                id=1004,
                username="waiter_r1_10a",
                full_name="Waiter R1",
                hashed_password=get_password_hash("pass12345"),
                role=UserRole.WAITER,
                restaurant_id=1,
                is_active=True,
                is_approved=True,
            )
            session.add(w1)
        else:
            w1.is_active = True
            w1.hashed_password = get_password_hash("pass12345")

        # Waiter for Rest 2 (id=1005)
        res_w2 = await session.execute(select(User).where(User.username == "waiter_r2_10a"))
        w2 = res_w2.scalar_one_or_none()
        if not w2:
            w2 = User(
                id=1005,
                username="waiter_r2_10a",
                full_name="Waiter R2",
                hashed_password=get_password_hash("pass12345"),
                role=UserRole.WAITER,
                restaurant_id=2,
                is_active=True,
                is_approved=True,
            )
            session.add(w2)
        else:
            w2.is_active = True
            w2.hashed_password = get_password_hash("pass12345")

        await session.commit()
    yield


@pytest.mark.anyio
async def test_create_user_role_restrictions():
    """Admin faqat waiter, chef, cashier yarata olsin. 'admin' va 'developer' ni faqat developer."""
    client = TestClient(app)
    admin_token = create_access_token({"sub": "1002", "role": "admin"})
    dev_token = create_access_token({"sub": "1001", "role": "developer"})

    headers_admin = {"Authorization": f"Bearer {admin_token}"}
    headers_dev = {"Authorization": f"Bearer {dev_token}"}

    # 1. Admin waiter yarata oladi -> 201
    r = client.post(
        "/api/v1/users/",
        headers=headers_admin,
        json={
            "username": "new_waiter_by_admin",
            "full_name": "New Waiter",
            "role": "waiter",
            "password": "password123",
        },
    )
    assert r.status_code == 201
    assert r.json()["role"] == "waiter"

    # 2. Admin cashier yarata oladi -> 201
    r = client.post(
        "/api/v1/users/",
        headers=headers_admin,
        json={
            "username": "new_cashier_by_admin",
            "full_name": "New Cashier",
            "role": "cashier",
            "password": "password123",
        },
    )
    assert r.status_code == 201

    # 3. Admin chef yarata oladi -> 201
    r = client.post(
        "/api/v1/users/",
        headers=headers_admin,
        json={
            "username": "new_chef_by_admin",
            "full_name": "New Chef",
            "role": "chef",
            "password": "password123",
        },
    )
    assert r.status_code == 201

    # 4. Admin 'admin' yaratishga urinsa -> 403
    r = client.post(
        "/api/v1/users/",
        headers=headers_admin,
        json={
            "username": "illegal_admin",
            "full_name": "Illegal Admin",
            "role": "admin",
            "password": "password123",
        },
    )
    assert r.status_code == 403
    assert "Admin faqat waiter, chef yoki cashier" in r.json()["detail"]

    # 5. Admin 'developer' yaratishga urinsa -> 403
    r = client.post(
        "/api/v1/users/",
        headers=headers_admin,
        json={
            "username": "illegal_dev",
            "full_name": "Illegal Dev",
            "role": "developer",
            "password": "password123",
        },
    )
    assert r.status_code == 403

    # 6. Developer 'admin' yarata oladi -> 201
    r = client.post(
        "/api/v1/users/",
        headers=headers_dev,
        json={
            "username": "legit_admin_by_dev",
            "full_name": "Legit Admin",
            "role": "admin",
            "restaurant_id": 1,
            "password": "password123",
        },
    )
    assert r.status_code == 201
    assert r.json()["role"] == "admin"

    # 7. Developer 'developer' yarata oladi -> 201
    r = client.post(
        "/api/v1/users/",
        headers=headers_dev,
        json={
            "username": "legit_dev_by_dev",
            "full_name": "Legit Dev",
            "role": "developer",
            "password": "password123",
        },
    )
    assert r.status_code == 201
    assert r.json()["role"] == "developer"


@pytest.mark.anyio
async def test_admin_cross_restaurant_and_developer_protection():
    """Admin faqat o'z restoranidagilarni ko'radi/o'zgartiradi; Admin developerga tegolmaydi (403)."""
    client = TestClient(app)
    admin_r1_token = create_access_token({"sub": "1002", "role": "admin"})
    dev_token = create_access_token({"sub": "1001", "role": "developer"})

    headers_r1 = {"Authorization": f"Bearer {admin_r1_token}"}
    headers_dev = {"Authorization": f"Bearer {dev_token}"}

    # 1. Admin R1 o'z restoranidagi xodimni (1004) ko'ra oladi -> 200
    r = client.get("/api/v1/users/1004", headers=headers_r1)
    assert r.status_code == 200

    # 2. Admin R1 boshqa restoran (Rest 2) xodimini (1005) ko'rishga urinsa -> 403
    r = client.get("/api/v1/users/1005", headers=headers_r1)
    assert r.status_code == 403
    assert "Siz faqat o'z restoraningizdagi" in r.json()["detail"]

    # 3. Admin R1 boshqa restoran xodimini (1005) yangilashga urinsa -> 403
    r = client.patch("/api/v1/users/1005", headers=headers_r1, json={"full_name": "Hacked Name"})
    assert r.status_code == 403

    # 4. Admin R1 developer (1001) ni ko'rish yoki yangilashga urinsa -> 403
    r = client.get("/api/v1/users/1001", headers=headers_r1)
    assert r.status_code == 403
    assert "developer" in r.json()["detail"]

    r = client.patch("/api/v1/users/1001", headers=headers_r1, json={"full_name": "Hacked Dev"})
    assert r.status_code == 403

    # 5. Developer boshqa restorandagi (1005) yoki har qanday foydalanuvchini ko'ra oladi -> 200
    r = client.get("/api/v1/users/1005", headers=headers_dev)
    assert r.status_code == 200


@pytest.mark.anyio
async def test_reset_user_password_endpoint():
    """PATCH /users/{id}/password: body {new_password: min_length=8}, tokenlar bekor qilinsin, audit."""
    client = TestClient(app)
    admin_r1_token = create_access_token({"sub": "1002", "role": "admin"})
    headers_r1 = {"Authorization": f"Bearer {admin_r1_token}"}

    # Waiter token
    waiter_token = create_access_token({"sub": "1004", "role": "waiter"})

    # 1. 8 ta belgidan kam bo'lsa -> 422
    r_short = client.patch(
        "/api/v1/users/1004/password",
        headers=headers_r1,
        json={"new_password": "12345"},
    )
    assert r_short.status_code == 422

    # 2. Muvaffaqiyatli parol yangilash -> 200
    r_ok = client.patch(
        "/api/v1/users/1004/password",
        headers=headers_r1,
        json={"new_password": "brand_new_pass_8"},
    )
    assert r_ok.status_code == 200
    assert r_ok.json()["message"] == "Parol muvaffaqiyatli yangilandi"

    # 3. Eski token bekor qilingan bo'lishi kerak -> 401
    r_old_token = client.get("/api/v1/users/1004", headers={"Authorization": f"Bearer {waiter_token}"})
    assert r_old_token.status_code == 401

    # 4. Yangi parol bilan login qilib bo'lishi kerak
    r_login = client.post(
        "/api/v1/auth/login",
        json={"username": "waiter_r1_10a", "password": "brand_new_pass_8"},
    )
    assert r_login.status_code == 200
    assert "access_token" in r_login.json()


@pytest.mark.anyio
async def test_delete_user_soft_delete_and_protections():
    """delete_user: is_active=False, token bekor qil, oxirgi faol adminni nofaol qilishga yo'l qo'yma (400), o'zini o'zi nofaol qila olmasin (400)."""
    client = TestClient(app)
    admin_r1_token = create_access_token({"sub": "1002", "role": "admin"})
    headers_r1 = {"Authorization": f"Bearer {admin_r1_token}"}

    # 1. O'zini o'zi nofaol qilishga urinsa -> 400
    r_self = client.delete("/api/v1/users/1002", headers=headers_r1)
    assert r_self.status_code == 400
    assert "O'zingizni nofaol qila olmaysiz" in r_self.json()["detail"]

    # 2. Restoranning oxirgi faol admin'i (1003 in Rest 2) ni nofaol qilish:
    # Developer orqali o'chirishga uringanda ham oxirgi admin bo'lgani uchun 400 berishi kerak
    dev_token = create_access_token({"sub": "1001", "role": "developer"})
    r_last_admin = client.delete("/api/v1/users/1003", headers={"Authorization": f"Bearer {dev_token}"})
    assert r_last_admin.status_code == 400
    assert "oxirgi faol admin" in r_last_admin.json()["detail"]

    # 3. Oddiy xodimni (1004) nofaol qilish -> 200
    waiter_token = create_access_token({"sub": "1004", "role": "waiter"})
    r_del = client.delete("/api/v1/users/1004", headers=headers_r1)
    assert r_del.status_code == 200
    assert "Foydalanuvchi nofaol qilindi" in r_del.json()["message"]

    # 4. Nofaol xodimning tokeni darhol bekor qilinadi -> 401
    r_tok = client.get("/api/v1/users/1004", headers={"Authorization": f"Bearer {waiter_token}"})
    assert r_tok.status_code == 401

    # 5. Nofaol foydalanuvchi tizimga kira olmasligi kerak -> 403
    r_login = client.post(
        "/api/v1/auth/login",
        json={"username": "waiter_r1_10a", "password": "pass12345"},
    )
    assert r_login.status_code == 403
    assert "faol emas" in r_login.json()["detail"]
