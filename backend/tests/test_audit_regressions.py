"""Reproductions for the restaurant audit. Every fixture has its own tenant."""
import asyncio
import itertools
from unittest.mock import AsyncMock, patch
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select, func
from app.main import app
from app.core.database import AsyncSessionLocal, engine, Base
from app.core.security import create_access_token
from app.models import Restaurant, RestaurantSettings, User, Table, Category, MenuItem, Order, PrintJob, ReceiptArchive
from app.models.debt import Debt, DebtPaymentRecord
from app.models.deposit import DepositMovement

pytestmark = pytest.mark.anyio
_ids = itertools.count(20000, 10)


@pytest.fixture
async def env(monkeypatch, tmp_path):
    import app.core.pdf_generator as pdf
    monkeypatch.setattr(pdf, 'PDF_ARCHIVE_BASE', str(tmp_path))
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    rid = next(_ids)
    async with AsyncSessionLocal() as db:
        for restaurant in (rid, rid+1):
            db.add(Restaurant(id=restaurant, name='Audit regression', slug=f'regression-{restaurant}'))
            db.add(RestaurantSettings(restaurant_id=restaurant, service_fee_percent=10,
                enable_chef_kds=True, auto_print_kitchen=True, auto_print_customer_bill=True,
                printer_customer_name='TEST-USB', printer_kitchen1_name='192.0.2.10',
                printer_kitchen2_name='192.0.2.11', telegram_bot_token='private-token', sms_provider_api_key='private-key'))
            db.add(Category(id=restaurant, restaurant_id=restaurant, name='Taomlar'))
            db.add(MenuItem(id=restaurant, category_id=restaurant, name='Osh', price=10000))
        for offset, role in enumerate(('admin', 'waiter', 'cashier', 'chef')):
            db.add(User(id=rid+offset, restaurant_id=rid, username=f'audit-{rid}-{role}',
                full_name=f'Audit {role}', hashed_password='unused-test-password', role=role, is_active=True, is_approved=True))
        for offset in range(3):
            db.add(Table(id=rid+offset, restaurant_id=rid, number=offset+1, qr_token=f'qr-{rid+offset}'))
        db.add(MenuItem(id=rid+2, category_id=rid, name='Baliq', price=50000, is_weighted=True, kitchen_station='cold_kitchen'))
        db.add(MenuItem(id=rid+3, category_id=rid, name='Suv', price=5000, kitchen_station='bar'))
        await db.commit()
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://regression') as client:
        async def req(method, path, body=None, role='admin', key=None):
            headers = {} if role is None else {'Authorization': 'Bearer '+create_access_token({'sub': str(rid+('admin','waiter','cashier','chef').index(role)), 'role':role})}
            if key: headers['Idempotency-Key'] = key
            return await client.request(method, '/api/v1'+path, json=body, headers=headers)
        async def create(items=None, table=None):
            r = await req('POST', '/orders/waiter-create', {'restaurant_id':rid, 'table_id':table or rid,
                'items': items or [{'menu_item_id':rid,'quantity':1}]}, 'waiter')
            assert r.status_code == 201, r.text
            return r.json()
        yield rid, req, create


@pytest.mark.parametrize('operation', ['add-items', 'delta', 'checkout'])
async def test_parallel_retries_apply_once(env, operation):
    rid, req, create = env
    order = await create()
    path=f"/orders/{order['id']}/"
    method='POST'
    body={'items':[{'menu_item_id':rid,'quantity':1}]}
    if operation=='delta':
        path+=f"items/{order['items'][0]['id']}/delta";method='PATCH';body={'delta':1}
    elif operation=='checkout':
        path+='checkout';body={'payment_method':'cash','print_receipt':False}
    else: path+='add-items'
    responses=await asyncio.gather(*[req(method,path,body,key='same-operation') for _ in range(10)])
    assert all(r.status_code==200 for r in responses), [r.text for r in responses]
    result=(await req('GET',f"/orders/{order['id']}")).json()
    assert result['items'][0]['quantity']==(1 if operation=='checkout' else 2)
    async with AsyncSessionLocal() as db:
        if operation=='checkout':
            assert await db.scalar(select(func.count(ReceiptArchive.id)).where(ReceiptArchive.order_id==order['id'], ReceiptArchive.receipt_type=='final_bill'))==1
    if operation!='checkout':
        body = {'delta':2} if operation=='delta' else {'items':[{'menu_item_id':rid,'quantity':2}]}
        assert (await req(method,path,body,key='same-operation')).status_code==409


