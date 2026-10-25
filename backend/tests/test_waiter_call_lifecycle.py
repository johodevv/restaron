"""Refresh persistence, legacy calls and concurrent acknowledgements on isolated DBs."""
import asyncio
from unittest.mock import patch

import pytest
from sqlalchemy import select, func

from test_audit_regressions import env
from app.core.database import AsyncSessionLocal
from app.models import Order, Notification
from app.models.order import CallStatus
from app.models.notification import NotificationType, NotificationTarget

pytestmark = pytest.mark.anyio


async def seed_call(rid, table_id, order_id=None, *, read=False):
    async with AsyncSessionLocal() as db:
        notification = Notification(restaurant_id=rid, type=NotificationType.CALL_WAITER,
            target=NotificationTarget.WAITER, title='Test call', message='Help',
            is_read=read, data={'table_id':table_id, 'table_number':1, 'order_id':order_id})
        db.add(notification)
        if order_id:
            order = await db.get(Order, order_id)
            order.call_waiter = True
            order.call_status = CallStatus.PENDING
        await db.commit()
        return notification.id


@pytest.mark.parametrize('legacy_id', [False, True])
async def test_table61_read_notification_pending_order_survives_refresh_fix(env, legacy_id):
    rid, req, create = env
    order = await create()
    await seed_call(rid, rid, order['id'], read=True)
    calls = (await req('GET',f'/orders/calls?restaurant_id={rid}',role='waiter')).json()
    assert len(calls) == 1
    identity = 100000 + order['id'] if legacy_id else calls[0]['id']
    replies = await asyncio.gather(*(req('POST',f'/orders/calls/{identity}/resolve',{},'waiter') for _ in range(8)))
    assert all(r.status_code == 200 for r in replies), [r.text for r in replies]
    # Independent GET requests reproduce page reloads, not optimistic local UI state.
    for _ in range(3):
        assert (await req('GET',f'/orders/calls?restaurant_id={rid}',role='waiter')).json() == []
    async with AsyncSessionLocal() as db:
        persisted = await db.get(Order,order['id'])
        assert not persisted.call_waiter and persisted.call_status == CallStatus.COMPLETED
        assert persisted.subtotal == order['subtotal'] and len(persisted.order_number) > 0


async def test_duplicate_calls_collapse_and_legacy_completion_clears_both_stores(env):
    rid,req,create = env
    order = await create()
    ids = [await seed_call(rid,rid,order['id']) for _ in range(3)]
    other_id = await seed_call(rid,rid+1)
    calls = (await req('GET',f'/orders/calls?restaurant_id={rid}',role='waiter')).json()
    assert sorted(c['table_id'] for c in calls) == [rid,rid+1]
    with patch('app.routers.orders.manager.broadcast_to_roles') as broadcast:
        result = await req('PATCH',f"/orders/{order['id']}/call/complete",{},'waiter')
        assert result.status_code == 200, result.text
        assert sorted(broadcast.call_args.args[2]['resolved_call_ids']) == ids
    assert [c['table_id'] for c in (await req('GET',f'/orders/calls?restaurant_id={rid}',role='waiter')).json()] == [rid+1]
    async with AsyncSessionLocal() as db:
        assert all([(await db.get(Notification,i)).is_read for i in ids])
        assert not (await db.get(Notification,other_id)).is_read


async def test_orderless_call_retries_do_not_duplicate_and_can_be_called_again(env):
    rid,req,_ = env
    body = {'table_id':rid,'qr_token':f'qr-{rid}'}
    # Bypass only rate limiting to exercise DB deduplication (including parallel requests).
    with patch('app.core.rate_limit.rate_limiter_storage.is_rate_limited',return_value=(False,0)):
        replies = await asyncio.gather(*(req('POST','/orders/call-waiter',body,role=None) for _ in range(6)))
        assert all(r.status_code == 200 for r in replies), [r.text for r in replies]
        first_ids = {r.json()['call_id'] for r in replies}
        assert len(first_ids) == 1
        first_id = first_ids.pop()
        assert (await req('POST',f'/orders/calls/{first_id}/resolve',{},'waiter')).status_code == 200
        new = await req('POST','/orders/call-waiter',body,role=None)
        assert new.status_code == 200 and new.json()['call_id'] != first_id
        assert (await req('POST',f'/orders/calls/{first_id}/resolve',{},'waiter')).json()['already_resolved']
    calls = (await req('GET',f'/orders/calls?restaurant_id={rid}',role='waiter')).json()
    assert len(calls) == 1 and calls[0]['id'] == new.json()['call_id']
    async with AsyncSessionLocal() as db:
        assert await db.scalar(select(func.count(Notification.id))) == 2


async def test_stale_fallback_cannot_accept_a_new_notification(env):
    rid,req,create = env
    order = await create()
    old_id = await seed_call(rid,rid,order['id'],read=True)
    newer_id = await seed_call(rid,rid,order['id'])
    assert (await req('POST',f"/orders/calls/{-order['id']}/resolve",{},'waiter')).status_code == 409
    assert (await req('POST',f'/orders/calls/{old_id}/resolve',{},'waiter')).json()['already_resolved']
    calls = (await req('GET',f'/orders/calls?restaurant_id={rid}',role='waiter')).json()
    assert len(calls) == 1 and calls[0]['id'] == newer_id
    replies = await asyncio.gather(*(req('POST',f'/orders/calls/{newer_id}/resolve',{},'waiter') for _ in range(10)))
    assert all(r.status_code == 200 for r in replies), [r.text for r in replies]
    assert (await req('GET',f'/orders/calls?restaurant_id={rid}',role='waiter')).json() == []


async def test_foreign_calls_and_missing_ids_do_not_acknowledge_local_calls(env):
    rid,req,_ = env
    local = await seed_call(rid,rid)
    foreign = await seed_call(rid+1,rid+1)
    for identity in (foreign, -999999, 999999):
        assert (await req('POST',f'/orders/calls/{identity}/resolve',{},'waiter')).status_code == 404
    calls = (await req('GET',f'/orders/calls?restaurant_id={rid}',role='waiter')).json()
    assert len(calls) == 1 and calls[0]['id'] == local


async def test_high_order_id_cannot_resolve_a_notification_with_same_positive_id(env):
    rid,req,create = env
    order = await create()
    async with AsyncSessionLocal() as db:
        o = await db.get(Order,order['id'])
        o.id = 100005
        o.call_waiter = True
        o.call_status = CallStatus.PENDING
        # Order items FK must move together before changing the order PK.
        from app.models.order import OrderItem
        # Defer FK validation until transaction commit for this synthetic fixture.
        from sqlalchemy import text, update
        await db.execute(text('PRAGMA defer_foreign_keys=ON'))
        await db.execute(update(OrderItem).where(OrderItem.order_id==order['id']).values(order_id=100005))
        db.add(Notification(id=100005,restaurant_id=rid,type=NotificationType.CALL_WAITER,
            target=NotificationTarget.WAITER,title='Other table',message='Help',
            data={'table_id':rid+1,'table_number':2}))
        await db.commit()
    calls = (await req('GET',f'/orders/calls?restaurant_id={rid}',role='waiter')).json()
    assert {c['id'] for c in calls} == {-100005,100005}
    assert (await req('POST','/orders/calls/-100005/resolve',{},'waiter')).status_code == 200
    calls = (await req('GET',f'/orders/calls?restaurant_id={rid}',role='waiter')).json()
    assert [c['id'] for c in calls] == [100005]
