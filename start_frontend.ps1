# RestAron Frontend Ishga tushirish scripti
# PowerShell: .\start_frontend.ps1

Write-Host "🎨  RestAron Frontend ishga tushirilmoqda..." -ForegroundColor Cyan

Set-Location "$PSScriptRoot\frontend"

$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

if (-not (Test-Path "node_modules")) {
    Write-Host "📦 Node modullari o'rnatilmoqda..." -ForegroundColor Yellow
    npm install
}

Write-Host "✅ Frontend server ishga tushirilmoqda: http://localhost:5173" -ForegroundColor Green
npm run dev -- --host
