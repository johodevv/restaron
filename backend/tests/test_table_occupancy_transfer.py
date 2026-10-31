import pytest
from sqlalchemy import select
from test_audit_regressions import env
from app.core.database import AsyncSessionLocal
from app.models import Order, OrderItem, Table
from app.models.order import OrderStatus
from app.models.table import TableStatus

pytestmark = pytest.mark.anyio


async def test_open_account_overrides_stale_available_without_rewriting_records(env):
    rid, req, create = env
    order = await create(table=rid+2)
    async with AsyncSessionLocal() as db:
        table = await db.get(Table, rid+2)
        table.status = TableStatus.AVAILABLE
        table.room = 'Xona'
        await db.commit()
    for response in [await req('GET', f'/tables/?restaurant_id={rid}'), await req('GET', f'/tables/{rid+2}')]:
        assert response.status_code == 200, response.text
        table = next(t for t in response.json() if t['id'] == rid+2) if isinstance(response.json(), list) else response.json()
        assert table['status'] == 'occupied' and table['is_occupied']
        assert table['active_order_id'] == order['id'] and table['open_orders_count'] == 1
    async with AsyncSessionLocal() as db:
        assert (await db.get(Table, rid+2)).status == TableStatus.AVAILABLE  # GET is read-only.
        assert (await db.get(Order, order['id'])).total == order['total']


async def test_stale_empty_target_cannot_overwrite_an_existing_account(env):
    rid, req, create = env
    source, target = await create(), await create(table=rid+2)
    async with AsyncSessionLocal() as db:
        (await db.get(Table, rid+2)).status = TableStatus.AVAILABLE
        await db.commit()
    response = await req('POST', f'/tables/{rid}/transfer/{rid+2}')
    assert response.status_code == 409, response.text
    for table_id, order in [(rid, source), (rid+2, target)]:
        active = (await req('GET', f'/orders/table/{table_id}/active')).json()
        assert len(active) == 1 and active[0]['id'] == order['id']
        assert active[0]['total'] == order['total']
        assert active[0]['items'][0]['id'] == order['items'][0]['id']
    preview = await req('GET', f'/tables/{rid}/merge-preview/{rid+2}')
    assert preview.status_code == 200, preview.text
    assert preview.json()['total'] == source['total'] + target['total']


@pytest.mark.parametrize('state', ['occupied', 'maintenance', 'inactive'])
async def test_unavailable_target_without_account_is_not_used(env, state):
    rid, req, create = env
    source = await create()
    async with AsyncSessionLocal() as db:
        table = await db.get(Table, rid+1)
        if state == 'inactive': table.is_active = False
        else: table.status = TableStatus(state)
        await db.commit()
    assert (await req('POST', f'/tables/{rid}/transfer/{rid+1}')).status_code == 409
    async with AsyncSessionLocal() as db:
        assert (await db.get(Order, source['id'])).table_id == rid


async def test_transfer_retains_identity_lines_amounts_and_refreshes_version(env):
    rid, req, create = env
    source = await create()
    async with AsyncSessionLocal() as db:
        line = await db.get(OrderItem, source['items'][0]['id'])
        line.sent_quantity = 1
        line.sent_to_kitchen = True
        version = (await db.get(Order, source['id'])).version
        await db.commit()
    assert (await req('POST', f'/tables/{rid}/transfer/{rid+2}')).status_code == 200
    assert (await req('GET', f'/orders/table/{rid}/active')).json() == []
    moved = (await req('GET', f'/orders/table/{rid+2}/active')).json()
    assert len(moved) == 1 and moved[0]['id'] == source['id']
    assert moved[0]['total'] == source['total'] and moved[0]['version'] > version
    assert moved[0]['items'][0]['id'] == source['items'][0]['id']
    assert moved[0]['items'][0]['sent_quantity'] == 1
    assert (await req('POST', f'/tables/{rid}/transfer/{rid+2}')).status_code == 409
    async with AsyncSessionLocal() as db:
        assert len((await db.scalars(select(OrderItem).where(OrderItem.order_id == source['id']))).all()) == 1


async def test_paid_and_cancelled_history_does_not_make_a_free_table_busy(env):
    rid, req, create = env
    order = await create()
    async with AsyncSessionLocal() as db:
        historical = await db.get(Order, order['id'])
        historical.status = OrderStatus.CANCELLED
        (await db.get(Table, rid)).status = TableStatus.AVAILABLE
        await db.commit()
    response = await req('GET', f'/tables/{rid}')
    assert response.json()['status'] == 'available'
    assert not response.json()['is_occupied'] and response.json()['open_orders_count'] == 0