async def test_failed_operation_key_can_be_retried(env):
    rid, req, create=env
    o=await create()
    body={'items':[{'menu_item_id':rid,'quantity':1}], 'send_to_kitchen_immediately':True}
    await req('PATCH',f'/restaurants/{rid}/settings',{'printer_kitchen1_name':''})
    path=f"/orders/{o['id']}/add-items"
    assert (await req('POST',path,body,key='recoverable')).status_code==400
    assert (await req('GET',f"/orders/{o['id']}")).json()['items'][0]['quantity']==1
    await req('PATCH',f'/restaurants/{rid}/settings',{'printer_kitchen1_name':'192.0.2.10'})
    assert (await req('POST',path,body,key='recoverable')).status_code==200
    async with AsyncSessionLocal() as db:
        assert await db.scalar(select(func.count(PrintJob.id)).where(PrintJob.order_id==o['id']))==1


async def test_price_snapshot_weight_and_history(env):
    rid, req, create=env
    o=await create()
    await req('PATCH',f'/menu/items/{rid}',{'price':20000})
    await req('PATCH',f"/orders/{o['id']}/items/{o['items'][0]['id']}/delta",{'delta':1})
    result=(await req('GET',f"/orders/{o['id']}")).json()
    assert result['subtotal']==20000
    await req('DELETE',f'/menu/items/{rid}')
    assert len((await req('GET',f"/orders/{o['id']}")).json()['items'])==1
    assert (await req('GET',f'/menu/full/{rid}',role=None)).json()[0]['items'][0]['id']!=rid
    w=await create([{'menu_item_id':rid+2,'quantity':1}],rid+1)
    await req('PATCH',f"/orders/{w['id']}/items/{w['items'][0]['id']}/weight",{'price':100000})
    r=await req('POST',f"/orders/{w['id']}/add-items",{'items':[{'menu_item_id':rid+2,'quantity':1}]})
    assert len(r.json()['items'])==2
    assert r.json()['items'][1]['manual_price'] is None
    assert (await req('POST',f"/orders/{w['id']}/checkout",{})).status_code==400


@pytest.mark.parametrize('action', ['two-deletes', 'checkout-first', 'delete-first'])
async def test_delete_checkout_preserves_totals(env, action):
    rid, req, create=env
    o=await create([{'menu_item_id':rid,'quantity':1},{'menu_item_id':rid+3,'quantity':1}])
    delete=lambda item:req('DELETE',f"/orders/{o['id']}/items/{item['id']}")
    checkout=lambda:req('POST',f"/orders/{o['id']}/checkout",{'print_receipt':False})
    if action=='two-deletes': await asyncio.gather(*(delete(i) for i in o['items']))
    elif action=='checkout-first': await asyncio.gather(checkout(),delete(o['items'][0]))
    else: await asyncio.gather(delete(o['items'][0]),checkout())
    result=(await req('GET',f"/orders/{o['id']}")).json()
    assert result['subtotal']==sum(i['total_price'] for i in result['items'])
    if result['is_paid']: assert result['total']==result['cash_amount']
    else: assert result['status']=='cancelled' and result['subtotal']==0


