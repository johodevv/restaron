from datetime import datetime, timezone
import pytest
from sqlalchemy import select, func
from test_audit_regressions import env
from app.core.database import AsyncSessionLocal
from app.models import Order, Table, ReceiptArchive, PrintJob, RestaurantSettings
from app.models.order import OrderStatus
from app.models.audit_log import AuditLog

pytestmark = pytest.mark.anyio


async def test_archive_days_use_tashkent_midnight_and_inclusive_end_day(env):
    rid, req, _ = env
    async with AsyncSessionLocal() as db:
        for i, stamp in enumerate(['2026-10-29T18:59:59.999999', '2026-10-29T19:00:00', '2026-10-30T18:59:59.999999', '2026-10-30T19:00:00']):
            db.add(ReceiptArchive(restaurant_id=rid, receipt_number=f'DATE-{i}', raw_text=f'Original {i}',
                receipt_type='final_bill', payment_method='cash', created_at=datetime.fromisoformat(stamp).replace(tzinfo=timezone.utc)))
        await db.commit()
    response = await req('GET', f'/receipts/?restaurant_id={rid}&from_day=2026-10-30&to_day=2026-10-30')
    assert response.status_code == 200, response.text
    assert [r['receipt_number'] for r in response.json()] == ['DATE-2', 'DATE-1']
    receipt = response.json()[0]
    view = await req('GET', f"/receipts/{receipt['id']}")
    assert view.json()['raw_text'] == 'Original 2'
    assert (await req('GET', f'/receipts/?restaurant_id={rid}&from_day=2026-10-31&to_day=2026-10-30')).status_code == 422
    assert (await req('GET', f'/receipts/?restaurant_id={rid}&from_day=2026-02-30')).status_code == 422
    async with AsyncSessionLocal() as db:
        assert await db.scalar(select(func.count(PrintJob.id))) == 0


@pytest.mark.parametrize('rate,total', [(0,10000), (12.5,11250)])
async def test_rate_changes_only_selected_open_account_and_audits(env, rate, total):
    rid, req, create = env
    order, other = await create(), await create(table=rid+1)
    response = await req('PATCH', f"/orders/{order['id']}/service-fee", {'percent':rate, 'expected_version':order['version']}, role='cashier')
    assert response.status_code == 200, response.text
    result = response.json()
    assert result['total'] == total and result['service_fee_percent'] == rate
    assert result['version'] > order['version']
    assert result['items'][0]['id'] == order['items'][0]['id']
    assert (await req('GET', f"/orders/{other['id']}")).json()['total'] == other['total']
    async with AsyncSessionLocal() as db:
        assert (await db.scalar(select(RestaurantSettings).where(RestaurantSettings.restaurant_id == rid))).service_fee_percent == 10
        assert await db.scalar(select(func.count(AuditLog.id)).where(AuditLog.action == 'order_service_fee_changed')) == 1
        assert await db.scalar(select(func.count(PrintJob.id))) == 0


async def test_rate_rejects_waiter_stale_invalid_and_closed_account(env):
    rid, req, create = env
    order = await create()
    path = f"/orders/{order['id']}/service-fee"
    body = {'percent':0, 'expected_version':order['version']}
    assert (await req('PATCH', path, body, role='waiter')).status_code == 403
    for percent in [-1, 101]:
        assert (await req('PATCH', path, {**body, 'percent':percent})).status_code == 422
    assert (await req('PATCH', f"/orders/{order['id']}/items/{order['items'][0]['id']}/delta", {'delta':1})).status_code == 200
    assert (await req('PATCH', path, body)).status_code == 409
    async with AsyncSessionLocal() as db:
        saved = await db.get(Order, order['id'])
        saved.is_paid = True; saved.status = OrderStatus.PAID; saved.cash_amount = saved.total
        body['expected_version'] = saved.version
        await db.commit()
    assert (await req('PATCH', path, body)).status_code == 409


async def test_rate_audit_failure_or_excess_deposit_rolls_back(env, monkeypatch):
    rid, req, create = env
    order = await create()
    path = f"/orders/{order['id']}/service-fee"
    body = {'percent':0, 'expected_version':order['version']}
    async with AsyncSessionLocal() as db:
        (await db.get(Table, rid)).deposit_amount = 10500
        await db.commit()
    assert (await req('PATCH', path, body)).status_code == 409
    async with AsyncSessionLocal() as db:
        assert (await db.get(Order, order['id'])).total == order['total']
        (await db.get(Table, rid)).deposit_amount = 0
        await db.commit()
    async def failed_audit(*args, **kwargs): return None
    monkeypatch.setattr('app.core.audit.log_audit_event', failed_audit)
    assert (await req('PATCH', path, body)).status_code == 500
    async with AsyncSessionLocal() as db:
        assert (await db.get(Order, order['id'])).total == order['total']
