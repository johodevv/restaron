"""Business invariants reproduced by the 2026-10-23 re-audit, on isolated DBs."""
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import patch
import pytest
from sqlalchemy import select, func
from test_audit_regressions import env
from app.core.database import AsyncSessionLocal
from app.models import Order, PrintJob, Notification, Review, ReceiptArchive, MenuItem
from app.models.debt import Debt
from app.models.notification import NotificationType, NotificationTarget

pytestmark = pytest.mark.anyio


async def test_paid_deliver_keeps_money_and_kitchen(env):
    rid, req, create = env
    order = await create()
    result = await req('POST', f"/orders/{order['id']}/checkout", {'print_receipt':False}, key='pay')
    assert result.status_code == 200, result.text
    before = (await req('GET',f'/receipts/shift-report/current?restaurant_id={rid}')).json()
    assert (await req('PATCH',f"/orders/{order['id']}/deliver",{},'waiter')).status_code == 409
    after = (await req('GET',f'/receipts/shift-report/current?restaurant_id={rid}')).json()
    assert {k:v for k,v in after.items() if k != 'current_time'} == {k:v for k,v in before.items() if k != 'current_time'}
    kds = (await req('GET','/kitchen/orders',role='chef')).json()
    assert [o['id'] for o in kds] == [order['id']]
    assert (await req('PATCH', f"/orders/{order['id']}/items/{order['items'][0]['id']}/prepared",{},'chef')).status_code == 200
    assert (await req('GET','/kitchen/orders',role='chef')).json() == []
    ready = (await req('GET',f'/orders/?restaurant_id={rid}&ready_for_delivery=true',role='waiter')).json()
    assert [o['id'] for o in ready] == [order['id']]
    assert (await req('PATCH',f"/orders/{order['id']}/deliver",{},'waiter')).status_code == 200
    assert (await req('GET',f'/orders/?restaurant_id={rid}&ready_for_delivery=true',role='waiter')).json() == []
    paid = (await req('GET', f"/orders/{order['id']}")).json()
    assert paid['status'] == 'paid' and paid['cash_amount'] == 11000
    final = (await req('GET',f'/receipts/shift-report/current?restaurant_id={rid}')).json()
    assert final['total_cash'] == before['total_cash'] and final['total_sales'] == before['total_sales']
    async with AsyncSessionLocal() as db:
        assert await db.scalar(select(func.count(PrintJob.id))) == 1


async def test_checkout_kitchen_atomic_failure_retry(env):
    rid, req, create = env
    o = await create()
    await req('PATCH', f'/restaurants/{rid}/settings', {'printer_kitchen1_name':''})
    path = f"/orders/{o['id']}/checkout"
    assert (await req('POST',path,{'print_receipt':False},key='atomic-pay')).status_code == 400
    current = (await req('GET',f"/orders/{o['id']}")).json()
    assert not current['is_paid'] and current['items'][0]['sent_quantity'] == 0
    await req('PATCH',f'/restaurants/{rid}/settings',{'printer_kitchen1_name':'TEST'})
    replies = await asyncio.gather(*(req('POST',path,{'print_receipt':False},key='atomic-pay') for _ in range(5)))
    assert all(r.status_code == 200 for r in replies), [r.text for r in replies]
    async with AsyncSessionLocal() as db:
        assert await db.scalar(select(func.count(PrintJob.id))) == 1
        assert await db.scalar(select(func.count(ReceiptArchive.id)).where(ReceiptArchive.receipt_type=='final_bill')) == 1


async def test_stoplist_cannot_be_bypassed_and_sent_size_is_locked(env):
    rid, req, create = env
    o = await create()
    path = f"/orders/{o['id']}/items/{o['items'][0]['id']}"
    assert (await req('POST',f"/orders/{o['id']}/send-to-kitchen",{})).status_code == 200
    assert (await req('PATCH',path+'/size',{'portion_size':'9 kg'})).status_code == 409
    async with AsyncSessionLocal() as db:
        item = await db.get(MenuItem,rid)
        item.is_stop_list = True
        await db.commit()
    assert (await req('PATCH',path+'/delta',{'delta':1})).status_code == 400
    assert (await req('PATCH',path+'/quantity',{'quantity':2})).status_code == 400


async def test_invalid_menu_prices_cannot_break_totals(env):
    rid,req,_=env
    for value in (-1,0,None):
        assert (await req('PATCH',f'/menu/items/{rid}',{'price':value})).status_code == 422


async def test_table_mutations_protect_open_accounts(env):
    rid, req, create = env
    await create()
    for body in ({'status':'available'},{'status':'reserved'},{'is_active':False}):
        r = await req('PATCH',f'/tables/{rid}',body)
        assert r.status_code == 409, r.text
    for body in ({'capacity':-1},{'number':0},{'capacity':None},{'status':None}):
        assert (await req('PATCH',f'/tables/{rid}',body)).status_code == 422


