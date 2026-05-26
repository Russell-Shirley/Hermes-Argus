# Registers the HermesHindsightStart Windows Task Scheduler task.
# Run once as the logged-in user (no elevation required).
# Triggers: AtLogOn + OnWake (covers sleep/hibernate kills of the Postgres process).
# Re-running is safe — removes and re-registers idempotently.

$TaskName   = "HermesHindsightStart"
$ScriptPath = "$env:USERPROFILE\Documents\GitHub\Hermes-Argus\deploy\hindsight-start.ps1"
$PwshExe    = "powershell.exe"

if (-not (Test-Path $ScriptPath)) {
    throw "hindsight-start.ps1 not found at $ScriptPath"
}

# Remove stale registration if it exists
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue

$action = New-ScheduledTaskAction `
              -Execute $PwshExe `
              -Argument "-NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$ScriptPath`""

# Trigger 1: at logon of current user
$logonTrigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME

# Trigger 2: on system wake from sleep/hibernate (Power-Troubleshooter Event ID 1)
$wakeClass   = Get-CimClass -Namespace ROOT\Microsoft\Windows\TaskScheduler -ClassName MSFT_TaskEventTrigger
$wakeTrigger = New-CimInstance -CimClass $wakeClass -ClientOnly
$wakeTrigger.Enabled      = $true
$wakeTrigger.Subscription = "<QueryList><Query Id='0' Path='System'><Select Path='System'>*[System[Provider[@Name='Microsoft-Windows-Power-Troubleshooter'] and EventID=1]]</Select></Query></QueryList>"
$wakeTrigger.ExecutionTimeLimit = "PT0S"

# Settings: restart on failure, run whenever triggered
$settings = New-ScheduledTaskSettingsSet `
                -ExecutionTimeLimit (New-TimeSpan -Minutes 5) `
                -RestartCount 3 `
                -RestartInterval (New-TimeSpan -Minutes 1) `
                -StartWhenAvailable `
                -MultipleInstances IgnoreNew

$principal = New-ScheduledTaskPrincipal `
                 -UserId $env:USERNAME `
                 -LogonType Interactive `
                 -RunLevel Limited

Register-ScheduledTask `
    -TaskName   $TaskName `
    -Action     $action `
    -Trigger    @($logonTrigger, $wakeTrigger) `
    -Settings   $settings `
    -Principal  $principal `
    -Description "Starts Hindsight pg0 Postgres (port 15432) and MCP server at logon and on wake from sleep. Handles stale postmaster.pid." | Out-Null

Write-Host "Registered task '$TaskName' (triggers: AtLogOn + OnWake)"
Write-Host "To start immediately: Start-ScheduledTask -TaskName '$TaskName'"
Write-Host "Log: $env:USERPROFILE\.hermes\logs\hindsight-start.log"
