"""Preview and atomically combine two open accounts, retaining an audit snapshot."""
from datetime import datetime, timezone
from fastapi import HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from app.core.audit import log_audit_event
from app.core.deposits import record_movement
from app.core.money import money_sum, percent
from app.core.transactions import lock_rows
from app.models.order import Order, OrderStatus
from app.models.table import Table, TableStatus


class MergeAccountsRequest(BaseModel):
    source_order_id: int = Field(gt=0)
    target_order_id: int = Field(gt=0)
    source_version: int = Field(gt=0)
    target_version: int = Field(gt=0)


async def read_merge(db, source_id, target_id, user):
    from app.routers.orders import load_order_full
    if source_id == target_id:
        raise HTTPException(400, 'Bir stol hisobini o‘ziga qo‘shib bo‘lmaydi')
    tables = (await db.scalars(select(Table).where(Table.id.in_([source_id, target_id])))).all()
    by_id = {table.id: table for table in tables}
    if len(by_id) != 2:
        raise HTTPException(404, 'Stol topilmadi')
    source_table, target_table = by_id[source_id], by_id[target_id]
    if source_table.restaurant_id != target_table.restaurant_id or (
        user.role.value != 'developer' and source_table.restaurant_id != user.restaurant_id
    ):
        raise HTTPException(403, 'Boshqa restoran hisobini qo‘shib bo‘lmaydi')
    if any(not table.is_active or table.status in (TableStatus.RESERVED, TableStatus.MAINTENANCE) for table in tables):
        raise HTTPException(409, 'Bron yoki ta’mirdagi stol hisobini qo‘shib bo‘lmaydi')
    ids = (await db.scalars(select(Order.id).where(
        Order.table_id.in_([source_id, target_id]), Order.is_paid == False,
        Order.status.notin_([OrderStatus.PAID, OrderStatus.CANCELLED]),
    ))).all()
    orders = [await load_order_full(db, order_id) for order_id in ids]
    sources = [order for order in orders if order.table_id == source_id]
    targets = [order for order in orders if order.table_id == target_id]
    if len(sources) != 1 or len(targets) != 1:
        raise HTTPException(409, 'Har ikkala stolda bittadan ochiq hisob bo‘lishi kerak. Hisoblarni yangilang')
    source, target = sources[0], targets[0]
    if not source.items or not target.items:
        raise HTTPException(409, 'Bo‘sh hisobni birlashtirib bo‘lmaydi')
    if any(any(getattr(order, name, 0) for name in ('cash_amount', 'card_amount', 'click_amount', 'debt_amount', 'advance_amount')) for order in orders):
        raise HTTPException(409, 'Hisobda oldingi to‘lov yozuvi bor; kassir tekshirishi kerak')
    subtotal = money_sum([source.subtotal, target.subtotal])
    discount = money_sum([source.discount, target.discount])
    fee = percent(subtotal, target.service_fee_percent)
    total = money_sum([subtotal, fee, -discount])
    deposit = money_sum([source_table.deposit_amount, target_table.deposit_amount])
    if total < 0 or deposit > total:
        raise HTTPException(409, 'Birlashtirilgan hisobdan chegirma yoki avans ortib ketadi. Avval kassada to‘g‘rilang')
    preview = dict(source_order_id=source.id, target_order_id=target.id,
        source_version=source.version, target_version=target.version,
        source_number=source.order_number, target_number=target.order_number,
        source_table_id=source_id, target_table_id=target_id,
        source_total=source.total, target_total=target.total,
        subtotal=subtotal, discount=discount, service_fee_percent=target.service_fee_percent,
        service_fee_amount=fee, total=total, deposit_amount=deposit, amount_due=money_sum([total, -deposit]),
        waiter_id=target.waiter_id, waiter_name=(target.waiter.full_name or target.waiter.username) if target.waiter else None)
    return source_table, target_table, source, target, preview


