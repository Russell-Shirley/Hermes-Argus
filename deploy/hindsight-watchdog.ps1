# Hindsight Watchdog
# Monitors the Hindsight MCP API (port 8888) and restarts the full stack
# via hindsight-start.ps1 when it goes down.
# Registered as a Windows Task Scheduler task via deploy/register-hindsight-watchdog.ps1
#
# Uses exponential backoff on repeated restart failures so a sustained
# boot-loop slows to 5-minute retries rather than hammering the stack.

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

function Test-Port($port) {
    return ($null -ne (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue))
}

Write-Log "=== Hindsight watchdog started ==="

# Single-instance guard via named OS mutex (atomic, no race condition).
# Mirrors the pattern in watchdog.ps1 for the Hermes gateway.
$mutex    = New-Object System.Threading.Mutex($false, "Global\HermesHindsightWatchdog")
$acquired = $mutex.WaitOne(0)
if (-not $acquired) {
    Write-Log "Another Hindsight watchdog holds the mutex -- exiting."
    exit 0
}

$delaySec = $MinDelaySec

while ($true) {
    if (Test-Port $ApiPort) {
        Start-Sleep -Seconds $PollSec
        continue
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
        Start-Sleep -Seconds $PollSec
    }
}

Write-Log "=== Hindsight watchdog exiting (should never reach here) ==="
