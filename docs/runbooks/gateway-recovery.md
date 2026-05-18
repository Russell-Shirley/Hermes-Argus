---
name: Gateway Recovery
description: Recover the Hermes gateway after crash, watchdog kill, or Slack silence
type: runbook
date: 2026-05-14
severity: sev-1
last_drill: never
---

# Gateway Recovery

## Trigger
- Slack messages to Argus go unanswered for >5 minutes
- `backup_health_check` cron posts a failure alert
- Gateway watchdog alert fires

## Diagnosis

### 1. Is the gateway process running?
```powershell
# From Windows PowerShell
tasklist | findstr node
# OR check the last known PID from CURRENT-STATE.md
```
From WSL:
```bash
ps aux | grep hermes
```

### 2. Is the watchdog running?
```powershell
Get-ScheduledTask HermesGatewayWatchdog | Select-Object TaskName, State
```
- **Running** → watchdog is alive and will restart the gateway automatically; wait 60s then recheck
- **Ready/Disabled** → watchdog is stopped; proceed to recovery

### 3. Check the gateway logs
```bash
tail -50 ~/.hermes/logs/gateway.log
```
Look for:
- `RuntimeError` → executor shutdown (Discord cascade — but Discord is now disabled, so unlikely)
- `MCP TimeoutError` → MCP call exceeded 120s deadline
- `STATUS_CONTROL_C_EXIT` / `0xC000013A` → process killed by Windows sleep/hibernate

---

## Recovery

### Fast path — restart watchdog (preferred)
The watchdog will restart the gateway automatically once it is running:
```powershell
Start-ScheduledTask HermesGatewayWatchdog
```
Wait 30s, then verify:
```powershell
Get-ScheduledTask HermesGatewayWatchdog | Select-Object TaskName, State
```
Check WSL logs for `Gateway running with 1 platform(s)`.

### Manual path — restart gateway directly
If the watchdog itself is broken or not registered:
```bash
# From WSL
cd /mnt/c/Users/Russell/Documents/GitHub/Hermes-Argus
hermes start --config ~/.hermes/config.yaml
```
Confirm Slack reconnected:
```bash
grep "Gateway running" ~/.hermes/logs/gateway.log | tail -3
```
Expected: `Gateway running with 1 platform(s)` (Slack-only — Discord is intentionally disabled).

### Re-register watchdog (if task is missing)
```powershell
# From elevated PowerShell
deploy\register-watchdog.ps1
```

---

## Background: Known crash vectors

| Vector | Status | Notes |
|--------|--------|-------|
| Discord shard teardown → shared executor shutdown | **Mitigated** | Discord token cleared from config; gateway runs Slack-only |
| MCP TimeoutError (>120s) kills gateway | **Active risk** | No fix yet; watchdog is the recovery net |
| Windows sleep/hibernate kills watchdog (0xC000013A) | **Mitigated** | OnWake trigger added in PR #4 |

---

## Escalation
If gateway crashes repeatedly (>3 times in 1 hour):
1. Check which MCP call is timing out — likely Cognee; run [Cognee health check runbook](cognee-health-check.md)
2. Temporarily disable the offending MCP server in `~/.hermes/config.yaml`
3. Restart gateway without it

## Post-Incident
- Note the crash timestamp and log snippet in CURRENT-STATE.md
- If root cause is new, open a GitHub issue
- Run `Start-ScheduledTask HermesArgusBackup` if the outage spanned the 02:00 backup window
