# RestAron: GitHub orqali yangilash

2026-10-25. Asosiy fayl: **RESTARON_YANGILASH.bat**.

## Bir marta yangi paketni joylashtirish

`RESTARON_YANGILASH_PAKETI.zip` ichidagilarni choyxonadagi loyiha papkasiga oching. BAT mavjud `RESTARON_YANGILASH.bat` o'rniga, yordamchi fayllar esa shu loyihaning `tools` papkasiga tushsin. Bu paket savdo bazasini o'z ichiga olmaydi.

Yangi kompyuterda **Git for Windows**, Node.js/npm va ishlaydigan **Python 3.12** virtual muhiti bo'lishi kerak. Git yo'q bo'lsa, [rasmiy Git sahifasidan](https://git-scm.com/downloads/win) o'rnating va oynani qayta oching. Loyiha ichida `.git` metama'lumotlari va joriy branch uchun upstream sozlamasi bo'lishi kerak. Private repozitoriy uchun GitHub kirishi shu Windows hisobida ishlashi kerak. `.git` yo'q bo'lsa, yangilagich mavjud bazani xavfga qo'yib boshqa branchni taxmin qilmaydi; tushunarli xato bilan to'xtaydi.

BAT va yordamchi fayllarni dasturchi kompyuteridan GitHub'ga ham commit/push qiling. Keyingi kod yangilanishlari aynan sozlangan upstream branchdan olinadi; yangilagich branch nomini oynada ko'rsatadi. Boshqa branchga qilingan push bu serverga avtomatik o'tmaydi.

## Keyingi yangilashlar

1. Dasturchi kompyuterida o'zgarishlarni tekshirib, kerakli branchga commit va push qiling.
2. Choyxonada buyurtma kiritish tugagach, `RESTARON_YANGILASH.bat` ni administrator sifatida oching. Oddiy ochilsa ham UAC ruxsatini o'zi so'raydi.
3. `YANGILASH TUGADI` va domen javob bergani haqidagi xabarni kuting. Brauzerda `Ctrl+F5` bilan sahifani yangilang.

Serverni alohida to'xtatish BAT'ini ochish shart emas. Yangilagich xizmat vazifasini olib tashlamasdan vaqtincha o'chiradi, faqat shu loyiha jarayonlarini to'xtatadi va oxirida avtomatik vazifani qayta yoqadi. Printer chek chiqarayotgan bo'lsa tugashini kutadi. 45 soniyada tugamasa kodni o'zgartirmay to'xtaydi.

## Mahalliy o'zgarishlar va baza

Mahalliy o'zgargan, staged yoki Git'da hali kuzatilmagan kod fayllari yangilashga to'siq bo'lmaydi. Avval ularning nusxasi va Git index holati `backups/updates/<sana>/` ichiga olinadi. GitHub'dagi kod ustun hisoblanadi. GitHub versiyasida yo'q mahalliy qo'shimcha kod modullari zaxiralangach olib tashlanadi. Yangilagich `git reset --hard` va `git clean` ishlatmaydi.

Quyidagilar GitHub versiyasidagi fayllar bilan almashtirilmaydi: ishchi SQLite bazasi, WAL/SHM fayllari, `.env` sozlamalari, Cloudflare tokeni va `cloudflared.exe`, uploads/QR rasmlari, chek arxivi, zaxiralar, `.venv` va `.venv_eski*` papkalari. Bazadan va mahalliy `.env` dan o'qilgan alohida uploads/PDF/baza yo'llari ham himoyalanadi. Python muhitidagi kutubxonalar esa yangi kod talablariga muvofiq yangilanadi; `.venv` ni qo'lda qayta nomlash shart emas.

## Xatoda nima bo'ladi

- Internetdan kod va Python kutubxonalari avval alohida papkaga olinadi. Frontend shu yerda yig'iladi. Bu bosqichlarda xato bo'lsa asosiy server to'xtatilmaydi.
- Yangi backend ishchi bazaning **nusxasida** ishga tushiriladi. Sinovda printer worker o'chiriladi. Keyin oldingi backend ham shu migratsiyadan o'tgan nusxada tekshiriladi.
- Hammasi tayyor bo'lgach mahalliy kod, Git index, Python muhiti, frontend va SQLite bazasidan zaxira olinadi. Server qisqa muddatga to'xtatiladi. Tayyor kod va oldindan yuklangan kutubxonalar joylanadi.
- Kutubxona o'rnatish yoki yangi backendni ishga tushirish xatosida oldingi kod, Git index, Python muhiti va frontendni qaytarishga uriniladi, so'ng server qayta ochiladi. Natija health tekshiruvi bilan tasdiqlanadi; tiklanish tasdiqlanmasa bu alohida aytiladi.
- **Ishchi baza avtomatik eski nusxaga qaytarilmaydi.** Yangi savdo yozuvlari ustidan eski ma'lumot yozib yuborilmasligi uchun zaxira qo'lda tekshirish uchun saqlanadi. Koddagi sxema migratsiyalari bazani yangilashi mumkin; murakkab migratsiya va elektr uzilishida qo'lda tiklash zarur bo'lishi mumkin.
- Mahalliy server sog'lom, lekin internet/domen tekshiruvi o'tmasa natija kodi **2** bo'ladi. Bunda tayyor kod orqaga qaytarilmaydi; Cloudflare/internet ulanishini tekshiring. Boshqa xatolar kodi **1**.

Eski GitHub versiyasida avvalgi yangilash BAT'i bo'lsa, yangi o'rnatilgan yangilagich unga qaytarib yuborilmaydi. GitHub'ga yangi yangilagichning barcha fayllari joylangach, yangilagichning o'zi ham keyingi relizlar bilan yangilanadi.

## Faqat tekshirish

```bat
RESTARON_YANGILASH.bat --check
```

Bu rejim Git/Python/Node mavjudligi, loyiha ildizi, branch va upstream sozlamasini tekshiradi. Internetdan kod olmaydi, savdo bazasini o'zgartirmaydi va serverni qayta ishga tushirmaydi. Bu tekshiruv muvaffaqiyatli bo'lishi GitHub kirishi yoki yangi kodning ishga tushishini o'zi tasdiqlamaydi; ular haqiqiy yangilashning keyingi bosqichlarida sinaladi.

Jurnallar: `backups/updates/<sana>/update.log`. Alohida sinov jurnallari: `scratch/updates/<sana>/smoke.log` va `rollback-smoke.log`. Zaxiralar avtomatik o'chirilmaydi; disk hajmini kuzatib boring.

## Ushbu tayyorlashda tekshirilganlar

Sinovlar vaqtinchalik Git repozitoriylari, bazalar va soxta xizmat boshqaruvi bilan o'tkazildi. Mahalliy/staged/untracked kod, noto'g'ri upstream, himoyalangan ma'lumotlar, eski BAT'ga qaytmaslik, dependency xatosi, yangi backend health xatosi, rollback vaqtida yangi savdoni saqlash, printer bandligi va Windows vazifa ta'rifi tekshirildi. Haqiqiy FastAPI ishchi bazaning alohida nusxasida, printer worker o'chirilgan holda ishga tushirildi. Joriy loyihada BAT `--check` rejimi bajarildi. Ishchi serverga haqiqiy yangilash qo'llanilmadi va boshqa kompyuterga masofadan kirilmadi.

Asos: [Git reset rejimlari](https://git-scm.com/docs/git-reset), [pip download va offline o'rnatish](https://pip.pypa.io/en/stable/cli/pip_download/).
