"""
Xprinter Termal Chek Xizmati (58mm va 80mm)
Oshxona begunogi (Kitchen runner), Mijoz hisob cheki (Bill / Pre-check)
va Kassa smena hisoboti (X/Z Report) generatsiya qilish
"""
from datetime import datetime
from typing import List, Dict, Any, Optional


def _pad_line(left: str, right: str, width: int = 42) -> str:
    """Ikki tomonlama tekislangan qator yaratish (chap va o'ng)"""
    left = str(left)
    right = str(right)
    space_needed = width - len(left) - len(right)
    if space_needed < 1:
        return f"{left[:width - len(right) - 1]} {right}"
    return f"{left}{' ' * space_needed}{right}"


def _center_line(text: str, width: int = 42) -> str:
    """Matnni markazga joylashtirish"""
    text = str(text)
    if len(text) >= width:
        return text[:width]
    pad = (width - len(text)) // 2
    return f"{' ' * pad}{text}"


def latin_to_cyrillic(text: Optional[str]) -> str:
    """O'zbek lotin yozuvidagi matnni krill harflariga o'girish (termal cheklar uchun)"""
    if not text:
        return ""
    s = str(text)

    # 2-harfli birikmalar (katta-kichik harflar bilan)
    multi_pairs = [
        ("sh", "ш"), ("Sh", "Ш"), ("SH", "Ш"),
        ("ch", "ч"), ("Ch", "Ч"), ("CH", "Ч"),
        ("yo", "ё"), ("Yo", "Ё"), ("YO", "Ё"),
        ("yu", "ю"), ("Yu", "Ю"), ("YU", "Ю"),
        ("ya", "я"), ("Ya", "Я"), ("YA", "Я"),
        ("ye", "е"), ("Ye", "Е"), ("YE", "Е"),
        ("o'", "ў"), ("O'", "Ў"), ("o‘", "ў"), ("O‘", "Ў"), ("o’", "ў"), ("O’", "Ў"), ("o`", "ў"), ("O`", "Ў"),
        ("g'", "ғ"), ("G'", "Ғ"), ("g‘", "ғ"), ("G‘", "Ғ"), ("g’", "ғ"), ("G’", "Ғ"), ("g`", "ғ"), ("G`", "Ғ"),
    ]
    for lat, cyr in multi_pairs:
        s = s.replace(lat, cyr)

    # 1-harfli harflar
    single_map = {
        'a': 'а', 'A': 'А',
        'b': 'б', 'B': 'Б',
        'd': 'д', 'D': 'Д',
        'e': 'е', 'E': 'Е',
        'f': 'ф', 'F': 'Ф',
        'g': 'г', 'G': 'Г',
        'h': 'ҳ', 'H': 'Ҳ',
        'i': 'и', 'I': 'И',
        'j': 'ж', 'J': 'Ж',
        'k': 'к', 'K': 'К',
        'l': 'л', 'L': 'Л',
        'm': 'м', 'M': 'М',
        'n': 'н', 'N': 'Н',
        'o': 'о', 'O': 'О',
        'p': 'п', 'P': 'П',
        'q': 'қ', 'Q': 'Қ',
        'r': 'р', 'R': 'Р',
        's': 'с', 'S': 'С',
        't': 'т', 'T': 'Т',
        'u': 'у', 'U': 'У',
        'v': 'в', 'V': 'В',
        'x': 'х', 'X': 'Х',
        'y': 'й', 'Y': 'Й',
        'z': 'з', 'Z': 'З',
    }
    return "".join(single_map.get(ch, ch) for ch in s)


def clean_for_cp866(text: str) -> str:
    """
    CP866 (DOS Russian) kodirovkasida xatolik '???' chiqmasligi uchun
    maxsus o'zbek kirill harflarini standart rus kirill harflariga normallashtirish.
    Xprinter termal printerlari buni 100% tiniq va xatosiz chop etadi!
    """
    if not text:
        return ""
    t = str(text)
    cp_map = {
        'Ў': 'У', 'ў': 'у',
        'Қ': 'К', 'қ': 'к',
        'Ғ': 'Г', 'ғ': 'г',
        'Ҳ': 'Х', 'ҳ': 'х',
        '’': "'", '‘': "'", '`': "'", '“': '"', '”': '"',
    }
    for k, v in cp_map.items():
        t = t.replace(k, v)
    return t


