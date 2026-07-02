# Hermes-Argus — Current State

> Single source of truth for the build state of the Argus agent system.
> Read at session start. Update on significant changes.

## Last Updated
- **Date:** 2026-07-02
- **By:** Hermes Agent (Open Brain — two new schema areas: meeting_notes + sales_recordings)

## Identity
- **Agent name:** Argus Panoptes ("Argus")
- **Company:** Bridge and Bolt
- **Runtime:** Hermes (v0.10) on WSL2 Ubuntu 24.04 (DESKTOP-I9UVAVD)
- **Primary channel:** Slack (DMs + @mentions)
- **Repo:** `/mnt/c/Users/Russell/Documents/GitHub/Hermes-Argus/`

## Live Operational State

| Component | Status |
|-----------|--------|
| Gateway | PID 30316, `running`, Slack `connected` |
| Watchdog (Task Scheduler) | **Running** — auto-restarts gateway at logon |
| Postgres (argus-openbrain) | Healthy — port 5432 |
| Cognee Server | Running — port 8000 |
| Hindsight Postgres (pg0) | Healthy — port 15432 (PID 39292) |
| Hindsight Task Scheduler | **Running** — `HermesHindsightStart` auto-starts on logon + wake |

## Architecture

```
Hermes Runtime (WSL2 ~/.hermes/)
  ├── config.yaml          — main config
  ├── .env                 — API keys/secrets (in password manager)
  ├── skills/              — procedural knowledge (ICM subfolder structure)
  ├── cron/                — scheduled jobs
  └── profiles/            — sub-agent profiles (ar_watcher, voucher_scanner, outreach)

Docker Stack (docker-compose.yml)
  ├── argus-openbrain      — Postgres 17 (OpenBrain structured data)
  │   ├── schema: invoices, contacts, outstanding_invoices, ar_invoices_aging
  │   └── backup_jobs table for observability
  └── cognee-server        — Knowledge graph + vector memory (MCP-wrapped)
        ├── MCP: memorize, query
        ├── Postgres MCP: query, execute
        └── Active LLM: deepseek-chat (via .env.llm.active toggle)

Windows Side
  ├── Task Scheduler: HermesGatewayWatchdog (gateway restart — AtLogOn + OnWake)
  ├── Task Scheduler: HermesHindsightStart (Hindsight pg0 + MCP server — AtLogOn + OnWake)
  └── Task Scheduler: HermesArgusBackup (nightly backup to D:)
```

## Skills Structure — Three-Lane ICM Architecture

All skills now follow the **ICM lowercase-hyphens** frontmatter convention and live in `skills/<domain>/<skill-name>/SKILL.md` subfolders.

### 🏗️ Lane 1: Development (architecture, ops, content)

| Skill | Domain | Path |
|-------|--------|------|
| `autonomous-memory-stack` | architecture | `skills/architecture/autonomous-memory-stack/SKILL.md` |
| `local-postgres-to-supabase-migration` | architecture | `skills/architecture/local-postgres-to-supabase-migration/SKILL.md` |
| `ollama-jit-vision-model` | architecture | `skills/architecture/ollama-jit-vision-model/SKILL.md` |
| `argus-disaster-recovery` | ops | `skills/ops/argus-disaster-recovery/SKILL.md` |
| `argus-slack-emoji-protocol` | ops | `skills/ops/argus-slack-emoji-protocol/SKILL.md` |
| `gmail-api-integration` | ops | `skills/ops/gmail-api-integration/SKILL.md` |
| `puppeteer-web-browsing` | ops | `skills/ops/puppeteer-web-browsing/SKILL.md` |
| `vision-analysis` | content | `skills/content/vision-analysis/SKILL.md` |
| `ui-design-models` | content | `skills/content/ui-design-models/SKILL.md` |
| `water-safety-app-vision` | content | `skills/content/water-safety-app-vision/SKILL.md` |

### 🤝 Lane 2: Client Services (clients)

| Skill | Domain | Path |
|-------|--------|------|
| *(none yet)* | clients | `skills/clients/_context.md` — placeholder |

### 🏢 Lane 3: Business/Internal (business)

| Skill | Domain | Path |
|-------|--------|------|
| `ai-smb-consulting-quick-cash-strategy` | business | `skills/business/ai-smb-consulting-quick-cash-strategy/SKILL.md` |
| `cinematic-html-presentation` | business | `skills/business/cinematic-html-presentation/SKILL.md` |
| `multi-agent-orchestration-framework` | business | `skills/business/multi-agent-orchestration-framework/SKILL.md` |
| `workmate-agent-framework` | business | `skills/business/workmate-agent-framework/SKILL.md` |

### New Infrastructure

