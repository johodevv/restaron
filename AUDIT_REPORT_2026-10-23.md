# RestAron: ishga tushirishdan oldingi texnik audit

Tekshiruv: 2026-10-22 kechasi – 2026-10-23, Asia/Tashkent. Manba: `C:\RestAron` dagi joriy kod va mahalliy fayllar.

## Qaror

**Hozirgi holatda katta choyxonada asosiy ishchi tizim sifatida ishga tushirish tavsiya etilmaydi.** Buyurtma va pul hisobida takroriy yozuv, yo'qolgan to'lov yangilanishi va o'zaro mos kelmaydigan summalar amalda qayta yaratildi. Oddiy parallel amallarning bir qismi to'g'ri ishlaydi, ammo bu boshqa amallar ham xavfsiz ekanini anglatmaydi.

Bu hujjat xatolarni tuzatganlik sertifikati emas. Mahsulotning manba kodi tuzatilmadi. Testlar yangi, ajratilgan SQLite bazalarida bajarildi. `backend/restaron.db` faqat `mode=ro` va `PRAGMA query_only=ON` orqali o'qildi. Undagi nomuvofiqliklar avtomatik tozalanmadi. Build tekshiruvida `frontend/dist` qayta yaratildi. UI'ning qolgan qismlarini ko'rish uchun yetishmayotgan bitta import faqat vaqtinchalik Vite diagnostika transformida qo'shildi; quyidagi UI kuzatuvlari shu shart bilan o'qiladi.

**“Bitta ham bug qolmagan”, “barcha mumkin bo'lgan usullar sinalgan” yoki “buyurtma hech qachon yo'qolmaydi” deb kafolat berish mumkin emas.** Quyida sinalgan holatlar, natijalar va ochiq qolgan chegaralar aniq ajratilgan. Aliposter 1.0.0.0 nusxasi bu muhitda mavjud emas; undan tezroq yoki qulayroq ekaniga bevosita solishtirma baho berilmadi.

1. Dalillar va tekshirish doirasi

| Tekshiruv | Natija va chegarasi |
|---|---|
| Frontend production build | `npm run build` o'tdi: 10.67 soniya. Lekin shu build brauzerda `LanguageProvider is not defined` bilan ochilmadi. |
| Mavjud backend testlari, tizim Python'i | 69 test: **68 o'tdi, 1 yiqildi**, 39.15 s. Kutubxonalar: SQLAlchemy 2.1.3, HTTPX 0.28.1, Pydantic 2.13.5. |
| Mavjud testlar, loyihaning `.venv` kutubxonalari | 69 test: **67 o'tdi, 2 yiqildi**, 79.75 s. SQLAlchemy 2.0.30, HTTPX 0.27.0, Pydantic 2.7.1. Yetishmayotgan `pytest-asyncio` faqat tashqi test plaginidan o'qildi, paket o'rnatilmadi. |
| Maxsus API/integratsion sinovlar | 20 asosiy ssenariy guruhi ikkala kutubxona muhitida; yana 12 qo'shimcha ssenariy guruhi `.venv` da. Har bir ishga tushirish yangi baza yaratadi. |
| Yuklama | `.venv` da 30, 60, 100 alohida ofitsiant; yangi buyurtma → qo'shish → +1 → oshxona → to'lov. Keyin yangi bazada 100 ofitsiant bilan qayta sinov. |
| Frontend–API mosligi | 135 ta `api.get/post/patch/delete` chaqiruvi marshrutlar bilan solishtirildi; admin POS'da 3 ta mos kelmaydigan manzil. Bu dinamik quriladigan barcha URL va barcha `fetch` chaqiruvlarini qoplaydigan formal tekshiruv emas. |
| UI | Ofitsiant va admin kirishi, taom qo'shish, savat, admin POS chek tugmasi, adminning barcha 12 navigatsiya bo'limi, mijoz QR menyusi, ofitsiant chaqiruvi va hisobni ko'rish. 390×844 va 1440×900 o'lchamlar ko'rildi. Har bir formaning barcha qiymatlari UI orqali tekshirilgan emas. |
| Chek | Test checkout yaratgan bitta PDF render qilinib ko'rildi; printer navbati, retry va status testlari bajarildi. Haqiqiy qog'ozga chop etish sinalmadi. |
| Mahalliy baza | Fizik integrity, bog'lanishlar, ochiq buyurtma takrorlari, summalar va printer navbati faqat o'qildi. Bu faylning haqiqiy restoran ishlab turgan bazasi ekanligi tasdiqlanmadi. |

**Mavjud testlardagi yiqilishlarni mahsulot buglari bilan adashtirmaslik kerak:**

- `test_hygiene_12.py::test_5_stale_orders_endpoint`: `403` o'rniga `401`. Oldingi concurrency testlari 3001–3003 user ID'larini boshqa rollar bilan yaratadi; hygiene fixture mavjud foydalanuvchining rolini tiklamaydi. Hygiene fayli yangi bazada alohida bajarilganda **5/5 o'tdi**.
- `test_perf_14.py::test_payments_report_sql_aggregation`: yarim tundan keyingi `.venv` yugurishida karta summasi 0. Fixture to'lovni `now - 1 hour` qilib yaratadi, endpoint esa sanasiz so'rovda bugungi Toshkent kunini hisoblaydi. Yarim tundan keyin bu yozuv kechagi kunga tushadi. Testga qat'iy vaqt yoki aniq sana oralig'i kerak; bu natija o'zicha ishlab chiqarish hisobotining xatosi ekanini isbotlamaydi.

