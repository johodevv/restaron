# Read-only: parse and construct a scheduled task in memory, never register it.
$ErrorActionPreference = 'Stop'
$scriptPath = Join-Path $PSScriptRoot '..\tools\windows_autostart.ps1'
$tokens = $null
$errors = $null
[void][Management.Automation.Language.Parser]::ParseFile($scriptPath, [ref]$tokens, [ref]$errors)
if ($errors.Count) { throw ($errors | Out-String) }
. $scriptPath -DefineOnly
$task = New-RestAronTask
if ($task.Triggers[0].Delay -ne 'PT30S') { throw 'Startup delay mismatch' }
if ($task.Triggers[0].CimClass.CimClassName -ne 'MSFT_TaskBootTrigger') { throw 'Not a boot trigger' }
if ($task.Principal.UserId -notin @('SYSTEM', 'S-1-5-18')) { throw 'Not SYSTEM' }
if ($task.Principal.LogonType -ne 5) { throw 'Not ServiceAccount' }
if ($task.Settings.MultipleInstances -ne 2) { throw 'Not IgnoreNew' }
if ($task.Settings.RestartCount -ne 999) { throw 'Missing recovery' }
if ($task.Settings.RestartInterval -ne 'PT1M') { throw 'Recovery delay mismatch' }
if ($task.Settings.ExecutionTimeLimit -ne 'PT0S') { throw 'Task would time out' }
if ($task.Settings.DisallowStartIfOnBatteries -or $task.Settings.StopIfGoingOnBatteries) { throw 'Battery blocks startup' }
if (-not $task.Settings.StartWhenAvailable) { throw 'Missed startup not handled' }
if (-not $task.Settings.Hidden) { throw 'Not hidden' }
if ($task.Settings.Priority -ne 5) { throw 'Not normal priority' }
if ($task.Actions[0].WorkingDirectory -ne $projectRoot) { throw 'Wrong working directory' }
if ($task.Actions[0].Execute -ne $pythonPath) { throw 'Wrong Python' }
if ($task.Actions[0].Arguments -notlike '*server_manager.py" serve') { throw 'Wrong entry point' }
Assert-RestAronTask $task
$badTask = New-ScheduledTask -Action (New-ScheduledTaskAction -Execute 'C:\unrelated\python.exe')
$rejected = $false
try { Assert-RestAronTask $badTask } catch { $rejected = $true }
if (-not $rejected) { throw 'Unrelated task was accepted' }
Write-Host 'PASS: Windows PowerShell syntax, SYSTEM boot task, recovery, timeout, quoting and task ownership.'
