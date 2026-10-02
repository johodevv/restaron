# RestAron — Windows kompyuterga o'rnatish

Bu qo'llanma restoran kompyuterini **doimiy server** qilib sozlaydi:
kompyuter yonganda server o'zi ishga tushadi, fonda uzluksiz ishlaydi,
qulab tushsa o'zi tiklanadi.

---

## 0. Oldindan kerak bo'ladigan dasturlar

Faqat **bir marta** o'rnatiladi:

| Dastur | Havola | Eslatma |
|---|---|---|
| **Python 3.11** | https://www.python.org/downloads/release/python-3119/ | O'rnatishda **"Add Python to PATH"** katagiga belgi qo'ying! |
| **Node.js LTS** | https://nodejs.org/ | Oddiy "Next → Next" bilan o'rnatiladi |

> Agar bu katakka belgi qo'yilmasa, skript Python'ni topa olmaydi va
> xato beradi. Shunda Python'ni o'chirib, qaytadan o'rnating.

---

## 0.1 — Kodni yuklab olish (MUHIM)

Windows internetdan yuklangan `.bat` fayllarni **belgilab qo'yadi** ("Mark of
the Web"). Shuning uchun skriptni ishga tushirganda quyidagi oyna chiqishi
mumkin:

> **Smart App Control blocked a file that may be unsafe**

Bu kodda muammo borligini bildirmaydi — internetdan kelgan HAR QANDAY `.bat`
fayl shunday belgilanadi. Uchta yechimdan birini tanlang.

### Eng toza usul — `git clone` (tavsiya etiladi)

Git orqali olingan fayllarda bu belgi umuman bo'lmaydi:

```
git clone -b claude/sharp-cerf-koy3wf https://github.com/johodevv/restaron C:\RestAron
```

Git yo'q bo'lsa: https://git-scm.com/download/win
Keyinchalik yangilanish olish ham oson bo'ladi — `git pull` yetarli.

### ZIP yuklasangiz — ochishdan OLDIN blokdan chiqaring

1. Yuklangan **ZIP faylni** o'ng tugma → **Properties**
2. Pastdagi **"Unblock"** katagiga belgi qo'ying → **OK**
3. **Shundan keyin** ZIP'ni oching

Shunda ichidagi barcha fayl toza bo'ladi.

### Allaqachon ochib bo'lgan bo'lsangiz

PowerShell'da bitta buyruq (papka yo'lini o'zingiznikiga almashtiring):

```powershell
Get-ChildItem -Path "C:\RestAron" -Recurse | Unblock-File
```

> **Smart App Control'ni O'CHIRMANG.** U bir marta o'chirilsa, Windows'ni
> qayta o'rnatmaguningizcha qayta yoqib bo'lmaydi. Yuqoridagi usullar
> xavfsizlikni pasaytirmasdan muammoni hal qiladi.

---

## 1-QADAM — Dasturni tayyorlash

Loyiha papkasida:

**`1_BIRINCHI_ORNATISH.bat`** — ikki marta bosing (oddiy, administrator kerak emas).

U quyidagilarni bajaradi:
- Python va Node.js borligini tekshiradi
- Backend kutubxonalarini o'rnatadi (`backend\.venv` ichiga)
- Saytni yig'adi (`frontend\dist`)

Taxminan **3–8 daqiqa** vaqt oladi. Oxirida *"1-QADAM TUGADI"* yozuvi chiqadi.

---

## 2-QADAM — Serverni doimiy ishlaydigan qilish

**`2_SERVERNI_ORNATISH.bat`** — **o'ng tugma** bilan bosing →
**"Run as administrator"** (Administrator nomidan ishga tushirish).

