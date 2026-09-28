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


async def create_tables():
    """Barcha jadvallarni yaratish (development uchun)"""
    import app.models  # noqa: F401
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
