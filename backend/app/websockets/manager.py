"""
WebSocket Connection Manager — Real-time xabarlar va bildirishnomalar boshqaruvi
"""
import asyncio
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

    def get_online_counts(self, restaurant_id: int) -> Dict[str, int]:
        """Onlayn foydalanuvchilar statistikasini olish"""
        counts = {"total": 0, "waiter": 0, "chef": 0, "admin": 0, "guest": 0}
        connections = self._restaurant_connections.get(restaurant_id, set())
        for ws in connections:
            meta = self._connection_meta.get(ws, {})
            role = meta.get("role", "guest")
            counts["total"] += 1
            if role in counts:
                counts[role] += 1
        return counts


# Global singleton nusxa
manager = ConnectionManager()
