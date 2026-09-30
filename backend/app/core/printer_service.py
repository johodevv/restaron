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


def format_kitchen_ticket(
    hall_name: Optional[str],
    room_name: Optional[str],
    table_number: Any,
    waiter_name: str,
    items: List[Dict[str, Any]],
    kitchen_note: Optional[str] = None,
    order_time: Optional[datetime] = None,
    paper_width: int = 80,
) -> str:
    """
    Oshxona / Bar begunogi (Runner ticket)
    Namuna (Rasm 1):
      Балкон
      Хона
      N# 30
      Выполнена: Зафарбек
      29.09.2026 | 20:09
      ------------------------------------------
      Кола1,5                                 1
      Фанта 1,5                               1
    """
    col_width = 42 if paper_width >= 80 else 32
    sep = "-" * col_width
    dt = order_time or datetime.now()
    dt_str = dt.strftime("%d.%m.%Y | %H:%M")

    lines = []
    if hall_name:
        lines.append(_center_line(hall_name.upper(), col_width))
    if room_name and room_name != hall_name:
        lines.append(str(room_name))
    lines.append(f"N# {table_number}")
    lines.append(f"Выполнена: {waiter_name or 'Официант'}")
    lines.append(dt_str)
    lines.append(sep)

    for item in items:
        name = item.get("name") or "Taom"
        qty = item.get("quantity") or 1
        lines.append(_pad_line(name, str(qty), col_width))
        if item.get("note"):
            lines.append(f"  * {item['note']}")

    lines.append(sep)
    if kitchen_note:
        lines.append(f"Izoh: {kitchen_note}")
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
    created_at: Optional[datetime] = None,
    paper_width: int = 80,
) -> str:
    """
    Mijoz hisob cheki (Pre-check / Bill)
    Namuna (Rasm 1 o'ng tomoni):
      Стол: Terasa-11
      Кассир/Официант: Зафарбек
      Блюда:
      1. Сомса        1 x 15 000        15 000
      ...
      Итого:                           217 000
      Обслуживание (12%):               26 040
      ИТОГО К ОПЛАТЕ:                  243 040
    """
    col_width = 42 if paper_width >= 80 else 32
    sep = "-" * col_width
    double_sep = "=" * col_width
    dt = created_at or datetime.now()
    dt_str = dt.strftime("%d.%m.%Y %H:%M")

    lines = []
    lines.append(double_sep)
    lines.append(_center_line(restaurant_name.upper(), col_width))
    if address:
        lines.append(_center_line(address, col_width))
    if phone:
        lines.append(_center_line(f"Tel: {phone}", col_width))
    lines.append(sep)

    lines.append(_pad_line(f"Стол: {table_name}", f"Чек: {order_number}", col_width))
    lines.append(_pad_line(f"Официант: {waiter_name or 'Xodim'}", dt_str, col_width))
    lines.append(sep)
    lines.append("Блюда:")

    for idx, it in enumerate(items, 1):
        name = it.get("name") or "Taom"
        qty = it.get("quantity") or 1
        unit_price = it.get("unit_price") or it.get("price") or 0.0
        line_total = it.get("total_price") or (qty * unit_price)

        # 1. Somsa
        lines.append(f"{idx}. {name}")
        # 1 x 15 000          15 000
        calc_str = f"   {qty} x {unit_price:,.0f}".replace(",", " ")
        tot_str = f"{line_total:,.0f}".replace(",", " ")
        lines.append(_pad_line(calc_str, tot_str, col_width))

    lines.append(sep)
    sub_str = f"{subtotal:,.0f}".replace(",", " ")
    lines.append(_pad_line("Итого:", sub_str, col_width))

    if service_fee_percent > 0:
        fee_title = f"Обслуживание ({service_fee_percent:.0f}%):"
        fee_str = f"{service_fee_amount:,.0f}".replace(",", " ")
        lines.append(_pad_line(fee_title, fee_str, col_width))

    if discount > 0:
        disc_str = f"-{discount:,.0f}".replace(",", " ")
        lines.append(_pad_line("Скидка:", disc_str, col_width))

    lines.append(double_sep)
    total_str = f"{total:,.0f}".replace(",", " ")
    lines.append(_pad_line("ИТОГО К ОПЛАТЕ:", total_str, col_width))
    lines.append(double_sep)

    if receipt_note:
        lines.append(f"Izoh: {receipt_note}")
        lines.append(sep)

    msg = footer_text or "Tashrifingiz uchun rahmat!"
    lines.append(_center_line(msg, col_width))

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
) -> str:
    """
    X-Report (oraliq hisobot) yoki Z-Report (kassani yopish)
    """
    col_width = 42 if paper_width >= 80 else 32
    sep = "-" * col_width
    double_sep = "=" * col_width

    title = "Z - HISOBOT (KASSA YOPILISHI)" if report_type.lower() == "z_report" else "X - HISOBOT (ORALIQ HISOBOT)"

    lines = []
    lines.append(double_sep)
    lines.append(_center_line(restaurant_name.upper(), col_width))
    lines.append(_center_line(title, col_width))
    lines.append(sep)

    lines.append(_pad_line(f"Smena: #{shift_number}", f"Kassir: {cashier_name}", col_width))
    if opened_at:
        lines.append(f"Ochilgan: {opened_at.strftime('%d.%m.%Y %H:%M')}")
    dt_close = closed_at or datetime.now()
    lines.append(f"Hisobot:  {dt_close.strftime('%d.%m.%Y %H:%M')}")
    lines.append(sep)

    lines.append(_pad_line("Yopilgan buyurtmalar:", str(total_orders), col_width))
    lines.append(sep)

    lines.append(_pad_line("Naqd pul (Наличные):", f"{total_cash:,.0f}".replace(",", " "), col_width))
    lines.append(_pad_line("Karta (Карта):", f"{total_card:,.0f}".replace(",", " "), col_width))
    lines.append(_pad_line("Click / Payme:", f"{total_click:,.0f}".replace(",", " "), col_width))
    lines.append(_pad_line("Nasiya / Qarz:", f"{total_debt:,.0f}".replace(",", " "), col_width))
    lines.append(sep)

    lines.append(_pad_line("Jami xizmat haqi:", f"{total_service_fee:,.0f}".replace(",", " "), col_width))
    lines.append(_pad_line("Ofitsiantlar ulushi:", f"{total_waiter_earnings:,.0f}".replace(",", " "), col_width))
    lines.append(double_sep)

    lines.append(_pad_line("UMUMIY TUSHUM:", f"{total_sales:,.0f}".replace(",", " "), col_width))
    lines.append(double_sep)

    if waiter_breakdown:
        lines.append("OFITSIANTLAR KESIMIDA:")
        for w in waiter_breakdown:
            w_name = w.get("name", "Ofitsiant")
            w_sales = w.get("sales", 0.0)
            w_earn = w.get("earning", 0.0)
            lines.append(f" • {w_name}:")
            lines.append(_pad_line(f"   Savdo: {w_sales:,.0f}".replace(",", " "), f"Ulush: {w_earn:,.0f}".replace(",", " "), col_width))
        lines.append(sep)

    return "\n".join(lines) + "\n\n\n"