## 2. Ishga tushirishni to'sadigan tasdiqlangan xatolar

P0 — ishga tushirishdan oldin yopilishi shart; P1 — muhim funksional/moliyaviy xavf; P2 — aniqlik, qulaylik yoki cheklangan sharoitdagi muammo.

### A01 — P0: sayt joriy manbadan yig'ilganda bo'sh ekran

- Dalil: production build brauzer konsolida `ReferenceError: LanguageProvider is not defined`.
- Manba: `frontend/src/main.jsx` komponentni JSX'da ishlatadi, lekin import qilmaydi. Xato React daraxti yaratilayotganda sodir bo'lgani uchun ichkaridagi ErrorBoundary ham uni ushlamaydi.
- Tuzatish: mavjud `LanguageProvider` eksportini import qilish; builddan keyin haqiqiy brauzerda mijoz va xodim sahifalarining ochilishini majburiy tekshirish. Build o'tishini ishga tushish isboti deb qabul qilmaslik.

### A02 — P0: bir xil amal takroran hisobga yoziladi

- Sinov: bitta buyurtmada 1 ta taom bor. Bir xil user, endpoint, body va `Idempotency-Key` bilan 10 parallel `add-items` yuborildi.
- Kutilgan: yakuniy son **2**. Amaldagi natija: **11**, barcha javoblar `200`. `.venv` da ham takrorlandi.
- Manba: `backend/app/core/idempotency.py:29`, `:50`; `orders.py:1094`. Kesh biznes qulfidan oldin tekshiriladi; javob biznes tranzaksiyasi commit bo'lganidan keyin alohida yoziladi. Keyingi unique-key konflikti allaqachon qo'shilgan taomni bekor qilmaydi.
- Tuzatish: amal kalitini tranzaksiyada oldindan atomar band qilish; buyurtma o'zgarishi va natijani bir tranzaksiyada saqlash; qulf olingandan keyin qayta tekshirish; body fingerprint; natijasi noma'lum qolgan amal uchun frontendda o'sha kalitni saqlash.

### A03 — P0: parallel qarz to'lovlari yo'qoladi

- Sinov: 100 000 so'm qarzga bir vaqtda 20 ta 1 000 so'mlik to'lov. Hammasi `200`.
- Kutilgan `paid_amount`: **20 000**. Bazada: **1 000**. Ikki kutubxona muhitida ham takrorlandi.
- Manba: `backend/app/routers/debts.py:143`. Qarz o'qiladi, xotirada summa oshiriladi va qayta yoziladi; to'lov qatorlari yoki atomar shartli yangilash yo'q.
- Tuzatish: har to'lovni alohida, takrorlanmaydigan yozuv sifatida saqlash; qarz qatorini qulflash yoki shartli atomar UPDATE; qoldiqdan ortiq birgalikdagi to'lovni ham tranzaksiyada tekshirish.

### A04 — P0: o'chirish va to'lov bir-birining hisobini buzadi

- Sinov: ikki taomli 20 000 + 10% xizmat hisobida bir taomni o'chirish va checkout parallel yuborildi, 10 marta takrorlandi.
- Natija: barcha juftliklar `200/200`; **9/10 holatda** yakuniy `total=11 000`, `cash_amount=22 000`. To'langan hisobning tarkibi to'lov jarayoni bilan to'qnashib o'zgardi.
- Manba: `backend/app/routers/orders.py:1644` o'chirishda buyurtma qulfi yo'q; checkoutdagi qulf bu yo'lni o'zicha himoya qilmaydi.
- Tuzatish: buyurtmaga ta'sir qiluvchi BARCHA yo'llarda bir xil qulf tartibi, yopilganlikni qulfdan keyin tekshirish va kerak bo'lsa versiya nazorati. To'lov snapshotini o'zgarmas saqlash.

### A05 — P0: ikki taomni parallel o'chirishdan keyin noto'g'ri ochiq hisob qoladi

- Sinov: ikki xil taom qatori parallel o'chirildi, 10 marta.
- Natija: **10/10** holatda taomlar soni 0, `subtotal=10 000`, status `pending`. Kutilgan summa 0 va bo'sh hisob uchun izchil yakuniy holat.
- Sabab: har sessiya eski ikki qatorli tarkibdan o'z natijasini hisoblaydi. Ikkala o'chirish bajariladi, lekin biri ikkinchisining summasini almashtiradi.
- Tuzatish: A04 bilan birga yagona tranzaksion o'zgartirish xizmati; yakuniy summa va stol holatini qulf ostida hisoblash.

### A06 — P0: menyudan taom o'chirilsa eski buyurtmalarning tarkibi ham o'chadi

- Manba: `backend/app/routers/menu.py:346` ichida `DELETE OrderItem WHERE menu_item_id=...` bor.
- Ochiq va to'langan buyurtmada alohida sinov qilindi: menyu DELETE `204`, buyurtmadagi taomlar **1 dan 0 ga** tushdi, eski subtotal esa 10 000 bo'lib qoldi.
- Muhim farq: mavjud `ReceiptArchive.items_json` snapshoti bu sinovda o'chirilgani ko'rsatilmagan. Ammo order tarixi va shu tarkibdan hisoblanadigan hisobotlar zarar ko'radi.
- Tuzatish: tarixda ishlatilgan taomga soft-delete/arxivlash; eski order line'da nom, birlik va sotilgan narx snapshoti. Tarixiy order item'larni katalog o'chirish orqali o'chirmaslik.

