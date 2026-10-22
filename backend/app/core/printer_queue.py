"""
RestAron — Printer Retry Queue (Chop etish navbati va qayta urinish)
Printer o'chiq, kabeli uzilgan yoki tarmoqda bo'lmaganda cheklarni yo'qotmasdan
ma'lumotlar bazasida (print_jobs jadvali) xavfsiz navbatga oladi va printer qayta
ulanganda avtomatik ravishda chop etadi. Server o'chib-yonsa ham navbat yo'qolmaydi!
"""
import asyncio
import time
import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List, Set
from dataclasses import dataclass, field

from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.print_job import PrintJob

logger = logging.getLogger("printer_queue")

# ─── Zudlik bilan uyg'otish hodisasi va holatlar ─────────────────────
_wake_event: Optional[asyncio.Event] = None
_worker_task: Optional[asyncio.Task] = None
_running: bool = False

# Printer bo'yicha alohida lock'lar va faol vazifalar
_printer_locks: Dict[str, asyncio.Lock] = {}
_busy_printers: Set[str] = set()
_active_job_ids: Set[int] = set()
_running_tasks: Set[asyncio.Task] = set()


def get_wake_event() -> asyncio.Event:
    """Joriy event loop'ga mos asyncio.Event ni qaytaradi (loop o'zgarganda yangilanadi)"""
    global _wake_event
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if _wake_event is None:
        _wake_event = asyncio.Event()
    elif loop is not None and getattr(_wake_event, "_loop", None) not in (None, loop):
        _wake_event = asyncio.Event()
    return _wake_event


def get_printer_key(printer_name: Optional[str]) -> str:
    """
    Printer uchun unikal lock kaliti:
    - LAN printer: 'ip:port' (masalan: 192.168.1.100:9100)
    - USB / Windows printer: printer nomi (masalan: XP-Q80A yoki __default__)
    """
    from app.core.printer_service import detect_transport
    raw = (printer_name or "").strip()
    if detect_transport(raw) == "lan":
        if ":" in raw:
            parts = raw.split(":")
            port = parts[1] if len(parts) > 1 and parts[1] else "9100"
            return f"{parts[0]}:{port}"
        return f"{raw}:9100"
    return raw if raw else "__default__"


def get_printer_lock(printer_key: str) -> asyncio.Lock:
    """Har bir printer uchun alohida asyncio.Lock (loop xavfsiz)"""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    lock = _printer_locks.get(printer_key)
    if lock is None or (loop is not None and getattr(lock, "_loop", None) not in (None, loop)):
        lock = asyncio.Lock()
        _printer_locks[printer_key] = lock
    return lock


def wake_printer_worker():
    """Tranzaksiya commit qilingandan keyin workerni zudlik bilan uyg'otish"""
    get_wake_event().set()



async def enqueue_print_job(
    db: AsyncSession,
    *,
    restaurant_id: int,
    order_id: Optional[int] = None,
    ticket_type: str = "kitchen",
    printer_name: str,
    raw_text: str,
    options: Optional[Dict[str, Any]] = None,
) -> PrintJob:
    """
    Chop etish ishini berilgan sessiyaga qo'shadi va flush qiladi.
    DIQQAT: commit QILMAYDI, chaqiruvchi commit qilishi kerak!
    Commit'dan keyin `wake_printer_worker()` chaqiriladi.
    """
    job = PrintJob(
        restaurant_id=restaurant_id,
        order_id=order_id,
        ticket_type=ticket_type,
        printer_name=printer_name or "",
        raw_text=raw_text or "",
        options=options,
        status="pending",
        attempts=0,
        next_attempt_at=datetime.now(timezone.utc),
        alerted=False,
    )
    db.add(job)
    await db.flush()
    await db.refresh(job)
    return job


