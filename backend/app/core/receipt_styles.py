"""Versioned receipt layouts. Stored documents keep queue retries and reprints stable.

Sizes are points (72/inch); customer defaults convert AliPos WPF 14/18 DIP
to 10.5/13.5 pt. Kitchen defaults come from its separate Arial GDI template.
No third-party font files are distributed with this application.
"""
from functools import lru_cache
from io import BytesIO
import os
from pathlib import Path
from typing import Literal

from PIL import Image, ImageDraw, ImageFont
from pydantic import BaseModel, Field


class ReceiptAppearance(BaseModel):
    font_family: Literal['Arial', 'Mercury'] = 'Arial'
    font_size: float = Field(10.5, ge=7, le=30, allow_inf_nan=False)
    font_bold: bool = False
    total_size: float = Field(13.5, ge=7, le=36, allow_inf_nan=False)
    total_bold: bool = True
    header_size: float = Field(14, ge=7, le=36, allow_inf_nan=False)
    header_bold: bool = True
    order_size: float = Field(20, ge=7, le=40, allow_inf_nan=False)
    order_bold: bool = True
    meta_size: float = Field(10.5, ge=7, le=30, allow_inf_nan=False)
    meta_bold: bool = False
    row_gap: float = Field(2, ge=0, le=12, allow_inf_nan=False)


class ReceiptBlock(BaseModel):
    cells: list[str] = Field(default_factory=list, max_length=4)
    widths: list[float] = Field(default_factory=list, max_length=4)
    role: Literal['body', 'meta', 'header', 'order', 'total'] = 'body'
    align: Literal['left', 'center', 'right'] = 'left'
    rule: Literal['', 'solid', 'dotted'] = ''


class ReceiptDocument(BaseModel):
    version: Literal[1] = 1
    style: Literal['aliposter'] = 'aliposter'
    kind: Literal['customer', 'kitchen']
    paper_width: Literal[58, 80] = 80
    appearance: ReceiptAppearance
    blocks: list[ReceiptBlock] = Field(max_length=2000)


class StyledReceipt(str):
    def __new__(cls, text, document):
        obj = super().__new__(cls, text)
        obj.print_document = document
        return obj


def appearance_defaults(kind):
    if kind == 'kitchen':
        return dict(font_size=16, font_bold=True, meta_size=12,
                    header_size=16, order_size=16)
    return {}


def layout_settings(settings, kind):
    if getattr(settings, f'{kind}_receipt_style', 'dunyo') != 'aliposter':
        return None
    return ReceiptAppearance(**{
        **appearance_defaults(kind),
        **(getattr(settings, f'{kind}_receipt_options', None) or {}),
    }).model_dump()


@lru_cache(maxsize=1)
def font_catalog():
    """Resolve internal family names, including per-user Windows installations."""
    roots = [Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts',
             Path(os.environ.get('LOCALAPPDATA', '')) / 'Microsoft/Windows/Fonts']
    found = {}
    for root in roots:
        if not root.is_dir():
            continue
        for path in sorted(root.iterdir()):
            if path.suffix.lower() not in ('.ttf', '.otf', '.ttc'):
                continue
            try:
                face = ImageFont.truetype(str(path), 16)
                family, variant = face.getname()
                if family.casefold() in ('arial', 'mercury'):
                    variant = variant.casefold()
                    if variant in ('regular', 'normal', 'roman', 'book', 'bold'):
                        found[(family.casefold(), variant == 'bold')] = str(path)
            except OSError:
                continue
    return found


def font_status(refresh=False):
    if refresh:
        font_catalog.cache_clear()
        _font.cache_clear()
    catalog = font_catalog()
    return {family: {'regular': (family.lower(), False) in catalog,
                     'bold': (family.lower(), True) in catalog}
            for family in ('Arial', 'Mercury')}


@lru_cache(maxsize=128)
def _font(family, bold, points):
    path = font_catalog().get((family.lower(), bold))
    if not path:
        raise ValueError(f'{family} ({"Bold" if bold else "Regular"}) shrifti serverda topilmadi. '
                         'Shriftni Windows’ga o‘rnating yoki boshqa shriftni tanlang.')
    return ImageFont.truetype(path, max(1, round(points * 203 / 72)))


def validate_fonts(appearance):
    a = ReceiptAppearance.model_validate(appearance)
    for role in ('font', 'total', 'header', 'order', 'meta'):
        _font(a.font_family, getattr(a, f'{role}_bold'), getattr(a, f'{role}_size'))


