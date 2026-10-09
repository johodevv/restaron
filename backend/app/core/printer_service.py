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


def _wrap_words(text: str, width: int, indent: str = "") -> List[str]:
    """Matnni so'zlar bo'yicha bir nechta qatorga bo'ladi.

    Katta shriftda qator 24 (yoki 16) belgiga tushadi, uzun taom nomi
    esa kesilib qolardi: "Шашлик (қўй гўш". Endi nom to'liq chiqadi.
    """
    text = str(text).strip()
    width = max(4, int(width))

    # Narx "120 000" ko'rinishida yoziladi — minglik ajratgich BO'SH JOY.
    # Shuning uchun oddiy so'z bo'yicha bo'lish raqamni ikkiga uzib
    # qo'yardi ("120" va "000 204 000" — mijoz chalkashadi). Raqam
    # guruhlarini bitta bo'linmas so'z qilib yig'amiz.
    words: List[str] = []
    for word in text.split():
        if (words and len(word) == 3 and word.isdigit()
                and words[-1] and words[-1][-1].isdigit()):
            words[-1] = f"{words[-1]} {word}"
        else:
            words.append(word)

    out: List[str] = []
    cur = ""
    for word in words or [""]:
        cand = word if not cur else f"{cur} {word}"
        if len(cand) <= width:
            cur = cand
            continue
        if cur:
            out.append(cur)
        # Bitta so'zning o'zi sig'masa — bo'laklab tashlaymiz.
        while len(word) > width:
            out.append(word[:width])
            word = word[width:]
        cur = word
    if cur or not out:
        out.append(cur)
    if not indent:
        return out
    return [out[0]] + [f"{indent}{ln}"[:width] for ln in out[1:]]


def _name_amount_block(name: str, right: str, width: int) -> List[str]:
    """Taom nomi + o'ngdagi qiymat (soni / summasi).

    Bir qatorga sig'sa — bitta qator. Sig'masa nom so'zlar bo'yicha
    bo'linadi va qiymat oxirgi qatorning o'ng chetiga tekislanadi
    (joy bo'lmasa alohida qatorga tushadi). Hech narsa kesilmaydi.
    """
    name = str(name).strip()
    right = str(right).strip()
    if len(name) + 1 + len(right) <= width:
        return [_pad_line(name, right, width)]

    parts = _wrap_words(name, width)
    last = parts[-1]
    if len(last) + 1 + len(right) <= width:
        parts[-1] = _pad_line(last, right, width)
    else:
        parts.append(right.rjust(width))
    return parts


def fmt_percent(value: float) -> str:
    """Foizni chekda chiroyli yozish: 12 -> "12", 7.5 -> "7.5".

    Ilgari ".0f" ishlatilgandi va 7.5% chekda "8%" bo'lib chiqardi —
    mijoz 8% deb o'qib, aslida 7.5% to'lardi.
    """
    v = float(value or 0)
    if abs(v - round(v)) < 0.005:
        return f"{round(v):d}"
    return f"{v:.2f}".rstrip("0").rstrip(".")


def _amount_line(label: str, amount: str, width: int = 42) -> str:
    """Nomi va summasini bir qatorga joylashtiradi.

    Katta shriftda qator tor bo'ladi (24 yoki 16 belgi) va nom bilan
    summa bir-biriga tiqilib, nom yarmida kesilib ketadi. Sig'masa
    nomni alohida qatorga chiqaramiz, summani esa o'ng chetga
    tekislaymiz — hech qanday raqam yo'qolmaydi.
    """
    label = str(label)
    amount = str(amount)
    if len(label) + 1 + len(amount) <= width:
        return _pad_line(label, amount, width)

    # Sig'masa: nomni so'zlar bo'yicha bo'lamiz va summani o'ng chetga
    # chiqaramiz. Summa HECH QACHON kesilmaydi — chekda pul miqdori
    # yarmida uzilib qolsa mijoz bilan janjal chiqadi.
    indent = label[:len(label) - len(label.lstrip())]
    inner = max(4, width - len(indent))
    parts = [f"{indent}{ln}" for ln in _wrap_words(label.strip(), inner)]
    last = parts[-1]
    if len(last) + 1 + len(amount) <= width:
        parts[-1] = _pad_line(last, amount, width)
    else:
        parts.append(amount.rjust(width) if len(amount) <= width else amount)
    return "\n".join(parts)


