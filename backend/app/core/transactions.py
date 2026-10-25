"""Shared locking order for order, payment and table mutations."""
from sqlalchemy import select, update, func, or_, and_
from fastapi import HTTPException


async def lock_rows(db, model, ids):
    ids = sorted(set(i for i in ids if i is not None))
    if not ids:
        return
    if db.bind.dialect.name == 'sqlite':
        values = {'id': model.id}
        if hasattr(model, 'updated_at'):
            values['updated_at'] = model.updated_at
        if not db.info.get('write_request'):
            await db.execute(update(model).where(model.id.in_(ids)).values(**values))
    else:
        await db.execute(select(model.id).where(model.id.in_(ids)).order_by(model.id).with_for_update())
    # Preserve unexplained legacy amounts. A normal edit must not silently
    # recalculate a damaged historical account from its remaining item rows.
    if model.__tablename__ in ('orders', 'tables'):
        from app.models.order import Order, OrderItem
        line_sum = select(func.coalesce(func.sum(OrderItem.total_price), 0)).where(OrderItem.order_id == Order.id).scalar_subquery()
        tender = sum(func.coalesce(getattr(Order, field), 0) for field in
                     ('cash_amount', 'card_amount', 'click_amount', 'debt_amount', 'advance_amount'))
        scope = Order.id.in_(ids) if model.__tablename__ == 'orders' else and_(Order.table_id.in_(ids), Order.is_paid == False, Order.status.notin_(['PAID','CANCELLED']))
        broken = await db.scalar(select(Order.id).where(scope, or_(
            func.abs(func.coalesce(Order.subtotal, 0) - line_sum) > .01,
            and_(Order.is_paid == True, func.abs(func.coalesce(Order.total, 0) - tender) > .01),
        )).limit(1))
        if broken is not None:
            raise HTTPException(409, f'Hisob #{broken}: eski summalar taomlar yoki to‘lovlarga mos emas. Dalil asosida tekshirish kerak; yozuv o‘zgartirilmadi.')
