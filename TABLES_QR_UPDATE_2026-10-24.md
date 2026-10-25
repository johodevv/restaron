# Stollar va QR bo‘limi: qulaylik va kodlar barqarorligi

Holat: yangi frontend ishchi saytga qo‘llandi. Backend qayta ishga tushirilmadi. Eski build `backups/frontend_before_update_*` kataloglarida saqlandi; eski ochiq sahifalar uchun hashed assetlar qoldirildi.

**Yakuniy tekshiruv yangilanishi, 2026-10-24 08:51:** keyingi “davom et” murojaatida server jarayoni ishlamayotgani aniqlandi; jurnalda to‘xtash sababi topilmadi. Oldingi qayta ishga tushirish ruxsati asosida yangi zaxira (`backups/server_restart/tables_ui_20261024T035150Z.db`) olinib, server odatdagi nazoratchi bilan ishga tushirildi. Lokal va internet sahifasi 200, yangi frontend assetlari mos, baza ulanishi healthy. **Haqiqiy serverni shu qayta ishga tushirishdan keyin ham 41 ta stolning QR tokenlari va rasm manzillari avvalgi holatga teng.** Dalil: `scratch/tables_ui_final_verification.json`. Birinchi paragraf frontendni joylash paytidagi holatni bildiradi.

## Interfeys

- Raqam, nom va zal bo‘yicha qidiruv. Raqam aynan mos kelgan stol o‘z guruhida oldinga chiqadi. Bir xil raqamli stollar zali bilan ajratiladi.
- Zal hamda Bo‘sh/Band/Bron/Ta’mirda filtrlari birga ishlaydi; sanoqlar qidiruv va tanlangan zalni hisobga oladi. Filtrlarni tozalash va tushunarli bo‘sh natija bor.
- 8–9 tugmali katta kartalar o‘rniga ixcham raqam, holat, sig‘im, QR va amallar kartasi. Desktopda 4–5, telefonda 2 ustun.
- Stol tanlanganda uning ochiq hisobi serverdan alohida olinadi. Hisob/to‘lov/chek tugmalari faqat ochiq hisob tekshirilgach yoqiladi. Ochiq hisobli stolni bo‘shatish bloklangan; backend himoyasi ham saqlangan.
- O‘chirish va holatni qo‘lda almashtirish qo‘shimcha amallarga olindi. QRga to‘g‘ridan-to‘g‘ri kirish yoqilgan bo‘lsa, keraksiz PIN tugmalari ko‘rsatilmaydi. Majburiy PIN rejimida tasdiqlash va qulflash mavjud.
- Zal yaratish/tahrirlash va QR manzilini sozlash alohida sozlamalar oynasiga ko‘chirildi. Katta umumiy admin va tarmoq bannerlari bu sahifadan olib tashlandi; printer ogohlantirishlari saqlangan.
- Yangi stol formasi alohida oynada; ma’lumotlar yozilgach faqat stollar va zallar yangilanadi. Har bir stol uchun QR rasm oldindan yuklanmaydi.
- Tarmoq xatosida oldingi stol ro‘yxati saqlanadi, xato va qayta urinish ko‘rsatiladi. Oyna klaviaturada yopilishi va fokus qaytishi qo‘llab-quvvatlanadi.

## Qo‘shimcha topilgan bron xatosi

Eski forma ism, telefon, sana, mehmon soni va avansni yig‘ardi, lekin faqat stol statusini `reserved` qilardi. Endi mavjud `/tables/{id}/reserve` endpointiga to‘liq ma’lumot yuboriladi va avans serverdagi mavjud tranzaksiya/ledger orqali saqlanadi. `10 000` kabi bo‘shliq bilan yozilgan summa ham 10000 sifatida yuboriladi; manfiy, cheksiz va yaroqsiz summa qabul qilinmaydi. Tanlangan stolni bron qilishda yana yuzlab stoldan tanlash talabi olib tashlandi.

## QR kod server qayta yoqilganda o‘zgaradimi?