### A07 — P0: maxfiy integratsiya sozlamalari autentifikatsiyasiz qaytadi

- Sinov: tokensiz `GET /api/v1/restaurants/1` testdagi `telegram_bot_token` va `sms_provider_api_key` qiymatlarini qaytardi.
- Manba: `backend/app/routers/restaurants.py:127` ORM restoranini `settings` bilan to'liq serializatsiya qiladi; ommaviy response schema yo'q.
- Tuzatish: ommaviy restoran DTO'sida faqat mijoz uchun kerakli maydonlar; integratsiya kalitlarini faqat vakolatli sozlamalar endpointida ham maskalash. Haqiqiy kalitlar shu endpoint orqali ilgari ochilgan bo'lsa, ularni almashtirish kerak.

### A08 — P0: restoranlar orasidagi ruxsat ajratilishi to'liq emas

- Test restoran 2 ofitsianti restoran 1 buyurtmasiga taom qo'shdi: `200`.
- Restoran 1 admini restoran 2 sozlamasini o'zgartirdi: `200`.
- Restoran 1 ofitsianti restoran 2 stollarini QR tokenlari bilan oldi: `200`.
- Restoran 1 buyurtmasi restoran 2 stoliga ko'chdi: `200`; `order.restaurant_id=1`, yangi stol restoran 2 bo'lib qoldi.
- Restoran 1 orderiga restoran 2 menyu taomi qo'shildi: `201`.
- Manbalar: `orders.py:839`, `:1094`, `:1878`, `:2142`; `tables.py:389`, `:1501`; `restaurants.py:143`, `:160`; menyu va qarz yo'llarida ham tenant scope'ni tizimli ko'rish kerak.
- Tuzatish: har obyektga DB query darajasida `restaurant_id` scope; order–table–menu.category bog'lanishini tekshirish. Faqat frontendda yashirish yoki rol nomini tekshirish yetmaydi.

### A09 — P0: katta parallel yuklamada SQLite yozuv qulflari tugaydi

- 60 va 100 ofitsiant sinovlarida server xatolari chiqdi; yangi bazada 100 ofitsiant bilan takrorlanganda aniq sabab **`sqlite3.OperationalError: database is locked`** bo'ldi.
- Bular bitta stolga ataylab urilgan so'rovlar emas: ofitsiantlar turli stollarda o'z buyurtmalarini yuritdi.
- Tuzatish: biznes yaxlitligi xatolarini avval yopish, yozuv tranzaksiyalarini qisqartirish, PostgreSQL migratsiyasini tegishli constraint/indexlar bilan tayyorlash va o'sha bazada qayta yuklama sinovi. Faqat timeout'ni uzaytirish yoki worker sonini oshirish ishonchli yechim emas.

## 3. Boshqa tasdiqlangan funksional va moliyaviy kamchiliklar

