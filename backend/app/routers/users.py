import time
import logging
"""
Foydalanuvchilar API — Admin va Developer tomonidan boshqarish
VAZIFA 10A: foydalanuvchilar boshqaruvi va xavfsizlik cheklovlari
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional

from app.core.database import get_db
from app.core.security import get_password_hash, require_role, get_current_user, revoke_user_tokens
from app.core.audit import log_audit_event
from app.core.transactions import lock_rows
from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserUpdate, UserResponse, UserPasswordReset

router = APIRouter(prefix="/users", tags=["👤 Foydalanuvchilar"])


async def notify_session_revoked(user):
    # Delivery is best-effort after commit. HTTP and WS auth also check persisted state.
    from app.websockets.manager import manager
    try:
        await manager.send_to_user(user.restaurant_id or 1, user.id, {"type":"session_revoked", "user_id":user.id})
    except Exception:
        logging.getLogger(__name__).warning("Staff session notification could not be delivered", exc_info=True)


def check_user_access(current_user: User, target_user: User) -> None:
    """
    Ruxsatlarni tekshirish:
    - Developer barcha foydalanuvchilarni ko'radi va boshqaradi.
    - Admin developer rolli foydalanuvchiga tegolmaydi (403).
    - Admin faqat o'z restoranidagi foydalanuvchilarni ko'radi va boshqaradi (403).
    """
    current_role = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)
    target_role = target_user.role.value if hasattr(target_user.role, "value") else str(target_user.role)

    if current_role == "developer":
        return

    # Admin developer rolli foydalanuvchiga tegolmasin
    if target_role == "developer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin developer rolli foydalanuvchini ko'rish yoki boshqarish huquqiga ega emas",
        )

    # Admin faqat o'z restoranidagi foydalanuvchilarni boshqara oladi
    if target_user.restaurant_id != current_user.restaurant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Siz faqat o'z restoraningizdagi foydalanuvchilarni boshqara olasiz",
        )


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
    """
    Yangi xodim yaratish:
    - Admin faqat waiter, chef, cashier yarata oladi.
    - 'admin' va 'developer' rollarini faqat developer yarata oladi (aks holda 403).
    """
    current_role = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)
    target_role = payload.role.value if hasattr(payload.role, "value") else str(payload.role)

    if current_role != "developer":
        if target_role in ("admin", "developer") or target_role not in ("waiter", "chef", "cashier"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin faqat waiter, chef yoki cashier yarata oladi. Admin va developer rollarini faqat developer yarata oladi.",
            )

    # Username mavjudligini tekshirish
    result = await db.execute(select(User).where(User.username == payload.username))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bu username allaqachon mavjud",
        )

    # Admin faqat o'z restoraniga xodim qo'sha oladi
    restaurant_id = payload.restaurant_id
    if current_role == "admin":
        restaurant_id = current_user.restaurant_id

    new_user = User(
        username=payload.username,
        full_name=payload.full_name,
        phone=payload.phone,
        hashed_password=get_password_hash(payload.password),
        role=payload.role,
        is_approved=True,
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
    """Barcha xodimlar ro'yxati (admin faqat o'z restorani va no-developerlarni ko'radi)"""
    current_role = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)
    query = select(User)

    if current_role == "admin":
        query = query.where(
            User.restaurant_id == current_user.restaurant_id,
            User.role != UserRole.DEVELOPER,
        )

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
    """Xodim ma'lumotlarini olish (admin faqat o'z restorani, developer emas)"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")

    check_user_access(current_user, user)
    return UserResponse.model_validate(user)


@router.patch("/{user_id}", response_model=UserResponse, summary="Xodimni yangilash")
async def update_user(
    user_id: int,
    payload: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "developer")),
):
    """Xodim ma'lumotlarini yangilash"""
    await lock_rows(db, User, [user_id])
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")

    check_user_access(current_user, user)

    update_data = payload.model_dump(exclude_unset=True)

    # O'z profilini adashib nofaol qilib qo'yishdan himoya
    if current_user.id == user.id and update_data.get("is_active") is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O'z profilingizni nofaol holatga o'tkaza olmaysiz! Bu tizimga kira olmay qolishingizga sabab bo'ladi.",
        )

    # Restoranning oxirgi faol admin'ini nofaol qilishga yo'l qo'yma (400)
    target_role = user.role.value if hasattr(user.role, "value") else str(user.role)
    if update_data.get("is_active") is False and target_role == "admin" and user.is_active:
        res = await db.execute(
            select(func.count(User.id)).where(
                User.restaurant_id == user.restaurant_id,
                User.role == UserRole.ADMIN,
                User.is_active == True,
                User.id != user.id,
            )
        )
        remaining_admins = res.scalar() or 0
        if remaining_admins == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Restoranning oxirgi faol adminini nofaol qilib bo'lmaydi",
            )

    for field, value in update_data.items():
        setattr(user, field, value)

    # Agar foydalanuvchi faolsizlantirilsa, uning barcha tokenlarini bekor qilish
    if update_data.get("is_active") is False:
        user.tokens_valid_after = time.time()

    await db.flush()
    audit = await log_audit_event(
        db=db,
        restaurant_id=user.restaurant_id or 1,
        action="user_updated",
        user=current_user,
        entity_type="user",
        entity_id=user.id,
        details={"updated_fields": list(update_data.keys()), "target_username": user.username},
    )
    if audit is None:
        raise HTTPException(503, "Xodim o‘zgarishini tarixga saqlab bo‘lmadi. O‘zgarish bekor qilindi; qayta urinib ko‘ring.")
    await db.commit()
    await db.refresh(user)
    if update_data.get("is_active") is False:
        revoke_user_tokens(user.id)
        await notify_session_revoked(user)

    return UserResponse.model_validate(user)


