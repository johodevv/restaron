# RestAron Backend Ishga tushirish scripti
# PowerShell: .\start_backend.ps1

Write-Host "🍽️  RestAron Backend ishga tushirilmoqda..." -ForegroundColor Cyan

$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

# Backend papkasiga o'tish
Set-Location "$PSScriptRoot\backend"

# Python virtual environment yaratish (agar yo'q bo'lsa)
if (-not (Test-Path ".venv")) {
    Write-Host "📦 Virtual environment yaratilmoqda..." -ForegroundColor Yellow
    python -m venv .venv
}

# Kutubxonalar o'rnatish (agar kerak bo'lsa)
if (-not (Test-Path ".venv\Lib\site-packages\fastapi")) {
    Write-Host "📚 Kutubxonalar o'rnatilmoqda..." -ForegroundColor Yellow
    & ".venv\Scripts\python.exe" -m pip install -r requirements.txt -q
}

# .env faylini tekshirish
if (-not (Test-Path ".env")) {
    Write-Host "⚠️  .env fayl topilmadi, namuna nusxalanmoqda..." -ForegroundColor Red
    Copy-Item ".env.example" ".env"
}

# Uploads papkalarini yaratish
New-Item -ItemType Directory -Force -Path "uploads\qr_codes" | Out-Null
New-Item -ItemType Directory -Force -Path "uploads\menu_items" | Out-Null
New-Item -ItemType Directory -Force -Path "uploads\logos" | Out-Null

# Boshlang'ich ma'lumotlarni yuklash (birinchi marta)
if (-not (Test-Path "restaron.db")) {
    Write-Host "🌱 Boshlang'ich ma'lumotlar yuklanmoqda..." -ForegroundColor Green
    & ".venv\Scripts\python.exe" -c "import asyncio; from app.core.database import create_tables; asyncio.run(create_tables())"
    & ".venv\Scripts\python.exe" seed.py
}

# Serverni ishga tushirish
Write-Host ""
Write-Host "✅ Backend server ishga tushirilmoqda: http://localhost:8000" -ForegroundColor Green
Write-Host "📖 API Docs: http://localhost:8000/docs" -ForegroundColor Blue
Write-Host ""
& ".venv\Scripts\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