| ID / daraja | Tasdiqlangan holat | Kerakli o'zgarish |
|---|---|---|
| A10 / P1 | Admin `POSView.jsx:538` `POST /orders/{id}/bill` yuboradi; backend yo'li `/print-bill`. Brauzerda “Chek” tugmasi **Method Not Allowed** berdi. | API manzilini tuzatish va brauzer E2E chek oqimini qo'shish. |
| A11 / P1 | `POSView.jsx:500` `/portion-size`, backend `/size`; `:1219` esa PATCH `/orders/{id}`, backend `/notes`. Izohdagi catch faqat console'ga yozib oynani yopadi. | Ikkala contractni tuzatish; saqlanmasa foydalanuvchiga aniq xabar va ochiq forma. |
| A12 / P1 | Printer sozlanmagan holda oshxonaga yuborish `200`, ticket `skipped`, job yo'q. Printer keyin sozlansa ham qayta oddiy yuborish `nothing_new=true`, job 0. | `sent_quantity` ni ish navbatga olingani bilan izchil bog'lash; sozlanmagan stansiyani bloklash/yoki tiklanadigan navbatda saqlash. Hozir reprint orqali qo'lda chiqarish mumkin, avtomatik tiklanish ishlamadi. |
| A13 / P1 | `send_to_kitchen_immediately=true` bilan qo'shilgan taom yuborilgan deb belgilandi, lekin **print job 0**. `orders.py:1155`. | Shu flag uchun ham haqiqiy tranzaksion ticket/job yaratish yoki flagni olib tashlash. |
| A14 / P1 | To'langan buyurtma uchun `send-to-kitchen` oddiy so'rovi `200` va yangi job yaratdi. `orders.py:1878`. | Yopilgan/bekor qilingan buyurtmani oddiy yuborishda rad etish; alohida vakolatli, auditli reprint. |
| A15 / P1 | Taom 10 000 narxda orderga kirdi; katalog 20 000 bo'lgach `+1` qilindi. `unit_price=10 000`, quantity 2, `total_price=40 000`. `orders.py:302`, `:1304`. | Qator summasini sotilgan `unit_price` asosida hisoblash; yangi narxni alohida qator/aniq siyosat bilan qo'llash. |
| A16 / P1 | Tortiladigan taomga qo'lda 100 000 summa yozilib, aynan shu taom yana qo'shildi. Quantity 2, jami hanuz 100 000; ikkinchi porsiyaga alohida narx talab qilinmadi. | Vazn, hajm va manual summa bo'yicha qatorlarni aralashtirmaslik; yangi tortilgan porsiyani alohida narxlash. |
| A17 / P1 | `payment_method=debt` va to'liq naqd summa birga yuborilganda checkout `200` bo'ldi va to'liq miqdorda yangi qarz ham yaratildi. `orders.py:2300`. | Qarzni faqat haqiqiy `debt_amount` asosida yaratish; bir-biriga zid to'lov body'larini rad etish. |
| A18 / P1 | `allow_debt_payment=false` bo'lsa ham debt checkout `200`. | Sozlamani backend checkoutda ham majburiy tekshirish. |
| A19 / P1 | 5 000 avansli stolning 11 000 hisobida checkout yana 11 000 naqd yozdi va stoldagi avans 0 bo'ldi. | Avansga o'zgarmas to'lov yozuvi, to'lovda avansni hisobga olish va ko'chirish/qaytarish tarixi. Avans alohida hisoblanishi biznes qoidasida ko'zda tutilgan bo'lsa, UI va jurnal buni aniq ko'rsatishi kerak. Hozir durable avans ledger'i yo'q. |
| A20 / P1 | Ikki manbadan bir bo'sh stolga parallel transfer: bittasi `200`, ikkinchisi **500** (`UNIQUE constraint failed: orders.table_id`). | Stollarni yagona tartibda qulflash; bandlikni qulfdan keyin tekshirish; konfliktni tushunarli `409` qilish. |
| A21 / P1 | Bir restoran uchun ikkita parallel Z-yopish **ikkalasi 200**, ikkita report ID, ikkalasida shift_number 1. Sinov restoranda savdo bo'lmagan; shu sinov daromad ikki marta hisoblanganini isbotlamaydi. | Smena identifikatori va bitta atomar yopish; takroriy Z uchun idempotency/unique constraint. |
| A22 / P1 | `/tables/{id}/checkout` to'langan order yaratdi, lekin shu order uchun `ReceiptArchive` soni **0**. | Eski va yangi checkout yo'llarini bitta to'lov/chek xizmatiga birlashtirish. |
| A23 / P1 | `service_fee_percent=-50` sozlamasi `200`; yangi 10 000 order jami 5 000 bo'ldi. `SettingsUpdate` da chegaralar yo'q. | Xizmat haqi 0–100; qog'oz eni, retention, stol sig'imi, avans va nullable maydonlarga ham izchil validatsiya. |
| A24 / P1 | Admin tasdig'i olingan waiter HTTP'da `403`, lekin `authenticate_ws_token` o'sha userni qabul qildi. `routers/ws.py:22`. | WebSocket va optional auth'da ham faollik, tasdiq va token bekor qilinganligini bir xil tekshirish; mavjud sessiyani bekor qilish. |
| A25 / P2 | QR token ko'rsatmasdan faqat `table_id` bilan ofitsiant chaqirish `200`. Rate limiter bor, ammo mijozning aynan shu stolga huquqi isbotlanmaydi. | QR/session tekshiruvi; rate limiter himoyasini saqlash. |
| A26 / P2 | Noma'lum `order_type='unknown'` va bo'sh items bilan order `201`. | Turlarni enum/Literal bilan cheklash; bo'sh draft uchun alohida oqim va muddati o'tgan draft siyosati. |

## 4. Koddan tasdiqlangan, to'liq joyida sinalmagan xavflar

Bu ro'yxatdagi bandlar uchun quyidagi aniqlik muhim: koddagi sabab topilgan, ammo real qurilma yoki barcha vaqt ketma-ketliklarida sodir bo'lish chastotasi o'lchanmagan.

