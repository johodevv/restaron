# RestAron — qayta audit va ishga tushirishga tayyorlik hisoboti

Sana: 2026-10-23, Asia/Tashkent. Tekshirilgan commit: `396037575e5b69c5758fe7a3cb44472cbb48cdd3`.

## 1. Qaror

**Hozirgi holatda katta choyxonada to‘liq ishga tushirishni tavsiya qilmayman.** Buyurtma va pul hisobiga ta’sir qiladigan xatolar amalda takrorlandi. Mavjud bazada ham hisob tafovutlari bor. 100 ofitsiantli sun’iy sinov yakuniy ma’lumotlarni saqladi, lekin operatsiyalar frontendning 25 soniyalik kutish chegarasidan oshdi.

Bu xulosa taxminiy “dastur yomon” bahosi emas. Quyida har bir muhim xatoning kuzatilgan natijasi, kodi va dalili berilgan. Oldingi audit va tuzatish hisobotlari tarixiy ma’lumot sifatida o‘qildi; ularning natijalari yangi sinov o‘rnida ishlatilmadi.

**Mahsulot kodi, ishchi sozlamalar, ishchi frontend buildi va savdo yozuvlariga tahrir kiritilmadi.** Sinov nusxasi va dalillar `C:/RestAron/scratch/reaudit_20261023/` ichida. Mahalliy savdo bazasi `mode=ro` va `PRAGMA query_only=ON` bilan o‘qildi. Yuklama va yozish/o‘chirish sinovlari yangi sun’iy bazalarda bajarildi. Printer adapterlari sun’iy bo‘ldi; fizik printerga sinov buyurtmalari yuborilmadi.

“Barcha holatlar tekshirildi, endi hech qanday bug yo‘q” degan kafolat berilmaydi. 121 ta router marshruti inventarizatsiya qilindi, ammo har bir marshrutning barcha rol, qiymat, qurilma va uzilish kombinatsiyasi amalda sinalgani da’vo qilinmaydi. Bajarilmagan sinovlar 10-bo‘limda ochiq ko‘rsatilgan.

## 2. Nima bajarildi va nima o‘tdi

| Tekshiruv | Joriy natija | Chegarasi |
|---|---|---|
| Mavjud backend va build yordamchisi testlari | **107 passed**, 163.20 soniya; 270 ogohlantirish | Belgilangan test holatlari; barcha biznes kombinatsiyalari emas |
| Frontend production build | O‘tdi, 24.39 soniya | Alohida `build/` papkasiga; ishchi `frontend/dist` almashtirilmadi |
| Frontend–API manzillari | 130 chaqiruv, mos kelmagan manzil 0 | Statik manzil/metod mosligi; ichki mantiq to‘g‘riligini isbotlamaydi |
| Test nusxasi va asl manba | 123 ta Python/JS/JSX/CSS fayli hash bilan bir xil | Audit yordamchi skriptlari alohida |
| Python dependency mosligi | `pip check`: No broken requirements found | Bu xavfsizlik/CVE skaneri emas |
| npm to‘liq audit | 10 dependency yozuvi: 7 high, 3 moderate | Bir zaiflik zanjiri bir nechta paket yozuvida ko‘rinishi mumkin |
| npm production dependency audit | 0 ta ma’lum zaiflik qaytdi | Barcha zaifliklar yo‘qligiga kafolat emas; dev/build zanjiri alohida xavf |
| 30 ofitsiant / 30 WebSocket | 150 biznes amali; yakuniy summa mos, xato 0 | Loopback, SQLite, sun’iy printer |
| 60 ofitsiant / 60 WebSocket | 300 biznes amali; yakuniy summa mos, xato 0 | Sekinlashish katta |
| 100 ofitsiant / 100 WebSocket | 500 biznes amali; yakuniy summa mos, xato 0 | 90 soniyalik test mijozida; oddiy frontend 25 soniya kutadi |
| Qo‘shimcha maqsadli sinovlar | Kassa, KDS, chaqiruvlar, stop-list, stollar, qarzlar, tenant, PDF payload, printer navbati, statistika | Quyidagi yangi xatolar aynan shu sinovlarda topildi |
| Mahalliy savdo bazasi | Fayl tuzilishi `integrity_check=ok` | Moliyaviy va FK yaxlitligi bo‘yicha muammolar bor |

Mavjud testlarda bir stolga 20 parallel yaratish, 20 parallel `+1`, 5 parallel oshxonaga yuborish, 5 parallel checkout, bir xil kalitli 10 parallel retry, taom o‘chirish–checkout poygalari, avans, transfer, token bekor qilish va ruxsatlarning ayrim holatlari tekshirildi. Shu testlarning o‘tishi quyidagi topilmalarga zid emas: yangi holatlar eski testlarda qamrab olinmagan.

Muhit cheklovi ham qayd etildi: sandboxdagi oddiy `asyncio.sleep` tugamay qoldi, sandbox tashqarisida esa ishladi. Shundan so‘ng izolyatsiyalangan testlar tashqarida bajarildi. Alohida, parallel instrumentlangan diagnostika yugurishida Windows native `access violation` ham kuzatildi; uning ildiz sababi aniqlanmadi. U muvaffaqiyatli tugagan 107 test natijasiga qo‘shilmadi va ishlab turgan RestAron serveri qulagan deb talqin qilinmadi.

## 3. Tezlik: o‘lchangan natijalar

Sharoit: Windows 11, taxminan 7.7 GiB RAM, 6 mantiqiy CPU ko‘rinadigan muhit; bitta backend, SQLite WAL/FULL, haqiqiy loopback HTTP, alohida xodimlar, WebSocketlar va sun’iy printer adapteri. Har bir ofitsiant alohida stolida yaratish → qo‘shish → `+1` → oshxona → admin orqali checkout oqimini bajardi. Menyu va stol ma’lumotlari sun’iy. Haqiqiy Wi-Fi, 100 telefon, butun menyu rasmlari va real printerlar bu o‘lchovga kirmaydi.

Quyidagi p95 — o‘lchovlarning taxminan 95 foizi shu vaqtgacha yakunlanganini bildiradi. Bu bir martalik burst namunalari; sertifikatlangan maksimal sig‘im emas. 30/60/100 yugurishlarining HTTP ulanish siyosati ham to‘liq bir xil emas; ularni aniq tezlashish koeffitsiyenti sifatida ishlatmaslik kerak.

| Amal, p95 | 30 ofitsiant | 60 ofitsiant | 100 ofitsiant |
|---|---:|---:|---:|
| Buyurtma yaratish | 3.25 s | 6.56 s | 22.04 s |
| Taom qo‘shish | 3.28 s | 9.35 s | 27.87 s |
| Miqdor `+1` | 2.77 s | 11.25 s | 29.93 s |
| Oshxonaga yuborish | 2.73 s | 11.04 s | 30.86 s |
| To‘lov / checkout | 3.25 s | 18.69 s | 38.18 s |