async def test_advance_ledger_and_legacy_checkout(env):
    rid, req, create=env
    assert (await req('POST',f'/tables/{rid}/reserve',{'deposit_amount':5000})).status_code==200
    o=await create()
    assert o['advance_amount']==5000 and o['amount_due']==6000
    assert (await req('POST',f'/tables/{rid}/checkout',{'payment_method':'cash'})).status_code==200
    result=(await req('GET',f"/orders/{o['id']}")).json()
    assert result['cash_amount']==6000 and result['advance_amount']==5000
    async with AsyncSessionLocal() as db:
        movements=(await db.scalars(select(DepositMovement).where(DepositMovement.table_id==rid))).all()
        assert sum(m.amount for m in movements)==0
        assert sum(m.cash_amount for m in movements)==5000
        assert await db.scalar(select(func.count(ReceiptArchive.id)).where(ReceiptArchive.order_id==o['id'], ReceiptArchive.receipt_type=='final_bill'))==1
    report=(await req('GET',f'/stats/payments-report?restaurant_id={rid}')).json()
    assert report['total_cash_in_drawer']==11000
    assert report['rows'][0]['advance_amount']==5000
    shift=(await req('GET',f'/receipts/shift-report/current?restaurant_id={rid}')).json()
    assert shift['total_cash']==11000


async def test_advance_surplus_and_transfer_are_not_lost(env):
    rid, req, create=env
    await req('POST',f'/tables/{rid}/reserve',{'deposit_amount':12000})
    o=await create()
    assert (await req('POST',f"/orders/{o['id']}/checkout",{})).status_code==409
    assert (await req('POST',f'/tables/{rid}/transfer/{rid+1}')).status_code==200
    assert (await req('GET',f"/orders/{o['id']}")).json()['advance_amount']==12000
    assert (await req('POST',f'/tables/{rid+1}/clear')).status_code==409


async def test_printers_and_kds_toggle(env):
    rid, req, create=env
    o=await create([{'menu_item_id':rid,'quantity':1},{'menu_item_id':rid+2,'quantity':1},{'menu_item_id':rid+3,'quantity':1}])
    r=await req('POST',f"/orders/{o['id']}/send-to-kitchen",{})
    assert r.status_code==200
    assert {t['printer_name'] for t in r.json()['tickets']}=={'TEST-USB','192.0.2.10','192.0.2.11'}
    r=await req('GET','/kitchen/orders',role='chef')
    assert len(r.json())==1
    assert (await req('PATCH',f"/orders/{o['id']}/items/{o['items'][0]['id']}/prepared",{},'chef')).status_code==200
    await req('PATCH',f'/restaurants/{rid}/settings',{'enable_chef_kds':False})
    assert (await req('GET','/kitchen/orders',role='chef')).status_code==403
    assert (await req('PATCH',f"/orders/{o['id']}/items/{o['items'][1]['id']}/prepared",{},'chef')).status_code==403


async def test_manual_bill_uses_real_signature_and_advance(env):
    rid, req, create=env
    await req('POST',f'/tables/{rid}/reserve',{'deposit_amount':5000})
    o=await create()
    r=await req('POST',f"/orders/{o['id']}/print-bill",{})
    assert r.status_code==200, r.text
    assert r.json()['queued'] and 'АВАНС' in r.json()['raw_text']


async def test_stale_checkout_is_rejected(env):
    rid, req, create=env
    o=await create()
    await req('POST',f"/orders/{o['id']}/add-items",{'items':[{'menu_item_id':rid,'quantity':1}]})
    r=await req('POST',f"/orders/{o['id']}/checkout",{'expected_version':o['version']})
    assert r.status_code==409
    assert not (await req('GET',f"/orders/{o['id']}")).json()['is_paid']


@pytest.mark.parametrize('field,value', [('service_fee_percent',-1),('printer_paper_width',70),('printer_char_spacing',-1),('archive_retention_years',0)])
async def test_invalid_settings(env,field,value):
    rid,req,_=env
    assert (await req('PATCH',f'/restaurants/{rid}/settings',{field:value})).status_code==422


async def test_tenant_secrets_and_themes(env):
    rid,req,create=env
    o=await create()
    assert (await req('PATCH',f'/restaurants/{rid+1}/settings',{'service_fee_percent':99})).status_code==404
    assert (await req('POST',f"/orders/{o['id']}/add-items",{'items':[{'menu_item_id':rid+1,'quantity':1}]})).status_code==404
    for role in (None,'waiter','admin'):
        r=await req('GET',f'/restaurants/{rid}',role=role)
        assert 'private-token' not in r.text and 'private-key' not in r.text
    assert (await req('PATCH',f'/restaurants/{rid}/settings',{'active_themes':['fresh-green']})).status_code==200
    assert (await req('GET',f'/restaurants/{rid}',role=None)).json()['settings']['active_themes']==['fresh-green']


