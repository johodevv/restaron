"""
Foydalanuvchilar API — Admin tomonidan boshqarish
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional

from app.core.database import get_db
from app.core.security import get_password_hash, require_role, get_current_user
from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserUpdate, UserResponse

router = APIRouter(prefix="/users", tags=["👤 Foydalanuvchilar"])


@router.post(
    "/",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Yangi xodim yaratish",
)
async def create_user(
    payload: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "developer")),
):
    """Admin yangi ofitsiant yoki oshpaz yaratadi"""
    # Username mavjudligini tekshirish
    result = await db.execute(select(User).where(User.username == payload.username))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bu username allaqachon mavjud",
        )

    # Admin faqat o'z restoraniga xodim qo'sha oladi
    restaurant_id = payload.restaurant_id
    if current_user.role == UserRole.ADMIN:
        restaurant_id = current_user.restaurant_id

    new_user = User(
        username=payload.username,
        full_name=payload.full_name,
        phone=payload.phone,
        hashed_password=get_password_hash(payload.password),
        role=payload.role,
        restaurant_id=restaurant_id,
    )
    db.add(new_user)
    await db.flush()
    await db.refresh(new_user)
    return UserResponse.model_validate(new_user)


@router.get("/", response_model=List[UserResponse], summary="Xodimlar ro'yxati")
async def list_users(
    role: Optional[UserRole] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "developer")),
):
    """Barcha xodimlar ro'yxati (admin faqat o'z restoranini ko'radi)"""
    query = select(User)

    if current_user.role == UserRole.ADMIN:
        query = query.where(User.restaurant_id == current_user.restaurant_id)

    if role:
        query = query.where(User.role == role)

    result = await db.execute(query.order_by(User.created_at.desc()))
    users = result.scalars().all()
    return [UserResponse.model_validate(u) for u in users]


@router.get("/{user_id}", response_model=UserResponse, summary="Xodim ma'lumoti")
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "developer")),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")
    return UserResponse.model_validate(user)


@router.patch("/{user_id}", response_model=UserResponse, summary="Xodimni yangilash")
async def update_user(
    user_id: int,
    payload: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "developer")),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)

    await db.flush()
    await db.refresh(user)
    return UserResponse.model_validate(user)


@router.delete("/{user_id}", status_code=204, summary="Xodimni o'chirish")
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "developer")),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")
    await db.delete(user)
