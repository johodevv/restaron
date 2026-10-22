"""
RestAron - Ma'lumotlar bazasini tiklash (Restore) skripti
1. backend/zaxira/ papkasidagi barcha mavjud zaxira nusxalarini ro'yxat qilib tanlatadi.
2. Serverni to'xtatish kerakligini ogohlantiradi.
3. Joriy bazani restaron_OLDINGI.db sifatida saqlab qo'yadi.
4. Foydalanuvchidan aniq tasdiq (ha/yo'q) so'raydi.
5. Tanlangan nusxani restaron.db ga tiklaydi va yaxlitligini tekshiradi.
"""
import os
import sys
import shutil
import sqlite3
import argparse
from datetime import datetime
from typing import List, Tuple, Optional

# Agar python-dotenv mavjud bo'lsa yuklaymiz
try:
    from dotenv import load_dotenv
    _tools_dir = os.path.dirname(os.path.abspath(__file__))
    _backend_dir = os.path.abspath(os.path.join(_tools_dir, ".."))
    load_dotenv(os.path.join(_backend_dir, ".env"))
    load_dotenv(os.path.join(_backend_dir, "..", ".env"))
except Exception:
    pass


def format_size(size_bytes: int) -> str:
    """Baytlarni o'qishga qulay formatga o'tkazish (KB, MB)"""
    if size_bytes < 1024:
        return f"{size_bytes} bayt"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.2f} MB"


