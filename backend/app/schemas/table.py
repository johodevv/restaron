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


class TableResponse(TableBase):
    id: int
    restaurant_id: int
    qr_token: str
    qr_image_url: Optional[str] = None
    status: TableStatus
    is_active: bool
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

    model_config = {"from_attributes": True}
