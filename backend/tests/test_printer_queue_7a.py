"""
Test suite for VAZIFA 7A: Persistent Printer Queue
"""
import pytest
import asyncio
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch

from sqlalchemy import select, text
from fastapi.testclient import TestClient

from app.core.database import Base, engine, AsyncSessionLocal
from app.models.print_job import PrintJob
from app.models.restaurant import Restaurant, RestaurantSettings
from app.models.user import User, UserRole
from app.core.printer_queue import (
    enqueue_print_job,
    wake_printer_worker,
    get_wake_event,
    get_printer_key,
    get_printer_lock,
    _execute_print_job,
    _worker_loop,
    start_printer_worker,
    stop_printer_worker,
)
from app.main import app


@pytest.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


@pytest.mark.anyio
async def test_print_job_model_and_enqueue():
    async with AsyncSessionLocal() as session:
        # 1. Enqueue job (flush only, no commit)
        job = await enqueue_print_job(
            session,
            restaurant_id=1,
            order_id=42,
            ticket_type="kitchen",
            printer_name="XP-Q80A",
            raw_text="Test begunok",
            options={"cut_paper": True},
        )
        assert job.id is not None
        assert job.restaurant_id == 1
        assert job.order_id == 42
        assert job.ticket_type == "kitchen"
        assert job.printer_name == "XP-Q80A"
        assert job.raw_text == "Test begunok"
        assert job.options == {"cut_paper": True}
        assert job.status == "pending"
        assert job.attempts == 0
        assert job.alerted is False
        assert job.next_attempt_at is not None

        # Tranzaksiyani commit qilamiz
        await session.commit()

        # wake_printer_worker ni tekshirish
        get_wake_event().clear()
        wake_printer_worker()
        assert get_wake_event().is_set()



@pytest.mark.anyio
async def test_printer_key_normalization():
    # LAN IP
    assert get_printer_key("192.168.1.100") == "192.168.1.100:9100"
    assert get_printer_key("192.168.1.100:9200") == "192.168.1.100:9200"

    # USB
    assert get_printer_key("XP-Q80A") == "XP-Q80A"
    assert get_printer_key("") == "__default__"
    assert get_printer_key(None) == "__default__"

    # Lock creation
    lock1 = get_printer_lock("192.168.1.100:9100")
    lock2 = get_printer_lock("192.168.1.100:9100")
    assert lock1 is lock2


@pytest.mark.anyio
async def test_job_execution_success():
    async with AsyncSessionLocal() as session:
        job = await enqueue_print_job(
            session,
            restaurant_id=1,
            order_id=None,
            ticket_type="test",
            printer_name="192.168.1.120:9100",
            raw_text="Hello world",
        )
        await session.commit()
        job_id = job.id

    # async_print_to_windows_printer ni mock qilamiz
    with patch(
        "app.core.printer_service.async_print_to_windows_printer",
        new=AsyncMock(return_value={"success": True, "printer": "192.168.1.120:9100"}),
    ):
        await _execute_print_job(job_id)

    async with AsyncSessionLocal() as session:
        updated = await session.get(PrintJob, job_id)
        assert updated.status == "done"
        assert updated.printed_at is not None
        assert updated.last_error is None


@pytest.mark.anyio
async def test_job_execution_failure_backoff_and_alert():
    async with AsyncSessionLocal() as session:
        job = await enqueue_print_job(
            session,
            restaurant_id=1,
            ticket_type="kitchen",
            printer_name="192.168.1.130:9100",
            raw_text="Order runner",
        )
        job.attempts = 4  # 4 ta urinish bo'lgan, keyingisi 5-urinish
        await session.commit()
        job_id = job.id

    ws_mock = AsyncMock()
    with patch(
        "app.core.printer_service.async_print_to_windows_printer",
        new=AsyncMock(return_value={"success": False, "error": "Connection timed out"}),
    ), patch(
        "app.websockets.manager.manager.broadcast_to_roles",
        new=ws_mock,
    ):
        await _execute_print_job(job_id)

    async with AsyncSessionLocal() as session:
        updated = await session.get(PrintJob, job_id)
        assert updated.status == "pending"
        assert updated.attempts == 5
        assert updated.last_error == "Connection timed out"
        assert updated.alerted is True
        # next_attempt_at: now + min(30, 2*5) = 10 soniya
        assert updated.next_attempt_at is not None

    # WebSocket alert yuborilganini tekshirish
    ws_mock.assert_called_once()
    call_args = ws_mock.call_args[1]
    assert call_args["roles"] == ["admin", "waiter"]
    assert call_args["message"]["type"] == "print_alert"
    assert call_args["message"]["printer"] == "192.168.1.130:9100"
    assert call_args["message"]["error"] == "Connection timed out"

    # Endi shu alerted=True bo'lgan ish muvaffaqiyatli chop etilsa -> print_ok ketishi kerak
    ws_ok_mock = AsyncMock()
    with patch(
        "app.core.printer_service.async_print_to_windows_printer",
        new=AsyncMock(return_value={"success": True}),
    ), patch(
        "app.websockets.manager.manager.broadcast_to_roles",
        new=ws_ok_mock,
    ):
        await _execute_print_job(job_id)

    async with AsyncSessionLocal() as session:
        done_job = await session.get(PrintJob, job_id)
        assert done_job.status == "done"

    ws_ok_mock.assert_called_once()
    ok_call = ws_ok_mock.call_args[1]
    assert ok_call["message"]["type"] == "print_ok"
    assert ok_call["message"]["printer"] == "192.168.1.130:9100"


