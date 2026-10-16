"""
RestAron — Printer Retry Queue (Chop etish navbati va qayta urinish)
Printer o'chiq, kabeli uzilgan yoki tarmoqda bo'lmaganda cheklarni yo'qotmasdan
xotirada navbatga oladi va printer qayta ulanganda avtomatik ravishda chop etadi.
"""
import asyncio
import time
import uuid
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field, asdict

logger = logging.getLogger("printer_queue")


@dataclass
class PrintJob:
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
    status: str = "pending"  # "pending", "retrying", "completed", "failed"

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
    """Asinxron printer navbati va qayta urinish menejeri."""

    def __init__(self, check_interval_seconds: int = 10):
        self._queue: Dict[str, PrintJob] = {}
        self._lock = asyncio.Lock()
        self._worker_task: Optional[asyncio.Task] = None
        self._running = False
        self.check_interval = check_interval_seconds

    def enqueue(
        self,
        raw_text: str,
        printer_name: Optional[str] = None,
        cut_paper: bool = True,
        max_attempts: int = 5,
        **kwargs,
    ) -> PrintJob:
        """Yangi chop etish vazifasini navbatga qo'shish"""
        job = PrintJob(
            id=str(uuid.uuid4()),
            raw_text=raw_text,
            printer_name=printer_name,
            cut_paper=cut_paper,
            max_attempts=max_attempts,
            kwargs=kwargs,
            status="pending",
        )
        self._queue[job.id] = job
        logger.info(f"Printer vazifasi navbatga qo'shildi: job_id={job.id}, printer='{printer_name}'")
        return job

    async def execute_job(self, job: PrintJob) -> bool:
        """Vazifani printerga yuborish"""
        from app.core.printer_service import async_print_to_windows_printer

        job.attempts += 1
        job.last_attempt_at = time.time()
        job.status = "retrying"

        try:
            res = await async_print_to_windows_printer(
                job.raw_text,
                printer_name=job.printer_name,
                cut_paper=job.cut_paper,
                **job.kwargs,
            )
            if res.get("success"):
                job.status = "completed"
                job.last_error = None
                logger.info(f"Navbatdagi chek chop etildi: job_id={job.id}")
                return True
            else:
                job.last_error = res.get("error", "Noma'lum xato")
                if job.attempts >= job.max_attempts:
                    job.status = "failed"
                    logger.warning(f"Chop etish urinishlari tugadi: job_id={job.id}, xato: {job.last_error}")
                return False
        except Exception as e:
            job.last_error = str(e)
            if job.attempts >= job.max_attempts:
                job.status = "failed"
            logger.error(f"Printerga yuborishda kutilmagan xato (job_id={job.id}): {e}")
            return False

    async def _worker_loop(self):
        """Orqa fonda navbatdagi cheklarni qayta-qayta tekshirib chop etuvchi sikl"""
        logger.info(f"Printer retry queue worker ishga tushdi (interval: {self.check_interval}s)")
        while self._running:
            try:
                await asyncio.sleep(self.check_interval)
                async with self._lock:
                    # pending yoki retrying holatidagi vazifalarni olish
                    pending_jobs = [
                        j for j in self._queue.values()
                        if j.status in ("pending", "retrying") and j.attempts < j.max_attempts
                    ]

                for job in pending_jobs:
                    success = await self.execute_job(job)
                    if success:
                        # Muvaffaqiyatli bo'lsa navbatdan o'chirish
                        async with self._lock:
                            self._queue.pop(job.id, None)

                # 24 soatdan oshgan eski completed/failed vazifalarni tozalash
                now = time.time()
                async with self._lock:
                    stale_ids = [
                        jid for jid, j in self._queue.items()
                        if j.status in ("completed", "failed") and now - j.created_at > 86400
                    ]
                    for jid in stale_ids:
                        self._queue.pop(jid, None)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Printer retry worker siklida xatolik: {e}")
                await asyncio.sleep(5)

    def start_worker(self):
        """Worker taskni ishga tushirish"""
        if self._running and self._worker_task and not self._worker_task.done():
            return
        self._running = True
        self._worker_task = asyncio.create_task(self._worker_loop())

    async def stop_worker(self):
        """Workerni xavfsiz to'xtatish"""
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
            self._worker_task = None
        logger.info("Printer retry queue worker to'xtatildi")

    def get_status(self) -> Dict[str, Any]:
        """Navbat holatini olish"""
        total = len(self._queue)
        pending = sum(1 for j in self._queue.values() if j.status in ("pending", "retrying"))
        failed = sum(1 for j in self._queue.values() if j.status == "failed")
        completed = sum(1 for j in self._queue.values() if j.status == "completed")

        return {
            "queue_running": self._running,
            "total_jobs": total,
            "pending_count": pending,
            "failed_count": failed,
            "completed_count": completed,
            "jobs": [j.to_dict() for j in list(self._queue.values())[-20:]],
        }

    def clear(self):
        """Barcha navbatdagi vazifalarni tozalash"""
        self._queue.clear()


# Global singleton nusxa
printer_queue = PrinterRetryQueue()


async def print_with_retry(
    raw_text: str,
    printer_name: Optional[str] = None,
    cut_paper: bool = True,
    **kwargs,
) -> Dict[str, Any]:
    """
    Chekni chop etishga urinadi.
    Agar printer o'chiq bo'lsa, xatoni yutib yubormasdan navbatga qo'yadi va
    printer tarmoqqa ulanganda avtomatik chiqarilishini kafolatlaydi.
    """
    from app.core.printer_service import async_print_to_windows_printer

    # Dastlabki to'g'ridan-to'g'ri urinish
    res = await async_print_to_windows_printer(
        raw_text=raw_text,
        printer_name=printer_name,
        cut_paper=cut_paper,
        **kwargs,
    )
    if res.get("success"):
        return res

    # Birinchi urinish o'xshamasa -> Navbatga qo'shish
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
