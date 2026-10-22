"""
Test suite for VAZIFA 11: Zaxira nusxa (Database Backup & Restore System)
1. backup_db.py: sqlite3 backup API orqali restaron_YYYYMMDD_HHMM.db yaratish,
   PRAGMA integrity_check, xato bo'lsa XATO_ prefiksi va non-zero exit code.
2. Saqlash (retention) qoidasi: oxirgi 48 soat barcha nusxalar, 48h-14d oralig'ida
   har kundan 1 ta, 14 kundan eskilari o'chirilishi.
3. BACKUP_EXTRA_DIR: boshqa joyga nusxalash va receipts_archive hamda uploads papkalarini sinxronlash.
4. restore_db.py: zaxiralar ro'yxati, restaron_OLDINGI.db saqlanishi, tasdiq va tiklash.
"""
import os
import shutil
import sqlite3
import pytest
from datetime import datetime, timedelta

from tools.backup_db import (
    create_sqlite_backup,
    check_sqlite_integrity,
    clean_retention_backups,
    sync_extra_directory,
)
from tools.restore_db import (
    get_available_backups,
    restore_database,
)


@pytest.fixture
def temp_backup_env(tmp_path):
    """Sinov uchun alohida vaqtinchalik muhit yaratish"""
    backend_dir = tmp_path / "backend"
    backend_dir.mkdir()
    zaxira_dir = backend_dir / "zaxira"
    zaxira_dir.mkdir()
    receipts_dir = backend_dir / "receipts_archive"
    receipts_dir.mkdir()
    uploads_dir = backend_dir / "uploads"
    uploads_dir.mkdir()
    extra_dir = tmp_path / "extra_backup"
    extra_dir.mkdir()

    # Haqiqiy sinov sqlite bazasi
    db_file = backend_dir / "restaron.db"
    conn = sqlite3.connect(str(db_file))
    cur = conn.cursor()
    cur.execute("CREATE TABLE test_data (id INTEGER PRIMARY KEY, note TEXT);")
    cur.execute("INSERT INTO test_data (note) VALUES ('original_data_1'), ('original_data_2');")
    conn.commit()
    conn.close()

    return {
        "root": tmp_path,
        "backend": backend_dir,
        "zaxira": zaxira_dir,
        "receipts": receipts_dir,
        "uploads": uploads_dir,
        "extra": extra_dir,
        "db": db_file,
    }


def test_sqlite_backup_and_integrity_check(temp_backup_env):
    """1. SQLite backup API xavfsiz nusxa oladi va yaxlitligini tekshiradi"""
    src_db = str(temp_backup_env["db"])
    dst_db = str(temp_backup_env["zaxira"] / "restaron_20261022_1200.db")

    create_sqlite_backup(src_db, dst_db)

    assert os.path.exists(dst_db)
    assert os.path.getsize(dst_db) > 0

    # PRAGMA integrity_check 'ok' ekanligi
    assert check_sqlite_integrity(dst_db) is True

    # Ma'lumotlar to'g'ri ko'chganligini tekshirish
    conn = sqlite3.connect(dst_db)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM test_data;")
    count = cur.fetchone()[0]
    conn.close()
    assert count == 2


def test_corrupted_database_integrity_failure(tmp_path):
    """1. Yaxlitlik tekshiruvi (integrity_check) buzilgan faylda False qaytaradi"""
    bad_db = tmp_path / "corrupt.db"
    # Buzilgan tasodifiy baytlar
    with open(bad_db, "wb") as f:
        f.write(b"NOT A SQLITE DATABASE HEADER CORRUPTED DATA" * 100)

    assert check_sqlite_integrity(str(bad_db)) is False


