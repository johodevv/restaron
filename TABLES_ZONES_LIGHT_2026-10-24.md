# Stollar: och rangli dizayn va zonalar paneli

2026-10-24. Foydalanuvchi qora rangni almashtirish va zonalarni chap tomonda doim ko‘rsatishni so‘radi.

- Fon och krem, kartalar oq, asosiy amallar sokin yashil. Holatlarning yengil belgilari va matni saqlandi.
- Zona tanlash ro‘yxati chap panelga ko‘chirildi. Har zonada jami va bo‘sh stollar soni ko‘rsatiladi. Tanlangan zona aniq ajratiladi.
- Zona tanlanganda faqat shu zonadagi stollar chiqadi. Oldingi qidiruv/holat filtri tozalanadi. Zona almashtirish uchun qo‘shimcha API so‘rovi kerak emas.
- Tor ekranda zonalar yuqoridagi gorizontal panelga o‘tadi. Qidiruv va holat filtri tanlangan zona doirasida ishlaydi.
- «Band qilish» va «Bron qilish» kartada ochiq turadi. Bron formasi va stol/QR/sozlamalar oynalari ham och rangga moslandi.
- Takroriy zona sarlavhasi va stol soni yozuvi qisqartirildi. Bron maydonlarida belgi va matn orasidagi masofa tuzatildi.

## Tekshiruv

9 ta mavjud frontend testi va yakuniy Vite build o‘tdi. Ajratilgan bazadagi 139 ta sun’iy stol bilan brauzerda:

- Terrassa tanlanganda 45 ta stol va faqat Terrassa guruhi chiqdi.
- 61 qidirilganda aynan shu stol chiqdi. Boshqa zonaga o‘tilganda qidiruv/holat filtri tozalandi.
- Bo‘sh stollar filtri 35 ta stolni ko‘rsatdi.
- 1-stol kartadan band qilinganda holat va zonadagi bo‘sh soni yangilandi.
- 4-stolning bron oynasi to‘g‘ri ochildi; och maydonlar va 36 px chap masofa tekshirildi.
- Ochiq hisobli 2-stolni bo‘shatish bloklangani tasdiqlandi.
- 390 va 768 px ekranlarda hujjat eni ekrandan oshmadi. Asosiy tugmalar kamida 44 px, mobil zona tugmalari kamida 58 px bo‘ldi.
- Ilova manbalaridan konsol xatosi qayd etilmadi. Boshqa bo‘limga o‘tilganda stollar uchun maxsus ranglar bekor bo‘ladi.

## Joylash

Oldingi frontend zaxirasi: `backups/frontend_before_update_20261024T042151902945Z`.

Yangi build ishchi saytga joylandi. Lokal va ommaviy manzil HTTP 200 qaytardi; kirish fayllari hamda AdminDashboard JS/CSS tarkibi yangi build bilan mos. Backend qayta ishga tushirilmadi.

Haqiqiy bazadagi 41 ta stolning QR tokenlari va rasm manzillari joylashdan oldin/keyin bir xil. Ishchi bazada sinov bronlari/buyurtmalari yaratilmagan, printerga chek yuborilmagan.

Dalillar: `scratch/tables_zones_light_build.txt`, `scratch/tables_zones_light_publish.json`, `scratch/tables_zones_light_desktop.jpg`, `scratch/tables_zones_light_available.jpg`, `scratch/tables_zones_light_mobile.jpg`. Rasmlar sun’iy sinov ma’lumotlari bilan olingan.
