import asyncio
import pytest
from sqlalchemy import select, func
from test_audit_regressions import env
from app.core.database import AsyncSessionLocal
from app.models import Order, OrderItem, Table, PrintJob
from app.models.audit_log import AuditLog
from app.models.deposit import DepositMovement
from app.models.order import OrderStatus

pytestmark = pytest.mark.anyio


async def prepare(env):
    rid, req, create = env
    source = await create(table=rid)
    target = await create(table=rid+1)
    async with AsyncSessionLocal() as db:
        a, b = await db.get(Order, source['id']), await db.get(Order, target['id'])
        a.service_fee_percent = 10; a.waiter_share_percent = 3
        b.service_fee_percent = 20; b.waiter_share_percent = 5; b.waiter_id = rid
        b.service_fee_amount = 2000; b.total = 12000
        item = await db.get(OrderItem, source['items'][0]['id'])
        item.sent_quantity = 1; item.sent_to_kitchen = True; item.prepared_quantity = 1
        a.status = OrderStatus.READY
        (await db.get(Table, rid)).deposit_amount = 1000
        (await db.get(Table, rid+1)).deposit_amount = 2000
        await db.commit()
    preview = await req('GET', f'/tables/{rid}/merge-preview/{rid+1}')
    assert preview.status_code == 200, preview.text
    data = preview.json()
    body = {field: data[field] for field in ('source_order_id','target_order_id','source_version','target_version')}
    return rid, req, source, target, data, body


@pytest.mark.parametrize('role', ['waiter', 'admin', 'cashier'])
async def test_merge_preserves_lines_deposit_and_target_rates_with_same_key_retry(env, role):
    rid, req, source, target, preview, body = await prepare(env)
    assert preview['total'] == 24000 and preview['amount_due'] == 21000
    path = f'/tables/{rid}/merge/{rid+1}'
    responses = await asyncio.gather(*[req('POST', path, body, role=role, key='merge-once') for _ in range(3)])
    assert all(response.status_code == 200 for response in responses), [r.text for r in responses]
    result = responses[0].json()['order']
    assert result['waiter_id'] == rid and result['total'] == 24000
    assert result['waiter_share_amount'] == 1000
    assert result['advance_amount'] == 3000
    assert {item['id'] for item in result['items']} == {source['items'][0]['id'], target['items'][0]['id']}
    sent = next(item for item in result['items'] if item['id'] == source['items'][0]['id'])
    assert sent['sent_quantity'] == 1 and sent['prepared_quantity'] == 1
    old = (await req('GET', f"/orders/{source['id']}")).json()
    assert old['merged_into_order_id'] == target['id'] and old['total'] == 0 and old['items'] == []
    async with AsyncSessionLocal() as db:
        assert (await db.get(Table, rid)).status.value == 'available'
        assert (await db.get(Table, rid)).deposit_amount == 0
        assert (await db.get(Table, rid+1)).deposit_amount == 3000
        log = await db.scalar(select(AuditLog).where(AuditLog.action == 'table_accounts_merged'))
        assert log.details['before'][0]['total'] == 11000
        assert len(log.details['moved_item_ids']) == 1
        assert await db.scalar(select(func.count(AuditLog.id)).where(AuditLog.action == 'table_accounts_merged')) == 1
        assert await db.scalar(select(func.count(PrintJob.id))) == 0
        assert await db.scalar(select(func.sum(DepositMovement.cash_amount))) == 0


async def test_stale_preview_rejects_without_moving_money_or_items(env):
    rid, req, source, target, preview, body = await prepare(env)
    response = await req('PATCH', f"/orders/{target['id']}/items/{target['items'][0]['id']}/delta", {'delta':1})
    assert response.status_code == 200
    response = await req('POST', f'/tables/{rid}/merge/{rid+1}', body, key='stale')
    assert response.status_code == 409, response.text
    assert len((await req('GET', f'/orders/table/{rid}/active')).json()) == 1
    async with AsyncSessionLocal() as db:
        assert (await db.get(Table, rid)).deposit_amount == 1000
        assert (await db.get(OrderItem, source['items'][0]['id'])).order_id == source['id']


async def test_merge_rejects_same_table_empty_target_and_chef(env):
    rid, req, source, target, preview, body = await prepare(env)
    assert (await req('GET', f'/tables/{rid}/merge-preview/{rid}')).status_code == 400
    assert (await req('GET', f'/tables/{rid}/merge-preview/{rid+2}')).status_code == 409
    assert (await req('POST', f'/tables/{rid}/merge/{rid+1}', body, role='chef')).status_code == 403


async def test_merge_rolls_back_if_audit_cannot_be_written(env, monkeypatch):
    rid, req, source, target, preview, body = await prepare(env)
    async def missing(*args, **kwargs): return None
    monkeypatch.setattr('app.core.table_merge.log_audit_event', missing)
    assert (await req('POST', f'/tables/{rid}/merge/{rid+1}', body, key='audit-failure')).status_code == 500
    async with AsyncSessionLocal() as db:
        assert (await db.get(OrderItem, source['items'][0]['id'])).order_id == source['id']
        assert (await db.get(Table, rid)).deposit_amount == 1000


async def test_opposite_merges_cannot_create_a_cycle_or_move_lines_twice(env):
    rid, req, source, target, preview, body = await prepare(env)
    inverse = dict(source_order_id=body['target_order_id'], target_order_id=body['source_order_id'],
        source_version=body['target_version'], target_version=body['source_version'])
    results = await asyncio.gather(req('POST', f'/tables/{rid}/merge/{rid+1}', body, key='forward'),
        req('POST', f'/tables/{rid+1}/merge/{rid}', inverse, key='backward'))
    assert sorted(response.status_code for response in results) == [200, 409]
    async with AsyncSessionLocal() as db:
        assert await db.scalar(select(func.count(OrderItem.id)).where(OrderItem.order_id.in_([source['id'], target['id']]))) == 2
        assert await db.scalar(select(func.count(AuditLog.id)).where(AuditLog.action == 'table_accounts_merged')) == 1


async def test_merged_account_checkout_applies_deposit_once_and_only_unsent_lines_print(env):
    rid, req, source, target, preview, body = await prepare(env)
    assert (await req('POST', f'/tables/{rid}/merge/{rid+1}', body, key='merge-pay')).status_code == 200
    sent = await req('POST', f"/orders/{target['id']}/send-to-kitchen", {}, key='merged-kitchen')
    assert sent.status_code == 200, sent.text
    current = (await req('GET', f"/orders/{target['id']}")).json()
    assert all(item['sent_quantity'] == 1 for item in current['items'])
    paid = await req('POST', f"/orders/{target['id']}/checkout", {'payment_method':'cash', 'print_receipt':False}, key='pay-merged')
    assert paid.status_code == 200, paid.text
    current = (await req('GET', f"/orders/{target['id']}")).json()
    assert current['cash_amount'] == 21000 and current['advance_amount'] == 3000 and current['is_paid']
    async with AsyncSessionLocal() as db:
        assert (await db.get(Table, rid+1)).deposit_amount == 0
        assert await db.scalar(select(func.count(DepositMovement.id)).where(DepositMovement.kind == 'applied')) == 1