async def _execute_print_job(job_id: int):
    """
    Alohida printerning navbatdagi ishini bajarish:
    1. 'printing' holatiga o'tkazish
    2. Chop etishga urinish
    3. Muvaffaqiyat (done) yoki xato (attempts += 1, backoff, alert)
    """
    from app.core.database import AsyncSessionLocal
    from app.core.printer_service import async_print_to_windows_printer
    from app.websockets.manager import manager as ws_manager

    # 1. Bazadan ishni olish va status='printing' qilish
    async with AsyncSessionLocal() as session:
        job = await session.get(PrintJob, job_id)
        if not job or job.status != "pending":
            return
        job.status = "printing"
        await session.commit()

        raw_text = job.raw_text
        printer_name = job.printer_name
        options = dict(job.options) if job.options else {}
        restaurant_id = job.restaurant_id
        already_alerted = job.alerted

    # 2. Chop etish
    try:
        res = await async_print_to_windows_printer(
            raw_text=raw_text,
            printer_name=printer_name,
            **options,
        )
        success = bool(res.get("success"))
        error_msg = res.get("error") if not success else None
    except Exception as e:
        success = False
        error_msg = str(e)

    # 3. Natijani qayd etish
    now = datetime.now(timezone.utc)
    should_send_alert = False
    should_send_ok = False
    pending_count = 0

    async with AsyncSessionLocal() as session:
        job = await session.get(PrintJob, job_id)
        if not job:
            return

        if success:
            job.status = "done"
            job.printed_at = now
            job.last_error = None
            if already_alerted:
                should_send_ok = True
                logger.info(f"PrintJob #{job_id} muvaffaqiyatli chop etildi (alert holati yechildi)")
            else:
                logger.info(f"PrintJob #{job_id} muvaffaqiyatli chop etildi")
        else:
            job.attempts += 1
            job.last_error = error_msg or "Chop etishda noma'lum xatolik"
            # min(30, 2 * attempts) soniya kutish
            delay_sec = min(30, 2 * job.attempts)
            job.next_attempt_at = now + timedelta(seconds=delay_sec)
            job.status = "pending"
            logger.warning(
                f"PrintJob #{job_id} xato berdi (attempts={job.attempts}, keyingi urinish: {delay_sec}s): {job.last_error}"
            )

            # attempts 5 ga yetganda bir marta WebSocket orqali admin va waiter rollariga bildirishnoma
            if job.attempts >= 5 and not job.alerted:
                job.alerted = True
                should_send_alert = True
                cnt_res = await session.execute(
                    select(func.count(PrintJob.id)).where(
                        PrintJob.restaurant_id == restaurant_id,
                        PrintJob.printer_name == printer_name,
                        PrintJob.status.in_(["pending", "printing"]),
                    )
                )
                pending_count = cnt_res.scalar() or 1

        await session.commit()

    # 4. WebSocket xabarlari
    try:
        if should_send_alert:
            await ws_manager.broadcast_to_roles(
                restaurant_id=restaurant_id,
                roles=["admin", "waiter"],
                message={
                    "type": "print_alert",
                    "printer": printer_name,
                    "error": error_msg or "Chop etishda xatolik",
                    "pending_count": pending_count,
                },
            )
        elif should_send_ok:
            await ws_manager.broadcast_to_roles(
                restaurant_id=restaurant_id,
                roles=["admin", "waiter"],
                message={
                    "type": "print_ok",
                    "printer": printer_name,
                },
            )
    except Exception as ws_err:
        logger.warning(f"PrintJob WebSocket xabarnomasida xatolik: {ws_err}")


async def _run_job_wrapper(job_id: int, printer_key: str):
    """Printerni bloklab ishni bajaradi, so'ngra qulfni bo'shatadi va navbatni uyg'otadi"""
    lock = get_printer_lock(printer_key)
    try:
        async with lock:
            await _execute_print_job(job_id)
    except Exception as e:
        logger.error(f"Job #{job_id} ({printer_key}) bajarishda xatolik: {e}")
    finally:
        _busy_printers.discard(printer_key)
        _active_job_ids.discard(job_id)
        wake_printer_worker()


async def _worker_loop():
    """Asosiy fon vazifasi (worker)"""
    logger.info("Printer retry queue worker ishga tushdi")

    # 5. Startda tozalash va tiklash
    try:
        from app.core.database import AsyncSessionLocal
        async with AsyncSessionLocal() as session:
            # Startda status='printing' bo'lib qolgan ishlarni pending ga qaytar
            await session.execute(
                update(PrintJob)
                .where(PrintJob.status == "printing")
                .values(status="pending", next_attempt_at=datetime.now(timezone.utc))
            )
            # done ishlarni 7 kundan keyin o'chir (startda)
            cutoff = datetime.now(timezone.utc) - timedelta(days=7)
            await session.execute(
                delete(PrintJob)
                .where(PrintJob.status == "done", PrintJob.created_at < cutoff)
            )
            await session.commit()
            logger.info("Printer worker: start tozalash yakunlandi (printing->pending tiklandi, 7+ kunlik done o'chirildi)")
    except Exception as e:
        logger.error(f"Printer worker start tozalashda xatolik: {e}")

    while _running:
        try:
            wake_evt = get_wake_event()
            try:
                await asyncio.wait_for(wake_evt.wait(), timeout=2.0)
            except asyncio.TimeoutError:
                pass
            finally:
                wake_evt.clear()

            if not _running:
                break

            now = datetime.now(timezone.utc)
            async with AsyncSessionLocal() as session:
                stmt = (
                    select(PrintJob)
                    .where(
                        PrintJob.status == "pending",
                        PrintJob.next_attempt_at <= now,
                    )
                    .order_by(PrintJob.id.asc())
                    .limit(50)
                )
                res = await session.execute(stmt)
                ready_jobs = res.scalars().all()

            if not ready_jobs:
                continue

            for job in ready_jobs:
                if not _running:
                    break
                p_key = get_printer_key(job.printer_name)
                # Bir printerga bir vaqtda bitta ish, turli printerlar parallel
                if p_key in _busy_printers or job.id in _active_job_ids:
                    continue

                _busy_printers.add(p_key)
                _active_job_ids.add(job.id)

                task = asyncio.create_task(_run_job_wrapper(job.id, p_key))
                _running_tasks.add(task)
                task.add_done_callback(_running_tasks.discard)

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Printer worker siklida kutilmagan xatolik: {e}")
            await asyncio.sleep(2)


