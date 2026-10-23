# RestAron: tuzatish va qayta tekshirish hisoboti

2026-10-23. Bu hujjat dastlabki AUDIT_REPORT_2026-10-23.md dan keyingi holatni ko‘rsatadi. Ishchi baza haqiqiy savdo bazasi ekanligi foydalanuvchi tomonidan tasdiqlangan.

Dastlab tuzatishlar manba kodda va sinov buildi scratch/fix-final-dist ichida edi. Foydalanuvchi xizmatni ishga tushirgach eski frontend/dist sabab qora ekran tasdiqlandi. 2026-10-23 kuni ishchi frontend build zaxiradan so‘ng yangilandi va jonli domen brauzerda tekshirildi; tafsilot BLACK_SCREEN_FIX_2026-10-23.md da. Bu frontend yangilashida server qayta ishga tushirilmadi va savdo bazasiga yozilmadi. Umumiy ishga tushirish bo‘yicha quyidagi cheklovlar saqlanadi.

## Asosiy natija

Koddagi buyurtma, to‘lov, avans, nasiya, printer navbati, restoranlar ajratilishi va POS sinxronlash xatolari uchun tuzatishlar kiritildi. 100 avtomatik test o‘tdi. 30 alohida ofitsiant va 30 jonli WebSocket bilan 150 amal yakunlandi: xato, yo‘qolgan buyurtma va summa tafovuti qayd etilmadi.

Bu natija dasturda umuman bug qolmaganini yoki katta choyxonada to‘liq ishga tushirish tasdiqlanganini anglatmaydi. Jismoniy printerlar, haqiqiy Wi-Fi va 30 telefon bilan sinov, uzoq muddatli ish, elektr uzilishi va PostgreSQL yuklamasi bajarilmagan. Eski savdo tarixida dalili yetishmaydigan 16 ta tafovut saqlangan.

## Tekshiruvlar va dalillar

| Tekshiruv | Yakuniy natija | Dalil |
|---|---|---|
| Backend regression | **100 passed**, 75.43 s | scratch/fix_final_pytest_log.txt |
| Qo‘shimcha regressionlar | Dastlabki 69 testga 31 holat qo‘shildi | backend/tests/test_audit_regressions.py |
| Production build | O‘tdi; yakuniy build logi saqlangan | scratch/fix_final_build_log.txt |
| Frontend–API manzillari | 131 chaqiruv; mos kelmagan manzil yo‘q | scratch/audit_route_contracts.py |
| TCP yuklama | 30 user + 30 WS + 150 amal, 0 xato | scratch/fix_final_tcp_load.json |
| Migratsiya | Ishchi bazaning yangi nusxasida 2 marta; eski ustunlardagi qiymatlar o‘zgarmadi; integrity=ok | scratch/fix_shadow_migration.json |
| Tiklash | 2 hisob, 4 ta taom qatori; to‘lovlar o‘zgarmadi; takrorlash 0 yangi qator | backups/receipt_restore_result_20261023.json |
| UI | Ofitsiant/admin POS, tez + bosish, stol tanlovi, 2 oshxona KDS filtri, tayyorlash, sozlamadan LAN IP va KDS toggle, naqd checkout | scratch/fix_pos_verified.png, scratch/fix_kds_verified.png |
| PDF | Unicode, mahalliy vaqt, uzun nomni o‘rash, avans/aralash to‘lov/izoh bilan footer chegaralari | regression testi va scratch/pdf_receipt_validation/ |

273 ta test ogohlantirishi asosan Pydantic, jose va eski test kutubxonalari deprecation xabarlaridir. Yakuniy logda test yiqilishi, yopilgan event loop yoki unhandled thread xatosi qayd etilmadi. Testlar barcha eski yordamchi skriptlar va har bir mumkin bo‘lgan UI kombinatsiyasini qamrab olmaydi.

## 30 ofitsiant: tezlik va ma’lumot yaxlitligi

Loopback TCP, SQLite WAL + FULL, alohida loginlar, 30 WebSocket, simulyatsiya qilingan printerlar. Har bir ofitsiant o‘z stolida yaratish → taom qo‘shish → +1 → oshxona → kassada to‘lash oqimini bajardi. Shu o‘lchov paytida boshqa test/build va brauzer fon so‘rovlari to‘xtatilgan.

