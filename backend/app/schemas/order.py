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
    # O'lchanadigan taom hajmi: "1.5 L", "1.4 kg" (ixtiyoriy)
    portion_size: Optional[str] = Field(default=None, max_length=50)
    # Tortiladigan taomning aniq og'irligi (kg/l). Narx shunga ko'paytiriladi.
    weight: Optional[float] = Field(default=None, gt=0, le=1000)


class OrderItemResponse(BaseModel):
    id: int
    menu_item_id: int
    quantity: int
    unit_price: float
    total_price: float
    special_note: Optional[str] = None
    portion_size: Optional[str] = None
    item_time: Optional[str] = None

    # Tortiladigan taom (baliq, go'sht) ma'lumotlari
    weight: Optional[float] = None          # aniq tortilgan og'irlik
    manual_price: Optional[float] = None    # qo'lda kiritilgan summa (kg o'rniga)
    is_weighted: bool = False               # bu taom tortiladimi
    unit: str = "dona"                      # "kg", "l", "dona"
    sent_to_kitchen: bool = False
    sent_to_kitchen_at: Optional[datetime] = None
    # Shu qatordan oshxonaga allaqachon nechta yuborilgan.
    # quantity > sent_quantity bo'lsa — farqi hali yuborilmagan.
    sent_quantity: int = 0
    is_prepared: bool = False
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


class WaiterOrderCreate(BaseModel):
    """Ofitsiant yoki kassir yangi zakaz yaratishi (Ali Poster uslubida)"""
    restaurant_id: int
    table_id: Optional[int] = None
    order_type: str = "table"               # "table" (Столы), "takeaway" (С собой), "delivery" (Доставка)
    hall_name: Optional[str] = None         # "Балкон", "Хона", "Тераса"
    customer_name: Optional[str] = None
    kitchen_note: Optional[str] = None      # Комент. к кухне
    receipt_note: Optional[str] = None      # Комент. к чеку
    items: List[OrderItemCreate] = []


class WaiterAddItemsRequest(BaseModel):
    """Ochiq stolga qo'shimcha taomlar qo'shish (Dozakaz)"""
    items: List[OrderItemCreate] = Field(..., min_length=1)
    send_to_kitchen_immediately: bool = False


class UpdateItemQtyRequest(BaseModel):
    """Taom sonini o'zgartirish [- 1 +]"""
    quantity: int = Field(..., gt=0)


class UpdateItemWeightRequest(BaseModel):
    """Tortiladigan taom narxini belgilash.

    Ikki yo'l bilan:
      * `price` — ofitsiant tarozidagi SUMMANI to'g'ridan-to'g'ri yozadi
        (asosiy yo'l: "baliqni kg emas, pulini yoz");
      * `weight` — aniq og'irlik (kg), narx 1 kg narxiga ko'paytiriladi.
    Ikkisi birga berilsa: summa — `price`, chekda esa og'irlik ham
    ko'rinadi (oshxona nechchi kg ekanini bilishi uchun).
    """
    weight: Optional[float] = Field(default=None, gt=0, le=1000)
    price: Optional[float] = Field(default=None, ge=0, le=1_000_000_000)


class UpdateItemSizeRequest(BaseModel):
    """O'lchanadigan taom hajmini belgilash: 1.5 L, 1.4 kg"""
    portion_size: Optional[str] = Field(default=None, max_length=50)


class OrderNoteUpdate(BaseModel):
    """Oshxona yoki chek izohini yangilash"""
    kitchen_note: Optional[str] = None
    receipt_note: Optional[str] = None


class OrderCheckoutRequest(BaseModel):
    """Kassada to'lovni qabul qilish va hisobni yopish"""
    payment_method: str = "cash"            # cash, card, click, debt, mixed
    cash_amount: float = 0.0
    card_amount: float = 0.0
    click_amount: float = 0.0
    debt_amount: float = 0.0
    discount: float = 0.0
    service_fee_percent: Optional[float] = None
    # Qarz (Nasiya) uchun ma'lumotlar
    debt_customer_name: Optional[str] = None
    debt_customer_phone: Optional[str] = None
    debt_due_date: Optional[datetime] = None
    debt_note: Optional[str] = None
    print_receipt: bool = True


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
    room: Optional[str] = None
    waiter_id: Optional[int] = None
    waiter_name: Optional[str] = None
    customer_name: Optional[str] = None
    customer_note: Optional[str] = None
    order_type: str = "table"
    hall_name: Optional[str] = None
    kitchen_note: Optional[str] = None
    receipt_note: Optional[str] = None
    status: OrderStatus
    subtotal: float
    service_fee_percent: float = 12.0
    service_fee_amount: float = 0.0
    discount: float = 0.0
    total: float
    is_paid: bool
    payment_method: Optional[str] = "cash"
    cash_amount: float = 0.0
    card_amount: float = 0.0
    click_amount: float = 0.0
    debt_amount: float = 0.0
    waiter_share_amount: float = 0.0
    call_waiter: bool = False
    call_status: Optional[CallStatus] = None
    call_note: Optional[str] = None
    items: List[OrderItemResponse] = []
    created_at: datetime
    preparing_at: Optional[datetime] = None
    ready_at: Optional[datetime] = None
    served_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
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
    portion_size: Optional[str] = None
    weight: Optional[float] = None
    # Ofitsiant qo'lda yozgan summa (baliqning kg i emas, puli)
    manual_price: Optional[float] = None
    unit: str = "dona"
    is_weighted: bool = False
    # Tortiladigan taomni admin panelda tuzatish uchun kerak
    # (masalan 1.5 kg deb olingan baliq 1.7 kg chiqsa).
    order_id: Optional[int] = None
    order_item_id: Optional[int] = None
    # Shu qatorga tegishli BARCHA buyurtma qatorlari (taom qaytarilganda
    # aniq shulardan olib tashlanadi)
    order_item_ids: List[int] = []
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


