"""
Saytdagi MAVJUD rasmlarni siqish.

Yangi yuklanadigan rasmlar avtomatik siqiladi, lekin ilgari yuklangan
suratlar hali ham katta. Bu skript ularni bir martada siqib chiqadi:
sayt sezilarli tez ochiladi va barcha rasmlar bir xil sifatda bo'ladi.

Ishlatish:
    python rasm_siqish.py              # siqadi (nusxa olib)
    python rasm_siqish.py --korish     # hech narsa o'zgartirmaydi,
                                       # faqat qancha yutilishini aytadi

Asl fayllar "uploads/_asl_nusxa/" papkasiga ko'chiriladi — biror narsa
yoqmasa qaytarib olish mumkin.
"""
import argparse
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings            # noqa: E402
from app.core.image_utils import (              # noqa: E402
    compress_image_bytes, already_compressed,
    MAX_SIDE, QUALITY, SKIP_IF_UNDER_BYTES,
)

# QR kodlar siqilmaydi — ular allaqachon kichik va aniq bo'lishi shart.
SKIP_DIRS = {"qr_codes", "_asl_nusxa"}
# Siqilgan faylga qo'shiladigan qo'shimcha — brauzer eski nusxani
# ko'rsatib qolmasligi uchun manzil o'zgarishi shart.
FILE_SUFFIX = "-s1"
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".avif"}


def human(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n/1:.1f} {unit}".replace(".0 ", " ")
        n /= 1024.0
    return f"{n:.1f} GB"


def url_of(root: str, path: str) -> str:
    """Disk yo'lini bazadagi manzilga aylantirish (/uploads/...)"""
    rel = os.path.relpath(path, root).replace(os.sep, "/")
    return f"/uploads/{rel}"


def iter_images(root: str):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            if os.path.splitext(name)[1].lower() in IMAGE_EXTS:
                yield os.path.join(dirpath, name)


def update_db_urls(renames) -> int:
    """Kengaytmasi o'zgargan rasmlarning manzilini bazada yangilash."""
    import sqlite3
    from urllib.parse import urlparse

    db_url = settings.DATABASE_URL
    if "sqlite" not in db_url:
        print("  (baza SQLite emas — manzillarni qo'lda yangilang)")
        return 0

    # "sqlite+aiosqlite:///./restaron.db" -> fayl yo'li
    raw = db_url.split("///", 1)[-1] if "///" in db_url else db_url
    raw = raw.split("?", 1)[0]
    if not os.path.isabs(raw):
        raw = os.path.join(os.path.dirname(os.path.abspath(__file__)), raw)
    raw = os.path.normpath(raw)
    if not os.path.exists(raw):
        print(f"  (baza fayli topilmadi: {raw})")
        return 0

    targets = [
        ("menu_items", "image_url"),
        ("categories", "image_url"),
        ("restaurants", "logo_url"),
        ("users", "avatar_url"),
    ]
    count = 0
    con = sqlite3.connect(raw)
    try:
        for table, col in targets:
            try:
                con.execute(f"SELECT {col} FROM {table} LIMIT 1")
            except Exception:
                continue   # bunday jadval/ustun yo'q
            for old_url, new_url in renames:
                cur = con.execute(
                    f"UPDATE {table} SET {col} = ? WHERE {col} = ?",
                    (new_url, old_url),
                )
                count += cur.rowcount
        con.commit()
    finally:
        con.close()
    return count


