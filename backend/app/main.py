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

# CORS
allowed_origins = [
    settings.FRONTEND_URL,
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:4173",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=r"https://.*\.vercel\.app|https://.*\.onrender\.com",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