def _center_line(text: str, width: int = 42) -> str:
    """Matnni markazga joylashtirish.

    Sig'masa — so'zlar bo'yicha bir nechta qatorga bo'linadi. Ilgari
    matn shunchaki KESILARDI: katta shriftda (24 ustun) oshxona nomi
    "1-ОШХОНА (ҚОЗОН ТАОМ" bo'lib yarmida uzilib qolardi.
    """
    text = str(text).strip()
    if len(text) <= width:
        pad = (width - len(text)) // 2
        return f"{' ' * pad}{text}"

    lines = []
    current = ""
    for word in text.split():
        if not current:
            current = word[:width]
        elif len(current) + 1 + len(word) <= width:
            current = f"{current} {word}"
        else:
            lines.append(current)
            current = word[:width]
    if current:
        lines.append(current)

    return "\n".join(
        f"{' ' * ((width - len(ln)) // 2)}{ln}" for ln in lines
    )


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

# ─── Chek shrifti o'lchami ─────────────────────────────────────────────
#
# GS ! n : yuqori 4 bit = KENGLIK ko'paytirgichi, quyi 4 bit = BALANDLIK
# (0 = 1x, 1 = 2x, 2 = 3x ...).
#
# MUHIM — nega "faqat bo'yi 2 barobar" (eski "katta") XIRA chiqadi:
# termal printer harfni bo'yiga cho'zganda har nuqta qatorini ikki marta
# bosadi, lekin harf chiziqlarining ENI o'sha-o'sha 1 nuqta qolib ketadi.
# Natijada harflar cho'zilgan, ingichka va xira ko'rinadi. Shuning uchun
# harf eni ham, bo'yi ham BIRGA kattalashtiriladi: chiziqlar ham 2 nuqta
# bo'ladi va yozuv to'q, qalin, aniq chiqadi.
#
#   normal      — 1x1  (80mm da 48 belgi)  — eng kichik
#   baland      — 1x2  (48 belgi)          — eski "katta" (xira chiqishi mumkin)
#   keng        — 2x1  (24 belgi)          — eni 2x, bo'yi o'sha-o'sha: eng TO'Q
#   katta       — 2x2  (24 belgi)          — SUKUT: katta va to'q
#   juda_katta  — 3x3  (16 belgi)          — eng katta
FONT_SIZES = {
    "normal":     {"gs": 0x00, "w": 1, "h": 1, "label": "1x1"},
    "baland":     {"gs": 0x01, "w": 1, "h": 2, "label": "1x2"},
    "keng":       {"gs": 0x10, "w": 2, "h": 1, "label": "2x1"},
    "katta":      {"gs": 0x11, "w": 2, "h": 2, "label": "2x2"},
    "juda_katta": {"gs": 0x22, "w": 3, "h": 3, "label": "3x3"},
}
DEFAULT_FONT_SIZE = "katta"

# Eski sozlamalar bilan moslik: ilgari "katta" faqat bo'yi 2x degani edi.
FONT_SIZE_ALIASES = {
    "kichik": "normal",
    "oddiy": "normal",
    "standart": "normal",
    "balandroq": "baland",
    "katta_baland": "baland",
    "eng_katta": "juda_katta",
}


def _font_spec(font_size: Optional[str]) -> dict:
    key = (font_size or "").strip().lower()
    key = FONT_SIZE_ALIASES.get(key, key)
    return FONT_SIZES.get(key, FONT_SIZES[DEFAULT_FONT_SIZE])


# ─── Harflar orasidagi masofa (ESC SP n) ──────────────────────────────
#
# Termal printerda harflar bir-biriga yopishib chiqadi va qari odamga
# o'qish qiyin bo'ladi. `ESC SP n` har harfning O'NG tomoniga n nuqta
# bo'sh joy qo'shadi (standart ESC/POS buyrug'i).
#
# MUHIM: bo'sh joy qo'shilsa bir qatorga sig'adigan belgilar soni
# kamayadi, shuning uchun `receipt_columns` buni hisobga oladi.
DEFAULT_CHAR_SPACING = 1      # nuqta (0 = yopishib turadi)
MAX_CHAR_SPACING = 6

