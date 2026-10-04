"""
RestAron — ma'lumotlarni tozalash vositasi.

Ishlatilishi:
    python tozalash.py buyurtmalar   # faqat buyurtma/chek/qarzlarni o'chiradi
    python tozalash.py menyu         # namuna menyuni tozalaydi, 4 kategoriya qoladi
    python tozalash.py hammasi       # butun bazani o'chiradi (noldan boshlash)

Har ikki holatda ham o'chirishdan OLDIN bazadan zaxira nusxa olinadi:
    backend/zaxira/restaron_YYYY-MM-DD_HH-MM-SS.db
"""
import os
import shutil
import sqlite3
import sys
from datetime import datetime

BACKEND_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BACKEND_DIR, "restaron.db")
BACKUP_DIR = os.path.join(BACKEND_DIR, "zaxira")

# Kunlik ish ma'lumotlari — menyu, stollar, xodimlar saqlanadi
OPERATIONAL_TABLES = [
    "order_items",
    "receipt_archives",
    "shift_reports",
    "commission_logs",
    "debts",
    "notifications",
    "reviews",
    "orders",
]


def make_backup() -> str:
    if not os.path.exists(DB_PATH):
        print("[i] Baza fayli yo'q — zaxira olishning hojati yo'q.")
        return ""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    dest = os.path.join(BACKUP_DIR, f"restaron_{stamp}.db")
    # SQLite backup API — server ishlab turgan bo'lsa ham xavfsiz nusxa oladi
    try:
        src = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        dst = sqlite3.connect(dest)
        with dst:
            src.backup(dst)
        dst.close()
        src.close()
    except Exception as e:
        print(f"[!] SQLite zaxirasi olinmadi ({e}) — fayl ko'chirib olinadi.")
        shutil.copy2(DB_PATH, dest)
    print(f"[OK] Zaxira nusxa: {dest}")
    return dest


def clean_operational() -> None:
    if not os.path.exists(DB_PATH):
        print("[!] Baza fayli topilmadi:", DB_PATH)
        return
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    existing = {r[0] for r in cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    )}
    cur.execute("PRAGMA foreign_keys = OFF")
    total = 0
    for t in OPERATIONAL_TABLES:
        if t not in existing:
            continue
        before = cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        cur.execute(f"DELETE FROM {t}")
        total += before
        print(f"    {t:<20} {before} yozuv o'chirildi")

    # Stollarni bo'shatish
    if "tables" in existing:
        cur.execute(
            "UPDATE tables SET status='AVAILABLE', is_unlocked=0, current_pin=NULL"
        )
        print(f"    {'tables':<20} barcha stollar bo'shatildi")

    # Buyurtma raqamlari yana #R1-0001 dan boshlanishi uchun
    if "sqlite_sequence" in existing:
        cur.execute(
            "DELETE FROM sqlite_sequence WHERE name IN "
            "('orders','order_items','receipt_archives','shift_reports',"
            "'commission_logs','debts','notifications','reviews')"
        )
    conn.commit()
    cur.execute("VACUUM")
    conn.close()
    print(f"[OK] Jami {total} yozuv o'chirildi. Menyu, stollar, QR kodlar va "
          f"xodimlar saqlandi.")


# Menyu noldan boshlanganda shu kategoriyalar qoladi
DEFAULT_CATEGORIES = [
    ("Kaboblar", "Шашлыки", "Kebabs", "Кабоблар", "\U0001F362"),
    ("Salatlar", "Салаты", "Salads", "Салатлар", "\U0001F957"),
    ("Ichimliklar", "Напитки", "Drinks", "Ичимликлар", "\U0001F964"),
    ("Choylar", "Чай", "Tea", "Чойлар", "\U0001FAD6"),
]