async def test_logout_revocation_survives_memory_reset(env):
    rid, req, _=env
    import app.core.security as security
    token=create_access_token({'sub':str(rid),'role':'admin'})
    async with AsyncClient(transport=ASGITransport(app=app),base_url='http://regression') as client:
        headers={'Authorization':'Bearer '+token}
        assert (await client.post('/api/v1/auth/logout',headers=headers)).status_code==200
        security._blacklisted_jtis.clear()
        assert (await client.get('/api/v1/auth/me',headers=headers)).status_code==401


async def test_utc_and_local_qr(env):
    rid,req,create=env
    o=await create()
    assert o['created_at'].endswith(('Z','+00:00'))
    r=await req('GET',f'/tables/qr-image/qr-{rid}?base_url=http://localhost:8017',role=None)
    assert r.status_code==200 and r.content.startswith(b'\x89PNG')


async def test_atomic_printer_claim(env):
    rid,req,create=env
    from app.core.printer_queue import _execute_print_job
    o=await create()
    r=await req('POST',f"/orders/{o['id']}/send-to-kitchen",{})
    job=r.json()['tickets'][0]['job_id']
    with patch('app.core.printer_service.async_print_to_windows_printer', new=AsyncMock(return_value={'success':True})) as printer:
        await asyncio.gather(_execute_print_job(job),_execute_print_job(job))
        assert printer.await_count==1


async def test_renamed_menu_preserves_old_lines_and_receipt(env):
    rid,req,create=env
    order=await create()
    assert (await req('PATCH',f'/menu/items/{rid}',{'name':'Yangi osh'})).status_code==200
    response=await req('POST',f"/orders/{order['id']}/add-items",{'items':[{'menu_item_id':rid,'quantity':1}]})
    assert [item['menu_item_name'] for item in response.json()['items']]==['Osh','Yangi osh']
    assert (await req('PATCH',f'/menu/items/{rid}',{'is_weighted':True})).status_code==409
    assert (await req('POST',f"/orders/{order['id']}/checkout",{'print_receipt':False})).status_code==200
    async with AsyncSessionLocal() as db:
        archive=await db.scalar(select(ReceiptArchive).where(ReceiptArchive.order_id==order['id']))
        import json
        items=json.loads(archive.items_json) if isinstance(archive.items_json,str) else archive.items_json
        assert [item['name'] for item in items]==['Osh','Yangi osh']


async def test_public_order_requires_qr_and_retries_once(env):
    rid,req,_=env
    await req('PATCH',f'/restaurants/{rid}/settings',{'allow_orders_from_qr':True})
    body={'table_id':rid,'items':[{'menu_item_id':rid,'quantity':1}]}
    assert (await req('POST','/orders/',body,role=None)).status_code==403
    body['qr_token']=f'qr-{rid}'
    responses=await asyncio.gather(*[req('POST','/orders/',body,role=None,key='public-retry') for _ in range(2)])
    assert all(r.status_code==201 for r in responses), [r.text for r in responses]
    assert len({r.json()['id'] for r in responses})==1
    order=responses[0].json()
    assert (await req('GET',f"/orders/{order['id']}")).json()['items'][0]['quantity']==1
    responses=await asyncio.gather(*[req('POST','/orders/',body,role=None,key='public-add-retry') for _ in range(2)])
    assert all(r.status_code==201 for r in responses)
    assert (await req('GET',f"/orders/{order['id']}")).json()['items'][0]['quantity']==2