# ─── ESC/POS buyruqlari ────────────────────────────────────────────────
ESC_INIT = b"\x1b\x40"          # ESC @   -- printerni boshlang'ich holatga keltirish
FS_KANJI_OFF = b"\x1c\x2e"      # FS .    -- IEROGLIF (Kanji) rejimini O'CHIRISH
FS_KANJI_OFF2 = b"\x1c\x43\x00"  # FS C 0 -- ko'p baytli belgilar rejimini o'chirish
ESC_FONT_A = b"\x1b\x21\x00"    # ESC ! 0 -- Font A, oddiy o'lcham (48 belgi / 80mm)
ESC_CUT = b"\n\n\n\n\x1d\x56\x42\x00"  # qog'ozni kesish

# PC866 (kirill) kod sahifasining raqami. Epson standartida 17, lekin
# ba'zi Xprinter modellarida boshqacha bo'lishi mumkin -- shuning uchun
# sozlamalardan o'zgartirish mumkin.
DEFAULT_CODEPAGE = 17

# Chek shrifti o'lchami (keksa odamlar ham o'qiy olishi uchun).
#   normal      — standart, 80mm da 48 belgi
#   katta       — bo'yi 2 barobar, kengligi o'sha-o'sha (48 belgi saqlanadi,
#                 chek chiroyli tekis chiqadi) — KO'PCHILIKKA SHU MA'QUL
#   juda_katta  — bo'yi ham, eni ham 2 barobar (80mm da 24 belgi)
# GS ! n : yuqori 4 bit = kenglik, quyi 4 bit = balandlik (0 = 1x)
FONT_SIZES = {
    "normal":     {"gs": 0x00, "w": 1},
    "katta":      {"gs": 0x01, "w": 1},
    "juda_katta": {"gs": 0x11, "w": 2},
}
DEFAULT_FONT_SIZE = "normal"


def _font_spec(font_size: Optional[str]) -> dict:
    return FONT_SIZES.get((font_size or "").strip().lower(), FONT_SIZES[DEFAULT_FONT_SIZE])


def build_escpos_payload(raw_text: str, cut_paper: bool = True,
                         codepage: int = DEFAULT_CODEPAGE,
                         font_size: str = DEFAULT_FONT_SIZE) -> bytes:
    """
    Matnni termal printer tushunadigan baytlarga aylantiradi.

    MUHIM: matnni CP866 ga kodlashning o'zi YETARLI EMAS. Printer sukut
    bo'yicha CP437 (lotin) kod sahifasida o'qiydi, shuning uchun kirill
    harflar tushunarsiz belgilarga aylanib chiqadi. Avval `ESC t 17`
    buyrug'i bilan printerga PC866 kod sahifasini ishlatishini aytamiz.

    Shuningdek `ESC @` bilan printerni tozalaymiz va `ESC ! 0` bilan
    Font A (oddiy o'lcham) ni o'rnatamiz -- aks holda oldingi ishdan
    qolgan kichik shrift (Font B) bilan chop etilishi mumkin.
    """
    clean_text = clean_for_cp866(raw_text or "")
    try:
        body = clean_text.encode("cp866", errors="replace")
    except Exception:
        body = (raw_text or "").encode("utf-8", errors="replace")

    # MUHIM: Xitoyda ishlab chiqarilgan printerlarda ko'pincha IEROGLIF
    # (Kanji/GB) rejimi yoqilgan bo'ladi -- har IKKI bayt bitta ieroglif
    # deb o'qiladi va kirill matn YAPONCHA/XITOYCHA bo'lib chiqadi.
    # Shuning uchun avval shu rejimni o'chiramiz, keyin kod sahifasini
    # tanlaymiz.
    esc_codepage = b"\x1b\x74" + bytes([max(0, min(255, int(codepage)))])

    # GS ! n — belgi o'lchami. Sozlamadan "katta" tanlansa harflar
    # bo'yiga 2 barobar kattayadi, qator kengligi esa o'zgarmaydi.
    gs_size = b"\x1d\x21" + bytes([_font_spec(font_size)["gs"]])

    payload = (ESC_INIT + FS_KANJI_OFF + FS_KANJI_OFF2
               + esc_codepage + ESC_FONT_A + gs_size + body)
    if cut_paper:
        payload += ESC_CUT
    return payload


