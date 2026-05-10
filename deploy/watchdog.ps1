# Hermes Gateway Watchdog
# Starts the gateway and restarts it automatically on crash.
# Registered as a Windows Task Scheduler task via deploy/register-watchdog.ps1
#
# Root cause mitigated: MCP discovery's future.result(timeout=120) raises an
# uncaught TimeoutError that kills the gateway. Watchdog auto-restarts it.

$HermesExe       = "$env:USERPROFILE\AppData\Local\Packages\PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0\LocalCache\local-packages\Python313\Scripts\hermes.exe"
$WatchdogLog     = "$env:USERPROFILE\.hermes\logs\watchdog.log"
$RestartDelaySec = 5
$MaxRestarts     = 200

$env:PYTHONIOENCODING = "utf-8"

function Write-Log($msg) {
    $ts = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    $line = "$ts  $msg"
    Add-Content -Path $WatchdogLog -Value $line
    Write-Host $line
}

Write-Log "=== Watchdog started ==="

$restarts = 0

while ($restarts -le $MaxRestarts) {
    Write-Log "Starting gateway (attempt $($restarts + 1))..."

    $proc = Start-Process -FilePath $HermesExe `
                          -ArgumentList "gateway", "run" `
                          -WindowStyle Hidden `
                          -PassThru

    Write-Log "Gateway PID $($proc.Id) launched"

    $proc.WaitForExit()
    $exitCode = $proc.ExitCode

    Write-Log "Gateway PID $($proc.Id) exited with code $exitCode"

    if ($restarts -ge $MaxRestarts) {
        Write-Log "ERROR: hit restart ceiling ($MaxRestarts). Stopping watchdog."
        break
    }

    $restarts++
    Write-Log "Restarting in ${RestartDelaySec}s..."
    Start-Sleep -Seconds $RestartDelaySec
}

Write-Log "=== Watchdog exiting ==="
