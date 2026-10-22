"""
RestAron - VAZIFA 16: Yuklama testi (Load Test Script)
Fayl: backend/tools/load_test.py

Xususiyatlari:
1. Sozlanadigan parametrlar:
   - --base-url: Server manzili (standart: http://127.0.0.1:8000)
   - --users: Virtual ofitsiantlar soni (standart: 30)
   - --duration: Test davomiyligi soniyalarda (standart: 15)
   - --in-process: Serverni ishga tushirmasdan to'g'ridan-to'g'ri ASGI (FastAPI app) orqali testlash
2. Xavfsizlik to'sig'i (DB Guard):
   - FAQAT test bazasida ishlaydi.
   - Agar haqiqiy ishlab chiqarish bazasi ('restaron.db' va nomida 'test' bo'lmagan) aniqlansa, darhol to'xtaydi.
3. Yuklama ssenariysi:
   - 30 virtual ofitsiant tizimga login qiladi.
   - Tasodifiy stollarga zakaz ochadi, taom qo'shadi, oshxonaga yuboradi.
   - So'rovlarning 5% bitta umumiy stolga (hotspot / poyga holati) yo'naltiriladi.
4. Yakuniy hisobot:
   - Jami so'rovlar soni, xatolar soni.
   - Endpoint bo'yicha p50, p95, p99 kechikishlar (latencies).
"""
import os
import sys
import time
import random
import asyncio
import argparse
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone

# Backend papkasini qidiruv yo'liga qo'shamiz
_current_dir = os.path.dirname(os.path.abspath(__file__))
_backend_dir = os.path.abspath(os.path.join(_current_dir, ".."))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

import httpx
from httpx import AsyncClient, ASGITransport


def check_database_safety(db_url: str):
    """
    XAVFSIZLIK TO'SIG'I:
    Haqiqiy ishlab chiqarish bazasida ('restaron.db') yuklama testini ishga tushirish qat'iyan taqiqlanadi!
    Faqat 'test' so'zi qatnashgan test bazalarida ruxsat beriladi.
    """
    normalized_url = db_url.lower().replace("\\", "/")
    
    # Agar bazada 'test' so'zi bo'lmasa yoki aniq 'restaron.db' ga bog'langan bo'lsa
    is_prod_db = (
        ("restaron.db" in normalized_url and "test" not in normalized_url)
        or ("test" not in normalized_url and "sqlite" in normalized_url)
    )

    if is_prod_db:
        print("\n" + "=" * 70)
        print(" [XAVFSIZLIK TO'SIG'I] XATOLIK: Haqiqiy ishlab chiqarish bazasi aniqlandi!")
        print(f" Joriy DATABASE_URL: {db_url}")
        print(" load_test.py FAQAT test bazasida (nomida 'test' bo'lgan bazada) ishlashi shart.")
        print(" Tavsiya:")
        print("   Windows:  set DATABASE_URL=sqlite+aiosqlite:///./restaron_load_test.db")
        print("   Linux:    export DATABASE_URL=sqlite+aiosqlite:///./restaron_load_test.db")
        print("=" * 70 + "\n")
        sys.exit(1)


def calculate_percentile(data: List[float], p: float) -> float:
    """Berilgan foiz (p50, p95, p99) bo'yicha percentileni hisoblash"""
    if not data:
        return 0.0
    s_data = sorted(data)
    k = (len(s_data) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(s_data) - 1)
    d = k - f
    return s_data[f] + d * (s_data[c] - s_data[f])


