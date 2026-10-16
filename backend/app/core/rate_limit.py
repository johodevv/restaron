"""
RestAron — So'rovlar tezligini cheklash (Rate Limiter)
DDoS, brute-force va bot hujumlaridan himoya qilish uchun sliding window algoritmi.
"""
import time
from collections import defaultdict, deque
from typing import Optional, Callable
from fastapi import Request, HTTPException, status


class InMemoryRateLimiter:
    """Xotirada ishlaydigan sliding window rate limiter."""

    def __init__(self):
        # key -> deque of timestamps
        self._records = defaultdict(deque)
        self._last_cleanup = time.time()

    def _cleanup(self, now: float):
        """Eski yozuvlarni xotiradan tozalash (har 5 daqiqada bir marta)"""
        if now - self._last_cleanup < 300:
            return
        self._last_cleanup = now
        stale_keys = []
        for key, timestamps in self._records.items():
            while timestamps and now - timestamps[0] > 3600:
                timestamps.popleft()
            if not timestamps:
                stale_keys.append(key)
        for key in stale_keys:
            del self._records[key]

    def is_rate_limited(self, key: str, max_requests: int, window_seconds: int) -> tuple[bool, int]:
        """
        So'rov ruxsat etilgan limitdan oshganini tekshiradi.
        Qaytaradi: (is_limited: bool, retry_after_seconds: int)
        """
        now = time.time()
        self._cleanup(now)

        timestamps = self._records[key]
        cutoff = now - window_seconds

        # Oynadan tashqaridagi eski so'rovlarni olib tashlash
        while timestamps and timestamps[0] < cutoff:
            timestamps.popleft()

        if len(timestamps) >= max_requests:
            oldest = timestamps[0]
            retry_after = max(1, int(window_seconds - (now - oldest)))
            return True, retry_after

        timestamps.append(now)
        return False, 0


# Global singleton rate limiter nusxasi
rate_limiter_storage = InMemoryRateLimiter()


def get_client_ip(request: Request) -> str:
    """Mijozning haqiqiy IP manzilini aniqlash (proxy/load balancer hisobga olingan)"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # Masalan: "192.168.1.5, 10.0.0.1" -> birinchi IP
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    return request.client.host if request.client else "unknown"


class RateLimiter:
    """FastAPI Dependency sifatida ishlatiladigan cheklovchi."""

    def __init__(
        self,
        times: int,
        seconds: int,
        key_func: Optional[Callable[[Request], str]] = None,
        detail: Optional[str] = None,
    ):
        self.times = times
        self.seconds = seconds
        self.key_func = key_func
        self.detail = detail

    async def __call__(self, request: Request):
        if self.key_func:
            custom_key = self.key_func(request)
            key = f"{request.url.path}:{custom_key}"
        else:
            client_ip = get_client_ip(request)
            key = f"{request.url.path}:{client_ip}"

        limited, retry_after = rate_limiter_storage.is_rate_limited(
            key=key,
            max_requests=self.times,
            window_seconds=self.seconds,
        )

        if limited:
            error_msg = (
                self.detail
                or f"Juda ko'p so'rov yuborildi. Iltimos, {retry_after} soniyadan keyin qayta urinib ko'ring."
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=error_msg,
                headers={"Retry-After": str(retry_after)},
            )
