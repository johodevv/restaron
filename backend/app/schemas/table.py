"""
Stol sxemalari (Pydantic)
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from app.models.table import TableStatus


class TableBase(BaseModel):
    number: int = Field(..., gt=0)
    name: Optional[str] = None
    room: Optional[str] = None
    capacity: int = Field(default=4, gt=0)


class TableCreate(TableBase):
    restaurant_id: int


class TableUpdate(BaseModel):
    number: Optional[int] = None
    name: Optional[str] = None
    room: Optional[str] = None
    capacity: Optional[int] = None
    status: Optional[TableStatus] = None
    is_active: Optional[bool] = None
    reserved_by_name: Optional[str] = None
    reserved_by_phone: Optional[str] = None
    reserved_time: Optional[str] = None
    reserved_guests: Optional[int] = None
    deposit_amount: Optional[float] = Field(None, ge=0, le=10_000_000_000, allow_inf_nan=False)
    reservation_note: Optional[str] = None


class TableReserveRequest(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    time: Optional[str] = None
    guests: Optional[int] = None
    reserved_by_name: Optional[str] = None
    reserved_by_phone: Optional[str] = None
    reserved_time: Optional[str] = None
    reserved_guests: Optional[int] = None
    deposit_amount: Optional[float] = Field(0.0, ge=0, le=10_000_000_000, allow_inf_nan=False)
    note: Optional[str] = None
    reservation_note: Optional[str] = None


class TableResponse(TableBase):
    id: int
    restaurant_id: int
    qr_token: str
    qr_image_url: Optional[str] = None
    status: TableStatus
    is_active: bool
    is_unlocked: bool = False
    current_pin: Optional[str] = None
    reserved_by_name: Optional[str] = None
    reserved_by_phone: Optional[str] = None
    reserved_time: Optional[str] = None
    reserved_guests: Optional[int] = None
    deposit_amount: Optional[float] = 0.0
    reservation_note: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class TablePublic(BaseModel):
    """QR kod skanerlagandan keyin mijozga beriladigan ma'lumot"""
    id: int
    number: int
    name: Optional[str] = None
    room: Optional[str] = None
    capacity: int
    restaurant_id: int
    is_unlocked: bool = False
    pin: Optional[str] = None
    current_pin: Optional[str] = None

    model_config = {"from_attributes": True}
