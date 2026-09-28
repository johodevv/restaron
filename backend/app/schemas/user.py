"""
Foydalanuvchi sxemalari (Pydantic)
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from app.models.user import UserRole


class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    full_name: str = Field(..., min_length=2, max_length=100)
    phone: Optional[str] = None
    role: UserRole = UserRole.WAITER


class UserCreate(UserBase):
    password: str = Field(..., min_length=6, max_length=100)
    restaurant_id: Optional[int] = None


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = None
    avatar_url: Optional[str] = None


class UserPasswordChange(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=6)


class UserResponse(UserBase):
    id: int
    is_active: bool
    avatar_url: Optional[str] = None
    restaurant_id: Optional[int] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class UserPublic(BaseModel):
    """Umumiy foydalanuvchi ma'lumoti"""
    id: int
    full_name: str
    role: UserRole
    avatar_url: Optional[str] = None

    model_config = {"from_attributes": True}


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
