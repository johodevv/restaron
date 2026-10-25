# Oshxonaga yuborilgan taomlarni himoyalash

Keyingi talab bo‘yicha tortiladigan taomning narxi va kg sini ofitsiant ham tuzatishi mumkin. Joriy qoida va tekshiruv: [Tortiladigan taom tuzatishlari](WEIGHTED_CORRECTIONS_2026-10-24.md). Quyidagi narxni kamaytirish cheklovi avvalgi holatni qayd etadi; o‘chirish/dona soni himoyasi saqlangan.

2026-10-24. Ishchi serverga qo‘llandi.

- Ofitsiant va kassir oshxonaga yuborilgan taomni o‘chira olmaydi. Miqdorni yuborilgan sondan pastga tushirish ham HTTP 403 bilan rad etiladi.
- Butun buyurtmani bekor qilish va tortiladigan taom narxini/og‘irligini kamaytirish orqali summani tushirish yo‘llari ham himoyalandi.
- Oshxonaga yuborilmagan qo‘shimchalar tahrirlanadi. Tortiladigan taomning hali kiritilmagan narxini birinchi marta kiritish ishlaydi.
- Admin o‘chirish/kamaytirish imkoniyatini saqlaydi. Texnik developer vakolati ham saqlangan. Kassir mustaqil bekor qila olmaydi.
- Admin o‘zgarishlari auditda qayd etiladi; yuborilgan miqdor bekor qilinganda oshxona bekor qilish cheki navbatiga tushadi.
- Eski yozuvlardagi yuborilganlik belgisi, vaqt yoki tayyorlangan miqdor ham tekshiriladi; faqat bitta bayroqqa ishonilmaydi.
- Ofitsiant ekranida «−» va o‘chirish tugmalari bloklanadi, «O‘chirish: faqat admin» izohi ko‘rsatiladi. Hisob oynasidagi qaytarish tugmasi ham faqat adminga ochiq.

## Tekshiruv

Ajratilgan bazada 27 ta yangi test: to‘g‘ridan-to‘g‘ri DELETE, quantity, delta, butun buyurtmani bekor qilish, narx/og‘irlik orqali kamaytirish, eski belgilar, admin auditi, yuborilmagan qo‘shimchalar va parallel yuborish/o‘chirish.

To‘liq backend sinovi: **157 passed**. Frontend: **12 passed**. Production build o‘tdi. Brauzerda haqiqiy ofitsiant roli bilan yuborilgan qatordagi tugmalar o‘chiq, yangi qatordagilari faol ekanligi tasdiqlandi. Sinovlar sun’iy bazada; haqiqiy printerga sinov chek yuborilmadi.

## Joylash

SQLite backup API bilan zaxira olindi, nusxaning integrity_check natijasi `ok`:

`backups/server_restart/sent_item_policy_20261024T061523Z.db`

Ishchi backend 14656 PID dan yangi 20224 PID ga qayta ko‘tarildi; health tekshiruvi o‘tdi. Qayta ishga tushirish paytida print holatidagi chek bo‘lmagan.

Stollar (41), buyurtmalar (4), buyurtma qatorlari (2) va ularning moliyaviy/QR maydonlari oldin-keyin xesh bilan solishtirildi: o‘zgarmagan. Lokal va internet sayt HTTP 200; yangi frontend fayllari joylangan build bilan mos.

Dalillar: `scratch/fixes_20261023/scratch/sent_item_full_regression.txt`, `scratch/sent_item_policy_restart.json`, `scratch/sent_item_policy_publish.json`, `scratch/sent_item_waiter_protection.jpg`.