def clean_menu() -> None:
    """Namuna menyuni tozalab, faqat 4 ta bo'sh kategoriya qoldiradi.

    Buyurtmalarda ishlatilgan taomlar O'CHIRILMAYDI (aks holda eski
    cheklar buzilardi) — ular shunchaki menyudan yashiriladi va
    internetdan olingan surati olib tashlanadi.
    """
    if not os.path.exists(DB_PATH):
        print("[!] Baza fayli topilmadi:", DB_PATH)
        return
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    existing = {r[0] for r in cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    )}
    if "menu_items" not in existing or "categories" not in existing:
        print("[!] Menyu jadvallari topilmadi.")
        conn.close()
        return

    used = set()
    if "order_items" in existing:
        used = {r[0] for r in cur.execute("SELECT DISTINCT menu_item_id FROM order_items")}

    total = cur.execute("SELECT COUNT(*) FROM menu_items").fetchone()[0]
    if used:
        marks = ",".join("?" * len(used))
        cur.execute(
            f"UPDATE menu_items SET is_available=0, is_stop_list=1, image_url=NULL "
            f"WHERE id IN ({marks})", tuple(used)
        )
        cur.execute(f"DELETE FROM menu_items WHERE id NOT IN ({marks})", tuple(used))
    else:
        cur.execute("DELETE FROM menu_items")
    removed = total - len(used)
    print(f"    o'chirildi:   {removed} ta taom")
    print(f"    yashirildi:   {len(used)} ta taom (buyurtmalarda ishlatilgan)")

    # Taomi qolmagan kategoriyalarni o'chiramiz
    cur.execute(
        "DELETE FROM categories WHERE id NOT IN "
        "(SELECT DISTINCT category_id FROM menu_items)"
    )

    # 4 ta asosiy kategoriyani tiklaymiz (bor bo'lsa qayta yaratilmaydi)
    rest_row = cur.execute("SELECT id FROM restaurants ORDER BY id LIMIT 1").fetchone()
    rest_id = rest_row[0] if rest_row else 1
    have = {str(r[0] or "").strip().lower()
            for r in cur.execute("SELECT name FROM categories WHERE restaurant_id=?", (rest_id,))}
    added = 0
    for i, (uz, ru, en, cyr, icon) in enumerate(DEFAULT_CATEGORIES):
        if uz.lower() in have:
            continue
        cur.execute(
            "INSERT INTO categories (restaurant_id, name, name_ru, name_en, name_cyrillic, "
            "icon, sort_order, is_active) VALUES (?,?,?,?,?,?,?,1)",
            (rest_id, uz, ru, en, cyr, icon, i),
        )
        added += 1
    print(f"    qo'shildi:    {added} ta kategoriya")

    conn.commit()
    cur.execute("VACUUM")
    conn.close()
    names = ", ".join(c[0] for c in DEFAULT_CATEGORIES)
    print(f"[OK] Menyu tozalandi. Kategoriyalar: {names}")
    print("[i] Endi admin panelda o'z taomlaringizni qo'shing.")


def clean_everything() -> None:
    if not os.path.exists(DB_PATH):
        print("[i] Baza fayli allaqachon yo'q.")
    else:
        os.remove(DB_PATH)
        print(f"[OK] O'chirildi: {DB_PATH}")
    # SQLite yordamchi fayllari
    for suffix in ("-wal", "-shm", "-journal"):
        extra = DB_PATH + suffix
        if os.path.exists(extra):
            os.remove(extra)
            print(f"[OK] O'chirildi: {extra}")
    print("[i] Server keyingi ishga tushganda baza qaytadan yaratiladi "
          "(admin: maqsad / 01020307m).")


def main() -> int:
    mode = (sys.argv[1] if len(sys.argv) > 1 else "").strip().lower()
    if mode not in ("buyurtmalar", "menyu", "hammasi"):
        print(__doc__)
        return 2

    print(f"[i] Baza: {DB_PATH}")
    make_backup()
    if mode == "buyurtmalar":
        print("[i] Buyurtmalar, cheklar, qarzlar va hisobotlar tozalanmoqda...")
        clean_operational()
    elif mode == "menyu":
        print("[i] Namuna menyu tozalanmoqda...")
        clean_menu()
    else:
        print("[i] Butun baza o'chirilmoqda...")
        clean_everything()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