async def test_debt_identity_links_and_repayment_history(env):
    rid, req, create = env
    o = await create()
    path = f"/orders/{o['id']}/checkout"
    assert (await req('POST',path,{'payment_method':'debt'})).status_code == 400
    body = {'restaurant_id':rid,'order_id':o['id'],'customer_name':'Audit customer','customer_phone':'998901234567','amount':1000}
    assert (await req('POST','/debts/',body)).status_code == 409
    body['order_id'] = 9999999
    assert (await req('POST','/debts/',body)).status_code == 404
    body.pop('order_id')
    debt = (await req('POST','/debts/',body)).json()
    assert (await req('PATCH',f"/debts/{debt['id']}/pay",{'payment_amount':100})).status_code == 200
    assert (await req('DELETE',f"/debts/{debt['id']}")).status_code == 409
    r = await req('POST',path,{'payment_method':'debt','debt_customer_name':'Audit customer','debt_customer_phone':'998901234567','print_receipt':False})
    assert r.status_code == 200, r.text
    async with AsyncSessionLocal() as db:
        linked = await db.scalar(select(Debt).where(Debt.order_id==o['id']))
        assert linked.amount == linked.remaining_amount == 11000


async def test_mismatched_legacy_debt_blocks_checkout(env):
    rid,req,create = env
    o = await create()
    async with AsyncSessionLocal() as db:
        db.add(Debt(restaurant_id=rid,order_id=o['id'],customer_name='Audit customer',customer_phone='998901234567',amount=1000,remaining_amount=1000))
        await db.commit()
    r = await req('POST',f"/orders/{o['id']}/checkout",{'payment_method':'debt'})
    assert r.status_code == 409
    assert not (await req('GET',f"/orders/{o['id']}")).json()['is_paid']


async def test_call_resolution_is_table_scoped(env):
    rid,req,_ = env
    ids = []
    async with AsyncSessionLocal() as db:
        for offset in (0,1):
            n = Notification(restaurant_id=rid,type=NotificationType.CALL_WAITER,target=NotificationTarget.WAITER,
                title='Test call',message='Test',data={'table_id':rid+offset,'table_number':offset+1})
            db.add(n)
            await db.flush()
            ids.append(n.id)
        await db.commit()
    assert (await req('POST',f'/orders/calls/{ids[0]}/resolve',{},'waiter')).status_code == 200
    async with AsyncSessionLocal() as db:
        assert (await db.get(Notification,ids[0])).is_read
        assert not (await db.get(Notification,ids[1])).is_read
    assert (await req('POST',f'/orders/calls/{ids[0]}/resolve',{},'waiter')).status_code==200
    async with AsyncSessionLocal() as db:
        assert not (await db.get(Notification,ids[1])).is_read


async def test_notification_cleanup_cannot_cross_restaurants(env):
    rid,req,_ = env
    async with AsyncSessionLocal() as db:
        n = Notification(restaurant_id=rid+1,type=NotificationType.CALL_WAITER,target=NotificationTarget.ADMIN,
            title='Foreign',message='Test',is_read=True,created_at=datetime.now(timezone.utc)-timedelta(days=10))
        db.add(n); await db.commit(); identity=n.id
    with patch('app.routers.notifications.random.random',return_value=0):
        assert (await req('GET',f'/notifications/?restaurant_id={rid+1}')).status_code == 404
    assert (await req('DELETE',f'/notifications/cleanup?restaurant_id={rid+1}')).status_code == 404
    assert (await req('DELETE',f'/notifications/cleanup?restaurant_id={rid}')).status_code == 200
    async with AsyncSessionLocal() as db:
        assert await db.get(Notification,identity) is not None


async def test_reviews_require_owned_order_qr_and_enabled_setting(env):
    rid,req,create = env
    o = await create()
    body={'restaurant_id':rid,'order_id':o['id'],'food_rating':5}
    assert (await req('POST','/reviews/',body,role=None)).status_code == 403

    body['qr_token']=f'qr-{rid}'
    body['menu_item_id']=rid+1
    assert (await req('POST','/reviews/',body,role=None)).status_code == 404
    body['menu_item_id']=rid
    assert (await req('POST','/reviews/',body,role=None)).status_code == 201
    assert (await req('POST','/reviews/',body,role=None)).status_code == 409
    await req('PATCH',f'/restaurants/{rid}/settings',{'allow_reviews':False})
    body.pop('menu_item_id')
    assert (await req('POST','/reviews/',body,role=None)).status_code == 403


