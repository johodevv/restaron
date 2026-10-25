# RestAron — tuzatishlar va tekshiruv natijalari

Sana: 2026-10-23. Manba: `REAUDIT_REPORT_2026-10-23.md` va foydalanuvchi yuborgan audit hisoboti. Boshlang‘ich commit: `396037575e5b69c5758fe7a3cb44472cbb48cdd3`. O‘zgarishlar lokal ishchi katalogda; commit/push va hostingga deploy bajarilmadi.

**Asosiy funksional xatolar tuzatildi, test deb tasdiqlangan eski hisoblar ma’lumot o‘chirmasdan tartibga keltirildi. Tezlik yaxshilandi, biroq 100 ofitsiantning bir vaqtdagi cho‘qqi yuklamasida kutish hali katta. Katta choyxonaga darhol to‘liq tarqatish uchun fizik printer va haqiqiy tarmoqdagi qabul sinovi ham kerak.**

## Tuzatilgan xatolar

| Audit | Natija |
|---|---|
| F01 — paid → served tufayli kassa hisoboti kamayishi | To‘langan hisobning moliyaviy `PAID` holati saqlanadi. Taom tayyor bo‘lgach yetkazish `served_at` bilan qayd etiladi. To‘lov va yetkazish smena tushumini o‘zgartirmasligi tekshirildi. |
| F02 — oshxonaga yuborilmasdan checkout | Checkout yuborilmagan taomlarni oshxona navbatiga to‘lov bilan **bitta tranzaksiyada** yozadi. Printer/KDS sozlamasi yaroqsiz bo‘lsa to‘lov ham, yuborish ham rollback bo‘ladi. Bir kalitli retry ikkinchi chek/to‘lov yaratmaydi. |
| F03 — oldindan to‘langan taom KDSdan yo‘qolishi | KDS moliyaviy yopilishga emas, yuborilgan va tayyorlangan miqdor farqiga qaraydi. Paid taomni tayyorlash mumkin. Alohida `ready_for_delivery` filtri va ofitsiantning tayyor taomlar ro‘yxati oldindan to‘langan buyurtmalarni ham ko‘rsatadi. |
| F04 — boshqa qurilmadagi delta savatga tushmasligi | Socket xabarida stol IDsi bir xil shaklga keltiriladi; frontend ichki `order.table_id`ni ham qabul qiladi. Savat, buyurtma ro‘yxati va stol summalari yangilanadi. Eski versiya yangisini bosib ketmaydi. Poll savat, tayyorlar va chaqiruvlarni tiklaydi. |
| F05 — chaqiruvlarni yakunlash | Yangilash aynan o‘sha stol bilan cheklangan. 61-stol bo‘yicha qo‘shimcha murojaatda eski orderdan tiklangan chaqiruv IDsi endpoint bilan mos emasligi ham aniqlandi va tuzatildi. Tafsilot: `WAITER_CALL_FIX_2026-10-23.md`. Joriy umumiy tekshiruv: 136 test o‘tdi; backend hali qayta ishga tushirilmagan. |
| F06 — stop-listni `+` orqali aylanib o‘tish | Delta va mutlaq miqdorni oshirishda mavjudlik, stop-list va o‘chirilganlik tekshiriladi. |
| F07 — yuborilgan taom hajmi oshxonaga xabarsiz almashishi | Oshxonaga yuborilgan qatorning hajmini yashirin almashtirish 409 bilan to‘xtatiladi. Eski taomni ruxsatli bekor qilish va yangisini qo‘shish kerak; oddiy o‘zgarmagan hajmni saqlashga ruxsat bor. |
| F08 — mavjud Debt noto‘g‘ri summa bilan qayta ishlatilishi | Qarz summasi, qoldig‘i va to‘langan qismi checkoutga mos bo‘lmasa butun amal 409 bilan rad etiladi. Qo‘lda qarz yaratish orqali order qarzini oldindan band qilish yopildi. |
| F09 — noma’lum mijozga nasiya | Checkoutda haqiqiy ism va kamida 7 raqamli telefon talab qilinadi. |
| F10 — boshqa restoranning orderiga Debt bog‘lash | Restoran/order mosligi tekshiriladi; orderga bog‘langan qarz faqat checkout tranzaksiyasida yaratiladi. Umumiy tenant FK tekshiruvi ham kengaytirildi. |
| F11 — begona taomga review va o‘chirilgan baholash | `allow_reviews` bajariladi. Buyurtma, restoran, stol QR kodi, taom va ofitsiant mosligi tekshiriladi; takroriy baho va tez-tez yuborish cheklanadi. Frontend QR tokenini yuboradi. |
| F12 — begona restoran notification cleanup | Restoran ruxsati fon vazifasini rejalashtirishdan oldin tekshiriladi. Fon yozuvi SQLite yozish navbatidan foydalanadi. |
| F13 — notification cleanup 500 | Noto‘g‘ri funksiya argumentlari olib tashlandi; tozalash joriy ruxsatli tranzaksiyada bajariladi. |
| F14/F15 — ochiq stolni bo‘shatish/yashirish | Umumiy PATCH orqali ham ochiq hisobli stolni bo‘shatish, bron holatiga o‘tkazish yoki yashirish 409 qaytaradi. Avansli stolni yashirish himoyalangan. |
| F16 — noto‘g‘ri qiymatlar va tarixli qarzni o‘chirish 500 | Stol raqami/sig‘imi, bo‘sh qiymatlar, narxlar tekshiriladi. Topilmagan order uchun boshqarilgan xato qaytadi. To‘lov yoki order tarixi bor qarz 409 bilan saqlanadi. |
| F17 — bitta buzilgan printer boshqa navbatni to‘sishi | Global 50 ta eski job o‘rniga printerlar bo‘yicha eng eski tayyor vazifalar tanlanadi. 100 ta sekin vazifa ortidagi boshqa printerning vazifasi alohida testdan o‘tdi. |
| F18 — PDF fallback noto‘g‘ri summa/nom | Restoran sozlamalari, avans, chegirma va olinadigan qoldiq qo‘shildi. Toshkent sanasi va aniq fayl nomi ishlatiladi; substring orqali begona chek topish to‘xtatildi. PDF yaratish event loopdan tashqarida bajariladi. |
| F19 — statistika JOIN tufayli ko‘payishi | Buyurtmalar va baholar alohida agregatsiya qilinadi. Ikki buyurtma va uch baho endi olti buyurtma bo‘lib sanalmaydi. |
| F20 — cho‘qqi yuklama | SQLite ulanishlari qayta ishlatiladi; buyurtma/taom/stol/ofitsiant bitta JOIN bilan yuklanadi; o‘zgarmagan FKlar qayta-qayta tekshirilmaydi; ortiqcha qayta yuklash va no-op yozuv qisqartirildi. Socket yuborish har bir ulanish uchun chegaralangan FIFOga ajratildi. **Tezlik muammosi to‘liq yopilgan deb baholanmaydi.** |
| F21 — Render ephemeral SQLite | Blueprint persistent disk, saqlanadigan DB/upload/PDF/backup yo‘llariga o‘zgartirildi. **Hostingga qo‘llanmadi. `starter` va disk pullik resurslar; mavjud ma’lumotlar avtomatik ko‘chirilmaydi.** |
| F22 — xavfli yangilash BAT | Ishlab turgan 8000-portda yangilash to‘xtatiladi; majburiy process/global cloudflared o‘ldirish olib tashlandi. Backup, `git pull --ff-only`, dependency xatolari va staging build tekshiriladi. Eski hashed assetlar saqlanadi. To‘liq BAT ishchi muhitda bajarilmadi. |
| F23 — dependency xavfsizligi | `python-multipart=0.0.32`, `python-jose=3.5.0`, Vite 6.4.5 va Tailwind 3.4.19 bilan tekshirildi. Vite dev serveri localhostga bog‘landi. **npm dev/build zanjirida 7 ta advisory yozuvi qolgan; production auditda 0.** |

