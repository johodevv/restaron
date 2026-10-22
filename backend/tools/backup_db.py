"""
RestAron - Ma'lumotlar bazasini xavfsiz zaxira qilish (Backup) skripti
1. SQLite backup API orqali server ishlab turganda ham ma'lumotlar bazasining
   to'liq yaxlit nusxasini yaratadi (backend/zaxira/restaron_YYYYMMDD_HHMM.db).
2. Nusxaning yaxlitligini PRAGMA integrity_check orqali tekshiradi.
   Agar 'ok' bo'lmasa, nusxa 'XATO_' prefiksi bilan saqlanadi va xato kodi (1) bilan chiqiladi.
3. Saqlash (retention) qoidasi:
   - Oxirgi 48 soatdagi barcha soatlik nusxalar saqlanadi.
   - 48 soatdan 14 kungacha bo'lgan davrda har kun uchun bittadan nusxa saqlanadi.
   - 14 kundan eski nusxalar avtomatik o'chiriladi.
4. BACKUP_EXTRA_DIR mavjud bo'lsa:
   - Nusxa qo'shimcha papkaga (tashqi disk / fleshka) ko'chiriladi.
   - receipts_archive va uploads papkalaridagi o'zgargan fayllar sinxronlanadi.
"""
import os
import sys
import re
import shutil
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Tuple, Dict

# Agar python-dotenv mavjud bo'lsa, .env ni yuklaymiz
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
logger = logging.getLogger("backup_db")

FILENAME_REGEX = re.compile(r"^restaron_(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})\.db$")


def format_size(size_bytes: int) -> str:
    """Baytlarni o'qishga qulay formatga o'tkazish (KB, MB)"""
    if size_bytes < 1024:
        return f"{size_bytes} bayt"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB ({size_bytes:,} bayt)"
    else:
        return f"{size_bytes / (1024 * 1024):.2f} MB ({size_bytes:,} bayt)"


