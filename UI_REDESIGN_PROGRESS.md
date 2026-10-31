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


## 2026-10-30 — hisoblarni birlashtirish, menyu va sessiya tuzatishlari

Foydalanuvchi tasdiqlagan qoida: admin/kassir ham, ofitsiant ham ikki band stolning ochiq hisobini birlashtiradi. Barcha taomlar qabul qiluvchi hisobning xizmat foizi va ofitsiantiga o‘tadi; ofitsiant ulushi ham qabul qiluvchi hisob stavkasida qayta hisoblanadi. Tasdiqlash oynasida stollar/zona, hisob raqamlari, ofitsiant, foiz, avvalgi va yangi jami, avans va qolgan summa ko‘rsatiladi. Bo‘sh stolga ko‘chirish avvalgi amal orqali ishlaydi.

Birlashtirish serverda bitta tranzaksiyada bajariladi: tartibli row lock, tasdiqlangan ikki hisob ID/version tekshiruvi, idempotency va majburiy audit bor. Taom satrlarining ID, narx/kg/qo‘lda kiritilgan summalari va oshxonaga yuborilgan/tayyorlangan sonlari saqlanadi; birlashtirishning o‘zi oshxona chekini qayta chiqarmaydi. Chegirmalar yig‘iladi, avans pul tushumi sifatida takror yozilmasdan qabul qiluvchi stolga o‘tadi. Eski hisob bazada merged_into_order_id bilan bog‘lanadi; uning asl summasi va taomlari audit snapshotida saqlanadi. Manba stol bo‘shaydi. Bron/ta’mir, bir stolda bir nechta ochiq hisob, mos kelmaydigan tarixiy summa, eski to‘lov yozuvi yoki ortiqcha avans bo‘lsa amal rad etiladi.

Stol qidiruvi barcha ofitsiant tanlash/ko‘chirish oynalaridan olib tashlandi. Taom qidiruvi saqlanadi. Menyu kategoriyalari endi yonlama surilmay, qatorlarga joylashadi va sonini ko‘rsatadi. Mobil rasmlar balandligi 64 dan 96 px ga oshirildi; alohida + belgisi olib tashlandi, taom kartasini bosish qo‘shadi. Saqlangan hisobni fonda qayta tekshirish menyuni yana xiralashtirmaydi; birinchi yuklanishda yolg‘on 0 jami o‘rniga Hisob yuklanmoqda yozuvi bor.

Login oqimida eski sessiyadan kech kelgan 401 yangi sessiyani chiqarib yubormasligi, eski auth/me javobi yangi foydalanuvchini bosib ketmasligi tuzatildi. Boshlang‘ich ulanish va qayta ulanish holatlari ajratildi; 2 soniyadan uzun uzilishda banner/Qayta urinish chiqadi. Haqiqiy ruxsat xatosi yashirilmaydi. Uvicorn jurnalida aniq xato ham topildi: token filtri AccessFormatter talab qiladigan 5 argumentni o‘chirib, har so‘rovda formatter exception chiqarayotgan edi. Argumentlar saqlanib, tokenni yashirish davom etadi. Haqiqiy lokal server qayta ishga tushirilgach HTTP 200 jurnallari va token=[redacted] WebSocket yozuvi formatter xatosisiz tekshirildi.

Tekshiruv: 49 frontend testi, production build va diff tekshiruvi o‘tdi. 228 backend testi o‘tdi (7 dependency deprecation ogohlantirishi, xato yo‘q). Yangi merge testlari uchala rol, bir xil kalit bilan parallel retry, eskirgan version, teskari yo‘nalishdagi parallel merge, audit saqlanmasa rollback, avans va keyingi checkoutni qamrab oladi. Jurnal filtri haqiqiy Uvicorn AccessFormatter bilan sinaldi.

