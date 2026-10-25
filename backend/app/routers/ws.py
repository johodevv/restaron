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
from app.core.security import decode_token, session_is_valid
from app.models.user import User
from app.models.table import Table
from app.websockets.manager import manager

router = APIRouter(prefix="/ws", tags=["⚡ WebSocket"])


async def authenticate_ws_token(token: str) -> Optional[User]:
    """Token orqali foydalanuvchini aniqlash va rol mosligini tekshirish"""
    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        token_role = payload.get("role")
        if not user_id:
            return None

        async with async_session_factory() as session:
            result = await session.execute(select(User).where(User.id == int(user_id)))
            user = result.scalar_one_or_none()
            if user and user.is_active:
                if not await session_is_valid(session, payload, user):
                    return None
                user_role_str = user.role.value if hasattr(user.role, "value") else str(user.role)
                if token_role and token_role != user_role_str:
                    return None
                if user_role_str in ('waiter', 'chef', 'cashier') and not user.is_approved:
                    return None
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

    has_token = token is not None and token.strip() != ""

    # A close before accept becomes an opaque HTTP 403/1006 in a browser.
    # Accept rejected handshakes only to send a close code; never register them.
    if has_token:
        user = await authenticate_ws_token(token)
        # 1. Token berilgan, lekin yaroqsiz yoki muddati o'tgan bo'lsa guest sifatida ulama — 4401 kodi bilan yop.
        if not user:
            await websocket.accept()
            await websocket.close(code=4401)
            return

        user_role_str = user.role.value if hasattr(user.role, "value") else str(user.role)
        is_dev = user_role_str == "developer"

        # 2. Xodim tokeni uchun user.restaurant_id yo'ldagi restaurant_id ga teng bo'lishi shart (developer istisno); bo'lmasa 4403 bilan yop.
        if not is_dev and user.restaurant_id != restaurant_id:
            await websocket.accept()
            await websocket.close(code=4403)
            return

        role = user_role_str
        user_id = user.id
        username = user.username
    else:
        # Token umuman yo'q bo'lsa faqat guest (mijoz) rejimi.
        # 3. Guest uchun table_id majburiy va shu restoranga tegishli stol bo'lishi kerak (bazada tekshir); aks holda 4403.
        if not table_id:
            await websocket.accept()
            await websocket.close(code=4403)
            return

        async with async_session_factory() as session:
            result = await session.execute(
                select(Table.id).where(
                    Table.id == table_id,
                    Table.restaurant_id == restaurant_id,
                )
            )
            table_row = result.scalar_one_or_none()
            if not table_row:
                await websocket.accept()
                await websocket.close(code=4403)
                return

        role = "guest"
        user_id = None
        username = None

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
            if has_token and not await authenticate_ws_token(token):
                await websocket.close(code=4401)
                raise WebSocketDisconnect(4401)
            manager.update_heartbeat(websocket)
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
                elif msg_type == "pong":
                    manager.update_heartbeat(websocket)
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
                elif message_text == "pong":
                    manager.update_heartbeat(websocket)
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except Exception:
        await manager.disconnect(websocket)


@router.get("/online/{restaurant_id}", summary="Onlayn xodimlar soni")
async def get_online_staff(restaurant_id: int):
    """Restorandagi joriy onlayn ulanishlar sonini qaytaradi"""
    stats = manager.get_online_counts(restaurant_id)
    return {"restaurant_id": restaurant_id, "online": stats}
