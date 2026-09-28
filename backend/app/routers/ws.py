"""
WebSocket router — Real-time ulanish va kanallar
"""
import json
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db, async_session_factory
from app.core.security import decode_token
from app.models.user import User
from app.websockets.manager import manager

router = APIRouter(prefix="/ws", tags=["⚡ WebSocket"])


async def authenticate_ws_token(token: str) -> Optional[User]:
    """Token orqali foydalanuvchini aniqlash"""
    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        if not user_id:
            return None

        async with async_session_factory() as session:
            result = await session.execute(select(User).where(User.id == int(user_id)))
            user = result.scalar_one_or_none()
            if user and user.is_active:
                return user
    except Exception:
        return None
    return None


@router.websocket("/{restaurant_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    restaurant_id: int,
    token: Optional[str] = Query(None),
    table_id: Optional[int] = Query(None),
):
    """
    Real-time WebSocket ulanish nuqtasi:
    - Xodimlar (Ofitsiant, Oshpaz, Admin): ?token=<JWT_TOKEN>
    - Mijozlar (Stoldagi QR orqali): ?table_id=<TABLE_ID>
    """
    user: Optional[User] = None
    role = "guest"
    user_id = None
    username = None

    if token:
        user = await authenticate_ws_token(token)
        if user:
            role = user.role.value if hasattr(user.role, "value") else str(user.role)
            user_id = user.id
            username = user.username

    # Ulanishni qabul qilish
    await manager.connect(
        websocket=websocket,
        restaurant_id=restaurant_id,
        user_id=user_id,
        role=role,
        table_id=table_id,
        username=username,
    )

    try:
        while True:
            # Mijozdan xabar kutish (keepalive ping/pong yoki buyruqlar)
            message_text = await websocket.receive_text()
            try:
                data = json.loads(message_text)
                msg_type = data.get("type", "message")

                if msg_type == "ping":
                    await manager.send_personal_message(
                        {
                            "type": "pong",
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        },
                        websocket,
                    )
                elif msg_type == "status_check":
                    online_info = manager.get_online_counts(restaurant_id)
                    await manager.send_personal_message(
                        {
                            "type": "online_stats",
                            "stats": online_info,
                        },
                        websocket,
                    )
            except json.JSONDecodeError:
                if message_text == "ping":
                    await websocket.send_text("pong")
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except Exception:
        await manager.disconnect(websocket)


@router.get("/online/{restaurant_id}", summary="Onlayn xodimlar soni")
async def get_online_staff(restaurant_id: int):
    """Restorandagi joriy onlayn ulanishlar sonini qaytaradi"""
    stats = manager.get_online_counts(restaurant_id)
    return {"restaurant_id": restaurant_id, "online": stats}
