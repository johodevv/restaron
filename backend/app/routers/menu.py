"""
Menyu API — Kategoriyalar va Taomlar
"""
import os
import uuid
import aiofiles
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import List, Optional

from app.core.database import get_db
from app.core.security import require_role
from app.core.config import settings
from app.models.menu import Category, MenuItem
from app.models.order import OrderItem
from app.models.user import User, UserRole
from app.schemas.menu import (
    CategoryCreate, CategoryUpdate, CategoryResponse,
    MenuItemCreate, MenuItemUpdate, MenuItemResponse, CategoryWithItems
)

router = APIRouter(prefix="/menu", tags=["🍽️ Menyu"])

# Telefon va Mac'dan kelgan suratlar ko'pincha HEIC bo'ladi, ba'zi
# brauzerlar esa turini umuman yubormaydi. Shuning uchun ro'yxat keng
# va tur noma'lum bo'lsa fayl kengaytmasiga qaraymiz.
ALLOWED_IMAGE_TYPES = {
    "image/jpeg", "image/jpg", "image/pjpeg",
    "image/png", "image/webp", "image/gif",
    "image/heic", "image/heif", "image/bmp", "image/avif",
}
ALLOWED_IMAGE_EXTS = {
    "jpg", "jpeg", "png", "webp", "gif", "heic", "heif", "bmp", "avif",
}
MAX_IMAGE_BYTES = 12 * 1024 * 1024   # 12 MB


def _image_ext(filename: Optional[str]) -> str:
    """Fayl kengaytmasini xavfsiz aniqlash ("photo.JPG" -> "jpg")"""
    name = (filename or "").strip()
    if "." not in name:
        return ""
    ext = name.rsplit(".", 1)[-1].lower()
    # Faqat harf va raqam qoldiramiz — fayl nomi orqali papkadan
    # chiqib ketishning oldini oladi.
    ext = "".join(ch for ch in ext if ch.isalnum())
    return ext[:8]


def check_image_upload(upload_file: UploadFile) -> str:
    """Yuklangan fayl rasm ekanini tekshirib, kengaytmasini qaytaradi.

    Tur (content_type) ba'zi brauzerlarda bo'sh yoki "application/octet-stream"
    bo'ladi — bunda kengaytmaga qaraymiz. Aks holda telefondan yuklangan
    oddiy surat ham rad etilib, admin sababni bilmay qoladi.
    """
    ext = _image_ext(upload_file.filename)
    ctype = (upload_file.content_type or "").lower().split(";")[0].strip()

    if ctype in ALLOWED_IMAGE_TYPES:
        return ext or (ctype.split("/")[-1] if "/" in ctype else "jpg")
    if ext in ALLOWED_IMAGE_EXTS:
        return ext

    raise HTTPException(
        status_code=400,
        detail=(
            f"Bu fayl rasm emas (turi: {ctype or 'nomalum'}, "
            f"kengaytmasi: {ext or 'yoq'}). "
            f"Ruxsat etilgan: JPG, PNG, WEBP, GIF, HEIC."
        ),
    )


async def save_upload_file(upload_file: UploadFile, subfolder: str, ext: str = "") -> str:
    """Rasm saqlash"""
    upload_dir = os.path.join(settings.UPLOAD_DIR, subfolder)
    os.makedirs(upload_dir, exist_ok=True)

    ext = ext or _image_ext(upload_file.filename) or "jpg"
    file_name = f"{uuid.uuid4()}.{ext}"
    file_path = os.path.join(upload_dir, file_name)

    content = await upload_file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Fayl bo'sh — qaytadan tanlang")
    if len(content) > MAX_IMAGE_BYTES:
        mb = len(content) / (1024 * 1024)
        raise HTTPException(
            status_code=400,
            detail=f"Rasm juda katta ({mb:.1f} MB). Eng ko'pi 12 MB. "
                   f"Telefonda rasmni kichraytirib qayta yuklang.",
        )

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

    # Kategoriya o'chirilsa ichidagi taomlar ham o'chadi. Agar o'sha
    # taomlar eski buyurtmalarda ishlatilgan bo'lsa, cheklar arxivi
    # buziladi — shuning uchun to'xtatamiz va nimani qilish kerakligini
    # aytamiz.
    used_res = await db.execute(
        select(MenuItem.name, func.count(OrderItem.id))
        .join(OrderItem, OrderItem.menu_item_id == MenuItem.id)
        .where(MenuItem.category_id == category.id)
        .group_by(MenuItem.id)
    )
    used_names = [row[0] for row in used_res.all()]
    if used_names:
        ro_yxat = ", ".join(used_names[:5])
        agar = " va boshqalar" if len(used_names) > 5 else ""
        raise HTTPException(
            status_code=400,
            detail=f"\"{category.name}\" kategoriyasini o'chirib bo'lmaydi: ichidagi "
                   f"{len(used_names)} ta taom eski buyurtmalarda ishlatilgan "
                   f"({ro_yxat}{agar}). Chek tarixi buzilmasligi uchun avval shu "
                   f"taomlarni boshqa kategoriyaga ko'chiring yoki \"Stop-list\" "
                   f"orqali yashiring.",
        )

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
    ext = check_image_upload(file)

    result = await db.execute(select(MenuItem).where(MenuItem.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Taom topilmadi")

    image_url = await save_upload_file(file, "menu_items", ext)
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

    # Eski buyurtmalarda ishlatilgan taomni o'chirsak, cheklar arxivi
    # buziladi (chekda "Taom #12" bo'lib qoladi). Shuning uchun bunday
    # taom o'chirilmaydi — uni Stop-list orqali yashirish mumkin.
    cnt_res = await db.execute(
        select(func.count(OrderItem.id)).where(OrderItem.menu_item_id == item.id)
    )
    used = cnt_res.scalar() or 0
    if used > 0:
        raise HTTPException(
            status_code=400,
            detail=f"\"{item.name}\" taomini o'chirib bo'lmaydi: u {used} ta buyurtmada "
                   f"ishlatilgan va eski cheklarda ko'rinadi. Menyudan yashirish uchun "
                   f"\"Stop-list\" tugmasini bosing — chek tarixi saqlanib qoladi.",
        )

    await db.delete(item)


@router.patch("/items/{item_id}/toggle-stop-list", response_model=MenuItemResponse, summary="Stop-List (Tugadi / Mavjud) 1 bosishda")
async def toggle_stop_list(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "waiter", "chef", "developer")),
):
    """Admin, Ofitsiant yoki Oshpaz taomni 1 bosish bilan Stop-listga kiritadi yoki chiqaradi"""
    result = await db.execute(
        select(MenuItem).options(selectinload(MenuItem.category)).where(MenuItem.id == item_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Taom topilmadi")

    # Holatni teskarisiga o'zgartirish
    new_stop_state = not bool(item.is_stop_list)
    item.is_stop_list = new_stop_state
    item.is_available = not new_stop_state

    await db.flush()
    await db.refresh(item)

    # Real-time WebSocket orqali barcha ulanganlarga tarqatish
    if item.category:
        from app.websockets.manager import manager
        await manager.broadcast_to_restaurant(
            item.category.restaurant_id,
            {
                "type": "stop_list_updated",
                "item_id": item.id,
                "item_name": item.name,
                "is_stop_list": item.is_stop_list,
                "is_available": item.is_available,
                "message": f"Taom '{item.name}' {'stop-listga kiritildi (tugadi)' if item.is_stop_list else 'stop-listdan chiqarildi'}",
            }
        )

    return MenuItemResponse.model_validate(item)

