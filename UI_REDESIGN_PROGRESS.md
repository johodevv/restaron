# Interfeysni bosqichma-bosqich moslashtirish

2026-10-29. Tugmalar joylashuvi AliPos 1.1 A251 kuzatuvlariga moslashtiriladi; ranglar Dunyo Choyxona uchun alohida bo‘ladi. Mavjud funksiyalar va vakolatlar saqlanadi. Har bosqich alohida tekshiriladi va commit/push qilinadi. Ishchi domen yoki Cloudflare bu lokal sinov uchun ishga tushirilmaydi.

## 1-qism — ofitsiant panelida Back / Forward

- Stol, mobil menyu/savat va buyurtma oynalari brauzer tarixiga bog‘landi.
- Back ochiq buyurtma oynasini yopadi; keyingi bosqichlarda menyu va stollar ro‘yxatiga qaytadi. Forward navigatsiyani qayta ochadi.
- Tarixda buyurtma tarkibi, narx, token yoki mijoz ma’lumoti saqlanmaydi. Navigatsiyaning o‘zi savdo amallarini yubormaydi.
- Stol almashtirish, tez ketma-ket qaytish, oynani ekran tugmasi orqali yopish, saqlash vaqtida qaytish, tinglovchini tozalash uchun regressiya testlari qo‘shildi.
- 30 ta frontend testi va production build o‘tdi.
- Microsoft Edge’da haqiqiy lokal backend bilan desktop va 400 px mobil emulyatsiyada tekshirildi: izoh → buyurtma → stollar; mobil savat → menyu; Forward; taom qo‘shilgach Back/Forward orqali 1 ta taom va 39 200 so‘m hisob saqlanishi. Konsolda sinov paytida JavaScript xatosi kuzatilmadi (brauzerning lazy-image eslatmalari bor).
- Sinov bazasi loyiha tashqarisida, printer sozlamalari o‘chirilgan; ishchi baza ishlatilmadi. Fizik telefondagi Back/gesture va barcha mobil brauzerlar alohida sinov qilinmagan. Global tema/printer oynalari bu qismning tarix boshqaruviga hali kiritilmagan.

## 2-qism — POS joylashuvi va Dunyo uslubi

Kompyuterda savat chapdagi taxminan uchdan bir qismda, menyu o‘ngda; telefonda savat yuqorida va menyu pastda birga ko‘rinadi. Savatni yoyish/menyuga qaytish tugmasi bor. Takroriy mobil stol satri va pastki savat tasmasi olib tashlandi. Asosiy oshxonaga yuborish amali hisob yonida. Mavjud transfer, izoh, narx/kg, chop etish va to‘lov amallari hamda vakolatlari saqlandi.

Dunyo logotipi, ko‘k-kulrang yuzalar, yashil asosiy amal va aniqroq jami summa ishlatildi. Qisqa telefon ekranida mahsulot rasmlari yashirilib nom/narx/qo‘shish uchun joy ajratiladi; uzunroq ekran va desktopda rasmlar qoladi.

Tekshiruv: 30 frontend testi; production build; Edge’da 400 px va 360 px mobil emulyatsiya hamda 1536 px desktop. Savatni yoyish va hisob saqlanishi kuzatildi. Sinov bazasida tarozili taomga 180 000 kiritilganda 1.5 kg hisoblandi va saqlandi; umumiy hisob 240 800 bo‘ldi. Physical printer yoki domen ishlatilmadi. Brauzerning AudioContext autoplay ogohlantirishi kuzatildi; bu JavaScript istisnosi emas, ovoz uchun foydalanuvchi harakati talabidir.

## 3-qism — admin navigatsiyasi va sozlamalar

2026-10-30. Yuqorida Buyurtma olish / Stollar va QR / Boshqaruv, o‘ngda yangilash; ichki bo‘limlar Savdo va hisob / Restoran / Sozlash guruhlariga ajratildi. Kassirning avvalgi bo‘lim cheklovlari saqlandi. Uzun ro‘yxat mustaqil siljiydi; bo‘lim almashtirilganda tashqi ish maydoni boshiga qaytadi. Ulanish va dastur versiyasi ma’lumoti yig‘iladigan tafsilotga olindi. Kichik kassa panelida summa bilan to‘lov/oshxona tugmalari alohida qatorlarga sig‘dirildi.

Sozlamalar yetti bo‘limga ajratildi; barcha inputlar mounted qoladi, ichki bo‘lim almashtirish kiritmalarni yo‘qotmaydi. 1043 px Chrome oynasida yettala bo‘lim amalda ochildi; restoran nomiga vaqtincha QA qo‘shilib, boshqa bo‘limdan qaytganda saqlangani tekshirildi va nom asl qiymatga qaytarildi. Saqlash tugmalari mavjudligi tekshirildi; ushbu amaliy sinovda integratsiya/QR ruxsatlari yoki fizik printer sozlamalari saqlab o‘zgartirilmadi.

30 frontend testi, production build va 142 tanlangan backend regressiya testi o‘tdi. Backend test tayyorlash funksiyasi AnyIO runneriga aniq bog‘landi: pytest 9 oddiy testlaridagi asinxron autouse fixture xatosi tuzatildi. Bu serverning ishchi kodini yoki bazasini o‘zgartirmaydi. Kutubxonalarning 6 ta deprecation ogohlantirishi bor; test xatosi yo‘q.

## Qolgan qism

4. To‘lov ko‘rinishi va yakuniy regressiya: mavjud hisob-kitob va printer oqimini saqlagan holda lokal tekshiruv.

Tekshiruvlar cheklangan muhitdagi dalildir; barcha qurilmalarda mutlaq xatosizlik kafolati emas. Yangi aniqlangan muammo bartaraf etilmaguncha tegishli qism tugallangan hisoblanmaydi.
