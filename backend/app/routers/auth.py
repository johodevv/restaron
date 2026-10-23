"""
Auth API — Login, token olish
"""
from datetime import timedelta
import asyncio
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from fastapi.security import HTTPAuthorizationCredentials
from app.core.database import get_db
from app.core.rate_limit import RateLimiter, get_client_ip
from app.core.security import (
    verify_password, get_password_hash, create_access_token, get_current_user, security
)
from app.core.config import settings
from app.models.user import User, UserRole
from app.schemas.user import LoginRequest, TokenResponse, UserResponse

router = APIRouter(prefix="/auth", tags=["🔐 Auth"])


async def login_rate_limit_key(request: Request) -> str:
    ip = get_client_ip(request)
    try:
        body = await request.json()
        username = (body.get("username") or "").strip().lower() if isinstance(body, dict) else ""
    except Exception:
        username = ""
    return f"login:{ip}:{username}"


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login qilish",
    dependencies=[
        Depends(
            RateLimiter(
                times=10,
                seconds=60,
                key_func=login_rate_limit_key,
                detail="Kirish urinishlari me'yoridan oshdi. Xavfsizlik yuzasidan 1 daqiqa kuting.",
            )
        )
    ],
)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Username va parol bilan login (brute-force himoyasi bilan)"""
    username_clean = payload.username.strip().lower()
    result = await db.execute(
        select(User).where(func.lower(User.username) == username_clean)
    )
    user = result.scalar_one_or_none()

    if not user or not await asyncio.to_thread(verify_password, payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Username yoki parol noto'g'ri",
        )

    user_id, verified_hash = user.id, user.hashed_password
    await db.rollback()
    user = await db.scalar(select(User).where(User.id == user_id))
    if user is None or user.hashed_password != verified_hash:
        raise HTTPException(401, 'Akkaunt o‘zgargan. Qaytadan kiring.')

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akkaunt faol emas. Admin bilan bog'laning.",
        )

    role_val = user.role.value if hasattr(user.role, "value") else str(user.role)
    if role_val in ("waiter", "chef", "cashier") and not getattr(user, "is_approved", False):
        try:
            from app.websockets.manager import manager
            await manager.broadcast_to_roles(
                user.restaurant_id or 1,
                ["admin", "developer"],
                {
                    "type": "staff_login_request",
                    "user_id": user.id,
                    "username": user.username,
                    "full_name": user.full_name,
                    "role": role_val,
                },
            )
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Kirish so'rovi Adminga yuborildi! Admin tasdiqlashini kuting...",
        )

    access_token = create_access_token(
        data={"sub": str(user.id), "role": role_val, 'auth_version': user.tokens_valid_after or 0},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    return TokenResponse(
        access_token=access_token,
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse, summary="Joriy foydalanuvchi")
async def get_me(current_user: User = Depends(get_current_user)):
    """Hozirgi kirgan foydalanuvchi ma'lumoti"""
    return UserResponse.model_validate(current_user)


@router.post("/logout", summary="Tizimdan chiqish va tokenni bekor qilish (Token Blacklist)")
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Foydalanuvchi tokenni qora ro'yxatga kiritib tizimdan chiqadi"""
    token = credentials.credentials
    from app.core.security import revoke_token
    revoke_token(token)
    from app.core.security import decode_token
    from app.models.token_revocation import TokenRevocation
    from jose import jwt
    from app.core.config import settings
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    if payload.get('jti') and await db.get(TokenRevocation, payload['jti']) is None:
        db.add(TokenRevocation(jti=payload['jti'], expires_at=float(payload.get('exp') or 0)))

    from app.core.audit import log_audit_event
    await log_audit_event(
        db=db,
        restaurant_id=current_user.restaurant_id or 1,
        action="user_logout",
        user=current_user,
        entity_type="user",
        entity_id=current_user.id,
    )
    return {"success": True, "message": "Muvaffaqiyatli chiqildi, sessiya bekor qilindi"}