| Amal | p95 | Eng sekin |
|---|---:|---:|
| Buyurtma yaratish | 1.49 s | 1.58 s |
| Taom qo‘shish | 1.71 s | 1.75 s |
| Miqdor +1 | 2.50 s | 2.55 s |
| Oshxonaga yuborish | 2.47 s | 2.53 s |
| Checkout | 3.09 s | 3.10 s |

- 150 biznes amali: 10.72 s; parallel loginlar: 1.45 s.
- 30 ta to‘langan hisob; subtotal 900 000; yangi naqd tushum 990 000; nomuvofiq hisob 0.
- Har bir WebSocket kamida 181 xabar oldi; 900 new_order, 1 800 order_updated, 1 800 table_status_updated va 900 order_paid yetkazilishi qayd etildi.
- 30 mock printer vazifasi done bo‘ldi; so‘rovlar tugagach navbatning bo‘shashi yana 2.14 s oldi. Bu qog‘oz chiqqanini tasdiqlamaydi.

Dastlabki auditdagi 30 user ASGI yaratish p95=19.84 s edi. Yakuniy TCP sinovi boshqa sharoitda bajarilgani sababli buni qat’iy bir xil benchmarkdagi tezlashish koeffitsiyenti deb ko‘rsatmaymiz. Bu safargi oraliq TCP yugurishlarida 8–14 s gacha p95 ham ko‘rildi; fon yuklamasi va kod holati farq qilgan. Faqat eng yaxshi natijani umumiy kafolat sifatida qabul qilish mumkin emas.

Profilash tenant-filter ifodalarini qayta qurish xarajatini ko‘rsatdi. Filtrlar restoran bo‘yicha cheklangan keshda qayta ishlatiladi; har ORM so‘rovida ajratish qo‘llanadi. Alohida 6 amalli mikro-sinov 0.910 s dan 0.234 s ga tushdi, SQL soni 134 bo‘lib qoldi. Dalillar: scratch/tenant_profile_before.json, scratch/tenant_profile_after.json, scratch/fix_backend_profile.dat. Xavfsizlik va umumiy 100 test optimizatsiyadan keyin qayta o‘tdi.

## Dastlabki xatolar bo‘yicha holat

| Band | Nima o‘zgardi | Tasdiq / chegara |
|---|---|---|
| A01 | LanguageProvider importi, sahifa ishga tushishi | Build + haqiqiy brauzer |
| A02 | Idempotency kaliti, so‘rov fingerprinti va javob biznes o‘zgarishi bilan bitta tranzaksiyada | 10 parallel bir xil add/delta/checkout faqat bir marta qo‘llandi; boshqa body=409 |
| A03 | Qarz to‘lovlari append-only tarix, qulf bilan | 20 parallel to‘lovning barchasi saqlandi |
| A04–A05 | O‘chirish, miqdor va checkout umumiy qulf tartibi, yopilgan hisobni himoyalash | Delete/checkout va ikki delete poygalari; summalar mos |
| A06 | Menyu taomini soft-delete, eski narx va nom snapshoti | Eski buyurtma/chek saqlandi; keyingi menyu o‘zgarishi tarixni almashtirmaydi |
| A07–A08 | Ommaviy settings allowlist, maxfiy kalitlar yashirilishi, ORM tenant ajratish va yozuv tekshiruvi | Begona taom/settings/order sinovlari; raw SQL bo‘lgan har yangi marshrut alohida review talab qiladi |
| A09 | SQLite yozuv navbati, BEGIN IMMEDIATE, umumiy lock tartibi va bir server instance himoyasi | Yakuniy 30 user TCP/WS sinovida 0 lock xatosi; 100 user uchun kafolat emas |
| A10–A11 | Ikki xil POS bitta komponentga birlashtirildi; print-bill, size va notes manzillari asosiy oqimdan ishlatiladi | 131 API contract tekshiruvida eski 3 noto‘g‘ri manzil yo‘q; manual bill regressioni o‘tdi |
| Eski savdo bazasi | Read-only diagnostika, zaxira, PDF hash bilan tiklash, noaniq summaga odatiy tahrir/checkoutni bloklash | 18 ta tafovutdan 2 tasi tiklandi; **16 tasi dalilsiz qolgan** |
| A12–A14 | Oshxona outbox, immediate yuborish, konfiguratsiyasiz amalni rollback, yopilgan hisobni yuborish cheklovi | Printer yo‘q=400; qayta sozlagach 1 job; KDS-only rejim ham ishlaydi |
| A15–A16 | Oldingi unit_price saqlanadi; vaznli taom alohida qator; o‘lchov turini tarix borida almashtirish bloklanadi | Narx/vazn/rename/soft-delete regressionlari |
| A17–A18 | Naqd checkoutdan noto‘g‘ri nasiya yaratilmaydi; nasiya toggle serverda tekshiriladi | Cash/debt/mixed sinovlari |
| A19 | Avans yakuniy qarzdorlikdan ayriladi; avansning pul harakati alohida tarixda | 11 000 hisob − 5 000 avans = 6 000 yangi to‘lov; hisobot va smenada qayta sanalmaydi |
| A20 | Transfer qulfi, rezerv/avans ko‘chishi, parallel konflikt | Ikki parallel transfer=200/409; avans yo‘qolmaydi |
| A21 | Z-yopish seri, to‘langan hisob va qo‘shimcha tushumlar | Parallel Z=200/409; yangi pul harakatisiz takror bloklanadi |
| A22 | Eski table checkout asosiy checkoutga yo‘naltirildi | 1 final archive; bittadan ko‘p eski ochiq hisob bo‘lsa konflikt |
| A23 | Sozlamalar diapazonlari va enumlar | Manfiy foiz/noto‘g‘ri qog‘oz eni/retention rad etiladi |
| A24 | HTTP/optional auth/WS approval va token revocation bir xil; logout serverga yuboriladi | Bekor qilingan token xotira tozalangach ham yaroqsiz |
| A25 | Chaqiruv va QR buyurtmasiga stol tokeni; lokal QR rasm | Token yo‘q=403; QR buyurtma retry dublikat qilmaydi |
| A26 | Buyurtma turi Literal, item soni chegarasi, bo‘sh draft aniq | Noma’lum tur/oddiy bo‘sh buyurtma rad etiladi |