| Natija | 30 | 60 | 100 |
|---|---:|---:|---:|
| Biznes amallari | 150 | 300 | 500 |
| Oqimlarning umumiy vaqti | 14.12 s | 54.83 s | 140.85 s |
| To‘langan hisoblar | 30 | 60 | 100 |
| Subtotal | 900 000 | 1 800 000 | 3 000 000 |
| Naqd tushum | 990 000 | 1 980 000 | 3 300 000 |
| Nomuvofiq yakuniy hisoblar | 0 | 0 | 0 |
| Sun’iy printerda `done` job | 30 | 60 | 100 |
| HTTP oqimlari tugagach navbatning bo‘shashi | 3.29 s | 8.68 s | 12.51 s |

**Amaliy ma’no:** shu sinovlarda buyurtma yoki summa yo‘qolmadi. Biroq “100 kishi tez va xatosiz ishlaydi” degan xulosa chiqmaydi. [api.js](C:/RestAron/frontend/src/utils/api.js:165) yozish so‘rovini 25 soniyadan keyin to‘xtatadi. 100 foydalanuvchida bir nechta amal bundan oshdi; brauzer timeout va qayta urinish holatiga tushishi mumkin. Test mijozining 90 soniya kutishi bu muammoni foydalanuvchi ko‘radigan darajada sinamagan.

Birinchi 60 foydalanuvchi yugurishi `httpx.ReadError` bilan tugagan. Yangi bazada, qayta ishlatiladigan HTTP ulanishlarisiz takrorlash o‘tdi; birinchi uzilish sababi to‘liq ajratilmadi. Birinchi 100 foydalanuvchi skripti server pingiga javob bermagani sabab WebSocketlar normal yopildi; bu yordamchi skript xatosi tuzatilib, yangi bazadagi yakuniy sinov o‘tdi. Xato yugurishlar ham dalillar papkasida saqlangan.

## 4. Ishga tushirishdan oldin tuzatilishi kerak bo‘lgan xatolar

P1 — savdo, oshxona, pul, mijoz chaqiruvi yoki ma’lumot ajratilishiga sezilarli ta’sir; ishga tushirishdan oldin tuzatish zarur. P2 — muhim funksional/ishlatish xatosi, aniq tuzatish va regression talab qiladi. Bu darajalar ekspluatatsiya tez-tezligi bo‘yicha statistik bashorat emas.

### F01 — P1: “Yetkazib berdim” to‘langan hisobni kassa hisobotidan chiqaradi

**Takrorlash:** 11 000 so‘mlik hisobni naqd to‘lash → shu hisobga ofitsiant tokeni bilan `PATCH /orders/{id}/deliver` yuborish.

**Natija:** HTTP 200, `is_paid=true`, lekin `status=served`. Smena previewda `total_orders` 4 dan 3 ga, savdo 44 000 dan 33 000 ga, naqd 33 000 dan 22 000 ga tushdi. Bazadagi pul ustuni saqlangan, hisobot uni sanamay qoldi.

**Sabab:** [deliver_order](C:/RestAron/backend/app/routers/orders.py:3346) `paid/is_paid` holatini rad etmaydi. [Smena hisoboti](C:/RestAron/backend/app/routers/receipts.py:846) va [jonli preview](C:/RestAron/backend/app/routers/receipts.py:1076) esa `status=PAID`ni talab qiladi.

**Tavsiya:** yopilgan hisobda deliver/status o‘zgarishini to‘xtatish; yetkazish va moliyaviy yopilish holatlarini aniq ajratish; checkout bilan kechikkan deliver poygasiga test. Dalil: `new_probes.json`, `deliver_paid_order`.

### F02 — P1: oshxonaga yuborilmagan hisobni to‘lash mumkin

**Takrorlash:** yangi taomli buyurtma yaratish → “Oshxonaga”ni bosmasdan checkout.

**Natija:** checkout 200, hisob `paid`, printer vazifasi 0. Keyin oddiy oshxonaga yuborish 409 qaytardi. Oshxona buyurtmani olmay qolishi mumkin.

**Kod:** [checkout_order](C:/RestAron/backend/app/routers/orders.py:2216) ichida yuborilmagan miqdor bo‘yicha to‘siq yo‘q; [send-to-kitchen](C:/RestAron/backend/app/routers/orders.py:1952) yopilgan hisobni rad etadi.

**Tavsiya:** yuborilmagan taom mavjudligini checkoutda tekshirish yoki buyurtma va oshxona vazifasini atomar yuborish. Oldindan to‘lovli oqim bo‘lsa u alohida loyihalanishi kerak. Dalil: `checkout_unsent`.

### F03 — P1: oldindan to‘langan, hali tayyorlanmagan buyurtma KDSdan yo‘qoladi

**Takrorlash:** buyurtmani oshxonaga yuborish → taom tayyor bo‘lmasdan kassada to‘lash.

**Natija:** checkoutdan oldin KDSda bor, keyin yo‘q. Taom `is_prepared=false` edi. Tayyorlash endpointi ham to‘langan hisobni 409 bilan rad etadi.

**Kod:** [kitchen_orders](C:/RestAron/backend/app/routers/kitchen.py:23) faqat `is_paid=false` buyurtmalarni oladi; [mark_item_prepared](C:/RestAron/backend/app/routers/orders.py:3664) to‘langan hisobni bloklaydi.

**Tavsiya:** oshxona bajarilishini to‘lovdan mustaqil yuritish yoki oldindan to‘lovni mahsulot oqimida aniq cheklash. Dalil: `kds_paid_unprepared`.

### F04 — P1: boshqa ofitsiant qo‘shgan miqdor ochiq POS savatida yangilanmaydi

**Takrorlash:** brauzerda 1-stol savatini ochish, unda 2 ta taom bor → ikkinchi ofitsiant bilan serverga `delta=1` yuborish.

**Natija:** server 200 va miqdor 3 qaytardi. Birinchi brauzerda son 2, jami 22 000 holatida qoldi. Brauzerdagi accessibility daraxti ham o‘zgarmadi. Sahifani keyingi reload bilan tekshirish ruxsat/limit to‘sig‘i sabab bajarilmadi.

**Sabab:** [delta xabari](C:/RestAron/backend/app/routers/orders.py:1505) `order_updated`da yuqori darajadagi `table_id`ni bermaydi; stol IDsi `order.table_id` ichida. [POS](C:/RestAron/frontend/src/pages/waiter/WaiterDashboard.jsx:499) aynan `event.table_id` bilan tekshiradi. 30 soniyalik polling [orders ro‘yxatini](C:/RestAron/frontend/src/pages/waiter/WaiterDashboard.jsx:408) almashtiradi, ochiq `activeOrder`ni shu yerda yangilamaydi.

**Tavsiya:** yagona WebSocket kontrakti, `order_id/table_id/version` bo‘yicha yangilash va versiya tartibi; ikki brauzerli regression. Dalil: `delta_websocket_contract`, `stale_cart_after_remote_delta.png`.

### F05 — P1: bitta stol chaqiruvini yakunlash boshqa stollar chaqiruvlarini ham yopadi

