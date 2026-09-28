# 🚀 RestAron Loyihasini Bepul Serverlarga Joylash (Deploy) Qo'llanmasi

Ushbu qo'llanma orqali siz **RestAron** tizimining Backend va Frontend qismlarini dunyodagi eng yaxshi bepul bulutli serverlarga (Render & Vercel) 100% bepul joylashtirishingiz mumkin.

---

## 1-Qadam: GitHub ga yuklash

1. [GitHub.com](https://github.com) saytiga kiring va yangi bo'sh repository yarating (masalan: `restaron`).
2. Terminalda quyidagi buyruqlarni bajaring:
```bash
git init
git add .
git commit -m "RestAron: Smart Restaurant System (Ready for Deploy)"
git branch -M main
git remote add origin https://github.com/<SIZNING_USERNAME>/restaron.git
git push -u origin main
```

---

## 2-Qadam: Backendni joylash (Render.com — 100% Bepul)

**Render.com** — FastAPI, WebSockets va Python uchun eng qulay bepul hosting.

1. [Render.com](https://render.com) ga kiring va GitHub orqali ro'yxatdan o'ting.
2. **"New +"** -> **"Web Service"** tugmasini bosing.
3. GitHub dagi `restaron` repository-ingizni tanlang.
4. Quyidagi parametrlarni kiriting:
   - **Name**: `restaron-backend`
   - **Region**: `Frankfurt (EU Central)`
   - **Root Directory**: `backend`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type**: `Free`
5. **Environment Variables** bo'limiga quyidagilarni qo'shing:
   - `APP_ENV` = `production`
   - `DEBUG` = `false`
   - `SECRET_KEY` = `restaron-super-secret-key-2026-xyz`
   - `DATABASE_URL` = `sqlite+aiosqlite:///./restaron.db`
   - `CORS_ORIGINS` = `*`
6. **"Deploy Web Service"** tugmasini bosing.
7. 2 daqiqadan so'ng backend manzilingiz tayyor bo'ladi (masalan: `https://restaron-backend.onrender.com`).

---

## 3-Qadam: Frontendni joylash (Vercel — 100% Bepul va Juda Tez)

**Vercel** — React / Vite ilovalari uchun eng yaxshi va tezkor global CDN hosting.

1. [Vercel.com](https://vercel.com) ga kiring va GitHub orqali kiring.
2. **"Add New..."** -> **"Project"** tugmasini bosing.
3. `restaron` repository-ingizni tanlang (Import).
4. **Project Settings** da:
   - **Framework Preset**: `Vite`
   - **Root Directory**: `frontend` (Edit tugmasini bosib `frontend` ni tanlang)
5. **Environment Variables** ga:
   - `VITE_API_URL` = `https://restaron-backend.onrender.com/api/v1` *(Render dan olgan Backend URL)*
   - `VITE_WS_URL` = `wss://restaron-backend.onrender.com/api/v1/ws` *(WebSocket URL)*
6. **"Deploy"** tugmasini bosing.
7. 1 daqiqadan so'ng sizning jonli saytingiz tayyor bo'ladi (masalan: `https://restaron.vercel.app`).

---

## 4-Qadam: QR Kod havolasini yangilash

Deploy yakunlangach, Admin panelga kiring (`/` -> Xodimlar):
- Login: `admin`
- Parol: `admin123`
- **"Stollar & QR Kodlar"** bo'limida **"QR Base URL"** manzilini o'zingizning Vercel manzilingizga (masalan: `https://restaron.vercel.app`) sozlab qo'ying.
- Shunda barcha stollar uchun chiqariladigan QR kodlar to'g'ridan-to'g'ri internet orqali har qanday telefonda ochiladi! 🎉
