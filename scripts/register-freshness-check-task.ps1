#Requires -Version 5.1
<#
.SYNOPSIS
    Registers the HermesArgusFreshnessCheck Task Scheduler task -- daily
    independent probe of the B2 backup's latest snapshot age.

.DESCRIPTION
    Schedules b2-freshness-check.ps1 to run daily at 08:30 local time.
    Independent of Argus's backup_jobs check; catches B2-side failures that
    the script's own DB insert can't see.

    Default threshold: alert if the latest B2 snapshot is older than 25 hours.

    Re-running this register script is safe -- updates the task in place if
    it already exists.

.NOTES
    Run once from an elevated PowerShell session. Assumes register-backup-task.ps1
    has already initialized Restic and the B2 repo.
#>

$ErrorActionPreference = "Stop"

$TaskName = "HermesArgusFreshnessCheck"
$Script   = Join-Path $PSScriptRoot "b2-freshness-check.ps1"
$RepoRoot = Split-Path $PSScriptRoot -Parent

if (-not (Test-Path $Script)) {
    throw "Freshness-check script not found at $Script"
}

$Action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NonInteractive -ExecutionPolicy Bypass -File `"$Script`"" `
    -WorkingDirectory $RepoRoot

$Trigger = New-ScheduledTaskTrigger -Daily -At "08:30"

$Settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -RunOnlyIfIdle:$false `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 10) `
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
        -Description "Daily independent probe of B2 backup freshness -- alerts Slack if latest snapshot > 25h old" | Out-Null
    Write-Host "Task '$TaskName' registered -- daily at 08:30" -ForegroundColor Green
}

Write-Host ""
Write-Host "Run a one-off check now:" -ForegroundColor Cyan
Write-Host "  Start-ScheduledTask '$TaskName'"
Write-Host "  # or directly (suppresses Slack alert):"
Write-Host "  powershell -File `"$Script`" -Quiet"
Write-Host ""
Write-Host "Inspect last result:"
Write-Host "  Get-Content D:\hermes-backups\b2-freshness.json"
