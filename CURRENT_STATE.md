# CURRENT STATE — Hermes-Argus

## Completed

- **Hermes Agent v0.10.0** installed via pip (Windows native)
- **Config:** DeepSeek provider active, Discord gateway running, MCP servers (Cognee, PostgreSQL) configured
- **Gateway:** Discord bot running (PID 37040), `discord.py` installed
- **Cognee:** Docker container `argus-cognee` up, learn/query round-trip working via HTTP
- **PostgreSQL:** `argus-openbrain` container up, all 7 business tables deployed, test data inserted
- **AR Watcher profile:** Copied to `~/.hermes/profiles/ar_watcher/`, detected by Hermes
- **Google Workspace tests:** 51/51 pass
- **E2E smoke tests:** 6/6 pass (`tests/test_e2e_phase0.py`)
- **Schema fix:** Reordered `business.sql` so `customers` precedes `ar_invoices`

## In Progress

- (none)

## Known Issues

| Issue | Detail |
|---|---|
| `hermes setup --non-interactive` | UnicodeEncodeError on Windows CP1252 — use `hermes config set` instead |
| `hermes gateway stop` | Fails on Windows (Unix signal) — use `Stop-Process` |
| `hermes skills install --dir` | Flag doesn't exist in v0.10 — ICM module integration TBD |
| Ollama cold start | 9.6GB `gemma4:e4b` times out on first load (expected) |
| Cognee `test_adapter.py` / `test_cognee_client.py` | Hang on DeepSeek API call from container — HTTP endpoints verified instead |
| No `/health` on Cognee | Use `/query?q=test` or `/learn` for health check |
| `curl` PowerShell alias | Must use `curl.exe` on Windows |

## Next Up

- Phase 1: Run `docs/PHASE_1_RUNBOOK.md`
- Proper ICM skill module integration with Hermes profiles
- MCP wrapper script for Cognee (if needed for Hermes tool calling)
- Ollama warmup and local model validation