async def test_waiter_statistics_do_not_multiply_orders_by_reviews(env):
    rid,req,create = env
    for tid in (rid,rid+1):
        o=await create(table=tid)
        assert (await req('PATCH',f"/orders/{o['id']}/deliver",{},'waiter')).status_code == 200
    async with AsyncSessionLocal() as db:
        for _ in range(3):
            db.add(Review(restaurant_id=rid,waiter_id=rid+1,service_rating=5))
        await db.commit()
    stats=(await req('GET',f'/stats/waiter-performance?restaurant_id={rid}')).json()
    assert stats[0]['orders_served']==2 and stats[0]['total_revenue']==22000


async def test_pdf_fallback_preserves_advance_discount_and_identity(env,tmp_path):
    rid,req,_=env
    await req('PATCH',f'/restaurants/{rid}/settings',{'receipt_header':'Audit Choyxona'})
    async with AsyncSessionLocal() as db:
        r=ReceiptArchive(restaurant_id=rid,receipt_number='PDF-AUDIT',receipt_type='final_bill',
            subtotal=20000,service_fee_amount=2000,total_amount=21000,advance_amount=5000,cash_amount=16000)
        db.add(r);await db.commit();identity=r.id
    saved=[]
    output=tmp_path/'audit.pdf';output.write_bytes(b'%PDF-1.4 test')
    def generate(data): saved.append(data);return str(output)
    with patch('app.core.pdf_generator.generate_checkout_receipt_pdf_sync',side_effect=generate):
        r=await req('GET',f'/receipts/{identity}/pdf')
    assert r.status_code==200
    assert saved[0]['restaurant_name']=='Audit Choyxona'
    assert saved[0]['advance_amount']==5000 and saved[0]['discount']==1000 and saved[0]['amount_due']==16000


async def test_healthy_printer_is_not_hidden_behind_other_printer_backlog(env,monkeypatch):
    rid,_,_=env
    import app.core.printer_queue as queue
    import app.core.printer_service as printer
    healthy=asyncio.Event();release=asyncio.Event()
    async def fake_print(**kwargs):
        if kwargs['printer_name']=='SLOW':await release.wait()
        else:healthy.set()
        return {'success':True}
    monkeypatch.setattr(printer,'async_print_to_windows_printer',fake_print)
    async with AsyncSessionLocal() as db:
        for _ in range(100):
            await queue.enqueue_print_job(db,restaurant_id=rid,printer_name='SLOW',raw_text='test')
        await queue.enqueue_print_job(db,restaurant_id=rid,printer_name='HEALTHY',raw_text='test')
        await db.commit()
    queue.start_printer_worker();queue.wake_printer_worker()
    try:await asyncio.wait_for(healthy.wait(),3)
    finally:
        release.set()
        await queue.stop_printer_worker()


def test_money_decimal_rounding():
    from app.core.money import money, money_sum, percent
    assert money(1.005)==1.01
    assert percent(10.05,10)==1.01
    assert money_sum([.1,.2])==.3


async def test_data_health_reports_legacy_anomaly_without_rewriting_it(env):
    from pathlib import Path
    from app.core.database import engine
    from tools.check_data_health import check_data_health
    rid,_,create=env
    o=await create()
    assert check_data_health(engine.url.database)['healthy']
    async with AsyncSessionLocal() as db:
        order=await db.get(Order,o['id']);order.subtotal=999999
        await db.commit()
    path=Path(engine.url.database);before=path.read_bytes()
    result=check_data_health(path)
    assert not result['healthy'] and result['inconsistent_accounts'][0]['id']==o['id']
    assert before==path.read_bytes()


async def test_confirmed_test_repair_keeps_rows_backup_and_audit(env,tmp_path):
    from tools.repair_confirmed_test_orders import repair
    from tools.check_data_health import check_data_health
    from app.core.database import engine
    rid,req,create=env
    o=await create()
    async with AsyncSessionLocal() as db:
        order=await db.get(Order,o['id']);order.subtotal=999999
        await db.commit()
    preview=repair(engine.url.database,[o['id']],tmp_path)
    assert preview['dry_run'] and not preview['delete_rows']
    result=repair(engine.url.database,[o['id']],tmp_path,apply=True)
    assert result['rows_deleted']==0
    assert check_data_health(engine.url.database)['healthy']
    async with AsyncSessionLocal() as db:
        order=await db.get(Order,o['id'])
        assert order.status.value=='cancelled' and order.subtotal==10000
        assert await db.scalar(select(func.count(Order.id)))==1
    import sqlite3
    with sqlite3.connect(result['backup']) as original:
        assert original.execute('SELECT subtotal FROM orders').fetchone()[0]==999999