U quyidagilarni bajaradi:
- Kompyuter **uyquga ketmasligini** sozlaydi (noutbuk qopqog'i yopilsa ham ishlaydi)
- Firewall'da **8000-port**ni ochadi (ofitsiant telefonlari uchun)
- Kompyuter yonganda server **avtomatik** ishga tushishini sozlaydi
  (tizimga kirmasangiz ham)
- Serverni darhol ishga tushiradi

Oxirida kirish manzillari ko'rsatiladi.

---

## Kirish

| Kim | Manzil |
|---|---|
| **Kassa / Admin** (shu kompyuterda) | http://localhost:8000 |
| **Ofitsiant telefoni** (bir xil Wi-Fi) | `http://<kompyuter-IP>:8000` |

**Admin login:** `maqsad`
**Admin parol:** `01020307m`

Kompyuter IP manzilini ko'rish: `2_SERVERNI_ORNATISH.bat` oxirida yoziladi,
yoki buyruq satrida `ipconfig`.

---

## Printerlarni ulash

Admin panel → **Sozlamalar** bo'limida har bir printer alohida ko'rsatiladi:

| Printer | Qiymat | Ulanish |
|---|---|---|
| 1 — Kassa (mijoz cheki) | `X-Q80A` | **USB** kabel |
| 2 — 1-Oshxona | `192.168.1.201` | **LAN** (RJ-45) |
| 3 — 2-Oshxona | `192.168.1.202` | **LAN** (RJ-45) |

- **Printer nomi** yozilsa → USB orqali chiqaradi
- **IP manzil** yozilsa → tarmoq orqali (TCP 9100) chiqaradi

> Oshxona printerlarining IP manzilini printerning o'zidan sozlaysiz,
> va routerda o'sha IP ni **statik** (DHCP reservation) qilib qo'ying —
> aks holda ertaga IP o'zgarib, chek chiqmay qoladi.

Qog'oz eni: **80mm** (Sozlamalar bo'limida o'zgartirish mumkin).

---

## Internetdan kirish

**Alohida hech narsa qilish shart emas.** `2_SERVERNI_ORNATISH.bat` o'rnatgan
xizmat ikkala rejimda ham ishlaydi:

| Rejim | Manzil | Qachon |
|---|---|---|
| Lokal Wi-Fi | `http://<IP>:8000` | Darhol |
| Internet (4G, uzoqdan) | `https://...trycloudflare.com` | 1-2 daqiqada |

Server ishga tushgach Cloudflare Tunnel avtomatik ko'tariladi va internet
manzili **`SERVER_ONLINE_URL.txt`** fayliga yoziladi.

Manzilni ko'rish: **`RESTARON_URL_KOR.bat`**

QR kodlar shu manzilga avtomatik moslashadi — ya'ni mijoz stoldagi QR ni
skanerlasa, internetdan ham, Wi-Fi'dan ham menyu ochiladi.

Tunnel uzilib qolsa, tizim o'zi qayta ulanadi va yangi manzilni faylga
yozadi. Internet bo'lmasa ham lokal Wi-Fi rejimi ishlashda davom etadi.

> Bepul tunnel manzili har safar qayta ishga tushganda **o'zgaradi**.
> Stollardagi QR kodlar doimiy bo'lishi kerak bo'lsa, o'z domeningiz bilan
> Cloudflare named tunnel sozlang yoki QR'ni LAN manziliga qo'ying.

---

## Kundalik ishlatish

Server **fonda doimiy** ishlaydi — hech narsa qilish shart emas.
Kompyuter o'chib yonsa, o'zi qayta ishga tushadi.

| Amal | Fayl |
|---|---|
| Serverni to'xtatish | `RESTARON_XIZMATNI_TOXTATISH.bat` (administrator) |
| Qayta yoqish | `2_SERVERNI_ORNATISH.bat` (administrator) |
| Jurnal (xatolarni ko'rish) | `server.log` |

---

## Ma'lumotlarni tozalash (noldan boshlash)

Ikkita skript bor. Ikkisi ham **o'chirishdan oldin avtomatik zaxira nusxa**
oladi: `backend\zaxira\restaron_<sana>.db`.

### Faqat buyurtmalarni tozalash (tavsiya etiladi)

**`RESTARON_TOZALASH_BUYURTMALAR.bat`** — o'ng tugma → *Run as administrator*.

| O'chiriladi | Saqlanadi |
|---|---|
| buyurtmalar, cheklar arxivi | menyu (taomlar, kategoriyalar) |
| qarzlar (nasiya) | stollar va ularning **QR kodlari** |
| smena hisobotlari (X/Z) | xodimlar va parollar |
| bildirishnomalar, izohlar | printer va restoran sozlamalari |

Barcha stollar "bo'sh" holatiga o'tadi, buyurtma raqamlari yana
`#R1-0001` dan boshlanadi. **Sinov uchun kiritilgan buyurtmalarni
tozalab, haqiqiy ishni boshlash uchun shu skriptni ishlating.**

### Hammasini tozalash

**`RESTARON_TOZALASH_HAMMASI.bat`** — o'ng tugma → *Run as administrator*.
Tasdiq uchun `TOZALA` deb yozish kerak.

Butun baza o'chiriladi va noldan yaratiladi: menyu, stollar, xodimlar,
sozlamalar — hammasi. Keyin admin logini yana `maqsad` / `01020307m`.

> **DIQQAT:** stollarning **QR kodlari yangidan yaratiladi**, ya'ni
> stollarda turgan eski chop etilgan QR kodlar ishlamay qoladi —
> ularni qayta chop etishingiz kerak. Menyuni ham qaytadan kiritasiz.
> Shuning uchun ko'pincha yuqoridagi "faqat buyurtmalarni tozalash"
> yetarli bo'ladi.

Ikkala skript ham serverni o'zi to'xtatadi, tozalaydi va qayta ishga
tushiradi — qo'lda hech narsa qilish shart emas.

Xato bilan tozalab qo'ysangiz: `backend\zaxira\` ichidagi kerakli faylni
`backend\restaron.db` nomi bilan qaytarib qo'ying (avval serverni
`RESTARON_XIZMATNI_TOXTATISH.bat` bilan to'xtatib oling).

---

## Ma'lumotlar va zaxira nusxa

Barcha ma'lumot bitta faylda: **`backend\restaron.db`**
(menyu, stollar, buyurtmalar, cheklar arxivi, qarzlar, xodimlar).

**Muntazam nusxa oling** — masalan har kuni kechqurun shu faylni
fleshka yoki bulutga ko'chiring. Serverni to'xtatib nusxa olish eng xavfsiz.

Dasturni yangilaganda bu fayl o'chmaydi.

---

## Muammo bo'lsa

| Belgi | Nima qilish |
|---|---|
| Sayt ochilmayapti | `server.log` ni oching; `2_SERVERNI_ORNATISH.bat` ni qayta ishga tushiring |
| Telefon ulanmayapti | Bir xil Wi-Fi'da ekanini va `open_firewall.bat` bajarilganini tekshiring |
| Chek chiqmayapti | Admin → Sozlamalar'da printer nomi/IP to'g'riligini tekshiring |
| Chek juda uzun/qisqa | Admin → Sozlamalar → qog'oz eni (58/80mm) |
| IP o'zgarib ketdi | Routerda kompyuterga statik IP (DHCP reservation) bering |
