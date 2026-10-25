# Ofitsiant mobil paneli va chek — 25.10.2026

O‘zgarishlar lokal nusxada tayyorlandi. Boshqa kompyuterdagi dunyochoyxona.uz serveriga ulanmadi va Cloudflare ishga tushirilmadi.

## Nima o‘zgardi

- Ofitsiant avval zonani, so‘ng stolni tanlaydi. Taomlar stol tanlangandan keyin ochiladi. Aralash uzun ro‘yxat olib tashlandi.
- Zonalarda faqat faol stollar ko‘rinadi. Qidiruv tanlangan zona ichida ishlaydi; aniq raqam birinchi chiqadi. Bo‘sh stollar yashil, bandlari qizil, bron sariq; ta’mirdagi stol tanlanmaydi.
- Stollar ekraniga qaytish, taomlar/savat o‘rtasida o‘tish va stolni ko‘chirish telefonga moslandi. Ko‘chirishda ham zona orqali tanlanadi.
- Telefon kartochkalaridagi narx va qo‘shish belgisi bir-birining ustiga chiqmaydi. Ofitsiant o‘zi yaratgan buyurtma uchun keraksiz “yangi buyurtma” xabari olmaydi.
- Ofitsiant oshxonaga yuborilgan taomni o‘chirishi yoki sonini kamaytirishi mumkin. Amal foydalanuvchi nomi bilan auditga yoziladi va bekor qilish cheki bazadagi printer navbatiga bir tranzaksiyada saqlanadi. Printer sozlanmagan bo‘lsa, o‘chirish amalga oshmaydi.
- To‘langan hisoblar va boshqa restoran ma’lumotlari o‘zgartirilmaydi. Butun hisobni status orqali bekor qilish hamda kassirning avvalgi cheklovi saqlandi. Tortiladigan taomning kg/narxini tahrirlash saqlandi.

## Aloqa

Kirish sahifasida tokensiz va stolsiz qayta-qayta WebSocket ochilishi to‘xtatildi. Eski ulanish yangi ulanish holatini buzmaydi; ulanish va javob kutish muddati, telefon uyqudan qaytishi va internet tiklanishi hisobga olindi. Ping/pong xizmat xabarlari buyurtma obunachilariga yuborilmaydi. Server pinglariga javob beriladi, ortiqcha odatiy pinglar kamaytirildi.

Ruxsat rad etilganda brauzer endi 4401/4403 kodini oladi; cheksiz qayta kirishga urinish to‘xtaydi. Bunday ulanish restoran kanaliga yozilmaydi. Uvicorn 0.29.0 bilan websockets 12.0 hamda yangi kompyuterdagi 17.3 alohida haqiqiy ulanish sinovidan o‘tdi; versiya aybdor deb taxmin qilinmadi.

Boshqa kompyuterdagi aynan o‘sha uzilishning barcha sabablarini uning loglari va tarmog‘ini tekshirmasdan tasdiqlab bo‘lmaydi. Lokal dasturdagi topilgan kamchiliklar tuzatildi.

## Cheklar

Jadval qatorlarida ESC/POS belgi va qator oralig‘i vaqtincha to‘g‘rilanib, keyin printer sozlamasi tiklanadi. Jami to‘lovning shrift balandligi oshirilib, tagi chizib ajratiladi; ustun eni saqlanadi. Ekran va brauzer orqali chop etishda jami qalinroq, shrift qog‘oz eniga mos chiqadi.

Uzun nom, sarlavha va telefon raqamining kesilishi tuzatildi. Bir nechta tortiladigan porsiya uchun umumiy kg ko‘rsatiladi. Hisob va bekor qilish chekida zona nomi ham bor. Pul miqdorini ustunga sig‘dirish uchun oxirgi raqamlar kesilmaydi.

## Tekshiruv natijalari

- Backend: 213 ta test.
- Frontend: 23 ta test.
- Frontend yig‘ilishi o‘tdi; ishchi frontend/dist o‘rniga alohida sinov papkasiga yig‘ildi.
- 360, 390, 768 va 1366 piksel oynalarda haqiqiy brauzer sinovlari: zona filtri, takroriy stol raqamlari, buyurtmaning to‘g‘ri stolga tushishi, yuborilgan taomni o‘chirish, sahifani yangilash va haqiqiy WebSocket ulanishini uzib qayta ulash o‘tdi.
- Admin POS, buyurtma turi almashtirish, mobil stol ko‘chirish va printer ishlamagandagi chek ko‘rinishi sinovlari o‘tdi.
- 50 ta parallel lokal WebSocket ulanishi xabar almashdi. Uch ulanish to‘liq heartbeat davridan keyin ham ishladi. Noto‘g‘ri token/restoran uchun 4401/4403 tekshirildi.
- 58/80 mm, besh shrift va uch belgi oralig‘ida 30 ta chek ko‘rinishi tekshirildi; ESC/POS baytlari, jami ajratilishi va sozlamalarning tiklanishi ham tekshirildi.
- Bir taomni besh marta parallel o‘chirishda bitta bekor qilish cheki va bitta audit qaydi yaratildi. Printer sozlanmaganida tranzaksiya qaytarilishi tekshirildi.

