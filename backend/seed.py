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
from app.models.restaurant import Restaurant, RestaurantSettings, Theme
from app.models.table import Table
from app.models.menu import Category, MenuItem


THEMES = [
    {
        "name": "Elegant Dark",
        "slug": "elegant-dark",
        "description": "Qora fon, oltin ranglar — premium restoran uchun",
        "config": {
            "primary": "#D4AF37",
            "secondary": "#1a1a2e",
            "background": "#0f0f1a",
            "surface": "#1a1a2e",
            "text": "#ffffff",
            "accent": "#e8b86d",
            "font": "Playfair Display",
        },
    },
    {
        "name": "Fresh Green",
        "slug": "fresh-green",
        "description": "Yashil va oq — sog'lom taomlar uchun",
        "config": {
            "primary": "#2ECC71",
            "secondary": "#27AE60",
            "background": "#f0faf4",
            "surface": "#ffffff",
            "text": "#1a1a1a",
            "accent": "#16A085",
            "font": "Nunito",
        },
    },
    {
        "name": "Warm Sunset",
        "slug": "warm-sunset",
        "description": "To'q sariq va to'q qizil — issiq, qulay muhit",
        "config": {
            "primary": "#E67E22",
            "secondary": "#C0392B",
            "background": "#FFF8F0",
            "surface": "#ffffff",
            "text": "#2C1810",
            "accent": "#F39C12",
            "font": "Lato",
        },
    },
    {
        "name": "Ocean Blue",
        "slug": "ocean-blue",
        "description": "Ko'k gradiyent — zamonaviy, sof dizayn",
        "config": {
            "primary": "#2980B9",
            "secondary": "#1ABC9C",
            "background": "#EBF5FB",
            "surface": "#ffffff",
            "text": "#1a1a1a",
            "accent": "#21618C",
            "font": "Inter",
        },
    },
    {
        "name": "Royal Purple",
        "slug": "royal-purple",
        "description": "Binafsha va oltin — hashamatli tuyg'u",
        "config": {
            "primary": "#8E44AD",
            "secondary": "#D4AC0D",
            "background": "#F9F0FF",
            "surface": "#ffffff",
            "text": "#1a1a1a",
            "accent": "#9B59B6",
            "font": "Raleway",
        },
    },
    {
        "name": "Minimalist White",
        "slug": "minimalist-white",
        "description": "Sof oq — eng sodda va zamonaviy",
        "config": {
            "primary": "#2C3E50",
            "secondary": "#BDC3C7",
            "background": "#FAFAFA",
            "surface": "#ffffff",
            "text": "#2C3E50",
            "accent": "#E74C3C",
            "font": "Roboto",
        },
    },
]


# Restoran egasining asosiy admin akkaunti
RESTAURANT_NAME = "Dunyo Choyxonasi"
ADMIN_USERNAME = "maqsad"
ADMIN_PASSWORD = "01020307m"


