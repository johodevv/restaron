import logging
import asyncio
import weakref
from contextlib import asynccontextmanager
from fastapi import Request
from sqlalchemy import event, text, inspect
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import AsyncAdaptedQueuePool
from app.core.config import settings

logger = logging.getLogger("database")

is_sqlite = "sqlite" in settings.DATABASE_URL
engine_kwargs = {
    "echo": settings.DEBUG,
}
if is_sqlite:
    # SQLite uchun bloklanishlarni oldini oluvchi 30 soniyalik kutish va multi-threading sozlamalari
    engine_kwargs.update({
        # SQLAlchemy 2.0.30 defaults to NullPool for file-based aiosqlite.
        # Reuse a bounded set of connections/worker threads instead of creating
        # and tearing down one for every request and printer status update.
        "poolclass": AsyncAdaptedQueuePool,
        "pool_size": 10,
        "max_overflow": 10,
        "pool_timeout": 30,
        "connect_args": {
            "timeout": 30.0,
            "check_same_thread": False,
        },
    })
else:
    # PostgreSQL (asyncpg) uchun Connection Pooling — High Concurrency (10,000+ buyurtma va rush hour)
    engine_kwargs.update({
        "pool_pre_ping": True,                      # Uzilgan ulanishlarni avtomatik aniqlash va tiklash
        "pool_size": getattr(settings, "DB_POOL_SIZE", 10),        # Asosiy doimiy faol ulanishlar soni
        "max_overflow": getattr(settings, "DB_MAX_OVERFLOW", 20),  # Rushtaymda qo'shimcha ochiladigan ulanishlar (jami 30 ta)
        "pool_timeout": getattr(settings, "DB_POOL_TIMEOUT", 30),  # Pool band bo'lsa navbatda kutish vaqti (soniya)
        "pool_recycle": getattr(settings, "DB_POOL_RECYCLE", 1800), # 30 daqiqada ulanishni yangilash (firewall/TCP drop oldini olish)
    })

# Async engine
engine = create_async_engine(settings.DATABASE_URL, **engine_kwargs)

if is_sqlite:
    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        """SQLite WAL (Write-Ahead Logging) rejimi: bir vaqtda bir nechta o'qish va yozish imkoni"""
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=FULL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.close()

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


_sqlite_write_gates = weakref.WeakKeyDictionary()


async def get_db(request: Request = None) -> AsyncSession:
    """FastAPI Dependency — DB session olish"""
    # Queue SQLite writers before opening a connection or reading auth data.
    # BEGIN IMMEDIATE also serializes writers in other processes. Reads use WAL.
    writes = request is not None and (
        request.method not in ('GET', 'HEAD', 'OPTIONS')
        or '/tables/scan/' in request.url.path
        or request.url.path.rstrip('/').endswith('/tables/zones')
    ) and not request.url.path.rstrip('/').endswith('/auth/login')
    gate = None
    if is_sqlite and writes:
        loop = asyncio.get_running_loop()
        gate = _sqlite_write_gates.setdefault(loop, asyncio.Lock())
        await gate.acquire()
    try:
        async with AsyncSessionLocal() as session:
            session.info['write_request'] = writes
            try:
                if is_sqlite and writes:
                    await session.execute(text('BEGIN IMMEDIATE'))
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    finally:
        if gate is not None:
            gate.release()


def write_session():
    """Background writers use the same SQLite queue as authenticated requests."""
    request = Request({'type': 'http', 'method': 'POST', 'path': '/background',
                       'scheme': 'http', 'server': ('localhost', 80), 'headers': [], 'query_string': b''})
    return asynccontextmanager(get_db)(request)