class MetricsCollector:
    """So'rovlar kechikishi va xatoliklarini qayd qiluvchi hisoblagich"""
    def __init__(self):
        self.lock = asyncio.Lock()
        # endpoint -> list of latencies (ms)
        self.latencies: Dict[str, List[float]] = {}
        # endpoint -> error count
        self.errors: Dict[str, int] = {}
        # endpoint -> success count
        self.successes: Dict[str, int] = {}

    async def record(self, endpoint: str, latency_ms: float, is_error: bool):
        async with self.lock:
            if endpoint not in self.latencies:
                self.latencies[endpoint] = []
                self.errors[endpoint] = 0
                self.successes[endpoint] = 0

            self.latencies[endpoint].append(latency_ms)
            if is_error:
                self.errors[endpoint] += 1
            else:
                self.successes[endpoint] += 1

    def print_summary(self, duration_sec: float, users: int):
        total_requests = sum(len(v) for v in self.latencies.values())
        total_errors = sum(self.errors.values())
        total_success = sum(self.successes.values())
        all_latencies = [lat for l_list in self.latencies.values() for lat in l_list]
        rps = total_requests / max(duration_sec, 0.001)

        print("\n" + "=" * 85)
        print(f" RESTARON YUKLAMA TESTI NATIJALARI (LOAD TEST REPORT)")
        print(f" Virtual foydalanuvchilar (Ofitsiantlar): {users} ta")
        print(f" Davomiyligi: {duration_sec:.1f} soniya | RPS: {rps:.1f} req/s")
        print(f" Jami so'rovlar: {total_requests} | Muvaffaqiyatli: {total_success} | Xatolar: {total_errors}")
        print("=" * 85)
        print(f"{'Endpoint':<32} | {'Soni':<7} | {'Xatolar':<7} | {'p50 (ms)':<9} | {'p95 (ms)':<9} | {'p99 (ms)':<9} | {'Max (ms)':<8}")
        print("-" * 85)

        for ep in sorted(self.latencies.keys()):
            lats = self.latencies[ep]
            errs = self.errors[ep]
            p50 = calculate_percentile(lats, 50)
            p95 = calculate_percentile(lats, 95)
            p99 = calculate_percentile(lats, 99)
            max_lat = max(lats) if lats else 0.0
            print(f"{ep:<32} | {len(lats):<7} | {errs:<7} | {p50:<9.2f} | {p95:<9.2f} | {p99:<9.2f} | {max_lat:<8.2f}")

        print("-" * 85)
        overall_p50 = calculate_percentile(all_latencies, 50)
        overall_p95 = calculate_percentile(all_latencies, 95)
        overall_p99 = calculate_percentile(all_latencies, 99)
        overall_max = max(all_latencies) if all_latencies else 0.0
        print(f"{'UMUMIY (JAMI)':<32} | {total_requests:<7} | {total_errors:<7} | {overall_p50:<9.2f} | {overall_p95:<9.2f} | {overall_p99:<9.2f} | {overall_max:<8.2f}")
        print("=" * 85 + "\n")


async def setup_test_environment(num_users: int) -> Tuple[List[dict], int, List[int]]:
    """
    Test ma'lumotlar bazasida 30 ta virtual ofitsiant, sinov stollari va taomlarni tayyorlash
    """
    from app.core.database import Base, engine, AsyncSessionLocal
    from app.models.restaurant import Restaurant, RestaurantSettings
    from app.models.user import User, UserRole
    from app.models.table import Table, TableStatus
    from app.models.menu import Category, MenuItem
    from app.core.security import get_password_hash

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    waiter_credentials = []
    common_table_id = 1
    other_table_ids = list(range(2, 21))

    async with AsyncSessionLocal() as session:
        # 1. Restoran
        rest = await session.get(Restaurant, 1)
        if not rest:
            session.add(Restaurant(id=1, name="Load Test Choyxona", slug="load-test"))

        settings = await session.get(RestaurantSettings, 1)
        if not settings:
            session.add(RestaurantSettings(
                restaurant_id=1,
                service_fee_percent=10.0,
                printer_kitchen1_name="XP-Kitchen",
                auto_print_kitchen=True,
            ))

        # 2. Stol 1 (Umumiy hotspot stol) va boshqa stollar
        t1 = await session.get(Table, 1)
        if not t1:
            session.add(Table(id=1, restaurant_id=1, number=1, capacity=6, room="Asosiy", qr_token="qr-load-1", status=TableStatus.AVAILABLE))

        for tid in other_table_ids:
            t = await session.get(Table, tid)
            if not t:
                session.add(Table(id=tid, restaurant_id=1, number=tid, capacity=4, room="Zal", qr_token=f"qr-load-{tid}", status=TableStatus.AVAILABLE))

        # 3. Kategoriya va taom
        cat = await session.get(Category, 1)
        if not cat:
            session.add(Category(id=1, restaurant_id=1, name="Taomlar", sort_order=1))

        dish = await session.get(MenuItem, 1)
        if not dish:
            session.add(MenuItem(
                id=1,
                category_id=1,
                name="Choyxona Palov",
                price=35000.0,
                is_available=True,
                kitchen_station="hot_kitchen",
            ))

        # 4. 30 ta ofitsiant foydalanuvchisini tayyorlash
        hashed_pwd = get_password_hash("loadtest123")
        for i in range(1, num_users + 1):
            uname = f"waiter_load_{i}"
            u = await session.get(User, 10000 + i)
            if not u:
                u = User(
                    id=10000 + i,
                    username=uname,
                    full_name=f"Waiter Load {i}",
                    hashed_password=hashed_pwd,
                    role=UserRole.WAITER,
                    restaurant_id=1,
                    is_active=True,
                    is_approved=True,
                )
                session.add(u)
            waiter_credentials.append({"username": uname, "password": "loadtest123"})

        await session.commit()

    return waiter_credentials, common_table_id, other_table_ids