async def test_uncertain_print_requires_operator_resolution(env):
    rid,req,create=env
    from app.core.printer_queue import _execute_print_job
    order=await create()
    sent=await req('POST',f"/orders/{order['id']}/send-to-kitchen",{})
    job_id=sent.json()['tickets'][0]['job_id']
    with patch('app.core.printer_service.async_print_to_windows_printer',new=AsyncMock(return_value={'success':False,'delivery_unknown':True,'error':'connection lost'})) as printer:
        await _execute_print_job(job_id)
        await _execute_print_job(job_id)
        assert printer.await_count==1
    async with AsyncSessionLocal() as db:
        assert (await db.get(PrintJob,job_id)).status=='uncertain'
    assert (await req('POST',f'/receipts/print-jobs/{job_id}/resolve?action=retry',role='waiter')).status_code==403
    assert (await req('POST',f'/receipts/print-jobs/{job_id}/resolve?action=retry')).status_code==200
    with patch('app.core.printer_service.async_print_to_windows_printer',new=AsyncMock(return_value={'success':True})) as printer:
        await _execute_print_job(job_id)
        assert printer.await_count==1
    async with AsyncSessionLocal() as db:
        job=await db.get(PrintJob,job_id)
        assert job.status=='done' and job.raw_text.startswith('*** TAKROR')


def test_websocket_tokens_are_redacted():
    import logging
    from app.core.logging import RedactTokenFilter
    record=logging.LogRecord('uvicorn.error',20,'',0,'WS /api/v1/ws/1?token=%s&table_id=1',('fake-secret',),None)
    assert RedactTokenFilter().filter(record)
    assert 'fake-secret' not in record.getMessage() and 'table_id=1' in record.getMessage()


async def test_websocket_order_datetime_does_not_disconnect():
    import json
    from datetime import datetime,timezone
    from app.websockets.manager import ConnectionManager
    class BrowserSocket:
        async def send_json(self,message):
            self.payload=json.dumps(message)
        async def close(self,**kwargs):
            raise AssertionError('A valid order event must not close the socket')
    socket=BrowserSocket()
    assert await ConnectionManager().send_personal_message({'type':'order_updated','order':{'created_at':datetime.now(timezone.utc)}},socket)
    assert 'order_updated' in socket.payload and '+00:00' in socket.payload


def test_receipt_footer_stays_visible_with_advance_and_split_tender(monkeypatch,tmp_path):
    from reportlab.pdfgen import canvas
    import app.core.pdf_generator as pdf
    real_canvas=canvas.Canvas
    drawings=[]
    class RecordingCanvas(real_canvas):
        def __init__(self,*args,**kwargs):
            super().__init__(*args,**kwargs)
            self.positions=[]
            drawings.append(self)
        def drawString(self,x,y,text,*args,**kwargs):
            self.positions.append((y,text))
            return super().drawString(x,y,text,*args,**kwargs)
        def drawRightString(self,x,y,text,*args,**kwargs):
            self.positions.append((y,text))
            return super().drawRightString(x,y,text,*args,**kwargs)
        def drawCentredString(self,x,y,text,*args,**kwargs):
            self.positions.append((y,text))
            return super().drawCentredString(x,y,text,*args,**kwargs)
    monkeypatch.setattr(canvas,'Canvas',RecordingCanvas)
    monkeypatch.setattr(pdf,'PDF_ARCHIVE_BASE',str(tmp_path))
    path=pdf.generate_checkout_receipt_pdf_sync({'order_number':'TEST-ONLY','restaurant_name':'Sinov',
        'order_type':'delivery','customer_name':'Sinov','customer_phone':'000','delivery_address':'Sinov manzili',
        'items':[{'name':'Uzoq nomli taom '*10,'quantity':1,'unit_price':50000,'total_price':0,'special_note':'Izoh '*30}],
        'subtotal':0,'total':0,'advance_amount':0,'payment_method':'mixed','cash_amount':1,'card_amount':1,
        'click_amount':1,'debt_amount':1,'receipt_note':'Sinov '*40,'footer_text':'Rahmat '*20,'wifi_pass':'sinov'})
    assert len(drawings)==2 and path.endswith('.pdf')
    final=drawings[-1]
    assert min(y for y,_ in final.positions)>=0
    assert all(y<final._pagesize[1] for y,_ in final.positions)
    assert any(text=='RestAron POS | PDF arxiv' for _,text in final.positions)
    assert any(text=="0 so'm" for _,text in final.positions)


