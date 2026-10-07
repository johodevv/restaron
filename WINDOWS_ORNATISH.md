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

## Skriptlarni ishga tushirish haqida

Eng oson usul — **Explorer'da faylni ikki marta bosish** (administrator
kerak bo'lsa: o'ng tugma → *Run as administrator*).

Agar **PowerShell** oynasidan ishga tushirsangiz, fayl nomini `.\` bilan
boshlash shart:

```powershell
cd C:\RestAron
.\1_BIRINCHI_ORNATISH.bat
```

Shunchaki `1_BIRINCHI_ORNATISH.bat` deb yozsangiz PowerShell
*"is not recognized as the name of a cmdlet"* xatosini beradi — bu kodda
muammo emas, PowerShell joriy papkadagi fayllarni xavfsizlik uchun
shunday yozishni talab qiladi. (`cmd.exe` da `.\` kerak emas.)

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
- Kompyuter yonganda **sayt brauzerda o'zi ochilishini** sozlaydi
- Serverni darhol ishga tushiradi va **saytni brauzerda ochadi**

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
| 4 — **BAR** (suv, choy, ichimlik) | `192.168.1.203` yoki bo'sh | **LAN** yoki USB |

Har bir taom kartasida **stansiya** tanlanadi — begunok shu printerdan chiqadi:

| Stansiya | Qayerdan chiqadi |
|---|---|
| 🫕 1-Oshxona | 2-printer (qozon taomlari) |
| 🐟 2-Oshxona | 3-printer (baliq, somsa, mangal) |
| 🥤 Bar | 4-printer; bo'sh bo'lsa **kassa printeri** |
| 🧾 **Kassa** | **kassadagi USB printer** (suv, non, desert) |
| 📢 Har 2 oshxona | 2- va 3-printer |

> **"Kassa" stansiyasi:** suv, non kabi oshxona tayyorlamaydigan narsalar
> uchun. Begunok kassadagi (USB) printerdan chiqadi, oshxonaga
> yuborilmaydi — kassir mahsulotni berib yuboradi.

- **Printer nomi** yozilsa → USB orqali chiqaradi
- **IP manzil** yozilsa → tarmoq orqali (TCP 9100) chiqaradi

> Oshxona printerlarining IP manzilini printerning o'zidan sozlaysiz,
> va routerda o'sha IP ni **statik** (DHCP reservation) qilib qo'ying —
> aks holda ertaga IP o'zgarib, chek chiqmay qoladi.

Qog'oz eni: **80mm** (Sozlamalar bo'limida o'zgartirish mumkin).

### Chek juda kichik chiqsa (keksa odamlar o'qiy olmasa)

Admin → **Sozlamalar** → **🔍 Chek shrifti o'lchami**:

| Variant | Nima bo'ladi |
|---|---|
| Oddiy | standart o'lcham |
| **Katta** ✓ | harflar **2 barobar balandroq**, chek kengligi o'zgarmaydi — **tavsiya etiladi** |
| Juda katta | harflar bo'yiga ham, eniga ham 2 barobar; qatorga 24 belgi sig'adi, chek uzunroq chiqadi |

"Katta" ko'pchilikka yetarli: o'qish osonlashadi, lekin chek tartibi
buzilmaydi va qog'oz ortiqcha sarflanmaydi.

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

> Bepul tunnel manzili har safar qayta ishga tushganda **o'zgaradi** —
> ya'ni stollardagi chop etilgan QR kodlar buziladi. Buni hal qilish
> uchun pastdagi bo'limga qarang.

---

## Internet manzilini doimiy qilish

Bepul `...trycloudflare.com` manzili server har qayta yonganda o'zgaradi.
Stollardagi QR kodlar doimiy bo'lishi uchun ikki yo'l bor.

### Yo'l 1 — QR kodlarni lokal manzilga bog'lash (BEPUL, eng oson)

Mijozlar restoran Wi-Fi'ida bo'lsa, bu yetarli:

1. Routerda kompyuterga **statik IP** bering (DHCP reservation) —
   masalan `192.168.1.50`. Shunda IP hech qachon o'zgarmaydi.
2. Admin panel → **Stollar & QR** → **"Manzilni o'zgartirish"** →
   `http://192.168.1.50:8000`
3. QR kodlarni chop eting — ular **doimiy** bo'ladi.