**Takrorlash:** 8- va 9-stoldan alohida chaqiruv → faqat 8-stol chaqiruviga `POST /orders/calls/{id}/resolve`.

**Natija:** 200; oldin chaqiruvlar `[8,9]`, keyin `[]`.

**Sabab:** [ommaviy UPDATE](C:/RestAron/backend/app/routers/orders.py:2944) restoran ichidagi barcha o‘qilmagan `CALL_WAITER` yozuvlarini belgilaydi; shu stol bo‘yicha cheklov yo‘q.

**Tavsiya:** aniq chaqiruv/stol bilan cheklash, parallel ikkita stol chaqiruvi va ikki ofitsiantning “Bordim” bosishiga test. Dalil: `complete_one_call`.

### F06 — P1: stop-list savatdagi “+” orqali chetlab o‘tiladi

**Takrorlash:** taomni savatga qo‘shish → admin taomni stop-listga kiritishi → mavjud qatorda `+1`.

**Natija:** `add-items` 400 qaytardi, ammo `delta` 200 va miqdorni 3 gacha oshirdi. Tugagan mahsulotga yangi miqdor qabul qilinadi.

**Kod:** [update_item_delta](C:/RestAron/backend/app/routers/orders.py:1391), shuningdek mutlaq quantity yo‘li. Stop-list faqat qo‘shishdagi tekshiruv bilan himoyalanmagan.

**Tavsiya:** miqdor oshiradigan barcha yo‘llarda mavjudlikni tekshirish; kamaytirish/qaytarishni ruxsat va oshxona qoidalari bilan saqlash. Dalil: `stop_list_delta_bypass`.

### F07 — P1: yuborilgan taomning hajmi o‘zgaradi, oshxona eski topshiriqda qoladi

**Takrorlash:** taomni oshxonaga yuborish → `PATCH .../size` bilan `9 kg` belgilash.

**Natija:** 200; bazadagi hajm yangilandi, ammo printer vazifalari soni 1 bo‘lib qoldi va unda yangi hajm yo‘q edi. Bu test fizik qog‘ozni emas, oshxonaga tayyorlangan topshiriqni tekshiradi.

**Kod:** [update_item_size](C:/RestAron/backend/app/routers/orders.py:1648) oldin yuborilgan qator uchun tuzatish cheki yaratmaydi.

**Tavsiya:** yuborilgan xususiyatni o‘zgartirishni bloklash yoki bekor qilish+tuzatish topshirig‘ini atomar chiqarish. Dalil: `change_sent_size`.

### F08 — P1: mavjud qarz yozuvi checkoutdagi nasiyani kam ko‘rsatishi mumkin

**Takrorlash:** 11 000 so‘mlik ochiq hisobga API orqali 1 000 so‘mlik manual qarz bog‘lash → shu hisobni nasiya bilan yopish.

**Natija:** checkout 200, hisob jami 11 000, nasiya daftaridagi qarz va qoldiq esa 1 000. 10 000 so‘m farq.

**Sabab:** [checkout](C:/RestAron/backend/app/routers/orders.py:2389) mavjud `Debt`ni oladi, ammo summa/holati mosligini tekshirmaydi. Manual qarz API `order_id`ni qabul qiladi. Hozirgi oddiy “Qarz qo‘shish” UI oqimi `order_id` yubormaydi; xato API orqali tasdiqlandi.

**Tavsiya:** qo‘lda qarz bilan checkout nasiyasining bog‘lanish qoidasi, bir orderga noyob moliyaviy bog‘lanish, mos kelmasa 409 va solishtirish. Dalil: `debt_links.json`.

### F09 — P2: checkout ismsiz va telefonsiz nasiyani qabul qiladi

**Natija:** `payment_method=debt` va shaxs ma’lumotisiz checkout 200; qarzdor `Noma'lum Mijoz`, telefon `—` bo‘lib saqlandi. Alohida qarz yaratish endpointi esa ism va telefonni tekshiradi.

**Kod:** [fallback qiymatlar](C:/RestAron/backend/app/routers/orders.py:2397).

**Tavsiya:** bir xil server validatsiyasi; ism/telefon yoki restoranning aniq tasdiqlangan istisno jarayoni. UI maydonini majburiy qilish serverni almashtirmaydi. Dalil: `anonymous_debt_checkout`.

### F10 — P1: qarzga boshqa restoran buyurtmasini bog‘lash mumkin

**Natija:** restoran 1 admini restoran 2 buyurtmasining IDsi bilan restoran 1 qarzini yaratdi — 201. Bu buyurtmaning boshqa ma’lumotlari o‘qilganini isbotlamaydi, ammo tenantlar orasidagi noto‘g‘ri moliyaviy bog‘lanishni tasdiqlaydi.

**Kod:** [create_debt](C:/RestAron/backend/app/routers/debts.py:86) `order_id`ning restorani va holatini tekshirmaydi; [tenant before_flush](C:/RestAron/backend/app/core/tenant.py:42) Debt uchun bunday referens tekshiruvini qo‘shmagan.

**Tavsiya:** barcha tashqi IDlar uchun egasi/restorani/holati tekshiruvi va mos cheklovlar. Dalil: `debt_foreign_order_reference`.

### F11 — P2: baholash endpointi boshqa restoran taomiga ta’sir qiladi va o‘chirilgan sozlamani e’tiborsiz qoldiradi

**Natija:** tokensiz restoran 1 sharhi ichida restoran 2 taom IDsi yuborildi — 201, begona taomning `rating_count`i 1 ga oshdi. `allow_reviews=false` qilingandan keyin ham yangi sharh 201 bo‘ldi. Ushbu routerda sharh uzunligi, bir buyurtmaga takroriy baho va chaqiruvlar soniga aniq chegaralar ko‘rinmadi.

**Kod:** [create_review](C:/RestAron/backend/app/routers/reviews.py:33).

**Tavsiya:** stol/buyurtma tasdig‘i, barcha referenslarning restoranga tegishliligi, sozlamaga rioya, takroriy baho siyosati va server limiti. Dalillar: `anonymous_cross_restaurant_review`, `disabled_reviews_still_accepted`.

### F12 — P1: bildirishnomalar fon tozalashi tenant himoyasidan tashqarida

**Takrorlash:** restoran 2da 10 kun oldingi o‘qilgan sun’iy bildirishnoma → restoran 1 admini bilan `GET /notifications/?restaurant_id=2`. Test 2% tasodifiy tozalash shoxini majburan tanladi.

**Natija:** GET 200 va bo‘sh ro‘yxat berdi, lekin restoran 2dagi yozuv o‘chirildi. UI orqali kundalik foydalanishda bu parametr albatta yuboriladi degan da’vo qilinmaydi; API himoyasi buzilishi tasdiqlandi.

**Sabab:** [fon helperi](C:/RestAron/backend/app/routers/notifications.py:22) yangi, tenant scope qo‘yilmagan sessiyada so‘rovdagi restoran IDsi bilan DELETE qiladi.