def test_retention_policy_rules(temp_backup_env):
    """
    2. Saqlash qoidasi:
    - Oxirgi 48 soat: hamma soatlik nusxalar saqlanadi
    - 48 soatdan 14 kungacha: har kundan faqat 1 ta
    - 14 kundan eski: o'chiriladi
    - Standart bo'lmagan fayllar (masalan restaron_BOSHLANGICH.db): tegilmaydi
    """
    zaxira_dir = temp_backup_env["zaxira"]
    now = datetime(2026, 10, 22, 12, 0, 0)

    # 1. Oxirgi 48 soatdagi fayllar (hammasi saqlanishi kerak)
    recent_files = [
        "restaron_20261022_1100.db",  # 1 soat oldin
        "restaron_20261022_0600.db",  # 6 soat oldin
        "restaron_20261021_1800.db",  # 18 soat oldin
        "restaron_20261021_0000.db",  # 36 soat oldin
        "restaron_20261020_1400.db",  # 46 soat oldin
    ]

    # 2. 48h va 14 kun oralig'idagi fayllar:
    # 2026-10-18 kunidan 2 ta (faqat 18:00 qolishi kerak, 09:00 o'chishi kerak)
    # 2026-10-15 kunidan 2 ta (faqat 20:00 qolishi kerak, 10:00 o'chishi kerak)
    mid_range_files = [
        "restaron_20261018_1800.db",  # Kun 1: eng yangisi (saqlanadi)
        "restaron_20261018_0900.db",  # Kun 1: eskisi (o'chiriladi)
        "restaron_20261015_2000.db",  # Kun 2: eng yangisi (saqlanadi)
        "restaron_20261015_1000.db",  # Kun 2: eskisi (o'chiriladi)
    ]

    # 3. 14 kundan eski fayllar (ikkalasi ham o'chiriladi)
    old_files = [
        "restaron_20261005_1200.db",  # 17 kun oldin
        "restaron_20260930_1200.db",  # 22 kun oldin
    ]

    # Maxsus saqlanishi kerak bo'lgan fayl
    special_file = "restaron_BOSHLANGICH.db"

    all_files = recent_files + mid_range_files + old_files + [special_file]
    for fn in all_files:
        p = zaxira_dir / fn
        p.write_text("dummy")

    kept, deleted = clean_retention_backups(str(zaxira_dir), now=now)

    # 48 soat ichidagilarning hammasi saqlangan
    for fn in recent_files:
        assert fn in kept
        assert (zaxira_dir / fn).exists()

    # 48h-14d oralig'ida har kundan 1 tasi saqlangan
    assert "restaron_20261018_1800.db" in kept
    assert (zaxira_dir / "restaron_20261018_1800.db").exists()
    assert "restaron_20261015_2000.db" in kept
    assert (zaxira_dir / "restaron_20261015_2000.db").exists()

    # Bir xil kundagi ikkinchi nusxalar o'chirilgan
    assert not (zaxira_dir / "restaron_20261018_0900.db").exists()
    assert not (zaxira_dir / "restaron_20261015_1000.db").exists()

    # 14 kundan eskilari o'chirilgan
    for fn in old_files:
        assert not (zaxira_dir / fn).exists()

    # Maxsus nomli faylga tegilmagan
    assert (zaxira_dir / special_file).exists()


def test_extra_directory_sync(temp_backup_env):
    """3. BACKUP_EXTRA_DIR mavjud bo'lsa yangi zaxira va papkalar sinxronlanadi"""
    backend_dir = str(temp_backup_env["backend"])
    extra_dir = str(temp_backup_env["extra"])

    # receipts va uploads fayllari
    rec1 = temp_backup_env["receipts"] / "receipt_001.txt"
    rec1.write_text("Receipt content 1")
    up1 = temp_backup_env["uploads"] / "photo_001.jpg"
    up1.write_bytes(b"JPEG DATA")

    new_backup = temp_backup_env["zaxira"] / "restaron_20261022_1200.db"
    new_backup.write_bytes(b"SQLITE BACKUP")

    # Sinxronlash
    sync_extra_directory(str(new_backup), backend_dir, extra_dir)

    # Zaxira fayli extra_dir ga nusxalangan
    assert (temp_backup_env["extra"] / "restaron_20261022_1200.db").exists()
    # receipts va uploads nusxalangan
    assert (temp_backup_env["extra"] / "receipts_archive" / "receipt_001.txt").exists()
    assert (temp_backup_env["extra"] / "uploads" / "photo_001.jpg").exists()


def test_restore_database_flow(temp_backup_env):
    """5. restore_db: ro'yxat, restaron_OLDINGI.db saqlash va tanlangan bazani tiklash"""
    db_file = str(temp_backup_env["db"])
    zaxira_dir = str(temp_backup_env["zaxira"])

    # 1-zaxira (eski ma'lumot bilan)
    backup_file = temp_backup_env["zaxira"] / "restaron_20261020_1000.db"
    conn_b = sqlite3.connect(str(backup_file))
    cur_b = conn_b.cursor()
    cur_b.execute("CREATE TABLE test_data (id INTEGER PRIMARY KEY, note TEXT);")
    cur_b.execute("INSERT INTO test_data (note) VALUES ('restored_backup_data');")
    conn_b.commit()
    conn_b.close()

    # Ro'yxatni olish
    backups = get_available_backups(zaxira_dir)
    assert len(backups) >= 1
    assert backups[0][0] == "restaron_20261020_1000.db"

    # Tiklash amali
    success = restore_database(str(backup_file), db_file, zaxira_dir)
    assert success is True

    # restaron_OLDINGI.db saqlanganligini tekshirish
    old_db = temp_backup_env["zaxira"] / "restaron_OLDINGI.db"
    assert old_db.exists()
    conn_old = sqlite3.connect(str(old_db))
    cur_old = conn_old.cursor()
    cur_old.execute("SELECT note FROM test_data;")
    old_rows = [r[0] for r in cur_old.fetchall()]
    conn_old.close()
    assert "original_data_1" in old_rows

    # Asosiy baza yangilanganligini tekshirish
    conn_new = sqlite3.connect(db_file)
    cur_new = conn_new.cursor()
    cur_new.execute("SELECT note FROM test_data;")
    new_rows = [r[0] for r in cur_new.fetchall()]
    conn_new.close()
    assert new_rows == ["restored_backup_data"]
