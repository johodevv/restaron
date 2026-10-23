> Keyingi tuzatish: [POS_SPACE_FIX_2026-10-23.md](POS_SPACE_FIX_2026-10-23.md). Quyidagi hisobot avvalgi maketga tegishli.

# POS chap buyurtma paneli — 2026-10-23

## Tuzatilgan joylar

- Stol va zal kartochkalari buyurtma ustida doim ochiq turmaydi. “Stol tanlash” oynasida qidiruv, zal filtri, bandlik, vaqt va yuborilmagan taom soni bor.
- Xodimlar sahifasi ekran balandligiga moslashtirildi. Taomlar o‘z ro‘yxatida aylanadi; jami hisob va asosiy tugmalar alohida, pastda qoladi.
- Oshxonaga yuborish va to‘lov ikkita asosiy tugma. Izoh, chek va stol ko‘chirish yuqorida. Olib ketish/dastavka rejimida ham izoh va chek saqlangan.
- Qatorlar panel kengligiga moslashadi. Narx taom nomi ostida, miqdor va jami alohida; tor panelda boshqaruv keyingi satrga tushadi.
- Printer navbati bitta satrga yig‘ildi; barcha printer xatolari va noaniq cheklar “Tafsilotlar” oynasida. POS ichida takroriy admin banneri olib tashlandi. Navbat kechikishi endi dalilsiz “printer ishlamayapti” deb ko‘rsatilmaydi.
- Chaqiruv banneri ixcham. Qolgan chaqiruvlar alohida sahifada mavjud.
- Tor ekranda Taomlar/Savat yuqori boshqaruv qatoriga birlashtirildi.
- Miqdor o‘zgargandagi tezkor hisobda xizmat haqi ham qayta hisoblanadi; server javobi yakuniy qiymat hisoblanadi. Oldingi holatda server javobigacha eski xizmat haqi ko‘rinardi.
- Yangi stol/printer oynalari Escape bilan yopiladi va Tab fokusini oyna ichida ushlab turadi.

## Dalillar va tekshiruvlar

Sinov bazasi: `C:\RestAron\scratch\audit_test_e7b9c059a4.db`. Haqiqiy savdo bazasida sinov buyurtmasi yaratilmagan.

| Tekshiruv | Natija |
|---|---|
| Production build | Muvaffaqiyatli; `scratch/pos_redesign_build_log.txt` |
| Frontendni xavfsiz joylash/startup tekshiruvi | 7 passed, 0.46 s; `scratch/pos_redesign_startup_tests.txt` |
| Tezkor summa hisoblash | 4 holat o‘tdi: miqdor o‘zgarishi, chegirma, 0% va kasrli summa; `scratch/pos_preview_checks.mjs` |
| Uzun buyurtma | 24 qator, 139 stol; oxirgi qatorgacha aylantirildi; ro‘yxat pastki chegarasi hisob boshlanishi bilan teng, ustma-ust kelmaydi |
| Miqdor + / − | Taom, xizmat va jami birga yangilandi. 770,000 + 77,000 = 847,000; qaytarilganda 760,000 + 76,000 = 836,000 |
| Oshxonaga yuborish | 24/24 taom yuborilgan deb belgilandi, 3 ta taqlid printer ishi done; haqiqiy printer chaqirilmadi |
| To‘lov oynasi | To‘g‘ri stol va 836,000 qoldiq bilan ochildi, bekor qilindi; sinov to‘lovi qabul qilinmadi |
| Izoh va olib ketish | Izoh oynasi ochildi/saqlandi; olib ketishda Izoh/Chek tugmalari mavjud |
| Stol qidirish va zal | “10” qidiruvi ishladi; Terrassa filtri 45 ta stol, hammasi shu zalda; Escape oynani yopdi |
| Printer va chaqiruv | 15 printer + 1 chaqiruv bilan tekshirildi; POS da faqat 1 printer banneri; tafsilotlarda barcha printerlar bor; sinov chaqiruvi qabul qilindi |
| Ekran kengliklari | 1280 desktop, 390 iframe telefon, 626 tor ekran ko‘rildi; oxirgi ixcham navigatsiya 626 da qayta tekshirildi |
| Oxirgi tor ekran o‘lchovi | 626×668: taomlar sohasi 188px (oldingi oraliq maketda 120px), hisob yuqori chegarasi 547.2px, pastki chegarasi 664px; sahifa gorizontal chiqib ketmagan |
| Domen orqali ochish | `https://dunyochoyxona.uz` yangi `/assets/index-CuokLBdB.js` bilan ochildi; ommaviy menyu ko‘rindi |
| JavaScript xatolari | Ilova manbasidan error kuzatilmadi. Brauzer kengaytmasining alohida Failed to fetch xabari ilova xatosi sifatida sanalmadi |
| Diff whitespace tekshiruvi | O‘tdi |

## Joylangan versiya

Frontend zaxirasi: `C:\RestAron\backups\frontend_before_update_20261023T085526773496Z`.
Yangi kirish fayli: `/assets/index-CuokLBdB.js`. Build manifest manba fayllariga mos.
Frontend serverni qayta ishga tushirmasdan joylandi; eski hashed fayllar ochiq sessiyalar uchun saqlandi.

Rasmlar: `scratch/pos_redesign_final_verified.png`, `scratch/pos_redesign_verified.png`, `scratch/pos_table_picker_verified.png`.

## Chegara

Bu hisobot buyurtma paneli va unga bog‘liq boshqaruvning ushbu o‘zgarishiga tegishli. Jismoniy printer/tarmoq barqarorligi yoki avvalgi hisobotdagi tarixiy savdo tafovutlari hal qilindi degani emas. Printerlarni qayta yuborish/tasdiqlash amallari haqiqiy navbatda bajarilmadi. Kichik ekranda katta ro‘yxat aylantiriladi; barcha 24 qatorning bir vaqtning o‘zida sig‘ishi va’da qilinmaydi.
