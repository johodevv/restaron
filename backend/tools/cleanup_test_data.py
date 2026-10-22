"""
RestAron - Test ma'lumotlarini tozalash (Cleanup Test Data) skripti
1. Standart holatda --dry-run rejimida ishlaydi (bazaga tegilmaydi, faqat nima
   o'chirilishi mumkinligi ko'rsatiladi).
2. Test yozuvlarni qidiradi:
   - Buyurtmalar (orders): '#T-TEST%', 'TEST-%', '#TEST%', '%TEST%', '%9999%', 'ORD-200%',
     va mijoz ismi 'Test%' yoki '%Test%' bo'lgan test yozuvlar.
   - Kassa/oshxona cheklari (receipt_archives): 'BILL_TEST%', '%TEST%', '%9999%' yoki
     yuqoridagi test buyurtmalarga tegishli cheklar.
   - Bog'liq order_items va print_jobs yozuvlari.
3. --apply bayrog'i berilganda:
   - O'chirishdan oldin AVTOMATIK backup_db.py orqali xavfsiz zaxira olinadi.
   - Faqat zaxira muvaffaqiyatli (integrity check OK) bo'lsa, tranzaksiya ichida
     bog'liq yozuvlar o'chiriladi.
"""
import os
import sys
import argparse
import sqlite3
import subprocess
import logging
from typing import List, Tuple, Dict, Any, Optional

# Agar backend .env bo'lsa yuklaymiz
try:
    from dotenv import load_dotenv
    _tools_dir = os.path.dirname(os.path.abspath(__file__))
    _backend_dir = os.path.abspath(os.path.join(_tools_dir, ".."))
    load_dotenv(os.path.join(_backend_dir, ".env"))
    load_dotenv(os.path.join(_backend_dir, "..", ".env"))
except Exception:
    pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("cleanup_test_data")


def get_db_path(custom_path: Optional[str] = None) -> str:
    """Ma'lumotlar bazasi fayl yo'lini aniqlash"""
    if custom_path and os.path.exists(custom_path):
        return custom_path

    env_db = os.getenv("SQLITE_DB_PATH")
    if env_db and os.path.exists(env_db):
        return env_db

    tools_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.abspath(os.path.join(tools_dir, ".."))
    default_db = os.path.join(backend_dir, "restaron.db")
    return default_db


def find_test_data(conn: sqlite3.Connection) -> Dict[str, Any]:
    """Test ma'lumotlarini qidirish va ularning ro'yxatini shakllantirish"""
    cursor = conn.cursor()

    # 1. Test buyurtmalarini topish
    order_query = """
        SELECT id, order_number, customer_name, total, is_paid, created_at, status
        FROM orders
        WHERE order_number LIKE '#T-TEST%'
           OR order_number LIKE 'TEST-%'
           OR order_number LIKE '#TEST%'
           OR order_number LIKE '%TEST%'
           OR order_number LIKE '%9999%'
           OR order_number LIKE 'ORD-200%'
           OR customer_name LIKE '%(Takeaway Test)%'
           OR customer_name LIKE '%(Delivery Test)%'
           OR customer_name LIKE '%Test Mijoz%'
           OR customer_name LIKE 'Test%'
        ORDER BY id ASC
    """
    cursor.execute(order_query)
    orders = cursor.fetchall()
    order_ids = [row[0] for row in orders]

    # 2. Bog'liq order_items
    items_count = 0
    items_list = []
    if order_ids:
        placeholders = ",".join("?" * len(order_ids))
        cursor.execute(
            f"SELECT id, order_id, menu_item_id, quantity, total_price FROM order_items WHERE order_id IN ({placeholders})",
            order_ids,
        )
        items_list = cursor.fetchall()
        items_count = len(items_list)

    # 3. Test cheklar (receipt_archives):
    # 'BILL_TEST%', '%TEST%', '%9999%' yoki test buyurtmalarga bog'langan cheklar
    receipt_query = """
        SELECT id, order_id, receipt_number, total_amount, created_at
        FROM receipt_archives
        WHERE receipt_number LIKE 'BILL_TEST%'
           OR receipt_number LIKE '%TEST%'
           OR receipt_number LIKE '%9999%'
    """
    cursor.execute(receipt_query)
    pattern_receipts = cursor.fetchall()

    linked_receipts = []
    if order_ids:
        placeholders = ",".join("?" * len(order_ids))
        cursor.execute(
            f"SELECT id, order_id, receipt_number, total_amount, created_at FROM receipt_archives WHERE order_id IN ({placeholders})",
            order_ids,
        )
        linked_receipts = cursor.fetchall()

    # Cheklarni birlashtirish (dublikatsiz)
    receipts_dict = {}
    for r in pattern_receipts + linked_receipts:
        receipts_dict[r[0]] = r
    all_receipts = sorted(receipts_dict.values(), key=lambda x: x[0])

    # 4. Bog'liq print_jobs (agar mavjud bo'lsa)
    print_jobs_count = 0
    if order_ids:
        try:
            placeholders = ",".join("?" * len(order_ids))
            cursor.execute(
                f"SELECT count(*) FROM print_jobs WHERE order_id IN ({placeholders})",
                order_ids,
            )
            print_jobs_count = cursor.fetchone()[0]
        except Exception:
            pass

    return {
        "orders": orders,
        "order_ids": order_ids,
        "items_count": items_count,
        "items_list": items_list,
        "receipts": all_receipts,
        "receipt_ids": [r[0] for r in all_receipts],
        "print_jobs_count": print_jobs_count,
    }