Chrome 360 px emulyatsiyada 6 kategoriya 2 qatorga sig‘ishi, stol qidiruvi yo‘qligi, rasmlar/alohida + yo‘qligi, menyu va buyurtma o‘tishlari tekshirildi. Alohida merge-test.db bazasida Zal Stol 1 (240 800) Xona Stol 1 (1 030 400) hisobiga qo‘shildi: jami 1 271 200; 4 ta satr/30 birlik va 1.5 kg baliqning 180 000 summasi saqlandi. Bazadan ham ID va summalar solishtirildi; eski hisob 2-hisobga bog‘langan, manba stol bo‘sh. Brauzer boshqa tabga o‘tkazilib lokal test backend qayta ishga tushirilganidan keyin qaytishda ulanish tiklandi. Sinov uchun 8029-port, alohida baza va test ma’lumotlari ishlatildi; 8028 server va ishchi savdo bazasi qayta ishga tushirilmadi.

Sinov tayyorlashda qo‘lda qo‘shilgan test taomlarining nullable statistik maydonlari sabab menu/full 500 chiqdi; test fixture defaultlari to‘ldirilib HTTP 200 qayta tekshirildi. Build vaqtida eski ochiq tab o‘chgan eski lazy chunkni so‘rab xato berdi; sahifani yangilash yangi buildni yukladi. Ushbu ikki kuzatuv ishlab turgan saytdagi uzilishning dalili deb olinmadi. Yakuniy yangi tabda ilovaga tegishli shu xatolar qolmadi; Blackbox kengaytmasining CORS/fetch xatolari alohida kuzatildi.

Bu o‘zgarish server kodini ham o‘z ichiga oladi: orders jadvaliga nullable merged_into_order_id migratsiyasi avtomatik qo‘llanadi. Boshqa kompyuterda yangilash BAT orqali backend/frontend birga yangilanishi kerak. Cloudflare yoki ishchi domen serverini bu ish doirasida qayta ishga tushirish bajarilmadi. Haqiqiy Android/4G uzoq seansi va jismoniy printer bu qabul sinovida tekshirilmadi; ulanishlarning yagona ishlab turgan server sababi to‘liq aniqlangan yoki mutlaq xatosizlik kafolatlangan degan da’vo yo‘q.


## 2026-10-30 — kategoriya chegaralari va qator bo‘shliqlari

Kategoriya tugmalari 360 px da uch ustun, 640 px dan to‘rt, 1280 px dan besh ustun asosida joylashadi. Flex-grow oxirgi qatordagi qolgan kenglikni ham tugmalarga beradi. Oraliq 4 px, aniq ko‘k-kulrang border, oq matn va tanlangan kategoriyada yashil fon/och border bor; glow va scale olib tashlandi. Uzun nomlar kesilmay qatorga o‘raladi, son belgisi o‘ngda qoladi, bosish balandligi kamida 44 px.

49 frontend testi, production build va diff tekshiruvi o‘tdi. Chrome 360 px mobil emulyatsiyada alohida lokal test bazasidagi 12 kategoriya (Asosiy taomlar, Banichniy ichimliklar va boshqalar) 4 qatorga sig‘di, barcha nom/sonlar va borderlar ko‘rindi; qator oxirida bo‘sh ustun qolmadi. Savdo yoki to‘lov amali bajarilmadi. Oldingi turnda foydalanuvchi Esc bilan to‘xtatgan vizual tekshiruv shu turnda yakunlandi.


## 2026-10-31 — admin menyusini ixchamlashtirish va matnni kattalashtirish

Faqat admin/kassirning POSView oynasi compactMenu rejimini yoqadi: taom qidiruvi bu oynada render qilinmaydi. Desktop (1024 px va kengroq) uchun alohida POSView.css kategoriya tugmalarining flex asosini 125 px, minimal balandligini 34 px, paddingini 3/6 px qiladi. Kategoriyalar kamroq joy egallab, taomlar ro‘yxatiga joy ochadi. Foydalanuvchi keyingi skrinshotda ushbu admin joylashuvini ma’qulladi va faqat matnni biroz kattalashtirishni so‘radi: shrift 12 dan 13 px ga oshirildi; line-height, padding, kenglik asosi, oraliq va balandlik qoidalari saqlandi. Son belgisining 10 px shrifti avvalgidek.