async def seed():
    async with AsyncSessionLocal() as db:
        print("🌱 Boshlang'ich ma'lumotlar yuklanmoqda...")

        # ─── 1. Developer akkaunt ─────────────────────────────
        from sqlalchemy import select
        result = await db.execute(select(User).where(User.username == "developer"))
        dev_user = result.scalar_one_or_none()
        if not dev_user:
            dev = User(
                username="developer",
                full_name="Tizim Dasturchi",
                hashed_password=get_password_hash("dev123456"),
                role=UserRole.DEVELOPER,
                is_active=True,
            )
            db.add(dev)
            print("✅ Developer akkaunt yaratildi: developer / dev123456")
        else:
            dev_user.hashed_password = get_password_hash("dev123456")
            dev_user.role = UserRole.DEVELOPER
            dev_user.is_active = True
            print("✅ Developer akkaunt yangilandi: developer / dev123456")

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
        else:
            dev2_user.hashed_password = get_password_hash("dev123456")
            dev2_user.role = UserRole.DEVELOPER
            dev2_user.is_active = True


        # ─── 2. Temalar ───────────────────────────────────────
        for theme_data in THEMES:
            result = await db.execute(select(Theme).where(Theme.slug == theme_data["slug"]))
            if not result.scalar_one_or_none():
                theme = Theme(**theme_data)
                db.add(theme)
        print("✅ 6 ta dizayn temalari qo'shildi")

        # ─── 3. Namuna Restoran ───────────────────────────────
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

            # Sozlamalar
            settings_obj = RestaurantSettings(restaurant_id=restaurant.id)
            db.add(settings_obj)

            # Demo xodimlar ro'yxati
            # Oshpaz paneli olib tashlandi — buyurtma to'g'ridan-to'g'ri
            # oshxona printeriga chiqadi, shuning uchun oshpaz akkaunti kerak emas.
            demo_users = [
                {"username": ADMIN_USERNAME, "full_name": "Restoran Admin", "role": UserRole.ADMIN, "pass": ADMIN_PASSWORD},
                {"username": "ofitsiant1", "full_name": "Akbar Ofitsiant", "role": UserRole.WAITER, "pass": "waiter123"},
            ]
            for u in demo_users:
                user_res = await db.execute(select(User).where(User.username == u["username"]))
                if not user_res.scalar_one_or_none():
                    db_user = User(
                        username=u["username"],
                        full_name=u["full_name"],
                        hashed_password=get_password_hash(u["pass"]),
                        role=u["role"],
                        restaurant_id=restaurant.id,
                        is_active=True,
                    )
                    db.add(db_user)
            await db.flush()

            # Stollar (5 ta)
            for i in range(1, 6):
                qr_token = str(uuid.uuid4())
                table = Table(
                    restaurant_id=restaurant.id,
                    number=i,
                    name=f"Stol #{i}",
                    capacity=4,
                    qr_token=qr_token,
                    qr_image_url=f"/uploads/qr_codes/{qr_token}.png",
                )
                db.add(table)

            await db.flush()

            # Menyu kategoriyalari.
            # NAMUNA TAOMLAR QO'SHILMAYDI — menyuda faqat restoran egasi
            # admin panelda o'zi kiritgan taomlar ko'rinadi.
            categories_data = [
                {"name": "Kaboblar", "name_ru": "Шашлыки", "name_en": "Kebabs",
                 "name_cyrillic": "Кабоблар", "icon": "🍢"},
                {"name": "Salatlar", "name_ru": "Салаты", "name_en": "Salads",
                 "name_cyrillic": "Салатлар", "icon": "🥗"},
                {"name": "Ichimliklar", "name_ru": "Напитки", "name_en": "Drinks",
                 "name_cyrillic": "Ичимликлар", "icon": "🥤"},
                {"name": "Choylar", "name_ru": "Чай", "name_en": "Tea",
                 "name_cyrillic": "Чойлар", "icon": "🫖"},
            ]

            for i, cat_data in enumerate(categories_data):
                db.add(Category(
                    restaurant_id=restaurant.id,
                    sort_order=i,
                    **cat_data,
                ))

            await db.flush()

            print("✅ Demo restoran yaratildi:")
            print("   Admin:     maqsad / 01020307m")
            print("   Ofitsiant: ofitsiant1 / waiter123")

        # ─── 3.5. Namuna nomini to'g'rilash ───────────────────
        # Eski o'rnatmalarda restoran "Demo Restoran" deb yaratilgan edi va
        # bu nom CHEKLARDA ham chiqardi. Haqiqiy nomga o'zgartiramiz.
        # (Egasi keyin Admin -> Sozlamalar da istalgan nomni qo'ya oladi.)
        demo_res = await db.execute(select(Restaurant).where(Restaurant.name == "Demo Restoran"))
        demo_rest = demo_res.scalar_one_or_none()
        if demo_rest:
            demo_rest.name = RESTAURANT_NAME
            print(f"[OK] Restoran nomi yangilandi: {RESTAURANT_NAME}")

        # Chek sarlavhasi "RestAron" bo'lib qolgan bo'lsa tozalaymiz --
        # shunda chekda restoranning HAQIQIY nomi chiqadi.
        hdr_res = await db.execute(
            select(RestaurantSettings).where(RestaurantSettings.receipt_header == "RestAron")
        )
        for st in hdr_res.scalars().all():
            st.receipt_header = None

        # ─── 4. Admin akkauntini KAFOLATLASH ──────────────────
        # MUHIM: yuqoridagi blok faqat restoran YANGI yaratilganda ishlaydi.
        # Mavjud o'rnatmalarda (restoran allaqachon bor) admin akkaunti
        # yaratilmay qolar edi va egasi tizimga kira olmasdi.
        # Shuning uchun uni har safar alohida tekshiramiz.
        rest_res = await db.execute(select(Restaurant).order_by(Restaurant.id))
        first_restaurant = rest_res.scalars().first()
        if first_restaurant:
            admin_res = await db.execute(select(User).where(User.username == ADMIN_USERNAME))
            admin_user = admin_res.scalar_one_or_none()
            if not admin_user:
                db.add(User(
                    username=ADMIN_USERNAME,
                    full_name="Restoran Admin",
                    hashed_password=get_password_hash(ADMIN_PASSWORD),
                    role=UserRole.ADMIN,
                    restaurant_id=first_restaurant.id,
                    is_active=True,
                ))
                print(f"✅ Admin akkaunti yaratildi: {ADMIN_USERNAME}")
            else:
                # Akkaunt o'chirilgan bo'lsa qayta yoqamiz va restoranga bog'laymiz
                admin_user.is_active = True
                admin_user.role = UserRole.ADMIN
                if not admin_user.restaurant_id:
                    admin_user.restaurant_id = first_restaurant.id

        await db.commit()
        print("\n🎉 Boshlang'ich ma'lumotlar muvaffaqiyatli yuklandi!")
        print("\n📋 Kirish ma'lumotlari:")
        print("   Developer: developer / dev123456")
        print("   Admin:     maqsad / 01020307m")
        print("   Ofitsiant: ofitsiant1 / waiter123")


if __name__ == "__main__":
    asyncio.run(seed())
