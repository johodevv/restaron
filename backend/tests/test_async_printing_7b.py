import re
import pytest
import asyncio
from pathlib import Path
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.print_job import PrintJob
from app.core.printer_queue import enqueue_print_job, wake_printer_worker
from app.routers.orders import _bg_tasks, create_bg_task


@pytest.mark.anyio
async def test_no_direct_printing_in_routers():
    """1 va 5: Routers ichida print_with_retry, async_print_to_windows_printer, printer_queue.enqueue qolmaganini tekshirish"""
    routers_dir = Path(__file__).resolve().parent.parent / "app" / "routers"
    target_files = [
        routers_dir / "orders.py",
        routers_dir / "tables.py",
        routers_dir / "receipts.py",
    ]

    forbidden_patterns = [
        r"\bprint_with_retry\(",
        r"\basync_print_to_windows_printer\(",
        r"\bprinter_queue\.enqueue\(",
    ]

    for fpath in target_files:
        assert fpath.exists(), f"{fpath} topilmadi"
        content = fpath.read_text(encoding="utf-8")
        for pat in forbidden_patterns:
            matches = re.findall(pat, content)
            assert not matches, f"{fpath.name} faylida bevosita chop etish chaqiruvi qolgan: {pat}"


@pytest.mark.anyio
async def test_bg_tasks_lifecycle():
    """4: create_bg_task modul darajasidagi _bg_tasks to'plamiga qo'shishi va tugagach tozalashi"""
    done_event = asyncio.Event()

    async def sample_coro():
        await asyncio.sleep(0.01)
        done_event.set()
        return 42

    task = create_bg_task(sample_coro())
    assert task in _bg_tasks, "Task _bg_tasks ga qo'shilmadi"

    await done_event.wait()
    await asyncio.sleep(0.02)  # Done callback ishlashi uchun kichik kutish

    assert task not in _bg_tasks, "Tugagan task _bg_tasks dan olib tashlanmadi"


@pytest.mark.anyio
async def test_enqueue_print_job_in_transaction():
    """2: enqueue_print_job tranzaksiya bilan birga commit qilinishi va wake_printer_worker chaqirilishi"""
    async with AsyncSessionLocal() as db:
        job = await enqueue_print_job(
            db,
            restaurant_id=1,
            order_id=99999,
            ticket_type="kitchen",
            printer_name="XP-Q80A",
            raw_text="Test Begunok 7B",
        )
        assert job.id is not None
        assert job.status == "pending"

        await db.commit()
        wake_printer_worker()

        # Bazadan tekshirish
        res = await db.execute(select(PrintJob).where(PrintJob.id == job.id))
        saved = res.scalar_one_or_none()
        assert saved is not None
        assert saved.order_id == 99999
        assert saved.raw_text == "Test Begunok 7B"
