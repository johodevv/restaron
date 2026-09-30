"""
Qarzlar va Nasiya Pydantic sxemalari
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class DebtCreate(BaseModel):
    restaurant_id: int
    order_id: Optional[int] = None
    customer_name: str = Field(..., min_length=2)
    customer_phone: str = Field(..., min_length=7)
    amount: float = Field(..., gt=0)
    due_date: Optional[datetime] = None
    note: Optional[str] = None


class DebtUpdate(BaseModel):
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    amount: Optional[float] = None
    due_date: Optional[datetime] = None
    note: Optional[str] = None
    status: Optional[str] = None


class DebtPayment(BaseModel):
    payment_amount: float = Field(..., gt=0)
    note: Optional[str] = None


class SendSMSRequest(BaseModel):
    custom_message: Optional[str] = None


class DebtResponse(BaseModel):
    id: int
    restaurant_id: int
    order_id: Optional[int] = None
    customer_name: str
    customer_phone: str
    amount: float
    paid_amount: float
    remaining_amount: float
    status: str
    due_date: Optional[datetime] = None
    note: Optional[str] = None
    last_sms_sent_at: Optional[datetime] = None
    sms_count: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DebtStatsResponse(BaseModel):
    total_debt_amount: float
    total_paid_amount: float
    total_remaining_amount: float
    unpaid_count: int
    paid_count: int
