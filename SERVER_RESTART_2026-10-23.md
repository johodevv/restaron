# Tuzatishlarni ishchi serverga qo‘llash

2026-10-23, Asia/Tashkent. Foydalanuvchi “serverni qayta ishga tushiraver” deb ruxsat berdi. Tekshiruv paytida 8000 va 8027 portlarida server ishlamayotgan edi; boshqa jarayon majburan to‘xtatilmadi.

- Ishga tushirishdan oldin zaxira: `backups/server_restart/20261023T172616Z-97e34783.db`; SHA256 va sanog‘i shu nomdagi `.json`da.
- Ishchi `.venv`da `python-multipart==0.0.32`, `python-jose==3.5.0` o‘rnatildi. Shu versiyalar bilan chaqiruvlarning 7 ta alohida sinovi yana o‘tdi. Avvalgi umumiy natija: 136 passed.
- `frontend_build.build_is_current` frontendni joriy manbaga mos deb tasdiqladi. Mavjud tayyor build saqlandi; ortiqcha qayta build qilinmadi.
- `server_manager.py serve` yashirin oynada ishga tushirildi. Backend 22:27:08 da qayta ishga tushgan; haqiqiy server logida PID 10760. Nazoratchi yozgan launcher PID 16168.
- Lokal `/health` 200, baza ulanishi `connected`, disk holati `ok`. `/` 200 va uzatilgan HTML diskdagi build bilan aynan bir xil; barcha kirish JS/CSS assetlari ham 200 va SHA256 bo‘yicha mos.
- Ruxsatsiz chaqiruvlar ro‘yxatiga murojaat 403 bilan rad etildi.
- Internet tunnel qayta ishga tushgan. `https://dunyochoyxona.uz/health` oddiy User-Agent bilan 200/healthy qaytardi. Dastlab Pythonning standart User-Agent so‘roviga Cloudflare 403/1010 qaytargan. [Cloudflare hujjati](https://developers.cloudflare.com/support/troubleshooting/http-status-codes/cloudflare-1xxx-errors/error-1010/) bu javob klient imzosiga bog‘liq cheklov ekanini tushuntiradi. Cloudflare xavfsizlik sozlamalari o‘zgartirilmadi.
- Printer navbatida pending/printing/uncertain vazifalar 0; Windows navbati ham 0. Sinov cheki yuborilmadi.

## Ma’lumotlar holati

Zaxira olinishidan oldin ham orders, order_items, receipt_archives va debts jadvallarida 0 ta satr bor edi; printer tarixida 211 ta satr bor edi. Ishga tushirishdan keyingi sonlar aynan shu holatda. Bu ishga tushirish davomida savdo yozuvlari o‘chirilmadi, eski zaxira ishchi bazaning ustiga tiklanmadi.

Oldingi navbat tozalash tekshiruvida aniqlangan 38 ta FK nomuvofiqligi ushbu amaldan oldin mavjud bo‘lgan va restartda tuzatilmadi. `/health`dagi `healthy` baza ulanishi va disk tekshiruvini bildiradi; barcha tarixiy FKlar toza degani emas. Printer navbati 0 bo‘lgani alohida tekshirildi.

Dalillar: `scratch/server_restart_smoke.json`, `scratch/server_restart_public_normal_header_smoke.json`, `scratch/server_restart_dependency_install.txt`, `scratch/fixes_20261023/scratch/call_tests_production_dependencies.txt`, `scratch/latest_server_restart.json`.

Oldingi hisobotlardagi “yangi kod hali serverga qo‘llanmagan” holati ushbu ishga tushirish bilan yangilandi. Bu fizik printer, telefon brauzeri yoki barcha choyxona ssenariylari qaytadan sinovdan o‘tdi degani emas.