Mavjud savdo muharriri umumiy bo‘lgani sabab qo‘shimcha propning standart qiymati false; faqat admin wrapper uni yoqadi. CSS ham data-menu-layout=compact belgisi bilan chegaralangan. Ofitsiantning qidiruvi, kategoriya o‘lchamlari, ranglari va buyurtma oqimi o‘zgarmaydi. Chrome’da yangi build bilan ofitsiantning 360 px ko‘rinishi amalda qayta ochilib, qidiruv va 12 kategoriyaning avvalgi 4 qatori saqlangani tekshirildi. Adminning alohida amaliy sinovi brauzer URL nazoratidagi vosita xatosi bilan to‘xtagan edi; adminning joylashuvini keyinchalik foydalanuvchi skrinshot va fikri bilan tasdiqladi. Oxirgi 13 px matn o‘zgarishi uchun alohida brauzer tasdig‘i olinmadi.

49 frontend regressiya testi va production build o‘tdi; faqat shrift o‘zgargach production build yana muvaffaqiyatli bajarildi. Backend, baza, printer va server boshqaruvi bu qismda o‘zgarmadi. Ishchi server qayta ishga tushirilmadi; tayyor distni mavjud server o‘qishi mumkin.

## 2026-10-31 — admin buyurtma turlari va band stollar

Admin/kassir POSView ichida Stollar, Olib ketish va Yetkazib berish yuqoridagi alohida tugmalar bo‘ldi. Olib ketish / Yetkazib berish avval shu turdagi ochiq buyurtmalar kartalarini va Yangi buyurtma kartasini ko‘rsatadi; mavjud kartani ochishda hisob serverdan qayta o‘qiladi, yangi kartada mijoz ma’lumotlari va mavjud taom muharriri ochiladi. Hisob birinchi taom qo‘shilgandagina mavjud API orqali yaratiladi. To‘lovdan keyin yopilgan karta chiqarilib ro‘yxat yangilanadi. Kartalarga qo‘shimcha bekor qilish yoki tez naqd yopish amallari qo‘shilmadi.

Rejimlar orasida o‘tish saqlash/yuborish tugamaguncha cheklangan. Eski o‘qish javoblari request va selection tekshiruvlari orqali boshqa rejimga tushmaydi; yopilgan hisob ochilmaydi, ro‘yxat qayta olinadi. Bir xil rejimni bosish hisobni o‘chirmaydi, ro‘yxatga qaytaradi. Olib ketish/dastavka to‘langanda eslab qolingan stolni noto‘g‘ri bo‘sh ko‘rsatadigan lokal holat admin rejimida cheklangan.

Zonalar yoniga Band stollar qo‘shildi: barcha zonalardagi faol band stollar, ularning soni va zona nomlari ko‘rinadi. Oddiy zona tugmasi shu zonaning barcha stollariga qaytaradi. Yangi rejim va filtr faqat admin wrapper yoqadigan prop bilan chegaralangan; ofitsiantning standart ko‘rinishi va transfer tanlagichi saqlangan.

Tekshiruv: 53 frontend testi, production build va diff tekshiruvi. Qo‘shimcha React server render tekshiruvi Yangi buyurtma kartasi, ikki tur ro‘yxatining ajralishi, to‘langan hisobning ko‘rinmasligi va mijoz matnining HTML sifatida bajarilmasligini tasdiqladi. Birinchi vaqtinchalik render skriptida Module.filename belgilanmagani sabab Node assertion chiqdi; skript tuzatilib tekshiruv muvaffaqiyatli o‘tdi. Bu ilovaning runtime xatosi emas. Brauzer orqali amaliy vizual tekshiruv oldingi turnda Computer Use URL aniqlash xatosi sabab to‘xtagan, ushbu qism uchun tugmalarni bosib yakuniy qabul sinovi bajarildi deb da’vo qilinmaydi. Backend/baza/printer amallari o‘zgarmadi; ishchi server qayta ishga tushirilmadi.

## 2026-10-31 — admin umumiy sahifasini surish