# ─── Qatorlar orasidagi masofa (ESC 3 n) ──────────────────────────────
#
# "zich" — printer o'zi hal qiladi (hech narsa yuborilmaydi)
# "oddiy" / "keng" / "juda_keng" — harf balandligiga qarab hisoblanadi
LINE_SPACINGS = {
    "zich": None,
    "oddiy": 6,
    "keng": 14,
    "juda_keng": 24,
}
DEFAULT_LINE_SPACING = "oddiy"

# Font A balandligi va kengligi (nuqtada), 203 dpi li printerlarda
FONT_A_W = 12
FONT_A_H = 24

# 80mm qog'ozda bosiladigan maydon 72mm = 576 nuqta, 58mm da 48mm = 384
PRINT_DOTS_80 = 576
PRINT_DOTS_58 = 384


def _clamp_char_spacing(value: Optional[int]) -> int:
    try:
        n = int(value if value is not None else DEFAULT_CHAR_SPACING)
    except (TypeError, ValueError):
        n = DEFAULT_CHAR_SPACING
    return max(0, min(MAX_CHAR_SPACING, n))


def _line_spacing_dots(line_spacing: Optional[str], height_mult: int) -> Optional[int]:
    """ESC 3 n uchun nuqta soni. None — printer o'zi hal qiladi."""
    key = (line_spacing or DEFAULT_LINE_SPACING).strip().lower()
    extra = LINE_SPACINGS.get(key, LINE_SPACINGS[DEFAULT_LINE_SPACING])
    if extra is None:
        return None
    return max(1, min(255, FONT_A_H * max(1, height_mult) + extra))


def build_escpos_payload(raw_text: str, cut_paper: bool = True,
                         codepage: int = DEFAULT_CODEPAGE,
                         font_size: str = DEFAULT_FONT_SIZE,
                         char_spacing: Optional[int] = None,
                         line_spacing: Optional[str] = None) -> bytes:
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

    # ESC E 1 — qalin (bold) matn, ESC G 1 — ikki marta bosish
    # (double-strike). Ikkisi birga chekni ancha TO'Q qiladi: termal chek
    # vaqt o'tishi bilan xiralashadi, qalin yozuvni esa keksa odamlar ham
    # bemalol o'qiydi. Ikkisi ham standart ESC/POS buyrug'i, shuning uchun
    # qo'llab-quvvatlanmasa ham printer ularni shunchaki e'tiborsiz
    # qoldiradi (qog'ozga begona belgi chiqmaydi).
    esc_bold = b"\x1b\x45\x01" + b"\x1b\x47\x01"

    # ESC SP n — har harfning o'ng tomoniga n nuqta bo'sh joy.
    # Harflar bir-biriga yopishib chiqmasin, keksa odam ham ajrata olsin.
    spacing = _clamp_char_spacing(char_spacing)
    esc_char_sp = b"\x1b\x20" + bytes([spacing])

    # ESC 3 n — qatorlar orasidagi masofa. "zich" tanlansa printer
    # o'zining sukutdagi oralig'ini ishlatadi.
    spec = _font_spec(font_size)
    ls_dots = _line_spacing_dots(line_spacing, spec.get("h", 1))
    esc_line_sp = b"\x1b\x33" + bytes([ls_dots]) if ls_dots is not None else b""

    payload = (ESC_INIT + FS_KANJI_OFF + FS_KANJI_OFF2
               + esc_codepage + ESC_FONT_A + gs_size + esc_bold
               + esc_char_sp + esc_line_sp + body)
    if cut_paper:
        payload += ESC_CUT
    return payload