Oddiy restartda **yo‘q**, shu baza saqlansa. `qr_token` jadvalda saqlanadi. Ilova yangi UUIDni yangi stol yaratishda yoki alohida `regenerate-qr` amali chaqirilgandagina tayinlaydi. Qulflashdagi PIN boshqa narsa; u QR tokenni o‘zgartirmaydi.

Sinovda ilova bitta vaqtinchalik baza bilan **ikkita alohida Python jarayonida** to‘liq startup/shutdown qilindi. Birinchi va ikkinchi ishga tushirishdagi stol IDsi, tokeni, rasm manzili va qayta hosil qilingan PNGning SHA256 qiymati bir xil chiqdi. QR skanerlash, PIN qulflash va stolni bo‘shatish ham tokenni o‘zgartirmadi.

QR ichida sayt manzili ham bor. IP yoki vaqtinchalik `trycloudflare.com` manzili almashsa, eski qog‘ozdagi havola ishlamay qolishi mumkin. Yangi interfeys buni ko‘rsatadi va avval tanlangan doimiy domenni restart paytidagi vaqtinchalik lokal URL bilan almashtirmaydi. Manzilni o‘zgartirishda eski bosma QRlarga ta’siri tushuntiriladi. Alohida QR qayta yaratish amali eski tokenni bekor qiladi; u bu kundalik interfeysda taklif qilinmaydi.

Ishchi bazada **41 ta stolning** QR tokenlari va rasm manzillari frontendni qo‘llashdan oldin/keyin bir xil ekanligi tekshirildi. Joriy doimiy manzil: `https://dunyochoyxona.uz`.

## Tekshiruv va dalillar

- 9 ta JS mantiq testi o‘tdi: qidiruv, bir xil raqam/turli zal, filtrlar, ta’mir holati, domen barqarorligi va URL tekshiruvi. `scratch/tables_ui_tests.txt`.
- Tegishli 20 ta backend testi o‘tdi; yangi QR jarayonlararo restart testi ham alohida o‘tdi. Dastlab yangi test fixtureida majburiy `full_name` yetishmagan edi; fixture to‘g‘rilanib qayta sinovdan o‘tkazildi. `scratch/fixes_20261023/scratch/tables_qr_backend_tests.txt`, `qr_persistence_final.txt`.
- Brauzerda alohida bazadagi 139–140 stol bilan: 61-stolni qidirish, zal+holat filtri, bo‘sh natija, band stol hisobini aniqlash, bo‘shatishning bloklanishi, QR rasm, yangi stol yaratish va bron saqlanishi tekshirildi.
- Sinovdagi bron uchun bazada mijoz nomi/telefoni, 10000 avans va **bitta** 10000 avans harakati saqlangani qayta o‘qib tekshirildi. Bu ishchi savdo bazasida bajarilmadi. Fizik printer funksiyasi sinov serverida maket bilan almashtirildi.
- 390 px kenglikda komponentning gorizontal chiqib ketishi aniqlanmadi. Desktop va telefon rasmlari: `scratch/tables_ui_overview.jpg`, `tables_ui_mobile.jpg`, `tables_ui_actions.jpg`. Rasmlarda sinov ma’lumotlari bor.
- Yakuniy brauzer logida ilovaga tegishli error topilmadi; begona brauzer kengaytmasining xatolari alohida chiqarib tashlandi. Bu barcha ssenariylarda bug yo‘qligi kafolati emas.
- Build o‘tdi. Lokal va internet sahifalari 200; kirish assetlari yangi buildga mos. Internet orqali JS/CSS va admin chunk mazmuni diskdagi fayllarga teng. `scratch/tables_ui_publish_result.json`.
- Qo‘llash paytida ishchi navbatda 236–238 raqamli 3 ta vazifa bor edi. Ular oldingi bekor qilingan 60 ta vazifadan emas; bu UI yangilashida ularning holati o‘zgartirilmadi.

Telefonning haqiqiy kamerasi va qog‘ozga QR chop etish ushbu ishda sinovdan o‘tkazilmadi. Saytni Ctrl+F5 bilan yangilab, “Stollar & QR” bo‘limini ochish mumkin.