- **POS'da javoblar tartibi va eski stol:** `WaiterDashboard.fetchTableActiveOrder` hamda admin POS fetch funksiyasi kechikkan javob qaysi tanlangan stolga tegishli ekanini qayta tekshirmaydi. Bir stol javobi yangi stol tanlanganidan keyin kelishi mumkin. Ofitsiantda mutation navbati mavjud, admin POS esa absolute quantity bilan va navbatsiz yozadi. Ikki kassir bir xil eski quantity'dan foydalansa, yangilanish yo'qolishi mumkin. API darajasida aynan 20 ta `delta=+1` to'g'ri ishlashi adminning absolute quantity oqimini tasdiqlamaydi.
- **Transfer WebSocket xabari:** `POSView.jsx` `event.order` yoki items yo'q bo'lsa `isCancelled=true` deb oladi. Transfer handleri ayrim `order_updated` xabarlarini `order` obyektsiz yuboradi. Band stolni ekranda bo'sh ko'rsatish xavfi bor.
- **Ko'p server jarayoni:** WebSocket manager, rate limit, token revocation va printer lock/busy holatlari process xotirasida. Printer job'ni olish SELECT → status UPDATE tarzida, atomar claim yo'q. Bir necha workerga o'tishdan oldin tashqi event almashish va yagona printer worker/atomar claim kerak. Bu auditda multiprocess stress bajarilmadi.
- **Docker WebSocket marshruti:** brauzer `/api/v1/ws/...` ga ulanadi, `frontend/nginx.conf` da Upgrade esa faqat `/ws/` location uchun sozlangan. `/api/` location'da upgrade yo'q. Docker ichidagi haqiqiy WS handshake hali sinalmagan; konfiguratsiya mos kelmaydi. `/uploads/` uchun ham backend proxy yo'q.
- **PostgreSQL tayyorgarligi:** maxsus indekslar va schema yangilashlar `database.py` da SQLite branchida. SQLite'dagi unique ochiq-order himoyasini PostgreSQL'da avtomatik bor deb hisoblash mumkin emas. Migratsiya va constraintlar alohida tayyorlanishi kerak.
- **Docker standart kalitlari:** compose ichidagi JWT secret va DB paroli o'zgarmas ochiq namunaviy qiymatlar. Hozirgi secret validator uzunligi yetarli bo'lgan compose namunasini qabul qiladi. Ishchi deploy shu qiymatlarni ishlatadimi — tekshirilmagan. Deploy oldidan majburiy almashtirish va validatsiya kerak.
- **Pul turi:** order/debt/payment ustunlari `Float`. Moliyaviy model uchun integer kichik birlik yoki Decimal/Numeric, yagona yaxlitlash siyosati va balans constraintlari ma'qul.
- **Printer “done” ma'nosi:** USB spooler yoki TCP'ga yuborilganlik qog'oz jismonan chiqqanini har doim isbotlamaydi. Bosib bo'lgach server to'xtab, `done` yozilmay qolsa startup'dagi printing→pending tiklash dublikat chiqarishi mumkin. Qayta chiqarish “TAKROR”, job ID va operator tasdig'i bilan bo'lishi kerak. Printer o'chiqligida pending job ustiga yangi reprint ochilishi ham ko'rib chiqilsin.
- **So'rov timeout va qayta urinish:** frontend yozuv uchun 25 s kutadi; yuklamada bundan uzun yozuvlar bor. Timeout natija noma'lumligini anglatadi. Yangi bosishda yangi idempotency key yaratiladi; `delta` yo'li esa bunday key ishlatmaydi. Saqlash holatini tiklash va aynan o'sha amalni aniqlash kerak.
- **Rasmlar va fon so'rovlari:** bir necha ekran barcha menyu rasmlarini oldindan yuklaydi; har yangilashda tarix bilan birga orderlar ham olinadi. Rasmlar katta bo'lsa Wi-Fi yuklanadi. Menyu uchun versiya/kesh, ko'rinayotgan rasmga ustuvorlik va active-order API kerak.
- **100 ta order cheklovi:** ekranlar ko'pincha default limit 100 bilan, paid/active ajratmasdan ro'yxat oladi. Eski ochiq/tayyor orderlar ko'p tarix ortida ko'rinmay qolish xavfi bor. Bu DB'dan o'chirilish emas; UI qamrov muammosi.
- **Test intizomi:** UI'da build xatosini ushlaydigan smoke test yo'q. Rootdagi ayrim eski test skriptlari `localhost:8000` ga to'g'ridan-to'g'ri yozadi va ishlab turgan bazani tanlashi mumkin; ular bu auditda ishga tushirilmadi. Faqat aniq izolyatsiya bilan ishlatish kerak.

## 5. Yuklama va tezlik natijalari

ASGI in-process transport ishlatildi: tarmoq, telefon rendering'i, Wi-Fi va jismoniy printer xarajati kiritilmagan. Har ofitsiantning alohida user ID/tokeni va o'z stoli bor. Printer job'lar DB'ga yozildi, haqiqiy printer worker'i ishlamadi. Checkout PDF fon vazifalari normal kod orqali ishga tushdi. Dastlabki yugurishda boshqa audit ishlari ham bo'lgan; bu ajratilgan benchmark serverining qat'iy SLA o'lchovi emas. Qayta yugurishdagi aniq lock xatolari muammoni mustaqil tasdiqladi.

`p95`: so'rovlarning 95 foizi shu vaqtdan tezroq yakunlangan.

| Bosqich | Jami so'rov | Xato | Order yaratish p50 | Order yaratish p95 | Butun bosqich |
|---|---:|---:|---:|---:|---:|
| 30 ofitsiant | 150 | 0 | 11.57 s | 19.84 s | 21.96 s |
| 60 ofitsiant | 296 | 3 ta HTTP 500 | 12.06 s | 34.43 s | 39.05 s |
| 100 ofitsiant | 388 | 31 ta HTTP 500 | 26.59 s | 36.23 s | 53.04 s |
| 100 ofitsiant, yangi bazada qayta | 484 | 5 ta `database is locked` istisnosi | 18.16 s | 32.76 s | 45.47 s |

Jami so'rovlar bosqichlarda turlicha: order yaratolmagan worker keyingi to'rtta amalni bajarmaydi. Qayta yugurishda ASGI exception'ni tashqariga chiqarish yoqilgan, shuning uchun xato “500” o'rniga uning aniq turi bilan qayd etilgan. Bu ikki xil hisoblash usuli bir xil qatorga yashirib qo'shilmadi.

Qayta 100 ofitsiant sinovida 96 ta order to'landi, 95 ta kitchen job yaratildi. Ya'ni bir hisob to'langan bo'lsa ham uning shu sinovdagi kitchen yuborishi xato bo'lgan. Kod checkoutdan oldin barcha taomlar oshxonaga yetib borganini majburiy tekshirmaydi; bu talab biznes siyosati bilan aniq belgilanib, UI'da ko'rsatilishi kerak.

