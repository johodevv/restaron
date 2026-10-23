# RestAron tuzatish jarayoni

Manba: AUDIT_REPORT_2026-10-23.md va foydalanuvchi yuborgan ro'yxat.

## Bosqichlar

1. Sayt ishga tushishi, takroriy amal va tranzaksiya yaxlitligi — kod tuzatildi, regression o‘tdi.
2. Restoranlar ajratilishi, maxfiy sozlamalar va autentifikatsiya — sinovlar o‘tdi.
3. Narx, vazn, nasiya, avans, smena va checkout — sinovlar o‘tdi; eski tarixda 16 tafovut ochiq.
4. Printer, POS, API va qayta ulanish — dasturiy/mocked sinov o‘tdi; jismoniy printer sinovi kutilmoqda.
5. Dizayn, sozlamalar, vaqt va migratsiya — UI va shadow migratsiya tekshirildi.
6. 100 regression testi, 30 user TCP/WS yuklamasi va hisobot — bajarildi; ishchi relizga ruxsat xulosasi berilmadi.

## Qoidalar

- Testlar faqat yangi ajratilgan bazalarda bajariladi.
- Mavjud ishchi yozuvlarni avtomatik o'chirish/tenglashtirish bajarilmaydi.
- Har bir “tuzatildi” holati sinov dalili bilan belgilanadi.
- Haqiqiy printer, Wi-Fi, PostgreSQL yoki elektr uzilishi sinalmasa ochiq ko'rsatiladi.
- Tasdiqlangan qoida: avans hisobdan ayriladi; KDS admin tomonidan yoqib/o'chiriladi; 30 ofitsiant; kassa USB, ikki oshxona LAN printerlari.

## Jarayon

- A01: LanguageProvider importi qo'shildi, production build o'tdi; brauzer tekshiruvi oldinda.
- A02: buyurtma va idempotency javobi bitta tranzaksiyada. 10 bir xil kalitli add-items: miqdor 2, dublikat yo'q.
- A03: 20 parallel 1 000 so'mlik qarz to'lovi: 20 000 saqlandi; append-only to'lov tarixi qo'shildi.
- A04/A05: delete/checkout 10 sinovida subtotal, taom yig'indisi, kassa mos. Ikki qatorni parallel o'chirish 10 sinovida 0 summa, cancelled.
- A06: menyudan o'chirish soft-delete; ochiq va to'langan buyurtmada tarix saqlandi.
- A07/A08: ommaviy API maxfiy kalitlarni qaytarmaydi; begona buyurtma/settings/menyu o'zgarishi 404. Begona restoran stol ro'yxati bo'sh, QR sizib chiqmaydi.
- A12/A13/A14: printer yo'q bo'lsa 400, yuborilgan miqdor saqlanmaydi; sozlangach retry 1 job. Immediate flag haqiqiy job yaratadi. Yopilgan hisobni yangi oshxona yuborishi 409.
- A15/A16: eski narx saqlanadi; vaznli taom yangi alohida qatorga tushadi.
- A17/A18: naqd to'langan hisobdan noto'g'ri nasiya yaratilmaydi; nasiya o'chirilgan holatda checkout 400.
- A19: 5 000 avans, 11 000 hisob => yangi to'lov 6 000. Alohida avans harakati tarixi; ortiqcha avansni yashirin o'chirish bloklangan. Hisobot/PDF/UI tekshiruvi davom etmoqda.
- A20: ikkita bir vaqtdagi transfer natijasi 200/409, 500 yo'q.
- A21: ikkita parallel Z: 200/409; bo'sh takror smena yaratilmaydi.
- A22: eski table-checkout ham asosiy checkoutdan o'tadi; 1 arxiv cheki yaratildi.
- A23/A24/A25/A26: manfiy xizmat foizi 422; tasdiqlanmagan xodim WSga kirmaydi; QR siz chaqirish 403; noma'lum order_type 422; bo'sh draft aniq belgilanishi shart.

Dalillar: scratch/fix_stage4_probes.json, scratch/fix_stage5_extra.json (faqat yangi test bazalari). Bu ro'yxat barcha ish tugaganini yoki jismoniy printer sinalganini anglatmaydi. UI/KDS, 30 ofitsiant yuklamasi, migratsiya va umumiy regression ishlari davom etmoqda.


## Yakuniy qayta tekshiruv (2026-10-23)

- 100 backend test o‘tdi; 131 API chaqiruvi mos; production build o‘tdi.
- 30 user + 30 WebSocket, 150 amal: 0 xato; 30 to‘langan hisob; subtotal 900 000, cash 990 000; barcha 30 mock print job done.
- TCP p95: create 1.49 s; add 1.71 s; delta 2.50 s; kitchen 2.47 s; checkout 3.09 s. Fon yuklamasi tugatilgan lokal o‘lchov; Wi-Fi/telefonlar sinovi emas.
- WebSocket datetime uzilishi, KDS dozakaz miqdori, eski table-bill otmena yo‘li va POS savati balandligi brauzer/regression tekshiruvida tuzatildi.
- Asl PDF dalili bilan 6/11-ID hisobdagi 4 ta yo‘qolgan qator tiklandi. To‘lov/summalar o‘zgarmadi. Qolgan 16 hisobning asl cheki yo‘qligi foydalanuvchi tomonidan tasdiqlangan.
- Migratsiya yangi shadow nusxada 2 marta; eski ustunlar o‘zgarmadi; integrity ok. 17 eski FK xatosi va 40-stoldagi 3 ochiq hisob dalilsiz o‘zgartirilmadi.
- Admin UI orqali LAN IP saqlash, KDS off/on va test hisobini naqd yopish sinovi o‘tdi; 139-stol AVAILABLE bo‘ldi.
- Haqiqiy printerlar bilan chop etish va tarmoq sinovi bajarilmagan. To‘liq ishga tushirish tasdiqlanmagan.

Batafsil holat: FIX_REPORT_2026-10-23.md. Eski savdo bo‘yicha ro‘yxat: backups/RECONCILIATION_2026-10-23.md.