def start_printer_worker():
    """Worker taskni ishga tushirish"""
    global _worker_task, _running
    if _running and _worker_task and not _worker_task.done():
        return
    _running = True
    get_wake_event().clear()
    _worker_task = asyncio.create_task(_worker_loop())
    logger.info("Printer persistent worker muvaffaqiyatli boshlandi")


async def stop_printer_worker():
    """Workerni xavfsiz to'xtatish"""
    global _worker_task, _running
    _running = False
    get_wake_event().set()
    if _worker_task:
        _worker_task.cancel()
        try:
            await _worker_task
        except asyncio.CancelledError:
            pass
        _worker_task = None

    if _running_tasks:
        for t in list(_running_tasks):
            t.cancel()
        await asyncio.gather(*_running_tasks, return_exceptions=True)
        _running_tasks.clear()

    logger.info("Printer persistent worker to'xtatildi")


# ─── Eski kodlar va sinovlar uchun moslik qatlami (Backward compatibility) ──
@dataclass
class PrintJobInMemory:
    id: str
    raw_text: str
    printer_name: Optional[str] = None
    cut_paper: bool = True
    kwargs: Dict[str, Any] = field(default_factory=dict)
    attempts: int = 0
    max_attempts: int = 5
    created_at: float = field(default_factory=time.time)
    last_attempt_at: Optional[float] = None
    last_error: Optional[str] = None
    status: str = "pending"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "printer_name": self.printer_name,
            "status": self.status,
            "attempts": self.attempts,
            "max_attempts": self.max_attempts,
            "created_at": self.created_at,
            "last_attempt_at": self.last_attempt_at,
            "last_error": self.last_error,
            "text_preview": (self.raw_text[:60] + "...") if len(self.raw_text) > 60 else self.raw_text,
        }


class PrinterRetryQueue:
    """Moslik uchun eski class"""
    def __init__(self, check_interval_seconds: int = 10):
        self._queue: Dict[str, PrintJobInMemory] = {}
        self._lock = asyncio.Lock()
        self.check_interval = check_interval_seconds

    def enqueue(
        self,
        raw_text: str,
        printer_name: Optional[str] = None,
        cut_paper: bool = True,
        max_attempts: int = 5,
        **kwargs,
    ) -> PrintJobInMemory:
        job = PrintJobInMemory(
            id=str(uuid.uuid4()),
            raw_text=raw_text,
            printer_name=printer_name,
            cut_paper=cut_paper,
            max_attempts=max_attempts,
            kwargs=kwargs,
            status="pending",
        )
        self._queue[job.id] = job
        return job

    def start_worker(self):
        start_printer_worker()

    async def stop_worker(self):
        await stop_printer_worker()

    def get_status(self) -> Dict[str, Any]:
        return {
            "queue_running": _running,
            "total_jobs": len(self._queue),
            "pending_count": sum(1 for j in self._queue.values() if j.status in ("pending", "retrying")),
            "failed_count": sum(1 for j in self._queue.values() if j.status == "failed"),
            "completed_count": sum(1 for j in self._queue.values() if j.status == "completed"),
            "jobs": [j.to_dict() for j in list(self._queue.values())[-20:]],
        }

    def clear(self):
        self._queue.clear()


# Global singleton nusxa (eski importlar uchun)
printer_queue = PrinterRetryQueue()


async def print_with_retry(
    raw_text: str,
    printer_name: Optional[str] = None,
    cut_paper: bool = True,
    **kwargs,
) -> Dict[str, Any]:
    """
    Chekni chop etishga urinadi.
    Mavjud funksiya nomi — 7B vazifagacha to'liq saqlanadi.
    """
    from app.core.printer_service import async_print_to_windows_printer

    res = await async_print_to_windows_printer(
        raw_text=raw_text,
        printer_name=printer_name,
        cut_paper=cut_paper,
        **kwargs,
    )
    if res.get("success"):
        return res

    job = printer_queue.enqueue(
        raw_text=raw_text,
        printer_name=printer_name,
        cut_paper=cut_paper,
        **kwargs,
    )
    job.last_error = res.get("error")

    return {
        "success": True,
        "queued": True,
        "job_id": job.id,
        "printer": printer_name,
        "warning": f"Printerga to'g'ridan-to'g'ri ulanib bo'lmadi ({res.get('error')}). Chek qayta urinish navbatiga olindi.",
    }