def _sync_schema_migrations(sync_conn):
    """SQLite jadvallariga yangi ustunlarni avtomatik qo'shish"""
    from sqlalchemy import text
    migrations = {
        "idempotency_keys": [("request_hash", "VARCHAR(64)")],
        "restaurant_settings": [
            ("service_fee_percent", "FLOAT DEFAULT 12.0"),
            # Sukut bo'yicha BO'SH — shunda chek tepasida restoran nomi
            # chiqadi. Ilgari bu yerda 'RestAron' turib, haqiqiy nomni
            # bosib ketardi.
            ("receipt_header", "VARCHAR(200)"),
            ("receipt_footer", "VARCHAR(500) DEFAULT 'Tashrifingiz uchun rahmat!'"),
            ("receipt_address", "VARCHAR(500)"),
            ("receipt_phone", "VARCHAR(50)"),
            ("receipt_wifi_pass", "VARCHAR(100)"),
            ("printer_paper_width", "INTEGER DEFAULT 80"),
            ("printer_font_size", "VARCHAR(20) DEFAULT 'katta'"),
            ("printer_char_spacing", "INTEGER DEFAULT 1"),
            ("printer_line_spacing", "VARCHAR(20) DEFAULT 'oddiy'"),
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
            ("printer_customer_name", "VARCHAR(100) DEFAULT NULL"),
            ("printer_kitchen1_name", "VARCHAR(100) DEFAULT NULL"),
            ("printer_kitchen2_name", "VARCHAR(100) DEFAULT NULL"),
            ("kitchen1_title", "VARCHAR(100) DEFAULT '1-Oshxona (Qozon taomlari)'"),
            ("kitchen2_title", "VARCHAR(100) DEFAULT '2-Oshxona (Baliq / Somsa)'"),
            ("auto_print_kitchen", "BOOLEAN DEFAULT 1"),
            ("auto_print_customer_bill", "BOOLEAN DEFAULT 1"),
            ("direct_qr_access", "BOOLEAN DEFAULT 1"),
            ("enable_chef_kds", "BOOLEAN DEFAULT 0"),
        ],
        "categories": [
            ("name_cyrillic", "VARCHAR(100)"),
            ("show_on_landing", "BOOLEAN DEFAULT 1"),
        ],
        "orders": [
            ("merged_into_order_id", "INTEGER"),
            ("version", "INTEGER NOT NULL DEFAULT 1"),
            ("advance_amount", "FLOAT NOT NULL DEFAULT 0"),
            ("order_type", "VARCHAR(50) DEFAULT 'table'"),
            ("hall_name", "VARCHAR(100)"),
            ("kitchen_note", "TEXT"),
            ("receipt_note", "TEXT"),
            ("service_fee_percent", "FLOAT DEFAULT 12.0"),
            ("service_fee_amount", "FLOAT DEFAULT 0.0"),
            ("discount", "FLOAT DEFAULT 0.0"),
            ("payment_method", "VARCHAR(50) DEFAULT 'cash'"),
            ("cash_amount", "FLOAT DEFAULT 0.0"),
            ("card_amount", "FLOAT DEFAULT 0.0"),
            ("click_amount", "FLOAT DEFAULT 0.0"),
            ("debt_amount", "FLOAT DEFAULT 0.0"),
            ("waiter_share_percent", "FLOAT DEFAULT 0.0"),
            ("waiter_share_amount", "FLOAT DEFAULT 0.0"),
            ("closed_at", "TIMESTAMP"),
        ],
        "tables": [
            ("reserved_by_name", "VARCHAR(100)"),
            ("reserved_by_phone", "VARCHAR(50)"),
            ("reserved_time", "VARCHAR(50)"),
            ("reserved_guests", "INTEGER"),
            ("deposit_amount", "FLOAT DEFAULT 0.0"),
            ("reservation_note", "TEXT"),
        ],
        "order_items": [
            ("name_snapshot", "VARCHAR(200)"),
            ("prepared_quantity", "INTEGER NOT NULL DEFAULT 0"),
            ("item_time", "VARCHAR(20)"),
            ("portion_size", "VARCHAR(50)"),
            ("weight", "FLOAT"),
            ("sent_to_kitchen", "BOOLEAN DEFAULT 0"),
            ("sent_to_kitchen_at", "TIMESTAMP"),
            ("sent_quantity", "INTEGER DEFAULT 0"),
            ("manual_price", "FLOAT"),
        ],
        "menu_items": [
            ("is_deleted", "BOOLEAN NOT NULL DEFAULT 0"),
            ("is_stop_list", "BOOLEAN DEFAULT 0"),
            ("name_cyrillic", "VARCHAR(200)"),
            ("description_cyrillic", "TEXT"),
            ("kitchen_station", "VARCHAR(50) DEFAULT 'hot_kitchen'"),
            ("is_weighted", "BOOLEAN DEFAULT 0"),
            ("unit", "VARCHAR(10) DEFAULT 'dona'"),
        ],
        "users": [
            ("tokens_valid_after", "FLOAT NOT NULL DEFAULT 0"),
            ("commission_percent", "FLOAT DEFAULT 0.0"),
            ("is_approved", "BOOLEAN DEFAULT 0"),
        ],
        "receipt_archives": [("advance_amount", "FLOAT NOT NULL DEFAULT 0")],
    }

    added = set()

    for table_name, cols in migrations.items():
        try:
            inspector = inspect(sync_conn)
            existing_cols = {c['name'] for c in inspector.get_columns(table_name)} if inspector.has_table(table_name) else set()
            if not existing_cols:
                continue
            for col_name, col_def in cols:
                if col_name not in existing_cols:
                    if sync_conn.dialect.name == 'postgresql':
                        col_def = col_def.replace('BOOLEAN DEFAULT 1', 'BOOLEAN DEFAULT TRUE').replace('BOOLEAN DEFAULT 0', 'BOOLEAN DEFAULT FALSE').replace('BOOLEAN NOT NULL DEFAULT 0', 'BOOLEAN NOT NULL DEFAULT FALSE')
                    sync_conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_def}"))
                    added.add((table_name, col_name))
        except Exception as exc:
            raise RuntimeError(f'Schema migration failed for {table_name}') from exc

    if ('order_items', 'name_snapshot') in added:
        sync_conn.execute(text('UPDATE order_items SET name_snapshot = (SELECT name FROM menu_items WHERE menu_items.id = order_items.menu_item_id) WHERE name_snapshot IS NULL'))

    if ('order_items', 'prepared_quantity') in added:
        sync_conn.execute(text('UPDATE order_items SET prepared_quantity = COALESCE(sent_quantity, 0) WHERE is_prepared = TRUE'))

    # Mavjud xodimlar is_approved holati bo'sh bo'lsa tasdiqlangan (1) deb belgilaymiz
    try:
        sync_conn.execute(text("UPDATE users SET is_approved = TRUE WHERE is_approved IS NULL"))
    except Exception:
        pass

    # Chek sarlavhasida dasturning eski sukut nomi ("RestAron") qolib
    # ketgan bo'lsa tozalaymiz — u restoran nomini bosib, chek tepasida
    # "Dunyo Choyxonasi" o'rniga "RestAron" chiqarardi. Admin ataylab
    # yozgan boshqa nom o'z holicha qoladi.
    try:
        sync_conn.execute(text(
            "UPDATE restaurant_settings SET receipt_header = NULL "
            "WHERE LOWER(TRIM(COALESCE(receipt_header, ''))) IN "
            "('restaron', 'restaron restaurant', 'restaron pos')"
        ))
    except Exception:
        pass

    # Yangi "sent_quantity" ustuni qo'shilganda: oshxonaga ALLAQACHON
    # yuborilgan qatorlarni yuborilgan deb belgilaymiz. Aks holda
    # yangilangandan keyin ochiq stollardagi barcha taomlar oshxonaga
    # qaytadan chiqib ketardi.
    if ("order_items", "sent_quantity") in added:
        try:
            sync_conn.execute(text(
                "UPDATE order_items SET sent_quantity = quantity "
                "WHERE sent_to_kitchen = TRUE"
            ))
            sync_conn.execute(text(
                "UPDATE order_items SET sent_quantity = 0 "
                "WHERE sent_quantity IS NULL"
            ))
        except Exception:
            pass


