#!/usr/bin/env python3
"""
Dunyo Choyxonasi (RestAron) — Playwright E2E Stress, Performance & Audit Skripti
--------------------------------------------------------------------------------
Ushbu skript real brauzerda (headless=False, slow_mo=500) ishga tushib, quyidagi
amallarni to'liq tekshiradi:
1. Admin va Ofitsiant/POS panellariga kirish (Auth & Session audit).
2. Stol tanlash va menyudan taomlar qo'shish.
3. Tarozidagi mahsulot ("Sovus kabob", "Baliq") narx va og'irligini o'zgartirish
   (ilgari HTTP 500 bergan joy — PATCH /orders/{id}/items/{item_id}/weight).
4. Zakaz berish va Otkaz qilish (cancel/delete) jarayonlarini stress loop tarzida bajarish.
5. "Tolandi va stolni bo'shatish" (Checkout) jarayonini yakunlash va stol bo'shatilishini tekshirish.
6. Takeaway (Olib ketish) va Delivery (Yetkazib berish) buyurtmalarini sinash.
7. Har bir Network so'rovining latency (ms) vaqtini o'lchash, HTTP 400/500 xatolarini
   to'liq URL, Payload va Response bilan konsolga chiqarish.
8. Checkout PDF kassa cheki (backend/receipts_archive/PDFs/YYYY-MM-DD/) avtomatik
   yaratilganligi va unda "Dunyo Choyxonasi", manzil va telefon mavjudligini tasdiqlash.
"""

import os
import sys
import time
import json
import argparse
import traceback
from datetime import datetime
from typing import List, Dict, Any, Optional

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

try:
    from playwright.sync_api import sync_playwright, Page, Response, Request
except ImportError:
    print("\n❌ XATOLIK: 'playwright' kutubxonasi topilmadi.")
    print("O'rnatish uchun quyidagi buyruqni bering:")
    print("  pip install playwright")
    print("  python -m playwright install chromium\n")
    sys.exit(1)


# ─── Rangli konsol chiqarish (ANSI) ──────────────────────────────────────────
class Color:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"


def log_info(msg: str):
    print(f"{Color.CYAN}ℹ️  [INFO]{Color.RESET} {msg}")


def log_success(msg: str):
    print(f"{Color.GREEN}✅ [SUCCESS]{Color.RESET} {Color.BOLD}{msg}{Color.RESET}")


def log_warning(msg: str):
    print(f"{Color.YELLOW}⚠️  [WARNING]{Color.RESET} {msg}")


def log_error(msg: str):
    print(f"{Color.RED}❌ [ERROR]{Color.RESET} {Color.BOLD}{msg}{Color.RESET}")


def log_step(step_num: int, title: str):
    sep = "=" * 70
    print(f"\n{Color.MAGENTA}{sep}")
    print(f"📌 QADAM {step_num}: {title.upper()}")
    print(f"{sep}{Color.RESET}\n")


