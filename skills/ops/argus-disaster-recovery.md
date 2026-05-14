---
name: argus-disaster-recovery
description: |
  Complete disaster recovery procedures for the Hermes-Argus agent stack.
  Covers full backup, bare-metal restore, data migration, and health verification.
  Backs up to D: drive nightly via PowerShell Task Scheduler.
  DO NOT use for: routine maintenance, config changes, skill edits, or daily operations.

category: ops
domain: infrastructure
intent:
  - disaster-recovery
  - backup
  - restore
  - migration
exclusions:
  - routine-maintenance
  - skill-editing
  - daily-operations
  - config-tweaks
requires:
  - docker
  - pg_dumpall
  - hermes-cli
  - powershell
  - restic

phase: maintenance
compatible_with: []
conflicts_with:
  - skill-editing
  - daily-operations
handoff_to: []

scope: local-only
data_access:
  mcp_servers: []
  secrets: [SLACK_BOT_TOKEN, OPENROUTER_API_KEY, POSTGRES_PASSWORD, RESTIC_PASSWORD]
  trust_level: admin

governed_by: []

version: 1.1.0
compatibility:
  min_runtime: hermes-1.0
deprecated: false
deprecation_notes: ""

examples:
  - "Full system restore after catastrophic WSL failure"
  - "Migrate Argus to a new machine"
  - "Restore specific data layer (e.g. Cognee only) after corruption"
---
# Argus Disaster Recovery

## What Makes Up "Argus" — Data Layer Inventory

"Argus" is the sum of six data layers. Lose any one and capability degrades. The nightly backup protects all six.

| # | Layer | What It Contains | Where It Lives | Backup Method | Restore Priority |
|---|-------|------------------|----------------|---------------|------------------|
| 1 | **OpenBrain (Postgres)** | Structured data: invoices, contacts, outstanding_invoices, ar_invoices_aging, backup_jobs. Core business memory. | Docker container `argus-openbrain` (port 5432), volume at `~/.hermes-data/postgres/` | pg_dumpall → `D:\hermes-backups\postgres\openbrain_<timestamp>.sql` (7-day retention) | 1st — without this, business ops are blind |
| 2 | **Cognee (Knowledge Graph)** | Vector embeddings, entity nodes/edges, relational memory. What I "know" long-term. | Docker container `cognee-server` (port 8000), volumes at `~/.hermes-data/cognee/.cognee_system` + `~/.hermes-data/cognee/.data_storage` | Restic snapshot (`~/.hermes-data/` via backup-to-d.ps1) + docker image save → `D:\hermes-backups\images\cognee-server_<date>.tar` (3-day retention) | 2nd — without this, I forget what I've learned |
| 3 | **Hermes Config + Secrets** | `config.yaml` (model, providers, cron, memory limits), `.env` (all API keys: SLACK_BOT_TOKEN, OPENROUTER_API_KEY, POSTGRES_PASSWORD, etc.) | `~/.hermes/` on WSL | Restic snapshot (`~/.hermes/` via backup-to-d.ps1). **Secrets also stored in Bitwarden separately.** | 3rd — without config/secrets, nothing connects |
| 4 | **Hermes Skills** | All SKILL.md files — the v5-compliant procedural knowledge tree | `~/.hermes/skills/` (runtime) + `Hermes-Argus/skills/` (GitHub repo) | Restic snapshot + git push (manual or scheduled). Skills dir is the "ground truth" after restore via `sync-skills-to-hermes.sh`. | 4th — without these, I lose procedural knowledge |
| 5 | **Cron Jobs** | Scheduled tasks: `ar_daily_check` (8am weekdays), `outreach_daily` (9am weekdays), `backup_health_check` | Hermes internal runtime data (`~/.hermes/cron/jobs.json`) | Restic snapshot. Export: `hermes cron list > cron_backup.txt`. | 5th — jobs stop firing, business ops degrade |
| 6 | **Docker Images** | `hermes-argus-cognee-server:latest`, `postgres:17` | Docker local registry | `docker save` → `D:\hermes-backups\images\*.tar` (3-day, keep most recent 3) | Last — can re-pull postgres:17, but cognee-server is custom-built |

