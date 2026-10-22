"""
Vaqt va Sana yordamchilari (Timezone Utilities)
Qoida:
- Ma'lumotlar bazasida (SQLite/PostgreSQL) vaqt UTC (naive) formatida saqlanadi.
- Foydalanuvchiga va barcha hisobotlarda Asia/Tashkent (UTC+5) vaqti ishlatiladi.
"""
from datetime import datetime, date, timedelta, timezone
from zoneinfo import ZoneInfo
from typing import Optional, Union, Tuple

# O'zbekiston / Toshkent vaqt mintaqasi (UTC+5)
UZ_TZ = ZoneInfo("Asia/Tashkent")


def to_uz(dt: Optional[datetime]) -> Optional[datetime]:
    """
    Har qanday datetime obyektini Asia/Tashkent (UTC+5) vaqtiga o'girish.
    Agar dt naive bo'lsa, u bazadan olingan deb hisoblanadi va UTC deb qabul qilinadi.
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        # Bazadagi UTC naive vaqtni timezone-aware UTC ga aylantiramiz
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(UZ_TZ)


def to_utc_naive(dt: Optional[datetime]) -> Optional[datetime]:
    """
    Datetime obyektini UTC naive (bazaga yozish uchun) formatiga o'tkazish.
    Agar dt naive bo'lsa, u Asia/Tashkent deb qabul qilinadi.
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UZ_TZ)
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def uz_now() -> datetime:
    """Asia/Tashkent mintaqasidagi joriy vaqt (timezone-aware)"""
    return datetime.now(UZ_TZ)


def utc_now_naive() -> datetime:
    """Joriy UTC vaqt (naive, bazaga yozish uchun)"""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def uz_day_bounds_utc(
    sana: Optional[Union[str, date, datetime]] = None,
) -> Tuple[datetime, datetime]:
    """
    Berilgan sana uchun Asia/Tashkent kunining (00:00:00 dan 24:00:00 / ertasi 00:00:00 gacha)
    UTC naive datetime chegaralarini qaytaradi: (start_utc_naive, end_utc_naive).

    Misol:
      sana = '2026-10-22'
      UZ kun: 2026-10-22 00:00:00 UZ -> 2026-10-21 19:00:00 UTC
              2026-10-23 00:00:00 UZ -> 2026-10-22 19:00:00 UTC
      Natija: (datetime(2026, 10, 21, 19, 0), datetime(2026, 10, 22, 19, 0))

    SQL da ishlatish:
      created_at >= start_utc AND created_at < end_utc
    """
    if sana is None:
        day_date = datetime.now(UZ_TZ).date()
    elif isinstance(sana, str):
        day_date = datetime.strptime(sana.strip()[:10], "%Y-%m-%d").date()
    elif isinstance(sana, datetime):
        # Agar datetime kelsa, avval UZ vaqtiga o'tkazib keyin sanasini olamiz
        day_date = to_uz(sana).date()
    elif isinstance(sana, date):
        day_date = sana
    else:
        raise ValueError(f"Noto'g'ri sana formati: {sana}")

    start_uz = datetime(day_date.year, day_date.month, day_date.day, 0, 0, 0, tzinfo=UZ_TZ)
    end_uz = start_uz + timedelta(days=1)

    start_utc = start_uz.astimezone(timezone.utc).replace(tzinfo=None)
    end_utc = end_uz.astimezone(timezone.utc).replace(tzinfo=None)

    return start_utc, end_utc


def uz_range_bounds_utc(
    start_sana: Optional[Union[str, date, datetime]] = None,
    end_sana: Optional[Union[str, date, datetime]] = None,
) -> Tuple[datetime, datetime]:
    """
    Berilgan sana oralig'i (start_sana 00:00 UZ dan end_sana 24:00 UZ gacha) uchun
    UTC naive datetime chegaralarini qaytaradi.
    """
    if start_sana is None:
        start_utc, _ = uz_day_bounds_utc(None)
    else:
        start_utc, _ = uz_day_bounds_utc(start_sana)

    if end_sana is None:
        _, end_utc = uz_day_bounds_utc(start_sana if start_sana else None)
    else:
        _, end_utc = uz_day_bounds_utc(end_sana)

    return start_utc, end_utc


def format_uz(dt: Optional[datetime], fmt: str = "%d.%m.%Y %H:%M") -> str:
    """Datetime ni UZ vaqtiga o'girib matn formatida qaytarish"""
    if dt is None:
        return "—"
    dt_uz = to_uz(dt)
    return dt_uz.strftime(fmt)
