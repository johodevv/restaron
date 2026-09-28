"""
Baholash (Review) API — Mijozlardan fikr-mulohaza
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from pydantic import BaseModel, Field
from typing import Optional, List

from app.core.database import get_db
from app.core.security import require_role
from app.models.review import Review
from app.models.menu import MenuItem
from app.models.order import Order

router = APIRouter(prefix="/reviews", tags=["⭐ Baholash"])


class ReviewCreate(BaseModel):
    restaurant_id: int
    order_id: Optional[int] = None
    menu_item_id: Optional[int] = None
    food_rating: Optional[int] = Field(None, ge=1, le=5)
    food_comment: Optional[str] = None
    waiter_id: Optional[int] = None
    service_rating: Optional[int] = Field(None, ge=1, le=5)
    service_comment: Optional[str] = None
    customer_name: Optional[str] = None


@router.post("/", status_code=201, summary="Baho qo'yish (mijoz)")
async def create_review(payload: ReviewCreate, db: AsyncSession = Depends(get_db)):
    """Mijoz taom va/yoki ofitsiantga baho beradi (auth kerak emas)"""
    overall = None
    ratings = [r for r in [payload.food_rating, payload.service_rating] if r]
    if ratings:
        overall = sum(ratings) / len(ratings)

    review = Review(
        restaurant_id=payload.restaurant_id,
        order_id=payload.order_id,
        menu_item_id=payload.menu_item_id,
        food_rating=payload.food_rating,
        food_comment=payload.food_comment,
        waiter_id=payload.waiter_id,
        service_rating=payload.service_rating,
        service_comment=payload.service_comment,
        overall_rating=overall,
        customer_name=payload.customer_name,
    )
    db.add(review)

    # Taom o'rtacha reytingini yangilash
    if payload.menu_item_id and payload.food_rating:
        item_result = await db.execute(
            select(MenuItem).where(MenuItem.id == payload.menu_item_id)
        )
        menu_item = item_result.scalar_one_or_none()
        if menu_item:
            new_count = menu_item.rating_count + 1
            new_avg = (menu_item.avg_rating * menu_item.rating_count + payload.food_rating) / new_count
            menu_item.avg_rating = round(new_avg, 2)
            menu_item.rating_count = new_count

    await db.flush()
    return {"success": True, "message": "Rahmat! Fikringiz qabul qilindi."}


@router.get("/", summary="Restoran reytinglari (query param)")
@router.get("/restaurant/{restaurant_id}", summary="Restoran reytinglari (path param)")
async def list_reviews(
    restaurant_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin", "developer")),
):
    target_id = restaurant_id or current_user.restaurant_id or 1
    result = await db.execute(
        select(Review)
        .where(Review.restaurant_id == target_id, Review.is_published == True)
        .order_by(Review.created_at.desc())
        .limit(100)
    )
    reviews = result.scalars().all()
    return [
        {
            "id": r.id,
            "food_rating": r.food_rating,
            "food_comment": r.food_comment,
            "service_rating": r.service_rating,
            "service_comment": r.service_comment,
            "overall_rating": r.overall_rating,
            "customer_name": r.customer_name,
            "created_at": r.created_at,
        }
        for r in reviews
    ]
