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

            # 3. Namuna Restoran
            res = await db.execute(select(Restaurant).where(Restaurant.id == 1))
            restaurant = res.scalar_one_or_none()
            if not restaurant:
                res_slug = await db.execute(select(Restaurant).where(Restaurant.slug == "demo-restoran"))
                restaurant = res_slug.scalar_one_or_none()

            if not restaurant:
                restaurant = Restaurant(
                    name="Demo Restoran",
                    slug="demo-restoran",
                    description="RestAron tizimini sinab ko'rish uchun namuna restoran",
                    address="Toshkent, Chilonzor tumani",
                    phone="+998 90 123 45 67",
                    commission_percent=5.0,
                )
                db.add(restaurant)
                await db.flush()

                settings_obj = RestaurantSettings(restaurant_id=restaurant.id)
                db.add(settings_obj)

            # 4. Demo xodimlar
            demo_users = [
                {"username": "admin", "full_name": "Restoran Admin", "role": UserRole.ADMIN, "pass": "admin123"},
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

            # 5. Stollar (kamida 10 ta)
            for i in range(1, 11):
                t_res = await db.execute(
                    select(Table).where(Table.restaurant_id == restaurant.id, Table.number == i)
                )
                if not t_res.scalar_one_or_none():
                    qr_token = str(uuid.uuid4())
                    db.add(Table(
                        restaurant_id=restaurant.id,
                        number=i,
                        name=f"Stol #{i}",
                        capacity=4,
                        location="Asosiy zal" if i <= 6 else "Terrasa",
                        qr_token=qr_token,
                        qr_code_url=f"/uploads/qr_codes/table_{i}.png",
                    ))

            # 6. Kategoriyalar va Taomlar
            categories_data = [
                {"name": "Milliy Taomlar", "icon": "🍲", "sort_order": 0},
                {"name": "Fast Food", "icon": "🍔", "sort_order": 1},
                {"name": "Ichimliklar", "icon": "🥤", "sort_order": 2},
                {"name": "Shirinliklar", "icon": "🍰", "sort_order": 3},
                {"name": "Salatlar", "icon": "🥗", "sort_order": 4},
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
                # Milliy
                {
                    "cat_idx": 0, "name": "Toshkent Palovi", "price": 45000,
                    "description": "Qo'y go'shti, devzira guruch, sabzi va mayiz bilan an'anaviy toshkentcha palov.",
                    "prep_time_minutes": 15, "calories": 650, "is_available": True, "is_featured": True,
                    "image_url": "https://images.unsplash.com/photo-1563379091339-03b21ab4a4f8?auto=format&fit=crop&w=600&q=80"
                },
                {
                    "cat_idx": 0, "name": "Qozon Kabob", "price": 55000,
                    "description": "Qarsildoq qovurilgan kartoshka va yumshoq mol go'shti.",
                    "prep_time_minutes": 20, "calories": 720, "is_available": True,
                    "image_url": "https://images.unsplash.com/photo-1544025162-d76694265947?auto=format&fit=crop&w=600&q=80"
                },
                {
                    "cat_idx": 0, "name": "Lag'mon (Cho'zma)", "price": 38000,
                    "description": "Qo'lda cho'zilgan xamir, yangi sabzavotlar va go'shtli qayla.",
                    "prep_time_minutes": 12, "calories": 520, "is_available": True,
                    "image_url": "https://images.unsplash.com/photo-1569718212165-3a8278d5f624?auto=format&fit=crop&w=600&q=80"
                },
                # Fast Food
                {
                    "cat_idx": 1, "name": "RestAron Burger", "price": 42000,
                    "description": "100% mol go'shti kotleti, cheddar pishlog'i va maxsus sous.",
                    "prep_time_minutes": 10, "calories": 580, "is_available": True, "is_featured": True,
                    "image_url": "https://images.unsplash.com/photo-1568901346375-23c9450c58cd?auto=format&fit=crop&w=600&q=80"
                },
                {
                    "cat_idx": 1, "name": "Katta Lavash (Mol go'shtli)", "price": 35000,
                    "description": "Yupqa xamirda marinadlangan go'sht, pomidor, bodring va sous.",
                    "prep_time_minutes": 8, "calories": 490, "is_available": True,
                    "image_url": "https://images.unsplash.com/photo-1626700051175-6818013e1d4f?auto=format&fit=crop&w=600&q=80"
                },
                # Ichimliklar
                {
                    "cat_idx": 2, "name": "Yalpizli Limonad", "price": 22000,
                    "description": "Yangi yalpiz, limon va laym sharbati bilan muzdek kokteyl.",
                    "prep_time_minutes": 5, "calories": 110, "is_available": True,
                    "image_url": "https://images.unsplash.com/photo-1513558161293-cdaf765ed2fd?auto=format&fit=crop&w=600&q=80"
                },
                {
                    "cat_idx": 2, "name": "Ko'k Choy (Choynakda)", "price": 8000,
                    "description": "Limon va novvot bilan xushbo'y ko'k choy.",
                    "prep_time_minutes": 3, "calories": 10, "is_available": True,
                    "image_url": "https://images.unsplash.com/photo-1576092768241-dec231879fc3?auto=format&fit=crop&w=600&q=80"
                },
                # Shirinliklar
                {
                    "cat_idx": 3, "name": "Chizkeyk Nyu-York", "price": 28000,
                    "description": "Klassik qaymoqli pishloqli nozik shirinlik.",
                    "prep_time_minutes": 5, "calories": 380, "is_available": True,
                    "image_url": "https://images.unsplash.com/photo-1533134242443-d4fd215305ad?auto=format&fit=crop&w=600&q=80"
                },
                # Salatlar
                {
                    "cat_idx": 4, "name": "Tsezar Salati", "price": 36000,
                    "description": "Tovuq filesi, aysberg barglari, parmezan pishlog'i va suxariklar.",
                    "prep_time_minutes": 10, "calories": 310, "is_available": True,
                    "image_url": "https://images.unsplash.com/photo-1546793665-c74683f339c1?auto=format&fit=crop&w=600&q=80"
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
            print("[OK] Boshlang'ich demo ma'lumotlar to'liq bazaga yuklandi!")
            return {"status": "success", "message": "Demo data initialized successfully"}
        except Exception as e:
            await db.rollback()
            print(f"[ERROR] Init DB error: {e}")
            raise e