## Ma’lumot saqlanishi va aniqlik

SQLite `WAL`, `synchronous=FULL`, tashqi kalitlar va `BEGIN IMMEDIATE` himoyasi saqlandi. Tezlashtirish uchun diskka ishonchli yozish o‘chirilmagan. Oshxona joblari, to‘lov, chek arxivi va idempotency javobi bitta tranzaksiyada yoziladi.

Pul hisoblashning asosiy yo‘llariga Decimal va `ROUND_HALF_UP` yordamchisi qo‘shildi: qator narxi, checkout, xizmat haqi va jami ikki xonali aniqlikda normallashtiriladi. Noto‘g‘ri/cheksiz narxlar rad etiladi. **Tarixiy Float ustunlari boshqa turga ommaviy migratsiya qilinmadi; barcha moliyaviy modul Numericga o‘tdi degan da’vo yo‘q.**

Idempotency kaliti avvalgidek saqlanadi. Cho‘qqi yuklamada commit bo‘lgan amalni foydalanuvchi xato deb tushunmasligi uchun idempotent yozish so‘rovlarining kutish oynasi 60 soniya qilindi. Oddiy GET 15 soniya, boshqa yozishlar 25 soniya. Bu kutish oynasi tezlik yaxshilangani o‘rnidagi dalil emas. Internet uzilsa, ayni kalitli qayta urinish qo‘llanadi va natija noma’lumligi tushunarli yoziladi.