def print_test_data_report(data: Dict[str, Any]) -> None:
    """Topilgan test ma'lumotlarining chiroyli ro'yxatini chiqarish"""
    orders = data["orders"]
    receipts = data["receipts"]
    items_count = data["items_count"]
    print("\n" + "=" * 70)
    print("  RESTARON TEST MA'LUMOTLARINI QIDIRISH NATIJALARI")
    print("=" * 70)

    print(f"\n1. Test buyurtmalar (orders): {len(orders)} ta topildi")
    if orders:
        print(f"   {'ID':<6} {'Order Number':<22} {'Customer':<26} {'Summa':<10} {'Sana'}")
        print("   " + "-" * 66)
        for o in orders:
            c_name = str(o[2] or "-")
            if len(c_name) > 24:
                c_name = c_name[:21] + "..."
            print(f"   {o[0]:<6} {o[1]:<22} {c_name:<26} {o[3] or 0:<10.0f} {o[5]}")

    print(f"\n2. Bog'liq buyurtma mahsulotlari (order_items): {items_count} ta topildi")

    print(f"\n3. Cheklar arxivi (receipt_archives): {len(receipts)} ta topildi")
    if receipts:
        print(f"   {'ID':<6} {'Order ID':<10} {'Receipt Number':<26} {'Summa':<10} {'Sana'}")
        print("   " + "-" * 66)
        for r in receipts:
            print(f"   {r[0]:<6} {str(r[1] or '-'):<10} {r[2]:<26} {r[3] or 0:<10.0f} {r[4]}")

    if data.get("print_jobs_count", 0) > 0:
        print(f"\n4. Bog'liq print_jobs: {data['print_jobs_count']} ta topildi")

    print("\n" + "=" * 70)