Admin POS tashqi qobig‘idagi h-full/overflow-hidden cheklovi olib tashlandi. Muharrirga alohida admin-pos-workspace balandligi berildi: viewportdan 100 px kam, kamida 560 px. Tashqi main allaqachon overflow-auto bo‘lgani sabab endi butun admin sahifasi pastga suriladi; yuqori navigatsiya ostida muharrir siqilmaydi. Menyu va savatning ichki surilishi ham saqlanadi. O‘zgarish admin JSX/CSS bilan chegaralangan. Production build va diff tekshiruvi o‘tdi; brauzerda amaliy scroll sinovi bajarilmadi.

## 2026-10-31 — stol ichidagi ortiqcha yuqori qator

Admin stol muharririda Stollar / Olib ketish / Yetkazib berish hamda Chaqiruvlar / Tayyor / ovoz / xodim qatori yashirildi. Stollarni tanlash ro‘yxatida qator ko‘rinadi. Stol ichida desktopda hisob sarlavhasi yoniga, tor ekranda menyu/buyurtma navigatsiyasiga 44 px qaytish tugmasi qo‘shildi; pending saqlash paytida qaytish bloklanadi. Ofitsiant, mijoz QR menyusi va boshqa buyurtma turlari o‘zgarmadi. 53 frontend testi, production build va diff tekshiruvi o‘tdi. Brauzerda amaliy vizual tekshiruv bajarilmadi.

## 2026-10-31 — asosiy navigatsiyani logo qatoriga ko‘chirish

Admin/kassir Navbar ichiga asosiy navigatsiya joyi qo‘shildi. AdminPrimaryNavigation mavjud tab va yangilash handlerlarini React portal orqali shu joyga chiqaradi; eski alohida qator takrorlanmaydi. Logo, Buyurtma olish / Stollar va QR / Boshqaruv / yangilash hamda til/tema/foydalanuvchi boshqaruvlari 1440 px dan keng ekranda bitta qatorda. Torroq ekranda navigatsiya shu yuqori panel ichida pastki qatorga tushadi va gorizontal suriladi. Ofitsiant va mijoz Navbar standart joylashuvi saqlangan. 53 frontend testi, production build va diff tekshiruvi o‘tdi. Brauzerda amaliy vizual sinov bajarilmadi.

## 2026-10-31 — stol bandligi va ko‘chirishda hisobni o‘qish

Stollar GET ro‘yxati va bitta stol javobi ochiq hisoblar sonini bitta guruhlangan so‘rovda hisoblaydi: eski AVAILABLE bayrog‘i bo‘lsa ham ochiq hisobi bor stol javobda occupied/is_occupied bilan ko‘rinadi. GET bazadagi tarixiy holat yoki summalarni qayta yozmaydi. Paid/cancelled arxiv hisoblari bandlikka kirmaydi. Transfer oynasi endi destination hisobini API orqali tekshiradi: haqiqiy ochiq hisob bo‘lsa birlashtirish preview va tasdiqlashga o‘tadi, bo‘sh bo‘lsa transfer endpoint ishlaydi. Tekshiruvdan keyin parallel ochilgan hisobni serverning mavjud lock/count himoyasi rad etadi.

Oddiy transfer faol bo‘lmagan, ta’mirdagi yoki hisobi yo‘q bo‘lsa ham occupied turgan stolga yuborilmaydi; manbada bir nechta eski hisob bo‘lsa kassir tekshiruvi talab qilinadi. Moved order version oshiriladi. Frontend ko‘chirishdan keyin eski activeOrder ref/state ni bo‘shatib destination scope o‘rnatadi va hisobni qayta o‘qiydi; 409 paytida ro‘yxat yangilanadi. Bir stolda bir nechta hisob topilsa yangi buyurtma yaratish read-error orqali bloklanadi. Transfer kartalarida zona nomi, oyna tepasida manba zona/stol/hisob raqami ko‘rinadi. Ofitsiant dizayni qayta ishlanmadi; umumiy savdo oqimining shu xavfsizlik tuzatishlari barcha rollarda qo‘llanadi.

