# CURRENT STATE — Hermes-Argus

## Completed

- **Phase 1 complete** — personality, skills, .env mapped
- **Phase 2 complete** — Cognee + PostgreSQL wired to Hermes via MCP
  - `cognee-server/mcp_wrapper.py` — MCP stdio server (FastMCP) wrapping Cognee REST
  - Cognee HTTP transport **not supported** by Hermes v0.10 — stdio wrapper required
  - Hermes v0.10 does **not forward `cwd`** to MCP subprocesses; use absolute script path
  - MCP tools confirmed in Discord: `cognee__memorize`, `cognee__query`, `mcp_postgres_query`, etc.
  - Memorize → recall round-trip verified in Discord
  - `tests/test_integration.py` — 5/5 pass
- **Phase 3 complete** — PostgreSQL wired as structured brain
  - `schema/business.sql` — 8 core tables/views deployed
  - `tests/test_data_integrity.py` — 7/7 pass
  - AR aging view verified
  - Collection letter templates (3 types)
- **Phase 4 complete** — Multi-Agent Profiles with tool scoping
  - 3 profiles deployed: `ar_watcher`, `voucher_scanner`, `outreach_agent` (+ default)
  - Hermes v0.10 profile architecture: each profile is an independent `HERMES_HOME` directory under `~/.hermes/profiles/<name>/`
  - Profile deployment via `hermes profile create` with `--clone` for full config copy
  - **Tool scoping** per profile:
    - `ar_watcher`: cognee + postgres only (no google-workspace, no web/browser/code_execution)
    - `voucher_scanner`: cognee + postgres + google-workspace (no web/browser)
    - `outreach_agent`: cognee + postgres + google-workspace (no web/browser)
  - `platform_toolsets.discord` used for built-in tool control (web, browser, code_execution)
  - `mcp_servers` control per-profile MCP access
  - Each profile has `config.yaml`, `SOUL.md`, `.env` — all configured
  - `tests/test_profile_scoping.py` — 15/15 pass
- **Phase 5 complete** — Cron Jobs + Business Logic
- **PostgreSQL MCP write access resolved** — Custom `cognee-server/postgres_mcp.py` replaces read-only npm package
  - Exposes both `query` (SELECT) and `execute` (INSERT/UPDATE/DELETE) MCP tools
  - Registered with all 3 profile configs and master config
  - Verified: gateway logs show 6 tools registered including `mcp_postgres_execute`
  - 3 cron jobs deployed and enabled: `ar_daily_check`, `voucher_watchdog`, `outreach_daily`
  - Jobs stored in `~/.hermes/cron/jobs.json` with correct Hermes v0.10 format
  - **Schedule format:** `{"kind": "cron", "expr": "<expr>", "display": "<expr>"}`
  - **Approval gate wired** — all 3 profile configs have `approvals.mode: manual`
  - `ar_daily_check` → profile `ar_watcher`, schedule `0 8 * * 1-5`, approval required
  - `voucher_watchdog` → profile `voucher_scanner`, schedule `*/15 * * * *`, auto-post >= 0.8 confidence
  - `outreach_daily` → profile `outreach_agent`, schedule `0 9 * * 1-5`, approval required
  - `tests/test_cron_business_logic.py` — 10/10 pass
  - **Runtime verified** — `voucher_watchdog` fires every 15 min, queries DB, produces reports
  - **Slack delivery confirmed** — cron reports delivered to `#biz-bridgeandbolt` via Slack Socket Mode
  - **Pivoted from Discord to Slack** — Discord rate limiting resolved; all 3 cron jobs deliver to `slack:#biz-bridgeandbolt`
- **Agent identity:** Argus Panoptes ("Argus" for short), deployed by Bridge and Bolt

## Profile Architecture (Hermes v0.10)

- Each profile is a fully independent `HERMES_HOME` directory
- `hermes gateway run --profile <name>` sets `HERMES_HOME` to `~/.hermes/profiles/<name>/`
- Profiles have their own config.yaml, SOUL.md, .env, sessions, logs, cron
- MCP server tool filtering: `tools.include` / `tools.exclude` per server in config.yaml
- Built-in tool control: `platform_toolsets.discord` in config.yaml
- Cross-profile isolation: sessions, logs, cron, personality all scoped per profile
- Cognee and PostgreSQL are shared across profiles (same connection strings in config)

