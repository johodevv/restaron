# 🍽️ RestAron — Professional Restoran Boshqaruv va POS Tizimi (Ali Poster Ekvivalenti)

**RestAron** — Restoran va kafelar uchun to'liq avtomatlashtirilgan aqlli bulutli platforma:
- **Mijozlar (QR Menyu)**: Stol ustidagi QR kod orqali kirib, chiroyli dizayndagi menyuni, narxlar, taom rasmlari va tavsiflarini ko'radi, 1 bosish bilan **"Ofitsiantni chaqirish"** yoki **"Hisob (Chek) so'rash"** tugmasini bosadi (saytdan mustaqil zakaz berish o'chirilgan, faqat zal nazorati uchun).
- **Ofitsiantlar (Ali Poster POS Paneli)**: Ali Poster standartidagi qulay sensorli ekran: Zallar, Stollar tanlash, Menyudan taomlarni 1 bosishda qo'shish, oshxonaga begunok chiqarish (**"На кухню"**), mijozga hisob chiqarish (**"К оплате"**), to'lov turlarini belgilash.
- **Xprinter Termal Chek Tizimi**: 58mm va 80mm Xprinter termal printerlarida oshxona begunogi (Kitchen runner), mijoz pre-cheki va kassa smena hisobotlari (X/Z-Report) chop etiladi.
- **Admin Paneli (11 ta bo'lim)**:
  1. *Xulosa (Dashboard)* — Jonli statistika va yangi chaqiruvlar
  2. *Menyu & Taomlar* — Taomlar, narxlar, rasmlar va **Tezkor Stop-List (1 bosishda Tugadi/Mavjud)**
  3. *Stollar & QR Kodlar* — Har bir stol uchun unikal QR generatsiya
  4. *Xodimlar* — Ofitsiant, oshpaz, kassir boshqaruvi
  5. *Qarzlar (Nasiya Kitobi)* — Mijozlar qarzlari, to'lovlar va **1-bosishda SMS eslatma**
  6. *Cheklar Arxivi* — Barcha chiqarilgan cheklarni **3 yilgacha saqlash** va istalgan payt qayta chop etish (Reprint)
  7. *Kassa Hisoboti (Отчет по оплатам)* — Naqd, Uzcard/Humo, Click/Payme, Nasiya bo'yicha to'liq tahlil, **X-Hisobot** va smena yopish **Z-Hisobot**
  8. *Ofitsiantlar KPI* — Savdo hajmi, xizmat haqi ulushi va ofitsiantlar reytingi
  9. *Dizayn & Temalar* — 6 xil zamonaviy restoran ranglar palitrasi
  10. *Sozlamalar* — Xizmat haqi foizi (12% ➔ 13%), Xprinter qog'oz eni (58/80mm), chek matnlari, SMS va Telegram Bot integratsiyasi
  11. *Baholar & Fikrlar* — Mijozlar qoldirgan izohlar
- **Dasturchi (Superadmin)**: Barcha ulangan restoranlar aylanmasi va oylik/haftalik platforma komissiyasi monitoringi.


---

## 🏗️ Arxitektura va Texnologiyalar

- **Backend**: FastAPI, PostgreSQL, SQLAlchemy (Async), Alembic, WebSockets, JWT, bcrypt.
- **Frontend**: React 18, Vite, Tailwind CSS, Lucide Icons, Canvas-confetti, Web Audio API chimes.
- **Dizayn Temalari**: 6 ta tayyor tema (*Elegant Dark*, *Fresh Green*, *Warm Sunset*, *Ocean Blue*, *Royal Purple*, *Minimalist White*).

---

## 🐳 Docker orqali ishga tushirish (1 ta buyruq bilan)

```bash
# Barcha servislar (Backend, Frontend, PostgreSQL DB) ni ishga tushirish
docker compose up -d --build

# Boshlang'ich demo ma'lumotlarni yuklash
docker compose exec backend python seed.py
```

### 🌐 Veb Manzillar:
- **Frontend Ilovasi**: http://localhost:5173
- **Backend API Hujjatlari (Swagger Docs)**: http://localhost:8000/docs
- **Backend ReDoc**: http://localhost:8000/redoc

---

## 💻 Mahalliy (Manual) Ishga Tushirish

### 1. Backend:
```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
source venv/bin/activate       # Linux/Mac
pip install -r requirements.txt
copy .env.example .env         # Windows
cp .env.example .env           # Linux/Mac

# PostgreSQL ishga tushgach:
python seed.py
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Frontend:
```bash
cd frontend
npm install
npm run dev
```

---

## 🔑 Demo Kirish Ma'lumotlari

Tizimda 1-bosish bilan kiruvchi tezkor sinov akkauntlari mavjud:

| Rol | Login | Parol | Huquqlari |
|-----|-------|-------|-----------|
| **Developer** | `developer` | `dev123456` | Platforma monitoringi, barcha restoranlar va komissiyalar |
| **Admin** | `admin` | `admin123` | Restoran sozlamalari, menyu, stollar, QR, xodimlar |
| **Ofitsiant** | `ofitsiant1` | `waiter123` | Buyurtmalar, chaqiruvlar, **"Yetkazib berdim"** tugmasi |
| **Oshpaz** | `oshpaz1` | `chef123` | KDS oshxona ekrani, taomlarni "Tayyor" deb belgilash |

---

## 📡 Asosiy API Endpointlar

### 🛒 Mijoz (Ochiq):
- `GET /api/v1/tables/scan/{qr_token}` — QR kodni skanerlash va stol ma'lumoti
- `GET /api/v1/menu/full/{restaurant_id}` — To'liq menyu
- `POST /api/v1/orders/` — Buyurtma berish (savatchadan)
- `POST /api/v1/orders/call-waiter` — Ofitsiant chaqirish
- `POST /api/v1/reviews/` — Taom va xizmatga baho berish

### 🚶‍♂️ Ofitsiant:
- `GET /api/v1/orders/?restaurant_id=1` — Buyurtmalar ro'yxati
- `PATCH /api/v1/orders/{id}/deliver` — **"Yetkazib berdim" (Delivered) tugmasi**
- `PATCH /api/v1/orders/{id}/call/complete` — Chaqiruvni yakunlash
- `POST /api/v1/tables/{id}/clear` — Stolni bo'shatish

### 👨‍🍳 Oshpaz:
- `PATCH /api/v1/orders/{id}/items/{item_id}/prepared` — Taomni tayyor deb belgilash
- `PATCH /api/v1/orders/{id}/status` — Butun buyurtmani "Tayyor" (READY) qilish

### ⚙️ Admin:
- `POST /api/v1/menu/items` — Yangi taom qo'shish
- `POST /api/v1/tables/` — Yangi stol qo'shish va QR generatsiya
- `POST /api/v1/users/` — Ofitsiant / oshpaz akkaunti yaratish
- `POST /api/v1/restaurants/{id}/themes` — 6 tadan 2 ta temani tanlash

### 🛡️ Developer:
- `GET /api/v1/restaurants/commissions/summary` — Komissiyalar hisoboti
- `POST /api/v1/restaurants/{id}/commission/pay` — Komissiya to'lovini qayd etish
- `PATCH /api/v1/restaurants/{id}/commission-rate` — Komissiya foizini o'zgartirish
- `POST /api/v1/restaurants/` — Yangi restoran qo'shish

### ⚡ WebSocket:
- `WS /api/v1/ws/{restaurant_id}?token=JWT` (Xodimlar uchun)
- `WS /api/v1/ws/{restaurant_id}?table_id=X` (Mijoz stoli uchun)
- `GET /api/v1/ws/online/{restaurant_id}` — Onlayn xodimlar soni