def receipt_columns(paper_width: int, font_size: str = DEFAULT_FONT_SIZE) -> int:
    """
    Termal printer uchun bir qatordagi belgilar soni.

    203 dpi li ESC/POS printerlarda standart Font A kengligi 12 nuqta =
    1.5 mm. Shunga ko'ra:
      - 80mm qog'oz -> bosiladigan maydon ~72mm -> 72 / 1.5 = 48 belgi
      - 58mm qog'oz -> bosiladigan maydon ~48mm -> 48 / 1.5 = 32 belgi

    Ilgari 80mm uchun 42 qo'yilgan edi: chek qog'ozning faqat ~87% ini
    egallab, tor va kichik bo'lib chiqardi.
    """
    base = 48 if paper_width >= 80 else 32
    # Harf eni 2 barobar bo'lsa, qatorga sig'adigan belgilar soni yarmiga
    # tushadi — aks holda matn qog'ozdan chiqib, chek buzilib ketadi.
    return max(16, base // _font_spec(font_size)["w"])


def format_kitchen_ticket(
    hall_name: Optional[str],
    room_name: Optional[str],
    table_number: Any,
    waiter_name: str,
    items: List[Dict[str, Any]],
    kitchen_note: Optional[str] = None,
    order_time: Optional[datetime] = None,
    paper_width: int = 80,
    station_title: Optional[str] = None,
    font_size: str = DEFAULT_FONT_SIZE,
) -> str:
    """
    Oshxona / Bar begunogi (Runner ticket) — To'liq Kirill alifbosida
    """
    col_width = receipt_columns(paper_width, font_size)
    sep = "-" * col_width
    dt = order_time or datetime.now()
    dt_str = dt.strftime("%d.%m.%Y | %H:%M")

    lines = []
    # Oshxona stansiyasi sarlavhasi
    st_title = station_title or "ОШХОНА БЕГУНОГИ"
    lines.append(_center_line(f"*** {latin_to_cyrillic(st_title).upper()} ***", col_width))

    # Zal / Xona nomi
    zal = hall_name or room_name or "Зал"
    lines.append(_center_line(latin_to_cyrillic(zal).upper(), col_width))
    if room_name and room_name != hall_name:
        lines.append(_center_line(latin_to_cyrillic(room_name), col_width))

    # Stol va Ofitsiant
    lines.append(f"Стол: № {table_number}")
    waiter_cyr = latin_to_cyrillic(waiter_name or 'Официант')
    lines.append(f"Официант: {waiter_cyr}")
    lines.append(f"Вақт: {dt_str}")
    lines.append(sep)

    lines.append(_pad_line("ТАОМ", "СОНИ", col_width))
    lines.append(sep)

    for item in items:
        raw_name = item.get("name_cyrillic") or item.get("name") or "Таом"
        name = latin_to_cyrillic(raw_name)
        # O'lchanadigan taom hajmi (1.5 L / 1.4 kg) nom bilan birga chiqadi —
        # oshpaz qaysi hajm kerakligini begunokdan ko'radi.
        size = (item.get("size") or "").strip()
        if size:
            name = f"{name} [{latin_to_cyrillic(size)}]"
        qty = item.get("quantity") or 1

        # Tortiladigan taom: og'irligi ko'rsatiladi, tortilmagan bo'lsa
        # oshxona ko'rib turishi uchun ogohlantirish chiqadi.
        if item.get("is_weighted"):
            wt = item.get("weight")
            unit_cyr = latin_to_cyrillic(item.get("unit") or "kg")
            if wt:
                lines.append(_pad_line(name, f"{wt:g} {unit_cyr}", col_width))
            else:
                lines.append(_pad_line(name, "ТОРТИЛСИН!", col_width))
            continue

        lines.append(_pad_line(name, f"{qty} та", col_width))
        if item.get("note"):
            note_cyr = latin_to_cyrillic(item['note'])
            lines.append(f"  * {note_cyr}")

    lines.append(sep)
    if kitchen_note:
        note_str = latin_to_cyrillic(kitchen_note)
        lines.append(f"Изоҳ: {note_str}")
        lines.append(sep)

    return "\n".join(lines) + "\n\n\n"


def format_pre_check(
    restaurant_name: str,
    address: Optional[str],
    phone: Optional[str],
    table_name: str,
    waiter_name: str,
    order_number: str,
    items: List[Dict[str, Any]],
    subtotal: float,
    service_fee_percent: float,
    service_fee_amount: float,
    discount: float,
    total: float,
    receipt_note: Optional[str] = None,
    footer_text: Optional[str] = None,
    wifi_pass: Optional[str] = None,
    created_at: Optional[datetime] = None,
    paper_width: int = 80,
    font_size: str = DEFAULT_FONT_SIZE,
) -> str:
    """
    Mijoz hisob cheki (Pre-check / Bill) — To'liq Kirill alifbosida
    """
    col_width = receipt_columns(paper_width, font_size)
    sep = "-" * col_width
    double_sep = "=" * col_width
    dt = created_at or datetime.now()
    dt_str = dt.strftime("%d.%m.%Y %H:%M")

    lines = []
    lines.append(double_sep)
    rest_cyr = latin_to_cyrillic(restaurant_name or "RestAron")
    lines.append(_center_line(rest_cyr.upper(), col_width))
    if address:
        lines.append(_center_line(latin_to_cyrillic(address), col_width))
    if phone:
        lines.append(_center_line(f"Тел: {phone}", col_width))
    if wifi_pass:
        lines.append(_center_line(f"Wi-Fi: {wifi_pass}", col_width))
    lines.append(sep)

    tbl_cyr = latin_to_cyrillic(table_name)
    lines.append(_pad_line(f"Стол: {tbl_cyr}", f"Чек: №{order_number}", col_width))
    w_cyr = latin_to_cyrillic(waiter_name or 'Ходим')
    lines.append(_pad_line(f"Официант: {w_cyr}", dt_str, col_width))
    lines.append(sep)
    lines.append("Таомлар:")

    for idx, it in enumerate(items, 1):
        raw_name = it.get("name_cyrillic") or it.get("name") or "Таом"
        name = latin_to_cyrillic(raw_name)
        size = (it.get("size") or "").strip()
        if size:
            name = f"{name} [{latin_to_cyrillic(size)}]"
        qty = it.get("quantity") or 1
        unit_price = it.get("unit_price") or it.get("price") or 0.0
        line_total = it.get("total_price") or (qty * unit_price)

        lines.append(f"{idx}. {name}")
        tot_str = f"{line_total:,.0f}".replace(",", " ")

        # Tortiladigan taomda hisob "og'irlik x 1 kg narxi" ko'rinishida
        # yoziladi — mijoz nechchi kg olganini va nega shuncha pul
        # ekanini chekning o'zidan ko'radi.
        wt = it.get("weight")
        if it.get("is_weighted") and wt:
            unit_cyr = latin_to_cyrillic(it.get("unit") or "kg")
            calc_str = f"   {wt:g} {unit_cyr} x {unit_price:,.0f}".replace(",", " ")
            if qty > 1:
                calc_str = f"   {qty} x {wt:g} {unit_cyr} x {unit_price:,.0f}".replace(",", " ")
        else:
            calc_str = f"   {qty} x {unit_price:,.0f}".replace(",", " ")
        lines.append(_pad_line(calc_str, tot_str, col_width))

    lines.append(sep)
    sub_str = f"{subtotal:,.0f}".replace(",", " ")
    lines.append(_pad_line("Жами (Итого):", sub_str, col_width))

    if service_fee_percent > 0:
        fee_title = f"Хизмат ҳақи ({service_fee_percent:.0f}%):"
        fee_str = f"{service_fee_amount:,.0f}".replace(",", " ")
        lines.append(_pad_line(fee_title, fee_str, col_width))

    if discount > 0:
        disc_str = f"-{discount:,.0f}".replace(",", " ")
        lines.append(_pad_line("Чегирма (Скидка):", disc_str, col_width))

    lines.append(double_sep)
    total_str = f"{total:,.0f}".replace(",", " ")
    lines.append(_pad_line("ЖАМИ ТЎЛОВ:", total_str, col_width))
    lines.append(double_sep)

    if receipt_note:
        lines.append(f"Изоҳ: {latin_to_cyrillic(receipt_note)}")
        lines.append(sep)

    foot = footer_text or "Ташрифингиз учун раҳмат! Яна келинг!"
    lines.append(_center_line(latin_to_cyrillic(foot), col_width))

    return "\n".join(lines) + "\n\n\n"


format_customer_receipt = format_pre_check


def format_shift_report(
    report_type: str,
    restaurant_name: str,
    shift_number: int,
    cashier_name: str,
    opened_at: Optional[datetime],
    closed_at: Optional[datetime],
    total_orders: int,
    total_sales: float,
    total_cash: float,
    total_card: float,
    total_click: float,
    total_debt: float,
    total_service_fee: float,
    total_waiter_earnings: float,
    waiter_breakdown: Optional[List[Dict[str, Any]]] = None,
    paper_width: int = 80,
    font_size: str = DEFAULT_FONT_SIZE,
) -> str:
    """
    X-Report (oraliq hisobot) yoki Z-Report (kassani yopish) — To'liq Kirill alifbosida
    """
    col_width = receipt_columns(paper_width, font_size)
    sep = "-" * col_width
    double_sep = "=" * col_width

    title = "Z - ҲИСОБОТ (КАССА ЁПИЛИШИ)" if report_type.lower() == "z_report" else "X - ҲИСОБОТ (ОРАЛИҚ)"

    lines = []
    lines.append(double_sep)
    lines.append(_center_line(latin_to_cyrillic(restaurant_name).upper(), col_width))
    lines.append(_center_line(title, col_width))
    lines.append(sep)

    c_cyr = latin_to_cyrillic(cashier_name or "Кассир")
    lines.append(_pad_line(f"Смена: #{shift_number}", f"Кассир: {c_cyr}", col_width))
    if opened_at:
        lines.append(f"Очилган: {opened_at.strftime('%d.%m.%Y %H:%M')}")
    dt_close = closed_at or datetime.now()
    lines.append(f"Ҳисобот: {dt_close.strftime('%d.%m.%Y %H:%M')}")
    lines.append(sep)

    lines.append(_pad_line("Ёпилган буюртмалар:", str(total_orders), col_width))
    lines.append(sep)

    lines.append(_pad_line("Нақд пул (Наличные):", f"{total_cash:,.0f}".replace(",", " "), col_width))
    lines.append(_pad_line("Банк карта (Карта):", f"{total_card:,.0f}".replace(",", " "), col_width))
    lines.append(_pad_line("Click / Payme:", f"{total_click:,.0f}".replace(",", " "), col_width))
    lines.append(_pad_line("Насия / Қарз:", f"{total_debt:,.0f}".replace(",", " "), col_width))
    lines.append(sep)

    lines.append(_pad_line("Жами хизмат ҳақи:", f"{total_service_fee:,.0f}".replace(",", " "), col_width))
    lines.append(_pad_line("Официантлар улуши:", f"{total_waiter_earnings:,.0f}".replace(",", " "), col_width))
    lines.append(double_sep)

    lines.append(_pad_line("УМУМИЙ ТУШУМ:", f"{total_sales:,.0f}".replace(",", " "), col_width))
    lines.append(double_sep)

    if waiter_breakdown:
        lines.append("ОФИЦИАНТЛАР КЕСИМИДА:")
        for w in waiter_breakdown:
            w_name = latin_to_cyrillic(w.get("name", "Официант"))
            w_sales = w.get("sales", 0.0)
            w_earn = w.get("earning", 0.0)
            lines.append(f" • {w_name}:")
            lines.append(_pad_line(f"   Савдо: {w_sales:,.0f}".replace(",", " "), f"Улуш: {w_earn:,.0f}".replace(",", " "), col_width))
        lines.append(sep)

    return "\n".join(lines) + "\n\n\n"


# ─── Windows USB / Spooler To'g'ridan-to'g'ri Chop Etish ─────
import platform
import logging

logger = logging.getLogger("printer_service")


def get_installed_printers() -> List[str]:
    """Tizimga o'rnatilgan printerlar ro'yxatini olish (USB / Network / Virtual)"""
    if platform.system() != "Windows":
        return []
    try:
        import win32print
        printers = win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS)
        return [p[2] for p in printers]
    except Exception as e:
        logger.warning(f"Printerlarni aniqlashda xatolik: {e}")
        return []