def _wrap(text, font, width):
    # Long names/amounts wrap rather than silently clipping or dropping digits.
    text = str(text).replace('\r', '').replace('\t', ' ')
    lines = []
    for paragraph in text.split('\n'):
        line = ''
        for word in paragraph.split(' '):
            candidate = f'{line} {word}'.strip()
            if font.getlength(candidate) <= width:
                line = candidate
                continue
            if line:
                lines.append(line)
                line = ''
            for char in word:
                if line and font.getlength(line + char) > width:
                    lines.append(line)
                    line = ''
                line += char
        lines.append(line)
    return lines or ['']


def render_document(document):
    doc = ReceiptDocument.model_validate(document)
    if sum(len(t) for b in doc.blocks for t in b.cells) > 100000:
        raise ValueError('Chek matni juda uzun')
    validate_fonts(doc.appearance)
    width = 576 if doc.paper_width == 80 else 384
    margin = 8
    usable = width - margin * 2
    a = doc.appearance
    gap = round(a.row_gap * 203 / 72)
    commands = []
    y = 8
    for block in doc.blocks:
        if block.rule:
            commands.append(('rule', y + 3, block.rule))
            y += 8
            continue
        prefix = 'font' if block.role == 'body' else block.role
        font = _font(a.font_family, getattr(a, f'{prefix}_bold'), getattr(a, f'{prefix}_size'))
        cells = block.cells or ['']
        weights = block.widths or [1] * len(cells)
        if len(weights) != len(cells) or any(w <= 0 or not w < 10000 for w in weights):
            raise ValueError('Chek ustunlari noto‘g‘ri')
        ascent, descent = font.getmetrics()
        line_height = ascent + descent + 2
        x = margin
        height = 0
        for i, (text, weight) in enumerate(zip(cells, weights)):
            cell_width = usable * weight / sum(weights)
            cell_font = font
            numeric = text.strip().replace(' ', '').replace(',', '').replace('.', '').lstrip('-').isdigit()
            if numeric and font.getlength(text) > cell_width - 8:
                points = max(7, getattr(a, f'{prefix}_size') * (cell_width - 8) / font.getlength(text))
                cell_font = _font(a.font_family, getattr(a, f'{prefix}_bold'), points)
            lines = _wrap(text, cell_font, max(10, cell_width - 8))
            for j, line in enumerate(lines):
                align = block.align if len(cells) == 1 else ('left' if i == 0 else 'right')
                dx = 0 if align == 'left' else (cell_width - 8 - cell_font.getlength(line)) / (2 if align == 'center' else 1)
                commands.append(('text', round(x + dx), y + j * line_height, line, cell_font))
            height = max(height, len(lines) * line_height)
            x += cell_width
        y += height + gap
        if y > 100000:
            raise ValueError('Chek uzunligi limitdan oshdi')
    image = Image.new('L', (width, y + 24), 255)
    draw = ImageDraw.Draw(image)
    for command in commands:
        if command[0] == 'text':
            _, x, top, line, font = command
            draw.text((x, top), line, font=font, fill=0, anchor='lt')
        else:
            _, top, style = command
            if style == 'solid':
                draw.line((margin, top, width - margin - 1, top), fill=0, width=2)
            else:
                for x in range(margin, width - margin, 8):
                    draw.line((x, top, min(x + 3, width - margin - 1), top), fill=0, width=1)
    return image.point(lambda p: 0 if p < 160 else 255, mode='1')


def png_bytes(document):
    buffer = BytesIO()
    render_document(document).save(buffer, format='PNG', dpi=(203, 203))
    return buffer.getvalue()