def run_backup_before_delete(db_path: str) -> bool:
    """O'chirishdan oldin backup_db.py orqali zaxira olish"""
    logger.info("O'chirishdan oldin AVTOMATIK ZAXIRA olinmoqda (backup_db.py)...")
    tools_dir = os.path.dirname(os.path.abspath(__file__))
    backup_script = os.path.join(tools_dir, "backup_db.py")

    env = os.environ.copy()
    env["SQLITE_DB_PATH"] = db_path

    try:
        res = subprocess.run(
            [sys.executable, backup_script],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        if res.stdout:
            for line in res.stdout.strip().splitlines():
                print(f"  [BACKUP] {line}")
        if res.returncode != 0:
            logger.critical(f"Zaxira olishda xatolik yuz berdi (exit code {res.returncode})! O'chirish bekor qilindi.")
            if res.stderr:
                logger.critical(f"Backup stderr: {res.stderr}")
            return False
        logger.info("Zaxira muvaffaqiyatli olindi va yaxlitlik tekshiruvidan o'tdi.")
        return True
    except Exception as e:
        logger.critical(f"Zaxira skriptini chaqirishda kutilmagan xatolik: {e}")
        return False


def apply_cleanup(conn: sqlite3.Connection, data: Dict[str, Any]) -> Tuple[int, int, int]:
    """Test ma'lumotlarini tranzaksiya ichida to'liq o'chirish"""
    order_ids = data["order_ids"]
    receipt_ids = data["receipt_ids"]

    cursor = conn.cursor()
    cursor.execute("BEGIN TRANSACTION;")

    deleted_receipts = 0
    deleted_items = 0
    deleted_orders = 0

    try:
        # 1. Cheklar arxivini o'chirish
        if receipt_ids:
            placeholders = ",".join("?" * len(receipt_ids))
            cursor.execute(f"DELETE FROM receipt_archives WHERE id IN ({placeholders})", receipt_ids)
            deleted_receipts = cursor.rowcount

        # 2. Bog'liq print_jobs o'chirish
        if order_ids:
            placeholders = ",".join("?" * len(order_ids))
            cursor.execute(f"DELETE FROM print_jobs WHERE order_id IN ({placeholders})", order_ids)

        # 3. Bog'liq order_items o'chirish
        if order_ids:
            placeholders = ",".join("?" * len(order_ids))
            cursor.execute(f"DELETE FROM order_items WHERE order_id IN ({placeholders})", order_ids)
            deleted_items = cursor.rowcount

        # 4. Test orders o'chirish
        if order_ids:
            placeholders = ",".join("?" * len(order_ids))
            cursor.execute(f"DELETE FROM orders WHERE id IN ({placeholders})", order_ids)
            deleted_orders = cursor.rowcount

        conn.commit()
        logger.info("Barcha test ma'lumotlari muvaffaqiyatli o'chirildi va tranzaksiya tasdiqlandi (commit).")
        return deleted_orders, deleted_items, deleted_receipts
    except Exception as e:
        conn.rollback()
        logger.error(f"O'chirish jarayonida xatolik yuz berdi, tranzaksiya bekor qilindi (rollback): {e}")
        raise


def main() -> int:
    parser = argparse.ArgumentParser(
        description="RestAron - Test ma'lumotlarini xavfsiz tozalash vositasi"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Haqiqiy o'chirishni amalga oshirish (avval avtomatik zaxira olinadi)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Faqat o'chiriladigan ma'lumotlar ro'yxatini ko'rsatish (standart holat)",
    )
    parser.add_argument(
        "--db",
        type=str,
        default=None,
        help="Ma'lumotlar bazasi fayliga to'liq yo'l (ixtiyoriy)",
    )

    args = parser.parse_args()
    db_path = get_db_path(args.db)

    if not os.path.exists(db_path):
        logger.error(f"Ma'lumotlar bazasi topilmadi: {db_path}")
        return 1

    conn = sqlite3.connect(db_path)
    try:
        data = find_test_data(conn)
        print_test_data_report(data)

        total_records = len(data["orders"]) + data["items_count"] + len(data["receipts"])
        if total_records == 0:
            print("\nTozalanadigan test ma'lumotlari topilmadi. Baza toza!")
            return 0

        if not args.apply:
            print("\n[DIQQAT] Standart --dry-run rejimi faol. Hech qanday ma'lumot o'chirilmadi.")
            print("Haqiqiy o'chirish va avtomatik zaxira olish uchun quyidagi buyruqni bering:")
            print(f"  python backend/tools/cleanup_test_data.py --apply")
            return 0

        # --apply berilgan bo'lsa:
        # 1. Zaxira olish
        backup_ok = run_backup_before_delete(db_path)
        if not backup_ok:
            return 1

        # 2. O'chirish
        del_orders, del_items, del_receipts = apply_cleanup(conn, data)
        print("\n" + "=" * 70)
        print("  TOZALASH YAKUNLANDI (APPLY)")
        print("=" * 70)
        print(f"  O'chirilgan buyurtmalar (orders):          {del_orders} ta")
        print(f"  O'chirilgan mahsulotlar (order_items):    {del_items} ta")
        print(f"  O'chirilgan cheklar (receipt_archives):   {del_receipts} ta")
        print("=" * 70)
        return 0

    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