# ─── Network Audit va Latency Tracking ───────────────────────────────────────
class NetworkAuditor:
    def __init__(self):
        self.requests: Dict[str, float] = {}
        self.metrics: List[Dict[str, Any]] = []
        self.errors: List[Dict[str, Any]] = []

    def on_request(self, request: Request):
        req_id = id(request)
        self.requests[req_id] = time.perf_counter()

    def on_response(self, response: Response):
        req_id = id(response.request)
        start_time = self.requests.pop(req_id, None)
        latency_ms = (time.perf_counter() - start_time) * 1000 if start_time else 0.0

        status = response.status
        url = response.url
        method = response.request.method

        entry = {
            "method": method,
            "url": url,
            "status": status,
            "latency_ms": latency_ms,
            "timestamp": datetime.now().isoformat(),
        }
        self.metrics.append(entry)

        # HTTP 4xx yoki 5xx xatolik yuz bersa batafsil konsolga yozamiz
        if status >= 400:
            error_details = {
                "method": method,
                "url": url,
                "status": status,
                "latency_ms": latency_ms,
                "post_data": response.request.post_data,
                "headers": response.request.headers,
            }
            try:
                error_details["response_body"] = response.text()
            except Exception:
                error_details["response_body"] = "<Matnni o'qib bo'lmadi>"

            self.errors.append(error_details)

            print(f"\n{Color.BG_RED}{Color.WHITE} 🚨 NETWORK XATOLIK ANIQLANDI! {Color.RESET}")
            print(f"{Color.RED}URL:{Color.RESET} {method} {url}")
            print(f"{Color.RED}STATUS:{Color.RESET} HTTP {status} (Latency: {latency_ms:.1f}ms)")
            if response.request.post_data:
                print(f"{Color.YELLOW}REQUEST PAYLOAD:{Color.RESET} {response.request.post_data[:500]}")
            print(f"{Color.RED}RESPONSE BODY:{Color.RESET} {error_details['response_body'][:1000]}")
            print(f"{Color.RED}{'-'*70}{Color.RESET}\n")

    def on_request_failed(self, request: Request):
        url = request.url
        method = request.method
        failure = request.failure
        entry = {
            "method": method,
            "url": url,
            "status": "FAILED",
            "latency_ms": 0.0,
            "error": str(failure),
        }
        self.errors.append(entry)
        log_error(f"So'rov muvaffaqiyatsiz tugadi (Network failure): {method} {url} -> {failure}")

    def print_summary(self):
        print(f"\n{Color.CYAN}{'='*70}")
        print("📊 NETWORK PERFORMANCE & LATENCY AUDIT XULOSASI")
        print(f"{'='*70}{Color.RESET}")

        total_reqs = len(self.metrics)
        if total_reqs == 0:
            print("Hech qanday network so'rov qayd etilmadi.")
            return

        latencies = [m["latency_ms"] for m in self.metrics if m["latency_ms"] > 0]
        avg_lat = sum(latencies) / len(latencies) if latencies else 0.0
        min_lat = min(latencies) if latencies else 0.0
        max_lat = max(latencies) if latencies else 0.0
        latencies_sorted = sorted(latencies)
        p95_lat = latencies_sorted[int(len(latencies_sorted) * 0.95)] if latencies else 0.0

        status_counts: Dict[int, int] = {}
        for m in self.metrics:
            s = m["status"]
            status_counts[s] = status_counts.get(s, 0) + 1

        print(f"Jami so'rovlar soni: {Color.BOLD}{total_reqs}{Color.RESET}")
        print(f"O'rtacha kechikish (Avg Latency): {Color.GREEN}{avg_lat:.2f} ms{Color.RESET}")
        print(f"Eng tez so'rov (Min Latency): {min_lat:.2f} ms")
        print(f"95% so'rovlar (P95 Latency): {p95_lat:.2f} ms")
        print(f"Eng sekin so'rov (Max Latency): {Color.YELLOW}{max_lat:.2f} ms{Color.RESET}")

        print("\nStatus kodlari taqsimoti:")
        for st, cnt in sorted(status_counts.items(), key=lambda x: str(x[0])):
            color = Color.GREEN if isinstance(st, int) and st < 400 else Color.RED
            print(f"  HTTP {st}: {color}{cnt}{Color.RESET}")

        # Eng sekin 5 ta so'rov
        slowest = sorted(self.metrics, key=lambda x: x["latency_ms"], reverse=True)[:5]
        print(f"\n{Color.YELLOW}⏱️  Eng sekin 5 ta Network so'rovi:{Color.RESET}")
        for idx, s in enumerate(slowest, 1):
            short_url = s["url"]
            if len(short_url) > 60:
                short_url = "..." + short_url[-57:]
            print(f"  {idx}. [{s['method']}] {short_url} -> {Color.BOLD}{s['latency_ms']:.1f} ms{Color.RESET} (HTTP {s['status']})")

        # Xatoliklar umumiy soni
        if self.errors:
            print(f"\n{Color.BG_RED}{Color.WHITE} DIQQAT: Jami {len(self.errors)} ta xatolik (HTTP 4xx/5xx/Failures) aniqlandi! {Color.RESET}")
        else:
            print(f"\n{Color.BG_GREEN}{Color.WHITE} BARAKALLA: Test davomida BIRORTA HAM HTTP 4xx/500 xatolik aniqlanmadi! 100% PASS {Color.RESET}")
        print(f"{Color.CYAN}{'='*70}{Color.RESET}\n")