async def merge_accounts(db, source_id, target_id, payload, user, idempotency):
    from app.routers.orders import build_order_response, recalc_order_totals, _finish_table_calls
    from app.websockets.manager import manager
    cached = await idempotency.get_cached_response(user.id)
    if cached is not None:
        return cached
    await lock_rows(db, Order, [payload.source_order_id, payload.target_order_id])
    await lock_rows(db, Table, [source_id, target_id])
    source_table, target_table, source, target, preview = await read_merge(db, source_id, target_id, user)
    if (source.id, target.id, source.version, target.version) != (
        payload.source_order_id, payload.target_order_id, payload.source_version, payload.target_version
    ):
        raise HTTPException(409, 'Tasdiqlash vaqtida hisob o‘zgargan. Yangilangan summani qayta tekshiring')
    before = [build_order_response(order).model_dump(mode='json') for order in (source, target)]
    moved_ids = [item.id for item in source.items]
    old_statuses = [source.status, target.status]
    for item in list(source.items):
        item.order = target
    target.discount = preview['discount']
    for name in ('kitchen_note', 'receipt_note'):
        if getattr(source, name):
            setattr(target, name, '\n'.join(filter(None, [getattr(target, name), f"{source.order_number}: {getattr(source, name)}"])))
    if (source_table.deposit_amount or 0) > 0:
        amount = source_table.deposit_amount
        await record_movement(db, source_table, user, -amount, 'transfer_out')
        await record_movement(db, target_table, user, amount, 'transfer_in')
        source_table.deposit_amount = 0
        target_table.deposit_amount = preview['deposit_amount']
    resolved_ids = await _finish_table_calls(db, source.restaurant_id, source_id)
    source.status = OrderStatus.CANCELLED  # Closed source, explicitly linked; no refund or cancellation receipt.
    source.merged_into_order_id = target.id
    source.closed_at = datetime.now(timezone.utc)
    for name in ('subtotal', 'service_fee_amount', 'discount', 'total', 'waiter_share_amount'):
        setattr(source, name, 0)
    source_table.status = TableStatus.AVAILABLE
    source_table.is_unlocked = False
    source_table.current_pin = None
    for name in ('reserved_by_name', 'reserved_by_phone', 'reserved_time', 'reserved_guests', 'reservation_note'):
        setattr(source_table, name, None)
    target_table.status = TableStatus.OCCUPIED
    if all(status == OrderStatus.SERVED for status in old_statuses):
        target.status = OrderStatus.SERVED
    elif all(status == OrderStatus.READY for status in old_statuses):
        target.status = OrderStatus.READY
    else:
        target.status = OrderStatus.PREPARING if any(item.sent_quantity or item.sent_to_kitchen for item in target.items) else OrderStatus.PENDING
        target.ready_at = None
    await recalc_order_totals(db, target)
    target.waiter_share_amount = percent(target.subtotal, target.waiter_share_percent)
    await db.flush()
    result = dict(success=True, message='Hisoblar birlashtirildi', order=build_order_response(target).model_dump(mode='json'), **preview)
    audit = await log_audit_event(db, source.restaurant_id, 'table_accounts_merged', user=user,
        entity_type='order', entity_id=source.id,
        details=dict(before=before, after=result, moved_item_ids=moved_ids))
    if audit is None:
        raise HTTPException(500, 'Birlashtirish tarixi saqlanmadi; hisoblar o‘zgartirilmadi')
    await idempotency.save_response(user.id, result)
    await db.commit()
    await manager.broadcast_to_restaurant(source.restaurant_id, dict(type='order_cancelled', order_id=source.id,
        table_id=source_id, merged_into_order_id=target.id))
    await manager.broadcast_to_restaurant(source.restaurant_id, dict(type='order_updated', order=result['order'], order_id=target.id, table_id=target_id))
    for table_id, status in [(source_id, 'available'), (target_id, 'occupied')]:
        await manager.broadcast_to_restaurant(source.restaurant_id, dict(type='table_status_updated', table_id=table_id, status=status, new_status=status))
        await manager.broadcast_to_table(source.restaurant_id, table_id, dict(type='order_updated', order_id=target.id if table_id == target_id else source.id, table_id=table_id))
    if resolved_ids:
        await manager.broadcast_to_restaurant(source.restaurant_id, dict(type='call_completed', table_id=source_id, resolved_call_ids=resolved_ids))
    return result
