from sqlalchemy import select, func
from fastapi import HTTPException
from app.models.deposit import DepositMovement


async def record_movement(db, table, user, amount, kind, *, cash_amount=0, order_id=None):
    # Existing installations may already have a balance without a ledger.
    exists = await db.scalar(select(DepositMovement.id).where(
        DepositMovement.table_id == table.id).limit(1))
    if exists is None and (table.deposit_amount or 0) > 0:
        db.add(DepositMovement(restaurant_id=table.restaurant_id, table_id=table.id,
                              user_id=user.id, kind='opening_balance',
                              amount=table.deposit_amount, cash_amount=0))
    db.add(DepositMovement(restaurant_id=table.restaurant_id, table_id=table.id,
                          user_id=user.id, kind=kind, amount=round(amount, 2),
                          cash_amount=round(cash_amount, 2), order_id=order_id))


async def set_deposit(db, table, user, value):
    if value is None or value < 0:
        raise HTTPException(400, 'Avans manfiy bo‘lishi mumkin emas')
    delta = round(value - (table.deposit_amount or 0), 2)
    if delta:
        await record_movement(db, table, user, delta,
                              'received' if delta > 0 else 'refund', cash_amount=delta)
        table.deposit_amount = round(value, 2)


async def extra_cash_in_range(db, restaurant_id, start, end):
    from app.models.debt import DebtPaymentRecord
    deposits = await db.scalar(select(func.coalesce(func.sum(DepositMovement.cash_amount), 0)).where(
        DepositMovement.restaurant_id == restaurant_id,
        DepositMovement.created_at >= start, DepositMovement.created_at < end))
    debts = await db.scalar(select(func.coalesce(func.sum(DebtPaymentRecord.amount), 0)).where(
        DebtPaymentRecord.restaurant_id == restaurant_id,
        DebtPaymentRecord.created_at >= start, DebtPaymentRecord.created_at < end))
    return float(deposits or 0), float(debts or 0)
