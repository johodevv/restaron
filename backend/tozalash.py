"""
RestAron — ma'lumotlarni tozalash vositasi.

Ishlatilishi:
    python tozalash.py buyurtmalar   # faqat buyurtma/chek/qarzlarni o'chiradi
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
    if mode not in ("buyurtmalar", "hammasi"):
        print(__doc__)
        return 2

    print(f"[i] Baza: {DB_PATH}")
    make_backup()
    if mode == "buyurtmalar":
        print("[i] Buyurtmalar, cheklar, qarzlar va hisobotlar tozalanmoqda...")
        clean_operational()
    else:
        print("[i] Butun baza o'chirilmoqda...")
        clean_everything()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