Yangi 7 test stale AVAILABLE + ochiq hisob, ikkala hisob/taom/summa saqlanishi, band/ta’mir/faol bo‘lmagan targetni rad qilish, normal transferda order/item ID va sent miqdor saqlanishi, version oshishi, takror transfer rad etilishi hamda cancelled tarix band hisoblanmasligini tekshiradi. Birlashtirish bilan birga 15 test o‘tdi. To‘liq backend: 235 passed, 7 dependency deprecation warnings; frontend: 53 passed; production build/diff tekshiruvi o‘tdi. Brauzerda amaliy klik sinovi bajarilmadi.

Shu kompyuterdagi mavjud bazani sqlite mode=ro bilan tekshirganda Zal #3 ochiq hisobi joyida, Xona #3 da ochiq hisob yo‘qligi aniqlandi; foydalanuvchi rasmida Xona zonasi tanlangan. Bu kuzatuv boshqa kompyuterdagi bazaning ham tekshirilganini bildirmaydi. Ishchi hisoblar o‘zgartirilmadi/tiklanmadi, server qayta ishga tushirilmadi. Tuzatish backend va frontendni birga yangilashni talab qiladi; migratsiya yo‘q.

## 2026-10-31 — xulosa, chek sanalari va hisob xizmat foizi

Xulosa ichidagi So‘nggi va faol buyurtmalar kartalari olib tashlandi; statistik kartalar va mavjud boshqa xulosa qismlari saqlandi. Recent orders ma’lumotlari Stollar/QR yangilanish belgisi uchun hali ishlatiladi.

Cheklar arxiviga Sanadan / Sanagacha maydonlari, sanani tozalash va har sahifada 100 tadan chekka oldingi/keyingi tugmalari qo‘shildi. Backend yangi from_day/to_day parametrlarini Asia/Tashkent kun chegaralariga aylantiradi: oxirgi kun 23:59:59.999999 gacha kiradi, keyingi kun 00:00 kirmaydi. Teskari/invalid sana rad etiladi; oldingi start_date/end_date API parametrlari saqlandi. Teng vaqtli yozuvlar ID bo‘yicha tartiblanadi. Frontend kechikkan eski filtr javoblarini rad etadi, xatolarni ko‘rsatadi va qidiruvni yuborilgan qiymat bo‘yicha sahifalaydi. Ro‘yxat statistikasi mavjud yuklangan sahifa bo‘yicha ekanini bildiradi. Ko‘rish / chop etish GET orqali saqlangan chek matnini olib, mavjud ThermalReceiptModal oynasini ochadi; chop etish foydalanuvchining alohida amali. GET print job yaratmaydi.

Admin/kassir POS hisobining Xizmat (%) satri ostiga Foizni o‘zgartirish va shu joydagi saqlash formasi qo‘shildi. Yangi order-ID endpointi aynan tanlangan ochiq hisob foizini 0–100 oralig‘ida o‘zgartiradi (UI ikki kasr xonasigacha, vergul qabul qiladi). Order lock va expected_version eski summadan saqlashni rad etadi; jami qayta hisoblanadi, avans/chegirmadan past summaga tushirish bloklanadi, audit majburiy. Audit ishlamasa rollback, to‘langan/cancelled hisob va ofitsiant vakolati rad etiladi. Umumiy restoran foizi va tarixiy chek nusxalari o‘zgarmaydi. Pending saqlashda boshqa amallar cheklangan; hisob tanlovi o‘zgarsa forma yopiladi. Ofitsiant dizayniga xizmat foizi tahriri qo‘shilmadi.

Tekshiruv: to‘liq backend 240 passed (7 dependency deprecation warnings), frontend 53 passed, production build va diff tekshiruvi o‘tdi. Yangi 5 backend test holati kunning ikkala chegarasi, sana validatsiyasi, GET preview print job yaratmasligi, 0%/12.5%, boshqa hisob/umumiy foiz saqlanishi, audit, version, role, paid hisob, deposit va audit rollbackni qamrab oldi. Brauzerda amaliy vizual va fizik printer tekshiruvi bajarilmadi. Ishchi baza yozuvlari o‘zgartirilmadi; backend/frontend birga yangilanishi kerak, migratsiya yo‘q.