import socket
import re

def is_ip_address(text: str) -> bool:
    """Tekshirish: kiritilgan matn IP manzilmi (masalan: 192.168.1.100 yoki 192.168.1.100:9100)"""
    if not text:
        return False
    clean = text.strip().split(":")[0]
    pattern = r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$"
    return bool(re.match(pattern, clean))


def print_to_network_printer(
    ip_or_host: str,
    port: int = 9100,
    raw_text: str = "",
    cut_paper: bool = True,
    codepage: int = DEFAULT_CODEPAGE,
    font_size: str = DEFAULT_FONT_SIZE,
) -> Dict[str, Any]:
    """
    Wi-Fi yoki Ethernet (LAN kabel) orqali ulangan Xprinterga
    to'g'ridan-to'g'ri TCP Port 9100 orqali chek chop etish.
    (Oshxonadagi uzoq masofali printerlar uchun eng qulay usul!)
    """
    host = ip_or_host.strip()
    if ":" in host:
        parts = host.split(":")
        host = parts[0]
        try:
            port = int(parts[1])
        except Exception:
            pass

    try:
        # Matnni ESC/POS baytlariga aylantirish (kod sahifasi bilan)
        payload = build_escpos_payload(raw_text, cut_paper=cut_paper,
                                       codepage=codepage, font_size=font_size)

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3.5)
        s.connect((host, port))
        s.sendall(payload)
        s.close()

        return {
            "success": True,
            "printer": f"LAN {host}:{port}",
            "message": f"Chek oshxona printeriga ({host}:{port}) tarmoq orqali muvaffaqiyatli yuborildi"
        }
    except Exception as e:
        logger.error(f"Tarmoq printeriga ({host}:{port}) ulanishda xatolik: {e}")
        return {
            "success": False,
            "error": f"Oshxona printeriga ({host}:{port}) ulanib bo'lmadi. Printer yoqilgani va Wi-Fi/kabelga ulangani tekshirilsin. Xato: {str(e)}"
        }