**O'tgan parallel nazoratlar:** bir stolga 20 parallel create → 1 order va aynan 20 ta taom; 20 parallel delta → aynan +20; 5 parallel send → bitta station job; 5 parallel checkout → 1 muvaffaqiyat + 4 konflikt, 1 qarz. Bular `.venv` da ham o'tdi. Ularning o'tishi A02–A06'dagi boshqa poygalarni yopmaydi.

### Tezlatish tartibi

1. A02–A08: avval ma'lumot va pul yaxlitligi. Noto'g'ri natijani tez qaytarish foyda bermaydi.
2. Order mutation'larini bir xizmatga yig'ish; umumiy qulf tartibi, atomar idempotency va qisqa DB tranzaksiyalari. Response o'qishidagi ortiqcha tranzaksiya vaqtini ham o'lchash.
3. PostgreSQL migratsiyasi: backup/rehearsal, tarixni muvofiqlashtirish, barcha kerakli indeks/constraintlar, PostgreSQL'da takroriy race/load test. Hozirgi buglar bazani almashtirish bilan avtomatik tuzalmaydi.
4. Bitta POS komponenti va bitta API contract. Admin/Ofitsiant huquqi alohida, hisoblash va sinxronlash bir xil bo'lsin.
5. Active orders endpointi, kerakli pagination, menyu kesh/versiyasi, WebSocket orqali kichik yangilanishlar; takroriy to'liq refetch'larni kamaytirish.
6. `bcrypt.checkpw` hozir async login ichida sinxron ishlaydi; login burst va event-loop kechikishini alohida o'lchab, threadpool'ga chiqarish. Bu auditda login burst latency soni o'lchanmadi.
7. Real zalda qabul mezoni sifatida, masalan, LAN'da odatiy yozuv p95 <500 ms, p99 <1.5 s va nol kutilmagan 5xx belgilash mumkin. Bular hozir erishilgan raqamlar emas, biznes bilan kelishiladigan taklif chegaralaridir.

## 6. Mahalliy baza holati

Tekshirilgan fayl: `C:\RestAron\backend\restaron.db`, 774 144 bayt. `.env` da database URL ko'rsatilmagan; kodning sukut varianti SQLite. Tashqi muhit o'zgaruvchisi bilan ishlayotgan server boshqa bazani ishlatishi mumkin; uning jonli deployment sozlamasi tasdiqlanmadi.

| Holat | Soni |
|---|---:|
| Restoran / stol / user / menyu taomi | 2 / 47 / 24 / 89 |
| Order / order item | 78 / 102 |
| Bir nechta ochiq orderi bor stol | 1 |
| `subtotal` va mavjud item summasi mos kelmaydigan order | 17 |
| To'langan jami va naqd+karta+click+qarz mos kelmaydigan order | 3 |
| Taomsiz ochiq/to'lanmagan order | 15 |
| Printer done / pending / printing | 72 / 124 / 1 |
| Foreign key buzilishi | 17 ta print_job mavjud bo'lmagan orderga bog'langan |

`PRAGMA integrity_check = ok`: bu disk fayli fizik tuzilishi yaxshi ekanini bildiradi, yuqoridagi biznes nomuvofiqliklarini inkor qilmaydi. `ux_orders_one_open_per_table` indeksi bu faylda yo'q. Startup kodi mavjud dublikatlarni ko'rsa indeks yaratishni faqat warning bilan o'tkazadi. Test engine ulanishida `PRAGMA foreign_keys=0` ham tasdiqlandi.

Yozuvlar demo, oldingi test yoki ishchi savdoga tegishli ekanini bu raqamlarning o'zi bildirmaydi. **Avval zaxira, keyin arxiv cheklari/to'lovlar bilan solishtirish, so'ng operator bilan kelishilgan tuzatish** kerak. Qolgan 124 job'ni real printerga ulashdan oldin ularning eskirganligi ham tekshirilsin. Bu audit ularni chop etmadi yoki o'chirmadi.

## 7. Dizayn va ishlatish qulayligi

Baholar diagnostika importi bilan ochilgan interfeysga tegishli. Dastlabki joriy build A01 sabab umuman ochilmadi.

**Yaxshi asos:** zonalar, stol tanlash, menyu qidiruvi, ko'rinadigan savat summasi, mobil menyu/savat o'tishi, xizmat haqi ajratilishi va printer muammosi banneri bor. Mijozning QR menyusi, ofitsiant chaqirishi va o'z hisobini ko'rishi sinovda ishladi. Adminning barcha navigatsiya bo'limlari ochildi; bu bo'limlarning barcha CRUD holatlari o'tganini bildirmaydi.

**O'zgartirishlar:**