**Tavsiya:** autentifikatsiyalangan restoran IDsi, fon sessiyasida ham tenant scope, GET yon ta’sirini alohida rejalashtirilgan jarayonga ko‘chirish. Dalil: `secondary_probes.json`.

### F13 — P2: bildirishnomalarni qo‘lda tozalash 500 qaytaradi

**Natija:** admin bilan `DELETE /notifications/cleanup?restaurant_id=1&days=7` → 500.

**Sabab:** [chaqiruv](C:/RestAron/backend/app/routers/notifications.py:149) `_cleanup_old_notifications(restaurant_id, db, days=days)` deydi, funksiya esa `(restaurant_id, days=7)` oladi; `days` ikki marta berilgan.

**Tavsiya:** imzo/chaqiruvni moslashtirish va endpoint darajasidagi regression. Dalil: `notification_cleanup_endpoint`.

### F14 — P1: stolning umumiy PATCH yo‘li ochiq hisob himoyasini chetlab o‘tadi

**Natija:** ochiq hisob bor stolga admin bilan `PATCH /tables/{id}` va `status=available` → 200. Stol “bo‘sh”, lekin active endpointda 1 ta hisob qolgan. Maxsus `/status` va `/clear` yo‘llaridagi ochiq hisob tekshiruvi bu umumiy PATCHga tatbiq etilmagan.

**Kod:** [update_table](C:/RestAron/backend/app/routers/tables.py:1266), [to‘g‘ridan-to‘g‘ri setattr](C:/RestAron/backend/app/routers/tables.py:1294).

**Tavsiya:** barcha status o‘zgarishlarini yagona biznes funksiyasiga o‘tkazish; oddiy tahrir orqali mavjud hisobni yashirishga yo‘l qo‘ymaslik. Dalil: `generic_table_update_bypasses_open_check`.

### F15 — P1: band stolni nofaol qilish faol hisobga kirishni yashiradi

**Natija:** ochiq hisob bor stol `is_active=false` bilan 200 bo‘lib yangilandi. Keyin `/orders/table/{id}/active` 404, lekin shu hisobga `add-items` 200 bo‘ldi. Hisob bazada o‘chmadi, turli endpointlar bir-biriga zid holatda qoldi.

**Tavsiya:** band stolni nofaol qilishdan oldin hisob/avans/bron siyosati, ko‘chirish yoki yopish; arxivlash jarayoni. Dalil: `deactivate_occupied_table`.

### F16 — P2: foydalanuvchi qiymati yoki odatiy cheklov 500ga aylanadigan yo‘llar bor

- `PATCH /tables/4` va `capacity=-1` → 500. [TableUpdate](C:/RestAron/backend/app/schemas/table.py:23) bu maydonga yaratishdagidek ijobiy son cheklovini qo‘ymagan.
- `POST /debts/` va mavjud bo‘lmagan `order_id=9999999` → 500. Referens oldindan tekshirilmaydi.
- Qarzga 100 so‘m qisman to‘lash 200; keyin `DELETE /debts/{id}` → 500. `debt_payments` FKsi o‘chirishni bloklaydi, router esa mos 409/400 javob bermaydi.

**Tavsiya:** noto‘g‘ri qiymatga 422, topilmagan referensga 404, moliyaviy tarixga zid o‘chirishga 409; moliyaviy yozuv uchun sababi va audit izi bor bekor qilish jarayoni. Xatoni yashirish uchun FKni o‘chirish yoki to‘lov tarixini cascade bilan yo‘qotish tavsiya qilinmaydi.

### F17 — P1: bir printerdagi katta navbat boshqa sog‘lom printerni ham kutdiradi

**Sinov:** bir sekin sun’iy printerga 100 eski job, boshqa sog‘lom sun’iy barga 101-job. Sekin adapter 10 soniya kutadi, bar 1 msda javob bera oladi.

**Natija:** 5.2 soniyadan keyin barga hali urinish ham bo‘lmagan, u `pending`. Faqat sekin printer chaqirilgan.

**Sabab:** [worker](C:/RestAron/backend/app/core/printer_queue.py:309) global eng eski 50 ta jobni oladi. Ularning barchasi band printerga tegishli bo‘lsa, keyingi printer tanlovga kirmaydi. Bu sinov cheksiz och qolishni isbotlamaydi, lekin printerlar parallel va mustaqil ishlashi buzilishini ko‘rsatadi.

**Tavsiya:** printer boshiga navbatdagi jobni adolatli tanlash, eski navbatga aniq operator siyosati, bir printer uzilganda qolganlari ishlashiga test. Dalil: `printer_backlog.json`.

### F18 — P2: PDF arxivini qayta yaratish asl chek ma’lumotlarini to‘liq uzatmaydi

**Sinov:** PDF fayli yo‘q sun’iy chek: subtotal 20 000, xizmat 2 000, chegirma 1 000, jami 21 000, avans 5 000, yangi naqd to‘lov 16 000. Generator payloadini spy bilan tekshirish.

**Natija:** endpoint 200; generatorga `advance_amount`, `discount`, `amount_due` yuborilmadi, restoran nomi sun’iy restoran o‘rniga hardcode `Dunyo Choyxonasi` bo‘ldi. Bu sinov haqiqiy PDF maketini ko‘rganlik da’vosi emas.

**Qo‘shimcha kod xavfi:** [qidirish](C:/RestAron/backend/app/routers/receipts.py:594) arxivning UTC sanasini ishlatadi, generator esa [UZ sanasini](C:/RestAron/backend/app/core/pdf_generator.py:99) ishlatadi. Qidirish chek raqamini fayl nomiga aniq tenglik bilan emas, substring bilan moslaydi. Tun oralig‘i va katta IDlarda alohida regression kerak; bu ikki qo‘shimcha shox ushbu auditda runtime takrorlanmadi.

**Tavsiya:** chek uchun o‘zgarmas to‘liq snapshot, aniq PDF identifikatori/yo‘li, bir xil sana va pul qiymatlari. Dalil: `pdf_payload.json`; [fallback kodi](C:/RestAron/backend/app/routers/receipts.py:606).

### F19 — P2: ofitsiant performance API sharhlar sonicha savdoni ko‘paytiradi

**Sinov:** bitta ofitsiantga 2 ta hisob, jami 22 000 va 3 ta sharh.

**Natija:** `/stats/waiter-performance` 6 ta buyurtma va 66 000 qaytardi. Ikki mustaqil ko‘p qatorli jadval to‘g‘ridan-to‘g‘ri JOIN qilingan.

**Kod:** [get_waiter_performance](C:/RestAron/backend/app/routers/stats.py:244). Hozirgi `WaiterKpiTab` boshqa `/waiter-kpi-detail` endpointini ishlatadi; shu sabab aynan u ekranda ham bu ko‘payish bor deb umumlashtirilmaydi.

**Tavsiya:** buyurtma va sharhlarni alohida agregatsiya qilib keyin JOIN; 2×3 qator holatiga regression. Dalil: `stats_probes.json`.

### F20 — P1: katta parallel yuklamada amallar foydalanuvchi kutish chegarasidan chiqadi