**Total backup destination:** `D:\hermes-backups\`
**Frequency:** Daily at 02:00 (Windows Task Scheduler — `HermesArgusBackup`)
**Password:** `D:\hermes-backups\.restic-password` — also stored in Bitwarden

## Current Backup System

### How it runs
The Windows Task Scheduler task `HermesArgusBackup` runs `scripts/backup-to-d.ps1` daily at 02:00.

**The script does 4 things:**
1. `pg_dumpall` from the `argus-openbrain` container → `D:\hermes-backups\postgres\`
2. `docker save` of `hermes-argus-cognee-server:latest` → `D:\hermes-backups\images\`
3. `docker save` of `postgres:17` → `D:\hermes-backups\images\`
4. **Restic snapshot** of `~/.hermes` (config, skills, cron, secrets) + `~/.hermes-data` (Cognee volumes) → Restic repo at `D:\hermes-backups\restic-repo\`

**Then:**
- Writes status to `D:\hermes-backups\last-status.json`
- Inserts a row into `backup_jobs` table in OpenBrain (Postgres)
- Posts Slack alert to `#biz-bridgeandbolt` on failure

**Retention:**
- Postgres dumps: 7 days
- Docker images: 3 most recent
- Restic snapshots: 7 daily / 4 weekly / 3 monthly

### Register the backup task (one-time setup)
```powershell
# Run once as Administrator
.\scripts\register-backup-task.ps1
```

This downloads Restic, initializes the repo, and registers the Task Scheduler task.

## Restore Procedures

### Full System Restore (Bare Metal)

Follow these phases in order. Each phase depends on the prior one.

#### Phase 0 — Verify Backup Availability

Before starting any restore, confirm:
```powershell
# Check D: drive has backups
Test-Path "D:\hermes-backups"

# List available Postgres dumps
Get-ChildItem "D:\hermes-backups\postgres\"

# List available Docker image tars
Get-ChildItem "D:\hermes-backups\images\"

# List Restic snapshots
D:\hermes-backups\tools\restic.exe -r D:\hermes-backups\restic-repo snapshots
```

#### Phase 1 — Bootstrap Platform

1. Install WSL2 (required for Hermes runtime)
2. Inside WSL: `sudo apt update && sudo apt install -y docker.io docker-compose-plugin postgresql-client git`
3. Start Docker: `sudo service docker start`
4. Clone the repo: `git clone https://github.com/Russell-Shirley/Hermes-Argus /mnt/c/Users/Russell/Documents/GitHub/Hermes-Argus`
5. Install Hermes CLI per Hermes docs
6. Ensure `hermes` is in PATH

#### Phase 2 — Restore Config + Secrets (Critical)

1. Restore `~/.hermes/config.yaml` from the Restic snapshot, or use a recent backup copy
2. **Restore `~/.hermes/.env` from Bitwarden** — this contains all API keys. Without this, nothing connects.
3. If Restic is available:
   ```powershell
   D:\hermes-backups\tools\restic.exe -r D:\hermes-backups\restic-repo restore latest --target C:\Users\Russell\ --include ".hermes/config.yaml"
   ```

#### Phase 3 — Restore Docker Stack + OpenBrain (Postgres)

```bash
# From repo root
cd /mnt/c/Users/Russell/Documents/GitHub/Hermes-Argus
docker compose up -d

# Wait for Postgres health
docker exec argus-openbrain pg_isready -U postgres -d openbrain

# Find the latest dump
LATEST_DUMP=$(ls -t /mnt/d/hermes-backups/postgres/openbrain_*.sql | head -1)

# Restore OpenBrain
type "$LATEST_DUMP" | docker exec -i argus-openbrain psql -U postgres -d openbrain

# Verify
docker exec argus-openbrain psql -U postgres -d openbrain -c "SELECT count(*) FROM invoices;"
```

**If Docker images need to be re-loaded from backup:**
```powershell
docker load -i D:\hermes-backups\images\cognee-server_<date>.tar
docker load -i D:\hermes-backups\images\postgres-17_<date>.tar
```

