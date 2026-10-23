# Qora ekran: sabab va tuzatish

2026-10-23, Asia/Tashkent.

Brauzerda haqiqiy `https://dunyochoyxona.uz/` ochilib, konsolda quyidagi xato tasdiqlandi:

```text
ReferenceError: LanguageProvider is not defined
at /assets/index-D1qIEjx_.js:26:25802
```

Lokal port 8000 ham aynan shu eski JS faylini ko‘rsatdi. Xizmat ishlab turgan, ammo frontend/dist 2026-10-22 23:52 dagi eski build edi. LanguageProvider importi manba kodda tuzatilgan va scratch buildda sinalgan, ishchi distga hali joylanmagan edi. Oddiy ishga tushirish BATi saytni qayta yig‘masdan shu papkani taqdim etgan.

## Bajarildi

- Tekshirilgan yangi build frontend/dist ichiga joylandi. Oldingi fayllar zaxirasi: `backups/frontend_before_update_20261023T040056690578Z`.
- Eski hashli assetlar saqlandi; allaqachon ochiq tablarning eski chunk so‘rovlari 404 bo‘lib qolmaydi. Yangi index.html assetlar nusxalangach atomar almashtirildi.
- Jonli domen brauzerda qayta ochildi: menyu, kategoriyalar va taomlar ko‘rindi. Yangilashdan keyingi sayt domeniga tegishli konsol errorlari: 0. Brauzer kengaytmasining alohida Failed to fetch xabari sayt xatosi sifatida hisoblanmadi.
- Serverni qayta ishga tushirish bajarilmadi. Bu tuzatish savdo bazasiga yozmaydi.
- server_manager.py ning start va serve yo‘llariga frontend build tekshiruvi qo‘shildi. Manba fingerprinti va assetlar mos bo‘lsa mavjud build ishlatiladi. Eskirgan build yangi vaqtinchalik papkada yig‘iladi; xato bo‘lsa oldingi build fayllari almashtirilmaydi. Node/npm yetishmasa aniq xabar logga yoziladi.
- `tests/test_frontend_build.py`: **7 passed**, 0.51 s. Joriy build, eskirgan manba, yo‘q asset, xatoli npm, muvaffaqiyatli staged build, zaxira va eski assetlarni saqlash tekshirildi.
- server_manager.prepare_frontend(): True. Yangi build manifesti joriy frontend manbasiga mos.

Yangi JS: `/assets/index-BpeS-1IS.js`. Vizual dalil: `scratch/black_screen_fixed_live_20261023.png`.

Foydalanuvchining avval ochilgan qora ekranli tabida **Ctrl+F5** bosish kerak: ishlamay qolgan eski JavaScript o‘zidan-o‘zi qayta ishga tushmaydi.

Bu faqat qora ekran va startup build muammosi bo‘yicha natija. Oldingi umumiy auditdagi eski hisoblar va jismoniy printer sinovi chegaralari saqlanadi.
