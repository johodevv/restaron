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

    # Admin yoki Developer yaratgan xodim darhol tasdiqlangan (is_approved=True) bo'ladi
    is_appr = True

    new_user = User(
        username=payload.username,
        full_name=payload.full_name,
        phone=payload.phone,
        hashed_password=get_password_hash(payload.password),
        role=payload.role,
        is_approved=is_appr,
        restaurant_id=restaurant_id,
    )
    db.add(new_user)
    await db.flush()
    await db.commit()
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

    # O'z profilini adashib nofaol qilib qo'yishdan himoya
    if current_user.id == user.id and update_data.get("is_active") is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O'z profilingizni nofaol holatga o'tkaza olmaysiz! Bu tizimga kira olmay qolishingizga sabab bo'ladi.",
        )

    for field, value in update_data.items():
        setattr(user, field, value)

    # Agar foydalanuvchi faolsizlantirilsa yoki paroli o'zgarsa, uning barcha tokenlarini bekor qilish
    from app.core.security import revoke_user_tokens
    if update_data.get("is_active") is False or "password" in update_data:
        revoke_user_tokens(user.id)

    await db.flush()
    await db.commit()
    await db.refresh(user)

    from app.core.audit import log_audit_event
    await log_audit_event(
        db=db,
        restaurant_id=user.restaurant_id or 1,
        action="user_updated",
        user=current_user,
        entity_type="user",
        entity_id=user.id,
        details={"updated_fields": list(update_data.keys()), "target_username": user.username},
    )

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

    # O'chirilayotgan xodimning barcha sessiyalarini darhol bekor qilish
    from app.core.security import revoke_user_tokens
    revoke_user_tokens(user.id)

    from app.core.audit import log_audit_event
    await log_audit_event(
        db=db,
        restaurant_id=user.restaurant_id or 1,
        action="user_deleted",
        user=current_user,
        entity_type="user",
        entity_id=user.id,
        details={"deleted_username": user.username},
    )

    await db.delete(user)


@router.patch("/{user_id}/approve", response_model=UserResponse, summary="Xodimni tasdiqlash yoki rad etish")
async def approve_user(
    user_id: int,
    is_approved: bool = True,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "developer")),
):
    """Admin yoki Developer yangi ro'yxatdan o'tgan xodim akkauntini tasdiqlaydi yoki rad etadi"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")

    user.is_approved = is_approved
    if not is_approved:
        from app.core.security import revoke_user_tokens
        revoke_user_tokens(user.id)

    await db.flush()
    await db.commit()
    await db.refresh(user)

    from app.core.audit import log_audit_event
    await log_audit_event(
        db=db,
        restaurant_id=user.restaurant_id or 1,
        action="user_approval_changed",
        user=current_user,
        entity_type="user",
        details={"is_approved": is_approved, "target_username": user.username},
    )

    from app.websockets.manager import manager
    await manager.broadcast_to_restaurant(
        user.restaurant_id or 1,
        {
            "type": "staff_approval_status",
            "user_id": user.id,
            "username": user.username,
            "is_approved": is_approved,
        }
    )

    return UserResponse.model_validate(user)