## 2026-10-31 — olib ketish va yetkazib berish ichki oynasini ixchamlashtirish

Admin order muharririda yuqoridagi buyurtma turlari/chaqiruv/tayyor/ovoz/xodim qatori endi uchala turda ham yashiriladi. Olib ketish va Yetkazib berish kartalari ro‘yxatida qator ko‘rinadi. Desktop hisob sarlavhasi yonida va tor ekrandagi navigatsiyada ixcham qaytish tugmasi aynan joriy tur ro‘yxatiga qaytaradi. Mavjud saqlash blokirovkasi saqlandi; hisob qaytish bilan o‘chirilmaydi. 53 frontend testi, production build va diff tekshiruvi o‘tdi. Brauzerda amaliy vizual tekshiruv bajarilmadi.

## 2026-10-31 — jonli aloqa qo‘lda qayta urinish

Foydalanuvchi dastlab sariq Jonli aloqa o‘rnatilmoqda holati uzoq turib, keyin ulanganini bildirdi. Tekshiruv vaqtida domen health endpointi User-Agent bilan HTTP 200 (1.64 s), ikki yaroqsiz diagnostik tokenli WebSocket handshake 0.875/0.75 s, kutilgan 4401 yopilishi bilan javob berdi. Bu haqiqiy foydalanuvchining o‘sha paytdagi login/tarmoq seansini qayta yaratish emas va dastlabki kechikish sababini isbotlamaydi. Oddiy urllib User-Agent so‘rovi 403 olgani server ishlamayapti deb talqin qilinmadi.

Aniq tiklash nuqsoni tuzatildi: UI Qayta urinish tugmasi avval avtomatik resume() ga ulangan, u esa hali 12 s bo‘lmagan handshake’ni saqlab, bosishni amalda bajarmas edi. Alohida retryNow() qo‘shildi: eski socket va backoff taymeri tozalanib yangi ulanish darhol boshlanadi. Ketma-ket 1 s ichidagi bosishlar cheklanadi. Avtomatik visibility/pageshow/online resume odati o‘zgarmadi, 4401/4403 rad etilgan seans va dispose’dan keyin qayta ulanish yo‘q. Dastlabki urinish xato bilan tugasa, UI endi connecting emas reconnecting holatini oladi; sariq tasma yoki yolg‘on connected holati yashirib qo‘yilmadi.

56 frontend testi (3 yangi tiklanish regressiyasi), production build va diff tekshiruvi o‘tdi. Alohida run_merge_local.py/merge-test.db serveri 8029 portda ui_admin sinov hisobi bilan haqiqiy protokolda tekshirildi: dastlabki ulanish 68 ms, qo‘lda retry 33 ms, states true/false/true va ikkita connection_established xabari. Domenning haqiqiy login seansi, Android uzoq seansi va brauzer tugmasini amalda bosish sinalmadi. Ishchi server/tunnel qayta ishga tushirilmadi; hisob yoki buyurtma ma’lumotlari o‘zgarmadi. Avvalgi kechikishning server/tarmoq sababi tasdiqlanmagan; bu o‘zgarish shu sabab butunlay yo‘qoldi degan kafolat emas.

## 2026-10-31 — mijoz va oshxona uchun alohida chek uslublari

Standart Dunyo matn cheki saqlandi. Admin → Boshqaruv → Restoran sozlamalari → Chek ko‘rinishi bo‘limida mijoz va oshxona/bar uchun alohida Dunyo yoki AliPoster uslubidagi grafik chek tanlanadi. Arial/Mercury oilasi, taomlar, sana/izoh, sarlavha, hisob raqami va jami yozuvlarining pt o‘lchami, qalinligi, qatorlar orasidagi masofa sozlanadi. Qog‘oz kengligi, sarlavha/pastki matn va qolgan mavjud sozlamalar saqlangan. Grafik namuna serverda aynan bosiladigan qora-oq rasm orqali ochiladi; oynani yopish yoki uning amallari sozlamalar formasini tasodifan yubormaydi. Namuna oynasi portal orqali ekran bo‘ylab ochiladi. USB xatosi avtomatik muvaffaqiyat deb ko‘rsatilmaydi.