Kamchiligi: QR faqat restoran Wi-Fi'ida ishlaydi (4G da ochilmaydi).
Ko'pchilik restoran uchun shu yetarli — mijoz baribir restoranda o'tiradi.

### Yo'l 2 — O'z domeningiz bilan doimiy internet manzili

Manzil hamma joyda ishlaydi va hech qachon o'zgarmaydi:
`https://restoran.sizningdomen.uz`

**Kerak bo'ladi:**

| Nima | Narxi |
|---|---|
| Cloudflare hisobi | **bepul** |
| O'z domeningiz (Cloudflare'ga qo'shilgan) | ~10–15 $ / yil |
| Cloudflare Tunnel | **bepul** |

**Qadamlar:**

1. [dash.cloudflare.com](https://dash.cloudflare.com) da hisob oching va
   domeningizni qo'shing.
2. **Zero Trust → Networks → Tunnels → Create a tunnel**
   - Connector: **Cloudflared**
   - Chiqqan **TOKEN** ni nusxalang
3. O'sha tunnelda **Public hostname** qo'shing:
   - Subdomain: `restoran` , Domain: `sizningdomen.uz`
   - Service: **HTTP** → `localhost:8000`
4. Kompyuterda **`RESTARON_DOIMIY_MANZIL.bat`** ni ishga tushiring,
   TOKEN va manzilni kiriting.
5. Admin panelga kirib **QR kodlarni qayta chop eting** — endi ular
   hech qachon buzilmaydi.

Orqaga qaytish uchun `tunnel_sozlama.txt` faylini o'chiring —
yana bepul, o'zgaruvchan manzilga qaytadi.

> **Nega port forwarding emas?** O'zbekistondagi ko'p provayderlar
> CGNAT ishlatadi — bunda routerda port ochish ishlamaydi. Cloudflare
> Tunnel esa har qanday tarmoqda ishlaydi, chunki ulanish ichkaridan
> tashqariga qiladi.

---

## Sayt o'zi ochilishi

Noutbukni yoqqaningizda hech narsa bosish shart emas:

1. Windows yuklanadi → **server o'zi ishga tushadi** (tizimga kirmasangiz ham)
2. Siz tizimga kirasiz → kichik oyna chiqadi: *"RestAron server kutilmoqda..."*
3. Server javob berishi bilan **brauzer o'zi ochiladi**: `http://localhost:8000`

Oyna serverni 3 daqiqagacha kutadi (kompyuter sekin yuklansa ham yetadi).
Server ko'tarilmasa, oyna buni aytadi va `server.log` ga yo'naltiradi.

`2_SERVERNI_ORNATISH.bat` ni bosganingizda ham sayt shu zahoti brauzerda
ochiladi.

> **Internet manzili** (`...trycloudflare.com`) alohida — u 1-2 daqiqada
> tayyor bo'ladi. Ko'rish uchun `RESTARON_URL_KOR.bat`, yoki admin panel
> yuqorisidagi yashil chiziqdan nusxalab oling. Brauzer esa doim
> `localhost` orqali ochiladi — u internetsiz ham ishlaydi va hech qachon
> o'zgarmaydi.

Saytning o'zi ochilishini **o'chirish** uchun: Windows qidiruviga
`shell:startup` yozing va ochilgan papkadan **"RestAron saytni ochish.cmd"**
faylini o'chiring. (`RESTARON_XIZMATNI_TOXTATISH.bat` ham uni olib tashlaydi.)

---

## Yangilash (yangi versiya olish)

**`RESTARON_YANGILASH.bat`** — o'ng tugma → *Run as administrator*.

Bitta bosishda hammasini qiladi:
1. Yangi kodni yuklaydi (`git pull`)
2. Kutubxonalarni tekshiradi
3. Saytni qayta yig'adi
4. Serverni qayta ishga tushiradi va saytni ochadi

**Ma'lumotlaringiz o'chmaydi** — menyu, stollar, QR kodlar, xodimlar,
buyurtmalar va cheklar arxivi joyida qoladi.

> Yangilangach brauzerda **Ctrl + F5** bosing — eski versiya keshda
> qolib ketmasligi uchun.

---

## Kundalik ishlatish

Server **fonda doimiy** ishlaydi — hech narsa qilish shart emas.
Kompyuter o'chib yonsa, o'zi qayta ishga tushadi va sayt o'zi ochiladi.

| Amal | Fayl |
|---|---|
| Serverni to'xtatish | `RESTARON_XIZMATNI_TOXTATISH.bat` (administrator) |
| Doimiy internet manzili | `RESTARON_DOIMIY_MANZIL.bat` |
| Namuna menyuni tozalash | `RESTARON_MENYUNI_TOZALASH.bat` (administrator) |
| Yangi versiyaga yangilash | `RESTARON_YANGILASH.bat` (administrator) |
| Boshqa kompyuterga ko'chirish | `RESTARON_NUSXA_OLISH.bat` |
| Qayta yoqish | `2_SERVERNI_ORNATISH.bat` (administrator) |
| Jurnal (xatolarni ko'rish) | `server.log` |

---

## Tortiladigan taomlar (baliq, go'sht)

Baliq 1 kg deb buyurtma qilinadi, lekin aniq 1 kg baliq topilmaydi —
1.35 kg chiqadi. Agar chekda "1 kg" yozilsa, mijoz "men 1 kg uchun
to'layman" deydi. Shuning uchun tizim **tortmaguncha chek chiqarmaydi**.

### 1. Admin: taomni "tortiladigan" deb belgilash

**Menyu & Taomlar** → taomni tahrirlash → **⚖️ Tortiladigan taom** katagiga
belgi qo'ying → o'lchov birligini tanlang (kg / l / g).

Shundan keyin **narx 1 kg uchun** bo'ladi. Masalan baliq 1 kg = 120 000 so'm.

### 2. Ofitsiant: tarozida tortish

Ofitsiant baliqni bosganda **"⚖️ Tarozida tortish"** oynasi o'zi ochiladi:

- Aniq og'irlikni kiritadi (masalan `1.35`)
- Narx shu zahoti ko'rinadi: `1.35 kg × 120 000 = 162 000 so'm`
- Saqlanadi va hisob yangilanadi

Hali tortilmagan bo'lsa qator qizil **"TORTILMAGAN — bosing!"** bo'lib
yonib turadi, pastda ham ogohlantirish chiqadi.

### 3. Tizim nimani bloklaydi

Tortilmagan taom bo'lsa quyidagilar **ishlamaydi** (tushunarli xato chiqadi):

- Mijoz chekini chiqarish (`Chek — Printer 1`)
- Kassada to'lovni qabul qilish
- Stolni bo'shatish

Oshxona begunogi esa chiqadi — unda taom yonida **"ТОРТИЛСИН!"** deb yoziladi,
shunda oshxona tortishi kerakligini biladi.

### 4. Chek qanday chiqadi

```
1. Балиқ (тирик)
   1.35 кг x 120 000                     162 000
2. Ош (Плов)
   1 x 35 000                             35 000
```

Mijoz nechchi kilogramm olganini va aynan shuning pulini chekdan ko'radi —
nizo chiqmaydi.

> Og'irlikni oshxonaga yuborgandan keyin ham o'zgartirish mumkin
> (to'lov qilinmaguncha). Narx avtomatik qayta hisoblanadi.

---

## Bosh sahifada qaysi kategoriyalar chiqishi

**Yangi qo'shilgan kategoriya bosh sahifada CHIQMAYDI** — o'zingiz yoqishingiz
kerak. Shunday qilib "Sigaret" kabi ichki kategoriyalar mijoz ko'radigan
sahifada o'zidan paydo bo'lmaydi.

Yoqish/o'chirish: Admin → **Menyu & Taomlar** → kategoriya yonidagi
**👁 Bosh sahifa** tugmasi:

- **👁** — bosh sahifada ko'rinadi
- **🚫** — yashirilgan

Yangi kategoriya yaratayotganda ham oynadagi **"👁 Bosh sahifada
ko'rsatilsin"** katagini belgilashingiz mumkin.

> **QR menyu boshqacha:** stoldagi QR kodni skanerlagan mijoz **barcha**
> kategoriyalarni ko'radi — sigaret ham, shunda ofitsiant uni buyurtmaga
> qo'sha oladi. Yashirish faqat saytning bosh sahifasiga tegishli.

---

## Chekdagi og'irlikni tuzatish

Baliq 1.5 kg deb buyurtma olingan, tarozida 1.7 kg chiqdi:

Admin → **Stollar & QR** → **Hisobni ko'rish** → baliq qatoridagi
**⚖️ 1.5 kg ✎** tugmasini bosing → yangi og'irlikni yozing.

Narx va chek avtomatik qayta hisoblanadi.

---

## Menyu va kategoriyalar

Mijoz ko'radigan menyuda **faqat siz admin panelda qo'shgan taomlar**
chiqadi. Boshqa hech narsa ko'rinmaydi.

Boshlang'ich kategoriyalar: **Kaboblar · Salatlar · Ichimliklar · Choylar**
(bo'sh holda beriladi — o'zingiz to'ldirasiz).

### Kategoriyalarni o'zgartirish

Admin → **Menyu & Taomlar**:

| Amal | Qayerda |
|---|---|
| Yangi kategoriya | **+ Yangi Kategoriya** tugmasi |
| Nomini / belgisini o'zgartirish | kategoriya yonidagi ✏️ |
| O'chirish | kategoriya yonidagi 🗑 |

> Eski buyurtmalarda ishlatilgan taomni yoki shunday taomi bor
> kategoriyani **o'chirib bo'lmaydi** — aks holda cheklar arxivi buziladi.
> Tizim buni tushuntirib aytadi. Bunday taomni menyudan yo'qotish uchun
> **"Stop-list"** tugmasini bosing: mijozga ko'rinmaydi, chek tarixi esa
> saqlanib qoladi.

### Namuna menyuni tozalash

Demo taomlar (internetdan olingan suratlar bilan) qolgan bo'lsa:

**`RESTARON_MENYUNI_TOZALASH.bat`** — o'ng tugma → *Run as administrator*.

- Ishlatilmagan namuna taomlar **o'chiriladi**
- Eski cheklarda ishlatilganlari **yashiriladi** (tarix buzilmaydi)
- 4 ta bo'sh kategoriya qoladi
- Stollar, QR kodlar, xodimlar, buyurtmalar va cheklar **saqlanadi**

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

## Boshqa kompyuterga ko'chirish

Papkani shunchaki ZIP qilib yuborish **ishlamaydi**: `backend\.venv`
ichida eski kompyuterning yo'llari yozilgan (`C:\Users\<nom>\...`),
yangi kompyuterda ular topilmaydi va server ishga tushmaydi.

Shuning uchun **`RESTARON_NUSXA_OLISH.bat`** ni ishlating — ikki marta
bosing (administrator kerak emas). U ish stolida toza ZIP yaratadi
(~40 MB).

| ZIP ichiga KIRADI | KIRMAYDI (yangi kompyuterda qayta yaratiladi) |
|---|---|
| butun dastur kodi | `backend\.venv` (eski yo'llar) |
| menyu, stollar, xodimlar | `frontend\node_modules` |
| buyurtmalar, cheklar arxivi | `frontend\dist` |
| taom suratlari, QR rasmlari | jurnal fayllari |
| sozlamalar (printerlar, shrift) | vaqtinchalik internet manzili |

Baza nusxasi SQLite ning o'z vositasi bilan olinadi — server ishlab
turganda ham butun nusxa chiqadi.

### Yangi kompyuterda

1. ZIP ni **o'ng tugma → Properties → "Unblock" → OK** *(shundan keyin oching!)*
2. `C:\RestAron` ga chiqaring
3. Python 3.11 va Node.js LTS o'rnating
4. **`1_BIRINCHI_ORNATISH.bat`** — ikki marta bosing
5. **`2_SERVERNI_ORNATISH.bat`** — administrator nomidan

Menyu, stollar, xodimlar, cheklar arxivi — hammasi avvalgidek bo'ladi.
Admin login ham o'zgarmaydi.

> **QR kodlar haqida.** Stollarning QR kodlari ichidagi manzil eski
> kompyuternikiga ishora qiladi. Yangi kompyuterda: Admin →
> **Stollar & QR** → "Manzilni o'zgartirish" → yangi IP ni qo'ying →
> QR kodlarni **qayta chop eting**.

> **Ikkala kompyuterda birga ishlatmang.** Bu ko'chirish, sinxronlash
> emas — har bir kompyuterda alohida baza bo'ladi va ular bir-biridan
> ajralib ketadi.

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
