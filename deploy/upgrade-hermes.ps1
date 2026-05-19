#Requires -Version 5.1
<#
.SYNOPSIS
    Upgrade hermes-agent on Windows with backup, watchdog quiescing, and config migrate.

.DESCRIPTION
    Solves the "Argus can't upgrade himself" problem. A separate process (this
    script) does what the gateway can't do for itself:

      1. Disables and stops the HermesGatewayWatchdog Task Scheduler task so it
         won't relaunch the gateway mid-upgrade.
      2. Snapshots $env:USERPROFILE\.hermes (config, profiles, cron, secrets,
         skills) to $env:USERPROFILE\.hermes-backups\<timestamp>\ via robocopy.
         Records the pre-upgrade hermes-agent version in upgrade-manifest.json
         inside the backup directory.
      3. Stops the running gateway via Stop-Process on the PID from
         gateway_state.json (the documented Windows-safe stop pattern - see
         CURRENT_STATE.md "hermes gateway stop fails on Windows").
      4. Runs pip install --upgrade hermes-agent against the Windows Python
         that owns the installed hermes.exe shim (NOT WSL). PyPI by default.
      5. Runs `hermes config migrate` if the subcommand exists in the new
         version.
      6. Re-enables and starts the watchdog so it relaunches the gateway.
      7. Tails watchdog.log briefly to confirm the gateway came back up.

    Always re-enables the watchdog in a finally block - even on failure - so
    the gateway is never left orphaned with the watchdog disabled.

    Run from an elevated PowerShell window that is NOT the gateway's own
    process tree. Do not invoke this from inside Hermes (Argus cannot stop
    himself - that is the whole point of this script).

.PARAMETER Version
    Pin to a specific hermes-agent version, e.g. -Version 0.11.2.
    Default: latest from PyPI.

.PARAMETER SkipBackup
    Skip the ~/.hermes snapshot. Only for emergencies - disaster recovery
    becomes much harder without the pre-upgrade snapshot.

.PARAMETER NoMigrate
    Skip `hermes config migrate` after pip upgrade. Use if migrate is known
    broken for the target version.

.PARAMETER DryRun
    Print what would happen without changing anything. Watchdog stays running,
    no files are written, no pip is invoked.

.PARAMETER Yes
    Skip the interactive "proceed?" confirmation. For unattended runs.

.EXAMPLE
    .\deploy\upgrade-hermes.ps1

.EXAMPLE
    .\deploy\upgrade-hermes.ps1 -Version 0.11.2

.EXAMPLE
    .\deploy\upgrade-hermes.ps1 -DryRun
#>

[CmdletBinding()]
param(
    [string]$Version,
    [switch]$SkipBackup,
    [switch]$NoMigrate,
    [switch]$DryRun,
    [switch]$Yes
)

$ErrorActionPreference = "Stop"

# -- Constants ----------------------------------------------------------------
# Paths mirror deploy/watchdog.ps1 - keep these in sync if the Hermes install
# location changes.
$HermesExe        = "$env:USERPROFILE\AppData\Local\Packages\PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0\LocalCache\local-packages\Python313\Scripts\hermes.exe"
$HermesHome       = "$env:USERPROFILE\.hermes"
$GatewayStateFile = "$HermesHome\gateway_state.json"
$WatchdogLog      = "$HermesHome\logs\watchdog.log"
$WatchdogTaskName = "HermesGatewayWatchdog"
$BackupRoot       = "$env:USERPROFILE\.hermes-backups"
$Timestamp        = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$BackupDir        = "$BackupRoot\$Timestamp"
$ManifestFile     = "$BackupDir\upgrade-manifest.json"

# -- Helpers ------------------------------------------------------------------
function Write-Step {
    param([string]$Msg, [string]$Level = "INFO")
    $ts = (Get-Date).ToString("HH:mm:ss")
    $prefix = switch ($Level) {
        "WARN"  { "[$ts] WARN " }
        "ERROR" { "[$ts] ERROR" }
        "OK"    { "[$ts] OK   " }
        default { "[$ts] >    " }
    }
    Write-Host "$prefix $Msg"
}