Moliyaviy tarixning barchasi tuzatildi deb umumlashtirish mumkin emas.

## Qo‘shimcha tuzatishlar

- Admin va ofitsiant bitta POSdan foydalanadi. Kechikkan javob boshqa stol savatini almashtirmaydi; harakatlar navbatga olinadi; sessiyada natijasi noma’lum amal kaliti saqlanadi. Kalit foydalanuvchi ID bilan bog‘lanadi, qayta login yangi dublikat kalit yaratmaydi. Server kalitlarni 24 soat saqlaydi; bundan eski noaniq amalni qaytarishdan oldin hisob tekshirilishi kerak.
- Checkout oynasi ochilganidan keyin hisob o‘zgarsa expected_version tekshiruvi 409 qaytaradi.
- WebSocket sana obyektlari JSONga aylantiriladi. Oldingi uzilish brauzer + TCP sinovida topildi va regression bilan yopildi. Querydagi tokenlar server logida yashiriladi.
- KDS admin paneldan yoqiladi/o‘chiriladi; 1/2-oshxona va ichimliklar filtri bor. Tayyorlangan miqdor alohida saqlanadi: oldingi 1 ta tayyor taomga 2 ta dozakaz bo‘lsa KDS faqat 2 tasini ko‘rsatadi. Ekrandagi eski miqdorni tayyor qilish urinishiga 409 qaytariladi.
- USB kassa printeri mijoz hisobi va ichimliklarga; ikki LAN printer tegishli oshxonalarga yo‘naltiriladi. IP va Windows nomlari admin sozlamalarida; bo‘sh maydonlar o‘rniga taxminiy IP saqlanmaydi. Bir xil ikki oshxona manzili uchun ogohlantirish bor.
- Printer job atomar olinadi. Uzatish natijasi noaniq bo‘lsa uncertain; operator qog‘oz chiqqanini tasdiqlaydi yoki TAKROR belgisi bilan yuboradi. Mavjud bo‘lmagan orderga bog‘langan eski job avtomatik chop etilmaydi.
- Eski table-bill orqali taomni qaytarish ham bekor qilish chekini atomar navbatga qo‘yadi. Xato bo‘lsa taom va summa saqlanadi.
- POSda uzun stol sarlavhasi, ortiqcha takroriy mobil boshqaruvlar va stol ro‘yxatining savatni siqishi tuzatildi; stol brauzeri alohida ochiladi. Taom kartalari klaviaturadan ham ishlaydi. Asosiy UZ/ЎЗ/RU/EN POS yozuvlari o‘girildi; butun admin panelning barcha tarjimalari yakunlangan deb hisoblanmaydi.
- Og‘ir barcha rasmlarni preload qilish olib tashlandi; faol orderlar alohida olinadi. Ekranlar active limit=300 ishlatadi; 300 dan ortiq bir vaqtning o‘zida faol hisob uchun pagination hali yo‘q.
- Eski taom nomlari uchun yangi snapshot migratsiya paytidagi mavjud menyudan olinadi. Avval o‘zgartirilgan tarixiy nomni dalilsiz tiklash mumkin emas; kelgusidagi nom o‘zgarishlari esa yangi snapshotni almashtirmaydi.
- SQLite WAL/FULL, foreign_keys, writer navbati va bir server instance himoyasi bor. PostgreSQL migratsiya SQLi/indekslari moslashtirilgan, ammo real PostgreSQLda ishlatilmagan. Docker WS/uploads proxy va majburiy secret/parol sozlamalari tuzatildi; Docker bu kompyuterda mavjud emasligi sababli konteyner sinovi bajarilmadi.

