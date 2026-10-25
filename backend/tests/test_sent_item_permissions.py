"""Sent item deletion is restricted; weighed price/weight corrections are allowed."""
import asyncio
from datetime import datetime, timezone
import pytest
from sqlalchemy import select, func
from test_audit_regressions import env
from app.core.database import AsyncSessionLocal
from app.models import OrderItem, PrintJob
from app.models.audit_log import AuditLog

pytestmark = pytest.mark.anyio


@pytest.mark.parametrize('role', ['waiter', 'cashier'])
@pytest.mark.parametrize('operation', ['delete', 'delta_delete', 'delta_reduce', 'quantity', 'cancel'])
async def test_sent_bill_cannot_be_reduced(env, role, operation):
    rid, req, create = env
    order = await create([{'menu_item_id': rid, 'quantity': 2}])
    oid = order['id']; iid = order['items'][0]['id']; path = f'/orders/{oid}/items/{iid}'
    assert (await req('POST', f'/orders/{oid}/send-to-kitchen', {})).status_code == 200
    before = (await req('GET', f'/orders/{oid}')).json()
    async with AsyncSessionLocal() as db:
        jobs = await db.scalar(select(func.count(PrintJob.id)).where(PrintJob.order_id == oid))
    if operation == 'delete': response = await req('DELETE', path, role=role)
    elif operation == 'cancel': response = await req('PATCH', f'/orders/{oid}/status', {'status': 'cancelled', 'note': 'Test cancellation'}, role)
    elif operation == 'quantity': response = await req('PATCH', path+'/quantity', {'quantity': 1}, role)
    else: response = await req('PATCH', path+'/delta', {'delta': -2 if operation == 'delta_delete' else -1}, role)
    assert response.status_code == 403, response.text
    after = (await req('GET', f'/orders/{oid}')).json()
    for key in ('items', 'subtotal', 'total', 'status', 'is_paid', 'version'):
        assert after[key] == before[key], key
    async with AsyncSessionLocal() as db:
        assert await db.scalar(select(func.count(PrintJob.id)).where(PrintJob.order_id == oid)) == jobs


@pytest.mark.parametrize('marker', ['counter_only', 'flag_only', 'timestamp_only', 'prepared_only'])
async def test_legacy_sent_markers_cannot_bypass_permission(env, marker):
    rid, req, create = env
    order = await create([{'menu_item_id': rid, 'quantity': 2}])
    oid = order['id']; iid = order['items'][0]['id']; path = f'/orders/{oid}/items/{iid}'
    async with AsyncSessionLocal() as db:
        item = await db.get(OrderItem, iid)
        item.sent_quantity = 2 if marker == 'counter_only' else 0
        item.sent_to_kitchen = marker == 'flag_only'
        item.sent_to_kitchen_at = datetime.now(timezone.utc) if marker == 'timestamp_only' else None
        item.prepared_quantity = 2 if marker == 'prepared_only' else 0
        await db.commit()
    assert (await req('DELETE', path, role='waiter')).status_code == 403
    assert (await req('PATCH', path+'/quantity', {'quantity': 1}, 'waiter')).status_code == 403
    assert (await req('PATCH', path+'/delta', {'delta': -2}, 'waiter')).status_code == 403


async def test_waiter_can_remove_only_unsent_additions(env):
    rid, req, create = env
    order = await create([{'menu_item_id': rid, 'quantity': 2}]); oid = order['id']; iid = order['items'][0]['id']
    assert (await req('POST', f'/orders/{oid}/send-to-kitchen', {})).status_code == 200
    assert (await req('POST', f'/orders/{oid}/add-items', {'items': [{'menu_item_id': rid, 'quantity': 1}, {'menu_item_id': rid+3, 'quantity': 1}]}, 'waiter')).status_code == 200
    reduced = await req('PATCH', f'/orders/{oid}/items/{iid}/delta', {'delta': -1}, 'waiter')
    assert reduced.status_code == 200, reduced.text
    sent = next(item for item in reduced.json()['items'] if item['id'] == iid)
    assert sent['quantity'] == sent['sent_quantity'] == 2
    assert (await req('PATCH', f'/orders/{oid}/items/{iid}/delta', {'delta': -1}, 'waiter')).status_code == 403
    fresh = next(item for item in reduced.json()['items'] if item['id'] != iid)
    assert (await req('DELETE', f"/orders/{oid}/items/{fresh['id']}", role='waiter')).status_code == 200


