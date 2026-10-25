# Windows PowerShell 5.1. Read-only: no app imports, installs, service changes or secrets.
$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$logPath = Join-Path $projectRoot 'RESTARON_TEKSHIRUV.txt'
$transcriptStarted = $false
$exitCode = 0
try {
    try {
        Start-Transcript -LiteralPath $logPath -Force | Out-Null
    } catch {
        $logPath = Join-Path $env:TEMP 'RESTARON_TEKSHIRUV.txt'
        Start-Transcript -LiteralPath $logPath -Force | Out-Null
    }
    $transcriptStarted = $true
    Write-Host 'RESTARON: YANGI KOMPYUTER TEKSHIRUVI'
    Write-Host ('Papka: ' + $projectRoot)
    Write-Host ('Windows: ' + [Environment]::OSVersion.VersionString)
    Write-Host ('64-bit Windows: ' + [Environment]::Is64BitOperatingSystem)
    Write-Host ('PowerShell: ' + $PSVersionTable.PSVersion)
    Write-Host ''
    foreach ($name in @('py.exe', 'python.exe', 'node.exe', 'npm.cmd')) {
        $program = Get-Command $name -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($null -eq $program) {
            Write-Host ('TOPILMADI: ' + $name)
        } else {
            Write-Host ('TOPILDI: ' + $program.Source)
        }
    }
    Write-Host ''
    $missing = @()
    foreach ($relative in @('1_BIRINCHI_ORNATISH.bat', 'server_manager.py', 'frontend_build.py',
        'backend\requirements.txt', 'backend\.env', 'backend\restaron.db',
        'cloudflared.exe', 'tunnel_sozlama.txt', 'tools\windows_autostart.py',
        'tools\windows_autostart.ps1', 'frontend\dist\index.html')) {
        if (Test-Path -LiteralPath (Join-Path $projectRoot $relative) -PathType Leaf) {
            Write-Host ('OK: ' + $relative)
        } else {
            Write-Host ('YOQ: ' + $relative)
            $missing += $relative
        }
    }
    # Deliberately do not print .env, tunnel token or process command lines.
    $python = Join-Path $projectRoot 'backend\.venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
        Write-Host ''
        Write-Host 'SABAB: backend\.venv\Scripts\python.exe topilmadi.'
        Write-Host 'YECHIM: Python va Node.js o''rnatib, 1_BIRINCHI_ORNATISH.bat ni bajaring.'
        $exitCode = 1
    } else {
        Write-Host ''
        Write-Host 'Python virtual muhiti tekshirilmoqda...'
        $env:PYTHONIOENCODING = 'utf-8'
        # Capture native stderr so a broken copied venv is recorded on PowerShell 5.1.
        $previousPreference = $ErrorActionPreference
        try {
            $ErrorActionPreference = 'Continue'
            $pythonOutput = & $python -X utf8 -c 'import sys; print(sys.version.split()[0]); print(sys.executable)' 2>&1
            $pythonCode = $LASTEXITCODE
        } finally {
            $ErrorActionPreference = $previousPreference
        }
        $pythonOutput | ForEach-Object { Write-Host $_ }
        if ($pythonCode -ne 0) {
            Write-Host 'SABAB: Python virtual muhiti ishga tushmadi. Eski kompyuterdan ko''chirilgan .venv bunga sabab bo''lishi mumkin.'
            Write-Host 'YECHIM: yangi kompyuterdagi backend\.venv papkasini .venv_eski deb nomlang; 1_BIRINCHI_ORNATISH.bat ni qayta bajaring.'
            $exitCode = 1
        } elseif ($missing -contains 'tools\windows_autostart.py') {
            Write-Host 'SABAB: tools\windows_autostart.py nusxada yetishmayapti.'
            $exitCode = 1
        } else {
            Write-Host ''
            Write-Host 'Server uchun zarur fayl, kutubxona, baza va domen tekshiruvi:'
            & $python -X utf8 (Join-Path $projectRoot 'tools\windows_autostart.py') check
            $exitCode = $LASTEXITCODE
            if ($exitCode -eq 0) {
                Write-Host 'ASOSIY TEKSHIRUV OTDI. Avto-server o''rnatish oynasidagi to''liq XATO satri kerak.'
            }
        }
    }
} catch {
    Write-Host ('TEKSHIRUV XATOSI: ' + $_.Exception.Message)
    $exitCode = 1
} finally {
    Write-Host ''
    Write-Host ('JURNAL: ' + $logPath)
    Write-Host 'Shu faylni yoki oynadagi SABAB / XATO yozuvini yuboring.'
    if ($transcriptStarted) { Stop-Transcript | Out-Null }
}
exit $exitCode
