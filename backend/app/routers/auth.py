"""
Auth API — Login, token olish
"""
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from fastapi.security import HTTPAuthorizationCredentials
from app.core.database import get_db
from app.core.rate_limit import RateLimiter
from app.core.security import (
    verify_password, get_password_hash, create_access_token, get_current_user, security
)
from app.core.config import settings
from app.models.user import User, UserRole
from app.schemas.user import LoginRequest, TokenResponse, UserResponse

router = APIRouter(prefix="/auth", tags=["🔐 Auth"])


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login qilish",
    dependencies=[
        Depends(
            RateLimiter(
                times=60,
                seconds=60,
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

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Username yoki parol noto'g'ri",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akkaunt faol emas. Admin bilan bog'laning.",
        )

    role_val = user.role.value if hasattr(user.role, "value") else str(user.role)
    access_token = create_access_token(
        data={"sub": str(user.id), "role": role_val},
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