@router.patch("/{user_id}/password", summary="Foydalanuvchi parolini yangilash (Admin / Developer)")
async def reset_user_password(
    user_id: int,
    payload: UserPasswordReset,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "developer")),
):
    """
    Foydalanuvchi parolini o'zgartirish:
    - Admin (o'z restorani) yoki Developer;
    - Parol xeshlansin;
    - Foydalanuvchi tokenlari bekor qilinsin (revoke_user_tokens);
    - Audit: 'user_password_reset' (parol log qilinmaydi).
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")

    check_user_access(current_user, user)

    # Parolni xeshlash
    user.hashed_password = get_password_hash(payload.new_password)

    # Tokenlarni bekor qilish
    revoke_user_tokens(user.id)
    user.tokens_valid_after = time.time()

    await db.flush()
    await db.commit()

    # Audit log (parol hech qayerda log qilinmasin!)
    await log_audit_event(
        db=db,
        restaurant_id=user.restaurant_id or 1,
        action="user_password_reset",
        user=current_user,
        entity_type="user",
        entity_id=user.id,
        details={"target_username": user.username},
    )
    await db.commit()

    return {"message": "Parol muvaffaqiyatli yangilandi"}


@router.delete("/{user_id}", summary="Xodimni nofaol qilish")
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "developer")),
):
    """
    Xodimni o'chirish:
    - Qattiq o'chirish o'rniga is_active=False va tokenlarni bekor qilish;
    - O'zini o'zi nofaol qila olmasin (400);
    - Restoranning oxirgi faol admin'ini nofaol qilishga yo'l qo'yilmaydi (400);
    - Javob: Foydalanuvchi nofaol qilindi.
    """
    await lock_rows(db, User, [user_id])
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")

    check_user_access(current_user, user)

    # O'zini o'zi nofaol qila olmasin
    if current_user.id == user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O'zingizni nofaol qila olmaysiz",
        )

    # Restoranning oxirgi faol admin'ini nofaol qilishga yo'l qo'yma (400)
    target_role = user.role.value if hasattr(user.role, "value") else str(user.role)
    if target_role == "admin" and user.is_active:
        res = await db.execute(
            select(func.count(User.id)).where(
                User.restaurant_id == user.restaurant_id,
                User.role == UserRole.ADMIN,
                User.is_active == True,
                User.id != user.id,
            )
        )
        remaining_admins = res.scalar() or 0
        if remaining_admins == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Restoranning oxirgi faol adminini nofaol qilib bo'lmaydi",
            )

    if not user.is_active:
        return {"message":"Foydalanuvchi nofaol qilindi", "detail":"Foydalanuvchi nofaol qilindi", "user_id":user.id, "is_active":False, "already_inactive":True}

    # Save deactivation and its audit together; preserve historical foreign keys.
    user.is_active = False
    user.tokens_valid_after = time.time()

    await db.flush()
    audit = await log_audit_event(
        db=db,
        restaurant_id=user.restaurant_id or 1,
        action="user_deactivated",
        user=current_user,
        entity_type="user",
        entity_id=user.id,
        details={"deactivated_username": user.username},
    )
    if audit is None:
        raise HTTPException(503, "Bo‘shatishni tarixga saqlab bo‘lmadi. Xodim bo‘shatilmadi; qayta urinib ko‘ring.")
    await db.commit()
    revoke_user_tokens(user.id)
    await notify_session_revoked(user)

    return {"message": "Foydalanuvchi nofaol qilindi", "detail": "Foydalanuvchi nofaol qilindi", "user_id":user.id, "is_active":False}


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

    check_user_access(current_user, user)

    user.is_approved = is_approved
    if not is_approved:
        revoke_user_tokens(user.id)
        user.tokens_valid_after = time.time()

    await db.flush()
    await db.commit()
    await db.refresh(user)

    await log_audit_event(
        db=db,
        restaurant_id=user.restaurant_id or 1,
        action="user_approval_changed",
        user=current_user,
        entity_type="user",
        details={"is_approved": is_approved, "target_username": user.username},
    )
    await db.commit()

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
