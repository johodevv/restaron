# Tortiladigan taom: narx va og‘irlikni tuzatish

2026-10-24. Foydalanuvchi talabiga ko‘ra ofitsiant va kassir tortiladigan taom narxi/og‘irligini oshxonaga yuborilgandan keyin ham oshirishi yoki kamaytirishi mumkin.

- Narx kiritilganda og‘irlik avtomatik hisoblanadi; og‘irlik kiritilganda jami narx hisoblanadi.
- 1 kg narxi 50 000 so‘m bo‘lsa: 65 000 so‘m → 1,3 kg; 1,8 kg → 90 000 so‘m; 1,35 kg → 67 500 so‘m.
- Bir qatorda bir nechta dona bo‘lsa summa jami uchun, og‘irlik har bir donaga tegishli. Hisoblash dona sonini ham hisobga oladi.
- Oxirgi tahrirlangan maydon serverga yuboriladi. Ko‘rsatilgan yaxlitlangan kg qo‘lda kiritilgan aniq summani o‘zgartirib yubormaydi. Eski mijoz ikkala maydonni yuborsa, narx asosiy qiymat hisoblanib kg qayta hisoblanadi.
- Narx/og‘irlik tuzatishlari foydalanuvchi, eski/yangi qiymatlar bilan auditga yoziladi. Dona soni va oshxonaga yuborilgan miqdor o‘zgarmaydi.
- Yuborilgan taomni o‘chirish va dona sonini yuborilgan sondan kamaytirish himoyasi saqlanadi. Yopilgan/to‘langan hisoblar o‘zgartirilmaydi.

## Tekshiruv va joylash

Ajratilgan bazada **171 ta backend testi**, **16 ta frontend testi** va production build o‘tdi. Narx hamda vaznni oshirish/kamaytirish, bir/ikki dona, o‘chirish himoyasi, audit va yopilgan hisoblar tekshirildi.

Brauzerda ofitsiant roli bilan 75 000 → 65 000 so‘m va 1,5 → 1,3 kg; 1,8 kg → 90 000 so‘m; 1,35 kg → 67 500 so‘m saqlandi. 390 px telefonda yon tomonga siljish yo‘q. Bazada oxirgi qator: quantity=1, sent_quantity=1, weight=1.35, total_price=67500; uchala tuzatish ham ofitsiant auditi bilan qayd etilgan.

Ishchi bazaga sinov savdosi yozilmadi. SQLite API orqali zaxira olindi:

`backups/server_restart/weighted_correction_20261024T062423Z.db`

Printer ishlayotgan paytda qayta ishga tushirish kechiktirildi, holati bo‘shagach backend 20224 PID dan 15568 PID ga qayta ishga tushdi. Health tekshiruvi o‘tdi. Stollar/QR va moliyaviy yozuvlar xeshi oldin/keyin bir xil. Lokal va internet sayt yangi frontendni qaytaryapti.

Dalillar: `scratch/fixes_20261023/scratch/weighted_correction_regression.txt`, `scratch/weighted_correction_restart.json`, `scratch/weighted_correction_publish.json`, `scratch/weighted_correction_ui_checks.json`, `scratch/weighted_correction_editor.jpg`.
