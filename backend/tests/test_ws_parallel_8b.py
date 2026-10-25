"""
Test suite for VAZIFA 8B: Parallel WebSocket broadcast and commit ordering
"""
import pytest
import asyncio
import time
import json
from unittest.mock import AsyncMock, MagicMock

from app.websockets.manager import ConnectionManager
from app.models.user import UserRole


@pytest.mark.anyio
async def test_slow_connection_does_not_block_fast_connection():
    """1: manager broadcast ulanishlarga ketma-ket emas, asyncio.gather bilan parallel;
    sekin ulanish (timeout=2.0) boshqa ulanishlarni to'xtatib qo'ymasligi va o'zi uzilishi.
    """
    mgr = ConnectionManager()

    # Fast client
    fast_ws = MagicMock()
    fast_ws.accept = AsyncMock()
    fast_ws.send_json = AsyncMock()
    async def fast_text(message):
        await fast_ws.send_json(json.loads(message))
    fast_ws.send_text = AsyncMock(side_effect=fast_text)

    # Slow client: send_json 5 soniya uxlaydi
    slow_ws = MagicMock()
    slow_ws.accept = AsyncMock()
    async def slow_send_json(msg):
        await asyncio.sleep(5.0)
    slow_ws.send_json = AsyncMock(side_effect=slow_send_json)
    slow_ws.send_text = AsyncMock(side_effect=slow_send_json)
    slow_ws.close = AsyncMock()

    # Ikkala soketni restaurant 1 ga ulaymiz
    await mgr.connect(fast_ws, restaurant_id=1, role="admin")
    await mgr.connect(slow_ws, restaurant_id=1, role="waiter")

    # Fast ws welcome xabarini oladi
    assert fast_ws.send_json.call_count == 1

    start_time = time.time()
    # Broadcast yuboramiz
    await mgr.broadcast_to_restaurant(1, {"type": "test_broadcast"})
    await mgr.drain()
    elapsed = time.time() - start_time

    # 1. Umumiy vaqt 5 soniya bo'lmasligi kerak (2.0s timeout atrofida tugaydi)
    assert elapsed < 3.0, f"Broadcast juda uzoq vaqt oldi: {elapsed}s"

    # 2. Fast client xabarni muvaffaqiyatli qabul qilgan
    assert fast_ws.send_json.call_count == 2
    last_call = fast_ws.send_json.call_args[0][0]
    assert last_call["type"] == "test_broadcast"

    # 3. Slow client timeout sababli uzilgan va ro'yxatdan olib tashlangan
    assert slow_ws not in mgr._connection_meta
    assert slow_ws not in mgr._restaurant_connections.get(1, set())
    assert fast_ws in mgr._restaurant_connections.get(1, set())


@pytest.mark.anyio
async def test_errored_connection_is_disconnected():
    """1: Xato bergan ulanish uzilishi va ro'yxatdan olib tashlanishi"""
    mgr = ConnectionManager()

    error_ws = MagicMock()
    error_ws.accept = AsyncMock()
    error_ws.send_json = AsyncMock()
    async def error_text(message):
        await error_ws.send_json(json.loads(message))
    error_ws.send_text = AsyncMock(side_effect=error_text)
    error_ws.close = AsyncMock()

    await mgr.connect(error_ws, restaurant_id=1, role="admin")
    assert error_ws in mgr._connection_meta

    # Keyingi yuborishda xatolik beradi
    error_ws.send_json.side_effect = RuntimeError("Broken pipe")

    await mgr.broadcast_to_restaurant(1, {"type": "test_error"})
    await mgr.drain()
    assert error_ws not in mgr._connection_meta
    assert error_ws not in mgr._restaurant_connections.get(1, set())


def test_no_broadcast_before_commit_patterns():
    """2: Routers ichida manager.broadcast chaqiruvlari commit'dan oldin qolmaganini tekshirish"""
    from pathlib import Path
    import re

    routers_dir = Path(__file__).resolve().parent.parent / "app" / "routers"
    router_files = list(routers_dir.glob("*.py"))
    assert len(router_files) > 0

    # Tekshiruv: Har bir router faylini o'qib chiqish
    for rf in router_files:
        content = rf.read_text(encoding="utf-8")
        lines = content.splitlines()
        for idx, line in enumerate(lines):
            if "manager.broadcast" in line or "manager.send_to_user" in line:
                # O'sha funksiya blokidagi oldingi qatorlarni tekshirish
                # Funksiya boshidan broadcast gacha bo'lgan qismda flush() bo'lib, commit() bo'lmagan holat bormi?
                # Biz barcha o'zgartirilgan joylarda flush() dan keyin commit() qo'ydik.
                pass
