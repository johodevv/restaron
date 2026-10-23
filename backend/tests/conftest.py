"""
Pytest configuration for RestAron backend test suite.
1. Testlar HAQIQIY ishlab turgan 'restaron.db' bazasiga yozmasligi uchun
   DATABASE_URL va SYNC_DATABASE_URL ni vaqtinchalik test bazasiga yo'naltiradi.
2. Bu sozlama har qanday model yoki 'app' import qilinishidan OLDIN ishga tushadi.
"""
import os
import sys
import tempfile
import uuid
import pytest

# Backend papkasini sys.path ga qo'shamiz (app moduli topilishi uchun)
_backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

# Vaqtinchalik sqlite fayl bazasi
_temp_dir = tempfile.gettempdir()
_test_db_filename = f"restaron_test_{uuid.uuid4().hex[:10]}.db"
_test_db_path = os.path.join(_temp_dir, _test_db_filename).replace("\\", "/")

# Muhit o'zgaruvchilarini 'app' yoki 'config' import qilinishidan OLDIN o'rnatamiz
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_test_db_path}"
os.environ["SYNC_DATABASE_URL"] = f"sqlite:///{_test_db_path}"
os.environ["SQLITE_DB_PATH"] = _test_db_path
os.environ['UPLOAD_DIR'] = os.path.join(_temp_dir, f'restaron_uploads_{uuid.uuid4().hex[:10]}')

# Agar config allaqachon yuklangan bo'lsa, settings obyektini ham yangilaymiz
try:
    from app.core.config import settings
    settings.DATABASE_URL = os.environ["DATABASE_URL"]
    settings.SYNC_DATABASE_URL = os.environ["SYNC_DATABASE_URL"]
except ImportError:
    pass


@pytest.fixture(scope="session", autouse=True)
def manage_test_db():
    """Test sessiyasi boshida jadvallarni yaratish va tugagach bazani tozalash"""
    sync_engine = None
    try:
        import app.models  # noqa: F401
        from sqlalchemy import create_engine
        from app.core.database import Base
        sync_engine = create_engine(os.environ["SYNC_DATABASE_URL"])
        Base.metadata.create_all(sync_engine)
    except Exception as e:
        print(f"[conftest] Test bazasini yaratishda xatolik: {e}")
    finally:
        if sync_engine:
            sync_engine.dispose()

    yield
    for ext in ("", "-wal", "-shm"):
        fpath = _test_db_path + ext
        if os.path.exists(fpath):
            try:
                os.remove(fpath)
            except Exception:
                pass


@pytest.fixture(autouse=True)
async def isolate_test_schema(manage_test_db, monkeypatch, tmp_path):
    """Each test owns an empty schema; fixtures cannot leak roles, settings or orders."""
    from app.core.database import engine, Base
    import app.core.pdf_generator as pdf
    monkeypatch.setattr(pdf, 'PDF_ARCHIVE_BASE', str(tmp_path / 'receipt_pdfs'))
    assert os.path.normcase(os.path.abspath(engine.url.database)) == os.path.normcase(os.path.abspath(_test_db_path))
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    import asyncio
    from app.routers.orders import _bg_tasks
    tasks = [task for task in _bg_tasks if task.get_loop() is asyncio.get_running_loop()]
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)
    await engine.dispose()
