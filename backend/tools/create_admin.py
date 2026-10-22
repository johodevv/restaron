"""
RestAron: Yangi administrator yoki xodim yaratish / parolini yangilash skripti
"""
import sys
import os
import asyncio
import getpass
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# Backend papkasini qidiruv yo'liga qo'shish
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.core.security import get_password_hash
from app.models.user import User, UserRole
from app.models.restaurant import Restaurant


ROLES_MAP = {
    "1": UserRole.ADMIN,
    "admin": UserRole.ADMIN,
    "2": UserRole.CASHIER,
    "cashier": UserRole.CASHIER,
    "3": UserRole.WAITER,
    "waiter": UserRole.WAITER,
    "4": UserRole.CHEF,
    "chef": UserRole.CHEF,
    "5": UserRole.DEVELOPER,
    "developer": UserRole.DEVELOPER,
}


async def create_or_update_user():
    print("=" * 60)
    print(" RestAron: Foydalanuvchi yaratish / yangilash")
    print("=" * 60)

    # 1. Username
    while True:
        username = input("Username kiriting: ").strip()
        if username:
            break
        print("❌ Username bo'sh bo'lishi mumkin emas!")

    # 2. To'liq ism
    full_name = input("To'liq ism (Enter bosilsa username olinadi): ").strip()
    if not full_name:
        full_name = username

    # 3. Rol tanlash
    print("\nMavjud rollar:")
    print("  1) admin     - Restoran administratori")
    print("  2) cashier   - Kassir")
    print("  3) waiter    - Ofitsiant")
    print("  4) chef      - Oshpaz")
    print("  5) developer - Dasturchi / Superadmin")

    selected_role = None
    while not selected_role:
        role_input = input("Rolni tanlang [1-5 yoki nomini yozing] (standart: 1): ").strip().lower()
        if not role_input:
            role_input = "1"
        selected_role = ROLES_MAP.get(role_input)
        if not selected_role:
            print("❌ Noto'g'ri rol kiritildi. Qaytadan tanlang.")

    # 4. Parol
    while True:
        password = getpass.getpass("Parol (kamida 10 ta belgi): ")
        if len(password) < 10:
            print("❌ Parol kamida 10 ta belgidan iborat bo'lishi kerak!")
            continue
        password_repeat = getpass.getpass("Parolni takrorlang: ")
        if password != password_repeat:
            print("❌ Parollar bir-biriga mos kelmadi! Qaytadan kiriting.")
            continue
        break

    # 5. DB ga yozish
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(User).where(User.username == username))
        existing_user = res.scalar_one_or_none()

        rest_res = await db.execute(select(Restaurant).order_by(Restaurant.id))
        first_restaurant = rest_res.scalars().first()
        rest_id = first_restaurant.id if first_restaurant else None

        hashed_pwd = get_password_hash(password)

        if existing_user:
            existing_user.hashed_password = hashed_pwd
            existing_user.role = selected_role
            existing_user.is_active = True
            existing_user.is_approved = True
            if full_name:
                existing_user.full_name = full_name
            if not existing_user.restaurant_id and rest_id and selected_role != UserRole.DEVELOPER:
                existing_user.restaurant_id = rest_id
            await db.commit()
            print(f"\n✅ Foydalanuvchi '{username}' paroli va roli ({selected_role.value}) muvaffaqiyatli yangilandi!")
        else:
            new_user = User(
                username=username,
                full_name=full_name,
                hashed_password=hashed_pwd,
                role=selected_role,
                is_active=True,
                is_approved=True,
                restaurant_id=rest_id if selected_role != UserRole.DEVELOPER else None,
            )
            db.add(new_user)
            await db.commit()
            print(f"\n✅ Yangi foydalanuvchi '{username}' ({selected_role.value}) muvaffaqiyatli yaratildi!")


def main():
    try:
        asyncio.run(create_or_update_user())
    except KeyboardInterrupt:
        print("\n\nJarayon bekor qilindi.")
        sys.exit(0)


if __name__ == "__main__":
    main()
