"""Receipt selection, immutable snapshots and actual ESC/POS raster round-trip.

No printer is contacted. On non-Windows test hosts only, substitute a known
test font; production never silently substitutes a missing font.
"""
import copy
from types import SimpleNamespace

import pytest
from PIL import ImageFont
from sqlalchemy import select, create_engine, text

from test_audit_regressions import env
from app.core.database import AsyncSessionLocal, _sync_schema_migrations
from app.core import receipt_styles as styles
from app.core.printer_service import build_escpos_payload, format_pre_check
from app.models import RestaurantSettings, PrintJob, ReceiptArchive

pytestmark = pytest.mark.anyio


@pytest.fixture
def available_fonts(monkeypatch):
    catalog = dict(styles.font_catalog())
    if ('arial', False) not in catalog:
        regular = ImageFont.truetype('DejaVuSans.ttf', 16).path
        bold = ImageFont.truetype('DejaVuSans-Bold.ttf', 16).path
        catalog.update({('arial', False): regular, ('arial', True): bold})
    catalog = {k: v for k, v in catalog.items() if k[0] != 'mercury'}
    monkeypatch.setattr(styles, 'font_catalog', lambda: catalog)
    styles._font.cache_clear()
    yield
    styles._font.cache_clear()


@pytest.mark.parametrize('kind', ['customer', 'kitchen'])
async def test_styles_are_independent_and_snapshot_survives_settings_change(env, available_fonts, kind):
    rid, req, create = env
    r = await req('PATCH', f'/restaurants/{rid}/settings', {
        f'{kind}_receipt_style': 'aliposter', f'{kind}_receipt_options': {'font_family': 'Arial', 'row_gap': 3}})
    assert r.status_code == 200, r.text
    order = await create()
    sent = await req('POST', f"/orders/{order['id']}/send-to-kitchen", {}, key='one-kitchen')
    assert sent.status_code == 200, sent.text
    retry = await req('POST', f"/orders/{order['id']}/send-to-kitchen", {}, key='one-kitchen')
    assert retry.json() == sent.json()
    paid = await req('POST', f"/orders/{order['id']}/checkout", {'payment_method': 'cash', 'print_receipt': True})
    assert paid.status_code == 200, paid.text
    async with AsyncSessionLocal() as db:
        rows = (await db.scalars(select(ReceiptArchive).where(ReceiptArchive.order_id == order['id']))).all()
        jobs = (await db.scalars(select(PrintJob).where(PrintJob.order_id == order['id']))).all()
        assert len(rows) == 2 and len(jobs) == 2
        for receipt in rows:
            selected = (receipt.receipt_type == 'kitchen') == (kind == 'kitchen')
            assert bool(receipt.print_document) == selected
            job = next(j for j in jobs if j.ticket_type == ('kitchen' if receipt.receipt_type == 'kitchen' else 'kassa'))
            assert job.options.get('print_document') == receipt.print_document
        archive = next(r for r in rows if r.print_document)
        snapshot, archive_id = copy.deepcopy(archive.print_document), archive.id
    assert (await req('PATCH', f'/restaurants/{rid}/settings', {f'{kind}_receipt_style': 'dunyo'})).status_code == 200
    detail = await req('GET', f'/receipts/{archive_id}')
    assert detail.json()['print_document'] == snapshot
    reprint = await req('POST', f'/receipts/{archive_id}/print-usb')
    assert reprint.status_code == 200, reprint.text
    async with AsyncSessionLocal() as db:
        job = await db.get(PrintJob, reprint.json()['job_id'])
        assert job.options['print_document'] == snapshot
    pdf = await req('GET', f'/receipts/{archive_id}/pdf')
    assert pdf.status_code == 200 and pdf.content.startswith(b'%PDF')


