param([switch]$CheckOnly)
# Windows PowerShell 5.1 launcher. Keep orchestration outside the venv being updated.
$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONDONTWRITEBYTECODE = '1'
$python = Join-Path $projectRoot 'backend\.venv\Scripts\python.exe'
$runner = Join-Path $PSScriptRoot 'windows_update.py'
try {
    if (-not $CheckOnly) {
        $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
        $principal = New-Object Security.Principal.WindowsPrincipal($identity)
        if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
            $arguments = '-NoProfile -ExecutionPolicy Bypass -File "{0}"' -f $PSCommandPath
            $elevated = Start-Process -FilePath (Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe') `
                -ArgumentList $arguments -Verb RunAs -Wait -PassThru
            exit $elevated.ExitCode
        }
    }
    if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
        throw 'Python muhiti topilmadi. Avval 1_BIRINCHI_ORNATISH.bat ni bajaring.'
    }
    if (-not (Test-Path -LiteralPath $runner -PathType Leaf)) {
        throw 'tools\windows_update.py topilmadi. ZIP paketini toliq oching.'
    }
    # Base Python holds no venv files open during install or rollback.
    $basePython = & $python -X utf8 -c 'import sys; print(sys._base_executable)'
    if ($LASTEXITCODE -ne 0 -or -not $basePython -or -not (Test-Path -LiteralPath $basePython -PathType Leaf)) {
        throw 'Ishchi Python muhiti ochilmadi. Uni Python 3.12 bilan qayta yaratish kerak.'
    }
    Set-Location -LiteralPath $projectRoot
    $arguments = @('-X', 'utf8', '-u', $runner, '--root', $projectRoot, '--python', $python)
    if ($CheckOnly) { $arguments += '--check' }
    & $basePython @arguments
    exit $LASTEXITCODE
} catch {
    Write-Host ('XATO: ' + $_.Exception.Message) -ForegroundColor Red
    exit 1
}