- **Slack reactions wired** — Hermes native 👀/✅ reactions confirmed working for all @mentions and DMs
  - `gateway/platforms/slack.py` handles reactions natively: `_should_react = is_dm or is_mentioned`
  - No config flag needed — always on for @mentions/DMs. ❌ error reaction is Discord-only (not Slack)
  - Default profile behavior: eyes on pickup, checkmark on completion, managed entirely by Hermes
  - `cognee-server/slack_mcp.py` created (MCP wrapper for Slack reactions API) but not wired — kept for future use
  - `config/hermes.yaml` now includes `agent.system_prompt` template (was missing — see architecture note below)
  - `deploy/watchdog.ps1` + `deploy/register-watchdog.ps1` added; `$MaxRestarts` bumped from 20 → 200

## Argus System Prompt Architecture (Critical)

**The default profile (Argus) does NOT use SOUL.md.** It uses `agent.system_prompt` in `~/.hermes/config.yaml`. SOUL.md at `~/.hermes/SOUL.md` is only loaded by named profiles (ar_watcher, voucher_scanner, outreach) via `personality.profiles.<name>.template`.

To update Argus's behavior:
- Edit `config/hermes.yaml` → `agent.system_prompt` (repo template)
- Apply to running instance: copy relevant section directly into `~/.hermes/config.yaml` → `agent.system_prompt`
- Restart gateway: `Stop-Process -Id (Get-Content ~/.hermes/gateway_state.json | ConvertFrom-Json).pid -Force`

The `config/hermes.yaml` repo template and `~/.hermes/config.yaml` have diverged in structure (different top-level keys). Always edit the running `~/.hermes/config.yaml` directly for immediate changes, then keep `config/hermes.yaml` in sync.

**Slack reactions**: Argus uses `curl` via terminal tool + `SLACK_BOT_TOKEN` (via `terminal.env_passthrough`) to manage four reaction states: 👀 eyes (working), ❓ question (waiting on user), ✅ white_check_mark (task done, last call of turn), 🧠 brain (alongside ✅ when Cognee write confirmed).

## Critical Operational Details

**Gateway is managed by the watchdog (Task Scheduler) — do not start manually.**

The watchdog task `HermesGatewayWatchdog` auto-starts at logon and restarts the gateway on any crash.
- Script: `deploy/watchdog.ps1`
- Register/re-register: `deploy/register-watchdog.ps1`
- Watchdog log: `~/.hermes/logs/watchdog.log`

```powershell
# Check watchdog status
Get-ScheduledTask -TaskName "HermesGatewayWatchdog" | Select-Object TaskName, State

# Force-restart (stop gateway; watchdog relaunches automatically)
$pid = (Get-Content "$env:USERPROFILE\.hermes\gateway_state.json" | ConvertFrom-Json).pid
Stop-Process -Id $pid -Force

# Emergency manual start (if watchdog task is not registered)
$hermesExe = "$env:USERPROFILE\AppData\Local\Packages\PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0\LocalCache\local-packages\Python313\Scripts\hermes.exe"
$env:PYTHONIOENCODING = "utf-8"
Start-Process -FilePath $hermesExe -ArgumentList "gateway","run" -WindowStyle Hidden
```

**Stopping:** `Stop-Process -Id <pid> -Force` (watchdog will restart it; stop the task first if a permanent stop is needed)

## Profiles

| Profile | MCP Servers | Email | Web/Browser | Code Exec | Cron Job |
|---|---|---|---|---|---|
| default | cognee, postgres | no | yes | yes | none |
| ar_watcher | cognee, postgres | no | no | no | ar_daily_check |
| voucher_scanner | cognee, postgres, google-workspace | yes | no | yes | voucher_watchdog |
| outreach_agent | cognee, postgres, google-workspace | yes | no | yes | outreach_daily |

## Cron Jobs

| Job | Profile | Schedule | Approval | Deliver |
|---|---|---|---|---|
| ar_daily_check | ar_watcher | 0 8 * * 1-5 | required | slack:#biz-bridgeandbolt |
| voucher_watchdog | voucher_scanner | */15 * * * * | not required | slack:#biz-bridgeandbolt |
| outreach_daily | outreach_agent | 0 9 * * 1-5 | required | slack:#biz-bridgeandbolt |

