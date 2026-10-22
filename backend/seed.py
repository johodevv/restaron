"""
Boshlang'ich ma'lumotlar: Temalar va namuna Restoran
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
from app.models.restaurant import Restaurant, RestaurantSettings
from app.models.table import Table
from app.models.menu import Category, MenuItem


# Restoran nomi
RESTAURANT_NAME = "Dunyo Choyxonasi"


async def seed(force: bool = False):
    async with AsyncSessionLocal() as db:
        from sqlalchemy import select

        # ─── IDEMPOTENCY TEKSHIRUVI ───────────────────────────────────────────
        result = await db.execute(select(Restaurant).where(Restaurant.slug == "demo-restoran"))
        demo_rest = result.scalar_one_or_none()
        already_seeded = (demo_rest is not None) and not force

        if already_seeded:
            _run = False
        else:
            print("🌱 Boshlang'ich ma'lumotlar yuklanmoqda...")
            _run = True

        if _run:
            # ─── 1. Namuna Restoran ───────────────────────────────────────
            if not demo_rest:
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
                    {"name": "Salatlar", "name_ru": "Салаты", "name_en": "Salads", "name_cyrillic": "Салатlar", "icon": "🥗"},
                    {"name": "Ichimliklar", "name_ru": "Напитки", "name_en": "Drinks", "name_cyrillic": "Ичимликлар", "icon": "🥤"},
                    {"name": "Choylar", "name_ru": "Чай", "name_en": "Tea", "name_cyrillic": "Чойлар", "icon": "🫖"},
                ]
                for i, cat_data in enumerate(categories_data):
                    db.add(Category(restaurant_id=restaurant.id, sort_order=i, **cat_data))
                await db.flush()

                print("✅ Demo restoran, stollar va kategoriyalar yaratildi.")

        # ─── XAVFSIZLIK TUZATISHLARI (har doim ishlaydi) ─────────────────────
        # Eski "Demo Restoran" nomini to'g'irlaymiz
        demo_res = await db.execute(select(Restaurant).where(Restaurant.name == "Demo Restoran"))
        demo_rest_old = demo_res.scalar_one_or_none()
        if demo_rest_old:
            demo_rest_old.name = RESTAURANT_NAME
            print(f"[OK] Restoran nomi yangilandi: {RESTAURANT_NAME}")

        # Chek sarlavhasidagi eski "RestAron" nomini tozalaymiz
        hdr_res = await db.execute(
            select(RestaurantSettings).where(RestaurantSettings.receipt_header == "RestAron")
        )
        for st in hdr_res.scalars().all():
            st.receipt_header = None

        await db.commit()
        if _run:
            print("\n🎉 Boshlang'ich ma'lumotlar muvaffaqiyatli yuklandi!")
            print("ℹ️ Foydalanuvchi yaratish uchun backend/tools/create_admin.py skriptidan foydalaning.")
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
