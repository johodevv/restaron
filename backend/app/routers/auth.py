"""
Auth API — Login, token olish
"""
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import (
    verify_password, create_access_token, get_current_user
)
from app.core.config import settings
from app.models.user import User
from app.schemas.user import LoginRequest, TokenResponse, UserResponse

router = APIRouter(prefix="/auth", tags=["🔐 Auth"])


@router.post("/login", response_model=TokenResponse, summary="Login qilish")
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Username va parol bilan login"""
    result = await db.execute(
        select(User).where(User.username == payload.username)
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

    access_token = create_access_token(
        data={"sub": str(user.id), "role": user.role},
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
