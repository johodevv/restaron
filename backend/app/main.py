"""
RestAron — Asosiy FastAPI ilovasi
"""
import os
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

# Static fayllar (rasmlar, QR kodlar)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

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
        if full_path.startswith("api/") or full_path.startswith("uploads/") or full_path in ["health", "docs", "redoc", "openapi.json"]:
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


@app.get("/health", tags=["🏥 Health Check"])
async def health():
    return {"status": "healthy", "app": settings.APP_NAME}