async def virtual_waiter_worker(
    waiter_id: int,
    creds: dict,
    client: AsyncClient,
    metrics: MetricsCollector,
    start_event: asyncio.Event,
    stop_event: asyncio.Event,
    common_table_id: int,
    other_table_ids: List[int],
):
    """
    1 ta virtual ofitsiantning ish jarayoni:
    1. Login qiladi.
    2. start_event berilishini kutadi (barcha 30 ofitsiant bir vaqtda boshlashi uchun).
    3. stop_event bo'lguncha doimiy ravishda:
       - 5% ehtimollik bilan umumiy stol (hotspot), 95% ehtimollik bilan tasodifiy stol
       - Zakaz ochadi (waiter-create)
       - Dozakaz qiladi (add-items)
       - Oshxonaga yuboradi (send-to-kitchen)
    """
    token: Optional[str] = None
    headers = {}

    # 1. Login
    t0 = time.perf_counter()
    try:
        resp = await client.post(
            "/api/v1/auth/login",
            json={"username": creds["username"], "password": creds["password"]},
        )
        latency = (time.perf_counter() - t0) * 1000.0
        is_err = resp.status_code >= 400
        await metrics.record("POST /auth/login", latency, is_err)
        if resp.status_code == 200:
            token = resp.json().get("access_token")
            headers["Authorization"] = f"Bearer {token}"
        else:
            return
    except Exception as ex:
        latency = (time.perf_counter() - t0) * 1000.0
        await metrics.record("POST /auth/login", latency, True)
        return

    # 2. Barcha ofitsiantlar login qilib bo'lishini kutamiz
    await start_event.wait()

    # 2. Buyurtma va oshxona tsikli
    while not stop_event.is_set():
        # 5% so'rovlar umumiy stolga (Table 1), 95% boshqa stollarga
        if random.random() < 0.05:
            target_table = common_table_id
        else:
            target_table = random.choice(other_table_ids)

        order_id = None

        # A: Buyurtma yaratish (POST /orders/waiter-create)
        t0 = time.perf_counter()
        try:
            resp = await client.post(
                "/api/v1/orders/waiter-create",
                json={
                    "restaurant_id": 1,
                    "table_id": target_table,
                    "order_type": "dine_in",
                    "items": [{"menu_item_id": 1, "quantity": random.randint(1, 3)}],
                },
                headers=headers,
            )
            lat = (time.perf_counter() - t0) * 1000.0
            is_err = resp.status_code not in (200, 201)
            await metrics.record("POST /orders/waiter-create", lat, is_err)
            if not is_err:
                order_id = resp.json().get("id")
        except Exception:
            lat = (time.perf_counter() - t0) * 1000.0
            await metrics.record("POST /orders/waiter-create", lat, True)

        if not order_id:
            await asyncio.sleep(0.05)
            continue

        # B: Dozakaz qo'shish (POST /orders/{order_id}/add-items)
        t0 = time.perf_counter()
        try:
            resp = await client.post(
                f"/api/v1/orders/{order_id}/add-items",
                json={
                    "items": [{"menu_item_id": 1, "quantity": 1}],
                    "send_to_kitchen_immediately": False,
                },
                headers=headers,
            )
            lat = (time.perf_counter() - t0) * 1000.0
            is_err = resp.status_code not in (200, 201)
            await metrics.record("POST /orders/add-items", lat, is_err)
        except Exception:
            lat = (time.perf_counter() - t0) * 1000.0
            await metrics.record("POST /orders/add-items", lat, True)

        # C: Oshxonaga yuborish (POST /orders/{order_id}/send-to-kitchen)
        t0 = time.perf_counter()
        try:
            resp = await client.post(
                f"/api/v1/orders/{order_id}/send-to-kitchen",
                headers=headers,
            )
            lat = (time.perf_counter() - t0) * 1000.0
            is_err = resp.status_code != 200
            await metrics.record("POST /orders/send-to-kitchen", lat, is_err)
        except Exception:
            lat = (time.perf_counter() - t0) * 1000.0
            await metrics.record("POST /orders/send-to-kitchen", lat, True)

        # Kichik oraliq (real ofitsiant kutish vaqti)
        await asyncio.sleep(random.uniform(0.01, 0.05))


