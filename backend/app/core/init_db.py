import uuid
import logging
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.core.security import get_password_hash
from app.models.user import User, UserRole
from app.models.restaurant import Restaurant, RestaurantSettings, Theme
from app.models.table import Table
from app.models.menu import Category, MenuItem

logger = logging.getLogger("init_db")

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

async def seed_initial_data():
    """Boshlang'ich ma'lumotlarni tekshirish va yaratish"""
    async with AsyncSessionLocal() as db:
        try:
            # 1. Developer akkaunt
            res = await db.execute(select(User).where(User.username == "developer"))
            if not res.scalar_one_or_none():
                dev = User(
                    username="developer",
                    full_name="Tizim Dasturchi",
                    hashed_password=get_password_hash("dev123456"),
                    role=UserRole.DEVELOPER,
                    is_active=True,
                )
                db.add(dev)

            # 2. Temalar
            for theme_data in THEMES:
                t_res = await db.execute(select(Theme).where(Theme.slug == theme_data["slug"]))
                if not t_res.scalar_one_or_none():
                    db.add(Theme(**theme_data))

            # 3. Dunyo Choyxonasi
            res = await db.execute(select(Restaurant).where(Restaurant.id == 1))
            restaurant = res.scalar_one_or_none()
            if not restaurant:
                res_slug = await db.execute(select(Restaurant).where(Restaurant.slug == "dunyo-choyxonasi"))
                restaurant = res_slug.scalar_one_or_none()

            if not restaurant:
                restaurant = Restaurant(
                    name="Dunyo Choyxonasi",
                    slug="dunyo-choyxonasi",
                    description="O'zbekona mehmondo'stlik, shinam so'rilar va haqiqiy milliy taomlar maskani",
                    address="Toshkent shahri, Chilonzor tumani",
                    phone="+998 71 200 00 00",
                    commission_percent=5.0,
                )
                db.add(restaurant)
                await db.flush()

                settings_obj = RestaurantSettings(restaurant_id=restaurant.id)
                db.add(settings_obj)
            else:
                restaurant.name = "Dunyo Choyxonasi"
                restaurant.description = "O'zbekona mehmondo'stlik, shinam so'rilar va haqiqiy milliy taomlar maskani"
                restaurant.phone = "+998 71 200 00 00"

            # 4. Demo xodimlar
            demo_users = [
                {"username": "admin", "full_name": "Dunyo Choyxonasi Admin", "role": UserRole.ADMIN, "pass": "admin123"},
                {"username": "waiter", "full_name": "Asosiy Ofitsiant", "role": UserRole.WAITER, "pass": "waiter123"},
                {"username": "ofitsiant1", "full_name": "Akbar Ofitsiant", "role": UserRole.WAITER, "pass": "waiter123"},
                {"username": "cook", "full_name": "Bosh Oshpaz", "role": UserRole.CHEF, "pass": "cook123"},
                {"username": "chef", "full_name": "Chef Oshpaz", "role": UserRole.CHEF, "pass": "chef123"},
                {"username": "oshpaz1", "full_name": "Zafar Oshpaz", "role": UserRole.CHEF, "pass": "chef123"},
            ]
            for u in demo_users:
                u_res = await db.execute(select(User).where(User.username == u["username"]))
                existing_u = u_res.scalar_one_or_none()
                if not existing_u:
                    db.add(User(
                        username=u["username"],
                        full_name=u["full_name"],
                        hashed_password=get_password_hash(u["pass"]),
                        role=u["role"],
                        restaurant_id=restaurant.id,
                        is_active=True,
                    ))
                else:
                    existing_u.hashed_password = get_password_hash(u["pass"])
                    existing_u.is_active = True

            # 5. Stollar (12 ta)
            for i in range(1, 13):
                t_res = await db.execute(
                    select(Table).where(Table.restaurant_id == restaurant.id, Table.number == i)
                )
                existing_t = t_res.scalar_one_or_none()
                room_name = "Asosiy Zal (So'ri)" if i <= 4 else ("Shinam Ayvon" if i <= 8 else "VIP Xona")
                if not existing_t:
                    qr_token = str(uuid.uuid4())
                    db.add(Table(
                        restaurant_id=restaurant.id,
                        number=i,
                        name=f"Stol #{i}",
                        room=room_name,
                        capacity=6 if i <= 4 else (8 if i <= 8 else 12),
                        qr_token=qr_token,
                        qr_code_url=f"/uploads/qr_codes/table_{i}.png",
                    ))
                else:
                    existing_t.room = room_name

            # 6. Kategoriyalar va Choyxona Taomlari
            categories_data = [
                {"name": "Milliy Taomlar & Palov", "icon": "🍲", "sort_order": 0},
                {"name": "Shashliklar & Kabob", "icon": "🍢", "sort_order": 1},
                {"name": "Somsalar & Tandir", "icon": "🥟", "sort_order": 2},
                {"name": "Salatlar & Gazaklar", "icon": "🥗", "sort_order": 3},
                {"name": "Choyxona Choylari & Ichimliklar", "icon": "🫖", "sort_order": 4},
                {"name": "Shirinliklar", "icon": "🍯", "sort_order": 5},
            ]

            category_map = {}
            for idx, cat_d in enumerate(categories_data):
                c_res = await db.execute(
                    select(Category).where(Category.restaurant_id == restaurant.id, Category.name == cat_d["name"])
                )
                cat_obj = c_res.scalar_one_or_none()
                if not cat_obj:
                    cat_obj = Category(restaurant_id=restaurant.id, **cat_d)
                    db.add(cat_obj)
                    await db.flush()
                category_map[idx] = cat_obj

            items_data = [
                # Milliy Taomlar & Palov
                {
                    "cat_idx": 0, "name": "Choyxona Maxsus Palovi", "price": 48000,
                    "description": "Devzira guruch, barra qo'y go'shti, qazi, bedana tuxum, noxat va mayiz bilan damlangan afsonaviy palov.",
                    "prep_time_minutes": 15, "calories": 720, "is_available": True, "is_featured": True,
                    "image_url": "https://images.unsplash.com/photo-1563379091339-03b21ab4a4f8?auto=format&fit=crop&w=600&q=80"
                },
                {
                    "cat_idx": 0, "name": "Qozon Kabob (Barra Go'sht)", "price": 58000,
                    "description": "Qarsildoq tillarang kartoshka va erib ketadigan barra qo'y qovurg'asi.",
                    "prep_time_minutes": 20, "calories": 780, "is_available": True, "is_featured": True,
                    "image_url": "https://images.unsplash.com/photo-1544025162-d76694265947?auto=format&fit=crop&w=600&q=80"
                },
                {
                    "cat_idx": 0, "name": "Tandir Go'shti (Jizzaxcha)", "price": 65000,
                    "description": "Archa shoxlarida xushbo'y dimlangan yumshoq tandir go'shti.",
                    "prep_time_minutes": 15, "calories": 690, "is_available": True, "is_featured": True,
                    "image_url": "https://images.unsplash.com/photo-1555939594-58d7cb561ad1?auto=format&fit=crop&w=600&q=80"
                },
                {
                    "cat_idx": 0, "name": "Uyg'urcha Lag'mon (Qo'lda Cho'zilgan)", "price": 38000,
                    "description": "Yupqa cho'zilgan xamir, yangi jiblajon sabzavotlar va lahm go'shtli qayla.",
                    "prep_time_minutes": 12, "calories": 540, "is_available": True,
                    "image_url": "https://images.unsplash.com/photo-1569718212165-3a8278d5f624?auto=format&fit=crop&w=600&q=80"
                },
                {
                    "cat_idx": 0, "name": "Xonadon Shurvasi (Qo'zichoq Go'shti)", "price": 35000,
                    "description": "Yengil va to'yimli sho'rva, yirik barra go'sht va sabzavotlar bilan.",
                    "prep_time_minutes": 10, "calories": 420, "is_available": True,
                    "image_url": "https://images.unsplash.com/photo-1547592166-23ac45744acd?auto=format&fit=crop&w=600&q=80"
                },
                # Shashliklar
                {
                    "cat_idx": 1, "name": "G'ijduvon Shashlik (Qiyma)", "price": 22000,
                    "description": "Yumshoq mol va qo'y go'shti qiymasi, maxsus ziravorlar bilan.",
                    "prep_time_minutes": 15, "calories": 380, "is_available": True, "is_featured": True,
                    "image_url": "https://images.unsplash.com/photo-1555939594-58d7cb561ad1?auto=format&fit=crop&w=600&q=80"
                },
                {
                    "cat_idx": 1, "name": "Kuskovoy (Bo'lak Go'sht) Shashlik", "price": 25000,
                    "description": "Marinadlangan lahm go'sht va dumba bo'laklari.",
                    "prep_time_minutes": 15, "calories": 410, "is_available": True,
                    "image_url": "https://images.unsplash.com/photo-1529193591184-b1d58069ecdd?auto=format&fit=crop&w=600&q=80"
                },
                {
                    "cat_idx": 1, "name": "Jigar Shashlik (Dumba Bilan)", "price": 20000,
                    "description": "Barra jigar bo'laklari, erigan dumba yog'i va piyoz bilan.",
                    "prep_time_minutes": 10, "calories": 340, "is_available": True,
                    "image_url": "https://images.unsplash.com/photo-1544025162-d76694265947?auto=format&fit=crop&w=600&q=80"
                },
                {
                    "cat_idx": 1, "name": "Tovuq Qanotlari Shashlik", "price": 20000,
                    "description": "Qarsildoq tillarang pishgan marinadlangan tovuq qanotlari.",
                    "prep_time_minutes": 15, "calories": 360, "is_available": True,
                    "image_url": "https://images.unsplash.com/photo-1527477378733-d8a4362b083c?auto=format&fit=crop&w=600&q=80"
                },
                # Somsalar & Tandir
                {
                    "cat_idx": 2, "name": "Tandir Somsa (Go'shtli & Dumbasimon)", "price": 12000,
                    "description": "Qarsildoq qatlama xamir, mayda to'g'ralgan lahm go'sht va piyoz.",
                    "prep_time_minutes": 5, "calories": 290, "is_available": True, "is_featured": True,
                    "image_url": "https://images.unsplash.com/photo-1626700051175-6818013e1d4f?auto=format&fit=crop&w=600&q=80"
                },
                {
                    "cat_idx": 2, "name": "Tandir Non / Patir Non", "price": 6000,
                    "description": "Yangi tandirdan uzilgan issiq qaymoqli patir non.",
                    "prep_time_minutes": 3, "calories": 210, "is_available": True,
                    "image_url": "https://images.unsplash.com/photo-1509440159596-0249088772ff?auto=format&fit=crop&w=600&q=80"
                },
                # Salatlar
                {
                    "cat_idx": 3, "name": "Achichuk Salati", "price": 16000,
                    "description": "Yangi yupqa to'g'ralgan shirin pomidor, piyoz va rayhon.",
                    "prep_time_minutes": 5, "calories": 90, "is_available": True, "is_featured": True,
                    "image_url": "https://images.unsplash.com/photo-1540420773420-3366772f4999?auto=format&fit=crop&w=600&q=80"
                },
                {
                    "cat_idx": 3, "name": "Suzma va Yangi Ko'katlar", "price": 14000,
                    "description": "Nordon xonaki suzma, kashnich, arpabodiyon va yalpiz.",
                    "prep_time_minutes": 3, "calories": 120, "is_available": True,
                    "image_url": "https://images.unsplash.com/photo-1546793665-c74683f339c1?auto=format&fit=crop&w=600&q=80"
                },
                # Choylar
                {
                    "cat_idx": 4, "name": "Choyxona 95 Ko'k Choy (Limon & Novvot Bilan)", "price": 10000,
                    "description": "Samovarda damlangan an'anaviy xushbo'y ko'k choy, limon va novvot bilan.",
                    "prep_time_minutes": 5, "calories": 30, "is_available": True, "is_featured": True,
                    "image_url": "https://images.unsplash.com/photo-1576092768241-dec231879fc3?auto=format&fit=crop&w=600&q=80"
                },
                {
                    "cat_idx": 4, "name": "Maxsus Zanjabilli Asal Choy", "price": 18000,
                    "description": "Tabiiy tog' asali, yangi zanjabil, limon va yalpizli darmondori choy.",
                    "prep_time_minutes": 5, "calories": 95, "is_available": True,
                    "image_url": "https://images.unsplash.com/photo-1513558161293-cdaf765ed2fd?auto=format&fit=crop&w=600&q=80"
                },
                {
                    "cat_idx": 4, "name": "Tog' Giyohlari Qora Choy", "price": 12000,
                    "description": "Kiyiko't va tog' yalpizi qo'shilgan quyuq xushbo'y qora choy.",
                    "prep_time_minutes": 5, "calories": 20, "is_available": True,
                    "image_url": "https://images.unsplash.com/photo-1576092768241-dec231879fc3?auto=format&fit=crop&w=600&q=80"
                },
                # Shirinliklar
                {
                    "cat_idx": 5, "name": "Asalli Chak-Chak", "price": 20000,
                    "description": "Xonaki asal va bodom donalari bilan bezatilgan qarsildoq chak-chak.",
                    "prep_time_minutes": 5, "calories": 410, "is_available": True,
                    "image_url": "https://images.unsplash.com/photo-1579372786545-d24232daf58c?auto=format&fit=crop&w=600&q=80"
                },
            ]

            for item in items_data:
                cat = category_map.get(item["cat_idx"])
                if cat:
                    i_res = await db.execute(
                        select(MenuItem).where(MenuItem.category_id == cat.id, MenuItem.name == item["name"])
                    )
                    if not i_res.scalar_one_or_none():
                        item_copy = dict(item)
                        item_copy.pop("cat_idx", None)
                        db.add(MenuItem(category_id=cat.id, **item_copy))

            await db.commit()
            print("[OK] Dunyo Choyxonasi ma'lumotlari to'liq bazaga yuklandi!")
            return {"status": "success", "message": "Dunyo Choyxonasi initialized successfully"}
        except Exception as e:
            await db.rollback()
            print(f"[ERROR] Init DB error: {e}")
            raise e
