# Hindsight Watchdog
# Monitors the Hindsight MCP API (port 8888) and restarts the full stack
# via hindsight-start.ps1 when it goes down.
# Registered as a Windows Task Scheduler task via deploy/register-hindsight-watchdog.ps1
#
# Uses exponential backoff on repeated restart failures so a sustained
# boot-loop slows to 5-minute retries rather than hammering the stack.
# Posts to Slack #biz-bridgeandbolt when the daemon goes down and when it recovers.

$StartScript = "$env:USERPROFILE\Documents\GitHub\Hermes-Argus\deploy\hindsight-start.ps1"
$ApiPort     = 8888
$WatchdogLog = "$env:USERPROFILE\.hermes\logs\hindsight-watchdog.log"
$PollSec     = 30    # how often to poll when the stack is healthy
$MinDelaySec = 10    # initial backoff after a failed restart
$MaxDelaySec = 300   # 5-minute cap during sustained failure loops

function Write-Log($msg) {
    $ts   = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    $line = "$ts  $msg"
    Add-Content -Path $WatchdogLog -Value $line
    Write-Host $line
}

function Get-SlackToken {
    if ($env:SLACK_BOT_TOKEN) { return $env:SLACK_BOT_TOKEN }
    $EnvFile = Join-Path $PSScriptRoot "..\cognee-server\.env"
    if (Test-Path $EnvFile) {
        $Line = Get-Content $EnvFile | Where-Object { $_ -match "^SLACK_BOT_TOKEN=" } | Select-Object -First 1
        if ($Line) { return $Line.Split("=", 2)[1].Trim() }
    }
    return $null
}

function Send-SlackAlert {
    param([Parameter(Mandatory)][string]$Text, [string]$Channel = "#biz-bridgeandbolt")
    $Token = Get-SlackToken
    if (-not $Token) {
        Write-Log "SLACK_BOT_TOKEN not found -- alert suppressed: $Text"
        return
    }
    $Body = (@{ channel = $Channel; text = $Text } | ConvertTo-Json -Compress)
    try {
        Invoke-RestMethod -Uri "https://slack.com/api/chat.postMessage" -Method Post `
            -ContentType "application/json; charset=utf-8" `
            -Headers @{ Authorization = "Bearer $Token" } `
            -Body $Body | Out-Null
    } catch {
        Write-Log "Slack post failed: $($_.Exception.Message)"
    }
}

function Test-Port($port) {
    return ($null -ne (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue))
}

Write-Log "=== Hindsight watchdog started ==="

# Single-instance guard via named OS mutex (atomic, no race condition).
$mutex    = New-Object System.Threading.Mutex($false, "Global\HermesHindsightWatchdog")
$acquired = $mutex.WaitOne(0)
if (-not $acquired) {
    Write-Log "Another Hindsight watchdog holds the mutex -- exiting."
    exit 0
}

$delaySec    = $MinDelaySec
$alertedDown = $false   # avoid repeated "down" alerts during backoff loop

while ($true) {
    if (Test-Port $ApiPort) {
        if ($alertedDown) {
            Write-Log "Hindsight recovered on port $ApiPort -- sending recovery alert"
            Send-SlackAlert ":white_check_mark: *Hindsight recovered* -- MCP API back on port $ApiPort."
            $alertedDown = $false
        }
        $delaySec = $MinDelaySec
        Start-Sleep -Seconds $PollSec
        continue
    }

    # Port is down
    if (-not $alertedDown) {
        $ts = (Get-Date).ToString("HH:mm")
        Write-Log "Port $ApiPort not listening -- sending down alert"
        Send-SlackAlert ":rotating_light: *Hindsight is DOWN* -- MCP API not listening on port $ApiPort at $ts. Attempting restart..."
        $alertedDown = $true
    }

    Write-Log "Port $ApiPort not listening -- invoking hindsight-start.ps1..."
    & powershell.exe -NonInteractive -ExecutionPolicy Bypass -File $StartScript
    $exitCode = $LASTEXITCODE

    if ($exitCode -ne 0) {
        Write-Log "hindsight-start.ps1 exited $exitCode -- backoff ${delaySec}s"
        $delaySec = [Math]::Min($delaySec * 2, $MaxDelaySec)
        Start-Sleep -Seconds $delaySec
    } elseif (-not (Test-Port $ApiPort)) {
        Write-Log "hindsight-start.ps1 succeeded but port $ApiPort still not up -- backoff ${delaySec}s"
        $delaySec = [Math]::Min($delaySec * 2, $MaxDelaySec)
        Start-Sleep -Seconds $delaySec
    } else {
        Write-Log "Hindsight back up on port $ApiPort -- backoff reset"
        $delaySec = $MinDelaySec
        # Recovery alert fires at top of next loop when Test-Port succeeds
        Start-Sleep -Seconds $PollSec
    }
}

Write-Log "=== Hindsight watchdog exiting (should never reach here) ==="
