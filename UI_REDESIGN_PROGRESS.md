# Interfeysni bosqichma-bosqich moslashtirish

2026-10-29. Tugmalar joylashuvi AliPos 1.1 A251 kuzatuvlariga moslashtiriladi; ranglar Dunyo Choyxona uchun alohida bo‘ladi. Mavjud funksiyalar va vakolatlar saqlanadi. Har bosqich alohida tekshiriladi va commit/push qilinadi. Ishchi domen yoki Cloudflare bu lokal sinov uchun ishga tushirilmaydi.

## 1-qism — ofitsiant panelida Back / Forward

- Stol, mobil menyu/savat va buyurtma oynalari brauzer tarixiga bog‘landi.
- Back ochiq buyurtma oynasini yopadi; keyingi bosqichlarda menyu va stollar ro‘yxatiga qaytadi. Forward navigatsiyani qayta ochadi.
- Tarixda buyurtma tarkibi, narx, token yoki mijoz ma’lumoti saqlanmaydi. Navigatsiyaning o‘zi savdo amallarini yubormaydi.
- Stol almashtirish, tez ketma-ket qaytish, oynani ekran tugmasi orqali yopish, saqlash vaqtida qaytish, tinglovchini tozalash uchun regressiya testlari qo‘shildi.
- 30 ta frontend testi va production build o‘tdi.
- Microsoft Edge’da haqiqiy lokal backend bilan desktop va 400 px mobil emulyatsiyada tekshirildi: izoh → buyurtma → stollar; mobil savat → menyu; Forward; taom qo‘shilgach Back/Forward orqali 1 ta taom va 39 200 so‘m hisob saqlanishi. Konsolda sinov paytida JavaScript xatosi kuzatilmadi (brauzerning lazy-image eslatmalari bor).
- Sinov bazasi loyiha tashqarisida, printer sozlamalari o‘chirilgan; ishchi baza ishlatilmadi. Fizik telefondagi Back/gesture va barcha mobil brauzerlar alohida sinov qilinmagan. Global tema/printer oynalari tarixga 4-qismda qo‘shildi.

## 2-qism — POS joylashuvi va Dunyo uslubi

Kompyuterda savat chapdagi taxminan uchdan bir qismda, menyu o‘ngda; telefonda savat yuqorida va menyu pastda birga ko‘rinadi. Savatni yoyish/menyuga qaytish tugmasi bor. Takroriy mobil stol satri va pastki savat tasmasi olib tashlandi. Asosiy oshxonaga yuborish amali hisob yonida. Mavjud transfer, izoh, narx/kg, chop etish va to‘lov amallari hamda vakolatlari saqlandi.

Dunyo logotipi, ko‘k-kulrang yuzalar, yashil asosiy amal va aniqroq jami summa ishlatildi. Qisqa telefon ekranida mahsulot rasmlari yashirilib nom/narx/qo‘shish uchun joy ajratiladi; uzunroq ekran va desktopda rasmlar qoladi.

Tekshiruv: 30 frontend testi; production build; Edge’da 400 px va 360 px mobil emulyatsiya hamda 1536 px desktop. Savatni yoyish va hisob saqlanishi kuzatildi. Sinov bazasida tarozili taomga 180 000 kiritilganda 1.5 kg hisoblandi va saqlandi; umumiy hisob 240 800 bo‘ldi. Physical printer yoki domen ishlatilmadi. Brauzerning AudioContext autoplay ogohlantirishi kuzatildi; bu JavaScript istisnosi emas, ovoz uchun foydalanuvchi harakati talabidir.

## 3-qism — admin navigatsiyasi va sozlamalar

2026-10-30. Yuqorida Buyurtma olish / Stollar va QR / Boshqaruv, o‘ngda yangilash; ichki bo‘limlar Savdo va hisob / Restoran / Sozlash guruhlariga ajratildi. Kassirning avvalgi bo‘lim cheklovlari saqlandi. Uzun ro‘yxat mustaqil siljiydi; bo‘lim almashtirilganda tashqi ish maydoni boshiga qaytadi. Ulanish va dastur versiyasi ma’lumoti yig‘iladigan tafsilotga olindi. Kichik kassa panelida summa bilan to‘lov/oshxona tugmalari alohida qatorlarga sig‘dirildi.