function Confirm-Proceed {
    param([string]$Prompt)
    if ($Yes) { return $true }
    $ans = Read-Host "$Prompt [y/N]"
    return $ans -match '^[Yy]'
}

function Resolve-PythonExe {
    # Resolve the Python interpreter that owns the installed hermes.exe shim.
    # The Store-installed Python 3.13 lives behind WindowsApps aliases; we
    # prefer python3.13, then python3, then the `py` launcher, then the
    # WindowsApps alias directly.
    $candidates = @(
        @{ Cmd = "python3.13"; Args = @() },
        @{ Cmd = "python3";    Args = @() },
        @{ Cmd = "py";         Args = @("-3.13") },
        @{ Cmd = "$env:USERPROFILE\AppData\Local\Microsoft\WindowsApps\python3.13.exe"; Args = @() }
    )
    foreach ($c in $candidates) {
        $found = Get-Command $c.Cmd -ErrorAction SilentlyContinue
        if ($found) {
            return @{ Exe = $found.Source; Args = $c.Args }
        }
    }
    throw "No Python 3.13 interpreter found. Tried: python3.13, python3, py -3.13, WindowsApps alias."
}

function Invoke-Py {
    # Wrap `& $Py.Exe ...` so callers don't have to remember PowerShell's
    # splatting rules. `@argList` (the splat operator on a variable) expands
    # the array into individual positional args; `@(...)` (the array
    # subexpression) does not and passes a single array argument.
    param($Py, [string[]]$Extra)
    $argList = @() + $Py.Args + $Extra
    & $Py.Exe @argList
}

function Get-InstalledHermesVersion {
    param($Py)
    try {
        $pipOut = Invoke-Py -Py $Py -Extra @("-m", "pip", "show", "hermes-agent") 2>&1
        $line = $pipOut | Where-Object { $_ -match '^Version:' } | Select-Object -First 1
        if ($line) { return ($line -replace '^Version:\s*', '').Trim() }
    } catch {}
    return "unknown"
}

function Stop-Watchdog {
    if ($DryRun) {
        Write-Step "DRY: would disable + stop scheduled task '$WatchdogTaskName'"
        return $true
    }
    $task = Get-ScheduledTask -TaskName $WatchdogTaskName -ErrorAction SilentlyContinue
    if (-not $task) {
        Write-Step "Watchdog task '$WatchdogTaskName' not registered - nothing to disable" "WARN"
        return $false
    }
    Write-Step "Disabling scheduled task '$WatchdogTaskName'"
    Disable-ScheduledTask -TaskName $WatchdogTaskName | Out-Null

    # Stop-ScheduledTask kills the currently running task instance (the
    # powershell.exe running watchdog.ps1). Without this the watchdog process
    # keeps running its restart loop until its current gateway child exits.
    Write-Step "Stopping any running instance of '$WatchdogTaskName'"
    Stop-ScheduledTask -TaskName $WatchdogTaskName -ErrorAction SilentlyContinue

    # Belt and suspenders: kill any leftover powershell.exe hosting watchdog.ps1.
    Get-CimInstance Win32_Process -Filter "Name = 'powershell.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -and $_.CommandLine -match 'watchdog\.ps1' } |
        ForEach-Object {
            Write-Step "Killing leftover watchdog host PID $($_.ProcessId)"
            Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
        }
    return $true
}