async def test_legacy_archive_does_not_adopt_new_style(env, available_fonts):
    rid, req, _ = env
    async with AsyncSessionLocal() as db:
        rec = ReceiptArchive(restaurant_id=rid, receipt_number='LEGACY', raw_text='Old exact text')
        db.add(rec); await db.commit(); await db.refresh(rec)
        receipt_id = rec.id
    assert (await req('PATCH', f'/restaurants/{rid}/settings', {'customer_receipt_style': 'aliposter'})).status_code == 200
    response = await req('POST', f'/receipts/{receipt_id}/print-usb')
    assert response.status_code == 200
    async with AsyncSessionLocal() as db:
        job = await db.get(PrintJob, response.json()['job_id'])
        assert job.raw_text == 'Old exact text' and not job.options.get('print_document')


async def test_missing_font_and_bad_settings_are_explicit_and_do_not_save(env, available_fonts):
    rid, req, _ = env
    body = {'customer_receipt_style': 'aliposter', 'customer_receipt_options': {'font_family': 'Mercury'}}
    response = await req('PATCH', f'/restaurants/{rid}/settings', body)
    assert response.status_code == 422 and 'Mercury' in response.text
    async with AsyncSessionLocal() as db:
        settings = await db.scalar(select(RestaurantSettings).where(RestaurantSettings.restaurant_id == rid))
        assert settings.customer_receipt_style == 'dunyo'
    for invalid in [{'customer_receipt_style': 'unknown'}, {'customer_receipt_options': {'font_size': 0}},
                    {'kitchen_receipt_options': {'row_gap': 100}}, {'customer_receipt_options': {'font_family': '../font.ttf'}}]:
        assert (await req('PATCH', f'/restaurants/{rid}/settings', invalid)).status_code == 422
    assert (await req('PATCH', f'/restaurants/{rid}/settings', {'customer_receipt_style': 'aliposter'}, role='waiter')).status_code == 403
    preview = await req('POST', '/receipts/templates/preview', {'style': 'aliposter', 'appearance': {'font_family': 'Mercury'}})
    assert preview.status_code == 422 and 'Mercury' in preview.text


@pytest.mark.parametrize('paper', [58, 80])
async def test_raster_packet_round_trip_preserves_every_pixel(available_fonts, paper):
    from app.routers.receipts import sample_ticket
    ticket = sample_ticket('customer', styles.ReceiptAppearance().model_dump(), paper)
    document = ticket.print_document
    image = styles.render_document(document)
    data = build_escpos_payload(ticket, print_document=document, cut_paper=False)
    assert data[:5] == b'\x1b@\x1ba\x00'
    offset, height, raster = 5, 0, bytearray()
    while data[offset:offset+4] == b'\x1dv0\x00':
        stride = int.from_bytes(data[offset+4:offset+6], 'little')
        chunk_height = int.from_bytes(data[offset+6:offset+8], 'little')
        offset += 8
        raster.extend(data[offset:offset + stride * chunk_height])
        offset += stride * chunk_height; height += chunk_height
    assert data[offset:] == b'\n\n\n'
    assert stride * 8 == image.width == (576 if paper == 80 else 384)
    assert height == image.height
    assert bytes(b ^ 255 for b in raster) == image.tobytes()
    assert image.getextrema() == (0, 255)


async def test_preview_is_read_only_and_test_print_uses_correct_kind(env, available_fonts):
    rid, req, _ = env
    for kind in ('customer', 'kitchen'):
        response = await req('POST', '/receipts/templates/preview', {'kind': kind, 'style': 'aliposter', 'restaurant_id': rid})
        assert response.status_code == 200, response.text
        assert response.json()['print_document']['kind'] == kind
        assert response.json()['image'].startswith('data:image/png;base64,')
    async with AsyncSessionLocal() as db:
        assert not (await db.scalars(select(PrintJob))).all()
    response = await req('POST', '/receipts/print-raw-usb', {'restaurant_id': rid, 'sample_receipt': True,
        'sample_kind': 'kitchen', 'receipt_style': 'aliposter', 'printer_name': 'TEST-USB'})
    assert response.status_code == 200, response.text
    async with AsyncSessionLocal() as db:
        job = await db.get(PrintJob, response.json()['job_id'])
        assert job.options['print_document']['kind'] == 'kitchen'
        assert job.options['print_document']['appearance']['font_size'] == 16


