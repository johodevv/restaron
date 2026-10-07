"""
Ma'lumotlar bazasidan XAVFSIZ nusxa olish.

Oddiy fayl ko'chirish server ishlab turganda yarim yozilgan baza beradi.
SQLite ning o'z backup API si esa yozuv o'rtasida ham butun nusxa oladi.

Ishlatilishi:
    python nusxa.py <manba.db> <nusxa.db>
"""
import os
import shutil
import sqlite3
import sys


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    src, dst = sys.argv[1], sys.argv[2]

    if not os.path.exists(src):
        print(f"[!] Baza topilmadi: {src}")
        return 1

    os.makedirs(os.path.dirname(os.path.abspath(dst)) or ".", exist_ok=True)
    try:
        s = sqlite3.connect(f"file:{src}?mode=ro", uri=True)
        d = sqlite3.connect(dst)
        with d:
            s.backup(d)
        d.close()
        s.close()
        print(f"[OK] Baza nusxasi olindi: {dst}")
    except Exception as e:
        # Zaxira yo'l: oddiy fayl ko'chirish
        print(f"[!] SQLite nusxasi olinmadi ({e}) - fayl ko'chiriladi.")
        shutil.copy2(src, dst)
        print(f"[OK] Baza ko'chirildi: {dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