Sinovlarda alohida vaqtinchalik bazalar ishlatildi. Haqiqiy printerga chop etish buyrug‘i berilmadi.

## Ko‘rish

Lokal sinov: http://127.0.0.1:8028/

“Xodimlar uchun” tugmasi → login **audit_1**, parol **Audit2026Local!**. Bu hisob va stollar sun’iy sinov ma’lumotlari. Admin sinovi: **audit_2**, shu parol.

Rasmlar: scratch/waiter_zones_mobile.png, scratch/waiter_cart_mobile.png, scratch/waiter_transfer_mobile.png va scratch/receipt_readability_preview.png.

Dalillar: scratch/waiter_verified_suite.log, scratch/waiter_frontend_tests.log, scratch/waiter_browser_results.json, scratch/waiter_ws_results.json, scratch/waiter_transfer_results.json va scratch/waiter_admin_regression.json.

Haqiqiy printerdagi qog‘oz sifatini tasdiqlash uchun keyin o‘sha printerdan bitta namuna chek chiqarish kerak. O‘zgarishlarni ishchi kompyuterga yangilash orqali alohida qo‘llash kerak.


## Qo‘shimcha tekshiruv: xodimlar va lokal ko‘rish

Xodimni bo‘shatish lokal API’da bajarilgan, biroq nofaol xodim ham eski ro‘yxatda va yana bo‘shatish tugmasi bilan ko‘ringan. Faol/Nofaol bo‘limlari, tushunarli tasdiqlash oynasi va natija xabari qo‘shildi. Amal xato bo‘lsa oyna yopilmaydi va qayta urinish mumkin. O‘z hisobini bo‘shatish tugmasi ko‘rsatilmaydi.

Bo‘shatish va audit bir tranzaksiyada saqlanadi; audit saqlanmasa o‘zgarish ham bekor qilinadi. Takroriy parallel bo‘shatish bir audit qaydini yaratadi. Xodimning oldingi ochiq/to‘langan hisoblari saqlanadi. Ulangan qurilmaga sessiya bekor qilingani darhol yuboriladi; qayta faollashtirish eski tokenni qayta ishlatishga yo‘l qo‘ymaydi.

Printer sozlamalariga “Yirik shriftni tanlash” tugmasi qo‘shildi: katta shrift, 1 nuqta belgi oralig‘i, keng qator oralig‘i. Keyin “Saqlash” bosiladi. Shu kompyuterdagi asl bazada avval normal/kichik shrift saqlangani faqat o‘qib tekshirildi; asl baza sozlamasi o‘zgartirilmadi. Tavsiya etilgan sozlama faqat sun’iy sinov bazasida qo‘llandi. Haqiqiy qog‘ozdagi tiniqlik namuna bilan tasdiqlanadi.

Yakuniy tekshiruv: **218 backend testi, 23 frontend testi va frontend build o‘tdi.** Brauzerda bo‘shatishni bekor qilish, xato va qayta urinish, faol ro‘yxatdan nofaolga o‘tish, qayta faollashtirish, xodimning darhol chiqishi va shrift sozlamasining saqlanishi tekshirildi.

Dalillar: scratch/staff_full_tests.log, scratch/staff_frontend_tests.log, scratch/staff_browser_results.json, scratch/staff_build_final.log.

Lokal server 8028 portda ishlayapti. Telefon hotspotidan Wi-Fi manzili telefonning o‘zida ERR_ADDRESS_UNREACHABLE berdi; USB modem manzili kompyuterda javob berdi, ammo haqiqiy telefonda kirish tasdiqlanmadi. Foydalanuvchi kompyuterdagi telefon ko‘rinishiga o‘tdi. In-app brauzerda ofitsiant sinov paneli 390×844 ko‘rinishda ochilib qoldirildi. Cloudflare yoqilmadi va onlayn serverga qo‘llanmadi. GitHub’dagi yangi o‘zgarishlar ishchi kompyuterga alohida yangilash orqali olinadi.