## Foydalanuvchi test deb tasdiqlagan eski yozuvlar

Foydalanuvchi quyidagi 16 ta nomuvofiq hisob va 40-stoldagi uch hisob test ma’lumotlari ekanini aniq tasdiqladi:

`1, 4, 9, 10, 13, 14, 15, 16, 36, 37, 38, 39, 55, 61, 63, 64`.

Avval haqiqiy bazaning nusxasida sinov qilindi. Keyin asl bazada atomar tranzaksiya bilan:

- Asl baza va tegishli satrlarning to‘liq snapshoti saqlandi.
- Faqat tasdiqlangan test hisoblari bekor qilingan holatga o‘tkazildi; summa taom qatorlariga moslashtirildi va test to‘lovlari nol qilindi. Asl summalar audit jurnalida va zaxirada bor.
- 17 ta buyurtmasi yo‘q printer FKsi tiklandi: yo‘q order IDsi auditga ko‘chirildi, yaroqsiz FK NULL qilindi. Bajarilmagan bunday vazifalar avtomatik bosilmaydigan `cancelled` holatiga olindi; tugallangan vazifa tugallanganicha qoldi.
- 40-stol bo‘shadi. Bitta stolda bitta ochiq hisobni kafolatlaydigan `ux_orders_one_open_per_table` indeksi yaratildi.
- Buyurtma yoki chek satrlari o‘chirilmadi; 33 ta audit yozuvi qo‘shildi.

| Jadval | Oldin | Keyin |
|---|---:|---:|
| Buyurtmalar | 82 | 82 |
| Buyurtma taomlari | 125 | 125 |
| Chek arxivi | 138 | 138 |
| Printer vazifalari | 210 | 210 |

Asl holat zaxirasi: `C:/RestAron/backups/confirmed_test_repair/20261023T121020Z-814f63c2.db`.

Satrlar arxivi va backup SHA256: `C:/RestAron/backups/confirmed_test_repair/20261023T121020Z-814f63c2.json`.

Tuzatishdan keyingi snapshot: `integrity_check=ok`, FK xatosi 0, nomuvofiq hisob 0, takroriy ochiq stol 0, qarz/order tafovuti 0. `healthy=true` aynan shu tekshiruvlarni bildiradi; butun mahsulotda bug yo‘qligi emas. Printerlarning pending/printing/uncertain holatlari real jarayon bilan o‘zgaradi va fizik qog‘oz chiqqanini ushbu tekshiruv isbotlamaydi.

Yordamchilar:

- `backend/tools/check_data_health.py` — faqat o‘qiydigan tekshiruv; `--database` va ixtiyoriy `--output` oladi. Xato topilsa exit code 2.
- `backend/tools/repair_confirmed_test_orders.py` — aniq test IDlari uchun; standart holatda dry-run. Umumiy haqiqiy savdoni qayta hisoblash uchun ishlatilmasin. Avans/qarz tarixi yoki hozir chop etilayotgan tegishli job bo‘lsa to‘xtaydi.
- `backend/tools/restore_db.py` — app instance qulfini ololmasa tiklashni rad etadi. Joriy bazaning xavfsiz backupi yaratilmasa davom etmaydi; tekshirilgan staged fayl atomar almashtiriladi.
- Tashqi zaxiralash xatosi endi muvaffaqiyatli exit code bilan yashirilmaydi; alohida media yo‘llari ham qo‘llanadi.