def print_to_windows_printer(
    raw_text: str,
    printer_name: Optional[str] = None,
    cut_paper: bool = True,
    codepage: int = DEFAULT_CODEPAGE,
    font_size: str = DEFAULT_FONT_SIZE,
) -> Dict[str, Any]:
    """
    USB, Windows Spooler yoki Tarmoq (LAN/Wi-Fi IP) orqali chop etish
    """
    target = (printer_name or "").strip()

    # Agar kiritilgan qiymat IP manzil bo'lsa -> Tarmoq orqali yuborish!
    if is_ip_address(target):
        return print_to_network_printer(target, raw_text=raw_text, cut_paper=cut_paper,
                                        codepage=codepage, font_size=font_size)

    if platform.system() != "Windows":
        return {"success": False, "error": "USB to'g'ridan-to'g'ri chop etish faqat Windows tizimida ishlaydi. Tarmoq printeri uchun IP manzil kiriting (masalan: 192.168.1.100)."}

    try:
        import win32print

        target = printer_name
        installed = get_installed_printers()

        if not target:
            # Xprinter yoki thermal printerni avtomatik qidirish
            for p in installed:
                p_lower = p.lower()
                if any(k in p_lower for k in ["xprinter", "xp-", "pos", "thermal", "58", "80", "receipt", "printer"]):
                    target = p
                    break

        if not target and installed:
            # Standart printerni olish
            try:
                target = win32print.GetDefaultPrinter()
            except Exception:
                target = installed[0]

        if not target:
            return {"success": False, "error": "Hech qanday printer topilmadi. Xprinter drayverini o'rnating."}

        # Matnni ESC/POS baytlariga aylantirish (kod sahifasi bilan)
        payload = build_escpos_payload(raw_text, cut_paper=cut_paper,
                                       codepage=codepage, font_size=font_size)

        hPrinter = win32print.OpenPrinter(target)
        try:
            hJob = win32print.StartDocPrinter(hPrinter, 1, ("RestAron_Receipt", None, "RAW"))
            try:
                win32print.StartPagePrinter(hPrinter)
                win32print.WritePrinter(hPrinter, payload)
                win32print.EndPagePrinter(hPrinter)
            finally:
                win32print.EndDocPrinter(hPrinter)
        finally:
            win32print.ClosePrinter(hPrinter)

        return {"success": True, "printer": target, "message": f"Chek '{target}' printeriga muvaffaqiyatli yuborildi"}
    except Exception as e:
        logger.error(f"Xprinter USB chop etishda xatolik: {e}")
        return {"success": False, "error": str(e)}


