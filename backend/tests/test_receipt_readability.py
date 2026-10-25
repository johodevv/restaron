"""Verify actual ESC/POS bytes and plain-text width; no physical printer calls."""
import pytest
from app.core.printer_service import (format_pre_check, receipt_columns, build_escpos_payload,
    receipt_line_roles, _wrap_words, _font_spec, clean_for_cp866, _center_line, _amount_line)


def sample(**options):
    return format_pre_check(order_number='TEST-ONLY', table_name='Zal #12', waiter_name='Ali',
        restaurant_name='Dunyo Choyxona', address='Xiva', phone='+998900001122',
        items=[{'name': 'Uzun nomli maxsus tovuq kabob', 'quantity': 2, 'unit_price': 50000, 'total_price': 100000},
               {'name': 'Baliq', 'quantity': 2, 'unit_price': 100000, 'weight': 1.5, 'is_weighted': True, 'total_price': 300000}],
        subtotal=400000, service_fee_percent=7.5, service_fee_amount=30000, discount=0, total=430000,
        footer_text='Rahmat', **options)


@pytest.mark.parametrize('paper', [58, 80])
@pytest.mark.parametrize('font', ['normal', 'baland', 'keng', 'katta', 'juda_katta'])
@pytest.mark.parametrize('spacing', [0, 1, 6])
def test_receipt_fits_paper_and_preserves_amounts(paper, font, spacing):
    text = sample(paper_width=paper, font_size=font, char_spacing=spacing)
    width = receipt_columns(paper, font, spacing)
    assert all(len(line) <= width for line in text.splitlines()), (width, text)
    assert '430 000' in text and '300 000' in text and '100 000' in text
    assert '7.5%' in text
    assert 'кабоб' in text and 'Балиқ' in text
    # Exact summed weight (2 portions * 1.5 kg), never a misleading 1.5 kg.
    compact = ''.join(text.split())
    assert '3кг' in compact
    framed = [line for line in text.splitlines() if line.startswith(('┌','│','├','└'))]
    assert not framed or len({len(line) for line in framed}) == 1


@pytest.mark.parametrize('font', ['normal', 'katta', 'juda_katta'])
def test_total_has_distinct_size_and_underline_without_changing_width(font):
    text = sample(font_size=font)
    data = build_escpos_payload(text, cut_paper=False, font_size=font)
    spec = _font_spec(font)
    total_size = ((spec['w']-1) << 4) | min(7, spec['h'])
    assert b'\x1d\x21'+bytes([total_size])+b'\x1b\x2d\x01' in data
    assert b'\x1b\x2d\x00' in data
    assert clean_for_cp866('430 000').encode('cp866') in data
    assert '\x1b' not in text


def test_table_uses_continuous_glyph_spacing_then_restores_printer_settings():
    data = build_escpos_payload(sample(font_size='normal'), font_size='normal', char_spacing=1)
    assert b'\x1b\x20\x00\x1b\x33\x18' in data
    assert b'\x1b\x20\x01\x1d\x21\x00' in data
    assert '┌'.encode('cp866') in data and '│'.encode('cp866') in data


def test_indented_wrapping_never_discards_letters():
    value = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ abcdefghijklmnopqrstuvwxyz'
    wrapped = _wrap_words(value, 12, indent='  ')
    assert ''.join(''.join(wrapped).split()) == ''.join(value.split())
    assert max(map(len, wrapped)) <= 12


def test_total_on_next_line_is_emphasized_but_subtotal_is_not():
    roles = receipt_line_roles('Таомлар: 100 000\nЖАМИ ТЎЛОВ:\n  110 000\nРаҳмат\n')
    assert [role for _, role in roles] == ['body', 'total', 'total', 'body']


def test_long_centered_header_and_phone_do_not_lose_characters():
    value = 'DunyoChoyxonasiningUzunNomi +998900001122'
    lines = _center_line(value, 10).splitlines()
    assert max(map(len, lines)) <= 10
    assert ''.join(''.join(lines).split()) == ''.join(value.split())


def test_large_total_uses_compact_digits_on_narrow_paper():
    text = _amount_line('ЖАМИ:', '999 999 999', 10)
    assert '999999999' in text
    assert max(map(len, text.splitlines())) <= 10
