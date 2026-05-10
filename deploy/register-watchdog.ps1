# Registers the Hermes watchdog as a Windows Task Scheduler task.
# Run once as the logged-in user (no elevation required).
# Task auto-starts at logon and restarts on failure.

$TaskName    = "HermesGatewayWatchdog"
$ScriptPath  = "$env:USERPROFILE\Documents\GitHub\Hermes-Argus\deploy\watchdog.ps1"
$PwshExe     = "powershell.exe"

# Remove stale registration if it exists
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue

$action  = New-ScheduledTaskAction `
               -Execute $PwshExe `
               -Argument "-NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$ScriptPath`""

# Trigger: at logon of current user
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME

# Settings: restart on failure, don't stop if running on battery, run indefinitely
$settings = New-ScheduledTaskSettingsSet `
                -ExecutionTimeLimit (New-TimeSpan -Days 365) `
                -RestartCount 10 `
                -RestartInterval (New-TimeSpan -Minutes 1) `
                -StartWhenAvailable `
                -RunOnlyIfNetworkAvailable

$principal = New-ScheduledTaskPrincipal `
                 -UserId $env:USERNAME `
                 -LogonType Interactive `
                 -RunLevel Limited

Register-ScheduledTask `
    -TaskName  $TaskName `
    -Action    $action `
    -Trigger   $trigger `
    -Settings  $settings `
    -Principal $principal `
    -Description "Hermes gateway watchdog - auto-restarts on crash (MCP TimeoutError mitigation)" | Out-Null

Write-Host "Registered task '$TaskName'"
Write-Host "It will start at next logon. To start immediately:"
Write-Host "  Start-ScheduledTask -TaskName '$TaskName'"
