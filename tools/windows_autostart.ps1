param(
    [switch]$CheckOnly,
    [switch]$Remove,
    [switch]$DefineOnly
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$taskName = 'RestAron Server'
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$pythonPath = Join-Path $projectRoot 'backend\.venv\Scripts\python.exe'
$helperPath = Join-Path $PSScriptRoot 'windows_autostart.py'
$env:PYTHONIOENCODING = 'utf-8'

function Invoke-RestAronHelper([string]$Action) {
    & $pythonPath -X utf8 $helperPath $Action
    if ($LASTEXITCODE -ne 0) {
        throw "RestAron tekshiruvi bajarilmadi: $Action (kod $LASTEXITCODE)."
    }
}

function New-RestAronTask {
    $managerPath = Join-Path $projectRoot 'server_manager.py'
    $action = New-ScheduledTaskAction -Execute $pythonPath `
        -Argument ('-X utf8 -u "{0}" serve' -f $managerPath) -WorkingDirectory $projectRoot
    $trigger = New-ScheduledTaskTrigger -AtStartup
    $trigger.Delay = 'PT30S'
    $principal = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest
    $settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -StartWhenAvailable `
        -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) `
        -ExecutionTimeLimit ([TimeSpan]::Zero) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -Hidden -Priority 5
    New-ScheduledTask -Action $action -Trigger $trigger -Principal $principal -Settings $settings `
        -Description 'RestAron va dunyochoyxona.uz Cloudflare tunneli. Windows yuklangach 30 soniyada, hisobga kirmasdan ishlaydi.'
}

function Get-RestAronTask {
    Get-ScheduledTask -TaskName $taskName -TaskPath '\' -ErrorAction SilentlyContinue
}

function Assert-RestAronTask($Task) {
    # Do not overwrite a similarly named task belonging to a different checkout.
    if ($null -ne $Task) {
        $matching = @($Task.Actions | Where-Object {
            ($_.Execute -eq $pythonPath -and $_.Arguments -like ('*"{0}"*' -f (Join-Path $projectRoot 'server_manager.py'))) -or
            ($_.Execute -eq (Join-Path $projectRoot '_xizmat_ishga_tushirish.cmd'))
        })
        if ($matching.Count -ne 1) {
            throw 'RestAron Server nomli vazifa boshqa sozlamaga tegishli. Unga tegilmadi.'
        }
    }
}

function Save-PowerSettings([string]$Directory) {
    & powercfg.exe /getactivescheme | Out-File -LiteralPath (Join-Path $Directory 'power-before.txt') -Encoding utf8
    & powercfg.exe /query SCHEME_CURRENT SUB_SLEEP | Out-File -LiteralPath (Join-Path $Directory 'power-before.txt') -Append -Encoding utf8
    if ($LASTEXITCODE -ne 0) { throw 'Quvvat rejimi o''qilmadi.' }
    $activeLine = (& powercfg.exe /getactivescheme) -join ' '
    $scheme = [regex]::Match($activeLine, '[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}').Value
    if (-not $scheme) { throw 'Quvvat rejimi identifikatori topilmadi.' }
    & powercfg.exe /export (Join-Path $Directory 'power-before.pow') $scheme
    if ($LASTEXITCODE -ne 0) { throw 'Quvvat rejimi zaxiralanmadi.' }
}

if ($DefineOnly) { return } # In-memory tests only; never registers a task.

