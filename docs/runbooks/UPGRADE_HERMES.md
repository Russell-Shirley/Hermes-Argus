# Upgrading hermes-agent on Windows

The Hermes gateway runs natively on Windows out of the user-local Python 3.13
Store install:

```
%USERPROFILE%\AppData\Local\Packages\PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0\LocalCache\local-packages\Python313\Scripts\hermes.exe
```

It is supervised by the `HermesGatewayWatchdog` Task Scheduler task
(`deploy/watchdog.ps1`), which restarts it on crash, logon, and system wake.

## Why this needs a separate script

Argus cannot upgrade himself directly:

- `hermes gateway stop` does not work on Windows (see Known Issues in
  `CURRENT_STATE.md`).
- Even after `Stop-Process`, the watchdog will relaunch `hermes.exe` within
  5 seconds, locking the files `pip` needs to replace.
- The gateway process holds open file handles inside the `Scripts\` directory.
  `pip install --upgrade` fails with a `WinError 5` / file-lock error if any
  hermes process is alive.

`deploy/upgrade-hermes.ps1` quiesces the watchdog, backs up `~/.hermes`,
kills the gateway, runs `pip install --upgrade`, runs `hermes config migrate`,
and re-enables the watchdog - in a `try/finally` so the watchdog always comes
back up.

## Prerequisites

- An elevated PowerShell window that is NOT a Hermes subprocess (i.e., open
  a fresh PowerShell as the same user; do not invoke this through the agent).
- `D:\` drive is optional - the pre-upgrade snapshot goes to
  `$env:USERPROFILE\.hermes-backups\<timestamp>\`.
- Network access to PyPI.

## Normal run

```powershell
cd $env:USERPROFILE\Documents\GitHub\Hermes-Argus
.\deploy\upgrade-hermes.ps1
```

You'll be prompted to confirm. The script prints each step with timestamps.
Typical wall-clock time: 60-120s.

## Dry run (no changes)

```powershell
.\deploy\upgrade-hermes.ps1 -DryRun
```

Prints exactly what it would do without disabling the watchdog or touching
pip.

## Pin a specific version

```powershell
.\deploy\upgrade-hermes.ps1 -Version 0.11.2
```

Useful for reproducing a known-good build or rolling back after a bad
upgrade.

## Unattended (e.g. from another script)

```powershell
.\deploy\upgrade-hermes.ps1 -Yes
```

## What it backs up

The script runs `robocopy` with the same exclusions as the nightly
`scripts/backup-to-d.ps1`:

- Included: `config.yaml`, `cron/jobs.json`, profile directories under
  `profiles/`, `skills/`, `.env`, `gateway_state.json` (frozen at the moment
  before stop).
- Excluded: `cache/`, `logs/`, `bin/`, `*.pid`, `*.lock`.

Each backup directory also gets an `upgrade-manifest.json` with the
pre-upgrade version and a ready-to-paste rollback command.

## Rollback

If the new version misbehaves, the manifest in the backup directory tells you
exactly what to do. Manual procedure:

```powershell
# 1. Stop the watchdog so it won't relaunch mid-rollback
Disable-ScheduledTask -TaskName 'HermesGatewayWatchdog'
Stop-ScheduledTask    -TaskName 'HermesGatewayWatchdog'

# 2. Stop the running gateway
# Note: $PID is a read-only automatic variable in PowerShell - use a different name.
$gwPid = (Get-Content "$env:USERPROFILE\.hermes\gateway_state.json" | ConvertFrom-Json).pid
Stop-Process -Id $gwPid -Force

# 3. Restore ~/.hermes from the snapshot
$snap = "$env:USERPROFILE\.hermes-backups\<timestamp>"
robocopy $snap "$env:USERPROFILE\.hermes" /E /MIR /XD cache logs

# 4. Pin the old hermes-agent version (exact command is in upgrade-manifest.json)
python3.13 -m pip install --force-reinstall hermes-agent==<old-version>

# 5. Re-enable the watchdog
Enable-ScheduledTask -TaskName 'HermesGatewayWatchdog'
Start-ScheduledTask  -TaskName 'HermesGatewayWatchdog'
```

## Common failures

| Symptom | Cause | Fix |
|---|---|---|
| `Gateway processes still running after 30s` | A non-watchdog process is keeping hermes alive (manual `hermes gateway run`, IDE debug session, etc.). | Find it: `Get-CimInstance Win32_Process \| Where-Object { $_.CommandLine -match 'hermes' }`, kill it, re-run. |
| `pip install` ends with `WinError 5` | A hermes process was missed and is still holding a file lock. | Re-run the script. The stop sweep has another go. |
| Watchdog task missing | First-time setup or task was unregistered. | Run `deploy\register-watchdog.ps1` first, then re-run the upgrade. |
| `hermes config migrate not present in this version` | The subcommand was added later; not all versions ship it. | Not an error - the script logs a warning and continues. |
| Watchdog stays disabled after a failure mid-upgrade | This should not happen - the `finally` block re-enables it. If it does, run: `Enable-ScheduledTask -TaskName 'HermesGatewayWatchdog'; Start-ScheduledTask -TaskName 'HermesGatewayWatchdog'`. | |

## Verification after a successful run

```powershell
# Version bumped
& "$env:USERPROFILE\AppData\Local\Packages\PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0\LocalCache\local-packages\Python313\Scripts\hermes.exe" --version

# Gateway is back
Get-Content "$env:USERPROFILE\.hermes\gateway_state.json" | ConvertFrom-Json

# Watchdog is enabled and running
Get-ScheduledTask -TaskName 'HermesGatewayWatchdog' | Select-Object TaskName, State

# Recent watchdog log
Get-Content "$env:USERPROFILE\.hermes\logs\watchdog.log" -Tail 20
```

If Slack delivery is your acceptance test, send a DM to Argus in
`#biz-bridgeandbolt` and confirm 👀 → ✅ reaction sequence.
