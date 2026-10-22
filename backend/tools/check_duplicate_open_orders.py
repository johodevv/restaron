"""
RestAron: Stolda 2+ ochiq buyurtma bo'lgan holatlarni tekshirish skripti.
Faqat O'QIYDI (sqlite3, mode=ro). Bazani hech qachon o'zgartirmaydi.
"""
import sys
import sqlite3
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass


def check_duplicate_open_orders():
    print("=" * 75)
    print(" RestAron: Dublikat Ochiq Buyurtmalarni Tekshirish (Read-Only)")
    print("=" * 75)

    backend_dir = Path(__file__).resolve().parent.parent
    db_path = backend_dir / "restaron.db"

    if not db_path.exists():
        print(f"\n⚠️ Baza fayli topilmadi: {db_path}")
        return

    # Faqat o'qish (mode=ro) rejimida ulanish
    uri = f"file:{db_path.as_posix()}?mode=ro"
    try:
        conn = sqlite3.connect(uri, uri=True)
        conn.row_factory = sqlite3.Row
    except Exception as exc:
        print(f"\n❌ Bazaga ulanishda xatolik: {exc}")
        return

    try:
        cursor = conn.cursor()

        # Bir stolda 2 yoki undan ortiq ochiq buyurtmasi bor stollarni topish
        dup_query = """
            SELECT table_id, COUNT(*) as open_count
            FROM orders
            WHERE table_id IS NOT NULL 
              AND is_paid = 0 
              AND status NOT IN ('CANCELLED', 'PAID')
            GROUP BY table_id
            HAVING COUNT(*) > 1
            ORDER BY table_id ASC
        """
        cursor.execute(dup_query)
        duplicate_tables = cursor.fetchall()

        if not duplicate_tables:
            print("\n✅ Birorta ham stolda dublikat ochiq buyurtmalar topilmadi.")
            print("   Barcha stollarda ko'pi bilan bittadan ochiq buyurtma mavjud.")
            return

        print(f"\n⚠️ Topilgan dublikat stollar soni: {len(duplicate_tables)}\n")

        for dt in duplicate_tables:
            table_id = dt["table_id"]
            count = dt["open_count"]

            # Stol ma'lumotlarini olish (raqami, xonasi)
            cursor.execute("SELECT number, room FROM tables WHERE id = ?", (table_id,))
            t_row = cursor.fetchone()
            table_info = f"Stol #{t_row['number']}" if t_row else f"Stol ID: {table_id}"
            if t_row and t_row["room"]:
                table_info += f" ({t_row['room']})"

            print("-" * 75)
            print(f"📍 {table_info} [table_id={table_id}] — Ochiq buyurtmalar soni: {count}")
            print("-" * 75)
            header = f" {'ID':<6} | {'Buyurtma #':<12} | {'Status':<12} | {'Yaratilgan vaqt':<22} | {'Summa':<12}"
            print(header)
            print(" " + "-" * (len(header) - 1))

            cursor.execute("""
                SELECT id, order_number, status, created_at, total
                FROM orders
                WHERE table_id = ?
                  AND is_paid = 0
                  AND status NOT IN ('CANCELLED', 'PAID')
                ORDER BY created_at ASC
            """, (table_id,))
            orders = cursor.fetchall()

            for ord_row in orders:
                oid = ord_row["id"]
                onum = ord_row["order_number"] or "—"
                ostatus = ord_row["status"] or "—"
                ocreated = str(ord_row["created_at"])[:19] if ord_row["created_at"] else "—"
                ototal = f"{ord_row['total']:,.0f} so'm" if ord_row["total"] is not None else "0 so'm"
                print(f" {oid:<6} | {onum:<12} | {ostatus:<12} | {ocreated:<22} | {ototal:<12}")
            print()

        print("=" * 75)
        print("💡 Eslatma: Ushbu buyurtmalarni kassir yoki admin orqali to'lab (checkout)")
        print("   yoki bekor qilib (cancel) yopgach, unikal indeks avtomatik faollashadi.")
        print("=" * 75)

    except Exception as exc:
        print(f"\n❌ Ma'lumotlarni o'qishda xatolik: {exc}")
    finally:
        conn.close()


if __name__ == "__main__":
    check_duplicate_open_orders()
