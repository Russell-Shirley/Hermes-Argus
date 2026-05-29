# Registers the Hermes watchdog as a Windows Task Scheduler task.
# Run once as the logged-in user (no elevation required).
# Triggers: AtLogon + OnWake + 5-minute heartbeat (self-heals if watchdog exits between events).

$TaskName    = "HermesGatewayWatchdog"
$ScriptPath  = "$env:USERPROFILE\Documents\GitHub\Hermes-Argus\deploy\watchdog.ps1"
$PwshExe     = "powershell.exe"

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
$wakeTrigger.Enabled = $true
$wakeTrigger.Subscription = "<QueryList><Query Id='0' Path='System'><Select Path='System'>*[System[Provider[@Name='Microsoft-Windows-Power-Troubleshooter'] and EventID=1]]</Select></Query></QueryList>"
$wakeTrigger.ExecutionTimeLimit = "PT0S"

# Trigger 3: heartbeat every 5 minutes — self-heals if watchdog exits between logon/wake events.
# MultipleInstances=IgnoreNew (set below) prevents double-launch when it's already running.
$heartbeatTrigger = New-ScheduledTaskTrigger `
    -Once `
    -At (Get-Date).Date `
    -RepetitionInterval (New-TimeSpan -Minutes 5) `
    -RepetitionDuration ([TimeSpan]::MaxValue)

# Settings: restart on failure, run indefinitely
$settings = New-ScheduledTaskSettingsSet `
                -ExecutionTimeLimit (New-TimeSpan -Days 365) `
                -RestartCount 99 `
                -RestartInterval (New-TimeSpan -Minutes 1) `
                -MultipleInstances IgnoreNew `
                -StartWhenAvailable `
                -RunOnlyIfNetworkAvailable

$principal = New-ScheduledTaskPrincipal `
                 -UserId $env:USERNAME `
                 -LogonType Interactive `
                 -RunLevel Limited

Register-ScheduledTask `
    -TaskName  $TaskName `
    -Action    $action `
    -Trigger   @($logonTrigger, $wakeTrigger, $heartbeatTrigger) `
    -Settings  $settings `
    -Principal $principal `
    -Description "Hermes gateway watchdog - restarts on crash, logon, system wake, and 5-min heartbeat" | Out-Null

Write-Host "Registered task '$TaskName' (triggers: AtLogon + OnWake + 5-min heartbeat)"
Write-Host "To start immediately: Start-ScheduledTask -TaskName '$TaskName'"
