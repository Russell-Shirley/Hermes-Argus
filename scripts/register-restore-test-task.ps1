#Requires -Version 5.1
<#
.SYNOPSIS
    Registers the HermesArgusRestoreTest Task Scheduler task -- quarterly
    automated restore test of the B2 backup.

.DESCRIPTION
    Schedules quarterly-restore-test.ps1 to run on the 1st of January, April,
    July, and October at 09:00. The script's own idempotency check (80-day
    skip window) provides a second guard against accidental re-runs.

    Re-running this register script is safe -- updates the task in place if
    it already exists.

.NOTES
    Run once from an elevated PowerShell session. Assumes register-backup-task.ps1
    has already initialized Restic and the B2 repo.
#>

$ErrorActionPreference = "Stop"

$TaskName     = "HermesArgusRestoreTest"
$Script       = Join-Path $PSScriptRoot "quarterly-restore-test.ps1"
$RepoRoot     = Split-Path $PSScriptRoot -Parent

if (-not (Test-Path $Script)) {
    throw "Restore-test script not found at $Script"
}

# Quarterly: 1st of Jan/Apr/Jul/Oct at 09:00 local time.
# MSFT_TaskMonthlyTrigger.MonthsOfYear is a bitmask: Jan=1, Apr=8, Jul=64, Oct=512.
$MonthsBitmask = 1 + 8 + 64 + 512    # 585
$class = Get-CimClass -Namespace ROOT\Microsoft\Windows\TaskScheduler -ClassName MSFT_TaskMonthlyTrigger
$Trigger = New-CimInstance -CimClass $class -ClientOnly -Property @{
    DaysOfMonth   = 1
    MonthsOfYear  = $MonthsBitmask
    StartBoundary = (Get-Date "09:00:00").ToString("yyyy-MM-ddTHH:mm:ss")
    Enabled       = $true
}

$Action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NonInteractive -ExecutionPolicy Bypass -File `"$Script`"" `
    -WorkingDirectory $RepoRoot

$Settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -RunOnlyIfIdle:$false `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1) `
    -WakeToRun

$Principal = New-ScheduledTaskPrincipal `
    -UserId "$env:USERDOMAIN\$env:USERNAME" `
    -LogonType S4U `
    -RunLevel Highest

$Existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($Existing) {
    Set-ScheduledTask -TaskName $TaskName `
        -Action $Action -Trigger $Trigger `
        -Settings $Settings -Principal $Principal | Out-Null
    Write-Host "Task '$TaskName' updated" -ForegroundColor Green
} else {
    Register-ScheduledTask -TaskName $TaskName `
        -Action $Action -Trigger $Trigger `
        -Settings $Settings -Principal $Principal `
        -Description "Quarterly Hermes-Argus restore test against B2 (independent verification that backups can be restored)" | Out-Null
    Write-Host "Task '$TaskName' registered -- quarterly at 09:00 on Jan/Apr/Jul/Oct 1st" -ForegroundColor Green
}

Write-Host ""
Write-Host "Run a one-off test now (will exit without restoring if last success < 80 days ago):" -ForegroundColor Cyan
Write-Host "  Start-ScheduledTask '$TaskName'"
Write-Host "  # or force a run regardless:"
Write-Host "  powershell -File `"$Script`" -Force"
Write-Host ""
Write-Host "Inspect last result:"
Write-Host "  Get-Content `$env:LOCALAPPDATA\hermes-restore-test\last-result.json"
