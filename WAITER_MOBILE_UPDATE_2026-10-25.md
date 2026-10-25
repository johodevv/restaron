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

Haqiqiy printerdagi qog‘oz sifatini tasdiqlash uchun keyin o‘sha printerdan bitta namuna chek chiqarish kerak. O‘zgarishlar bu safar GitHub’ga push qilinmadi va boshqa kompyuterga qo‘llanmadi.