def _sync_database_indexes(sync_conn):
    """SQLite jadvallari uchun zarur indekslar va unikal qisman indeksni yaratish"""
    indexes = [
        ("ix_orders_table_id", "orders", ["table_id"], "CREATE INDEX IF NOT EXISTS ix_orders_table_id ON orders(table_id)"),
        ("ix_orders_status", "orders", ["status"], "CREATE INDEX IF NOT EXISTS ix_orders_status ON orders(status)"),
        ("ix_orders_is_paid", "orders", ["is_paid"], "CREATE INDEX IF NOT EXISTS ix_orders_is_paid ON orders(is_paid)"),
        ("ix_orders_created_at", "orders", ["created_at"], "CREATE INDEX IF NOT EXISTS ix_orders_created_at ON orders(created_at)"),
        ("ix_orders_closed_at", "orders", ["closed_at"], "CREATE INDEX IF NOT EXISTS ix_orders_closed_at ON orders(closed_at)"),
        ("ix_orders_waiter_id", "orders", ["waiter_id"], "CREATE INDEX IF NOT EXISTS ix_orders_waiter_id ON orders(waiter_id)"),
        ("ix_orders_restaurant_id_created_at", "orders", ["restaurant_id", "created_at"], "CREATE INDEX IF NOT EXISTS ix_orders_restaurant_id_created_at ON orders(restaurant_id, created_at)"),
        ("ix_order_items_order_id", "order_items", ["order_id"], "CREATE INDEX IF NOT EXISTS ix_order_items_order_id ON order_items(order_id)"),
        ("ix_order_items_menu_item_id", "order_items", ["menu_item_id"], "CREATE INDEX IF NOT EXISTS ix_order_items_menu_item_id ON order_items(menu_item_id)"),
        ("ix_tables_restaurant_id", "tables", ["restaurant_id"], "CREATE INDEX IF NOT EXISTS ix_tables_restaurant_id ON tables(restaurant_id)"),
        ("ix_receipt_archives_order_id", "receipt_archives", ["order_id"], "CREATE INDEX IF NOT EXISTS ix_receipt_archives_order_id ON receipt_archives(order_id)"),
        ("ix_debts_order_id", "debts", ["order_id"], "CREATE INDEX IF NOT EXISTS ix_debts_order_id ON debts(order_id)"),
        ("ix_notifications_restaurant_id", "notifications", ["restaurant_id"], "CREATE INDEX IF NOT EXISTS ix_notifications_restaurant_id ON notifications(restaurant_id)"),
    ]

    for idx_name, table_name, cols, create_sql in indexes:
        try:
            inspector = inspect(sync_conn)
            existing_cols = {c['name'] for c in inspector.get_columns(table_name)} if inspector.has_table(table_name) else set()
            if not existing_cols:
                logger.warning("Indeks yaratilmadi: '%s' jadvali mavjud emas", table_name)
                continue
            missing = [c for c in cols if c not in existing_cols]
            if missing:
                logger.warning("Indeks '%s' yaratilmadi: '%s' jadvalida ustunlar mavjud emas: %s", idx_name, table_name, missing)
                continue
            sync_conn.execute(text(create_sql))
        except Exception as exc:
            logger.warning("Indeks '%s' yaratishda xatolik yuz berdi: %s", idx_name, exc)

    # Unikal qisman indeks: bitta stolda faqat bitta ochiq buyurtma bo'lishi mumkin
    try:
        orders_cols = {c['name'] for c in inspect(sync_conn).get_columns('orders')}
        if all(col in orders_cols for col in ("table_id", "is_paid", "status")):
            dup_res = sync_conn.execute(text(
                "SELECT table_id, COUNT(*) as cnt FROM orders "
                "WHERE table_id IS NOT NULL AND is_paid = FALSE AND status NOT IN ('CANCELLED', 'PAID') "
                "GROUP BY table_id HAVING COUNT(*) > 1"
            ))
            dup_tables = [row[0] for row in dup_res.fetchall()]
            if dup_tables:
                logger.warning(
                    "Unikal qisman indeks (ux_orders_one_open_per_table) yaratilmadi: "
                    "quyidagi stollarda bir nechta ochiq buyurtmalar mavjud (table_id): %s",
                    dup_tables,
                )
            else:
                sync_conn.execute(text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS ux_orders_one_open_per_table "
                    "ON orders(table_id) WHERE table_id IS NOT NULL AND is_paid = FALSE "
                    "AND status NOT IN ('CANCELLED','PAID')"
                ))
        else:
            logger.warning("ux_orders_one_open_per_table indeksi yaratilmadi: orders jadvalida zarur ustunlar yo'q")
    except Exception as exc:
        logger.warning("Unikal qisman indeks yaratishda kutilmagan xatolik: %s", exc)


async def create_tables():
    """Barcha jadvallarni yaratish va mavjud jadvallarni yangilash"""
    import app.models  # noqa: F401
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_sync_schema_migrations)
        await conn.run_sync(_sync_database_indexes)
        # Har safar server ishga tushganda bo'sh bo'lgan tasdiqlarni tiklash
        try:
            await conn.execute(text("UPDATE users SET is_approved = TRUE WHERE is_approved IS NULL"))
        except Exception:
            pass
        # 24 soatdan eski idempotency yozuvlarini startda tozalash
        try:
            from app.core.idempotency import cleanup_expired_idempotency_keys_sync
            await conn.run_sync(cleanup_expired_idempotency_keys_sync)
        except Exception:
            pass