def scan_network_printers(port: int = 9100, timeout: float = 0.35) -> List[Dict[str, Any]]:
    """
    Lokal tarmoqda (x.x.x.1-254) ochiq 9100-portga ega qurilmalarni qidiradi.

    Termal (ESC/POS) printerlar deyarli har doim shu portda "RAW" chop
    etishni qabul qiladi. Shuning uchun bu usul LAN kabeli bilan ulangan
    printerning IP manzilini topishning eng oson yo'li -- foydalanuvchi
    router sozlamalariga kirmasdan, tugma bosib topadi.
    """
    import concurrent.futures

    # Serverning o'z IP manzilini aniqlaymiz
    try:
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        probe.connect(("8.8.8.8", 80))
        local_ip = probe.getsockname()[0]
        probe.close()
    except Exception:
        return []

    parts = local_ip.split(".")
    if len(parts) != 4:
        return []
    subnet = ".".join(parts[:3])

    def check(host_num: int):
        ip = f"{subnet}.{host_num}"
        if ip == local_ip:
            return None
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            if s.connect_ex((ip, port)) == 0:
                s.close()
                return {"ip": ip, "port": port}
            s.close()
        except Exception:
            pass
        return None

    found = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=120) as pool:
        for r in pool.map(check, range(1, 255)):
            if r:
                found.append(r)
    return found


