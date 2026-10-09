"""
Rasmlarni siqish — sayt tez ochilishi uchun.

Telefondan yuklangan surat odatda 3–8 MB bo'ladi, saytda esa u atigi
~400 nuqta kenglikdagi kartochkada ko'rsatiladi. Ya'ni foydalanuvchi
kerak bo'lganidan 30–60 barobar ko'p ma'lumot yuklab oladi va sayt
sekin ishlaydi.

Shuning uchun har bir rasm saqlashdan oldin:
  * kattaligi MAX_SIDE dan oshsa kichraytiriladi (nisbati saqlanadi);
  * JPEG sifatida, QUALITY sifat darajasida qayta yoziladi;
  * EXIF burilishi to'g'rilanadi (telefonda yonboshlab chiqmasin);
  * ortiqcha EXIF ma'lumotlari olib tashlanadi.

Sifat ataylab JUDA past qilinmagan: 1400 nuqta + 82% sifat — ekranda
ko'z bilan farqi bilinmaydi, lekin hajmi o'nlab barobar kichrayadi.
"""
import io
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# Rasmning eng uzun tomoni (nuqta). Saytdagi eng katta kartochka ~500px,
# Retina ekranlar uchun 2 barobar zaxira bilan olingan.
MAX_SIDE = 1400
# JPEG sifati: 82 — ko'z bilan farqi sezilmaydigan chegara.
QUALITY = 82
# Shaffof (alpha) rasm PNG bo'lib qoladi, lekin u ham kichraytiriladi.
PNG_MAX_SIDE = 1000

ANIMATED_FORMATS = {"GIF", "WEBP"}

# Siqilgan faylga shu belgi yoziladi (JPEG COM markeri). Shu belgi bor
# rasm QAYTA siqilmaydi — har siqish sifatni bir oz yo'qotadi, skript
# ikki marta ishlasa rasm xiralashib ketardi.
STAMP = b"RestAron-siqilgan-v1"


def already_compressed(content: bytes, max_side: int = MAX_SIDE) -> bool:
    """Rasm allaqachon shu skript tomonidan siqilganmi?"""
    try:
        from PIL import Image
        with Image.open(io.BytesIO(content)) as img:
            if max(img.size) > max_side:
                return False
            comment = img.info.get("comment")
            if isinstance(comment, str):
                comment = comment.encode("utf-8", "ignore")
            return bool(comment) and STAMP in comment
    except Exception:
        return False


def _has_transparency(img) -> bool:
    if img.mode in ("RGBA", "LA"):
        extrema = img.getextrema()
        try:
            alpha_min = extrema[-1][0]
            return alpha_min < 255
        except Exception:
            return True
    return img.mode == "P" and "transparency" in img.info


def compress_image_bytes(
    content: bytes,
    ext: str = "",
    max_side: int = MAX_SIDE,
    quality: int = QUALITY,
) -> Tuple[bytes, str]:
    """Rasmni siqib, (yangi_baytlar, yangi_kengaytma) qaytaradi.

    Siqib bo'lmasa (masalan HEIC yoki buzilgan fayl) — asl fayl
    o'zgarishsiz qaytariladi. Yuklash hech qachon xatolik bermaydi.
    """
    if not content:
        return content, (ext or "jpg")

    try:
        from PIL import Image, ImageOps
    except Exception:  # pragma: no cover
        logger.warning("Pillow topilmadi — rasm siqilmadi")
        return content, (ext or "jpg")

    # Allaqachon siqilgan bo'lsa — qayta siqmaymiz (sifat pasaymasin).
    if already_compressed(content, max_side):
        return content, (ext or "jpg")

    try:
        img = Image.open(io.BytesIO(content))
        fmt = (img.format or "").upper()

        # Animatsiyali GIF/WEBP ni qayta yozmaymiz — harakati yo'qoladi.
        if getattr(img, "is_animated", False) and fmt in ANIMATED_FORMATS:
            return content, (ext or fmt.lower() or "gif")

        # Telefon suratlarida burilish EXIF da yoziladi.
        img = ImageOps.exif_transpose(img)

        transparent = _has_transparency(img)
        limit = PNG_MAX_SIDE if transparent else max_side

        if max(img.size) > limit:
            img.thumbnail((limit, limit), Image.LANCZOS)

        out = io.BytesIO()
        if transparent:
            # Shaffoflik kerak (logotip) — PNG bo'lib qoladi.
            if img.mode not in ("RGBA", "LA", "P"):
                img = img.convert("RGBA")
            img.save(out, format="PNG", optimize=True)
            new_ext = "png"
        else:
            if img.mode != "RGB":
                img = img.convert("RGB")
            img.save(
                out, format="JPEG", quality=quality,
                optimize=True, progressive=True, comment=STAMP,
            )
            new_ext = "jpg"

        data = out.getvalue()
        # Siqilgan fayl aslidan kattaroq bo'lib qolsa (allaqachon siqilgan
        # kichik rasm) — aslini qoldiramiz, foyda yo'q.
        if len(data) >= len(content):
            return content, (ext or fmt.lower() or "jpg")
        return data, new_ext

    except Exception as e:
        logger.warning(f"Rasmni siqib bo'lmadi ({e}) — asl fayl saqlanadi")
        return content, (ext or "jpg")


# Allaqachon yetarlicha kichik rasmni qayta siqmaymiz: har siqish
# sifatni bir oz yo'qotadi, skript ikki marta ishlasa rasm xiralashadi.
SKIP_IF_UNDER_BYTES = 250 * 1024


def compress_file(path: str, max_side: int = MAX_SIDE,
                  quality: int = QUALITY,
                  skip_under: int = SKIP_IF_UNDER_BYTES) -> Optional[Tuple[int, int, str]]:
    """Diskdagi rasmni joyida siqadi.

    Qaytaradi: (eski_hajm, yangi_hajm, yangi_yo'l) yoki None (o'zgarmadi).
    Kengaytma o'zgarsa fayl yangi nom bilan yoziladi va eskisi o'chiriladi.
    """
    import os

    try:
        with open(path, "rb") as f:
            original = f.read()
    except Exception:
        return None

    old_size = len(original)

    # Allaqachon siqilgan yoki kichik va o'lchami normal rasmga tegmaymiz.
    if already_compressed(original, max_side):
        return None
    if old_size <= skip_under:
        try:
            from PIL import Image
            with Image.open(io.BytesIO(original)) as probe:
                if max(probe.size) <= max_side:
                    return None
        except Exception:
            return None
    old_ext = path.rsplit(".", 1)[-1].lower() if "." in path else ""
    data, new_ext = compress_image_bytes(original, old_ext, max_side, quality)

    if data is original or len(data) >= old_size:
        return None

    new_path = path
    if new_ext and new_ext != old_ext:
        new_path = (path.rsplit(".", 1)[0] if "." in path else path) + "." + new_ext

    try:
        with open(new_path, "wb") as f:
            f.write(data)
        if new_path != path and os.path.exists(path):
            os.remove(path)
    except Exception as e:
        logger.warning(f"{path} saqlanmadi: {e}")
        return None

    return old_size, len(data), new_path