async def run_load_test(
    base_url: str,
    num_users: int,
    duration: float,
    in_process: bool = False,
):
    from app.core.config import settings
    check_database_safety(settings.DATABASE_URL)

    print(f"\n[INFO] Yuklama testi boshlanmoqda...")
    print(f"[INFO] Baza: {settings.DATABASE_URL} (Xavfsizlik tekshiruvidan o'tdi)")
    print(f"[INFO] Virtual ofitsiantlar soni: {num_users} ta")
    print(f"[INFO] Test davomiyligi: {duration} soniya")
    print(f"[INFO] Rejim: {'In-Process ASGI' if in_process else f'HTTP ({base_url})'}")

    creds_list, common_tbl, other_tbls = await setup_test_environment(num_users)
    metrics = MetricsCollector()
    start_event = asyncio.Event()
    stop_event = asyncio.Event()

    client_kwargs = {
        "timeout": httpx.Timeout(20.0, connect=10.0),
    }

    if in_process:
        from app.main import app
        client_kwargs["transport"] = ASGITransport(app=app)
        client_kwargs["base_url"] = "http://test"
    else:
        client_kwargs["base_url"] = base_url

    async with AsyncClient(**client_kwargs) as client:
        # Ishchilarni parallel ishga tushirish
        workers = [
            asyncio.create_task(
                virtual_waiter_worker(
                    waiter_id=i + 1,
                    creds=creds_list[i],
                    client=client,
                    metrics=metrics,
                    start_event=start_event,
                    stop_event=stop_event,
                    common_table_id=common_tbl,
                    other_table_ids=other_tbls,
                )
            )
            for i in range(num_users)
        ]

        print(f"[PROGRESS] {num_users} ta ofitsiant tizimga login qilmoqda...")
        for _ in range(60):
            if len(metrics.latencies.get("POST /auth/login", [])) >= num_users:
                break
            await asyncio.sleep(0.5)

        print(f"[PROGRESS] Ofitsiantlar login qildi. Sinov yuborilmoqda ({duration}s)...")
        start_event.set()
        start_time = time.time()

        # Test davomiyligini kutish
        await asyncio.sleep(duration)
        stop_event.set()

        # Barcha vazifalarning yakunlanishini kutish
        await asyncio.gather(*workers, return_exceptions=True)
        elapsed = time.time() - start_time

    metrics.print_summary(elapsed, num_users)


def main():
    parser = argparse.ArgumentParser(description="RestAron - Yuqori yuklama va poyga holatlari testi (Load Test)")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="FastAPI server manzili")
    parser.add_argument("--users", type=int, default=30, help="Virtual ofitsiantlar soni (standart: 30)")
    parser.add_argument("--duration", type=float, default=15.0, help="Test davomiyligi soniyalarda (standart: 15)")
    parser.add_argument("--in-process", action="store_true", help="Serverni ishga tushirmasdan to'g'ridan-to'g'ri ASGI orqali testlash")
    parser.add_argument("--db-url", default=None, help="Test bazasi URL manzili (masalan: sqlite+aiosqlite:///./test_load.db)")
    args = parser.parse_args()

    # Agar maxsus db-url berilgan bo'lsa yoki DATABASE_URL o'rnatilmagan bo'lsa
    if args.db_url:
        os.environ["DATABASE_URL"] = args.db_url
        os.environ["SYNC_DATABASE_URL"] = args.db_url.replace("sqlite+aiosqlite", "sqlite")
    elif "test" not in os.environ.get("DATABASE_URL", "").lower():
        # Xavfsiz test bazasiga yo'naltirish
        default_test_db = os.path.join(_backend_dir, "restaron_load_test.db").replace("\\", "/")
        os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{default_test_db}"
        os.environ["SYNC_DATABASE_URL"] = f"sqlite:///{default_test_db}"

    # Config yuklanganidan keyin tekshiruv
    from app.core.config import settings
    if args.db_url:
        settings.DATABASE_URL = os.environ["DATABASE_URL"]
        settings.SYNC_DATABASE_URL = os.environ["SYNC_DATABASE_URL"]

    asyncio.run(
        run_load_test(
            base_url=args.base_url,
            num_users=args.users,
            duration=args.duration,
            in_process=args.in_process or (args.base_url == "http://127.0.0.1:8000"),
        )
    )


if __name__ == "__main__":
    main()