async def test_unexplained_legacy_amount_cannot_be_silently_recalculated(env):
    rid,req,create=env
    order=await create()
    from sqlalchemy import update
    async with AsyncSessionLocal() as db:
        await db.execute(update(Order).where(Order.id==order['id']).values(subtotal=99000,total=108900))
        await db.commit()
    read=await req('GET',f"/orders/{order['id']}")
    assert read.status_code==200 and read.json()['integrity_warning']
    assert (await req('POST',f"/orders/{order['id']}/add-items",{'items':[{'menu_item_id':rid,'quantity':1}]})).status_code==409
    assert (await req('POST',f"/orders/{order['id']}/checkout",{})).status_code==409
    assert (await req('POST',f'/tables/{rid}/clear')).status_code==409
    async with AsyncSessionLocal() as db:
        original=await db.get(Order,order['id'])
        assert original.subtotal==99000 and original.total==108900 and not original.is_paid


async def test_kds_only_new_quantity_after_prepared_dozakaz(env):
    rid,req,create=env
    order=await create()
    oid=order['id'];iid=order['items'][0]['id']
    await req('POST',f'/orders/{oid}/send-to-kitchen',{})
    assert (await req('PATCH',f'/orders/{oid}/items/{iid}/prepared',{'expected_sent_quantity':1},'chef')).status_code==200
    await req('PATCH',f'/orders/{oid}/items/{iid}/delta',{'delta':2},'waiter')
    await req('POST',f'/orders/{oid}/send-to-kitchen',{})
    kitchen=(await req('GET','/kitchen/orders',role='chef')).json()
    assert kitchen[0]['status']=='preparing'
    item=kitchen[0]['items'][0]
    assert item['quantity']==3 and item['prepared_quantity']==1 and item['kitchen_pending_quantity']==2
    assert (await req('PATCH',f'/orders/{oid}/items/{iid}/prepared',{'expected_sent_quantity':1},'chef')).status_code==409
    assert (await req('PATCH',f'/orders/{oid}/items/{iid}/prepared',{'expected_sent_quantity':3},'chef')).status_code==200
    final=(await req('GET',f'/orders/{oid}')).json()
    assert final['status']=='ready' and final['items'][0]['kitchen_pending_quantity']==0


async def test_legacy_bill_remove_sends_cancellation_atomically(env):
    rid,req,create=env
    order=await create()
    oid=order['id'];iid=order['items'][0]['id']
    await req('POST',f'/orders/{oid}/send-to-kitchen',{})
    await req('PATCH',f'/restaurants/{rid}/settings',{'printer_kitchen1_name':''})
    body={'order_item_ids':[iid]}
    assert (await req('POST',f'/tables/{rid}/remove-items',body)).status_code==400
    assert (await req('GET',f'/orders/{oid}')).json()['subtotal']==10000
    await req('PATCH',f'/restaurants/{rid}/settings',{'printer_kitchen1_name':'192.0.2.10'})
    response=await req('POST',f'/tables/{rid}/remove-items',body)
    assert response.status_code==200,response.text
    final=(await req('GET',f'/orders/{oid}')).json()
    assert final['status']=='cancelled' and final['subtotal']==0 and final['items']==[]
    async with AsyncSessionLocal() as db:
        assert await db.scalar(select(func.count(PrintJob.id)).where(PrintJob.order_id==oid,PrintJob.ticket_type=='cancel'))==1


async def test_orphan_legacy_print_job_never_reaches_printer(env):
    rid,req,_=env
    import sqlite3
    from app.core.printer_queue import _execute_print_job
    # Reproduce a legacy FK violation outside the ORM on this test database only.
    with sqlite3.connect(engine.url.database) as legacy:
        cursor=legacy.execute("INSERT INTO print_jobs(restaurant_id,order_id,ticket_type,printer_name,raw_text,status,attempts,alerted) VALUES (?,999999,'kitchen','TEST-ONLY','TEST-ONLY','pending',0,0)",(rid,))
        job_id=cursor.lastrowid
    with patch('app.core.printer_service.async_print_to_windows_printer',new=AsyncMock(return_value={'success':True})) as printer:
        await _execute_print_job(job_id)
        assert printer.await_count==0
    async with AsyncSessionLocal() as db:
        assert (await db.get(PrintJob,job_id)).status=='uncertain'
    assert (await req('POST',f'/receipts/print-jobs/{job_id}/resolve?action=retry')).status_code==409