def raster_payload(document, cut_paper=True):
    image = render_document(document)
    stride = (image.width + 7) // 8
    # ESC/POS raster uses 1 for ink, while Pillow mode 1 uses 1 for white.
    data = bytes(b ^ 255 for b in image.tobytes())
    payload = bytearray(b'\x1b@\x1ba\x00')
    for top in range(0, image.height, 256):
        height = min(256, image.height - top)
        payload.extend(b'\x1dv0\x00' + bytes((stride % 256, stride // 256, height % 256, height // 256)))
        payload.extend(data[top * stride:(top + height) * stride])
    payload.extend(b'\n\n\n')
    if cut_paper:
        payload.extend(b'\x1dV\x00')
    return bytes(payload)


def styled_receipt(text, kind, appearance, paper_width, fields):
    from app.core.printer_service import latin_to_cyrillic, merge_receipt_items, fmt_percent
    a = ReceiptAppearance.model_validate(appearance).model_dump()
    validate_fonts(a)
    blocks = []
    def row(*cells, role='body', widths=None, align='left'):
        blocks.append(dict(cells=[str(c) for c in cells], widths=widths or [], role=role, align=align))
    def rule(dotted=False):
        blocks.append(dict(rule='dotted' if dotted else 'solid'))
    def cyr(value):
        return latin_to_cyrillic(str(value or ''))
    def money(value):
        return f'{float(value or 0):,.0f}'.replace(',', ' ')
    if kind == 'customer':
        row(cyr(fields['restaurant_name']), role='header', align='center')
        for value in (fields.get('address'), fields.get('phone')):
            if value:
                row(cyr(value), role='meta', align='center')
        row(cyr(fields['table_name']), fields['date'], role='meta', widths=[1, 1])
        row(f"Официант: {cyr(fields['waiter_name'])}", role='meta')
        row(f"№ {fields['order_number']}", role='order', align='center')
        rule()
        if paper_width == 80:
            row('Таом', 'Кол', 'Нархи', 'Жами', widths=[115, 35, 52, 60])
        else:
            row('Таом', 'Жами', widths=[3, 2])
    else:
        row(cyr(fields.get('station_title') or 'ОШХОНА'), role='header', align='center')
        row(cyr(fields.get('hall_name') or fields.get('room_name') or 'Зал'), role='header')
        row(f"Стол: № {fields['table_number']}", role='order')
        if fields.get('order_number'):
            row(f"N# {fields['order_number']}", role='order')
        row(f"Выполнен: {cyr(fields['waiter_name'])}", role='meta')
        row(fields['date'], role='meta')
        if fields.get('is_reprint'):
            row('ТАКРОР — ЯНГИ БУЮРТМА ЭМАС', role='header')
        rule()
    for index, item in enumerate(merge_receipt_items(fields['items']), 1):
        name = cyr(item.get('name_cyrillic') or item.get('name') or 'Таом')
        if item.get('size'):
            name += f" [{cyr(item['size'])}]"
        qty = item.get('quantity') or 1
        count = str(qty)
        price = money(item.get('unit_price') or item.get('price'))
        amount = money(item.get('total_price') if item.get('total_price') is not None else qty * float(item.get('unit_price') or 0))
        if item.get('is_weighted'):
            if item.get('weight'):
                count = f"{float(item['weight']) * qty:g} {cyr(item.get('unit') or 'kg')}"
            elif item.get('manual_price') is None:
                count, amount = 'ТОРТИЛСИН', '—'
            else:
                price = '—'
        if kind == 'customer':
            if paper_width == 80:
                row(f'{index}. {name}', count, price, amount, widths=[115, 30, 58, 60])
            else:
                row(f'{index}. {name}', amount, widths=[3, 2])
                row(f'Миқдор: {count} · Нархи: {price}', role='meta')
            rule(True)
        else:
            row(name, count, widths=[4, 1])
        if item.get('note'):
            row(cyr(item['note']), role='meta')
    rule()
    if kind == 'customer':
        row('Подытог', money(fields['subtotal']), role='total', widths=[3, 2])
        if fields.get('service_fee_percent'):
            fee_label = 'Обслуживание' if paper_width == 80 else 'Хизмат'
            row(fee_label, f"{fmt_percent(fields['service_fee_percent'])}%", role='total', widths=[3, 2])
        if fields.get('discount'):
            row('Скидка', money(fields['discount']), role='total', widths=[3, 2])
        row('Итого', money(fields['total']), role='total', widths=[3, 2])
        if fields.get('advance_amount'):
            row('Аванс', money(fields['advance_amount']), role='total', widths=[3, 2])
            row('К оплате', money(max(0, fields['total'] - fields['advance_amount'])), role='total', widths=[3, 2])
        for value in (fields.get('receipt_note'), fields.get('footer_text')):
            if value:
                row(cyr(value), role='meta')
        if fields.get('wifi_pass'):
            row(f"Wi-Fi: {fields['wifi_pass']}", role='meta')
    elif fields.get('kitchen_note'):
        row(cyr(fields['kitchen_note']))
    document = ReceiptDocument(kind=kind, paper_width=paper_width, appearance=a, blocks=blocks).model_dump()
    return StyledReceipt(text, document)
