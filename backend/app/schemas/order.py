"""
Buyurtma sxemalari (Pydantic)
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from app.models.order import OrderStatus, CallStatus


# ─── OrderItem ────────────────────────────────────────────
class OrderItemCreate(BaseModel):
    menu_item_id: int
    quantity: int = Field(..., gt=0, le=50)
    special_note: Optional[str] = None


class OrderItemResponse(BaseModel):
    id: int
    menu_item_id: int
    quantity: int
    unit_price: float
    total_price: float
    special_note: Optional[str] = None
    is_prepared: bool
    prepared_at: Optional[datetime] = None

    # Nested menu item info
    menu_item_name: Optional[str] = None
    menu_item_image: Optional[str] = None

    model_config = {"from_attributes": True}


# ─── Order ────────────────────────────────────────────────
class OrderCreate(BaseModel):
    table_id: int
    customer_name: Optional[str] = None
    customer_note: Optional[str] = None
    items: List[OrderItemCreate] = Field(..., min_length=1)


class CallWaiterRequest(BaseModel):
    table_id: int
    note: Optional[str] = None


class OrderStatusUpdate(BaseModel):
    status: OrderStatus
    note: Optional[str] = None


class OrderDeliverRequest(BaseModel):
    """Ofitsiant 'Yetkazib berdim' tugmasini bosganda ixtiyoriy izoh"""
    note: Optional[str] = None


class OrderResponse(BaseModel):
    id: int
    order_number: str
    restaurant_id: int
    table_id: int
    table_number: Optional[int] = None
    waiter_id: Optional[int] = None
    waiter_name: Optional[str] = None
    customer_name: Optional[str] = None
    customer_note: Optional[str] = None
    status: OrderStatus
    subtotal: float
    discount: float
    total: float
    is_paid: bool
    call_waiter: bool
    call_status: Optional[CallStatus] = None
    call_note: Optional[str] = None
    items: List[OrderItemResponse] = []
    created_at: datetime
    preparing_at: Optional[datetime] = None
    ready_at: Optional[datetime] = None
    served_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class OrderSummary(BaseModel):
    """Ro'yxat uchun qisqartirilgan buyurtma"""
    id: int
    order_number: str
    table_id: int
    table_number: Optional[int] = None
    waiter_id: Optional[int] = None
    waiter_name: Optional[str] = None
    status: OrderStatus
    total: float
    items_count: int
    call_waiter: bool = False
    call_status: Optional[CallStatus] = None
    call_note: Optional[str] = None
    created_at: datetime
    ready_at: Optional[datetime] = None
    served_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class BillItemSummary(BaseModel):
    menu_item_id: int
    name: str
    quantity: int
    unit_price: float
    total_price: float
    special_notes: List[str] = []


class TableBillResponse(BaseModel):
    table_id: int
    table_number: int
    room: Optional[str] = None
    restaurant_name: str
    restaurant_phone: Optional[str] = None
    restaurant_address: Optional[str] = None
    status: str
    waiter_name: Optional[str] = None
    orders_count: int
    order_numbers: List[str] = []
    items: List[BillItemSummary] = []
    subtotal: float
    service_fee_percent: float = 10.0
    service_fee_amount: float
    discount: float = 0.0
    grand_total: float
    has_active_orders: bool
    is_paid: bool
    created_at: Optional[datetime] = None


class WaiterCallResponse(BaseModel):
    id: int  # Notification ID or synthetic ID
    type: str = "call_waiter"
    table_id: int
    table_number: int
    room: Optional[str] = None
    note: Optional[str] = None
    order_id: Optional[int] = None
    created_at: datetime
    is_resolved: bool = False