Sozlamalar yetti bo‘limga ajratildi; barcha inputlar mounted qoladi, ichki bo‘lim almashtirish kiritmalarni yo‘qotmaydi. 1043 px Chrome oynasida yettala bo‘lim amalda ochildi; restoran nomiga vaqtincha QA qo‘shilib, boshqa bo‘limdan qaytganda saqlangani tekshirildi va nom asl qiymatga qaytarildi. Saqlash tugmalari mavjudligi tekshirildi; ushbu amaliy sinovda integratsiya/QR ruxsatlari yoki fizik printer sozlamalari saqlab o‘zgartirilmadi.

30 frontend testi, production build va 142 tanlangan backend regressiya testi o‘tdi. Backend test tayyorlash funksiyasi AnyIO runneriga aniq bog‘landi: pytest 9 oddiy testlaridagi asinxron autouse fixture xatosi tuzatildi. Bu serverning ishchi kodini yoki bazasini o‘zgartirmaydi. Kutubxonalarning 6 ta deprecation ogohlantirishi bor; test xatosi yo‘q.

## 4-qism — kassa va yakuniy regressiya

2026-10-30. Keng ekranda kassa uch qismga ajratildi: buyurtma tarkibi; qolgan hisob/chegirma/qaytim; to‘lov turlari va katta raqamli tugmalar. Tor ekranda bo‘limlar ketma-ket joylashadi va oyna ichida siljiydi. Mavjud Naqd/Karta/Click/Aralash/Qarz yo‘llari, version va idempotency bilan checkout, serverda hisoblash va printer oqimi saqlandi. Alohida yangi backend savdo funksiyasi qo‘shilmadi. Raqamli tugmalar faqat kiritiladigan summani o‘zgartiradi; ularning o‘zi to‘lov qilmaydi.

Kassa ochilganda fokus chegirmaga emas, naqd maydoniga tushadi. Saqlash paytida oynani yopish cheklangan. Aniq 0 kiritilishi bo‘sh maydonning eski “aniq summa” xatti-harakatiga aylanib ketmasligi uchun yetishmovchilik tekshiruvi tuzatildi; bo‘sh maydonning avvalgi xatti-harakati saqlandi.

Tema va printer navbati oynalari umumiy ofitsiant Back/Forward oqimiga bog‘landi; yopilgan oynalar qayta ochilishi, unmount va tinglovchi tozalash testlari bor. Tema oynasida fokus va Escape boshqaruvi ham qo‘shildi.

Amaliy sinovlar: Chrome’da 1043 px va keng 1536 px ko‘rinish; 240 800 so‘mlik hisobga klaviatura bilan 250 000 kiritilib, 9 200 qaytim ko‘rildi. Aralash to‘lov yetishmaganda tasdiqlash faol bo‘lmadi; karta, Click va qarz maydonlari ochildi. Kassa Escape bilan to‘lovsiz yopildi. Ofitsiant hisobida tema → Back (yopildi) → Forward (qayta ochildi) → Escape (yopildi) tekshirildi; lokal URL saqlandi. Printer navbati oynasi uchun dasturiy test bor, bu sinovda printer navbati bo‘sh bo‘lgani sabab uning oynasi amalda bosilmadi.

Yakuniy tekshiruvlar: **37 frontend testi**, **218 backend testi** o‘tdi; production build va `git diff --check` muvaffaqiyatli. Backend testlarida 7 ta kutubxona deprecation ogohlantirishi bor, xato yo‘q. Chrome/Edge’ning autoplay va lazy-image eslatmalari kuzatilgan; jismoniy ovoz/printer natijasi bu sinov bilan tasdiqlanmaydi.

1–4 qismlar alohida commit va push qilindi. Domen orqali deploy yoki boshqa kompyuterdagi serverni yangilash bajarilmadi. Real printerdagi bosma sifat, haqiqiy telefon gesture/klaviaturasi va choyxonaning barcha qurilmalaridagi birgalikdagi ish alohida qabul sinovini talab qiladi; ularning hammasi bu dizayn sinovida tekshirildi, degan da’vo qilinmaydi.

Tekshiruvlar cheklangan muhitdagi dalildir; barcha qurilmalarda mutlaq xatosizlik kafolati emas. Yangi aniqlangan muammo bartaraf etilmaguncha tegishli qism tugallangan hisoblanmaydi.
