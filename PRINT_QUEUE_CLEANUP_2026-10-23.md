# Sinov cheklarining navbatini tozalash

2026-10-23. Foydalanuvchi rasmdagi 60 ta sinov chekini bekor qilishni so‘radi.

- `backend/restaron.db`: 1-restoranning navbatdagi 60 ta vazifasi `cancelled` qilindi. Yozuvlar o‘chirilmadi. Amal audit jurnaliga yozildi.
- To‘liq baza zaxirasi va 60 ta vazifaning oldingi/keyingi holati saqlandi: `backups/test_print_queue_cleanup/20261023T130649Z-fb4cf3aa.db` va shu nomdagi `.json`.
- Buyurtmalar, taom qatorlari, chek arxivi, qarzlar va avans harakatlarining to‘liq satrlar bo‘yicha SHA256 qiymatlari tranzaksiyadan oldin/keyin bir xil ekanligi tekshirildi.
- Windows printer navbatlaridagi 65 ta `RestAron_Receipt` va 1 ta `Test Page` topshirig‘i `Remove-PrintJob` orqali bekor qilindi. Oldingi ro‘yxat va natija shu zaxira papkasidagi `windows_spool_*.json` fayllarda.
- `X-Q80A` Windows navbati oxirgi topshiriqlar bekor qilingach ro‘yxatda qolmadi. Printer olib tashlash buyrug‘i ishlatilmadi. `POSPrinter POS80` mavjud, navbati 0.
- Yakuniy tekshiruvda dasturdagi `pending/printing/uncertain` vazifalar 0, Windows topshiriqlari 0. SQLite integrity: `ok`.
- Server qayta ishga tushirilmadi, yangi build joylanmadi, printer sozlamalari o‘zgartirilmadi va yangi sinov cheki yuborilmadi. Xizmatdan keyingi yangilash kelishuvi saqlandi.

To‘liq baza tekshiruvi natijasi `scratch/data_health_after_print_cleanup.json`da. Bu fayldagi umumiy `healthy` qiymatini navbatning tozalanganlik belgisi deb talqin qilmaslik kerak; u moliyaviy ma’lumotlarning alohida tekshiruvlarini ham o‘z ichiga oladi. Zaxira va joriy baza tekshiruvlarini solishtirish: `scratch/print_cleanup_validation.json`. Ushbu amalda faqat tasdiqlangan printer navbati o‘zgartirildi.

Ekrandagi banner 10 soniyalik yangilashda yoki uning yangilash tugmasi bosilganda yo‘qolishi kerak. Keyin yaratiladigan yangi buyurtmalar mavjud printer sozlamalari asosida ishlashda davom etadi.
