"""
Boshlang'ich ma'lumotlar: Developer, Temalar va namuna Restoran
"""
import asyncio
import sys
import uuid

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import AsyncSessionLocal
from app.core.security import get_password_hash
from app.models.user import User, UserRole
from app.models.restaurant import Restaurant, RestaurantSettings
from app.models.table import Table
from app.models.menu import Category, MenuItem


# Restoran egasining asosiy admin akkaunti
RESTAURANT_NAME = "Dunyo Choyxonasi"
ADMIN_USERNAME = "maqsad"
ADMIN_PASSWORD = "01020307m"


async def seed(force: bool = False):
    async with AsyncSessionLocal() as db:
        from sqlalchemy import select

        # ─── IDEMPOTENCY TEKSHIRUVI ───────────────────────────────────────────
        # Production'da har server qayta ishga tushganda to'liq seed ishlashi
        # keraksiz: bcrypt xeshlash sekin, DB yozuvlari ortiqcha.
        # Developer user mavjudligi — tizim allaqachon seed qilinganligini bildiradi.
        result = await db.execute(select(User).where(User.username == "developer"))
        dev_user = result.scalar_one_or_none()
        already_seeded = (dev_user is not None) and not force

        if already_seeded:
            # Faqat xavfsizlik uchun zaruriy tuzatishlarni ishlatamiz
            # (admin akkaunt tiklanishi, chek sarlavhasi tozalanishi)
            _run = False
        else:
            print("🌱 Boshlang'ich ma'lumotlar yuklanmoqda...")
            _run = True

        if _run:
            # ─── 1. Developer akkaunt ─────────────────────────────────────
            dev = User(
                username="developer",
                full_name="Tizim Dasturchi",
                hashed_password=get_password_hash("dev123456"),
                role=UserRole.DEVELOPER,
                is_active=True,
            )
            db.add(dev)
            print("✅ Developer akkaunt yaratildi: developer / dev123456")

            result_dev2 = await db.execute(select(User).where(User.username == "dev"))
            dev2_user = result_dev2.scalar_one_or_none()
            if not dev2_user:
                dev2 = User(
                    username="dev",
                    full_name="Tizim Dasturchi",
                    hashed_password=get_password_hash("dev123456"),
                    role=UserRole.DEVELOPER,
                    is_active=True,
                )
                db.add(dev2)
                print("✅ Dev akkaunt yaratildi: dev / dev123456")

            # ─── 2. Namuna Restoran ───────────────────────────────────────
            result = await db.execute(select(Restaurant).where(Restaurant.slug == "demo-restoran"))
            if not result.scalar_one_or_none():
                restaurant = Restaurant(
                    name=RESTAURANT_NAME,
                    slug="demo-restoran",
                    description="RestAron tizimini sinab ko'rish uchun namuna restoran",
                    address="Xorazm viloyati, Xiva tumani",
                    phone="+998 88 459 34 00",
                    commission_percent=5.0,
                )
                db.add(restaurant)
                await db.flush()

                settings_obj = RestaurantSettings(restaurant_id=restaurant.id)
                db.add(settings_obj)

                demo_users = [
                    {"username": "admin", "full_name": "Dunyo Choyxonasi Admin", "role": UserRole.ADMIN, "pass": "01020307m"},
                    {"username": "maqsad", "full_name": "Restoran Admin", "role": UserRole.ADMIN, "pass": "01020307m"},
                    {"username": "waiter", "full_name": "Asosiy Ofitsiant", "role": UserRole.WAITER, "pass": "01020307m"},
                    {"username": "ofitsiant", "full_name": "Ofitsiant", "role": UserRole.WAITER, "pass": "01020307m"},
                    {"username": "ofitsiant1", "full_name": "Akbar Ofitsiant", "role": UserRole.WAITER, "pass": "01020307m"},
                ]
                for u in demo_users:
                    user_res = await db.execute(select(User).where(User.username == u["username"]))
                    if not user_res.scalar_one_or_none():
                        db.add(User(
                            username=u["username"],
                            full_name=u["full_name"],
                            hashed_password=get_password_hash(u["pass"]),
                            role=u["role"],
                            restaurant_id=restaurant.id,
                            is_active=True,
                        ))
                await db.flush()

                for i in range(1, 6):
                    qr_token = str(uuid.uuid4())
                    db.add(Table(
                        restaurant_id=restaurant.id,
                        number=i,
                        name=f"Stol #{i}",
                        capacity=4,
                        qr_token=qr_token,
                        qr_image_url=f"/uploads/qr_codes/{qr_token}.png",
                    ))
                await db.flush()

                categories_data = [
                    {"name": "Kaboblar", "name_ru": "Шашлыки", "name_en": "Kebabs", "name_cyrillic": "Кабоблар", "icon": "🍢"},
                    {"name": "Salatlar", "name_ru": "Салаты", "name_en": "Salads", "name_cyrillic": "Салатлар", "icon": "🥗"},
                    {"name": "Ichimliklar", "name_ru": "Напитки", "name_en": "Drinks", "name_cyrillic": "Ичимликлар", "icon": "🥤"},
                    {"name": "Choylar", "name_ru": "Чай", "name_en": "Tea", "name_cyrillic": "Чойлар", "icon": "🫖"},
                ]
                for i, cat_data in enumerate(categories_data):
                    db.add(Category(restaurant_id=restaurant.id, sort_order=i, **cat_data))
                await db.flush()

                print("✅ Demo restoran yaratildi:")
                print("   Admin:     maqsad / 01020307m")
                print("   Ofitsiant: ofitsiant1 / waiter123")

        # ─── XAVFSIZLIK TUZATISHLARI (har doim ishlaydi) ─────────────────────
        # Eski "Demo Restoran" nomini to'g'irlaymiz
        demo_res = await db.execute(select(Restaurant).where(Restaurant.name == "Demo Restoran"))
        demo_rest = demo_res.scalar_one_or_none()
        if demo_rest:
            demo_rest.name = RESTAURANT_NAME
            print(f"[OK] Restoran nomi yangilandi: {RESTAURANT_NAME}")

        # Chek sarlavhasidagi eski "RestAron" nomini tozalaymiz
        hdr_res = await db.execute(
            select(RestaurantSettings).where(RestaurantSettings.receipt_header == "RestAron")
        )
        for st in hdr_res.scalars().all():
            st.receipt_header = None

        # ─── 4. Admin va Ofitsiant akkauntlarini KAFOLATLASH ──────────────────
        rest_res = await db.execute(select(Restaurant).order_by(Restaurant.id))
        first_restaurant = rest_res.scalars().first()
        if first_restaurant:
            guaranteed_users = [
                ("admin", "Dunyo Choyxonasi Admin", UserRole.ADMIN, "01020307m"),
                ("maqsad", "Restoran Admin", UserRole.ADMIN, "01020307m"),
                ("waiter", "Asosiy Ofitsiant", UserRole.WAITER, "01020307m"),
                ("ofitsiant", "Ofitsiant", UserRole.WAITER, "01020307m"),
            ]
            for uname, fname, urole, upass in guaranteed_users:
                u_res = await db.execute(select(User).where(User.username == uname))
                user_obj = u_res.scalar_one_or_none()
                if not user_obj:
                    db.add(User(
                        username=uname,
                        full_name=fname,
                        hashed_password=get_password_hash(upass),
                        role=urole,
                        restaurant_id=first_restaurant.id,
                        is_active=True,
                    ))
                    print(f"✅ Akkaunt yaratildi: {uname} ({urole.value})")
                else:
                    user_obj.is_active = True
                    user_obj.role = urole
                    user_obj.hashed_password = get_password_hash(upass)
                    if not user_obj.restaurant_id:
                        user_obj.restaurant_id = first_restaurant.id

        await db.commit()
        if _run:
            print("\n🎉 Boshlang'ich ma'lumotlar muvaffaqiyatli yuklandi!")
            print("\n📋 Kirish ma'lumotlari:")
            print("   Developer: developer / dev123456")
            print("   Admin:     maqsad / 01020307m")
            print("   Ofitsiant: ofitsiant1 / waiter123")
        else:
            print("[OK] Seed: tizim allaqachon sozlangan, o'tkazib yuborildi.")


if __name__ == "__main__":
    if "--help" in sys.argv or "-h" in sys.argv:
        print("RestAron Database Seeder")
        print("Foydalanish: python seed.py [--force]")
        print("  --force, -f : Idempotency tekshiruvini aylanib o'tib, majburiy qayta seed qilish")
        sys.exit(0)
    force_flag = "--force" in sys.argv or "-f" in sys.argv
    asyncio.run(seed(force=force_flag))