def main() -> int:
    ap = argparse.ArgumentParser(description="Saytdagi rasmlarni siqish")
    ap.add_argument("--korish", action="store_true",
                    help="Hech narsa o'zgartirmaydi, faqat hisobot beradi")
    ap.add_argument("--sifat", type=int, default=QUALITY,
                    help=f"JPEG sifati 1-95 (sukut: {QUALITY})")
    ap.add_argument("--olcham", type=int, default=MAX_SIDE,
                    help=f"Eng uzun tomoni, nuqta (sukut: {MAX_SIDE})")
    args = ap.parse_args()

    root = settings.UPLOAD_DIR
    if not os.path.isdir(root):
        print(f"Rasmlar papkasi topilmadi: {root}")
        return 1

    backup_root = os.path.join(root, "_asl_nusxa")
    files = sorted(iter_images(root))
    if not files:
        print("Siqiladigan rasm topilmadi.")
        return 0

    print(f"Rasmlar papkasi : {root}")
    print(f"Topilgan rasmlar: {len(files)} ta")
    print(f"Sozlama         : eng uzun tomoni {args.olcham} nuqta, sifat {args.sifat}%")
    if args.korish:
        print("REJIM           : FAQAT KO'RISH (hech narsa o'zgarmaydi)")
    print("-" * 64)

    total_old = total_new = 0
    changed = skipped = 0
    renames = []   # (eski_manzil, yangi_manzil) — bazada yangilanadi

    for path in files:
        try:
            with open(path, "rb") as f:
                original = f.read()
        except Exception as e:
            print(f"  o'qib bo'lmadi: {os.path.basename(path)} ({e})")
            continue

        old_size = len(original)
        total_old += old_size

        # Allaqachon siqilgan rasmga tegmaymiz (sifati pasaymasin).
        if already_compressed(original, args.olcham):
            total_new += old_size
            skipped += 1
            continue

        # Allaqachon kichik rasmni ham qayta siqmaymiz.
        if old_size <= SKIP_IF_UNDER_BYTES:
            try:
                import io
                from PIL import Image
                with Image.open(io.BytesIO(original)) as probe:
                    if max(probe.size) <= args.olcham:
                        total_new += old_size
                        skipped += 1
                        continue
            except Exception:
                total_new += old_size
                skipped += 1
                continue

        data, new_ext = compress_image_bytes(
            original, os.path.splitext(path)[1].lstrip(".").lower(),
            max_side=args.olcham, quality=args.sifat,
        )
        if len(data) >= old_size:
            total_new += old_size
            skipped += 1
            continue

        total_new += len(data)
        changed += 1
        saved = 100 - (len(data) * 100 // max(1, old_size))
        print(f"  {os.path.basename(path)[:40]:42s} "
              f"{human(old_size):>9s} -> {human(len(data)):>9s}  (-{saved}%)")

        if args.korish:
            continue

        # Asl nusxani saqlab qo'yamiz
        rel = os.path.relpath(path, root)
        bpath = os.path.join(backup_root, rel)
        os.makedirs(os.path.dirname(bpath), exist_ok=True)
        try:
            shutil.copy2(path, bpath)
        except Exception as e:
            print(f"    (nusxa olinmadi: {e}) — bu fayl o'tkazib yuborildi")
            continue

        # Fayl HAR DOIM yangi nom bilan yoziladi.
        #
        # Sabab: brauzerga rasmlarni bir yil saqlashni aytganmiz (tez
        # ochilishi uchun). Agar fayl nomi o'zgarmasa, ilgari saytga
        # kirgan mijozning telefonida ESKI katta rasm qolib ketardi.
        # Nom o'zgarsa — hamma darhol yangi, yengil rasmni oladi.
        base = os.path.splitext(os.path.basename(path))[0]
        if not base.endswith(FILE_SUFFIX):
            base += FILE_SUFFIX
        new_path = os.path.join(os.path.dirname(path), f"{base}.{new_ext}")

        try:
            with open(new_path, "wb") as f:
                f.write(data)
        except Exception as e:
            print(f"    saqlanmadi: {e}")
            continue

        if new_path != path:
            renames.append((url_of(root, path), url_of(root, new_path)))
            try:
                os.remove(path)
            except Exception:
                pass

    print("-" * 64)
    print(f"Siqildi     : {changed} ta")
    print(f"O'zgarmadi  : {skipped} ta (allaqachon kichik)")
    print(f"Umumiy hajm : {human(total_old)} -> {human(total_new)}")
    if total_old > 0:
        print(f"Tejaldi     : {human(total_old - total_new)} "
              f"({100 - (total_new * 100 // max(1, total_old))}%)")
    if renames and not args.korish:
        updated = update_db_urls(renames)
        print(f"Bazada yangilandi: {updated} ta rasm manzili")
        if updated < len(renames):
            print(f"  DIQQAT: {len(renames) - updated} ta manzil bazada "
                  f"topilmadi (ishlatilmayotgan eski rasm bo'lishi mumkin)")

    if not args.korish and changed:
        print()
        print(f"Asl nusxalar: {backup_root}")
        print("Hammasi joyida bo'lsa shu papkani o'chirib yuborsangiz bo'ladi.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
