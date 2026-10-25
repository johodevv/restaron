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
    try:
        try:
            from tools.database_lock import offline_database_lock
        except ImportError:
            from database_lock import offline_database_lock
        with offline_database_lock(db_path):
            return _restore_database_unlocked(selected_backup_path, db_path, backup_dir)
    except (RuntimeError, OSError) as exc:
        print(f'[XATOLIK] {exc}', file=sys.stderr)
        return False


def _restore_database_unlocked(selected_backup_path, db_path, backup_dir):
    from contextlib import closing
    import tempfile
    if os.path.abspath(selected_backup_path) == os.path.abspath(db_path):
        return False
    if not check_sqlite_integrity(selected_backup_path):
        print('[XATOLIK] Zaxira nusxasi buzilgan', file=sys.stderr)
        return False
    staged = None
    try:
        os.makedirs(backup_dir, exist_ok=True)
        # Stage first: even choosing OLDINGI.db cannot overwrite the selected
        # recovery source while backing up the current database.
        fd, staged = tempfile.mkstemp(prefix='.restore-', suffix='.db', dir=os.path.dirname(os.path.abspath(db_path)))
        os.close(fd)
        shutil.copy2(selected_backup_path, staged)
        if not check_sqlite_integrity(staged):
            return False
        old_backup_path = os.path.join(backup_dir, 'restaron_OLDINGI.db')
        if os.path.exists(db_path):
            with closing(sqlite3.connect(db_path, timeout=5)) as src:
                checkpoint = src.execute('PRAGMA wal_checkpoint(TRUNCATE)').fetchone()
                if checkpoint and checkpoint[0] != 0:
                    raise RuntimeError('WAL band; tiklash boshlanmadi')
                with closing(sqlite3.connect(old_backup_path)) as dst:
                    src.backup(dst)
            if not check_sqlite_integrity(old_backup_path):
                raise RuntimeError('Joriy bazaning zaxirasi tekshiruvdan o‘tmadi')
        for ext in ('-wal', '-shm'):
            sidecar = db_path + ext
            if os.path.exists(sidecar):
                os.remove(sidecar)
        os.replace(staged, db_path)
        staged = None
        print('[OK] Baza tekshirilgan zaxiradan atomar tiklandi; oldingi baza saqlandi')
        return check_sqlite_integrity(db_path)
    except (OSError, sqlite3.Error, RuntimeError) as exc:
        print(f'[XATOLIK] Tiklash to‘xtatildi: {exc}', file=sys.stderr)
        return False
    finally:
        if staged and os.path.exists(staged):
            os.remove(staged)


def main() -> int:
    parser = argparse.ArgumentParser(description="RestAron ma'lumotlar bazasini zaxiradan tiklash")
    parser.add_argument("--list", action="store_true", help="Mavjud zaxiralar ro'yxatini ko'rsatish")
    parser.add_argument("--backup-file", type=str, help="To'g'ridan-to'g'ri tiklanadigan fayl nomi yoki yo'li")
    parser.add_argument("--yes", "-y", action="store_true", help="Tasdiqlash so'rovini avtomatik qabul qilish")
    args = parser.parse_args()

    tools_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.abspath(os.path.join(tools_dir, ".."))
    db_path = os.path.join(backend_dir, "restaron.db")
    backup_dir = os.getenv('BACKUP_DIR') or os.path.join(backend_dir, "zaxira")

    custom_db = os.getenv("SQLITE_DB_PATH")
    if custom_db:
        db_path = custom_db
    else:
        from sqlalchemy.engine import make_url
        if backend_dir not in sys.path:
            sys.path.insert(0, backend_dir)
        from app.core.config import settings
        url = make_url(settings.DATABASE_URL)
        if url.get_backend_name() != 'sqlite':
            print('PostgreSQL uchun pg_restore asosidagi tiklash talab qilinadi', file=sys.stderr)
            return 1
        db_path = url.database

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
