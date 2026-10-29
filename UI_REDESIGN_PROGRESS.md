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

## Keyingi qismlar

### 2-qism — POS joylashuvi va Dunyo uslubi

Kompyuterda savat chapdagi taxminan uchdan bir qismda, menyu o‘ngda; telefonda savat yuqorida va menyu pastda birga ko‘rinadi. Savatni yoyish/menyuga qaytish tugmasi bor. Takroriy mobil stol satri va pastki savat tasmasi olib tashlandi. Asosiy oshxonaga yuborish amali hisob yonida. Mavjud transfer, izoh, narx/kg, chop etish va to‘lov amallari hamda vakolatlari saqlandi.

Dunyo logotipi, ko‘k-kulrang yuzalar, yashil asosiy amal va aniqroq jami summa ishlatildi. Qisqa telefon ekranida mahsulot rasmlari yashirilib nom/narx/qo‘shish uchun joy ajratiladi; uzunroq ekran va desktopda rasmlar qoladi.

Tekshiruv: 30 frontend testi; production build; Edge’da 400 px va 360 px mobil emulyatsiya hamda 1536 px desktop. Savatni yoyish va hisob saqlanishi kuzatildi. Sinov bazasida tarozili taomga 180 000 kiritilganda 1.5 kg hisoblandi va saqlandi; umumiy hisob 240 800 bo‘ldi. Physical printer yoki domen ishlatilmadi. Brauzerning AudioContext autoplay ogohlantirishi kuzatildi; bu JavaScript istisnosi emas, ovoz uchun foydalanuvchi harakati talabidir.

2. Ofitsiant va umumiy POS: tanish tugma joylashuvi, Dunyo logosi, ko‘zga qulay ranglar; mobil asosiy amallarni soddalashtirish.
3. Admin navigatsiyasi va sozlamalar: yuqori asosiy bo‘limlar, chapda sozlamalar guruhlari; barcha mavjud amallar uchun joy.
4. To‘lov ko‘rinishi va yakuniy regressiya: mavjud hisob-kitob va printer oqimini saqlagan holda lokal tekshiruv.

Tekshiruvlar cheklangan muhitdagi dalildir; barcha qurilmalarda mutlaq xatosizlik kafolati emas. Yangi aniqlangan muammo bartaraf etilmaguncha tegishli qism tugallangan hisoblanmaydi.
