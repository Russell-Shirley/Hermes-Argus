#Requires -Version 5.1
<#
.SYNOPSIS
    Registers HermesArgusCodeGraphCheck as a twice-daily Task Scheduler task.

.DESCRIPTION
    Schedules codegraph-health-check.ps1 at 09:00 and 17:00 every day.
    Checks binary availability, MCP wiring in ~/.claude.json, and all 6 B&B repo
    indexes. Alerts Slack #biz-bridgeandbolt on any failure.

    Re-running this script is safe -- it updates the task in place if it already exists.

    The companion Argus cron (config\cron\jobs.json: codegraph_health_check) reads
    D:\hermes-backups\codegraph-health.json at 09:15 and 17:15 as a second
    independent check that can surface stale-probe conditions.

.NOTES
    Run once from an elevated PowerShell session.
    Requires: scripts\codegraph-health-check.ps1 to exist alongside this file.
#>

$ErrorActionPreference = "Stop"

$TaskName = "HermesArgusCodeGraphCheck"
$Script   = Join-Path $PSScriptRoot "codegraph-health-check.ps1"
$RepoRoot = Split-Path $PSScriptRoot -Parent

if (-not (Test-Path $Script)) {
    throw "Health-check script not found at $Script -- ensure codegraph-health-check.ps1 is present."
}

$Action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NonInteractive -ExecutionPolicy Bypass -File `"$Script`"" `
    -WorkingDirectory $RepoRoot

$Triggers = @(
    (New-ScheduledTaskTrigger -Daily -At "09:00"),
    (New-ScheduledTaskTrigger -Daily -At "17:00")
)

$Settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -RunOnlyIfIdle:$false `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 5) `
    -WakeToRun

$Principal = New-ScheduledTaskPrincipal `
    -UserId "$env:USERDOMAIN\$env:USERNAME" `
    -LogonType S4U `
    -RunLevel Highest

$Existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($Existing) {
    Set-ScheduledTask -TaskName $TaskName `
        -Action $Action -Trigger $Triggers `
        -Settings $Settings -Principal $Principal | Out-Null
    Write-Host "Task '$TaskName' updated (09:00 + 17:00 daily)" -ForegroundColor Green
} else {
    Register-ScheduledTask -TaskName $TaskName `
        -Action $Action -Trigger $Triggers `
        -Settings $Settings -Principal $Principal `
        -Description "Twice-daily CodeGraph health probe -- checks binary, MCP wiring, and all 6 B&B repo indexes. Alerts Slack on failure." | Out-Null
    Write-Host "Task '$TaskName' registered -- runs daily at 09:00 and 17:00" -ForegroundColor Green
}

Write-Host ""
Write-Host "Useful commands:" -ForegroundColor Cyan
Write-Host "  Run now (via Task Scheduler):"
Write-Host "    Start-ScheduledTask '$TaskName'"
Write-Host ""
Write-Host "  Run now directly (no Slack):"
Write-Host "    powershell -File `"$Script`" -Quiet"
Write-Host ""
Write-Host "  Inspect last result:"
Write-Host "    Get-Content D:\hermes-backups\codegraph-health.json | ConvertFrom-Json | Format-List"
Write-Host ""
Write-Host "  View task history:"
Write-Host "    Get-ScheduledTaskInfo '$TaskName' | Format-List"
