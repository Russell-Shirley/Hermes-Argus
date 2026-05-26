---
name: Cognee Health Check + Restart
description: Diagnose and recover Cognee when containers are running but MCP memorize fails or graph is empty
type: runbook
date: 2026-05-14
severity: sev-2
last_drill: never
---

# Cognee Health Check + Restart

## Trigger
- Argus reports `Error executing tool` on memorize calls
- Graph queries always return `engine=sql_fallback, data=[]`
- `/learn` endpoint returns 202 but no nodes/edges appear after 10+ minutes
- Cognee container is running but `backup_health_check` flags it

## Diagnosis

### 1. Are both containers running?
```powershell
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```
Expected: `argus-openbrain` (port 5432) and `cognee-server` (port 8000) both `Up`.

### 2. Is the HTTP endpoint responding?
```powershell
Invoke-RestMethod http://localhost:8000/health
# or
curl http://localhost:8000/health
```

### 3. Check cognee-server logs for errors
```powershell
docker logs cognee-server --tail 50
```
Key errors to look for:

| Error | Meaning | Fix |
|-------|---------|-----|
| `ValidationError: Invalid JSON` | DeepSeek v4-flash returning plain text, cognee adapter expects JSON | Switch to gemma: `scripts\switch-llm.ps1 gemma` |
| `ollama: 501` on embedding model | `gemma4:e4b` doesn't support embeddings | Embedding model must be `nomic-embed-text`, not gemma |
| `postmaster.pid` conflict | Stale pid file blocking Postgres start | See Hindsight runbook (#13) |
| `LLM_API_KEY` empty | `.env.llm.active` missing a key | Check active env file |

### 4. Send a canary ingest
```powershell
$body = @{ content = "canary test $(Get-Date -Format 'HH:mm:ss')"; dataset_name = "canary" } | ConvertTo-Json
Invoke-RestMethod -Uri http://localhost:8000/learn -Method Post -Body $body -ContentType "application/json"
```
Expected: `{"status": "queued"}` with HTTP 202.

Then check for graph activity after 2–3 minutes:
```powershell
docker exec argus-openbrain psql -U postgres -d cognee -c "SELECT COUNT(*) FROM nodes; SELECT COUNT(*) FROM edges;"
```
- Counts > 0 → pipeline is working (may just be slow on gemma)
- Counts = 0 after 10 min → pipeline is stuck; proceed to recovery

---

## Recovery

### Step 1 — Switch LLM if DeepSeek JSON errors present
```powershell
scripts\switch-llm.ps1 gemma
docker compose up -d cognee-server --force-recreate
```
**Note:** `docker compose restart` does NOT reload env_file — must use `--force-recreate`.

### Step 2 — Restart containers in correct order
```powershell
docker compose down
docker compose up -d
```
Wait 15s for Postgres to be ready before cognee-server connects.

### Step 3 — Verify embeddings model
```powershell
docker exec cognee-server env | findstr EMBEDDING
```
Must be `EMBEDDING_MODEL=nomic-embed-text`. If it shows `gemma4:e4b`, the env file is wrong — gemma does not support embeddings (returns 501).

### Step 4 — Re-run canary and check nodes
Repeat the canary ingest from diagnosis step 4. If nodes appear, pipeline is healthy.

### Step 5 — Check for UTF-8 BOM in env files
PowerShell writes UTF-16 with BOM by default. If env vars are being read as garbage:
```bash
# From WSL
file cognee-server/.env.llm.active
# Should say ASCII or UTF-8, not UTF-16
python3 -c "open('cognee-server/.env.llm.active','rb').read()[:3] == b'\xef\xbb\xbf' and print('BOM found')"
```
If BOM present: strip it with `scripts/switch-llm.ps1` (already handles this) or re-write the file from WSL.

---

## Known Persistent Issue
DeepSeek mode: `deepseek-chat` now auto-routes to `deepseek-v4-flash` on DeepSeek's API. Cognee's custom DeepSeek adapter (`/usr/local/lib/python3.11/site-packages/cognee/infrastructure/llm/.../deepseek/adapter.py`) expects JSON output but v4-flash returns plain text → `ValidationError`. Workaround: use gemma mode. Fix path: patch adapter to send `response_format={"type":"json_object"}`.

---

## Escalation
If graph remains empty after restart and LLM switch:
1. Check cognee version: `docker exec cognee-server pip show cognee` — v1.0 has stricter JSON validation than the earlier fork
2. Consider option D from CURRENT-STATE.md: bypass cognee entirely, write directly to `nodes`+`edges` Postgres tables with nomic embeddings as pgvector

## Post-Incident
- Note which LLM mode resolved it in CURRENT-STATE.md
- If replay needed: `scripts/replay_slack_to_cognee.py` (delete `.replay_state.json` first to reset)
- 84 threads from Slack channel C0B2E1CHZ8T (May 8–11) are queued for replay when pipeline is stable