- Ofitsiant ekranida suratli katta kartalar bilan birga **ixcham ro'yxat** va **tez-tez sotiladiganlar** rejimi bo'lsin. Katta zalda taomni kamroq scroll bilan topish surat animatsiyasidan muhimroq.
- Stol qidiruvi, “mening stollarim”, zona/bandlik filtri va o'zgarish qilayotgan xodim nomi. 139 sun'iy stol bilan uzun ro'yxatlar ko'rildi; haqiqiy zaldagi joylashuv bilan sinash kerak.
- “Tasdiqlash” amali nimani tasdiqlashi aniq yozilsin: **Oshxonaga yuborish**. Holatlar: saqlanmoqda → bazaga saqlandi → printer navbatida → printerga yuborildi → muammo. Job yo'q/skipped holatini muvaffaqiyat sifatida ko'rsatmaslik.
- Checkoutda order versiyasi/jami o'zgarsa kassirga yangi summa ko'rsatilib qayta tasdiqlansin. Avans, qoldiq, aralash to'lov va nasiya alohida tushunarli bo'lsin.
- Admin POS'dagi `alert`, muvaffaqiyat konfettisi va xatoni faqat console'ga yozish o'rniga bir xil toast va tiklanadigan forma ishlatilsin.
- 390 px sinovda asosiy tab tugmalari 44 px balandlikda, til tugmalari esa taxminan 25×23 px. Tez ishlash uchun asosiy tegish nishonlarini kamida 44 px qilish, ikonkalarga aniq nom va klaviatura/fokus qo'shish tavsiya etiladi.
- Ofitsiant panelida RU tanlanganda asosiy POS matnlari o'zgarmadi. Ko'p matnlar hardcode qilingan; to'liq tarjima sifatida ko'rsatishdan oldin barcha POS va xato xabarlari lug'atga o'tkazilsin.
- Yangi order bir necha daqiqa turganida ekran taxminan “5s 2daq” bandlikni ko'rsatdi. SQLite'dan kelgan timezone'siz UTC `created_at` frontend `new Date` orqali mahalliy vaqt deb olinmoqda. API barcha vaqtlarni offset/`Z` bilan qaytarsin; print va PDF ham bir xil Toshkent vaqtini ishlatsin.
- Tema tanlash `handleToggleThemeSelection` da faqat React context'ni o'zgartiradi; serverga saqlanmaydi. Admin tanlagan ikki tema boshqa mijoz qurilmasiga doimiy qo'llanadi degan UI va'dasi hozir kod bilan bajarilmayapti.
- Kassir ham admin navigatsiyasini oladi, lekin to'lovlar hisoboti va cheklar ro'yxati kabi ayrim endpointlar cashier rolini qabul qilmaydi. Vakolatli bo'limlar ro'yxatini rolga mos qilish; kassirga kerakli kassa hisoboti huquqini biznes bo'yicha belgilash.
- Oshpaz paneli `App.jsx` da ataylab olib tashlangan, ammo README va `enable_chef_kds` sozlamasi bor. Printer-only ish tartibi tanlansa, ishlamaydigan KDS va'dasi/sozlamasi yashirilsin. KDS talab qilinsa, ekran qayta amalga oshirilishi kerak.
- QR rasmini ko'rsatadigan ayrim admin joylari tashqi `api.qrserver.com` dan foydalanadi. Lokal QR generator mavjud: internet o'chganda ham foydalanish uchun shu resursga o'tish ma'qul.

**PDF kuzatuvi:** bitta 80 mm test PDF'da son va summalar o'qiladi. Sarlavha yonidagi emoji kvadrat bo'lib ko'rindi, footer matni koddagi 40 belgi kesish sabab qisqargan; vaqt UTC'da chiqib, oshxona matnidagi mahalliy vaqtdan farq qiladi. Uzoq taom nomlari, 58 mm, ko'p qator va haqiqiy Xprinter shrift/kirill mosligi shu bitta render bilan tasdiqlanmaydi.

## 8. Bo'limlar bo'yicha baho

10 ball — ishchi sharoitda ishonchli va tasdiqlangan holat. Bular o'lchangan foizlar emas, topilgan dalillarga asoslangan muhandislik bahosi.

| Yo'nalish | Baho | Sabab |
|---|---:|---|
| Buyurtma hisobining yaxlitligi | 2/10 | O'chirish/to'lov va menyu o'chirish bo'yicha P0 xatolar. |
| Ko'p xodim bilan barqarorlik | 3/10 | Ba'zi lock testlari o'tdi, katta yuklamada SQLite lock va idempotency xatosi bor. |
| To'lov, nasiya, avans, smena | 2/10 | Parallel qarz to'lovi yo'qoladi; avans va Z-yopish izchil emas. |
| Xavfsizlik va restoran ajratilishi | 2/10 | Ommaviy secret javobi va cross-restaurant yozishlar. |
| Oshxona/printer dasturiy oqimi | 4/10 | Persistent navbat/retry bor, ammo skipped/immediate/paid yuborish xatolari bor; hardware sinalmagan. |
| Mijoz menyusi va chaqiruv | 6/10 | Diagnostika nusxasida asosiy oqimlar ishladi; QR avtorizatsiya va tiklanish cheklovlari bor. |
| POS qulayligi va dizayn | 6/10 | Asos qulay, admin/ofitsiant farqi, kichik boshqaruvlar va noto'g'ri muvaffaqiyat holatlari ishni sekinlashtiradi. |
| Zaxira/tiklash va ekspluatatsiya | 5/10 | SQLite backup/restore testlari o'tdi; haqiqiy tiklash mashqi, PostgreSQL va uzilishlar sinalmagan. |
| Testlar va release nazorati | 4/10 | 69 backend test bor, lekin UI startup bugi o'tib ketgan va fixturelar o'zaro ta'sir qiladi. |
| Hozir katta choyxonada ishga tushirishga tayyorlik | **1/10** | Ishga tushirishni to'sadigan bir nechta mustaqil P0 mavjud. |

## 9. Ishga tushirish uchun aniq qabul shartlari

