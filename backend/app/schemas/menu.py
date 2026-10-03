"""
Menyu sxemalari (Pydantic)
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ─── Category ─────────────────────────────────────────────
class CategoryBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    name_ru: Optional[str] = None
    name_en: Optional[str] = None
    name_cyrillic: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    image_url: Optional[str] = None
    sort_order: int = 0
    is_active: bool = True


class CategoryCreate(CategoryBase):
    restaurant_id: int


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    name_ru: Optional[str] = None
    name_en: Optional[str] = None
    name_cyrillic: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    image_url: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class CategoryResponse(CategoryBase):
    id: int
    restaurant_id: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── MenuItem ─────────────────────────────────────────────
class MenuItemBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    name_ru: Optional[str] = None
    name_en: Optional[str] = None
    name_cyrillic: Optional[str] = None
    description: Optional[str] = None
    description_ru: Optional[str] = None
    description_en: Optional[str] = None
    description_cyrillic: Optional[str] = None
    price: float = Field(..., gt=0)
    image_url: Optional[str] = None
    is_available: bool = True
    is_stop_list: bool = False
    is_featured: bool = False
    show_price: bool = True
    prep_time_minutes: int = 15
    calories: Optional[int] = None
    weight_grams: Optional[int] = None
    kitchen_station: Optional[str] = "hot_kitchen"
    # Tortiladigan taom (baliq, go'sht): price = 1 birlik narxi
    is_weighted: bool = False
    unit: str = "dona"                       # "kg", "l", "dona"
    sort_order: int = 0


class MenuItemCreate(MenuItemBase):
    category_id: int


class MenuItemUpdate(BaseModel):
    name: Optional[str] = None
    name_ru: Optional[str] = None
    name_en: Optional[str] = None
    name_cyrillic: Optional[str] = None
    description: Optional[str] = None
    description_ru: Optional[str] = None
    description_en: Optional[str] = None
    description_cyrillic: Optional[str] = None
    price: Optional[float] = None
    image_url: Optional[str] = None
    is_available: Optional[bool] = None
    is_stop_list: Optional[bool] = None
    is_featured: Optional[bool] = None
    show_price: Optional[bool] = None
    prep_time_minutes: Optional[int] = None
    calories: Optional[int] = None
    weight_grams: Optional[int] = None
    kitchen_station: Optional[str] = None
    is_weighted: Optional[bool] = None
    unit: Optional[str] = None
    category_id: Optional[int] = None
    sort_order: Optional[int] = None


class MenuItemResponse(MenuItemBase):
    id: int
    category_id: int
    total_ordered: int
    avg_rating: float
    rating_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class CategoryWithItems(CategoryResponse):
    """Kategoriya va uning taomlar ro'yxati"""
    items: List[MenuItemResponse] = []

    model_config = {"from_attributes": True}