async def test_long_names_weights_and_large_totals_are_not_dropped(available_fonts):
    args = dict(restaurant_name='Dunyo', address='Xiva', phone='1', table_name='Zal #1', waiter_name='Ofitsiant',
                order_number='TEST', items=[{'name':'Juda uzun taom nomi ' * 8, 'quantity':2,
                'unit_price':230000, 'total_price':690000, 'is_weighted':True, 'weight':1.5}],
                subtotal=690000, service_fee_percent=12, service_fee_amount=82800, discount=0, total=772800)
    old = format_pre_check(**args)
    assert not getattr(old, 'print_document', None)
    styled = format_pre_check(**args, layout=styles.ReceiptAppearance().model_dump())
    assert old == styled  # Existing text formatter remains byte-for-byte unchanged.
    cells = [b['cells'] for b in styled.print_document['blocks'] if b.get('cells')]
    assert any('3 кг' in row for row in cells)
    assert any('772 800' in row for row in cells)
    styles.render_document(styled.print_document)
    assert styles.layout_settings(SimpleNamespace(customer_receipt_style='dunyo'), 'customer') is None


async def test_customer_fee_shows_only_percent_but_total_keeps_fee(available_fonts):
    from app.routers.receipts import sample_ticket
    ticket = sample_ticket('customer', styles.ReceiptAppearance().model_dump())
    cells = [b['cells'] for b in ticket.print_document['blocks'] if b.get('cells')]
    assert ['Обслуживание', '12%'] in cells
    assert not any('10 440' in row for row in cells)
    assert ['Итого', '97 440'] in cells


async def test_cancellation_uses_kitchen_style_and_marks_negative_quantity(env, available_fonts):
    rid, req, create = env
    assert (await req('PATCH', f'/restaurants/{rid}/settings', {'kitchen_receipt_style': 'aliposter'})).status_code == 200
    order = await create()
    assert (await req('POST', f"/orders/{order['id']}/send-to-kitchen", {})).status_code == 200
    response = await req('DELETE', f"/orders/{order['id']}/items/{order['items'][0]['id']}")
    assert response.status_code == 200, response.text
    async with AsyncSessionLocal() as db:
        job = await db.scalar(select(PrintJob).where(PrintJob.order_id == order['id'], PrintJob.ticket_type == 'cancel'))
        assert job.options['print_document']['kind'] == 'kitchen'
        rows = [b.get('cells') for b in job.options['print_document']['blocks']]
        assert ['БЕКОР ҚИЛИНДИ (ОТМЕНА)'] in rows
        assert any(row and row[-1] == '-1' for row in rows)


async def test_regular_font_is_not_black_variant(available_fonts):
    assert styles._font('Arial', False, 10.5).getname()[1].lower() in ('regular', 'normal', 'roman', 'book')


async def test_schema_upgrade_defaults_keep_old_receipts_and_styles():
    engine = create_engine('sqlite:///:memory:')
    with engine.begin() as connection:
        connection.execute(text('CREATE TABLE restaurant_settings (id INTEGER PRIMARY KEY)'))
        connection.execute(text('CREATE TABLE receipt_archives (id INTEGER PRIMARY KEY, raw_text TEXT)'))
        connection.execute(text("INSERT INTO restaurant_settings (id) VALUES (1)"))
        connection.execute(text("INSERT INTO receipt_archives (id, raw_text) VALUES (1, 'unchanged')"))
        _sync_schema_migrations(connection)
        _sync_schema_migrations(connection)
        row = connection.execute(text('SELECT customer_receipt_style, kitchen_receipt_style FROM restaurant_settings')).one()
        assert tuple(row) == ('dunyo', 'dunyo')
        assert tuple(connection.execute(text('SELECT raw_text, print_document FROM receipt_archives')).one()) == ('unchanged', None)
    engine.dispose()