@pytest.mark.anyio
async def test_startup_cleanup():
    async with AsyncSessionLocal() as session:
        # 1. 'printing' holatida qolib ketgan ish
        stuck_job = PrintJob(
            restaurant_id=1,
            ticket_type="kitchen",
            printer_name="XP-Q80A",
            raw_text="Stuck job",
            status="printing",
        )
        session.add(stuck_job)

        # 2. 8 kun oldin 'done' bo'lgan eski ish
        old_done_job = PrintJob(
            restaurant_id=1,
            ticket_type="kitchen",
            printer_name="XP-Q80A",
            raw_text="Old done job",
            status="done",
            created_at=datetime.now(timezone.utc) - timedelta(days=8),
        )
        session.add(old_done_job)

        # 3. 2 kun oldin 'done' bo'lgan yangi ish (o'chirilmasligi kerak)
        recent_done_job = PrintJob(
            restaurant_id=1,
            ticket_type="kitchen",
            printer_name="XP-Q80A",
            raw_text="Recent done job",
            status="done",
            created_at=datetime.now(timezone.utc) - timedelta(days=2),
        )
        session.add(recent_done_job)

        await session.commit()
        stuck_id = stuck_job.id
        old_id = old_done_job.id
        recent_id = recent_done_job.id

    # Oldingi worker bo'lsa to'xtatamiz va yangidan ishga tushiramiz
    await stop_printer_worker()
    start_printer_worker()
    await asyncio.sleep(0.15)
    await stop_printer_worker()

    async with AsyncSessionLocal() as session:
        j_stuck = await session.get(PrintJob, stuck_id)
        assert j_stuck.status == "pending"  # printing -> pending tiklangan

        j_old = await session.get(PrintJob, old_id)
        assert j_old is None  # 8 kunlik ish o'chirilgan

        j_recent = await session.get(PrintJob, recent_id)
        assert j_recent is not None  # 2 kunlik ish saqlanib qolgan


@pytest.mark.anyio
async def test_receipts_print_jobs_endpoints():
    from app.core.security import get_current_user

    dummy_user = User(
        id=1,
        username="testadmin",
        full_name="Admin Test",
        role=UserRole.ADMIN,
        restaurant_id=1,
        is_active=True,
        is_approved=True,
    )

    test_printer = f"192.168.1.188:{uuid.uuid4().hex[:4]}"
    async with AsyncSessionLocal() as session:
        # Create a few jobs
        j1 = await enqueue_print_job(
            session,
            restaurant_id=1,
            ticket_type="kitchen",
            printer_name=test_printer,
            raw_text="Item 1",
        )
        j2 = await enqueue_print_job(
            session,
            restaurant_id=1,
            ticket_type="bar",
            printer_name=test_printer,
            raw_text="Item 2",
        )
        j2.last_error = "Printer offline"
        await session.commit()
        j1_id, j2_id = j1.id, j2.id

    app.dependency_overrides[get_current_user] = lambda: dummy_user
    try:
        with TestClient(app) as client:
            # 1. GET /api/v1/receipts/print-jobs/summary
            res_summary = client.get("/api/v1/receipts/print-jobs/summary?restaurant_id=1")
            assert res_summary.status_code == 200
            data = res_summary.json()
            assert isinstance(data, list)
            p_data = next((x for x in data if x.get("printer_name") == test_printer), None)
            assert p_data is not None
            assert p_data["pending_count"] == 2
            assert p_data["last_error"] == "Printer offline"
            assert p_data["oldest_age_seconds"] is not None


            # 2. GET /api/v1/receipts/print-jobs?ids=1,2
            res_jobs = client.get(f"/api/v1/receipts/print-jobs?ids={j1_id},{j2_id}")
            assert res_jobs.status_code == 200
            jobs_list = res_jobs.json()
            assert len(jobs_list) == 2
            assert jobs_list[0]["id"] == j1_id
            assert jobs_list[0]["status"] == "pending"
            assert jobs_list[1]["id"] == j2_id
            assert jobs_list[1]["status"] == "pending"
    finally:
        app.dependency_overrides.pop(get_current_user, None)