3-bo‘limdagi 60/100 natijalari bunga dalil. [get_db](C:/RestAron/backend/app/core/database.py:68) SQLite yozuvchilarini bitta navbatga oladi. Qulf dependency tugaguncha ushlanadi; ayrim routerlar commitdan keyin ham WebSocket yuborishni kutadi. Birinchi marta yozuvni muvaffaqiyatli commit qilish bilan telefonning javob olishi orasida vaqt bor.

**Tavsiya:** navbatda kutish, tranzaksiya, SQL, serializatsiya va WebSocket vaqtlarini alohida o‘lchash; tarmoq tarqatishni yozish navbatidan chiqaradigan xavfsiz outbox; ortiqcha to‘liq payloadlar va barcha xodimlarga fanoutni kamaytirish. Faqat timeoutni kattalashtirish tezlikni tuzatmaydi.

## 5. Ishchi bazaning joriy holati

Mahalliy sozlamada `sqlite+aiosqlite` va `restaron.db` ishlatilishi tasdiqlandi. Bir read-only tranzaksiyadagi snapshot: 82 buyurtma, 125 taom qatori, 47 stol, 24 foydalanuvchi, 89 menyu taomi.

**Fayl yaxlitligi bilan savdo yaxlitligi boshqa-boshqa narsalar.** `PRAGMA integrity_check=ok`, ammo:

- 15 hisobda subtotal taom qatorlari yig‘indisiga mos emas.
- 3 to‘langan hisobda jami summa naqd+karta+Click+nasiya+avansga mos emas.
- Ushbu guruhlarning birlashmasi **16 ta alohida hisob**. Qaysi tarixiy amal sabab bo‘lganini bu snapshotning o‘zi isbotlamaydi.
- `table_id=40`da 3 ochiq hisob: 36, 37, 38.
- `ux_orders_one_open_per_table` unikal indeksi mahalliy bazada yo‘q. [Migratsiya kodi](C:/RestAron/backend/app/core/database.py:302) eski dublikatlarni topsa indeks yaratishni tashlab ketadi. Yangi toza test bazasi bilan eski bazaning himoyasi shu jihatdan farq qiladi.
- 17 FK buzilishi — mavjud bo‘lmagan buyurtmaga bog‘langan printer joblar.

| Hisob ID | Subtotal | Taom qatorlari yig‘indisi | Qo‘shimcha to‘lov tafovuti |
|---:|---:|---:|---|
| 1 | 49 000 | 0 | — |
| 4 | 1 424 000 | 1 149 000 | — |
| 9 | 10 000 | 0 | — |
| 10 | 15 000 | 0 | — |
| 13 | 30 000 | 0 | — |
| 14 | 15 000 | 0 | — |
| 15 | 30 000 | 0 | — |
| 16 | 15 000 | 0 | — |
| 36 | 200 000 | 0 | — |
| 37 | 200 000 | 0 | — |
| 38 | 200 000 | 0 | — |
| 39 | 709 000 | 679 000 | — |
| 55 | 1 658 000 | 1 648 000 | To‘langan jami 1 856 960, tender 0 |
| 61 | 15 000 | 0 | — |
| 63 | Subtotal tekshiruvida tafovut qaydmadi | — | To‘langan jami 63 840, tender 0 |
| 64 | 19 000 | 0 | To‘langan jami 21 280, tender 0 |

Printer navbati snapshoti: **73 done, 98 pending, 1 printing, 38 uncertain**. 17 orphan job IDsi: 61, 62, 72, 82, 92, 102, 112, 122, 132, 142, 152, 162, 172, 182, 192, 202, 212. Navbatdagi holatlar ishlab turgan tizimda keyin o‘zgarishi mumkin. Eski pending vazifalar oddiy restartda qayta bajarilishi mumkin; ularni operator qarorisiz joriy ovqat topshirig‘i deb qabul qilish xavfli.

**Tavsiya:** asl chek, hisob kitobi va egasi/kassir dalillari asosida solishtirish; har tuzatishdan oldin izchil zaxira, avval nusxada repetitsiya va audit izi. Summani qatorlar bo‘yicha avtomatik “to‘g‘rilash”, hisoblarni o‘chirish yoki hammasini nol qilish dalilsiz tavsiya etilmaydi. Ushbu audit hech qaysi yozuvni tuzatmadi.

Dalil: [inventory_current.json](C:/RestAron/scratch/reaudit_20261023/scratch/inventory_current.json).

## 6. Xavfsizlik, joylashtirish va saqlash bo‘yicha qo‘shimcha xavflar

### F21 — P1: repodagi Render Free + lokal SQLite yo‘riqnomasi savdo uchun yaroqsiz

