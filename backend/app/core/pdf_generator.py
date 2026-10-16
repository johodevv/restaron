"""
RestAron — Kassa Cheklari Uchun PDF Generatori (Customer Checkout Bill PDF Archive)
Faqat kassa cheklarini (checkout / final bill) serverda maxsus papkada
(backend/receipts_archive/PDFs/YYYY-MM-DD/) avtomatik PDF formatida arxivlaydi.
Non-blocking va xatoliklarga chidamli (tranzaksiyani to'xtatmaydi).
"""
import os
import re
import asyncio
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from app.core.config import BACKEND_DIR
from app.core.disk_utils import ensure_disk_space

logger = logging.getLogger("pdf_generator")

# PDF Saqlash asosiy papkasi
PDF_ARCHIVE_BASE = os.path.join(BACKEND_DIR, "receipts_archive", "PDFs")

# ─── Shriftlarni yuklash (Unicode / Kirill va Lotin harflari uchun) ────────────
_font_registered = False
_font_regular = "Helvetica"
_font_bold = "Helvetica-Bold"


def _init_fonts():
    global _font_registered, _font_regular, _font_bold
    if _font_registered:
        return

    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont

        # Windows shriftlari (Kirill va O'zbek harflarini 100% to'g'ri ko'rsatish uchun)
        candidates = [
            ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
            ("C:/Windows/Fonts/calibri.ttf", "C:/Windows/Fonts/calibrib.ttf"),
            ("C:/Windows/Fonts/tahoma.ttf", "C:/Windows/Fonts/tahomabd.ttf"),
            ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
            ("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
        ]

        for reg_path, bold_path in candidates:
            if os.path.exists(reg_path):
                pdfmetrics.registerFont(TTFont("ReceiptFont", reg_path))
                if os.path.exists(bold_path):
                    pdfmetrics.registerFont(TTFont("ReceiptFontBold", bold_path))
                else:
                    pdfmetrics.registerFont(TTFont("ReceiptFontBold", reg_path))

                _font_regular = "ReceiptFont"
                _font_bold = "ReceiptFontBold"
                _font_registered = True
                logger.info(f"PDF uchun Unicode shrift muvaffaqiyatli yuklandi: {reg_path}")
                return

        _font_registered = True
    except Exception as e:
        logger.warning(f"TTF shriftlarni ro'yxatga olishda xatolik (standart shrift ishlatiladi): {e}")
        _font_registered = True


def _clean_str(val: Any) -> str:
    """Xavfsiz matnga aylantirish"""
    if val is None:
        return ""
    return str(val).strip()


def _fmt_money(val: float) -> str:
    """Pul miqdorini formatlash: 120000 -> 120 000 so'm"""
    try:
        v = float(val or 0.0)
        return f"{v:,.0f}".replace(",", " ") + " so'm"
    except Exception:
        return f"{val} so'm"


def generate_checkout_receipt_pdf_sync(data: Dict[str, Any]) -> str:
    """
    Sinxron ravishda kassa cheki uchun PDF faylini generatsiya qilish.
    (80mm termal chek uslubidagi ixcham va chiroyli PDF slip)
    """
    _init_fonts()
    from reportlab.pdfgen import canvas

    now_dt = data.get("created_at") or datetime.now()
    if isinstance(now_dt, str):
        try:
            now_dt = datetime.fromisoformat(now_dt)
        except Exception:
            now_dt = datetime.now()

    date_str = now_dt.strftime("%Y-%m-%d")
    time_str = now_dt.strftime("%H:%M:%S")

    # Papka yo'li: backend/receipts_archive/PDFs/YYYY-MM-DD/
    day_folder = os.path.join(PDF_ARCHIVE_BASE, date_str)
    os.makedirs(day_folder, exist_ok=True)

    # Disk to'lib qolmasligini tekshirish
    ensure_disk_space(required_mb=5, path=day_folder)

    # Fayl nomini tozalash (masalan: #R1-0012 -> BILL_R1-0012.pdf)
    order_num = _clean_str(data.get("order_number") or "BILL")
    clean_num = re.sub(r"[^\w\-]", "", order_num.replace("#", ""))
    file_name = f"BILL_{clean_num}_{now_dt.strftime('%H%M%S')}.pdf"
    pdf_path = os.path.join(day_folder, file_name)

    # O'lchamlar (80mm eni = 226.77 pt)
    page_width = 80.0 * 2.83465  # 226.77 pt
    margin = 12.0
    usable_width = page_width - (margin * 2)

    items: List[Dict[str, Any]] = data.get("items") or []

    # Dinamik balandlikni hisoblash (chek qog'ozi behuda cho'zilib ketmasligi uchun)
    base_height = 240.0  # Sarlavha, jadvallar, yakuniy qism va footer
    item_height = len(items) * 22.0
    notes_height = 25.0 if data.get("receipt_note") else 0.0
    deliv_extra = 25.0 if (data.get("delivery_address") or data.get("customer_phone")) else 0.0
    page_height = max(280.0, base_height + item_height + notes_height + deliv_extra)

    c = canvas.Canvas(pdf_path, pagesize=(page_width, page_height))
    c.setTitle(f"Chek #{clean_num}")

    # Chizish koordinatalari (yuqoridan pastga)
    y = page_height - 20.0

    def draw_dashed_line(cur_y: float):
        c.setDash(2, 2)
        c.setStrokeColorRGB(0.5, 0.5, 0.5)
        c.line(margin, cur_y, page_width - margin, cur_y)
        c.setDash([])
        c.setStrokeColorRGB(0, 0, 0)

    def draw_solid_line(cur_y: float):
        c.setStrokeColorRGB(0.2, 0.2, 0.2)
        c.setLineWidth(0.8)
        c.line(margin, cur_y, page_width - margin, cur_y)

    # 1. Restoran nomi va rekvizitlari
    rest_name = _clean_str(data.get("restaurant_name") or "Dunyo Choyxonasi")
    c.setFont(_font_bold, 12)
    c.drawCentredString(page_width / 2.0, y, rest_name[:30])
    y -= 14.0

    c.setFont(_font_regular, 8)
    address = _clean_str(data.get("address") or "Xorazm viloyati, Xiva tumani")
    if address:
        c.drawCentredString(page_width / 2.0, y, address[:45])
        y -= 11.0

    phone = _clean_str(data.get("phone") or "+998884593400")
    if phone:
        c.drawCentredString(page_width / 2.0, y, f"Tel: {phone[:25]}")
        y -= 11.0

    c.setFont(_font_bold, 9)
    c.drawCentredString(page_width / 2.0, y, "★ KASSA TO'LOV CHEKI ★")
    y -= 8.0

    draw_dashed_line(y)
    y -= 12.0

    # 2. Buyurtma va stol ma'lumotlari
    c.setFont(_font_regular, 7.5)
    c.drawString(margin, y, f"Chek: {order_num}")
    c.drawRightString(page_width - margin, y, f"Sana: {date_str} {time_str}")
    y -= 10.0

    order_type = _clean_str(data.get("order_type") or "dine_in").lower()
    table_disp = _clean_str(data.get("table_name") or data.get("table_disp"))
    if not table_disp:
        if order_type == "delivery":
            table_disp = "Yetkazib berish (Dostavka)"
        elif order_type == "takeaway":
            table_disp = "Olib ketish (Takeaway)"
        else:
            table_disp = "Kassa"

    waiter_disp = _clean_str(data.get("waiter_name") or data.get("waiter_disp") or "Kassa")

    if order_type in ("delivery", "takeaway"):
        c.drawString(margin, y, f"Turi: {table_disp[:24]}")
        c.drawRightString(page_width - margin, y, f"Kassir: {waiter_disp[:16]}")
    else:
        c.drawString(margin, y, f"Stol: {table_disp[:24]}")
        c.drawRightString(page_width - margin, y, f"Ofitsiant: {waiter_disp[:16]}")
    y -= 10.0

    cust_name = _clean_str(data.get("customer_name"))
    cust_phone = _clean_str(data.get("customer_phone"))
    if cust_name or cust_phone:
        disp_cust = cust_name
        if cust_phone:
            disp_cust = f"{cust_name} ({cust_phone})" if cust_name else f"Tel: {cust_phone}"
        c.drawString(margin, y, f"Mijoz: {disp_cust[:38]}")
        y -= 10.0

    deliv_addr = _clean_str(data.get("delivery_address"))
    if deliv_addr:
        c.drawString(margin, y, f"Manzil: {deliv_addr[:40]}")
        y -= 10.0

    draw_solid_line(y)
    y -= 11.0

    # 3. Taomlar ro'yxati (Jadval sarlavhasi)
    c.setFont(_font_bold, 7.5)
    c.drawString(margin, y, "Taom nomi")
    c.drawString(margin + 105, y, "Soni")
    c.drawRightString(page_width - margin, y, "Jami")
    y -= 4.0

    draw_dashed_line(y)
    y -= 10.0

    # 4. Taomlar qatorlari
    c.setFont(_font_regular, 7.5)
    for it in items:
        name = _clean_str(it.get("name") or "Taom")
        qty = it.get("quantity") or 1
        unit_price = it.get("unit_price") or 0.0
        total_p = it.get("total_price") or (qty * unit_price)
        weight = it.get("weight")

        qty_str = f"{weight}kg" if weight else f"{qty} dona"

        # 1-qator: Taom nomi
        c.drawString(margin, y, name[:24])
        # Soni va narxi
        c.drawString(margin + 105, y, str(qty_str)[:8])
        # Qator summasi
        c.drawRightString(page_width - margin, y, _fmt_money(total_p))
        y -= 9.0

        # Agar narx yoki qo'shimcha ma'lumot bo'lsa
        if weight:
            c.setFont(_font_regular, 6.5)
            c.setFillColorRGB(0.3, 0.3, 0.3)
            c.drawString(margin + 6, y, f"(1 kg = {_fmt_money(unit_price)})")
            c.setFillColorRGB(0, 0, 0)
            c.setFont(_font_regular, 7.5)
            y -= 8.0

        spec_note = _clean_str(it.get("special_note"))
        if spec_note:
            c.setFont(_font_regular, 6.5)
            c.setFillColorRGB(0.4, 0.4, 0.4)
            c.drawString(margin + 6, y, f"• {spec_note[:32]}")
            c.setFillColorRGB(0, 0, 0)
            c.setFont(_font_regular, 7.5)
            y -= 8.0

        y -= 2.0

    draw_solid_line(y)
    y -= 11.0

    # 5. Moliyaviy jami hisob-kitob
    subtotal = float(data.get("subtotal") or 0.0)
    fee_pct = float(data.get("service_fee_percent") or 0.0)
    fee_amt = float(data.get("service_fee_amount") or (subtotal * fee_pct / 100.0))
    discount = float(data.get("discount") or 0.0)
    grand_total = float(data.get("total") or (subtotal + fee_amt - discount))

    c.setFont(_font_regular, 7.5)
    c.drawString(margin, y, "Oraliq jami:")
    c.drawRightString(page_width - margin, y, _fmt_money(subtotal))
    y -= 10.0

    if fee_pct > 0:
        c.drawString(margin, y, f"Xizmat haqi ({fee_pct:.0f}%):")
        c.drawRightString(page_width - margin, y, _fmt_money(fee_amt))
        y -= 10.0

    if discount > 0:
        c.drawString(margin, y, "Chegirma:")
        c.drawRightString(page_width - margin, y, f"-{_fmt_money(discount)}")
        y -= 10.0

    draw_dashed_line(y)
    y -= 12.0

    # JAMI SUMMA (Katta va qalin)
    c.setFont(_font_bold, 10.5)
    c.drawString(margin, y, "JAMI TO'LOV:")
    c.drawRightString(page_width - margin, y, _fmt_money(grand_total))
    y -= 13.0

    # To'lov turi
    pay_method = _clean_str(data.get("payment_method") or "cash").upper()
    pay_uz = {
        "CASH": "Naqd pul",
        "CARD": "Plastik karta (Terminal)",
        "CLICK": "Click / Payme",
        "DEBT": "Nasiya (Qarz)",
        "MIXED": "Aralash to'lov",
    }.get(pay_method, pay_method)

    c.setFont(_font_bold, 7.5)
    c.drawString(margin, y, "To'lov turi:")
    c.drawRightString(page_width - margin, y, pay_uz)
    y -= 10.0

    # Aralash to'lov tafsiloti bo'lsa
    cash_a = float(data.get("cash_amount") or 0.0)
    card_a = float(data.get("card_amount") or 0.0)
    click_a = float(data.get("click_amount") or 0.0)
    debt_a = float(data.get("debt_amount") or 0.0)
    if pay_method == "MIXED":
        c.setFont(_font_regular, 6.5)
        if cash_a > 0:
            c.drawString(margin + 10, y, f"Naqd: {_fmt_money(cash_a)}")
            y -= 8.0
        if card_a > 0:
            c.drawString(margin + 10, y, f"Karta: {_fmt_money(card_a)}")
            y -= 8.0
        if click_a > 0:
            c.drawString(margin + 10, y, f"Click: {_fmt_money(click_a)}")
            y -= 8.0
        if debt_a > 0:
            c.drawString(margin + 10, y, f"Nasiya: {_fmt_money(debt_a)}")
            y -= 8.0

    # Chek izohi (agar bo'lsa)
    receipt_note = _clean_str(data.get("receipt_note"))
    if receipt_note:
        y -= 2.0
        c.setFont(_font_regular, 6.5)
        c.drawString(margin, y, f"Izoh: {receipt_note[:45]}")
        y -= 9.0

    draw_dashed_line(y)
    y -= 11.0

    # 6. Chek oxiri (Footer)
    footer = _clean_str(data.get("footer_text") or "Tashrifingiz uchun rahmat! Dunyo Choyxonasi (+998884593400)")
    c.setFont(_font_regular, 7.5)
    c.drawCentredString(page_width / 2.0, y, footer[:40])
    y -= 9.0

    wifi_pass = _clean_str(data.get("wifi_pass"))
    if wifi_pass:
        c.setFont(_font_regular, 6.5)
        c.drawCentredString(page_width / 2.0, y, f"Wi-Fi parol: {wifi_pass[:30]}")
        y -= 8.0

    c.setFont(_font_regular, 5.5)
    c.setFillColorRGB(0.5, 0.5, 0.5)
    c.drawCentredString(page_width / 2.0, y, "Dunyo Choyxonasi POS | Avtomatlashtirilgan PDF Arxiv")

    c.save()
    logger.info(f"Kassa PDF cheki muvaffaqiyatli saqlandi: {pdf_path}")
    return pdf_path


async def async_save_checkout_receipt_pdf(data: Dict[str, Any]) -> Optional[str]:
    """
    Kassa cheki PDF faylini asinxron va xavfsiz (non-blocking) tarzda saqlash.
    Xatolik yuz bersa (disk to'lishi, font xatosi) asosiy tranzaksiyani
    to'xtatmaydi, xatoni logga yozib None qaytaradi.
    """
    try:
        return await asyncio.to_thread(generate_checkout_receipt_pdf_sync, data)
    except Exception as exc:
        logger.error(f"Kassa PDF chekini arxivlashda xatolik yuz berdi: {exc}", exc_info=True)
        return None