Customer 14/18 WPF DIP qiymatlari 10.5/13.5 pt qilib o‘girildi. Oshxonaning alohida Aliposter.Printing.dll manbasida Arial 16 pt Bold va metadata 12 pt Regular aniqlandi. Mercury shu kompyuterdagi tizim/per-user shriftlari va AliPos papkasida topilmadi. Internet qidiruvi nomdosh turli shriftlarni ko‘rsatdi, aynan shu AliPos nusxasiga mos original fayl/manba tasdiqlanmadi; Mercury yuklab olinmadi va joyiga noma’lum boshqa shrift o‘rnatilmadi. Mercury uchun tanlash/tekshirish tayyor, lekin Regular/Bold o‘rnatilmaguncha shu tanlov saqlanishi va chiqarilishi aniq xato bilan to‘xtaydi; Arialga yashirin almashtirish yo‘q. Demak Mercury va fizik printerdagi birga bir moslik bajarilgan deb hisoblanmaydi.

Print document v1 snapshot’i yangi oshxona va yakuniy/mijoz hisoblarida navbat va arxivga yoziladi; navbatning qayta urinishi hamda arxivdan USB/PDF/brauzer orqali chiqarish shu layoutni oladi. Eski arxivda document yo‘q bo‘lsa eski matn cheki saqlanadi. Kitchen stansiyalari, bar, bekor qilish cheki va test printer namunalari alohida kitchen tanlovini oladi. 58mm chekda miqdor/narx alohida qo‘shimcha satrda, summa o‘ngda, uzun nomlar o‘raladi; katta raqamlar qog‘oz chetida yo‘qolmaydi. Arial Black xato ravishda Regular deb aniqlanishi namuna tekshiruvida topilib, shrift variantlari aniq Regular/Bold bilan cheklab tuzatildi.

Foydalanuvchining keyingi talabi bo‘yicha yangi mijoz chekining xizmat haqi satrida pul summasi chiqarilmaydi: Обслуживание | 12%. Jami summa xizmat haqini o‘z ichiga oladi. Standart Dunyo chekida ham avvaldan faqat foiz chiqishi o‘zgartirilmadi. Oshxona uchun xizmat haqi chiqarilmaydi.

Migratsiya: restaurant_settings jadvaliga customer_receipt_style/kitchen_receipt_style (default dunyo) va ikkita options JSON; receipt_archives jadvaliga nullable print_document JSON qo‘shiladi. Eski arxiv matni va savdo summalari qayta yozilmaydi. Frontend va backend birga yangilanishi kerak.

Tekshiruv: to‘liq backend 252 passed (7 mavjud dependency deprecation warnings); frontend 56 passed; production build va git diff --check o‘tdi. Yangi regressiyalar tanlovlarning mustaqilligi, idempotent yuborish, snapshot/reprint/PDF, eski arxiv, mavjud bo‘lmagan shrift/422 va rollback, role/range validation, ESC/POS raster baytlarini pikselgacha qayta tiklash (58/80mm), uzoq nom/vazn/summa, faqat foiz chiqishi, oshxona bekor qilish belgisi va eski sxemani ikki marta migratsiya qilishni qamraydi.

Chrome headless bilan 127.0.0.1:8029 dagi alohida merge-test.db/ui_admin hisobida haqiqiy UI tekshirildi: har ikki uslub, o‘lchamni o‘zgartirib saqlash/qayta ochish, Mercury yo‘q ogohlantirishi, ikkala grafik namuna, mijoz satrida 12% va summa yo‘qligi, to‘liq ekran modal, oyna yopilganda ortiqcha settings yozuvi bo‘lmasligi. JS xatosi 0; fizik print so‘rovi 0. PNG va browser-check.json C:/Users/johodev/Documents/RestAron-ui-local/receipt-style-previews ichida. Ishchi baza/tunnel/server o‘zgartirilmadi; faqat alohida lokal sinov serveri qayta ishga tushirildi. Fizik printer, haqiqiy termoqog‘ozdagi tiniqlik va Mercury birga bir mosligi tekshirilmagan.
