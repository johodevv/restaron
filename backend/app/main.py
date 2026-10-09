"""
RestAron — Asosiy FastAPI ilovasi
"""
import os
from datetime import datetime
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
from app.routers import auth, users, restaurants, tables, menu, orders, stats, notifications, reviews, ws, debts, receipts

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
    try:
        from seed import seed
        await seed()
    except Exception as e:
        print(f"[WARN] Auto seed xatosi: {e}")

    print(f"[OK] {settings.APP_NAME} ishga tushdi!")
    yield
    print("[STOP] Server to'xtatildi.")


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
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS — Restoran ichki Wi-Fi (192.168.x.x), mobil telefonlar, localhost va bulutli domenlarni to'liq qo'llab-quvvatlash
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r".*",
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
class CachedStaticFiles(StaticFiles):
    """Rasmlarni brauzer keshida uzoq saqlaydigan static fayl xizmati."""

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
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": APP_VERSION["commit"],
        "updated_at": APP_VERSION["date"],
    }


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
