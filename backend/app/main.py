"""
RestAron — Asosiy FastAPI ilovasi
"""
import os
import re
from datetime import datetime, timezone
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

from app.core.config import settings
from app.core.database import create_tables

# Routerlar
from app.routers import auth, users, restaurants, tables, menu, orders, stats, notifications, reviews, ws, debts, receipts, audit

# Upload papkalarini yaratish (import vaqtida kerak)
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(os.path.join(settings.UPLOAD_DIR, "qr_codes"), exist_ok=True)
os.makedirs(os.path.join(settings.UPLOAD_DIR, "menu_items"), exist_ok=True)
os.makedirs(os.path.join(settings.UPLOAD_DIR, "logos"), exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup va shutdown hodisalari"""
    # Jadvallarni yaratish
    await create_tables()
    if os.getenv("AUTO_SEED", "false").lower() in ("1", "true", "yes"):
        try:
            from seed import seed
            await seed()
        except Exception as e:
            print(f"[WARN] Auto seed xatosi: {e}")

    # Printer retry queue workerni ishga tushirish
    from app.core.printer_queue import printer_queue
    printer_queue.start_worker()

    # WebSocket heartbeat monitorini ishga tushirish
    from app.websockets.manager import manager as ws_manager
    ws_manager.start_heartbeat(interval_seconds=25, timeout_seconds=60)

    print(f"[OK] {settings.APP_NAME} ishga tushdi!")
    yield
    await ws_manager.stop_heartbeat()
    await printer_queue.stop_worker()
    print("[STOP] Server to'xtatildi.")


docs_enabled = bool(settings.DEBUG or getattr(settings, "ENABLE_DOCS", False))

app = FastAPI(
    title=f"{settings.APP_NAME} API",
    description="""
## 🍽️ RestAron — Restoran Boshqaruv Tizimi

### Panellar:
- **Mijoz**: QR kod → Menyu → Buyurtma → Baho
- **Ofitsiant**: Real-time bildirishnomalar → Buyurtmalar
- **Oshpaz**: Buyurtma qabul → Tayyor belgisi
- **Admin**: Boshqaruv paneli, statistika, QR kodlar
- **Developer**: Server monitoring, komissiya

### Autentifikatsiya:
Bearer JWT token ishlatiladi. `/auth/login` orqali token oling.
    """,
    version="1.0.0",
    docs_url="/docs" if docs_enabled else None,
    redoc_url="/redoc" if docs_enabled else None,
    openapi_url="/openapi.json" if docs_enabled else None,
    lifespan=lifespan,
)


def build_cors_regex() -> str:
    """Xavfsiz CORS regex: Faqat localhost, restoran Wi-Fi (LAN) va ruxsat berilgan domenlar."""
    patterns = [
        r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
        r"https?://192\.168\.\d+\.\d+(:\d+)?",
        r"https?://10\.\d+\.\d+\.\d+(:\d+)?",
        r"https?://172\.(1[6-9]|2\d|3[01])\.\d+\.\d+(:\d+)?",
    ]
    for url_val in [settings.FRONTEND_URL, settings.QR_BASE_URL]:
        if url_val and not any(loc in url_val for loc in ["localhost", "127.0.0.1"]):
            cleaned = url_val.strip().rstrip("/")
            if cleaned:
                patterns.append(re.escape(cleaned) + r"(:\d+)?")
    allowed_extra = getattr(settings, "ALLOWED_ORIGINS", "")
    if allowed_extra:
        for domain in allowed_extra.split(","):
            cleaned = domain.strip().rstrip("/")
            if cleaned:
                patterns.append(re.escape(cleaned) + r"(:\d+)?")

    return rf"^({'|'.join(patterns)})$"


# CORS — Restoran ichki Wi-Fi tarmog'i, mobil telefonlar va xavfsiz domenlar
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=build_cors_regex(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# ─── Static fayllar (rasmlar, QR kodlar) ──────────────────────────
#
# Rasm fayl nomi UUID — mazmuni hech qachon o'zgarmaydi. Shuning uchun
# brauzerga "bu faylni bir yil saqla" deymiz. Aks holda mijoz har safar
# kategoriyani almashtirganda har bir rasm uchun serverga qayta murojaat
# qilinadi va menyu sekin ochiladi.
# Agar rasm diskdan o'chirilgan bo'lsa (404), brauzer keshidagi eski nusxa
# ko'rinmasligi uchun Cache-Control: no-cache qaytaramiz.
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import Response, PlainTextResponse


class CachedStaticFiles(StaticFiles):
    """Rasmlarni brauzer keshida saqlaydigan static fayl xizmati."""

    async def get_response(self, path: str, scope) -> Response:
        try:
            response = await super().get_response(path, scope)
            if response.status_code >= 400:
                response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            return response
        except StarletteHTTPException as exc:
            return PlainTextResponse(
                exc.detail or "Not Found",
                status_code=exc.status_code,
                headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
            )

    def file_response(self, *args, **kwargs):
        resp = super().file_response(*args, **kwargs)
        try:
            resp.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        except Exception:
            pass
        return resp


app.mount("/uploads", CachedStaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# Routerlarni ulash
app.include_router(auth, prefix="/api/v1")
app.include_router(users, prefix="/api/v1")
app.include_router(restaurants, prefix="/api/v1")
app.include_router(tables, prefix="/api/v1")
app.include_router(menu, prefix="/api/v1")
app.include_router(orders, prefix="/api/v1")
app.include_router(stats, prefix="/api/v1")
app.include_router(notifications, prefix="/api/v1")
app.include_router(reviews, prefix="/api/v1")
app.include_router(ws, prefix="/api/v1")
app.include_router(debts, prefix="/api/v1")
app.include_router(receipts, prefix="/api/v1")
app.include_router(audit, prefix="/api/v1")


# ─── Health Check ─────────────────────────────────────────
# MUHIM: Bu endpoint SPA catch-all marshrutidan OLDIN ro'yxatdan o'tishi shart,
# aks holda "/{full_path:path}" uni soyalab qo'yadi va /health 404 qaytaradi.
def read_app_version() -> dict:
    """Ishlab turgan kod versiyasi (git commit) ni aniqlash.

    Git dasturi kerak emas — .git papkasidagi fayllar o'qiladi.
    Shu ma'lumot admin panelda ko'rsatiladi, shunda "yangiladim, lekin
    o'zgarmadi" degan holatda qaysi versiya ishlayotganini bilish mumkin.
    """
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    git_dir = os.path.join(root, ".git")
    info = {"commit": "nomalum", "date": None}
    try:
        head_path = os.path.join(git_dir, "HEAD")
        if not os.path.exists(head_path):
            return info
        head = open(head_path, encoding="utf-8").read().strip()
        stamp_path = head_path
        if head.startswith("ref:"):
            ref = head.split(" ", 1)[1].strip()
            ref_path = os.path.join(git_dir, *ref.split("/"))
            if os.path.exists(ref_path):
                sha = open(ref_path, encoding="utf-8").read().strip()
                stamp_path = ref_path
            else:
                # packed-refs ichidan qidiramiz
                sha = ""
                packed = os.path.join(git_dir, "packed-refs")
                if os.path.exists(packed):
                    for line in open(packed, encoding="utf-8"):
                        if line.strip().endswith(" " + ref):
                            sha = line.split(" ", 1)[0].strip()
                            break
        else:
            sha = head
        if sha:
            info["commit"] = sha[:7]
        # Oxirgi o'zgarish vaqti — HEAD faylining sanasi
        info["date"] = datetime.fromtimestamp(
            os.path.getmtime(stamp_path)
        ).strftime("%Y-%m-%d %H:%M")
    except Exception:
        pass
    return info


APP_VERSION = read_app_version()


@app.get("/health", tags=["🏥 Health Check"])
async def health():
    """
    Tizim salomatligi monitoringi:
    - Baza bilan real vaqtda aloqa (SELECT 1)
    - Disk xotirasi holati
    - Kod versiyasi va vaqt
    """
    from starlette.responses import JSONResponse
    from app.core.database import async_session_factory
    from app.core.disk_utils import get_free_disk_mb

    db_status = "connected"
    db_latency_ms = None
    is_db_healthy = True

    start_time = datetime.now()
    try:
        from sqlalchemy import text
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
        db_latency_ms = round((datetime.now() - start_time).total_seconds() * 1000, 2)
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
        is_db_healthy = False

    free_mb = get_free_disk_mb()
    disk_healthy = free_mb >= 50.0

    status_str = "healthy"
    status_code = 200
    if not is_db_healthy:
        status_str = "unhealthy"
        status_code = 503
    elif not disk_healthy:
        status_str = "warning_disk_low"

    content = {
        "status": status_str,
        "database": {
            "status": db_status,
            "latency_ms": db_latency_ms,
        },
        "disk": {
            "free_mb": round(free_mb, 1),
            "status": "ok" if disk_healthy else "low_space",
        },
        "app": settings.APP_NAME,
        "version": APP_VERSION["commit"],
        "updated_at": APP_VERSION["date"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    if status_code != 200:
        return JSONResponse(status_code=status_code, content=content)
    return content


# ─── Frontend Statik Fayllarini Taqdim Etish (Standalone Server Rejimi) ───
from fastapi.responses import FileResponse
from fastapi import HTTPException

frontend_dist = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist"))
if os.path.exists(frontend_dist) and os.path.exists(os.path.join(frontend_dist, "index.html")):
    assets_dir = os.path.join(frontend_dist, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/", include_in_schema=False)
    async def serve_spa_root():
        return FileResponse(os.path.join(frontend_dist, "index.html"))

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        # Backend marshrutlari bu yerga tushmasligi kerak — ular yuqorida
        # ro'yxatdan o'tgan, shuning uchun bu yerga faqat noma'lum yo'llar keladi.
        BACKEND_PREFIXES = (
            "api/", "uploads/", "assets/", "docs", "redoc", "openapi.json", "health",
        )
        if any(full_path.startswith(p) for p in BACKEND_PREFIXES):
            raise HTTPException(status_code=404, detail="Not found")
        file_path = os.path.join(frontend_dist, full_path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(frontend_dist, "index.html"))
else:
    @app.get("/", tags=["🏠 Asosiy"])
    async def root():
        return {
            "app": settings.APP_NAME,
            "version": "1.0.0",
            "docs": "/docs",
            "status": "running ✅",
        }