#### Phase 4 — Restore Cognee (Knowledge Graph)

Cognee data lives in `~/.hermes-data/cognee/` which is backed up via Restic.

```bash
# Remove current Cognee data (Docker must be stopped for this)
docker stop cognee-server
rm -rf ~/.hermes-data/cognee/.cognee_system ~/.hermes-data/cognee/.data_storage

# Restore from Restic (run from Windows side or mount the path)
restic -r D:\hermes-backups\restic-repo restore latest --target C:\Users\Russell\ --include ".hermes-data/cognee/*"

# Restart Cognee
docker start cognee-server

# Wait for re-index (~5 min on first startup)
docker logs -f cognee-server
```

**If Restic is not available** — Cognee data is the hardest to restore from first principles. The `cognee-server` Docker image (saved via `docker save`) contains no data; the data is in the volumes. This is why Restic is the critical piece for Cognee recovery.

#### Phase 5 — Restore Skills

```bash
cd /mnt/c/Users/Russell/Documents/GitHub/Hermes-Argus
bash scripts/sync-skills-to-hermes.sh
```

This copies skills from the repo (canonical) to the Hermes runtime at `~/.hermes/skills/`.

#### Phase 6 — Re-Register Cron Jobs

Re-create cron jobs. Known jobs:
- `ar_daily_check` — AR collections (profile: ar_watcher, schedule: weekdays 8am)
- `outreach_daily` — customer outreach (profile: outreach_agent, schedule: weekdays 9am)
- `backup_health_check` — checks backup_jobs table at 08:00 daily

If a backup of cron job definitions exists:
```bash
# Export format
hermes cron list
```

#### Phase 7 — Verify Everything

```bash
# Docker stack
docker compose ps
# Expected: argus-openbrain (healthy), cognee-server (running)

# Hermes gateway
hermes gateway status
# Expected: running, Slack connected

# Postgres data
docker exec argus-openbrain psql -U postgres -d openbrain -c "\dt"
# Expected: all tables present

# Cognee
curl http://localhost:8000/health
# Expected: 200 OK

# Skills discovered
hermes skills list
# Expected: all skills registered

# Cron jobs active
hermes cron list
# Expected: all jobs present
```

### Single-Layer Restore (Partial Recovery)

#### Restore OpenBrain Only
```bash
LATEST_DUMP=$(ls -t /mnt/d/hermes-backups/postgres/openbrain_*.sql | head -1)
type "$LATEST_DUMP" | docker exec -i argus-openbrain psql -U postgres
```

#### Restore Cognee Only
```bash
docker stop cognee-server
rm -rf ~/.hermes-data/cognee/.cognee_system ~/.hermes-data/cognee/.data_storage
restic -r D:\hermes-backups\restic-repo restore latest --target C:\Users\Russell\ --include ".hermes-data/cognee/*"
docker start cognee-server
```

#### Restore Hermes Config Only
```bash
restic -r D:\hermes-backups\restic-repo restore latest --target C:\Users\Russell\ --include ".hermes/config.yaml"
```

#### Restore Skills from Repo
```bash
cd /mnt/c/Users/Russell/Documents/GitHub/Hermes-Argus
git pull
bash scripts/sync-skills-to-hermes.sh
```

## Emergency Quick-Start (5-Minute Checklist)

If I'm completely down (WSL reinstall, Docker wiped, everything gone):