try {
    if (-not (Test-Path -LiteralPath $pythonPath -PathType Leaf)) {
        throw 'Python muhiti topilmadi. Avval 1_BIRINCHI_ORNATISH.bat ni bajaring.'
    }
    if ($CheckOnly) {
        Invoke-RestAronHelper 'check'
        $existing = Get-RestAronTask
        if ($null -eq $existing) {
            Write-Host 'Avtomatik vazifa hali o''rnatilmagan. BAT faylni oddiy rejimda ishga tushiring.'
        } else {
            Assert-RestAronTask $existing
            Write-Host ("Avtomatik vazifa: {0}; holati: {1}" -f $existing.TaskName, $existing.State)
        }
        & $pythonPath -X utf8 $helperPath health
        exit $LASTEXITCODE
    }

    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        $arguments = '-NoProfile -ExecutionPolicy Bypass -File "{0}"' -f $PSCommandPath
        if ($Remove) { $arguments += ' -Remove' }
        $elevated = Start-Process -FilePath (Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe') `
            -ArgumentList $arguments -Verb RunAs -Wait -PassThru
        exit $elevated.ExitCode
    }

    Set-Location -LiteralPath $projectRoot
    $existing = Get-RestAronTask
    Assert-RestAronTask $existing
    # Complete checks/build before touching the running service.
    if (-not $Remove) { Invoke-RestAronHelper 'prepare' }
    $stamp = Get-Date -Format 'yyyyMMdd_HHmmss_fff'
    $backupDirectory = Join-Path $projectRoot ("backups\autostart\settings_$stamp")
    New-Item -ItemType Directory -Path $backupDirectory -Force | Out-Null
    if ($null -ne $existing) {
        Export-ScheduledTask -TaskName $taskName -TaskPath '\' |
            Out-File -LiteralPath (Join-Path $backupDirectory 'task-before.xml') -Encoding utf8
    }
    if (-not $Remove) {
        $definition = New-RestAronTask
        Save-PowerSettings $backupDirectory
        # AC-only: preserve the battery, lid, display and global hibernation settings.
        & powercfg.exe /change standby-timeout-ac 0
        if ($LASTEXITCODE -ne 0) { throw 'Elektr tarmog''ida uyqu rejimini sozlab bo''lmadi.' }
        & powercfg.exe /change hibernate-timeout-ac 0
        if ($LASTEXITCODE -ne 0) { throw 'Elektr tarmog''ida hibernatsiyani sozlab bo''lmadi.' }
    }

    $wasEnabled = $null -ne $existing -and $existing.Settings.Enabled
    if ($null -ne $existing) { Disable-ScheduledTask -TaskName $taskName -TaskPath '\' | Out-Null }
    try {
        Write-Host 'Chek chiqarish tugashi kutilmoqda; baza zaxiralanadi va eski RestAron nusxalari yopiladi...'
        Invoke-RestAronHelper 'stop'
    } catch {
        if ($wasEnabled) { Enable-ScheduledTask -TaskName $taskName -TaskPath '\' | Out-Null }
        throw
    }
    if ($null -ne $existing) { Stop-ScheduledTask -TaskName $taskName -TaskPath '\' }

    if ($Remove) {
        if ($null -ne $existing) {
            Unregister-ScheduledTask -TaskName $taskName -TaskPath '\' -Confirm:$false
        }
        Write-Host 'RestAron avtomatik ishga tushishi bekor qilindi. Baza, buyurtmalar va Cloudflare sozlamasi saqlandi.'
        exit 0
    }

    try {
        Register-ScheduledTask -TaskName $taskName -TaskPath '\' -InputObject $definition -Force | Out-Null
        Start-ScheduledTask -TaskName $taskName -TaskPath '\'
    } catch {
        # Restore runtime if Task Scheduler rejects registration/start after migration.
        $startError = $_
        if ($wasEnabled) {
            try {
                Enable-ScheduledTask -TaskName $taskName -TaskPath '\' | Out-Null
                Start-ScheduledTask -TaskName $taskName -TaskPath '\'
            } catch {
                Write-Host 'Vazifa tiklanmadi; vaqtincha fonda ishga tushirishga uriniladi.'
            }
        }
        Start-Process -FilePath $pythonPath -ArgumentList ('-X utf8 -u "{0}" serve' -f (Join-Path $projectRoot 'server_manager.py')) `
            -WorkingDirectory $projectRoot -WindowStyle Hidden
        throw $startError
    }
    Write-Host 'Avtomatik vazifa o''rnatildi. Server va domen tayyorligi tekshirilmoqda (120 soniyagacha)...'
    & $pythonPath -X utf8 $helperPath wait
    $readyCode = $LASTEXITCODE
    $installed = Get-RestAronTask
    if ($null -eq $installed -or -not $installed.Settings.Enabled -or [string]$installed.State -ne 'Running') {
        throw 'Avtomatik vazifa ishlayotgani tasdiqlanmadi. Task Scheduler va server.log ni tekshiring.'
    }
    Write-Host ("Vazifa: {0}; holati: {1}; jurnal: {2}" -f $taskName, $installed.State, (Join-Path $projectRoot 'server.log'))
    Write-Host 'Keyingi safar Windows yuklangach, foydalanuvchi hisobiga kirmasdan fonda ishga tushadi.'
    Write-Host 'Odatda 1-2 daqiqa: Windows yuklanishi va internet tayyorligiga bog''liq. Kompyuter o''chsa sayt ham o''chadi.'
    exit $readyCode
} catch {
    Write-Host ("XATO: {0}" -f $_.Exception.Message) -ForegroundColor Red
    Write-Host 'Muvaffaqiyat tasdiqlanmadi. Xatoni tekshirib, BAT faylni qayta ishga tushiring.'
    exit 1
}
