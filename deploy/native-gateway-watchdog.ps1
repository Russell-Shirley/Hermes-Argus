# Hermes NATIVE Gateway Watchdog
# --------------------------------------------------------------------------
# Ensures the Windows-NATIVE Hermes gateway stays running.
# Replaces the old WSL-based deploy/watchdog.ps1 (task HermesGatewayWatchdog,
# now DISABLED). This watchdog NEVER touches WSL.
#
# Model: health-check (non-owning). It does not spawn/own the gateway via
# WaitForExit; it polls for a live native gateway process and, if absent for
# GraceChecks consecutive polls, relaunches it through the canonical
# Hermes_Gateway.vbs launcher (which sets HERMES_HOME + runs pythonw gateway run).
# This coexists with the Hermes_Gateway logon task without fighting it.
#
# Registered as scheduled task 'HermesNativeGatewayWatchdog' (AtLogon + 5-min heartbeat).
# --------------------------------------------------------------------------

$ErrorActionPreference = 'Continue'
$HermesHome  = "C:\Users\Russell\AppData\Local\hermes"
$Launcher    = "$HermesHome\gateway-service\Hermes_Gateway.vbs"
$LogFile     = "$HermesHome\logs\native-gateway-watchdog.log"
$PollSec     = 30    # health poll interval
$GraceChecks = 2     # consecutive down-polls before we relaunch (covers boot/restart windows)
$BootWaitSec = 75    # pause after a relaunch so the gateway can connect before we re-check

function Write-Log($m) {
    $ts = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
    try { Add-Content -Path $LogFile -Value "$ts  $m" } catch {}
    Write-Host "$ts  $m"
}

function Test-GatewayAlive {
    # A live native gateway is a python/pythonw process running "hermes_cli.main gateway run".
    $p = Get-CimInstance Win32_Process -Filter "Name='pythonw.exe' OR Name='python.exe'" -ErrorAction SilentlyContinue |
         Where-Object { $_.CommandLine -match 'hermes_cli\.main\s+gateway\s+run' }
    return [bool]$p
}

# --- Single-instance guard (named OS mutex) ---
$mutex = New-Object System.Threading.Mutex($false, 'Global\HermesNativeGatewayWatchdog')
if (-not $mutex.WaitOne(0)) {
    Write-Log 'Another native watchdog instance holds the mutex -- exiting.'
    exit 0
}

Write-Log '=== Native gateway watchdog started ==='
$down = 0
while ($true) {
    if (Test-GatewayAlive) {
        if ($down -gt 0) { Write-Log 'Gateway healthy again.' }
        $down = 0
    } else {
        $down++
        Write-Log "Native gateway not detected (strike $down/$GraceChecks)."
        if ($down -ge $GraceChecks) {
            if (-not (Test-Path $Launcher)) {
                Write-Log "ERROR: launcher missing at $Launcher -- cannot relaunch."
            } else {
                Write-Log "Relaunching native gateway via $Launcher"
                try {
                    Start-Process -FilePath 'wscript.exe' `
                        -ArgumentList '//B', '//Nologo', "`"$Launcher`"" `
                        -WindowStyle Hidden
                    Write-Log "Launch issued; pausing ${BootWaitSec}s for boot/connect."
                } catch {
                    Write-Log "Launch FAILED: $_"
                }
            }
            $down = 0
            Start-Sleep -Seconds $BootWaitSec
            continue
        }
    }
    Start-Sleep -Seconds $PollSec
}
