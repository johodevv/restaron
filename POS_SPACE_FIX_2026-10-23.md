# Taomlar ro‘yxatiga ko‘proq joy — 2026-10-23

Bu o‘zgarish avvalgi POS maketini almashtiradi. Foydalanuvchi ko‘rsatgan dastavka rejimida ochiq mijoz shakli va qo‘shimcha qatorlar taomlar uchun juda kam joy qoldirgan edi.

## Yakuniy o‘zgarishlar

- Chap panel yuqorisida bitta ixcham qator: buyurtma turi, stol/buyurtma tanlash, mijoz ma’lumotlari, izoh va chek. Stolda stol ko‘chirish ham shu yerda.
- Dastavka/olib ketish mijoz ma’lumotlari alohida oynada. Yangi buyurtmada ism, telefon va manzil kiritiladi; mavjud buyurtmada yozilgan ma’lumot ko‘riladi.
- Dastavka/olib ketishning ochiq buyurtmalari qidiruvli alohida oynada; yangi buyurtma boshlash tugmasi ham shu yerda.
- Jami summa va Oshxonaga/To‘lov tugmalari pastda bitta ixcham qatorda. Ro‘yxat balandlikning qolgan qismini egallaydi, vertikal aylantiriladi.
- Alohida chaqiruv banneri o‘rniga yuqoridagi Chaqiruvlar tugmasi faol chaqiruv soni bilan ajratib ko‘rsatiladi. Chaqiruvlar sahifasi va qabul qilish amali saqlangan.
- Admin/kassir menyusidagi “Oshpaz ekrani” kategoriyasi va shu menyudagi render olib tashlandi. Oshpaz roli uchun alohida ekran va KDS sozlamalari saqlangan; foydalanuvchi admin kategoriyasini olib tashlashni so‘ragan.

## Brauzerda o‘lchangan natija

| Ekran va rejim | Chap panel | Taomlar ro‘yxati | Ro‘yxat ulushi | Pastki hisob |
|---|---:|---:|---:|---:|
| 1280×720, dastavka | 494.4px | 358.8px | 73% | 78.8px |
| 626×668, stolda | 442.4px | 312.4px | 71% | 73.2px |

Bular CSS piksel o‘lchovlari. Har ikki o‘lchamda pastki hisob ekran ichida, taomlar va hisob orasida ustma-ust kelish kuzatilmadi. Sig‘magan taomlar o‘z ro‘yxatida aylantiriladi.

## Tekshiruv

Sinov bazasi: `C:\RestAron\scratch\audit_test_bb0cce9c6e.db`. Haqiqiy savdo bazasida sinov buyurtmasi yaratilmagan.

- 24 taomli dastavka buyurtmasi ochildi; 5 ochiq dastavka buyurtmasi alohida oynadan tanlandi.
- Oxirgi taom miqdori +1 / −1 qilindi. 760,000 + 76,000 = 836,000 qayta tasdiqlandi; +1 holatida 810,000 + 81,000 = 891,000.
- Oxirgi qatorgacha aylantirildi: oxirgi qator pastki chegarasi hisob boshlanishi bilan 1 CSS piksel ichida mos, tugmalar ko‘rinadigan joyda.
- Mijoz oynasi, buyurtma tanlash va yangi buyurtma oqimi tekshirildi. Yangi sinov buyurtmasidagi ism, telefon, manzil va 11,000 jami bazadan qayta o‘qib tasdiqlandi.
- 24 taomli stol buyurtmasi tor ekranda ochildi.
- Sinovda 15 printer ogohlantirishi va 1 chaqiruv bor edi. Yangi tartibda ular taomlar ro‘yxatini siqadigan alohida chaqiruv qatorini yaratmaydi.
- Admin tab DOMida `admin-tab-kitchen` yo‘q: ikkala o‘lchamda tekshirildi.
- Production build muvaffaqiyatli (`scratch/pos_space_v2_build.txt`), diff tekshiruvi o‘tdi. Tezkor summa uchun 4 tekshiruv yana o‘tdi.
- Domen `/assets/index-D2mqgJGj.js` yangi faylini berdi, ommaviy menyu ochildi. Ilova manbasidan JavaScript error kuzatilmadi; brauzer kengaytmasining alohida Failed to fetch xabari ilova xatosi sifatida sanalmadi.

## Joylash va dalillar

Frontend zaxirasi: `C:\RestAron\backups\frontend_before_update_20261023T091957203240Z`.
Server qayta ishga tushirilmadi. Faqat frontend yangilandi; navbatdagi BAT ishga tushirishida manifest ham manbaga mos.

- `scratch/pos_space_v2_verified.png` — dastavka ko‘rinishi.
- `scratch/pos_space_v2_narrow.png` — tor ekrandagi stol buyurtmasi.
- `scratch/pos_space_v2_metrics.json`, `scratch/pos_space_v2_narrow_metrics.json` — haqiqiy DOM o‘lchovlari.

Jismoniy printer sinovi bu maket tekshiruviga kirmaydi; haqiqiy savdo buyurtmasi, to‘lov yoki printer navbatiga sinov amali yuborilmadi.
