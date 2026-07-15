# ============================================================================
# DEPRECATED (2026-07-14) — DO NOT USE. Superseded by native-gateway-watchdog.ps1
# ----------------------------------------------------------------------------
# This script launches the gateway inside WSL2. The gateway now runs
# WINDOWS-NATIVE, and running a WSL gateway alongside it makes both poll the
# same Telegram bot token -> 409 conflict + a --replace restart storm (this is
# exactly what took Telegram/Slack/Email down on 2026-07-14).
#
# The 'HermesGatewayWatchdog' scheduled task has been REPOINTED to
# native-gateway-watchdog.ps1 and this WSL watchdog is no longer invoked.
# Do NOT re-enable a WSL watchdog. Kept only for historical reference.
# See: native-gateway-watchdog.ps1 and memory project_windows_native_gateway.
# ============================================================================
#
# Hermes Gateway Watchdog (legacy WSL)
# Starts the gateway inside WSL2 and restarts it automatically on crash.
# Registered as a Windows Task Scheduler task via deploy/register-watchdog.ps1
#
# Uses exponential backoff on fast crashes (< 30s uptime) so a sustained
# boot-loop slows to 5-minute retries rather than burning through a hard ceiling.

$WslExe       = "wsl.exe"
$HermesCmd    = "/home/russell/.hermes/hermes-agent/venv/bin/hermes"
$WatchdogLog  = "$env:USERPROFILE\.hermes\logs\watchdog.log"
$MinDelaySec  = 5
$MaxDelaySec  = 300   # 5-minute cap during sustained crash loops
$FastCrashSec = 30    # uptime below this counts as a fast crash

$env:PYTHONIOENCODING = "utf-8"

function Write-Log($msg) {
    $ts   = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    $line = "$ts  $msg"
    Add-Content -Path $WatchdogLog -Value $line
    Write-Host $line
}

Write-Log "=== Watchdog started ==="

# Single-instance guard via named OS mutex (atomic, no race condition).
# First instance to start acquires the mutex and runs the loop.
# Any subsequent instance (e.g. background Claude agent sessions) fails to acquire,
# kicks the Task Scheduler task to ensure the real watchdog is running, and exits.
$mutex    = New-Object System.Threading.Mutex($false, "Global\HermesGatewayWatchdog")
$acquired = $mutex.WaitOne(0)
if (-not $acquired) {
    Write-Log "Another watchdog holds the mutex -- delegating to HermesGatewayWatchdog task and exiting."
    Start-ScheduledTask -TaskName "HermesGatewayWatchdog" -ErrorAction SilentlyContinue
    exit 0
}

$delaySec = $MinDelaySec
$attempt  = 0

while ($true) {
    $attempt++
    Write-Log "Starting gateway inside WSL2 (attempt $attempt)..."

    $startTime = Get-Date
    $proc = Start-Process -FilePath $WslExe `
                          -ArgumentList "-u", "russell", "--", $HermesCmd, "gateway", "run", "--replace" `
                          -WindowStyle Hidden `
                          -PassThru

    Write-Log "Gateway PID $($proc.Id) launched (wsl.exe host)"
    $proc.WaitForExit()
    $exitCode = $proc.ExitCode
    $uptime   = [int]((Get-Date) - $startTime).TotalSeconds

    Write-Log "Gateway wsl.exe PID $($proc.Id) exited (code=$exitCode uptime=${uptime}s)"

    if ($uptime -lt $FastCrashSec) {
        $delaySec = [Math]::Min($delaySec * 2, $MaxDelaySec)
        Write-Log "Fast crash -- backoff increased to ${delaySec}s"
    } else {
        $delaySec = $MinDelaySec
        Write-Log "Gateway ran $uptime s -- backoff reset to ${delaySec}s"
    }

    Write-Log "Restarting in ${delaySec}s..."
    Start-Sleep -Seconds $delaySec
}

Write-Log "=== Watchdog exiting (should never reach here) ==="