## Sinov natijalari

Yakuniy umumiy test: **129 passed**, 10 warning, 147.25 soniya. Dalil: `scratch/fixes_20261023/scratch/full_tests_final_release.txt`. Shu to‘plamdagi backup/tiklash tekshiruvlari alohida ham **9 passed** natija berdi. Frontend savat sinxronlash testlari: **3 passed**. Production build: **o‘tdi**, 13.45 soniya. `git diff --check` o‘tdi.

Sinov bazalari ishchi savdo bazasidan ajratilgan. Yozishlar va printer sinovlarida sun’iy baza va adapter ishlatilgan. Ishchi bazadagi yagona rejalashtirilgan tuzatish yuqorida foydalanuvchi tasdiqlagan test yozuvlari va yetim printer FKlarini arxivlashdir. Ishlab turgan server o‘z odatiy fon ishlarini davom ettirgan bo‘lishi mumkin.

Yangi regressionlar to‘lov/yetkazish, oldindan to‘lov → KDS → tayyor → yetkazish, atomic checkout rollback/retry, stop-list, hajm, stol, nasiya, tenant, chaqiruv qayta yuborilishi, notification cleanup, review QR, PDF payload, statistika, sekin printer, Decimal, test ma’lumotlarini saqlab tuzatish, restore qulfi va sekin socket/FIFO holatlarini qamrab oladi.

## Tezlikning yakuniy o‘lchovi

Sharoit: loopback HTTP, bir backend, SQLite WAL/FULL, ofitsiantlar uchun alohida login va WebSocket, sun’iy printer. Har ofitsiant yaratish → qo‘shish → delta → oshxona → checkout oqimini bajardi. Mijoz testida timeout 90 soniya. Bu haqiqiy Wi-Fi va 100 telefon sinovi emas. 1 va 30 ofitsiant namunalari o‘sha test serverida oldingi 100 ta to‘langan hisobdan keyin bajarildi.

| Amal | 1 foydalanuvchi, bitta namuna | 30 ofitsiant p95 | 100 ofitsiant p95 |
|---|---:|---:|---:|
| Yaratish | 331 ms | 2.10 s | 18.69 s |
| Taom qo‘shish | 97 ms | 2.15 s | 18.04 s |
| Delta | 64 ms | 1.75 s | 22.77 s |
| Oshxonaga | 88 ms | 1.62 s | 20.52 s |
| Checkout | 105 ms | 2.16 s | 29.38 s |

| Natija | 1 | 30 | 100 |
|---|---:|---:|---:|
| Biznes amali | 5 | 150 | 500 |
| Umumiy oqim vaqti | 0.68 s | 9.24 s | 101.23 s |
| Yakuniy hisob tafovuti | 0 | 0 | 0 |
| HTTP xatosi | 0 | 0 | 0 |
| Bajarilgan sun’iy printer jobi | 1 | 30 | 100 |

100 ta hisobning subtotal yig‘indisi **3 000 000**, naqd tushumi **3 300 000**; 100 ta WebSocket xabar oldi. Eng katta checkout 30.05 soniya; oxirgi sinovda navbat HTTPlar tugagach 5.56 soniyada bo‘shadi.

Oldingi auditda 30 ofitsiant oqimi 14.12 s, 100 ofitsiant oqimi 140.85 s, checkout p95 mos ravishda 3.25 s va 38.18 s edi. Hozirgi raqamlar yaxshiroq, lekin qat’iy bir xil sharoitdagi ilmiy A/B o‘lchovi emas. Oraliq optimizatsiya yugurishlarida 100 ofitsiant oqimi 52.41 s va 91.10 s ham bo‘ldi; **52.41 s eng yaxshi natijani doimiy kafolat sifatida ko‘rsatish noto‘g‘ri**. Hostda boshqa jarayonlar ishladi; o‘lchov atrofidagi snapshotda CPU 71%, bo‘sh RAM taxminan 0.9 GiB edi. Aynan qaysi omil qancha vaqt qo‘shgani ajratilmadi.