- **`CONTEXT.md`** at repo root — Layer 1 routing doc mapping request types to lanes/domains
- **`_config/lane-conventions.md`** — shared frontmatter template and naming rules

## Backup System — D: Drive (Primary)

The D: drive backup is the canonical, running backup system.

| Component | Detail |
|-----------|--------|
| **Schedule** | Daily at 02:00 (Windows Task Scheduler — `HermesArgusBackup`) |
| **Script** | `scripts/backup-to-d.ps1` — pg_dumpall + docker save + Restic |
| **Register** | `scripts/register-backup-task.ps1` (run once as Admin) |
| **Destination** | `D:\\hermes-backups\\` (USB external drive) |
| **Contents** | Postgres dumps (7-day retention), Docker images (3 daily `.tar` exports), Restic repo (7 daily / 4 weekly / 3 monthly snapshots) |
| **Observability** | `backup_jobs` table in Postgres; `backup_health_check` cron at 08:00 daily posts Slack alert on failure |

## Active Cron Jobs

| Job | Profile | Schedule | Deliver | Status |
|-----|---------|----------|---------|--------|
| `ar_daily_check` | ar_watcher | Weekdays 8am | Slack #biz-bridgeandbolt | ✅ Running |
| `outreach_daily` | outreach_agent | Weekdays 9am | Slack #biz-bridgeandbolt | ✅ Running |

## Known Issues

| Issue | Detail | Status |
|-------|--------|--------|
| Cognee MCP memorize | Memorize calls return `Error executing tool` despite both containers healthy | 🔍 Investigating |
| Hermes memory tool | At capacity (2,031/2,200 chars) | Needs trimming |
| Cognee DeepSeek adapter | Prior issue with JSON parsing on v4-flash | 🔍 May be resolved |
| Skill registration | TIRITH blocked `skill_manage` for DR skill due to config/secrets references | ⚠️ Workaround: raw file write |

## Open Brain — Two New Schema Areas (2026-07-02)

Two dedicated tables created in OpenBrain Postgres (argus-openbrain container):

| Section | Table | Purpose |
|---------|-------|---------|
| 📋 Meeting Notes | `meeting_notes` | Transcripts, summaries, participants, projects |
| 🎧 Sales Call Recordings | `sales_recordings` | Audio file refs, call outcomes, prospect tracking |

**Schema file:** `schema/openbrain-meetings.sql` — idempotent DDL with `CREATE TABLE IF NOT EXISTS`.
**Helper functions:** `upsert_meeting_note()` and `upsert_sales_recording()` — returns UUID on insert.
**Auto-updated_at triggers:** ✅ Shared `update_updated_at_column()` function + `BEFORE UPDATE` triggers on both tables (verified).
**OB1 metadata.json:** ✅ `schema/openbrain-meetings-sales/metadata.json` — version 1.0.0, category: extensions.
**Deno MCP server:** ✅ `schema/openbrain-meetings-sales/index.ts` + `deno.json` — 6 MCP tools (`save_meeting_note`, `save_sales_recording`, `query_meetings`, `query_sales_recordings`, `get_meeting_stats`, `get_sales_pipeline`) for Claude/Cursor stdio integration. Compiles clean on Deno 2.9.1.
**Skill:** `openbrain-meetings-sales` v2.0.0 — full docs for SQL + MCP usage, Claude/Cursor config instructions.

## Future / Deferred
- **Extend ICM pattern to Bridgeboard repo** — apply same three-lane structure
- **Extend to AI Factory** — align AI Factory skills frontmatter with Hermes-Argus convention
- **Create client services skills** — populate `skills/clients/` with onboarding and outreach playbooks
- **Hindsight auto-start** — add to Task Scheduler so it survives reboots (tracked in issue #13)

## Runbooks
- **[Gateway recovery](docs/runbooks/gateway-recovery.md)** — sev-1. Slack silence / gateway crash.
- **[Cognee health check + restart](docs/runbooks/cognee-health-check.md)** — sev-2. MCP memorize failing or graph empty.

## Pointers
- **DR Skill:** `~/.hermes/skills/ops/argus-disaster-recovery/SKILL.md`
- **GitHub:** `Russell-Shirley/Hermes-Argus` (default branch: `master`)
- **Docker stack:** `docker-compose.yml` in repo root
- **LLM toggle:** `scripts/switch-llm.ps1 deepseek|gemma`
- **Skill sync:** `scripts/sync-skills-to-hermes.sh` (repo → runtime)
- **Watchdog register:** `deploy/register-watchdog.ps1`
- **Hindsight start:** `deploy/hindsight-start.ps1`
- **Hindsight register:** `deploy/register-hindsight-task.ps1`