def check_sqlite_integrity(db_path: str) -> bool:
    """PRAGMA integrity_check tekshiruvi"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA integrity_check;")
        rows = cursor.fetchall()
        conn.close()
        return bool(rows and len(rows) == 1 and str(rows[0][0]).strip().lower() == "ok")
    except Exception:
        return False


def get_available_backups(backup_dir: str) -> List[Tuple[str, str, datetime, int]]:
    """
    zaxira papkasidagi mos fayllarni olish:
    Qaytaradi: [(fayl_nomi, toliq_yo'l, vaqt, hajm), ...]
    """
    if not os.path.exists(backup_dir):
        return []

    backups = []
    for fname in os.listdir(backup_dir):
        if not fname.endswith(".db"):
            continue
        # XATO_ va restaron_OLDINGI.db ni oddiy zaxiralar ro'yxatiga kiritmaymiz
        if fname.startswith("XATO_") or fname == "restaron_OLDINGI.db":
            continue

        fpath = os.path.join(backup_dir, fname)
        if not os.path.isfile(fpath):
            continue

        mtime = datetime.fromtimestamp(os.path.getmtime(fpath))
        size = os.path.getsize(fpath)
        backups.append((fname, fpath, mtime, size))

    # Eng yangisi tepada bo'lishi uchun saralaymiz
    backups.sort(key=lambda x: x[2], reverse=True)
    return backups


def restore_database(
    selected_backup_path: str,
    db_path: str,
    backup_dir: str,
) -> bool:
    """Tanlangan zaxirani tiklash amali"""
    # 1. Tanlangan zaxiraning yaxlitligini tekshirish
    if not check_sqlite_integrity(selected_backup_path):
        print(f"\n[XATOLIK] Tanlangan zaxira nusxasi buzilgan (integrity_check muvaffaqiyatsiz):", file=sys.stderr)
        print(f"  {selected_backup_path}", file=sys.stderr)
        return False

    # 2. Joriy bazani restaron_OLDINGI.db sifatida saqlab qo'yish
    old_backup_path = os.path.join(backup_dir, "restaron_OLDINGI.db")
    if os.path.exists(db_path):
        try:
            # SQLite backup API bilan yoki xavfsiz nusxa olish
            src_conn = sqlite3.connect(db_path)
            dst_conn = sqlite3.connect(old_backup_path)
            with dst_conn:
                src_conn.backup(dst_conn)
            dst_conn.close()
            src_conn.close()
            print(f"[1/3] Joriy ma'lumotlar bazasi saqlandi: {old_backup_path}")
        except Exception as e:
            # Agar fayl qulflangan bo'lsa oddiy copy urinib ko'ramiz
            try:
                shutil.copy2(db_path, old_backup_path)
                print(f"[1/3] Joriy ma'lumotlar bazasi ko'chirildi: {old_backup_path}")
            except Exception as copy_err:
                print(f"[OGOHLANTIRISH] Joriy bazani saqlashda xatolik: {copy_err}")

    # Eski WAL va SHM fayllarini tozalash (yangi bazaga ta'sir qilmasligi uchun)
    for ext in ("-wal", "-shm"):
        wal_file = db_path + ext
        if os.path.exists(wal_file):
            try:
                os.remove(wal_file)
            except Exception as e:
                print(f"[OGOHLANTIRISH] {wal_file} faylini o'chirib bo'lmadi: {e}")

    # 3. Tanlangan nusxani restaron.db ga tiklash
    try:
        shutil.copy2(selected_backup_path, db_path)
        print(f"[2/3] Tanlangan zaxira nusxasi tiklandi: {os.path.basename(selected_backup_path)} -> {os.path.basename(db_path)}")
    except Exception as e:
        print(f"[XATOLIK] Faylni ko'chirishda xatolik: {e}", file=sys.stderr)
        return False

    # 4. Tiklangan bazaning yaxlitligini tekshirish
    if not check_sqlite_integrity(db_path):
        print(f"[XATOLIK] Tiklangan ma'lumotlar bazasi yaxlitlik tekshiruvidan o'tmadi!", file=sys.stderr)
        return False

    print(f"[3/3] Tiklangan baza yaxlitligi tasdiqlandi: OK (PRAGMA integrity_check muvaffaqiyatli)")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="RestAron ma'lumotlar bazasini zaxiradan tiklash")
    parser.add_argument("--list", action="store_true", help="Mavjud zaxiralar ro'yxatini ko'rsatish")
    parser.add_argument("--backup-file", type=str, help="To'g'ridan-to'g'ri tiklanadigan fayl nomi yoki yo'li")
    parser.add_argument("--yes", "-y", action="store_true", help="Tasdiqlash so'rovini avtomatik qabul qilish")
    args = parser.parse_args()

    tools_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.abspath(os.path.join(tools_dir, ".."))
    db_path = os.path.join(backend_dir, "restaron.db")
    backup_dir = os.path.join(backend_dir, "zaxira")

    custom_db = os.getenv("SQLITE_DB_PATH")
    if custom_db:
        db_path = custom_db

    backups = get_available_backups(backup_dir)

    if args.list:
        print("Mavjud zaxiralar:")
        for idx, (fname, _, dt, sz) in enumerate(backups, 1):
            print(f"  [{idx}] {fname} ({dt.strftime('%d.%m.%Y %H:%M')}, {format_size(sz)})")
        return 0

    if not backups:
        print(f"\n[XATOLIK] Zaxira papkasida ({backup_dir}) hech qanday zaxira nusxasi topilmadi!")
        return 1

    selected_backup_path: Optional[str] = None
    selected_backup_name: Optional[str] = None

    if args.backup_file:
        target = args.backup_file
        if not os.path.isabs(target):
            # zaxira papkasi ichidan yoki joriy yo'ldan qidiramiz
            cand1 = os.path.join(backup_dir, target)
            cand2 = os.path.abspath(target)
            if os.path.exists(cand1):
                target = cand1
            elif os.path.exists(cand2):
                target = cand2

        if not os.path.exists(target):
            print(f"[XATOLIK] Ko'rsatilgan zaxira fayli topilmadi: {target}", file=sys.stderr)
            return 1
        selected_backup_path = target
        selected_backup_name = os.path.basename(target)
    else:
        print("\n" + "=" * 65)
        print("  RESTARON - MA'LUMOTLAR BAZASINI TIKLASH (RESTORE)")
        print("=" * 65)
        print("\n[DIQQAT! OGOHLANTIRISH]")
        print("  Bazani tiklashdan oldin RestAron SERVERINI TO'XTATISH SHART!")
        print("  Server ishlab turganda tiklansa, ma'lumotlar buzilishi mumkin.")
        print("  Tiklashdan oldin joriy baza 'restaron_OLDINGI.db' ga saqlanadi.")
        print("=" * 65)
        print("\nMavjud zaxira nusxalari:")

        for idx, (fname, _, dt, sz) in enumerate(backups, 1):
            print(f"  [{idx}] {fname:<32} ({dt.strftime('%d.%m.%Y %H:%M')}, {format_size(sz)})")
        print("  [0] Chiqish (bekor qilish)")
        print("-" * 65)

        while True:
            try:
                choice = input("\nTiklash uchun nusxa raqamini kiriting (0 - chiqish): ").strip()
            except (KeyboardInterrupt, EOFError):
                print("\nJarayon bekor qilindi.")
                return 0

            if not choice or choice == "0":
                print("Jarayon bekor qilindi.")
                return 0

            if choice.isdigit() and 1 <= int(choice) <= len(backups):
                selected_idx = int(choice) - 1
                selected_backup_name, selected_backup_path, _, _ = backups[selected_idx]
                break
            else:
                print(f"Noto'g'ri raqam! 1 dan {len(backups)} gacha raqam kiriting.")

    # Tasdiq so'rash
    if not args.yes:
        print("\n" + "!" * 65)
        print(f"  Tanlangan nusxa: {selected_backup_name}")
        print(f"  Tiklanadigan joy: {db_path}")
        print("!" * 65)
        try:
            confirm = input("Haqiqatan ham ushbu zaxirani tiklamoqchimisiz? (ha/yo'q): ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print("\nBekor qilindi.")
            return 0

        if confirm not in ("ha", "h", "yes", "y"):
            print("Tiklash bekor qilindi.")
            return 0

    success = restore_database(selected_backup_path, db_path, backup_dir)
    if success:
        print("\n" + "=" * 65)
        print("  BAZA MUVAFFAQIYATLI TIKLANDI!")
        print("  Endi RestAron serverini xavfsiz ishga tushirishingiz mumkin.")
        print("=" * 65 + "\n")
        return 0
    else:
        print("\n" + "=" * 65)
        print("  XATOLIK: Bazani tiklash muvaffaqiyatsiz tugadi!")
        print("=" * 65 + "\n", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