def _send_raw_bytes(payload: bytes, target: str) -> Dict[str, Any]:
    """
    Tayyor ESC/POS baytlarni printerga yuboradi (USB nomi yoki LAN IP).
    Kod sahifasi sinovi kabi maxsus holatlar uchun.
    """
    if is_ip_address(target):
        host, port = target.strip(), 9100
        if ":" in host:
            host, _, prt = host.partition(":")
            try:
                port = int(prt)
            except Exception:
                pass
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(4.0)
            s.connect((host, port))
            s.sendall(payload)
            s.close()
            return {"success": True, "message": f"{host}:{port} ga yuborildi"}
        except Exception as e:
            return {"success": False, "error": f"{host}:{port} ga ulanib bo'lmadi: {e}"}

    if platform.system() != "Windows":
        return {"success": False, "error": "USB chop etish faqat Windows'da ishlaydi"}
    try:
        import win32print
        h = win32print.OpenPrinter(target)
        try:
            job = win32print.StartDocPrinter(h, 1, ("RestAron_CodepageTest", None, "RAW"))
            try:
                win32print.StartPagePrinter(h)
                win32print.WritePrinter(h, payload)
                win32print.EndPagePrinter(h)
            finally:
                win32print.EndDocPrinter(h)
        finally:
            win32print.ClosePrinter(h)
        return {"success": True, "message": f"'{target}' printeriga yuborildi"}
    except Exception as e:
        return {"success": False, "error": str(e)}