function Start-Watchdog {
    if ($DryRun) {
        Write-Step "DRY: would re-enable + start scheduled task '$WatchdogTaskName'"
        return
    }
    $task = Get-ScheduledTask -TaskName $WatchdogTaskName -ErrorAction SilentlyContinue
    if (-not $task) {
        Write-Step "Watchdog task missing - cannot re-enable. Run deploy\register-watchdog.ps1." "ERROR"
        return
    }
    Write-Step "Re-enabling scheduled task '$WatchdogTaskName'"
    Enable-ScheduledTask -TaskName $WatchdogTaskName | Out-Null
    Write-Step "Starting scheduled task '$WatchdogTaskName'"
    Start-ScheduledTask -TaskName $WatchdogTaskName
}

function Stop-Gateway {
    $pid_ = $null
    if (Test-Path $GatewayStateFile) {
        try {
            $state = Get-Content $GatewayStateFile -Raw | ConvertFrom-Json
            $pid_ = $state.pid
        } catch {
            Write-Step "Could not parse $GatewayStateFile : $($_.Exception.Message)" "WARN"
        }
    }

    if ($pid_) {
        $proc = Get-Process -Id $pid_ -ErrorAction SilentlyContinue
        if ($proc) {
            if ($DryRun) {
                Write-Step "DRY: would Stop-Process -Id $pid_ -Force (name=$($proc.ProcessName))"
            } else {
                Write-Step "Stopping gateway PID $pid_ ($($proc.ProcessName))"
                Stop-Process -Id $pid_ -Force -ErrorAction SilentlyContinue
            }
        } else {
            Write-Step "Gateway PID $pid_ from state file is no longer running"
        }
    } else {
        Write-Step "No PID recorded in $GatewayStateFile - skipping targeted stop" "WARN"
    }

    # Sweep any stragglers. hermes.exe is the Scripts shim; the actual process
    # name is usually 'hermes' or 'python' depending on how the shim resolved.
    # Match by command line containing 'hermes' AND 'gateway' to avoid killing
    # unrelated Python processes.
    if (-not $DryRun) {
        Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
            Where-Object {
                $_.CommandLine -and
                $_.CommandLine -match 'hermes' -and
                $_.CommandLine -match '\bgateway\b' -and
                $_.ProcessId -ne $PID
            } |
            ForEach-Object {
                Write-Step "Killing stray gateway process PID $($_.ProcessId): $($_.CommandLine)"
                Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
            }
    }

    # Wait up to 30s for processes to exit. pip can't replace a locked .exe.
    if (-not $DryRun) {
        $deadline = (Get-Date).AddSeconds(30)
        while ((Get-Date) -lt $deadline) {
            $stillRunning = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
                Where-Object {
                    $_.CommandLine -and
                    $_.CommandLine -match 'hermes' -and
                    $_.CommandLine -match '\bgateway\b'
                }
            if (-not $stillRunning) { break }
            Start-Sleep -Milliseconds 500
        }
        $stillRunning = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
            Where-Object {
                $_.CommandLine -and
                $_.CommandLine -match 'hermes' -and
                $_.CommandLine -match '\bgateway\b'
            }
        if ($stillRunning) {
            throw "Gateway processes still running after 30s - aborting before pip would fail with file lock."
        }
    }
}

function Backup-HermesHome {
    if ($SkipBackup) {
        Write-Step "Backup skipped (-SkipBackup). Rollback path is much harder." "WARN"
        return $null
    }
    if (-not (Test-Path $HermesHome)) {
        Write-Step "$HermesHome does not exist - nothing to back up" "WARN"
        return $null
    }
    if ($DryRun) {
        Write-Step "DRY: would robocopy $HermesHome -> $BackupDir"
        return $BackupDir
    }
    New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null

    # Mirror exclusions from backup-to-d.ps1 - cache, logs, bin are bulky and
    # not needed for rollback.
    $robocopyArgs = @(
        $HermesHome, $BackupDir,
        "/E",                       # subdirectories including empty ones
        "/COPY:DAT",                # data, attributes, timestamps
        "/R:2", "/W:2",             # 2 retries, 2s wait
        "/XD", "cache", "logs", "bin",
        "/XF", "*.pid", "*.lock",
        "/NFL", "/NDL", "/NJH", "/NP"
    )
    Write-Step "Robocopy $HermesHome -> $BackupDir (excluding cache/logs/bin)"
    & robocopy @robocopyArgs | Out-Null
    # Robocopy uses bitmapped exit codes; 0-7 are success, 8+ are failure.
    if ($LASTEXITCODE -ge 8) {
        throw "robocopy failed with exit code $LASTEXITCODE"
    }
    return $BackupDir
}

