import uuid
import time
import bcrypt
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.database import get_db

security = HTTPBearer()
security_optional = HTTPBearer(auto_error=False)

# Server har safar o'chib yonganda barcha ofitsiant/xodimlarni qayta login qildirish va tasdiq so'rash uchun
SERVER_BOOT_NONCE = str(uuid.uuid4())

# Qora ro'yxat (Blacklist): jti -> expires_at_timestamp
_blacklisted_jtis: Dict[str, float] = {}
# Foydalanuvchi bo'yicha bekor qilish vaqti: user_id -> revoked_after_timestamp
_user_revocation_timestamps: Dict[int, float] = {}


def revoke_token(token_or_jti: str) -> bool:
    """Bitta tokenni yoki JTI ni yaroqsiz qilish (logout yoki xavfsizlik uchun)"""
    if not token_or_jti:
        return False
    if "." in token_or_jti:
        try:
            payload = jwt.decode(token_or_jti, settings.SECRET_KEY, algorithms=[settings.ALGORITHM], options={"verify_exp": False})
            jti = payload.get("jti")
            exp = payload.get("exp")
            if jti:
                _blacklisted_jtis[jti] = float(exp) if exp else time.time() + 86400
                return True
        except Exception:
            pass
    else:
        _blacklisted_jtis[token_or_jti] = time.time() + 86400
        return True
    return False


def revoke_user_tokens(user_id: int) -> None:
    """Foydalanuvchining barcha faol tokenlarini bekor qilish (ishdan bo'shatilganda/parol o'zgarganda)"""
    _user_revocation_timestamps[int(user_id)] = time.time()


def is_token_revoked(payload: dict) -> bool:
    """Token qora ro'yxatda yoki foydalanuvchi sessiyasi bekor qilinganligini tekshirish"""
    jti = payload.get("jti")
    now = time.time()

    # Eskirgan jti larni xotiradan tozalash
    if len(_blacklisted_jtis) > 1000:
        stale = [k for k, v in _blacklisted_jtis.items() if v < now]
        for k in stale:
            _blacklisted_jtis.pop(k, None)

    if jti and jti in _blacklisted_jtis:
        return True

    user_id = payload.get("sub") or payload.get("user_id")
    iat = payload.get("iat")
    if user_id:
        try:
            uid = int(user_id)
            revoked_at = _user_revocation_timestamps.get(uid)
            if revoked_at is not None and (iat is None or iat <= revoked_at):
                return True
        except (ValueError, TypeError):
            pass

    return False


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8")[:72], hashed_password.encode("utf-8"))
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    pwd_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    now_dt = datetime.now(timezone.utc)
    if expires_delta:
        expire = now_dt + expires_delta
    else:
        expire = now_dt + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode.update({
        "exp": expire,
        "iat": now_dt.timestamp(),
        "jti": str(uuid.uuid4()),
        "boot_nonce": SERVER_BOOT_NONCE,
    })
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        if is_token_revoked(payload):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Ushbu sessiya bekor qilingan (token revoked). Iltimos, qaytadan tizimga kiring.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token yaroqsiz yoki muddati o'tgan",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def session_is_valid(db, payload, user):
    from app.models.token_revocation import TokenRevocation
    if 'auth_version' in payload and payload['auth_version'] != (user.tokens_valid_after or 0):
        return False
    if (user.tokens_valid_after or 0) > 0 and float(payload.get('iat') or 0) <= user.tokens_valid_after:
        return False
    if payload.get('jti') and await db.get(TokenRevocation, payload['jti']) is not None:
        return False
    return True


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
):
    from app.models.user import User

    payload = decode_token(credentials.credentials)
    user_id: str = payload.get("sub")
    token_role: Optional[str] = payload.get("role")

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token ma'lumotlari noto'g'ri",
        )

    try:
        uid = int(user_id)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token formati noto'g'ri",
        )

    result = await db.execute(select(User).where(User.id == uid))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Foydalanuvchi topilmadi",
        )
    if not await session_is_valid(db, payload, user):
        raise HTTPException(401, 'Sessiya bekor qilingan. Qaytadan kiring.')
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Foydalanuvchi faol emas",
        )

    # Rol o'zgargan bo'lsa tokenni rad etish
    user_role_str = user.role.value if hasattr(user.role, "value") else str(user.role)
    if token_role and token_role != user_role_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Foydalanuvchi roli o'zgargan. Iltimos, qaytadan tizimga kiring.",
        )

    # Ofitsiant, oshpaz va kassirlar admin tomonidan tasdiqlangan bo'lishi shart
    if user_role_str in ("waiter", "chef", "cashier") and not getattr(user, "is_approved", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akkauntingiz Admin tomonidan tasdiqlanmagan!",
        )

    from app.core.tenant import apply_tenant_scope
    await apply_tenant_scope(db, user)
    return user


async def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_optional),
    db: AsyncSession = Depends(get_db),
):
    """Autentifikatsiya ixtiyoriy bo'lgan endpointlar uchun (masalan, buyurtma kuzatish)"""
    if not credentials or not credentials.credentials:
        return None
    try:
        from app.models.user import User

        payload = decode_token(credentials.credentials)
        user_id = payload.get("sub")
        token_role = payload.get("role")
        if not user_id:
            return None

        result = await db.execute(select(User).where(User.id == int(user_id)))
        user = result.scalar_one_or_none()
        if not user or not user.is_active:
            return None
        if not await session_is_valid(db, payload, user):
            return None

        user_role_str = user.role.value if hasattr(user.role, "value") else str(user.role)
        if token_role and token_role != user_role_str:
            return None

        if user_role_str in ('waiter', 'chef', 'cashier') and not user.is_approved:
            return None
        from app.core.tenant import apply_tenant_scope
        await apply_tenant_scope(db, user)
        return user
    except Exception:
        return None


def require_role(*roles: str):
    """Role-based access control dependency"""
    async def role_checker(current_user=Depends(get_current_user)):
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Bu amal uchun ruxsat yo'q. Kerakli rol: {', '.join(roles)}",
            )
        return current_user
    return role_checker
