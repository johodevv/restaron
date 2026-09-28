"""
Menyu API — Kategoriyalar va Taomlar
"""
import os
import uuid
import aiofiles
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List, Optional

from app.core.database import get_db
from app.core.security import require_role
from app.core.config import settings
from app.models.menu import Category, MenuItem
from app.models.user import User, UserRole
from app.schemas.menu import (
    CategoryCreate, CategoryUpdate, CategoryResponse,
    MenuItemCreate, MenuItemUpdate, MenuItemResponse, CategoryWithItems
)

router = APIRouter(prefix="/menu", tags=["🍽️ Menyu"])

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}


async def save_upload_file(upload_file: UploadFile, subfolder: str) -> str:
    """Rasm saqlash"""
    upload_dir = os.path.join(settings.UPLOAD_DIR, subfolder)
    os.makedirs(upload_dir, exist_ok=True)

    ext = upload_file.filename.rsplit(".", 1)[-1].lower()
    file_name = f"{uuid.uuid4()}.{ext}"
    file_path = os.path.join(upload_dir, file_name)

    content = await upload_file.read()
    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)

    return f"/uploads/{subfolder}/{file_name}"


# ─── Categories ──────────────────────────────────────────
@router.post("/categories", response_model=CategoryResponse, status_code=201,
             summary="Kategoriya qo'shish")
async def create_category(
    payload: CategoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "developer")),
):
    category = Category(**payload.model_dump())
    db.add(category)
    await db.flush()
    await db.refresh(category)
    return CategoryResponse.model_validate(category)


@router.get("/categories", response_model=List[CategoryResponse], summary="Kategoriyalar ro'yxati")
async def list_categories(
    restaurant_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Category)
        .where(Category.restaurant_id == restaurant_id, Category.is_active == True)
        .order_by(Category.sort_order, Category.id)
    )
    return [CategoryResponse.model_validate(c) for c in result.scalars().all()]


@router.get("/categories/{category_id}", response_model=CategoryWithItems,
            summary="Kategoriya va taomlar")
async def get_category_with_items(
    category_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Category)
        .options(selectinload(Category.items))
        .where(Category.id == category_id)
    )
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=404, detail="Kategoriya topilmadi")
    return CategoryWithItems.model_validate(category)


@router.get("/full/{restaurant_id}", response_model=List[CategoryWithItems],
            summary="To'liq menyu (QR sahifasi uchun)")
async def get_full_menu(restaurant_id: int, db: AsyncSession = Depends(get_db)):
    """Mijoz QR orqali kirganida to'liq menyuni oladi (auth kerak emas)"""
    result = await db.execute(
        select(Category)
        .options(selectinload(Category.items))
        .where(Category.restaurant_id == restaurant_id, Category.is_active == True)
        .order_by(Category.sort_order)
    )
    return [CategoryWithItems.model_validate(c) for c in result.scalars().all()]


@router.patch("/categories/{category_id}", response_model=CategoryResponse,
              summary="Kategoriyani yangilash")
async def update_category(
    category_id: int,
    payload: CategoryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "developer")),
):
    result = await db.execute(select(Category).where(Category.id == category_id))
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=404, detail="Kategoriya topilmadi")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(category, field, value)
    await db.flush()
    await db.refresh(category)
    return CategoryResponse.model_validate(category)


@router.delete("/categories/{category_id}", status_code=204, summary="Kategoriyani o'chirish")
async def delete_category(
    category_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "developer")),
):
    result = await db.execute(select(Category).where(Category.id == category_id))
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=404, detail="Kategoriya topilmadi")
    await db.delete(category)


# ─── Menu Items ───────────────────────────────────────────
@router.post("/items", response_model=MenuItemResponse, status_code=201,
             summary="Taom qo'shish")
async def create_menu_item(
    payload: MenuItemCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "developer")),
):
    item = MenuItem(**payload.model_dump())
    db.add(item)
    await db.flush()
    await db.refresh(item)
    return MenuItemResponse.model_validate(item)


@router.post("/items/{item_id}/image", response_model=MenuItemResponse,
             summary="Taom rasmi yuklash")
async def upload_item_image(
    item_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "developer")),
):
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Faqat rasm fayllari qabul qilinadi")

    result = await db.execute(select(MenuItem).where(MenuItem.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Taom topilmadi")

    image_url = await save_upload_file(file, "menu_items")
    item.image_url = image_url
    await db.flush()
    await db.refresh(item)
    return MenuItemResponse.model_validate(item)


@router.patch("/items/{item_id}", response_model=MenuItemResponse, summary="Taomni yangilash")
async def update_menu_item(
    item_id: int,
    payload: MenuItemUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "developer")),
):
    result = await db.execute(select(MenuItem).where(MenuItem.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Taom topilmadi")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    await db.flush()
    await db.refresh(item)
    return MenuItemResponse.model_validate(item)


@router.delete("/items/{item_id}", status_code=204, summary="Taomni o'chirish")
async def delete_menu_item(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "developer")),
):
    result = await db.execute(select(MenuItem).where(MenuItem.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Taom topilmadi")
    await db.delete(item)