1. **D: drive available?** Check `D:\hermes-backups\` exists
2. **WSL installed?** If not, `wsl --install -d Ubuntu-24.04`
3. **Docker installed?** Install Docker Desktop for Windows
4. **`.env` restored from Bitwarden?** **This is the single point of failure**
5. **Repo cloned?** `git clone` into `Documents\GitHub\Hermes-Argus`
6. **Docker stack up?** `docker compose up -d` from repo root
7. **Database restored?** Run Phase 3 OpenBrain restore
8. **Cognee restored?** Run Phase 4 Cognee restore
9. **Skills synced?** `bash scripts/sync-skills-to-hermes.sh`
10. **Gateway running?** `hermes gateway run`

## RTO Estimates

| Scenario | Estimated RTO | Notes |
|----------|---------------|-------|
| Docker stack restart (data intact) | ~2 min | Containers restart, no data loss |
| Postgres restore only | ~5 min | Single-layer: find latest dump, pipe to docker exec |
| Cognee restore from Restic | ~15 min | Rsync-like restore + ~5 min re-index |
| Full restore from D: drive backups | ~30-45 min | All 7 phases, assuming WSL + Docker are ready |
| Bare metal (new machine) | ~2-4 hours | OS, WSL, Docker, clone, restore data, verify |
| Skills-only restore (data already live) | ~2 min | `git pull` + sync |
| Restic password lost | 😱 Disaster | Snapshots are **unrecoverable**. Password in Bitwarden. |

## Critical Dependencies

| What | Why It Matters | Where It's Stored |
|------|----------------|-------------------|
| Restic password | All historical snapshots unreadable without it | `D:\hermes-backups\.restic-password` + **Bitwarden** |
| `.env` file | No Slack, no OpenRouter, no AI, no database | `~/.hermes/.env` + **Bitwarden** |
| D: drive | The backup destination itself | Physical D: drive. If D: dies, backups are gone. |
| GitHub repo | Skills canonical source, docker-compose.yml, scripts | GitHub (Russell-Shirley/Hermes-Argus) |
| Windows Task Scheduler | Nightly backup automation | Registered as `HermesArgusBackup` (dump from existing system) |

## Recovery Pitfalls

- **WSL vs Windows paths:** The Hermes-Argus repo lives on Windows (`/mnt/c/Users/...`); Hermes runtime lives in WSL2 (`~/.hermes`). The `sync-skills-to-hermes.sh` script bridges them. After restore, ensure this script is run.
- **Docker volume persistence:** If Docker volumes are lost (e.g., `docker compose down -v`), `pg_dump` backups are your only recovery path. The backup stores dumps separately from Docker's volume layer — this is intentional.
- **Token sandboxing:** `SLACK_BOT_TOKEN` is sandboxed from subprocesses. The MCP tools cannot use it. This is expected — do not attempt curl-based Slack API calls from terminal.
- **Cognee re-indexing:** After restoring Cognee data dirs, the server needs ~5 minutes to re-index on first startup. This is normal. Monitor with `docker logs -f cognee-server`.
- **Restic restore paths:** Restic restores to the **target** directory — if you restore `~/.hermes` with target `C:\Users\Russell`, files land at `C:\Users\Russell\.hermes\...`. Ensure the target path matches the original.
- **PowerShell execution policy:** The backup script requires `-ExecutionPolicy Bypass`. The Task Scheduler task handles this, but running manually requires the flag.

## Observed Backup Health

The `backup_health_check` cron job queries the `backup_jobs` table in OpenBrain daily at 08:00. It checks:
- Was there a backup run in the last 24 hours?
- Did it succeed?
- Posts Slack alert to `#biz-bridgeandbolt` on failure or missing run.

You can also check manually:
```powershell
# Check last status
Get-Content D:\hermes-backups\last-status.json | ConvertFrom-Json | Format-List

# List recent Postgres dumps
Get-ChildItem D:\hermes-backups\postgres\ | Sort-Object LastWriteTime -Descending | Select-Object -First 5
```

## DR Skill Version History

- **1.0.0** (2026-05-14) — Initial version. Planned WSL-local backup approach.
- **1.1.0** (2026-05-14) — Rewritten to match the real D: drive backup system. All data layers documented. Full restore procedures aligned with `backup-to-d.ps1`.

## References
- `CURRENT-STATE.md` — repo-level build state and architecture
- `scripts/backup-to-d.ps1` — the actual backup script
- `scripts/register-backup-task.ps1` — one-time setup
- `docker-compose.yml` — service definitions
- `scripts/sync-skills-to-hermes.sh` — runtime-to-repo skill bridge
- Bitwarden — `.env` secrets + Restic password