1. Barcha P0 va asosiy P1 lar tuzatiladi; yuqoridagi reproducerlar kutilgan qiymatlar bilan regression testga aylantiriladi.
2. Yangi va eski orderlar: subtotal = item summasi; total = subtotal + xizmat − chegirma; to'langan summalar jami = total. Qarzni yopish va avans ledger'i ham mos bo'ladi. Mavjud mahalliy anomal yozuvlar kelib chiqishi aniqlanadi.
3. Bitta stolga bitta ochiq order constraint'i kafolatlanadi. Dublikat bo'lsa server uni jim o'tkazib ishlayvermaydi; xavfsiz tuzatish jarayoni mavjud bo'ladi.
4. Rejalashtirilgan eng ko'p xodim soni va kamida 2 baravar burst bilan **maqsadli server, maqsadli baza va haqiqiy HTTP/WebSocket** orqali sinov. Nol yo'qolgan/takroriy amal, nol kutilmagan 5xx; har javob bilan yakuniy baza ham tekshiriladi.
5. Printer o'chirish/yoqish, qog'oz tugashi, USB/LAN uzilishi, bosish o'rtasida restart, pending ustiga reprint, oshxona/bar ajratilishi, o'zbek/kirill shrift va 58/80 mm amalda sinaladi.
6. Telefon ekran bloklanishi, Wi-Fi uzilishi, qayta ulanish, ikki kassir bir orderda, eski sahifadan to'lov, bir vaqtdagi qaytarish/checkout/transfer va yarim tungi smena amalda tekshiriladi.
7. Backup alohida diskka olinadi va bo'sh sinov serveriga tiklab tekshiriladi. Qancha ma'lumot yo'qotish va qancha vaqtda tiklash mumkinligi egasi bilan kelishiladi; UPS va LAN ishlashi tekshiriladi.
8. Avval cheklangan stol/xodimlar bilan pilot smena; yakunda naqd, karta, nasiya, avans va cheklar qo'lda solishtiriladi. Aliposterga qaytish rejasi tayyor turadi; bir savdoni ikkita tizimga chalkash tarzda ikki marta kiritishdan saqlaniladi.

Ishonchli yakuniy yuklama mezonini tanlash uchun haqiqiy bir vaqtdagi ofitsiantlar soni, stol soni, server CPU/RAM/disk, printer modellari/ulanishi va LAN/Wi-Fi tuzilishi kerak. Bu ma'lumotlar berilmagan; ular taxmin qilinmadi.

## 10. Qolgan tekshirilmagan doira

Haqiqiy restoran serveri va qurilmalari; PostgreSQL va Docker ichidagi amaliy sinov; bir necha server processi; uzoq muddatli 8–24 soat soak; elektr/disk to'lishi/OS restart; haqiqiy printer va to'lov terminali; haqiqiy SMS/Telegram yetkazilishi; barcha brauzer/telefon kombinatsiyalari; barcha CRUD qiymatlari va har route uchun to'liq permission matrix; tashqi dependency/CVE skaneri; mustaqil pentest; Aliposter 1.0.0.0 bilan yonma-yon tezlik/UX o'lchovi. Ularning tekshirilmagani yashirilmaydi va “o'tdi” deb belgilanmaydi.

## 11. Takrorlash va xom natijalar

Quyidagi fayllar `C:\RestAron\scratch` ichida saqlangan. Skriptlar haqiqiy baza o'rniga `audit_test_<unique>.db` yaratadi. UI serveri uchun faqat sun'iy foydalanuvchilar ishlatilgan. Asl testlar yoki eski root E2E skriptlarini ishchi serverga qarshi nazoratsiz ishga tushirmang.

- `audit_probes.py`, `audit_probes.json`, `audit_probes_venv.json`: asosiy reproducerlar va natijalar.
- `audit_extra.py`, `audit_extra.json`: o'chirish/to'lov, transfer, avans, smena va qo'shimcha ruxsat holatlari.
- `audit_load.py`, `audit_load.json`, `audit_load_repeat.json`: barcha endpointlarning p50/p95/p99/max va error tafsilotlari.
- `audit_pytest_run2.txt`, `audit_venv_pytest_log.txt`, `audit_hygiene_isolated.txt`: mavjud testlarning to'liq natijalari.
- `audit_inventory.py`, `audit_inventory.json`: mahalliy baza uchun faqat o'qish so'rovlari.
- `audit_route_contracts.py`, `audit_route_contracts.json`: frontend API mosligi.
- `audit_contract_smoke.py`, `audit_contract_smoke.json`: noto'g'ri/to'g'ri POS marshrutlari va cashier ruxsat tekshiruvi.
- `audit_build.txt`, `audit_ui_sections.json`: build va admin bo'limlari kuzatuvi.
- `audit_waiter_desktop.png`, `audit_waiter_mobile.png`, `audit_admin_print_error.png`, `audit_customer_bill.png`: diagnostika UI dalillari.
- `audit_receipt_preview.png` va `audit_pdf_archive/`: test cheki ko'rinishi; bu haqiqiy savdo hujjati emas.

Asosiy reproducer:

```powershell
backend/.venv/Scripts/python.exe scratch/audit_probes.py
backend/.venv/Scripts/python.exe scratch/audit_extra.py
backend/.venv/Scripts/python.exe scratch/audit_load.py
```

Sinovlar OS sandboxida Python asyncio sikli hatto oddiy `asyncio.sleep` da to'xtab qolganidan so'ng sandboxdan tashqarida, shu izolyatsiya saqlangan holda bajarildi. Sandboxdagi boshlang'ich timeout/temp ruxsat xatolari mahsulot xatosi sifatida hisoblanmadi.