## Known Issues

| Issue | Detail |
|---|---|
| `os.kill(pid, 0)` on Windows | Patched in `status.py` — may need upstream fix |
| `skip_context_files=True` in gateway | Patched to `False` in `run.py:5934` |
| Hermes HTTP MCP transport | Not supported in v0.10 — use stdio wrapper |
| Hermes doesn't forward `cwd` to MCP stdio | Use absolute paths in `args` |
| `hermes gateway stop` | Fails on Windows — use `Stop-Process` |
| Google Workspace auth | No credentials.json/token.json — will run in degraded mode |
| Ollama cold start | gemma4:e4b (~3GB) times out on first load — run a warmup query before relying on it |
| Cognee primary pipeline | Fails due to missing `transformers` — fallback DeepSeek works |
| Cron runtime + Slack delivery | Verified — `voucher_watchdog` fires every 15 min, reports delivered to `#biz-bridgeandbolt` |
| ~~PostgreSQL MCP write access~~ | **Resolved** — `cognee-server/postgres_mcp.py` now exposes `query` + `execute` |
| ~~Discord rate limiting~~ | **Resolved** — Discord fully disabled; Slack is the only messaging platform |
| ~~Slack bidirectional messaging~~ | **Resolved** — three fixes required: (1) SOUL.md must not contain literal injection strings like `"ignore previous instructions"` or Hermes's prompt_builder blocks the file and silently aborts every interactive session; (2) Slack App must have `message.channels` event subscribed (without it the bot is deaf to all channel messages while outbound cron posts still work); (3) App Home → Messages Tab must be enabled for DMs; (4) app must be reinstalled after any scope/event change |
| **Hermes gateway crash (upstream bug)** | `_run_on_mcp_loop` in `tools/mcp_tool.py` polls with `future.result(timeout=0.1)` from the asyncio event loop thread on every MCP call, blocking the loop each time. When MCP discovery or a tool call exceeds the 120 s hard deadline, `return future.result(timeout=0)` sits outside the try/except and raises `concurrent.futures.TimeoutError` uncaught, killing the process silently. Previously this also caused Discord shard heartbeat starvation -> `loop.shutdown_default_executor()` -> Slack API failure cascade. **Workarounds applied:** (1) Discord disabled entirely (`DISCORD_BOT_TOKEN` cleared, removed from `config.yaml`) to eliminate the shard cascade. (2) Watchdog task `HermesGatewayWatchdog` auto-restarts gateway on any crash. Upstream fix needed: make MCP calls non-blocking from the event loop thread. |

## Test Results

| Suite | Tests | Status |
|---|---|---|
| Phase 0 E2E (`test_e2e_phase0.py`) | 6/6 | All pass |
| Phase 2 Integration (`test_integration.py`) | 5/5 | All pass |
| Phase 3 Data Integrity (`test_data_integrity.py`) | 7/7 | All pass |
| Phase 4 Profile Scoping (`test_profile_scoping.py`) | 15/15 | All pass |
| Phase 5 Cron Business Logic (`test_cron_business_logic.py`) | 10/10 | All pass |
| Phase 6 Deployment (`test_deployment.py`) | 18/18 | All pass |
| **Total** | **61/61** | **All pass** |
| Google Workspace | 51/51 | All pass |

## Next Up

- Production smoke test: provision a real org end-to-end
- Google Workspace OAuth setup for real email/capability (credentials.json + token.json in google-tools/)
- Ollama warmup


## Phase 6 Completion Notes

Phase 6 (Per-Org Deployment) is complete:
- `deploy/provision.sh` enhanced with `--preset`, `--modules`, `--cloud` flags
- `deploy/templates/` — 3 org-type presets: construction, dental, retail
- `deploy/apply_preset.py` — applies preset overrides (approvals, thresholds, HIPAA) to provisioned instance
- `deploy/ONBOARDING.md` — comprehensive onboarding checklist (pre-deploy → provisioning → validation → client handoff → monitoring)
- `tests/test_deployment.py` — 18 tests covering preset validity, script flags, onboarding checklist, cross-cutting rules
- Provision script deployable in under 30 minutes per the runbook gate criteria
