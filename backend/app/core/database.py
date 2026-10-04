from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

is_sqlite = "sqlite" in settings.DATABASE_URL
engine_kwargs = {
    "echo": settings.DEBUG,
}
if not is_sqlite:
    engine_kwargs.update({
        "pool_pre_ping": True,
        "pool_size": 10,
        "max_overflow": 20,
    })

# Async engine
engine = create_async_engine(settings.DATABASE_URL, **engine_kwargs)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)
async_session_factory = AsyncSessionLocal



class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    """FastAPI Dependency — DB session olish"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def _sync_sqlite_migrations(sync_conn):
    """SQLite jadvallariga yangi ustunlarni avtomatik qo'shish"""
    from sqlalchemy import text
    migrations = {
        "restaurant_settings": [
            ("service_fee_percent", "FLOAT DEFAULT 12.0"),
            ("receipt_header", "VARCHAR(200) DEFAULT 'RestAron'"),
            ("receipt_footer", "VARCHAR(500) DEFAULT 'Tashrifingiz uchun rahmat!'"),
            ("receipt_address", "VARCHAR(500)"),
            ("receipt_phone", "VARCHAR(50)"),
            ("receipt_wifi_pass", "VARCHAR(100)"),
            ("printer_paper_width", "INTEGER DEFAULT 80"),
            ("printer_font_size", "VARCHAR(20) DEFAULT 'normal'"),
            ("printer_bar_name", "VARCHAR(100) DEFAULT ''"),
            ("bar_title", "VARCHAR(100) DEFAULT 'BAR (Ichimliklar)'"),
            ("printer_codepage", "INTEGER DEFAULT 17"),
            ("archive_retention_years", "INTEGER DEFAULT 3"),
            ("allow_debt_payment", "BOOLEAN DEFAULT 1"),
            ("allow_orders_from_qr", "BOOLEAN DEFAULT 0"),
            ("enable_telegram_notifications", "BOOLEAN DEFAULT 0"),
            ("telegram_bot_token", "VARCHAR(255)"),
            ("telegram_chat_id", "VARCHAR(100)"),
            ("enable_sms_reminders", "BOOLEAN DEFAULT 0"),
            ("sms_provider_api_key", "VARCHAR(255)"),
            ("sms_template", "TEXT"),
            ("printer_customer_name", "VARCHAR(100) DEFAULT 'XP-Q80A'"),
            ("printer_kitchen1_name", "VARCHAR(100) DEFAULT 'XP-Q80A'"),
            ("printer_kitchen2_name", "VARCHAR(100) DEFAULT 'XP-Q80A'"),
            ("kitchen1_title", "VARCHAR(100) DEFAULT '1-Oshxona (Qozon taomlari)'"),
            ("kitchen2_title", "VARCHAR(100) DEFAULT '2-Oshxona (Baliq / Somsa)'"),
            ("auto_print_kitchen", "BOOLEAN DEFAULT 1"),
            ("auto_print_customer_bill", "BOOLEAN DEFAULT 1"),
            ("direct_qr_access", "BOOLEAN DEFAULT 1"),
            ("enable_chef_kds", "BOOLEAN DEFAULT 0"),
        ],
        "categories": [
            ("name_cyrillic", "VARCHAR(100)"),
        ],
        "orders": [
            ("order_type", "VARCHAR(50) DEFAULT 'table'"),
            ("hall_name", "VARCHAR(100)"),
            ("kitchen_note", "TEXT"),
            ("receipt_note", "TEXT"),
            ("service_fee_percent", "FLOAT DEFAULT 12.0"),
            ("service_fee_amount", "FLOAT DEFAULT 0.0"),
            ("payment_method", "VARCHAR(50) DEFAULT 'cash'"),
            ("cash_amount", "FLOAT DEFAULT 0.0"),
            ("card_amount", "FLOAT DEFAULT 0.0"),
            ("click_amount", "FLOAT DEFAULT 0.0"),
            ("debt_amount", "FLOAT DEFAULT 0.0"),
            ("waiter_share_percent", "FLOAT DEFAULT 0.0"),
            ("waiter_share_amount", "FLOAT DEFAULT 0.0"),
            ("closed_at", "TIMESTAMP"),
        ],
        "order_items": [
            ("item_time", "VARCHAR(20)"),
            ("portion_size", "VARCHAR(50)"),
            ("weight", "FLOAT"),
            ("sent_to_kitchen", "BOOLEAN DEFAULT 0"),
            ("sent_to_kitchen_at", "TIMESTAMP"),
        ],
        "menu_items": [
            ("is_stop_list", "BOOLEAN DEFAULT 0"),
            ("name_cyrillic", "VARCHAR(200)"),
            ("description_cyrillic", "TEXT"),
            ("kitchen_station", "VARCHAR(50) DEFAULT 'hot_kitchen'"),
            ("is_weighted", "BOOLEAN DEFAULT 0"),
            ("unit", "VARCHAR(10) DEFAULT 'dona'"),
        ],
        "users": [
            ("commission_percent", "FLOAT DEFAULT 0.0"),
        ],
    }

    for table_name, cols in migrations.items():
        try:
            res = sync_conn.execute(text(f"PRAGMA table_info({table_name})"))
            existing_cols = {row[1] for row in res.fetchall()}
            if not existing_cols:
                continue
            for col_name, col_def in cols:
                if col_name not in existing_cols:
                    sync_conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_def}"))
        except Exception as e:
            pass


async def create_tables():
    """Barcha jadvallarni yaratish va mavjud jadvallarni yangilash"""
    import app.models  # noqa: F401
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        if is_sqlite:
            await conn.run_sync(_sync_sqlite_migrations)

