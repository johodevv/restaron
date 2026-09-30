"""
Cheklar Arxivi va Smena Hisobotlari Pydantic sxemalari
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Any, Dict
from datetime import datetime


class ReceiptArchiveResponse(BaseModel):
    id: int
    restaurant_id: int
    order_id: Optional[int] = None
    receipt_number: str
    receipt_type: str
    hall_name: Optional[str] = None
    table_name: Optional[str] = None
    waiter_name: Optional[str] = None
    subtotal: float
    service_fee_percent: float
    service_fee_amount: float
    total_amount: float
    payment_method: str
    cash_amount: float
    card_amount: float
    click_amount: float
    debt_amount: float
    items_json: Optional[Any] = None
    notes: Optional[str] = None
    raw_text: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ShiftReportCreate(BaseModel):
    restaurant_id: int
    report_type: str = "z_report"  # "x_report" yoki "z_report"
    close_shift: bool = True       # Agar true bo'lsa smena yopiladi


class ShiftReportResponse(BaseModel):
    id: int
    restaurant_id: int
    cashier_user_id: Optional[int] = None
    shift_number: int
    report_type: str
    opened_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    total_orders: int
    total_sales: float
    total_cash: float
    total_card: float
    total_click: float
    total_debt: float
    total_service_fee: float
    total_waiter_earnings: float
    waiter_breakdown: Optional[Any] = None
    items_breakdown: Optional[Any] = None
    is_closed: bool
    created_at: datetime
    raw_text: Optional[str] = None

    class Config:
        from_attributes = True