def check_sqlite_integrity(db_path: str) -> bool:
    """PRAGMA integrity_check bajarish va 'ok' ekanligini tasdiqlash"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA integrity_check;")
        rows = cursor.fetchall()
        conn.close()
        if rows and len(rows) == 1 and str(rows[0][0]).strip().lower() == "ok":
            return True
        logger.error(f"Integrity check xatolik qaytardi: {rows}")
        return False
    except Exception as e:
        logger.error(f"Integrity check vaqtida istisno yuz berdi: {e}")
        return False


def create_sqlite_backup(src_db: str, dst_db: str) -> None:
    """SQLite backup API yordamida jonli bazadan xavfsiz nusxa olish"""
    src_conn = sqlite3.connect(src_db)
    dst_conn = sqlite3.connect(dst_db)
    try:
        with dst_conn:
            src_conn.backup(dst_conn)
    finally:
        dst_conn.close()
        src_conn.close()


def clean_retention_backups(
    backup_dir: str,
    now: Optional[datetime] = None,
) -> Tuple[List[str], List[str]]:
    """
    Saqlash (retention) qoidasi:
    - Oxirgi 48 soat: barcha nusxalar saqlanadi.
    - 48 soatdan 14 kungacha: har bir kun uchun faqat 1 ta (eng oxirgi) nusxa saqlanadi.
    - 14 kundan eski: barchasi o'chiriladi.
    Qaytaradi: (saqlangan_fayllar, ochirilgan_fayllar)
    """
    if now is None:
        now = datetime.now()

    cutoff_48h = now - timedelta(hours=48)
    cutoff_14d = now - timedelta(days=14)

    if not os.path.exists(backup_dir):
        return [], []

    parsed_files: List[Tuple[datetime, str, str]] = []
    for fname in os.listdir(backup_dir):
        m = FILENAME_REGEX.match(fname)
        if m:
            year, month, day, hour, minute = map(int, m.groups())
            try:
                dt = datetime(year, month, day, hour, minute)
                full_path = os.path.join(backup_dir, fname)
                parsed_files.append((dt, fname, full_path))
            except ValueError:
                continue

    # Sanasi bo'yicha saralash (eng yangisi oldinda)
    parsed_files.sort(key=lambda x: x[0], reverse=True)

    kept: List[str] = []
    deleted: List[str] = []

    # 48h va 14d oralig'i uchun kunlik guruhlash (YYYY-MM-DD -> [files])
    daily_groups: Dict[str, List[Tuple[datetime, str, str]]] = {}

    for dt, fname, fpath in parsed_files:
        if dt >= cutoff_48h:
            # 1. Oxirgi 48 soatdagi barcha nusxalar
            kept.append(fname)
        elif dt >= cutoff_14d:
            # 2. 48 soatdan 14 kungacha: kunga qarab guruhlaymiz
            day_key = dt.strftime("%Y-%m-%d")
            daily_groups.setdefault(day_key, []).append((dt, fname, fpath))
        else:
            # 3. 14 kundan eski: o'chirish
            deleted.append(fpath)

    # Kunlik guruhlardan har bir kun uchun faqat bittasini (eng oxirgisini) qoldiramiz
    for day_key, group in daily_groups.items():
        # group allaqachon sana bo'yicha kamayish tartibida
        kept.append(group[0][1])  # birinchisini qoldiramiz
        for _, _, old_fpath in group[1:]:
            deleted.append(old_fpath)

    # Eskirgan fayllarni o'chirish
    for fpath in deleted:
        try:
            if os.path.exists(fpath):
                os.remove(fpath)
                logger.info(f"Eski zaxira o'chirildi (retention): {os.path.basename(fpath)}")
        except Exception as e:
            logger.warning(f"Eski zaxirani o'chirib bo'lmadi ({fpath}): {e}")

    return kept, deleted


def sync_extra_directory(
    new_backup_path: str,
    backend_dir: str,
    extra_dir: str,
) -> None:
    """
    BACKUP_EXTRA_DIR ko'rsatilgan bo'lsa:
    - Yangi zaxira faylini nusxalash.
    - receipts_archive va uploads papkalaridagi yangi/o'zgargan fayllarni nusxalash.
    Asosiy zaxirani to'xtatmasligi uchun har qanday xatolik ushlanadi va logga yoziladi.
    """
    try:
        if not extra_dir or not extra_dir.strip():
            return

        extra_dir = os.path.expanduser(os.path.expandvars(extra_dir.strip()))
        os.makedirs(extra_dir, exist_ok=True)

        # 1. Bazaning yangi zaxirasini nusxalash
        backup_filename = os.path.basename(new_backup_path)
        dest_backup = os.path.join(extra_dir, backup_filename)
        shutil.copy2(new_backup_path, dest_backup)
        logger.info(f"Qo'shimcha joyga nusxalandi: {dest_backup}")

        # 2. receipts_archive va uploads papkalarini sinxronlash
        for folder_name in ("receipts_archive", "uploads"):
            src_folder = os.path.join(backend_dir, folder_name)
            if not os.path.exists(src_folder):
                continue

            dst_folder = os.path.join(extra_dir, folder_name)
            os.makedirs(dst_folder, exist_ok=True)

            copied_count = 0
            for root, _, files in os.walk(src_folder):
                rel_dir = os.path.relpath(root, src_folder)
                target_sub = os.path.join(dst_folder, rel_dir) if rel_dir != "." else dst_folder

                for f in files:
                    s_file = os.path.join(root, f)
                    d_file = os.path.join(target_sub, f)

                    should_copy = False
                    if not os.path.exists(d_file):
                        should_copy = True
                    else:
                        s_stat = os.stat(s_file)
                        d_stat = os.stat(d_file)
                        if s_stat.st_mtime > d_stat.st_mtime + 1.0 or s_stat.st_size != d_stat.st_size:
                            should_copy = True

                    if should_copy:
                        os.makedirs(os.path.dirname(d_file), exist_ok=True)
                        shutil.copy2(s_file, d_file)
                        copied_count += 1

            if copied_count > 0:
                logger.info(f"BACKUP_EXTRA_DIR: {folder_name} ichidan {copied_count} ta o'zgargan fayl nusxalandi.")

    except Exception as e:
        logger.warning(f"BACKUP_EXTRA_DIR nusxalashda xatolik (asosiy zaxira ta'sirlanmadi): {e}")


def main() -> int:
    """Asosiy zaxira olish funksiyasi"""
    tools_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.abspath(os.path.join(tools_dir, ".."))
    db_path = os.path.join(backend_dir, "restaron.db")
    backup_dir = os.path.join(backend_dir, "zaxira")

    # Muhit o'zgaruvchisidan DB yo'li o'zgargan bo'lsa tekshirish
    custom_db = os.getenv("SQLITE_DB_PATH")
    if custom_db and os.path.exists(custom_db):
        db_path = custom_db

    if not os.path.exists(db_path):
        logger.error(f"Asosiy ma'lumotlar bazasi topilmadi: {db_path}")
        return 1

    os.makedirs(backup_dir, exist_ok=True)

    now = datetime.now()
    timestamp_str = now.strftime("%Y%m%d_%H%M")
    backup_filename = f"restaron_{timestamp_str}.db"
    backup_path = os.path.join(backup_dir, backup_filename)

    logger.info(f"Zaxira nusxa olinmoqda: {db_path} -> {backup_path}")

    try:
        create_sqlite_backup(db_path, backup_path)
    except Exception as e:
        logger.error(f"SQLite backup API orqali nusxa olishda xatolik: {e}")
        if os.path.exists(backup_path):
            try:
                os.remove(backup_path)
            except Exception:
                pass
        return 1

    # Yaxlitlik tekshiruvi (PRAGMA integrity_check)
    is_valid = check_sqlite_integrity(backup_path)
    if not is_valid:
        bad_filename = f"XATO_{backup_filename}"
        bad_path = os.path.join(backup_dir, bad_filename)
        try:
            if os.path.exists(bad_path):
                os.remove(bad_path)
            os.rename(backup_path, bad_path)
            logger.critical(f"PRAGMA integrity_check 'ok' qaytarmadi! Fayl saqlandi: {bad_path}")
        except Exception as rename_err:
            logger.critical(f"Xato faylni qayta nomlashda xatolik: {rename_err}")
        return 1

    # Natija: papka va hajmni chiqarish
    file_size = os.path.getsize(backup_path)
    formatted_sz = format_size(file_size)
    print("=" * 60)
    print("  RESTARON MA'LUMOTLAR BAZASI ZAXIRA NUSXASI YARATILDI")
    print("=" * 60)
    print(f"  Fayl:      {backup_filename}")
    print(f"  Papka:     {backup_dir}")
    print(f"  Hajmi:     {formatted_sz}")
    print(f"  Yaxlitlik: OK (PRAGMA integrity_check muvaffaqiyatli)")
    print("=" * 60)

    # Retention tozalash
    try:
        kept, deleted = clean_retention_backups(backup_dir, now)
        logger.info(f"Retention natijasi: {len(kept)} ta nusxa saqlab qolindi, {len(deleted)} ta eskilari tozalandi.")
    except Exception as e:
        logger.warning(f"Retention tozalashda xatolik: {e}")

    # BACKUP_EXTRA_DIR qo'shimcha nusxa olish
    extra_dir = os.getenv("BACKUP_EXTRA_DIR")
    if extra_dir and extra_dir.strip():
        sync_extra_directory(backup_path, backend_dir, extra_dir.strip())

    return 0


if __name__ == "__main__":
    sys.exit(main())
