# RestAron: Windows bilan avtomatik server

2026-10-24. Server manzili: **https://dunyochoyxona.uz**.

## Bir marta o'rnatish

1. `C:\RestAron\RESTARON_AVTO_SERVER.bat` ustiga o'ng tugma bosing va **Run as administrator** ni tanlang. Oddiy ochilsa ham administrator ruxsatini o'zi so'raydi; **Yes / Ha** ni bosing.
2. Oynadagi tekshiruv tugashini kuting. O'rnatishda ishchi server qisqa muddat qayta ishga tushadi. `TAYYOR: lokal server va https://dunyochoyxona.uz javob bermoqda` xabari ikkala ulanish ham tekshirilganini bildiradi.
3. Keyingi safar kompyuterni yoqing. Windows yuklanganidan 30 soniya keyin serverni ishga tushirish boshlanadi; hisobga kirish yoki alohida qora oynani ochib qo'yish kerak emas. Internet tayyor bo'lsa, odatda 1–2 daqiqada foydalanish mumkin. Aniq muddat kompyuter va tarmoq tezligiga bog'liq.

BAT va `tools` papkasidagi yordamchi fayllar shu loyiha ichida qolsin. O'rnatilgandan keyin `C:\RestAron` papkasini ko'chirmang: vazifada mutlaq yo'llar saqlanadi. Mavjud `2_SERVERNI_ORNATISH.bat` ham shu yangi o'rnatuvchini chaqiradi.

## Nima sozlanadi

- Windows Task Scheduler ichida **RestAron Server** vazifasi yaratiladi: SYSTEM, AtStartup, 30 soniya kutish, bir vaqtning o'zida bitta nusxa. Parol yoki avtomatik Windows login talab qilinmaydi.
- Vazifa Python virtual muhiti orqali `server_manager.py serve` ni fonda ishlatadi; frontend tayyor builddan ochiladi. Ishga tushishda pip/npm kutubxonalari qayta o'rnatilmaydi. Eskirgan build o'rnatish vaqtida xavfsiz tayyorlanadi.
- Backend jarayoni to'xtasa nazoratchi uni qayta ochadi; Cloudflare jarayoni uzilsa qayta urinadi. Nazoratchining o'zi qulaganda uning backend va tunnel jarayonlari Windows Job Object orqali yopiladi, vazifa bir daqiqadan keyin qayta urinadi (999 urinishgacha).
- Kompyuter elektr tarmog'ida turganda avtomatik uyqu va hibernatsiya vaqt cheklovlari o'chiriladi. Eski quvvat sozlamalari `backups\autostart\settings_*\power-before.pow` va `power-before.txt` ichida saqlanadi. Ekran, qopqoq va batareya rejimlari o'zgartirilmaydi. Uyqu yoki o'chirishni qo'lda tanlasangiz, sayt ham ishlamaydi.
- Mavjud `tunnel_sozlama.txt` tokeni va doimiy domen ishlatiladi. DNS, token, QR kodlar va stol yozuvlari qayta yaratilmaydi. Token yangi tunnel jarayonining buyruq qatoriga chiqarilmaydi. Routerning internet portlarini ochish talab qilinmaydi: Cloudflare mavjud chiquvchi tunnelidan foydalaniladi.

## Baza va eski jarayonlar

O'rnatuvchi avval kerakli fayllar, kutubxonalar, domen, baza tuzilishi, frontend va 8000-port egasini tekshiradi. Chek chop etilayotgan bo'lsa, tugashini 45 soniyagacha kutadi; tugamasa xizmatni to'xtatmay xato qaytaradi. Mavjud SQLite bazasidan backup API orqali `backups\autostart\*.db` nusxa olinadi va `integrity_check` bilan tekshiriladi. So'ng aynan shu loyiha yo'liga tegishli nazoratchilar va ularning jarayonlari yopiladi. Boshqa Python dasturlari yoki boshqa loyihaning port egasiga tegilmaydi.

Buyurtmalar va printer navbati o'chirilmaydi. Tizim ishlayotgan paytda foydalanuvchilar yangi amal yuborishi mumkinligi sabab, birinchi o'rnatishni buyurtma kiritilmayotgan vaqtda bajaring.

## Holatni tekshirish

CMD oynasida:

```bat
cd /d C:\RestAron
RESTARON_AVTO_SERVER.bat --check
```

Bu rejim sozlamalarni o'zgartirmaydi. Fayllar/baza/build, avtomatik vazifa mavjudligi, lokal va domen `/health` javoblarini tekshiradi. `local_healthy: true` va `domain_healthy: true` bo'lsa ikkala manzil javob beryapti. Domen tayyor bo'lmasa, tayyor deb ko'rsatilmaydi.

Jurnallar: `C:\RestAron\server.log` va `C:\RestAron\uvicorn.log`. Internet kechiksa lokal server ishlashi mumkin; internet qaytganda tunnel qayta ulanadi. Kompyuter o'chiq yoki uyquda bo'lsa saytni shu kompyuter orqali ochib bo'lmaydi.

Avtomatik ishlashni bekor qilish uchun `RESTARON_XIZMATNI_TOXTATISH.bat` ni oching. U faqat shu loyihani to'xtatadi va vazifasini olib tashlaydi; baza va domen sozlamasi saqlanadi. Elektr tarmog'idagi uyqu sozlamalarini orqaga avtomatik o'zgartirmaydi; oldingi qiymatlar yuqoridagi zaxirada bor.

## Tekshiruv chegarasi

Tayyorlash vaqtida o'rnatish bajarilmadi: mavjud ishchi server ishlashda davom etdi. Avtomatik yuklanish **BAT administrator sifatida bajarilgandan keyin** o'rnatiladi. Kompyuter qayta yuklanmadi va SYSTEM ostida haqiqiy startup, printer ulanishi yoki elektr uzilishi sinovi o'tkazilmadi.

16 ta alohida Python sinovi o'tdi: fayl qulfini turli jarayonlarda tekshirish, nazoratchi qulaganda bolalar jarayonlarini yopish, ortiqcha nusxani rad etish, build xatosining chiqish kodi, tokenni buyruq qatoriga chiqarmaslik, UTF-8 BOM, domenni tekshirish, begona jarayon/portni saqlash, printer bandligi, bazaning faqat o'qilishi va zaxirasi. Alohida Windows PowerShell 5.1 tekshiruvida sintaksis va vazifa ta'rifi xotirada tekshirildi; vazifa ro'yxatga olinmadi. Amaldagi BAT `--check` rejimida lokal va domen sog'lomligini tasdiqladi.

Texnik asos: [Microsoft Task Scheduler sozlamalari](https://learn.microsoft.com/en-us/powershell/module/scheduledtasks/new-scheduledtasksettingsset?view=windowsserver2025-ps), [Windows Job Objects](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects), [Cloudflare tunnel parametrlari](https://developers.cloudflare.com/tunnel/reference/run-parameters/).