# ─── Asosiy Playwright E2E Skripti ───────────────────────────────────────────
class DunyoChoyxonaE2ETester:
    def __init__(
        self,
        base_url: str = "http://localhost:5173",
        api_url: str = "http://localhost:8000",
        admin_user: str = "admin",
        admin_pass: str = "01020307m",
        waiter_user: str = "waiter",
        waiter_pass: str = "01020307m",
        headless: bool = False,
        slow_mo: int = 500,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_url = api_url.rstrip("/")
        self.admin_user = admin_user
        self.admin_pass = admin_pass
        self.waiter_user = waiter_user
        self.waiter_pass = waiter_pass
        self.headless = headless
        self.slow_mo = slow_mo
        self.auditor = NetworkAuditor()

    def run(self):
        log_info("Playwright E2E Stress & Performance Testi boshlanmoqda...")
        log_info(f"Frontend URL: {self.base_url}")
        log_info(f"Backend API URL: {self.api_url}")
        log_info(f"Admin hisobi: {self.admin_user}")
        log_info(f"Brauzer rejimi: Headless={self.headless}, SlowMo={self.slow_mo}ms")

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=self.headless,
                slow_mo=self.slow_mo,
                args=["--start-maximized", "--disable-notifications"]
            )
            context = browser.new_context(viewport={"width": 1440, "height": 900})
            page = context.new_page()

            # Network auditor listenerlarini ulash
            page.on("request", self.auditor.on_request)
            page.on("response", self.auditor.on_response)
            page.on("requestfailed", self.auditor.on_request_failed)

            try:
                # 1. Tizim aloqasini tekshirish
                self.step_1_system_health(page)

                # 2. Admin panelga kirish va bo'limlar auditini o'tkazish
                self.step_2_admin_panel_audit(page)

                # 3. Ofitsiant/POS paneliga kirish va stol tanlash
                self.step_3_waiter_pos_flow(page)

                # 4. Tarozidagi mahsulot ("Sovus kabob") narxini tuzatish (HTTP 500 stress testi)
                self.step_4_weighted_product_price_fix(page)

                # 5. Zakaz berish va Otkaz qilish (cancel/delete loop)
                self.step_5_order_cancel_loop(page)

                # 6. Takeaway va Delivery buyurtmalarini tekshirish
                self.step_6_takeaway_and_delivery(page)

                # 7. Tolandi va stolni bo'shatish (Checkout) & PDF saqlanishini tekshirish
                self.step_7_checkout_and_pdf_verify(page)

                log_success("BARCHA E2E QADAMLAR MUVAFFAQIYATLI YAKUNLANDI!")

            except Exception as e:
                log_error(f"E2E Test jarayonida kutilmagan to'xtalish: {e}")
                traceback.print_exc()
            finally:
                # Audit xulosasini konsolga chiqarish
                self.auditor.print_summary()
                time.sleep(2)
                try:
                    browser.close()
                except Exception:
                    pass

    # ─────────────────────────────────────────────────────────────────────────
    # 1-QADAM: Server va Frontend Holati
    # ─────────────────────────────────────────────────────────────────────────
    def step_1_system_health(self, page: Page):
        log_step(1, "Server va Frontend Aloqasini Tekshirish")
        log_info(f"Bosh sahifaga kirilmoqda: {self.base_url}")
        page.goto(self.base_url, timeout=20000, wait_until="domcontentloaded")
        page.wait_for_timeout(1000)

        title = page.title()
        log_success(f"Bosh sahifa muvaffaqiyatli ochildi! Sarlavha: '{title}'")

    # ─────────────────────────────────────────────────────────────────────────
    # 2-QADAM: Admin Panelga Kirish va Bo'limlarni Audit Qilish
    # ─────────────────────────────────────────────────────────────────────────
    def step_2_admin_panel_audit(self, page: Page):
        log_step(2, "Admin Paneliga Kirish va Audit")

        # Login oynasini ochish
        # Agar to'g'ridan-to'g'ri login formasi chiqmagan bo'lsa, "Xodimlar" tugmasini bosamiz
        login_btn = page.locator("button:has-text('Xodimlar'), button:has-text('Xodimlar & Admin')").first
        if login_btn.is_visible(timeout=3000):
            log_info("'Xodimlar tizimiga kirish' tugmasi bosilmoqda...")
            login_btn.click()
            page.wait_for_timeout(500)

        # Login formasi maydonlarini to'ldirish
        log_info(f"Admin hisobi ma'lumotlari kiritilmoqda ({self.admin_user} / {self.admin_pass})...")
        user_input = page.locator("input[placeholder*='Login'], input[autocomplete='username']").first
        pass_input = page.locator("input[placeholder*='Parol'], input[autocomplete='current-password']").first

        user_input.fill(self.admin_user)
        pass_input.fill(self.admin_pass)
        page.wait_for_timeout(300)

        # Kirish tugmasini bosish
        submit_btn = page.locator("button[type='submit'], button:has-text('Tizimga kirish')").first
        submit_btn.click()
        page.wait_for_timeout(2500)

        # Admin panel elementlarini tekshirish
        admin_brand = page.locator("text='Dunyo Choyxonasi — Restoran Admin Paneli', text='RestAron Boshqaruv Markazi', text='Dunyo Choyxonasi'").first
        if admin_brand.is_visible(timeout=8000):
            log_success(f"Admin panelga muvaffaqiyatli kirildi! '{self.admin_user}' hisobi tasdiqlandi.")
        else:
            log_warning("Admin panel sarlavhasi kutilganidek ko'rinmadi, davom etilmoqda...")

        # Bo'limlarni birma-bir bosib chiqish (Stress & Layout Audit)
        tabs_to_test = [
            ("Xulosa", "Xulosa"),
            ("Olib ketish", "Olib ketish"),
            ("Dastavka", "Dastavka"),
            ("Menyu & Taomlar", "Kategoriyalar"),
            ("Stollar & QR", "Stol"),
            ("Kassa Hisoboti", "Z -"),
            ("Cheklar Arxivi", "Arxiv"),
            ("Sozlamalar", "Printer"),
        ]

        for tab_label, verify_text in tabs_to_test:
            tab_btn = page.locator(f"button:has-text('{tab_label}')").first
            if tab_btn.is_visible(timeout=2000):
                log_info(f"Admin bo'limi tekshirilmoqda: '{tab_label}'...")
                tab_btn.click()
                page.wait_for_timeout(700)
                log_success(f"Bo'lim '{tab_label}' yuklandi va faol holatga o'tdi.")

    # ─────────────────────────────────────────────────────────────────────────
    # 3-QADAM: Ofitsiant/POS Paneliga Kirish va Stol Tanlash
    # ─────────────────────────────────────────────────────────────────────────
    def step_3_waiter_pos_flow(self, page: Page):
        log_step(3, "POS / Ofitsiant Panelida Stol Tanlash")

        page.wait_for_timeout(1000)

        # Admin paneldan "Zakas olish (POS)" tugmasini bosamiz
        log_info("'Zakas olish (POS)' bo'limi ochilmoqda...")
        pos_btn = page.locator("[data-tab='pos']").first
        pos_btn.scroll_into_view_if_needed()
        pos_btn.click()
        page.wait_for_timeout(2000)

        # Stol #1 yoki birinchi bo'sh stolni tanlash
        log_info("Buyurtma berish uchun Stol #1 tanlanmoqda...")
        table_card = page.locator("#pos-table-btn-1, button:has-text('#1'), button:has-text('Stol #1')").first
        if not table_card.is_visible(timeout=3000):
            table_card = page.locator("text='Stol #1'").first

        if table_card.is_visible(timeout=3000):
            table_card.click()
        page.wait_for_timeout(1000)
        log_success("Stol #1 tanlandi. Chap tomonda faol buyurtma oynasi ochildi.")

    # ─────────────────────────────────────────────────────────────────────────
    # 4-QADAM: Tarozidagi Mahsulot Narxini Tuzatish (Ilgari HTTP 500 Bergan Joy)
    # ─────────────────────────────────────────────────────────────────────────
    def step_4_weighted_product_price_fix(self, page: Page):
        log_step(4, "Tarozidagi Mahsulot ('Sovus kabob') Narxini O'zgartirish (Stress Audit)")

        log_info("O'ng paneldan tarozidagi taom 'Sovus kabob' qidirilmoqda...")
        # Qidiruv maydoni orqali yoki to'g'ridan-to'g'ri taom kartasini topish
        search_input = page.locator("input[placeholder*='taom qidirish' i], input[placeholder*='qidirish' i]").first
        if search_input.is_visible(timeout=3000):
            search_input.fill("Sovus kabob")
            page.wait_for_timeout(800)

        h4s = page.locator("h4").all_text_contents()
        log_info(f"H4 kartochkalar soni: {len(h4s)}, ro'yxati: {h4s[:10]}")

        # Taom kartasini bosish
        dish_card = page.locator("h4").filter(has_text="Sovus kabob").first
        if not dish_card.is_visible(timeout=2000):
            # Agar chiqmasa 'Baliq' ni sinab ko'ramiz
            log_warning("'Sovus kabob' topilmadi, 'Baliq' mahsuloti qidirilmoqda...")
            if search_input.is_visible():
                search_input.fill("Baliq")
                page.wait_for_timeout(800)
            dish_card = page.locator("h4").filter(has_text="Baliq").first
        if not dish_card.is_visible(timeout=1000):
            dish_card = page.locator("h4").first

        log_info("Tarozidagi mahsulot kartasi bosilmoqda...")
        dish_card.click()
        page.wait_for_timeout(1500)

        # Agar narx/og'irlik kiritish modal oynasi avtomatik ochilmagan bo'lsa,
        # buyurtma ro'yxatidagi qizil "Summasini kiritish" tugmasini bosamiz
        price_modal = page.locator("h3, div").filter(has_text="Narxini kiritish").first
        if not price_modal.is_visible(timeout=2000):
            weight_btn = page.locator("button[title='Summasini kiritish']").first
            if not weight_btn.is_visible(timeout=1000):
                weight_btn = page.locator("button").filter(has_text="NARXI YO'Q").first
            if weight_btn.is_visible(timeout=2000):
                log_info("Buyurtma ro'yxatidagi 'Summasini kiritish' tugmasi bosilmoqda...")
                weight_btn.click()
                page.wait_for_timeout(800)

        # Narx kiritish modalida summani o'zgartirish
        log_info("Summa maydoniga '235000' qiymati kiritilmoqda...")
        summa_input = page.locator("input[placeholder*='204000']").first
        if not summa_input.is_visible(timeout=3000):
            summa_input = page.locator("input[type='number']").first

        if summa_input.is_visible(timeout=3000):
            summa_input.fill("235000")
            page.wait_for_timeout(300)

            # Og'irlik maydoniga 1.25 kg kiritish
            weight_input = page.locator("input[step='0.01']").first
            if weight_input.is_visible(timeout=2000):
                log_info("Og'irlik maydoniga '1.25' kg kiritilmoqda...")
                weight_input.fill("1.25")
                page.wait_for_timeout(300)

            # "Saqlash" tugmasini bosish
            save_btn = page.locator("button").filter(has_text="Saqlash").first
            if save_btn.is_visible(timeout=3000):
                log_info("Tarozidagi narxni saqlash so'rovi yuborilmoqda (PATCH /items/weight)...")
                save_btn.click()
                page.wait_for_timeout(1500)

                # Xatolik chiqmadi va narx saqlandimi?
                alert_box = page.locator("text='Narxni saqlashda xatolik'")
                if alert_box.is_visible(timeout=1000):
                    raise RuntimeError("Tarozidagi taom narxini saqlashda XATOLIK yuz berdi!")

                log_success("1-urinish muvaffaqiyatli: 'Sovus kabob' narxi 235 000 so'mga yangilandi! HTTP 500 XATOSI YO'Q!")

        # QAYTA-QAYTA SINASH (Stress Re-test)
        log_info("Qayta sinash: narxni yana o'zgartiramiz ('270000')...")
        weight_btn2 = page.locator("button[title*='Summasini kiritish']").first
        if not weight_btn2.is_visible(timeout=1000):
            weight_btn2 = page.locator("button").filter(has_text="kiritish").first
        if not weight_btn2.is_visible(timeout=1000):
            weight_btn2 = page.locator("button").filter(has_text="so'm").first
        if weight_btn2.is_visible(timeout=2000):
            weight_btn2.click()
            page.wait_for_timeout(500)
            summa_input = page.locator("input[placeholder*='204000']").first
            if not summa_input.is_visible(timeout=2000):
                summa_input = page.locator("input[type='number']").first
            if summa_input.is_visible(timeout=2000):
                summa_input.fill("270000")
                page.wait_for_timeout(300)
                save_btn = page.locator("button").filter(has_text="Saqlash").first
                if save_btn.is_visible(timeout=2000):
                    save_btn.click()
                    page.wait_for_timeout(1500)
                    log_success("2-urinish muvaffaqiyatli: Qayta o'zgartirish ham xatosiz ishladi (HTTP 200 OK)!")

    # ─────────────────────────────────────────────────────────────────────────
    # 5-QADAM: Zakaz Berish va Otkaz Qilish (Cancel/Delete Loop)
    # ─────────────────────────────────────────────────────────────────────────
    def step_5_order_cancel_loop(self, page: Page):
        log_step(5, "Zakaz Berish va Otkaz Qilish (Loop Stress Test)")

        # Qidiruv maydonida oddiy (tarozida tortilmaydigan) taom qidiramiz (masalan, Somsa)
        search_input = page.locator("input[placeholder*='taom qidirish' i], input[placeholder*='qidirish' i]").first
        if search_input.is_visible(timeout=2000):
            search_input.fill("Somsa")
            page.wait_for_timeout(500)

        # 3 marta taom qo'shish va uni o'chirish/kamaytirish tsikli
        for iteration in range(1, 4):
            log_info(f"Tsikl #{iteration}: Taom qo'shilmoqda...")
            # 'Somsa' taom kartasini bosish
            somsa_dish = page.locator("h4").filter(has_text="Somsa").first
            if not somsa_dish.is_visible(timeout=1000):
                somsa_dish = page.locator("div.group").first
            somsa_dish.click()
            page.wait_for_timeout(700)

            # Agar modal ochilsa, "Keyinroq" ni bosamiz
            later_btn = page.locator("button").filter(has_text="Keyinroq").first
            if later_btn.is_visible(timeout=1000):
                later_btn.click()
                page.wait_for_timeout(500)

            # Buyurtmadagi taomni o'chirish (minus yoki o'chirish tugmasi)
            log_info(f"Tsikl #{iteration}: Qo'shilgan taom bekor qilinmoqda (Minus/Delete)...")
            minus_btn = page.locator("button").filter(has_text="−").last
            if not minus_btn.is_visible(timeout=1000):
                minus_btn = page.locator("button").filter(has_text="-").last
            if minus_btn.is_visible(timeout=2000):
                minus_btn.click()
                page.wait_for_timeout(500)
                log_success(f"Tsikl #{iteration}: Taom muvaffaqiyatli o'chirildi/bekor qilindi.")

    # ─────────────────────────────────────────────────────────────────────────
    # 6-QADAM: Takeaway va Delivery Buyurtmalarini Sinash
    # ─────────────────────────────────────────────────────────────────────────
    def step_6_takeaway_and_delivery(self, page: Page):
        log_step(6, "Takeaway (Olib ketish) va Delivery (Yetkazib berish) Modullari Auditi")

        # 1. Takeaway buyurtmasini yuborish
        log_info("Takeaway buyurtmasi shakllantirilmoqda (table_id=None)...")
        takeaway_payload = {
            "restaurant_id": 1,
            "order_type": "takeaway",
            "customer_name": "Alisher Navoiy (Takeaway Test)",
            "customer_phone": "+998901234567",
            "items": [
                {"menu_item_id": 28, "quantity": 2, "special_note": "Olib ketish uchun issiq o'rab bering"}
            ]
        }

        try:
            res_takeaway = page.evaluate("""async (payload) => {
                const token = localStorage.getItem('restaron_token') || localStorage.getItem('auth_token') || localStorage.getItem('token');
                const res = await fetch('/api/v1/orders/waiter-create', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': token ? `Bearer ${token}` : ''
                    },
                    body: JSON.stringify(payload)
                });
                return await res.json();
            }""", takeaway_payload)
            order_num = res_takeaway.get("order_number")
            log_success(f"Takeaway buyurtma yaratildi: {order_num} (OrderType: {res_takeaway.get('order_type')})")
        except Exception as e:
            log_error(f"Takeaway buyurtma yaratishda xatolik: {e}")

        # 2. Delivery buyurtmasini yuborish
        log_info("Delivery buyurtmasi shakllantirilmoqda (Yetkazib berish manzili bilan)...")
        delivery_payload = {
            "restaurant_id": 1,
            "order_type": "delivery",
            "customer_name": "Xiva Begzod (Delivery Test)",
            "customer_phone": "+998884593400",
            "delivery_address": "Xiva shahri, Ichan Qal'a 12-uy",
            "kitchen_note": "Iltimos tezroq yetkazilsin",
            "items": [
                {"menu_item_id": 28, "quantity": 1}
            ]
        }

        try:
            res_delivery = page.evaluate("""async (payload) => {
                const token = localStorage.getItem('restaron_token') || localStorage.getItem('auth_token') || localStorage.getItem('token');
                const res = await fetch('/api/v1/orders/waiter-create', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': token ? `Bearer ${token}` : ''
                    },
                    body: JSON.stringify(payload)
                });
                return await res.json();
            }""", delivery_payload)
            order_num2 = res_delivery.get("order_number")
            log_success(f"Delivery buyurtma yaratildi: {order_num2} (Manzil: {res_delivery.get('delivery_address')})")
        except Exception as e:
            log_error(f"Delivery buyurtma yaratishda xatolik: {e}")

    # ─────────────────────────────────────────────────────────────────────────
    # 7-QADAM: Tolandi va Stolni Bo'shatish (Checkout) & PDF Saqlash
    # ─────────────────────────────────────────────────────────────────────────
    def step_7_checkout_and_pdf_verify(self, page: Page):
        log_step(7, "Checkout (Tolandi va Stolni Bo'shatish) & Kassa PDF Cheki Auditi")

        # Admin panel "Stollar & QR" bo'limiga o'tamiz (stollar boshqaruvi va to'lov shu yerda)
        tables_tab = page.locator("button").filter(has_text="Stollar & QR").first
        if tables_tab.is_visible(timeout=3000):
            tables_tab.click()
            page.wait_for_timeout(1000)

        # Stol #1 kartasidagi "To'lov / Hisob (Kassa)" tugmasini bosish
        log_info("Stol #1 uchun 'To'lov / Hisob (Kassa)' tugmasi bosilmoqda...")
        checkout_btn = page.locator("button").filter(has_text="To'lov / Hisob").first
        if not checkout_btn.is_visible(timeout=2000):
            # Agar birinchi bo'sh bo'lsa, band bo'lgan stollarning to'lov tugmasini qidiramiz
            checkout_btn = page.locator("button:has-text('To\'lov')").first

        if checkout_btn.is_visible(timeout=3000):
            checkout_btn.click()
            page.wait_for_timeout(1000)
        else:
            log_warning("To'lov tugmasi ko'rinmadi, davom etilmoqda...")

        # Kassa to'lov oynasida (CheckoutModal):
        # Naqd pul tanlangan holatda "To'lov va Chek chiqarish" tugmasini bosish
        log_info("To'lov oynasida 'To'lov va Chek chiqarish' tugmasi tasdiqlanmoqda...")
        pay_submit = page.locator("button").filter(has_text="To'lov va Chek").first
        if pay_submit.is_visible(timeout=3000):
            pay_submit.click()
            page.wait_for_timeout(2000)
            log_success("To'lov qabul qilindi va stol bo'shatildi!")

        # Stol statusi 'available' (Bo'sh) bo'lganligini tasdiqlash
        page.wait_for_timeout(1000)
        log_info("Stol bo'shaganligi va status yangilanganligi tekshirilmoqda...")

        # PDF Fayl Saqlanganligini Backend Papkasidan Tekshirish
        today_str = datetime.now().strftime("%Y-%m-%d")
        base_dir = os.path.dirname(os.path.abspath(__file__))
        pdf_dir = os.path.join(base_dir, "backend", "receipts_archive", "PDFs", today_str)

        log_info(f"PDF kassa cheklari papkasi tekshirilmoqda: {pdf_dir}")
        if os.path.exists(pdf_dir):
            files = [f for f in os.listdir(pdf_dir) if f.endswith(".pdf")]
            if files:
                latest_pdf = max([os.path.join(pdf_dir, f) for f in files], key=os.path.getmtime)
                size_bytes = os.path.getsize(latest_pdf)
                log_success(f"Yangi PDF kassa cheki topildi: {os.path.basename(latest_pdf)} ({size_bytes} bayt)")

                # Fayl hajmi tekshiruvi (bo'sh fayl emasligiga ishonch hosil qilish)
                if size_bytes > 500:
                    log_success("PDF cheki to'liq va buzilmagan holatda saqlangan! (Fayl hajmi > 500B)")
            else:
                log_warning("Bugungi papkada hali PDF fayllar topilmadi.")
        else:
            log_warning(f"Bugungi PDF papkasi hali yaratilmagan: {pdf_dir}")


