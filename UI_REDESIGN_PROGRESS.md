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

## 2026-10-30 — mobil bo‘shliq va ixcham savat tuzatishi

Keyingi AliPoster bilan birga bir dizayn rejalari va muhokamadagi qo‘shimcha funksiyalar foydalanuvchi tomonidan bekor qilindi. Ushbu tuzatish faqat mavjud interfeysdagi ikkita muammoga tegishli.

- Xodim paneli tashqarisidagi `min-h-screen` (100vh) va ichidagi 100dvh tafovuti bartaraf qilindi: xodimlar uchun yagona dinamik viewport va ichki scroll ishlatiladi. Tashqi hujjatning surilib qora bo‘shliq ochishi cheklangan. Mijoz sahifalarining min-height tartibi saqlandi.
- Tor savatdagi son tugmalarini ikkinchi qatorga tushirgan container qoidasi almashtirildi. Taom nomi, − / son / + va o‘chirish birinchi qatorda; narx, kg/hajm, vaqt, yuborish holati va jami ikkinchi qatorda. Tugmalar kamida 44 px; buyurtma amallari/vakolatlari o‘zgarmadi.
- 37 frontend testi, production build va diff tekshiruvi o‘tdi. Chrome’da 400 va 360 px mobil emulyatsiya, stollarni/savatni surish va 1043 px kompyuter ko‘rinishi tekshirildi. Lokal alohida sinov bazasida Osh 1 → 2 → 1: hisob 240 800 → 280 000 → 240 800 qaytdi. Oshxonaga yuborish, to‘lov va fizik chop etish bajarilmadi.
- Konsoldagi Blackbox brauzer kengaytmasining CORS/fetch xatolari va AudioContext autoplay eslatmasi ushbu sinovda ham bor; ular bu tuzatish bilan bartaraf etildi deb da’vo qilinmaydi. Haqiqiy Android brauzer paneli/klaviaturasi ochilib-yopilishi alohida qabul sinovini talab qiladi. Ishchi server yoki Cloudflare yangilanmadi.

## 2026-10-30 — mobil menyu/buyurtmani ajratish va ulanish tiklanishi

Foydalanuvchining yangi so‘roviga ko‘ra mobil ekrandagi birga ko‘rinadigan savat/menyu tartibi almashtirildi: Taomlar va Buyurtma tugmalari alohida ko‘rinishlarni ochadi. Menyuda pastki Buyurtmani ko‘rish tugmasi jami summani ko‘rsatadi; buyurtmada oshxonaga yuborish va mavjud amallar qoladi. Keng desktopda ikki panel yonma-yon. Bu AliPoster bilan birga bir dizayn rejasini qayta boshlash emas.

Ulanish kodida aniq takrorlangan zaif holatlar tuzatildi: ketma-ket resume hodisalari 12 soniyalik ochilayotgan handshake’ni qayta uzmaydi; vaqt tugagan handshake almashtiriladi; ping/pong yuborish istisnolari qayta ulanish navbatiga o‘tadi. Eskirgan ulanish almashtirilayotganda holat false bo‘ladi. Sahifa BFCache’dan qaytishidagi pageshow ham ulanishni tekshiradi. Eski socketlar va ruxsat rad etilgan ulanishlar himoyasi saqlandi.

Dalillar: 42 frontend testi, 5 WebSocket backend regressiya testi (6 dependency warning), production build va diff tekshiruvi o‘tdi. Alohida lokal bazadagi haqiqiy server bilan ulanish ochildi, ataylab yopildi, qayta tiklandi; ikki resume va keyingi 55 soniya ichida ortiqcha socket yoki heartbeat uzilishi bo‘lmadi. Domenning WebSocket endpointi diagnostik yaroqsiz token bilan handshake qabul qildi va kutilgan 4401 bilan yopildi; haqiqiy savdo hisobi bilan protokol testi bajarilmadi. Domain/frontend tekshiruvida yangi build asseti ham ko‘rindi: ushbu kompyuterdagi dist xizmatga bevosita uzatilayotgan bo‘lishi mumkin; backend, Cloudflare yoki boshqa kompyuter qayta ishga tushirilmadi.

Chrome 360 px mobil emulyatsiyada faqat menyu, faqat buyurtma, Back → menyu, Forward → buyurtma, summa/son saqlanishi tekshirildi. Lokal sinov miqdori asl holatga qaytarildi. Haqiqiy 4G/Android, Cloudflare orqali uzoq davom etuvchi autentifikatsiyalangan seans va printer sinovi bajarilmadi; rasmdagi uzilishning yagona ishlab turgan server sababi aniqlangan deb da’vo qilinmaydi. Konsolda kengaytmaning Blackbox CORS/fetch xatolari ko‘rindi; ular ilovaning WebSocket xatosi sifatida talqin qilinmadi.