## Haqiqiy bazada nima qilindi

Avval consistent backup olindi. 6 va 11-ID hisoblarning asl PDFlari yakuniy chek arxivi hamda to‘lovlarga mosligi tekshirildi. Nusxada repetitsiya, takroriy qo‘llash va qolgan jadvallarni solishtirishdan so‘ng haqiqiy bazaga faqat 4 ta yo‘qolgan taom qatori va tiklash audit yozuvi qo‘shildi. To‘lov, qarz, hisob summasi, stol va menyu qiymatlari o‘zgarmadi.

Qolgan 16 tafovut uchun asl chek yo‘qligi foydalanuvchi tomonidan tasdiqlangan. Batafsil ro‘yxat va zaxira manzillari: **backups/RECONCILIATION_2026-10-23.md**. Dalil yo‘qligi ma’lumotni “to‘g‘ri” deb belgilash yoki summalarni nolga tushirishga asos emas.

Ishchi bazaning tarixiy printer navbatida 106 pending va 19 uncertain bor. 17 job mavjud bo‘lmagan orderga bog‘langan. **Ishchi serverni qayta yoqishdan oldin navbat ko‘rib chiqilishi kerak**: oddiy pending joblar avtomatik qayta urinadi. Ishchi server bu tekshiruv uchun ishga tushirilmadi; UI/yuklama serveri faqat scratch bazalari va mock printerlardan foydalandi.

## Ishga tushirish bo‘yicha baho va qolgan ish

**Hozircha katta choyxonada to‘liq ishga tushirishga yakuniy ruxsat xulosasi berilmaydi.** Sabablar aniq:

1. Eski 16 tafovut, 40-ID stoldagi 3 ochiq hisob va eski printer navbati bo‘yicha egasi/kassir qarori kerak. Asl cheklar yo‘qligi qayd etilgan; tarixni tiklangan deb ko‘rsatish mumkin emas.
2. To‘g‘ri USB/LAN sozlamalari admin panelga kiritilib, uchala printerda test chek, buyurtma, ichimlik, otmena, final bill va uzilib-qayta ulanish joyida sinalishi kerak. Drayverning Normal holati jismoniy chop etish dalili emas.
3. 30 haqiqiy qurilma bilan choyxona Wi-Fi tarmog‘ida sinov va navbatning maqbul vaqt ichida chiqishi tasdiqlanishi kerak. Lokal p95=1.49–3.09 s bo‘lishi har bir telefon/tarmoq uchun kafolat emas.
4. PostgreSQL, ko‘p jarayon, Docker deployment, elektr/disk uzilishi, 24–72 soatli ishlash va off-device zaxiradan tiklash hali tekshirilmagan. Bir instance himoyasini olib tashlab bir nechta worker ochish mumkin emas: WS/ratelimit xotirada.
5. Pul ustunlari hali Float. Hozir ikki kasrga yaxlitlash va balans tekshiruvlari bor; saqlash turini Numeric/integerga ko‘chirish tarix uchun alohida migratsiya va solishtirish talab qiladi. Bu bajarildi deb belgilanmagan.

Asosiy buyurtma va kassa oqimlari sinovlarda ancha yaxshilandi. Kuzatilmagan holatlarni “bug yo‘q” deb kafolatlamaymiz. Keyingi amaliy bosqich — tarix/navbat bo‘yicha qarorni rasmiy qayd etish va sozlangan haqiqiy qurilmalarda cheklangan pilot sinovi.