**Xulosa:** bitta foydalanuvchida asosiy amallar qisqa; 30 ofitsiant burstida sezilarli yaxshilanish bor. 100 kishi birdan faol yozganda SQLite yozish navbati hali cheklov. 60 soniyalik retry oynasi bu holatni tezlashtirmaydi. PostgreSQLga o‘tish yoki worker sonini ko‘paytirish tayyor isbotlangan yechim deb aytilmaydi; joriy tenant lock, umumiy eventlar va printer egasi bilan birga alohida sinov kerak.

## Qolgan chegaralar va ishga tushirish

1. **F20 qisman ochiq:** 100 ofitsiant peakida 29 s checkout hali “darhol” emas. Choyxonaning maqsadli serverida, to‘liq frontend polling/rasm yuklanishi bilan, aniq maksimal oqim bo‘yicha qabul sinovi kerak.
2. **F23 qisman ochiq:** npm production dependency audit 0; dev/build zanjiri 7 yozuv — 5 high, 2 moderate. Qolgan zanjir Tailwind 3 bilan bog‘liq; Tailwind 4ga ko‘chirish dizayn va eski qurilma mosligini alohida tekshirishni talab qiladi. Ularning hammasi tuzatildi deyilmaydi.
3. **Brauzer tekshiruvi bloklangan:** Work sozlamalarida local browser use o‘chirilgan. Shu sabab ushbu tuzatishlarning yakuniy ekranlari, mobil ko‘rinishi va real brauzerdagi ikki qurilma sinxronlash jarayoni qayta ko‘rilmadi. Build va 3 ta JS mantiq testi vizual audit o‘rnini bosmaydi.
4. Fizik USB/LAN printer, kabel/tarmoq uzilishi, operatorning “chek chiqqan/chiqmagan” tekshiruvi, elektr uzilishi, disk to‘lishi, 24–72 soat soak va boshqa qurilmaga to‘liq tiklash bu sessiyada o‘tkazilmadi.
5. **Yangilanish, 2026-10-23 22:27:** foydalanuvchi ruxsatidan keyin ishchi backend joriy kod bilan ishga tushirildi; frontend manbaga mosligi va HTTP orqali berilayotgan fayllar tekshirildi. `.venv`ga python-multipart 0.0.32 va python-jose 3.5.0 o‘rnatildi. Lokal va internetdagi health tekshiruvi 200 qaytardi. Tafsilot va chegaralar: `SERVER_RESTART_2026-10-23.md`.
6. Render blueprint pullik persistent storagega tayyorlangan konfiguratsiya; hisob yaratish, pullik resurs olish yoki deploy bajarilmagan.
7. Aliposter 1.0.0.0 bilan bevosita o‘lchov yo‘q. “Aliposterdan tezroq” yoki “hech qanday bug qolmadi” degan kafolat berilmaydi.

## Dalillar

- Umumiy test: `scratch/fixes_20261023/scratch/full_tests_final_release.txt`.
- Qo‘shimcha backup test: `scratch/fixes_20261023/scratch/backup_final_tests.txt`.
- JS test: `scratch/fix_frontend_tests.txt`; build: `scratch/fix_build_release.txt`.
- Yuklama: `scratch/fixes_20261023/scratch/load_1.json`, `load_30.json`, `load_100.json`; server/harness ham shu papkada.
- Ishchi bazaning oldingi holati: `scratch/data_health_after_fixes.json`; tuzatilgan holati: `scratch/data_health_repaired.json`.
- Saqlangan satrlar soni: `scratch/test_repair_preservation.json`; qo‘llangan tuzatish: `scratch/confirmed_test_repair_applied.json`.
- Dependency: `scratch/pip_fix_dependencies.txt`, `scratch/npm_after_upgrade.json`, `scratch/npm_prod_verified.json`.
- Manba va test nusxasi mosligi: `scratch/fix_source_hashes.json`.

Texnik asoslar: [SQLAlchemy aiosqlite pool hujjati](https://docs.sqlalchemy.org/en/20/dialects/sqlite.html#pooling-behavior), [python-multipart relizi](https://pypi.org/project/python-multipart/), [python-jose 3.5.0](https://pypi.org/project/python-jose/3.5.0/), [Render persistent disk](https://render.com/docs/disks).