## 2026-10-30 — ofitsiant panelini ixchamlashtirish va tez bosishlar navbati

- Ofitsiantda printer navbati komponenti endi mount qilinmaydi: tasma ham, uning 10 soniyalik summary so‘rovlari ham yo‘q. Admin/kassirda saqlanadi. Stollar sahifasidagi takroriy Stollar/holat/ovoz qatori olib tashlandi; chaqiruv belgisi Stol tanlang yoniga joylashdi. Chaqiruvlar sahifasi orqali mavjud tayyor taom va ovoz boshqaruvlari ochiladi.
- Ofitsiant stol ichiga kirganda tashqi logo/til/chiqish paneli yashiriladi, stollarga qaytganda tiklanadi. Ichkarida qaytish, Taomlar/Buyurtma va kerakli buyurtma amallari qoladi. Qisqa mobil ekranda taom rasmlarini yashirgan CSS qoidasi olib tashlandi; rasm URL’i yo‘q mahsulotda joytutgich qoladi. Mijoz QR menyusi o‘zgartirilmadi.
- Create/add/delta uchun tiklanadigan yagona navbat qo‘shildi. Ketma-ket bir xil taom qo‘shish yoki bir tomonga miqdor o‘zgarishlari serverning 50 birlik so‘rov chegarasigacha birlashtiriladi. Ekranda qolgan niyatlar tasdiqlangan server javobi ustiga hisoblanadi: kech kelgan WebSocket/poll javoblari pending sonni ortga tushirmaydi. Tarozili taomlar alohida qoladi; qo‘lda kiritilgan jami summa quantity preview’da birlik narxiga aylanib ketmaydi.
- Javobi noma’lum amal o‘sha idempotency kaliti bilan retry qilinadi, keyingi amallar xato ustiga yangi yaratish so‘rovlarini yubormaydi. Bitta saqlash ogohlantirishi va Qayta urinish/Navbatni bekor qilish bor. Navbatni bekor qilish tasdiqlangan buyurtmalarni o‘chirmaydi; bajarilmagan niyatlar bekor qilinib hisob serverdan qayta olinadi. Navbat faqat ochiq sahifa xotirasida: sahifani yopganda barcha yuborilmagan niyatlar saqlanadi, degan kafolat yo‘q. Hisobni GET bilan o‘qish muvaffaqiyatsiz bo‘lsa, o‘qilmaguncha yangi taom kiritish bloklanadi. Boshlang‘ich ma’lumotlarni parallel qayta yuklash ko‘payishi cheklangan.
- Saqlash indikatori normal holatda layout’ni o‘zgartirmaydigan qilib joylashtirildi. Avvalgi sinovda tepaga status qo‘shilishi ketma-ket bosish koordinatasini o‘zgartirishi aniqlanib, shu turn davomida tuzatildi. Pending paytida ko‘chirish va alohida o‘chirish cheklangan; boshqa panelga chiqilgach eski navbat yangi foydalanuvchi nomidan ish boshlamaydi.

Tekshiruv: 48 frontend testi (6 yangi navbat regressiyasi), 31 backend audit regressiyasi (6 dependency warning), production build va diff tekshiruvi o‘tdi. Haqiqiy alohida lokal bazada commit’dan keyin javobni ataylab yo‘qotish sinovida bitta hisobga 25 + 3 taom aniq yozildi; retry bilan jami 3 so‘rov. 20 plus va 10 minus 2 delta so‘roviga yig‘ilib, miqdor 35 va yakuniy summa server bilan teng bo‘ldi.

Chrome 360 px mobil emulyatsiyada ixcham stollar/ichki panel, rasmli kartalar va haqiqiy Offline → online → retry sinovi bajarildi: 3 online va 3 offline qo‘shishdan keyin Osh soni bazada 7, umumiy hisob 476 000 bo‘ldi. Keyingi kamaytirish va 5 marta tez minusdan so‘ng boshlang‘ich 1 ta Osh va 240 800 hisob tiklandi. 4G/Android apparatidagi tarmoq uzilishi yoki rasmdagi ishlab turgan server uzilishining asl sababi bu sinov bilan aniqlangan deb da’vo qilinmaydi. Ishchi bazada savdo, to‘lov yoki chop etish amallari bajarilmadi; backend/server/Cloudflare qayta ishga tushirilmadi.