[render.yaml](C:/RestAron/render.yaml:1) `plan: free` va lokal SQLite ishlatadi, persistent disk belgilanmagan. Render rasmiy hujjatiga ko‘ra free servisning lokal SQLite/rasmlari restart, redeploy yoki uxlab qolishda yo‘qoladi; free instansiyalarni production uchun tavsiya qilmaydi. Bu kompyuterdagi lokal bazaning hozir yo‘qolgani degani emas — aynan shu deployment retseptining xavfi. Manba: [Render Free hujjati](https://render.com/docs/free).

Mahalliy ishlash, doimiy saqlash va printerga yetadigan tarmoq bilan aniq tanlangan deployment zarur. Bulutdagi server choyxonadagi USB printerga to‘g‘ridan-to‘g‘ri kira olmaydi; alohida mahalliy print agenti yoki boshqa hujjatlashtirilgan yechim talab qilinadi.

### F22 — P1: Windows yangilash skripti xavfsiz publish yordamchisini chetlab o‘tadi

[RESTARON_YANGILASH.bat](C:/RestAron/RESTARON_YANGILASH.bat:67) ishlayotgan checkoutda `git pull`, backendga `pip install`, so‘ng bevosita `npm run build` bajaradi. Buildning odatiy `dist` tozalashi va eski assetlarning yo‘qolishi ochiq brauzerlarni buzishi mumkin. Backend paketlarini o‘rnatish xatosi alohida tekshirilmaydi. Restartda jarayon majburan o‘ldiriladi. Ushbu xavf statik tekshiruvdan; ishchi tizimda skript bajarilmadi.

[frontend_build.py](C:/RestAron/frontend_build.py:63)da staging, zaxira va eski hashed assetlarni saqlash yordamchisi bor, lekin bu BAT oqimi undan foydalanmaydi. Tavsiya: bitta nazoratli yangilash jarayoni, sog‘lom build tayyor bo‘lgach atomar publish, migration oldidan zaxira, graceful shutdown va rollback.

### F23 — xavfsizlik: eskirgan kutubxonalar va ochiq form parsing

O‘rnatilgan `python-multipart=0.0.9`. Maintainer advisorysi `<0.0.18` versiyalarda noto‘g‘ri multipart chegaralari event loopni band qiladigan DoSga olib kelishi mumkinligini ko‘rsatadi. Bu loyihada upload endpointlari bor. Ushbu audit zararli payload bilan serverni ataylab yiqitmadi. Manba: [python-multipart maintainer advisory](https://github.com/Kludex/python-multipart/security/advisories/GHSA-59g5-xgcq-4qw3).

`python-jose=3.3.0` ham ma’lum xavfsizlik advisorylari bor eski versiya. Lekin RestAron token dekodlashda `algorithms=[HS256]`ni cheklaydi; “tokensiz admin bo‘lish mumkin” degan xulosa chiqarilmadi. Yangilash moslik va xavfsizlik regressionlari bilan bajarilishi kerak.

To‘liq npm auditida `vite`, `tailwindcss` va ularning zanjiridagi 10 paket yozuvi belgilandi; `--omit=dev` natijasi 0. Ularni brauzerdagi React runtimega avtomatik ravishda tatbiq etish noto‘g‘ri. Biroq [Vite serveri](C:/RestAron/frontend/vite.config.js:33) `host:true`; dev serverni savdo tarmog‘i/internetga production sifatida ochish tavsiya etilmaydi. Audit ma’lumotlari `npm_audit_outside.json` va `npm_audit_production.json`da.

### Tuzilish bo‘yicha cheklovlar

- Pul ustunlari hanuz `Float`. Hozirgi sinovlar yaxlitlikning ayrim holatlarini o‘tkazdi, ammo barcha chegirma/foiz/vazn kombinatsiyalarida aniq pul hisobiga kafolat yo‘q. Decimal/Numeric yoki belgilangan eng kichik birlikka migratsiya tarixiy summalarni solishtirish bilan bajarilishi kerak.
- Bitta backend instansiyasi himoyasi mavjud. WebSocket hub va ayrim cheklovlar xotirada. Shunchaki `workers=4` qilish yechim emas. Ko‘p process uchun umumiy event tarqatish, printer egasi, idempotency va ruxsat holati loyihalanishi kerak.
- PostgreSQLda ham [tenant write lock](C:/RestAron/backend/app/core/tenant.py:79) restoran yozuvlarini ketma-ketlashtiradi; bazani almashtirishning o‘zi parallel tezlikka kafolat bermaydi.
- [revenue-chart](C:/RestAron/backend/app/routers/stats.py:216) SQLitega xos `date(created_at, '+5 hours')` ifodasidan foydalanadi. PostgreSQL mosligi real bazada tekshirilmagan; bu yo‘l alohida moslashtirish/sinov talab qiladi.
- Zaxira yordamchisi SQLite backup API va retention testlaridan o‘tdi. Ammo `integrity_check=ok` moliyaviy/FK sog‘lomligini bildirmaydi — ishchi snapshot buning amaliy misoli. Boshqa diskka nusxalash xatosi logda warning bo‘lib qoladi; tashqi zaxira ishlaganini alohida monitoring qilish kerak.
- Restore skripti server to‘xtatilganiga operator orqali tayanadi. Ishlayotgan savdo serverida tiklash sinovi bajarilmadi. Elektr, disk to‘lishi va boshqa qurilmaga haqiqiy tiklash hali qabul sharti bo‘lib qoladi.

## 7. Dizayn va qulaylik bahosi

Brauzerda yangi buildning administrator POSi oddiy katta ekran va 390×844 o‘lchamda ko‘rildi. Sun’iy ma’lumotlar ishlatilgani sabab ko‘p kartada rasm o‘rniga placeholder bor; bu haqiqiy menyu rasmlari buzilgan degani emas. Brauzerning tashqi overlay tugmasi mahsulot xatosi sifatida hisoblanmadi.

**Ishlaydigan jihatlar:** savat va menyu ajratilgan; jami va “Oshxonaga” asosiy joyda; mobil menyu/savat almashtirish ishladi; ofitsiant/kassir bitta POS komponentidan foydalanadi; stol tanlash va qidiruv imkoniyati bor. Mobil savatda miqdor tugmalari va pastki jami paneli ko‘rinib turdi.

**O‘zgartirishga arziydigan joylar:**

1. **Birinchi navbatda raqamlarning ishonchliligi.** Eskirgan savat, yo‘qoladigan chaqiruv va kassa hisobotidagi tafovut chiroyli ko‘rinishdan muhimroq. “Serverda saqlandi”, “oshxona navbatida”, “printerga uzatildi” va “natija noma’lum” holatlari farqli va tushunarli ko‘rinsin.
2. **Soddaroq ish rejimi.** Ofitsiant uchun stol, menyu, savat, chaqiruv va tayyor ovqatlar yetarli. Kassa statistikasi, tema va texnik sozlamalar xizmat oqimidan ajratilsin. Administrator yuqori bo‘limlari ko‘p bo‘lgani uchun gorizontal surish talab etiladi.
3. **Zal bo‘yicha katta stol kartalari.** Mobil ko‘rinishda uzun zal/stol nomi bir necha qatorga bo‘lindi. Zal filtri, stol raqami va bandlikni bir qarashda ajratish; uzoq nom uchun qisqa ko‘rinish va to‘liq nomni ochish.
4. **Tez POS uchun ixcham menyu.** Katta rasmlar kamroq taomni bitta ekranga sig‘diradi. “Ixcham/rasmli” rejim, tez-tez sotiladiganlar va aniq nom/narxni ustun qilish foydali. Bu dizayn tavsiyasi; Aliposter bilan vaqt farqi o‘lchanmagan.
5. **Ikonka ma’nosi.** Ko‘chirish, izoh, hajm va chek tugmalarini yangi xodimga tushunarli qilish; klaviatura/fokus hamda ekranni o‘qish belgilarini butun panel bo‘yicha tekshirish. Ayrim dialoglarda focus helper bor, checkoutda umumiy dialog/fokus oqimi hali to‘liq tekshirilmagan.
6. **Chegirma, avans va nasiya.** Kassir yakuniy jami, avvalgi avans, hozir olinadigan pul va qaytimni bir joyda ko‘rsin. Server aynan ko‘rsatilgan versiyani qabul qilsin; xato bo‘lsa qaysi summa o‘zgargani aytilsin.
7. **Chaqiruvlar doim ko‘rinsin.** Har bir chaqiruvga vaqt, stol va kim xizmatga olgani; bitta xodim olganda boshqalar aynan shu chaqiruv olinganini ko‘rsin. Ovozning takrorlanishi va tasdiqlanishini katta zalda amalda tekshirish kerak.
8. **Mijoz menyusida xatoni ko‘rsatish.** Ayrim sahifalarda API xatosi faqat consolega yoziladi; mijoz bo‘sh menyuni “taom yo‘q” deb tushunishi mumkin. Aloqa xatosi va qayta urinish tugmasi kerak.
9. **Customer stop-list sinxronlash.** Mijoz menyusi boshlang‘ich yuklashda mavjud bo‘lmagan taomni ro‘yxatdan chiqaradi; keyingi socket handler faqat bor taomlarni map qiladi. Qayta mavjud qilingan, avval ro‘yxatga olinmagan taom qaytishi uchun refetch/insert zarur. Bu kod kuzatuvi, brauzerda alohida runtime sinovi bajarilmadi.
10. **Ko‘p til va kam animatsiya.** POS tarjimalari bor, lekin butun panel uchun to‘liq UZ/ЎЗ/RU/EN audit tugallanmadi. Konfetti, ko‘p dekor va tovushni o‘chirish rejimi eski telefonlar va shovqinli zal uchun foydali.

Dalillar: [katta ekran](C:/RestAron/scratch/reaudit_20261023/scratch/admin_pos.png), [mobil menyu](C:/RestAron/scratch/reaudit_20261023/scratch/admin_mobile.png), [mobil savat](C:/RestAron/scratch/reaudit_20261023/scratch/cart_mobile.png).

![Sinov bazasidagi POS](C:/RestAron/scratch/reaudit_20261023/scratch/admin_pos.png)

## 8. Tezlashtirish uchun ustuvor ishlar

Bu bo‘lim taklif; kod o‘zgartirilmadi va hali olinmagan tezlashish va’da qilinmaydi.

1. **Global yozish navbatini profilash.** Har so‘rov uchun navbatga kirish, qulfni olish, birinchi SQL, commit va javob vaqtini qayd etish. Hozirgi 100 user natijasida eng katta og‘riq yozuv amallarida.
2. **Commitdan keyingi tarmoq ishini ajratish.** WebSocket yuborish va og‘ir javob tayyorlash yozuvchi qulfni keragidan ortiq ushlab turmasin. Buni atomarlik va retry himoyasini buzmagan holda bajarish kerak.
3. **Socket fanout va payloadni qisqartirish.** 100 user sinovida 10 000 `new_order`, 20 000 `order_updated`, 20 000 `table_status_updated`, 10 000 `order_paid` yetkazilishi qayd etildi. Kichik delta, kerakli rol/stolga yuborish, UI versiyalarini birlashtirish va keraksiz refetchni kamaytirish.
4. **Faol ro‘yxatlarni sahifalash.** POS `limit=300&include_items=true` ishlatadi. 300 dan ortiq faol hisob uchun UI pagination yo‘q. Doim barcha taomlari bilan ro‘yxat olish o‘rniga qisqa stol holati va tanlangan buyurtmani alohida olishni baholash.
5. **Menyu va rasmlar.** `CustomerMenu` va `DunyoLanding` hali barcha rasmlarni fonda preload qiladi. Faol kategoriya/keyingi ekran, o‘lchami mos thumbnail, lazy loading, kesh va sekin tarmoq rejimi. Ofitsiantdagi oldingi preload olib tashlangani butun mijoz oqimiga tatbiq etilgan deb bo‘lmaydi.
6. **KDS so‘rovlarini filtrlash.** Hozir u har 5 soniya va har qanday socket hodisasidan so‘ng qayta yuklashi mumkin; station filtri asosan brauzerda. Kerakli hodisalar, kerakli stansiya va faqat tugallanmagan ishlarni olishni o‘lchash.
7. **Indeks va tarix hajmi.** Haqiqiy 3 yillik hisob/taom/print/audit hajmida query plan va p95ni o‘lchash. 82 hisobli joriy fayl 3 yillik sig‘im sinovi emas.
8. **PostgreSQLni alohida loyiha sifatida sinash.** Moliyaviy turi, migration, sana funksiyasi, lock tartibi, backup/restore va yuklama tekshirilgach qaror qilish. Shunchaki SQLite URLni almashtirish yetarli emas.

## 9. Bo‘limlar bo‘yicha ishga tayyorlik bahosi

| Bo‘lim | Baho | Asos |
|---|---|---|
| Login, role, token | Asosiy holatlar o‘tdi; to‘liq xavfsizlik tasdig‘i yo‘q | 107 testning tegishli qismi, eski dependencylar va tenant istisnolari |
| Ofitsiant POS | Ishga tushirishga to‘siqlar bor | Eskirgan savat, stop-list `+`, yuqori parallel kechikish |
| Buyurtma yaratish/qo‘shish | Sun’iy parallel sinovlarda yakuniy yaxlitlik yaxshi | 30/60/100 oqimlar va 20 ta bir stol poygasi |
| O‘chirish/qaytarish | Tekshirilgan poygalar o‘tdi; to‘liq emas | Yopilgan hisob himoyasi bor; barcha legacy yo‘llar va fizik bekor qilish cheki sinalmagan |
| Oshxona printeri | Joyida qabul sinovi shart | Navbat atomarligi bor; printerlararo kutish xatosi va eski joblar bor |
| KDS | Oldindan to‘lov oqimi uchun tayyor emas | To‘langan, tugallanmagan buyurtma yo‘qoladi |
| Mijoz menyusi/QR | Asosiy ko‘rinish mavjud; qayta tekshirish zarur | Ruxsat testlari bor; stop-list qaytishi, xato holatlari, telefonlar to‘liq sinalmagan |
| Ofitsiant chaqirish | Tayyor emas | Bitta chaqiruvni yopish boshqa stol chaqiruvlarini yo‘qotadi |
| Kassa va smena | Tayyor emas | To‘langan hisobni deliver qilish tushumni kamaytiradi |
| Nasiya | Tayyor emas | Mavjud qarz summasi, begona order bog‘lanishi, anonim qarzdor |
| Avans/bron/transfer | Asosiy regressionlar o‘tdi | Generic stol tahriri himoyasi va real kassir jarayoni tekshirilishi kerak |
| Arxiv/PDF | To‘liq ishonchli emas | Eski tafovutlar, fallback snapshot kamchiliklari |
| Statistika/KPI | Endpointlar bo‘yicha farqlanadi | Performance API 2 hisobni 6 deb sanadi; joriy KPI UI boshqa endpointda |
| Zaxira/tiklash | Yordamchi testlar o‘tdi | Tashqi qurilmadan va elektr/disk uzilishidan haqiqiy tiklash sinalmagan |
| Docker/PostgreSQL/cloud | Production tasdig‘i yo‘q | Runtime sinovi yo‘q; Render SQLite retsepti xavfli |
| Aliposter 1.0.0.0dan ustunlik | O‘lchanmagan | Aliposterning ishlaydigan nusxasi, bir xil qurilma va bir xil vazifa bilan solishtirish yo‘q |

## 10. Hali amalda sinalmagan muhim holatlar

- Choyxonadagi haqiqiy USB va ikki LAN printer: har stansiya, ichimlik, dozakaz, otmena, pre-check, final, qayta chop etish; kabel uzish, qog‘oz tugashi, spooler/OS restart.
- Haqiqiy ofitsiant telefonlari va Wi-Fi: kamida kutilgan eng yuqori parallel qurilmalar, yurib AP almashish, ekran qulflanishi, brauzer fon rejimi, internet uzilganda lokal ishlash.
- 24–72 soat uzluksiz ish, xotira/ulanish/navbat o‘sishi, katta tarix hajmi, uzoq vaqtli sessiyalar.
- Elektr uzilishi yoki jarayonni aynan commit/print o‘rtasida to‘xtatish; jismoniy qayta bosilmaslik va yo‘qolmaslik.
- Disk to‘lishi, yozish ruxsati yo‘qolishi, zaxira diski uzilishi, boshqa kompyuterga to‘liq tiklash va iqtisodiy summalarni solishtirish.
- PostgreSQL va Docker runtime, ko‘p backend processi va serverlararo ish. Hozirgi bitta instance himoyasini shunchaki o‘chirish mumkin emas.
- Haqiqiy SMS/Telegram yetkazilishi va tashqi to‘lov terminali/provayder bilan reconciliation. “Karta/Click” maydoniga yozish real to‘lov provayderi tasdig‘i ekanini bu audit tekshirmadi.
- Har bir 121 marshrut uchun to‘liq permission matrix, barcha malformed/null/boundary qiymatlar, mustaqil pentest va to‘liq Python transitive dependency skani.
- Barcha brauzer/telefon o‘lchamlari, tarjimalar, rang kontrasti, klaviatura va screen reader auditining to‘liq qamrovi.
- Aliposterda bir xil amallarni vaqtga o‘lchab yonma-yon UX taqqoslash.

Brauzerdagi oxirgi reload avtomatik approval tekshiruvi tomonidan foydalanish limiti sabab bajarilmadi. Bu xavfli amal topilgani emas, approval tekshiruvi yakunlana olmagan holat. Keyingi brauzer sinovlari muqobil yashirin yo‘l bilan aylanib o‘tilmadi; qolgan vizual holatlar “o‘tdi” deb yozilmadi.

## 11. Ishga tushirishdan oldingi qabul mezonlari

Quyidagilar o‘tmaguncha katta zalda to‘liq almashtirish tavsiya qilinmaydi:

1. F01–F08, F12, F14–F17 va moliyaviy/tenant bilan bog‘liq boshqa P1lar tuzatilib, aynan reproducerlar regression sifatida o‘tsin. Eski 107 test ham saqlansin.
2. 16 ta eski hisob, dublikat stol va printer navbatiga egasi/kassir tomonidan dalilli qaror; zaxira va o‘zgarmas audit izi. Dublikatlar hal bo‘lgach unikal himoya tekshirilsin.
3. Haqiqiy qurilma/tarmoqda kutilgan peak bilan to‘liq ofitsiant–oshxona–kassa sinovi. Taklif etiladigan boshlang‘ich maqsad: taom qo‘shish p95 ≤1 s, oshxonaga qabul/checkout p95 ≤2 s, timeout/yo‘qolgan/dublikat amal 0. Bular hozir erishilgan natija emas, egasi bilan kelishiladigan qabul mezonlari.
4. Har bir printer uzilishida qolganlari ishlasin. “Navbatga olindi” bilan fizik qog‘ozni operator alohida tasdiqlasin; natijasi noaniq jobni takror chiqarishda belgi va hisob izi bo‘lsin.
5. Tashqi zaxiradan yangi qurilmaga tiklash: buyurtma qatorlari, to‘lovlar, qarzlar, avans, chek va printer navbati alohida solishtirilsin.
6. 24–72 soatlik soak va ish vaqtida nazoratli uzilishlardan keyingi tiklanish o‘tsin.
7. Cheklangan zal/stollar bilan pilot, kassir va oshpaz bilan yakuniy hisob solishtirish; keyin bosqichma-bosqich kengaytirish. Aliposter o‘rnini to‘liq bosish qarori real jarayon va qabul natijasiga tayansin.

## 12. Dalillar va qayta tekshirish

Asosiy dalillar papkasi: [scratch/reaudit_20261023/scratch](C:/RestAron/scratch/reaudit_20261023/scratch).

| Fayl | Mazmun |
|---|---|
| `pytest_current_outside.txt` | Muvaffaqiyatli 107 test logi |
| `build.txt` | Alohida production build logi |
| `static_inventory.json` | Commit, dependency versiyalari, 121 marshrut va 123 fayl hash taqqoslovi |
| `audit_route_contracts.json` | 130 frontend API manzil/metod tekshiruvi |
| `new_probes.py`, `new_probes.json`, `new_probes_final_log.txt` | Checkout, KDS, WS kontrakt, stop-list, chaqiruv, anonim qarz, review, hajm, deliver reproducerlari |
| `secondary_probes.py`, `secondary_probes.json`, `secondary_probes_verified_log.txt` | Bildirishnomalar va umumiy stol tahriri |
| `debt_link_probe.py`, `debt_links.json` | Qarzni begona orderga bog‘lash va kam summa bilan qayta ishlatish |
| `stats_probe.py`, `stats_probes.json` | Statistik JOIN, o‘chirilgan review sozlamasi, to‘lovli qarzni o‘chirish |
| `pdf_payload_probe.py`, `pdf_payload.json` | PDF qayta generatsiyasi uchun yuborilgan qiymatlar; valid PDF maketi sinovi emas |
| `printer_backlog_probe.py`, `printer_backlog.json` | Bir printer navbatining boshqasini kutdirishi; adapterlar sun’iy |
| `inventory_current.json` | Mahalliy savdo bazasining read-only snapshot tekshiruvlari |
| `load_30.json`, `load_60.json`, `load_100.json` | Yakunlangan TCP/WS yuklama natijalari |
| `load_60_log.txt`, `load_100_incomplete_log.txt` | Qabul qilinmagan dastlabki yugurishlar |
| `load_100_fixed_harness.py` | Server pingiga pong qaytaradigan yakuniy 100 user test mijoz kodi |
| `npm_audit_outside.json`, `npm_audit_production.json` | To‘liq va production npm audit |
| `admin_pos.png`, `admin_mobile.png`, `cart_mobile.png`, `stale_cart_after_remote_delta.png` | Sun’iy bazadagi brauzer ko‘rinishlari |

Yordamchi skriptlar audit nusxasida yangi sun’iy DB nomlarini yaratadi. Ularni ishlab turgan savdo serveriga qarshi ko‘r-ko‘rona o‘zgartirib ishlatmaslik kerak. Audit serverlari faqat 127.0.0.1 dagi 8027–8029 portlardan foydalandi. Asl 8000 server bu tekshiruv uchun qayta ishga tushirilmadi.

Audit tugagach uchala sinov serveri yopildi; `cleanup.json`da qayd bor. Brauzerning vaqtinchalik viewportini qaytarish urinishi ham lokal browser use Work sozlamalarida o‘chirilgani sabab bajarilmadi. Sinov tabidagi vaqtinchalik o‘lcham mahsulot konfiguratsiyasi emas.

**Yakuniy baho:** tizimda foydali POS asoslari va ayrim muhim parallel himoyalar bor. Ushbu sinovlar buyurtmalar avtomatik ravishda yo‘qoladi degan da’voni tasdiqlamadi. Ammo kassa hisobotini kamaytiradigan amal, oshxona topshirig‘i yo‘qoladigan oqim, boshqa stol chaqiruvining yopilishi, eskirgan savat, nasiya tafovuti va katta yuklamadagi kechikishlar real ishga tushirishga to‘siqdir.
