"""
WebSocket Connection Manager — Real-time xabarlar va bildirishnomalar boshqaruvi
"""
import asyncio
import time
from datetime import datetime, timezone
from typing import Dict, Set, Optional, List, Any
from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        # restaurant_id -> Set[WebSocket]
        self._restaurant_connections: Dict[int, Set[WebSocket]] = {}
        # websocket -> metadata dict
        self._connection_meta: Dict[WebSocket, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._running = False

    def update_heartbeat(self, websocket: WebSocket):
        """Mijozdan faollik (ping/pong) kelganda oxirgi ko'ringan vaqtni yangilash"""
        if websocket in self._connection_meta:
            self._connection_meta[websocket]["last_seen"] = time.time()

    async def connect(
        self,
        websocket: WebSocket,
        restaurant_id: int,
        user_id: Optional[int] = None,
        role: Optional[str] = None,
        table_id: Optional[int] = None,
        username: Optional[str] = None,
    ):
        """Yangi ulanishni qabul qilish va saqlash"""
        await websocket.accept()

        async with self._lock:
            if restaurant_id not in self._restaurant_connections:
                self._restaurant_connections[restaurant_id] = set()
            self._restaurant_connections[restaurant_id].add(websocket)

            self._connection_meta[websocket] = {
                "restaurant_id": restaurant_id,
                "user_id": user_id,
                "role": role.lower() if role else "guest",
                "table_id": table_id,
                "username": username,
                "connected_at": datetime.now(timezone.utc).isoformat(),
                "last_seen": time.time(),
            }

        # Welcome xabari yuborish
        await self.send_personal_message(
            {
                "type": "connection_established",
                "status": "connected",
                "restaurant_id": restaurant_id,
                "role": role or "guest",
                "user_id": user_id,
                "table_id": table_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            websocket,
        )

    async def disconnect(self, websocket: WebSocket):
        """Ulanish uzilganda tozalash"""
        async with self._lock:
            meta = self._connection_meta.pop(websocket, None)
            if meta:
                restaurant_id = meta.get("restaurant_id")
                if restaurant_id and restaurant_id in self._restaurant_connections:
                    self._restaurant_connections[restaurant_id].discard(websocket)
                    if not self._restaurant_connections[restaurant_id]:
                        del self._restaurant_connections[restaurant_id]

    async def send_personal_message(self, message: dict, websocket: WebSocket) -> bool:
        """Bitta mijozga xabar yuborish"""
        try:
            await websocket.send_json(message)
            return True
        except Exception:
            await self.disconnect(websocket)
            return False

    async def send_to_user(self, restaurant_id: int, user_id: int, message: dict):
        """Muayyan foydalanuvchiga (ofitsiant, oshpaz, admin) yuborish"""
        target_sockets: List[WebSocket] = []
        async with self._lock:
            connections = list(self._restaurant_connections.get(restaurant_id, set()))
            for ws in connections:
                meta = self._connection_meta.get(ws, {})
                if meta.get("user_id") == user_id:
                    target_sockets.append(ws)

        for ws in target_sockets:
            await self.send_personal_message(message, ws)

    async def broadcast_to_role(self, restaurant_id: int, role: str, message: dict):
        """Muayyan roldagi barcha foydalanuvchilarga yuborish (waiter, chef, admin)"""
        role_lower = role.lower()
        target_sockets: List[WebSocket] = []
        async with self._lock:
            connections = list(self._restaurant_connections.get(restaurant_id, set()))
            for ws in connections:
                meta = self._connection_meta.get(ws, {})
                # Admin har doim barcha bildirishnomalarni ko'ra oladi
                if meta.get("role") == role_lower or meta.get("role") in ["admin", "developer"]:
                    target_sockets.append(ws)

        for ws in target_sockets:
            await self.send_personal_message(message, ws)

    async def broadcast_to_roles(self, restaurant_id: int, roles: List[str], message: dict):
        """Bir nechta rollarga yuborish"""
        roles_set = {r.lower() for r in roles} | {"admin", "developer"}
        target_sockets: List[WebSocket] = []
        async with self._lock:
            connections = list(self._restaurant_connections.get(restaurant_id, set()))
            for ws in connections:
                meta = self._connection_meta.get(ws, {})
                if meta.get("role") in roles_set:
                    target_sockets.append(ws)

        for ws in target_sockets:
            await self.send_personal_message(message, ws)

    async def broadcast_to_table(self, restaurant_id: int, table_id: int, message: dict):
        """Stolda o'tirgan mijoz(lar)ga yuborish"""
        target_sockets: List[WebSocket] = []
        async with self._lock:
            connections = list(self._restaurant_connections.get(restaurant_id, set()))
            for ws in connections:
                meta = self._connection_meta.get(ws, {})
                if meta.get("table_id") == table_id:
                    target_sockets.append(ws)

        for ws in target_sockets:
            await self.send_personal_message(message, ws)

    async def broadcast_to_restaurant(self, restaurant_id: int, message: dict):
        """Restorandagi hamma ulanganlarga tarqatish"""
        async with self._lock:
            target_sockets = list(self._restaurant_connections.get(restaurant_id, set()))

        for ws in target_sockets:
            await self.send_personal_message(message, ws)

    def start_heartbeat(self, interval_seconds: int = 25, timeout_seconds: int = 60):
        """Orqa fonda WebSocket ping/heartbeat tekshiruvini boshlash"""
        if self._running and self._heartbeat_task and not self._heartbeat_task.done():
            return
        self._running = True
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop(interval_seconds, timeout_seconds))

    async def _heartbeat_loop(self, interval_seconds: int, timeout_seconds: int):
        while self._running:
            try:
                await asyncio.sleep(interval_seconds)
                now = time.time()

                # 1. Timeout bo'lgan (javob bermagan) o'lik ulanishlarni tozalash
                stale_sockets: List[WebSocket] = []
                async with self._lock:
                    for ws, meta in list(self._connection_meta.items()):
                        last_seen = meta.get("last_seen", now)
                        if now - last_seen > timeout_seconds:
                            stale_sockets.append(ws)

                for ws in stale_sockets:
                    try:
                        await ws.close(code=1000)
                    except Exception:
                        pass
                    await self.disconnect(ws)

                # 2. Barcha faol ulanishlarga ping yuborish
                all_sockets: List[WebSocket] = []
                async with self._lock:
                    all_sockets = list(self._connection_meta.keys())

                for ws in all_sockets:
                    try:
                        await ws.send_json({
                            "type": "ping",
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        })
                    except Exception:
                        await self.disconnect(ws)

            except asyncio.CancelledError:
                break
            except Exception:
                await asyncio.sleep(5)

    async def stop_heartbeat(self):
        """Heartbeat siklini xavfsiz to'xtatish"""
        self._running = False
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
            self._heartbeat_task = None


# Global singleton nusxa
manager = ConnectionManager()
