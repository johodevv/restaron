"""Kitchen display: only tickets that were explicitly sent to the kitchen."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.core.security import require_role
from app.models import RestaurantSettings, Order, OrderItem
from app.models.order import OrderStatus
from app.routers.orders import build_order_response

router = APIRouter(prefix='/kitchen', tags=['Oshpaz ekrani'])


@router.get('/orders')
async def kitchen_orders(db=Depends(get_db), user=Depends(require_role('chef', 'admin', 'cashier', 'developer'))):
    settings = await db.scalar(select(RestaurantSettings).where(RestaurantSettings.restaurant_id == user.restaurant_id))
    if not settings or not settings.enable_chef_kds:
        raise HTTPException(403, "Oshpaz ekrani admin tomonidan o'chirilgan")
    orders = (await db.scalars(select(Order).options(
        selectinload(Order.items).selectinload(OrderItem.menu_item),
        selectinload(Order.table), selectinload(Order.waiter)).where(
            Order.restaurant_id == user.restaurant_id, Order.is_paid == False,
            Order.status.notin_([OrderStatus.PAID, OrderStatus.CANCELLED]),
            Order.items.any(OrderItem.sent_quantity > 0)).order_by(Order.created_at, Order.id))).all()
    return [build_order_response(order) for order in orders]