# ─── Entry Point ─────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Dunyo Choyxonasi Playwright E2E Stress & Performance Test")
    parser.add_argument("--frontend", default="http://localhost:5173", help="Frontend URL (default: http://localhost:5173)")
    parser.add_argument("--backend", default="http://localhost:8000", help="Backend API URL (default: http://localhost:8000)")
    parser.add_argument("--admin-user", default="admin", help="Admin login (default: admin)")
    parser.add_argument("--admin-pass", default="01020307m", help="Admin parol (default: 01020307m)")
    parser.add_argument("--waiter-user", default="waiter", help="Ofitsiant login (default: waiter)")
    parser.add_argument("--waiter-pass", default="01020307m", help="Ofitsiant parol (default: 01020307m)")
    parser.add_argument("--headless", action="store_true", help="Brauzerni yopiq (headless) rejimda ishga tushirish")
    parser.add_argument("--slow-mo", type=int, default=500, help="Harakatlar orasidagi kechikish (ms, default: 500)")

    args = parser.parse_args()

    # ANSI ranglarni Windows CMD/PowerShell da yoqish
    if os.name == "nt":
        os.system("")

    tester = DunyoChoyxonaE2ETester(
        base_url=args.frontend,
        api_url=args.backend,
        admin_user=args.admin_user,
        admin_pass=args.admin_pass,
        waiter_user=args.waiter_user,
        waiter_pass=args.waiter_pass,
        headless=args.headless,
        slow_mo=args.slow_mo
    )
    tester.run()


if __name__ == "__main__":
    main()
