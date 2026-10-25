# 61-stol chaqiruvi: tuzatish va tekshiruv

Sana: 2026-10-23. Foydalanuvchi “Qabul qildim” bosilgandan keyin sahifa yangilanganda chaqiruv qaytganini bildirdi.

## Dalil va sabab

Ishchi bazadagi 61-stolning ichki IDsi **601**. **901-buyurtmada** `call_waiter=1`, `call_status=PENDING` qolgan. Shu stol/orderga bog‘langan **13-bildirishnoma** esa `is_read=1` bo‘lgan; yangi o‘qilmagan chaqiruv topilmadi.

Ro‘yxat buyurtma belgisidan chaqiruvni tiklab, `100000 + order.id` ID qaytarardi. Qabul qilish endpointi bu qiymatni `Order.id` deb qidirardi. Eski kod topilmagan buyurtmada ham muvaffaqiyat javobini qaytarib, belgini o‘zgartirmasdi. Frontend kartani vaqtincha olib tashlardi; yangilashda server chaqiruvni yana qaytarardi.

Bu holat oldingi 129 ta testda qamrab olinmagan. Eski endpoint kodi alohida test nusxasiga qo‘yilganda ikkala reproduksiya ham **qayta GET qilganda chaqiruv qolib ketishi** sababli yiqildi.

## Tuzatishlar

- Bildirishnoma IDlari musbat, buyurtmadan tiklangan chaqiruv IDlari manfiy. Yangi formatda 100 mingdan katta IDlar ham aralashmaydi. Bildirishnoma topilmasa, eski klientning `100000 + order.id` formati ham qabul qilinadi.
- Qabul qilish bir tranzaksiyada aynan shu stolning bildirishnomalari va buyurtma belgilarini yakunlaydi. Eski `/orders/{id}/call/complete` endpointi ham ikkala saqlash joyini yangilaydi.
- Yopilgan bildirishnomaga qayta kelgan so‘rov yangi chaqiruvni yopmaydi. Eski buyurtma kartasi o‘rniga yangi bildirishnoma kelgan bo‘lsa, 409 va ro‘yxatni yangilash talabi qaytadi.
- Buyurtmasiz stolda ham takroriy chaqiruv yangi bildirishnoma yaratmaydi. Ro‘yxat tarixiy dublikatlarni bitta stol kartasiga birlashtiradi.
- PostgreSQL uchun stol satri bloklanadi; SQLite yozish so‘rovlari mavjud `BEGIN IMMEDIATE` navbatidan foydalanadi. Sinovlar SQLite’da o‘tkazildi; PostgreSQL bu sessiyada ishlatilmadi.
- Ofitsiant qabul qilgach, ro‘yxat serverdan qayta olinadi. `call_completed` xabari aynan yopilgan bildirishnomalarning doimiy toastlarini olib tashlaydi.

## Ishchi bazadagi 61-stol

Foydalanuvchi bu chaqiruvni qabul qilganini bildirgan. To‘liq SQLite zaxirasi olinib, 901-buyurtmaning **faqat** `call_waiter` va `call_status` maydonlari `0` va `COMPLETED`ga o‘zgartirildi. Satr zaxiradan keyin o‘zgarmagani va shu stolda yangi o‘qilmagan chaqiruv yo‘qligi `BEGIN IMMEDIATE` ichida qayta tekshirildi. Amal `audit_logs`ga yozildi. Summalar, taomlar va to‘lovlar o‘zgarmadi; satr o‘chirilmadi.

- Zaxira: `backups/waiter_call_repair/20261023T124118Z-0546d47e.db`.
- Oldingi/keyingi holat va SHA256: shu nomdagi `.json`.
- Keyingi tekshiruv: integrity `ok`, FK buzilishi 0, hisob summasi nomuvofiqligi 0, takroriy ochiq hisob 0, qarz bog‘lanishi nomuvofiqligi 0.

## Sinovlar

**136 backend/helper test o‘tdi**, 10 ta mavjud dependency/deprecation ogohlantirishi. Shu jumladan 7 ta yangi chaqiruv sinovi:

1. O‘qilgan bildirishnoma + kutayotgan order: qabul qilish va uchta mustaqil yangilash, 8 ta parallel qabul qilish.
2. Xuddi shu holat eski klientning sintetik IDsi bilan.
3. Uchta tarixiy dublikatni birlashtirish va eski endpoint orqali ikkala saqlash joyini yopish; boshqa stol ochiq qolishi.
4. Buyurtmasiz stolga 6 ta parallel chaqirish bitta bildirishnoma yaratishi; qabul qilingach yana chaqirish va eski so‘rovni qayta yuborish.
5. Eski karta yangi chaqiruvni yopmasligi; 10 ta parallel qabul qilishning bir xil yakuni.
6. Begona restoran va topilmagan IDlar mahalliy chaqiruvni o‘zgartirmasligi.
7. Bir xil musbat qiymatli order/notification IDsi, jumladan 100 mingdan katta order bilan aralashmasligi.

Frontenddagi mavjud **3 ta JS test o‘tdi**, production build muvaffaqiyatli yig‘ildi. Oxirgi ekranlar brauzerda tekshirilmadi: Work sozlamasida local browser use o‘chirilgan.

Dalillar:

- `scratch/call_baseline/scratch/call_baseline_tests.txt`: eski kodda ikkita reproduksiya yiqilgan.
- `scratch/fixes_20261023/scratch/full_tests_calls_release.txt`: 136 passed, 157.77 s.
- `scratch/call_fix_frontend_tests.txt`: 3 passed.
- `scratch/call_fix_frontend_build.txt`; build: `scratch/call_fix_build`.
- `scratch/data_health_after_call_repair.json`.

## Qo‘llash holati

**Yangilanish, 2026-10-23 22:27:** foydalanuvchi ruxsati bilan backend joriy kodda qayta ishga tushirildi, frontend mosligi tekshirildi va ishchi kutubxonalar yangilandi. Lokal va internet health 200; chaqiruvlarning 7 ta testi ishchi dependencylar bilan ham o‘tdi. Quyidagi paragraf tuzatish tayyorlangan paytdagi tarixiy holatni bildiradi. Joriy dalillar: `SERVER_RESTART_2026-10-23.md`.

61-stolning qolib ketgan belgisi ishchi bazada tuzatildi. **Yangi backend kodi va frontend build hali ishchi serverga qo‘llanmagan.** 8000-portdagi backend PID 9148 tuzatishlardan oldin, 08:55:52 da ishga tushgan. Backend va frontendni birga qo‘llab, xizmatni qayta ishga tushirish kerak. Bazadagi bitta holatni tuzatish eski koddagi kelajakdagi xatolarni bartaraf etmaydi.

Bu “hech qanday bug qolmagan” degan kafolat emas. U aynan ko‘rsatilgan xatoni takrorlash, tuzatish va yuqoridagi holatlarni avtomatik tekshirish bilan tasdiqlaydi.
