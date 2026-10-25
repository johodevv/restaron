"""Apply restaurant ownership to authenticated ORM reads and writes."""
from fastapi import HTTPException
from sqlalchemy import event, select, text, inspect
from sqlalchemy.orm import Session, with_loader_criteria
from functools import lru_cache


def _models():
    from app.models import (RestaurantSettings, Table, TableZone, Category, Order,
                            Debt, ReceiptArchive, ShiftReport, Review, Notification,
                            AuditLog, PrintJob, CommissionLog)
    from app.models.debt import DebtPaymentRecord
    from app.models.deposit import DepositMovement
    return (RestaurantSettings, Table, TableZone, Category, Order, Debt,
            DebtPaymentRecord, ReceiptArchive, ShiftReport, Review, Notification,
            AuditLog, PrintJob, CommissionLog, DepositMovement)


@lru_cache(maxsize=512)
def _scope_options(rid):
    from app.models import Restaurant, MenuItem, Category, OrderItem, Order
    options = [with_loader_criteria(model, model.restaurant_id == rid, include_aliases=True, propagate_to_loaders=False)
               for model in _models()]
    options.extend([
        with_loader_criteria(Restaurant, Restaurant.id == rid, include_aliases=True, propagate_to_loaders=False),
        with_loader_criteria(MenuItem, MenuItem.category_id.in_(
            select(Category.id).where(Category.restaurant_id == rid)), include_aliases=True, propagate_to_loaders=False),
        with_loader_criteria(OrderItem, OrderItem.order_id.in_(
            select(Order.id).where(Order.restaurant_id == rid)), include_aliases=True, propagate_to_loaders=False),
    ])
    return tuple(options)


@event.listens_for(Session, 'do_orm_execute')
def _scope_statement(state):
    rid = state.session.info.get('restaurant_id')
    if rid is None or not state.is_orm_statement:
        return
    # Every ORM statement, including relationship loads, receives one immutable
    # set of criteria. Reusing it avoids rebuilding 18 expressions per query.
    state.statement = state.statement.options(*_scope_options(rid))


@event.listens_for(Session, 'before_flush')
def _check_ownership(session, flush_context, instances):
    rid = session.info.get('restaurant_id')
    if rid is None:
        return
    from app.models import MenuItem, Category, Order, Table, OrderItem, Debt, Review
    from app.models.user import User
    models = _models()
    for obj in session.new.union(session.dirty):
        if isinstance(obj, models) and obj.restaurant_id != rid:
            raise HTTPException(403, 'Boshqa restoran maʼlumotini o‘zgartirish mumkin emas')
        references = []
        state = inspect(obj)
        def changed(name):
            return obj in session.new or state.attrs[name].history.has_changes()
        if isinstance(obj, MenuItem):
            if changed('category_id'):
                references.append((Category, obj.category_id))
        if isinstance(obj, Order) and obj.table_id is not None and changed('table_id'):
            references.append((Table, obj.table_id))
        if isinstance(obj, OrderItem):
            if changed('menu_item_id'):
                references.append((MenuItem, obj.menu_item_id))
            if changed('order_id'):
                references.append((Order, obj.order_id))
        if isinstance(obj, (Debt, Review)) and obj.order_id is not None and changed('order_id'):
            references.append((Order, obj.order_id))
        if isinstance(obj, Review):
            if obj.menu_item_id is not None:
                references.append((MenuItem, obj.menu_item_id))
            if obj.waiter_id is not None and session.scalar(select(User.id).where(
                    User.id == obj.waiter_id, User.restaurant_id == rid)) is None:
                raise HTTPException(403, 'Ofitsiant ushbu restoranga tegishli emas')
        for model, identity in references:
            if session.scalar(select(model.id).where(model.id == identity)) is None:
                raise HTTPException(403, 'Maʼlumot ushbu restoranga tegishli emas')


async def apply_tenant_scope(db, user):
    role = user.role.value if hasattr(user.role, 'value') else str(user.role)
    if role == 'developer':
        return
    if user.restaurant_id is None:
        raise HTTPException(403, 'Foydalanuvchiga restoran biriktirilmagan')
    db.info['restaurant_id'] = user.restaurant_id
    # One mutation at a time per restaurant also protects aggregate operations
    # (table moves, shift closing) across PostgreSQL workers.
    if db.bind.dialect.name == 'postgresql' and db.info.get('write_request'):
        await db.execute(text('SELECT pg_advisory_xact_lock(73411, :rid)'),
                         {'rid': user.restaurant_id})