function Write-Manifest {
    param(
        [string]$OldVersion,
        [string]$TargetSpec,
        $Py
    )
    if ($DryRun -or $SkipBackup -or -not (Test-Path $BackupDir)) { return }
    $manifest = [ordered]@{
        timestamp        = $Timestamp
        hermes_exe       = $HermesExe
        python_exe       = $Py.Exe
        python_args      = $Py.Args
        pre_upgrade_ver  = $OldVersion
        target_spec      = $TargetSpec
        hermes_home_src  = $HermesHome
        backup_dir       = $BackupDir
        rollback_command = "& '$($Py.Exe)' $($Py.Args -join ' ') -m pip install --force-reinstall hermes-agent==$OldVersion"
    }
    $manifest | ConvertTo-Json -Depth 5 | Set-Content -Path $ManifestFile -Encoding UTF8
    Write-Step "Wrote upgrade manifest $ManifestFile" "OK"
}

function Invoke-PipUpgrade {
    param($Py, [string]$Spec)
    $extra = @("-m", "pip", "install", "--upgrade", "--user", $Spec)
    if ($DryRun) {
        Write-Step "DRY: would run: $($Py.Exe) $(($Py.Args + $extra) -join ' ')"
        return
    }
    Write-Step "Running: $($Py.Exe) $(($Py.Args + $extra) -join ' ')"
    Invoke-Py -Py $Py -Extra $extra
    if ($LASTEXITCODE -ne 0) {
        throw "pip install exited $LASTEXITCODE"
    }
}

function Invoke-ConfigMigrate {
    if ($NoMigrate) {
        Write-Step "Skipping config migrate (-NoMigrate)" "WARN"
        return
    }
    if ($DryRun) {
        Write-Step "DRY: would run: $HermesExe config migrate"
        return
    }
    if (-not (Test-Path $HermesExe)) {
        Write-Step "$HermesExe missing after upgrade - cannot run migrate" "ERROR"
        return
    }

    # Probe for the subcommand. Older hermes-agent versions did not ship
    # `config migrate`; if it's not there, log and continue rather than fail.
    $help = & $HermesExe config --help 2>&1
    if ($help -notmatch 'migrate') {
        Write-Step "hermes config migrate not present in this version - skipping" "WARN"
        return
    }
    Write-Step "Running: hermes config migrate"
    & $HermesExe config migrate
    if ($LASTEXITCODE -ne 0) {
        throw "hermes config migrate exited $LASTEXITCODE"
    }
}

function Test-PostUpgradeHealth {
    if ($DryRun) {
        Write-Step "DRY: would tail watchdog.log and check gateway PID"
        return
    }
    Write-Step "Watching $WatchdogLog for gateway restart (30s)..."
    $deadline = (Get-Date).AddSeconds(30)
    $sawLaunch = $false
    while ((Get-Date) -lt $deadline) {
        if (Test-Path $WatchdogLog) {
            $recent = Get-Content $WatchdogLog -Tail 20 -ErrorAction SilentlyContinue
            if ($recent -match 'Gateway PID \d+ launched') {
                $sawLaunch = $true
                break
            }
        }
        Start-Sleep -Seconds 2
    }
    if ($sawLaunch) {
        Write-Step "Watchdog reports gateway launched" "OK"
    } else {
        Write-Step "Did not observe gateway launch in 30s - inspect $WatchdogLog manually" "WARN"
    }

    if (Test-Path $GatewayStateFile) {
        try {
            $state = Get-Content $GatewayStateFile -Raw | ConvertFrom-Json
            $proc = Get-Process -Id $state.pid -ErrorAction SilentlyContinue
            if ($proc) {
                Write-Step "Gateway PID $($state.pid) is running" "OK"
            } else {
                Write-Step "gateway_state.json PID $($state.pid) not running" "WARN"
            }
        } catch {
            Write-Step "Could not read $GatewayStateFile : $($_.Exception.Message)" "WARN"
        }
    }
}