def receipt_columns(paper_width: int, font_size: str = DEFAULT_FONT_SIZE,
                    char_spacing: Optional[int] = None) -> int:
    """
    Termal printer uchun bir qatordagi belgilar soni.

    203 dpi li ESC/POS printerlarda Font A kengligi 12 nuqta = 1.5 mm,
    bosiladigan maydon 80mm qog'ozda 576 nuqta (72mm), 58mm da 384.

    Bitta belgining egallaydigan joyi:
        (12 + harflar_orasi) x kenglik_ko'paytirgichi

    MUHIM: harflar orasiga bo'sh joy qo'shilsa (ESC SP) bitta belgi
    kengroq bo'ladi va qatorga kamroq belgi sig'adi. Buni hisobga
    olmasak matn qog'ozdan chiqib, chek buzilib ketardi.
    """
    dots = PRINT_DOTS_80 if paper_width >= 80 else PRINT_DOTS_58
    spacing = _clamp_char_spacing(char_spacing)
    cell = (FONT_A_W + spacing) * max(1, _font_spec(font_size)["w"])
    return max(10, dots // cell)


def printer_options(settings: Any) -> Dict[str, Any]:
    """Restoran sozlamalaridan chop etish parametrlarini yig'ib beradi.

    Hamma joyda bir xil bo'lishi uchun (oshxona begunogi, mijoz cheki,
    smena hisoboti, sinov cheki) — bitta manba.
    """
    cs = getattr(settings, "printer_char_spacing", None)
    return {
        "codepage": getattr(settings, "printer_codepage", None) or DEFAULT_CODEPAGE,
        "font_size": getattr(settings, "printer_font_size", None) or DEFAULT_FONT_SIZE,
        "char_spacing": _clamp_char_spacing(cs),
        "line_spacing": getattr(settings, "printer_line_spacing", None) or DEFAULT_LINE_SPACING,
    }


def merge_receipt_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Bir xil qatorlarni birlashtiradi.

    Mijoz ikki marta non buyurtma qilsa chekda "1 non" ikki qator bo'lib
    emas, "2 non" bo'lib bitta qatorda chiqishi kerak.

    Taom nomi, hajmi (1.5 L), og'irligi va dona narxi bir xil bo'lsa
    qatorlar qo'shiladi. Tortiladigan taomlar (har baliq o'z og'irligida)
    birlashtirilmaydi.
    """
    merged: List[Dict[str, Any]] = []
    index: Dict[tuple, Dict[str, Any]] = {}

    for it in items or []:
        if it.get("is_weighted"):
            merged.append(dict(it))
            continue

        key = (
            it.get("name_cyrillic") or it.get("name") or "",
            (it.get("size") or "").strip(),
            (it.get("note") or "").strip(),
            round(float(it.get("unit_price") or it.get("price") or 0.0), 2),
        )
        row = index.get(key)
        if row is None:
            row = dict(it)
            index[key] = row
            merged.append(row)
        else:
            row["quantity"] = (row.get("quantity") or 0) + (it.get("quantity") or 0)
            if it.get("total_price") is not None:
                row["total_price"] = (row.get("total_price") or 0.0) + it["total_price"]

    return merged


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
    char_spacing: Optional[int] = None,
    is_reprint: bool = False,
) -> str:
    """
    Oshxona / Bar begunogi (Runner ticket) — To'liq Kirill alifbosida
    """
    col_width = receipt_columns(paper_width, font_size, char_spacing)
    sep = "-" * col_width
    dt = order_time or datetime.now()
    dt_str = dt.strftime("%d.%m.%Y | %H:%M")

    lines = []
    # Oshxona stansiyasi sarlavhasi
    st_title = station_title or "ОШХОНА БЕГУНОГИ"
    lines.append(_center_line(f"*** {latin_to_cyrillic(st_title).upper()} ***", col_width))

    # Takroriy begunok: oshpaz buni YANGI buyurtma deb o'ylamasligi kerak.
    if is_reprint:
        lines.append(sep)
        lines.append(_center_line("!!! ТАКРОР !!!", col_width))
        lines.append(_center_line("ЯНГИ БУЮРТМА ЭМАС", col_width))
        lines.append(sep)

    # Zal / Xona nomi
    zal = hall_name or room_name or "Зал"
    lines.append(_center_line(latin_to_cyrillic(zal).upper(), col_width))
    if room_name and room_name != hall_name:
        lines.append(_center_line(latin_to_cyrillic(room_name), col_width))

    # Stol va Ofitsiant. Tor chekda (katta shrift) qatorlar so'zlar
    # bo'yicha bo'linadi — printer o'zi so'z o'rtasidan uzib tashlamasin.
    lines.extend(_wrap_words(f"Стол: № {table_number}", col_width, indent="  "))
    waiter_cyr = latin_to_cyrillic(waiter_name or 'Официант')
    lines.extend(_wrap_words(f"Официант: {waiter_cyr}", col_width, indent="  "))
    if len(f"Вақт: {dt_str}") <= col_width:
        lines.append(f"Вақт: {dt_str}")
    else:
        # "Вақт: 08.10.2026 | 05:20" — tor chekda sana va soat alohida.
        lines.append("Вақт:")
        lines.extend(_wrap_words(dt_str.replace("|", " "), col_width, indent="  "))
    lines.append(sep)

    lines.append(_pad_line("ТАОМ", "СОНИ", col_width))
    lines.append(sep)

    for item in merge_receipt_items(items):
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
                lines.extend(_name_amount_block(name, f"{wt:g} {unit_cyr}", col_width))
            elif item.get("manual_price") is not None:
                # Ofitsiant summani o'zi yozgan — demak taom allaqachon
                # tortilgan/o'lchangan, oshxonaga "ТОРТИЛСИН!" chiqmasin.
                lines.extend(_name_amount_block(name, f"{qty} та", col_width))
            else:
                lines.extend(_name_amount_block(name, "ТОРТИЛСИН!", col_width))
            continue

        lines.extend(_name_amount_block(name, f"{qty} та", col_width))
        if item.get("note"):
            note_cyr = latin_to_cyrillic(item['note'])
            lines.extend(_wrap_words(f"  * {note_cyr}", col_width, indent="    "))

    lines.append(sep)
    if kitchen_note:
        note_str = latin_to_cyrillic(kitchen_note)
        lines.extend(_wrap_words(f"Изоҳ: {note_str}", col_width, indent="  "))
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
    char_spacing: Optional[int] = None,
) -> str:
    """
    Mijoz hisob cheki (Pre-check / Bill) — To'liq Kirill alifbosida
    """
    col_width = receipt_columns(paper_width, font_size, char_spacing)
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
    w_cyr = latin_to_cyrillic(waiter_name or 'Ходим')
    stol_s = f"Стол: {tbl_cyr}"
    chek_s = f"Чек: №{order_number}"
    ofi_s = f"Официант: {w_cyr}"

    # Katta shriftda qator kengligi 24 ga tushadi — ikkita yozuvni bitta
    # qatorga tiqishtirsak, ikkalasi ham kesilib qoladi ("Стол: Тер").
    # Shuning uchun tor chekda har birini alohida qatorga chiqaramiz.
    if col_width < 40 or len(stol_s) + len(chek_s) + 1 > col_width:
        lines.extend(_wrap_words(stol_s, col_width, indent="  "))
        lines.extend(_wrap_words(chek_s, col_width, indent="  "))
    else:
        lines.append(_pad_line(stol_s, chek_s, col_width))

    if col_width < 40 or len(ofi_s) + len(dt_str) + 1 > col_width:
        lines.extend(_wrap_words(ofi_s, col_width, indent="  "))
        lines.extend(_wrap_words(dt_str, col_width, indent="  "))
    else:
        lines.append(_pad_line(ofi_s, dt_str, col_width))
    lines.append(sep)
    lines.append("Таомлар:")

    for idx, it in enumerate(merge_receipt_items(items), 1):
        raw_name = it.get("name_cyrillic") or it.get("name") or "Таом"
        name = latin_to_cyrillic(raw_name)
        size = (it.get("size") or "").strip()
        if size:
            name = f"{name} [{latin_to_cyrillic(size)}]"
        qty = it.get("quantity") or 1
        unit_price = it.get("unit_price") or it.get("price") or 0.0
        line_total = it.get("total_price") or (qty * unit_price)

        lines.extend(_wrap_words(f"{idx}. {name}", col_width, indent="   "))

        # Tortiladigan taom hali narxlanmagan bo'lsa narx YOZILMAYDI:
        # ilgari "1 x 120 000" deb 1 kg narxi chiqib ketardi va mijoz
        # hali aniqlanmagan summani ko'rardi.
        if (it.get("is_weighted") and not it.get("weight")
                and it.get("manual_price") is None):
            unit_cyr = latin_to_cyrillic(it.get("unit") or "kg")
            lines.append(_amount_line(f"   1 {unit_cyr} = {unit_price:,.0f}".replace(",", " "),
                                      "ТОРТИЛМАГАН" if col_width >= 12 else "ТОРТИЛМ.",
                                      col_width))
            continue

        tot_str = f"{line_total:,.0f}".replace(",", " ")

        # Tortiladigan taomda hisob "og'irlik x 1 kg narxi" ko'rinishida
        # yoziladi — mijoz nechchi kg olganini va nega shuncha pul
        # ekanini chekning o'zidan ko'radi.
        wt = it.get("weight")
        manual = it.get("manual_price")
        if it.get("is_weighted") and manual is not None:
            # Ofitsiant summani o'zi yozgan. Og'irlik ham kiritilgan
            # bo'lsa uni ko'rsatamiz, aks holda faqat summa chiqadi —
            # mijoz "1 kg narxi x soni" degan noto'g'ri hisobni ko'rmaydi.
            if wt:
                unit_cyr = latin_to_cyrillic(it.get("unit") or "kg")
                calc_str = f"   {wt:g} {unit_cyr}"
            else:
                calc_str = "   Нарх:"
        elif it.get("is_weighted") and wt:
            unit_cyr = latin_to_cyrillic(it.get("unit") or "kg")
            calc_str = f"   {wt:g} {unit_cyr} x {unit_price:,.0f}".replace(",", " ")
            if qty > 1:
                calc_str = f"   {qty} x {wt:g} {unit_cyr} x {unit_price:,.0f}".replace(",", " ")
        else:
            calc_str = f"   {qty} x {unit_price:,.0f}".replace(",", " ")
        lines.append(_amount_line(calc_str, tot_str, col_width))

    lines.append(sep)
    # Katta shriftda qator tor (24 yoki 16 belgi) — uzun ruscha-o'zbekcha
    # izohlar sig'masligi uchun qisqa yozuvlardan foydalanamiz.
    narrow = col_width < 32
    sub_str = f"{subtotal:,.0f}".replace(",", " ")
    lines.append(_amount_line("Жами:" if narrow else "Жами (Итого):", sub_str, col_width))

    if service_fee_percent > 0:
        # MIJOZ CHEKIDA xizmat haqining SUMMASI yozilmaydi — faqat
        # foizi ko'rinadi ("Хизмат ҳақи: 12%"). Summa baribir umumiy
        # to'lovga qo'shilgan. Ichki hisobotlarda (smena hisoboti) esa
        # summa to'liq chiqadi.
        if col_width < 20:
            fee_title = "Хизмат:"
        elif narrow:
            fee_title = "Хизмат ҳақи:"
        else:
            fee_title = "Хизмат ҳақи (Обслуж.):"
        lines.append(_amount_line(
            fee_title, f"{fmt_percent(service_fee_percent)}%", col_width))

    if discount > 0:
        disc_str = f"-{discount:,.0f}".replace(",", " ")
        lines.append(_amount_line("Чегирма:" if narrow else "Чегирма (Скидка):",
                                  disc_str, col_width))

    lines.append(double_sep)
    total_str = f"{total:,.0f}".replace(",", " ")
    lines.append(_amount_line("ЖАМИ:" if narrow else "ЖАМИ ТЎЛОВ:", total_str, col_width))
    lines.append(double_sep)

    if receipt_note:
        lines.extend(_wrap_words(f"Изоҳ: {latin_to_cyrillic(receipt_note)}",
                                 col_width, indent="  "))
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
    char_spacing: Optional[int] = None,
) -> str:
    """
    X-Report (oraliq hisobot) yoki Z-Report (kassani yopish) — To'liq Kirill alifbosida
    """
    col_width = receipt_columns(paper_width, font_size, char_spacing)
    sep = "-" * col_width
    double_sep = "=" * col_width

    title = "Z - ҲИСОБОТ (КАССА ЁПИЛИШИ)" if report_type.lower() == "z_report" else "X - ҲИСОБОТ (ОРАЛИҚ)"

    lines = []
    lines.append(double_sep)
    lines.append(_center_line(latin_to_cyrillic(restaurant_name).upper(), col_width))
    lines.append(_center_line(title, col_width))
    lines.append(sep)

    c_cyr = latin_to_cyrillic(cashier_name or "Кассир")
    smena_s = f"Смена: #{shift_number}"
    kassir_s = f"Кассир: {c_cyr}"
    if len(smena_s) + 1 + len(kassir_s) <= col_width:
        lines.append(_pad_line(smena_s, kassir_s, col_width))
    else:
        lines.extend(_wrap_words(smena_s, col_width, indent="  "))
        lines.extend(_wrap_words(kassir_s, col_width, indent="  "))
    if opened_at:
        lines.extend(_wrap_words(f"Очилган: {opened_at.strftime('%d.%m.%Y %H:%M')}",
                                 col_width, indent="  "))
    dt_close = closed_at or datetime.now()
    lines.extend(_wrap_words(f"Ҳисобот: {dt_close.strftime('%d.%m.%Y %H:%M')}",
                             col_width, indent="  "))
    lines.append(sep)

    narrow = col_width < 32
    lines.append(_amount_line("Буюртмалар:" if narrow else "Ёпилган буюртмалар:",
                              str(total_orders), col_width))
    lines.append(sep)

    lines.append(_amount_line("Нақд:" if narrow else "Нақд пул (Наличные):",
                              f"{total_cash:,.0f}".replace(",", " "), col_width))
    lines.append(_amount_line("Карта:" if narrow else "Банк карта (Карта):",
                              f"{total_card:,.0f}".replace(",", " "), col_width))
    lines.append(_amount_line("Click/Payme:", f"{total_click:,.0f}".replace(",", " "), col_width))
    lines.append(_amount_line("Насия:" if narrow else "Насия / Қарз:",
                              f"{total_debt:,.0f}".replace(",", " "), col_width))
    lines.append(sep)

    lines.append(_amount_line("Хизмат ҳақи:" if narrow else "Жами хизмат ҳақи:",
                              f"{total_service_fee:,.0f}".replace(",", " "), col_width))
    lines.append(_amount_line("Улушлар:" if narrow else "Официантлар улуши:",
                              f"{total_waiter_earnings:,.0f}".replace(",", " "), col_width))
    lines.append(double_sep)

    lines.append(_amount_line("УМУМИЙ:" if narrow else "УМУМИЙ ТУШУМ:",
                              f"{total_sales:,.0f}".replace(",", " "), col_width))
    lines.append(double_sep)

    if waiter_breakdown:
        if col_width < 24:
            lines.append("ОФИЦИАНТ:")
        elif col_width < 32:
            lines.append("ОФИЦИАНТЛАР:")
        else:
            lines.append("ОФИЦИАНТЛАР КЕСИМИДА:")
        for w in waiter_breakdown:
            w_name = latin_to_cyrillic(w.get("name", "Официант"))
            w_sales = w.get("sales", 0.0)
            w_earn = w.get("earning", 0.0)
            lines.extend(_wrap_words(f" * {w_name}:", col_width, indent="   "))
            sav = f"{w_sales:,.0f}".replace(",", " ")
            ulu = f"{w_earn:,.0f}".replace(",", " ")
            if col_width < 24:
                # Juda tor chekda "Савдо" va "Улуш" alohida qatorda.
                lines.append(_amount_line("  Савдо:", sav, col_width))
                lines.append(_amount_line("  Улуш:", ulu, col_width))
            else:
                lines.append(_amount_line(f"   Савдо: {sav}", f"Улуш: {ulu}", col_width))
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
    char_spacing: Optional[int] = None,
    line_spacing: Optional[str] = None,
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
                                       codepage=codepage, font_size=font_size,
                                       char_spacing=char_spacing, line_spacing=line_spacing)

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
    char_spacing: Optional[int] = None,
    line_spacing: Optional[str] = None,
) -> Dict[str, Any]:
    """
    USB, Windows Spooler yoki Tarmoq (LAN/Wi-Fi IP) orqali chop etish
    """
    target = (printer_name or "").strip()

    # Agar kiritilgan qiymat IP manzil bo'lsa -> Tarmoq orqali yuborish!
    if is_ip_address(target):
        return print_to_network_printer(target, raw_text=raw_text, cut_paper=cut_paper,
                                        codepage=codepage, font_size=font_size,
                                        char_spacing=char_spacing, line_spacing=line_spacing)

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
                                       codepage=codepage, font_size=font_size,
                                       char_spacing=char_spacing, line_spacing=line_spacing)

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