@pytest.mark.parametrize('operation,action', [('delete','delete_kitchen_item'), ('delta','cancel_kitchen_item_qty'), ('quantity','cancel_kitchen_item_qty'), ('cancel','order_cancelled'), ('bill','remove_kitchen_bill_item'), ('price','edit_kitchen_item_price')])
async def test_admin_can_correct_sent_bill_with_audit(env, operation, action):
    rid, req, create = env
    order = await create([{'menu_item_id': rid+2 if operation == 'price' else rid, 'quantity': 2, **({'weight': 1} if operation == 'price' else {})}])
    oid = order['id']; iid = order['items'][0]['id']; path = f'/orders/{oid}/items/{iid}'
    assert (await req('POST', f'/orders/{oid}/send-to-kitchen', {})).status_code == 200
    if operation == 'delete': response = await req('DELETE', path)
    elif operation == 'cancel': response = await req('PATCH', f'/orders/{oid}/status', {'status':'cancelled','note':'Admin correction'})
    elif operation == 'bill': response = await req('POST', f'/tables/{rid}/remove-items', {'order_item_ids':[iid],'quantity':1})
    elif operation == 'price': response = await req('PATCH', path+'/weight', {'price':10000})
    else: response = await req('PATCH', path+'/'+operation, {'delta':-1} if operation == 'delta' else {'quantity':1})
    assert response.status_code == 200, response.text
    async with AsyncSessionLocal() as db:
        audit = await db.scalar(select(AuditLog).where(AuditLog.restaurant_id == rid, AuditLog.action == action))
        assert audit is not None and audit.user_id == rid


async def test_waiter_can_price_an_unpriced_sent_weighted_item(env):
    rid, req, create = env
    order = await create([{'menu_item_id':rid+2,'quantity':1}]); oid = order['id']; iid = order['items'][0]['id']
    assert (await req('POST', f'/orders/{oid}/send-to-kitchen', {})).status_code == 200
    priced = await req('PATCH', f'/orders/{oid}/items/{iid}/weight', {'price':75000}, 'waiter')
    assert priced.status_code == 200, priced.text
    assert priced.json()['items'][0]['total_price'] == 75000


@pytest.mark.parametrize('role', ['waiter', 'cashier'])
@pytest.mark.parametrize('quantity', [1, 2])
@pytest.mark.parametrize('field', ['price', 'weight'])
@pytest.mark.parametrize('actual_weight', [1.3, 1.8])
async def test_sent_weighed_food_can_be_corrected_in_both_directions(env, role, quantity, field, actual_weight):
    rid, req, create = env
    order = await create([{'menu_item_id':rid+2,'quantity':quantity,'weight':1.5}])
    oid = order['id']; iid = order['items'][0]['id']; path = f'/orders/{oid}/items/{iid}'
    assert (await req('POST', f'/orders/{oid}/send-to-kitchen', {})).status_code == 200
    expected_price = 50000 * quantity * actual_weight
    payload = {'price':expected_price} if field == 'price' else {'weight':actual_weight}
    result = await req('PATCH', path+'/weight', payload, role)
    assert result.status_code == 200, result.text
    data = result.json(); item = data['items'][0]
    assert item['weight'] == actual_weight
    assert item['total_price'] == expected_price
    assert item['quantity'] == item['sent_quantity'] == quantity
    assert data['subtotal'] == expected_price and data['total'] == round(expected_price * 1.1, 2)
    assert (await req('DELETE', path, role=role)).status_code == 403
    assert (await req('PATCH', path+'/delta', {'delta':-1}, role)).status_code == 403
    async with AsyncSessionLocal() as db:
        audit = await db.scalar(select(AuditLog).where(AuditLog.restaurant_id==rid, AuditLog.action=='edit_kitchen_item_price'))
        assert audit is not None and audit.user_id == rid + (1 if role=='waiter' else 2)
        assert audit.details['new_weight'] == actual_weight and audit.details['input'] == field


async def test_price_is_authoritative_if_old_client_sends_stale_weight(env):
    rid, req, create = env
    order = await create([{'menu_item_id':rid+2,'quantity':2,'weight':1.5}])
    oid = order['id']; iid = order['items'][0]['id']
    result = await req('PATCH', f'/orders/{oid}/items/{iid}/weight', {'price':130000,'weight':1.5}, 'waiter')
    assert result.status_code == 200, result.text
    assert result.json()['items'][0]['weight'] == 1.3
    assert result.json()['items'][0]['total_price'] == 130000


async def test_paid_weighed_bill_stays_immutable(env):
    rid, req, create = env
    order = await create([{'menu_item_id':rid+2,'quantity':1,'weight':1.5}]); oid = order['id']; iid = order['items'][0]['id']
    assert (await req('POST', f'/orders/{oid}/checkout', {'print_receipt':False})).status_code == 200
    before = (await req('GET',f'/orders/{oid}')).json()
    result = await req('PATCH', f'/orders/{oid}/items/{iid}/weight', {'weight':1.3}, 'waiter')
    assert result.status_code == 400
    after = (await req('GET',f'/orders/{oid}')).json()
    assert after['items'] == before['items'] and after['total'] == before['total']


async def test_concurrent_send_and_delete_cannot_erase_sent_food(env):
    rid, req, create = env
    order = await create(); oid = order['id']; iid = order['items'][0]['id']
    sent, deleted = await asyncio.gather(req('POST', f'/orders/{oid}/send-to-kitchen', {}), req('DELETE', f'/orders/{oid}/items/{iid}', role='waiter'))
    if sent.status_code == 200 and sent.json().get('items_count', 0):
        assert deleted.status_code == 403
        assert len((await req('GET', f'/orders/{oid}')).json()['items']) == 1
    else:
        assert deleted.status_code == 200 and sent.status_code in (200, 409)