# -- Main ---------------------------------------------------------------------
Write-Host ""
Write-Host "=== Hermes-Argus Upgrade ==="
Write-Host "  hermes.exe       : $HermesExe"
Write-Host "  ~/.hermes        : $HermesHome"
Write-Host "  Backup dir       : $BackupDir"
Write-Host "  Target version   : $(if ($Version) { $Version } else { 'latest (PyPI)' })"
Write-Host "  Dry run          : $DryRun"
Write-Host "  Skip backup      : $SkipBackup"
Write-Host "  Skip migrate     : $NoMigrate"
Write-Host ""

if (-not (Test-Path $HermesExe)) {
    throw "hermes.exe not found at $HermesExe. Adjust the constant at the top of this script or install hermes-agent first."
}

$py = Resolve-PythonExe
Write-Step "Using Python: $($py.Exe) $($py.Args -join ' ')"

$oldVersion = Get-InstalledHermesVersion -Py $py
Write-Step "Pre-upgrade hermes-agent version: $oldVersion"

$spec = if ($Version) { "hermes-agent==$Version" } else { "hermes-agent" }

if (-not $DryRun -and -not (Confirm-Proceed "Proceed with upgrade?")) {
    Write-Step "Aborted by user."
    return
}

$watchdogWasStopped = $false
try {
    $watchdogWasStopped = Stop-Watchdog
    Stop-Gateway
    $backupPath = Backup-HermesHome
    Write-Manifest -OldVersion $oldVersion -TargetSpec $spec -Py $py
    Invoke-PipUpgrade -Py $py -Spec $spec
    $newVersion = Get-InstalledHermesVersion -Py $py
    Write-Step "Post-pip hermes-agent version: $newVersion" "OK"
    if ($newVersion -eq $oldVersion -and -not $Version) {
        Write-Step "Version unchanged after upgrade - already on latest, or PyPI unreachable" "WARN"
    }
    Invoke-ConfigMigrate
}
finally {
    # ALWAYS re-enable the watchdog so the gateway is never orphaned, even if
    # pip or migrate failed. If watchdog wasn't registered to begin with, this
    # is a no-op that logs a warning.
    if ($watchdogWasStopped -or $DryRun) {
        Start-Watchdog
    }
}

Test-PostUpgradeHealth

Write-Host ""
Write-Step "=== Upgrade complete ===" "OK"
if (-not $DryRun -and -not $SkipBackup -and (Test-Path $ManifestFile)) {
    Write-Host ""
    Write-Host "Rollback:"
    Write-Host "  1. Stop the watchdog:   Disable-ScheduledTask -TaskName '$WatchdogTaskName'; Stop-ScheduledTask -TaskName '$WatchdogTaskName'"
    Write-Host "  2. Stop the gateway:    Stop-Process -Id (Get-Content '$GatewayStateFile' | ConvertFrom-Json).pid -Force"
    Write-Host "  3. Restore .hermes:     robocopy '$BackupDir' '$HermesHome' /E /MIR /XD cache logs"
    Write-Host "  4. Pin old hermes-agent: see rollback_command in $ManifestFile"
    Write-Host "  5. Re-enable watchdog:  Enable-ScheduledTask -TaskName '$WatchdogTaskName'; Start-ScheduledTask -TaskName '$WatchdogTaskName'"
}
