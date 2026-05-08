# Argus → Hermes Rebase Specification

**Date:** 2026-05-08
**Goal:** Rebase Argus on Hermes Agent while preserving Cognee graph memory, Google Workspace MCP tools, and the bolt-on architecture.

---

## What Survives (Keep)

| Asset | What it is | Effort |
|-------|-----------|--------|
| `cognee-server/` | Custom DeepSeek-fork Cognee with `/learn` and `/query` endpoints | Zero (wrap as MCP or HTTP) |
| `google-tools/` | Google Workspace MCP server (Gmail, Calendar, Tasks) | Zero (Hermes MCP config) |
| `soul.md` | System prompt identity | Convert to Hermes personality |
| `skills/` | Markdown runbooks | Convert to Hermes SKILL.md format |
| Cognee DeepSeek provider fork | Upstream PR pending | Keep as-is |

## What Hermes Replaces (Delete)

| Argus file | Hermes equivalent | Notes |
|-----------|-------------------|-------|
| `src/agent.ts` | `run_agent.py` | Agent loop, tool dispatch, system prompt |
| `src/bot.ts` | Hermes Discord gateway | Already supports Discord + 19 other platforms |
| `src/reflect.ts` | Hermes cron system | `cron.jobs.json` with platform delivery |
| `src/llm.ts` | Hermes provider system | 18+ providers, routing, fallbacks |
| `src/mcp.ts` | Hermes MCP config | Stdio + HTTP, tool filtering |
| `src/memory.ts` | Hermes session + memory plugin | FTS5 search, Honcho/Mem0/Hindsight |
| `src/config.ts` | `~/.hermes/config.yaml` | Full config surface |
| `src/logger.ts` | Hermes logging | Structured, configurable |
| `src/skills.ts` | Hermes skills system | agentskills.io standard, curator |
| `mcp.json` (Argus format) | Hermes `mcp_servers` config | Same servers, different config shape |
| `.env` (Argus) | `~/.hermes/.env` | Same pattern |
| `docker-compose.yml` | Hermes deployment + Cognee sidecar | Simplified (no custom agent container) |

## What Must Be Built (New)

### 1. Cognee MCP Connector
Cognee is currently called via HTTP from `src/agent.ts`. Wrap it as an MCP server so Hermes discovers it natively.

```python
# cognee-server/mcp_wrapper.py (new)
# Exposes two MCP tools:
#   cognee__memorize(text: str) → entity/relationship extraction
#   cognee__query(query: str) → graph + vector search
```

**Alternate path:** Keep HTTP and add to Hermes MCP config as an HTTP server. Easier, less code.

### 2. Multi-Agent Profiles
One Hermes deployment per org. Multiple agents per deployment.

```yaml
# ~/.hermes/config.yaml
profiles:
  ar_watcher:
    personality: ar_watcher.md
    skills: [ar_collections, collection_letters, icm_base]
    mcp_servers: [cognee, postgres]
    cron: ar_daily_check
  
  voucher_scanner:
    personality: voucher_scanner.md
    skills: [voucher_processing, accounting_entry, icm_base]
    mcp_servers: [cognee, postgres, google-workspace]
    cron: voucher_watchdog
  
  outreach_agent:
    personality: outreach.md
    skills: [customer_outreach, contact_cadence, icm_base]
    mcp_servers: [cognee, postgres]
    cron: outreach_daily
```

### 3. ICM Skill Scaffolding
A curated skill base that gets filtered per deployment.

```
modules/
  icm_base/          → Every org gets this (memory, graph, safety)
  ar_collections/     → AR aging, collections letters, payment tracking
  voucher_processing/ → OCR → accounting entry, approval routing
  customer_outreach/  → Contact cadence, re-engagement triggers
  inventory/          → Stock alerts, reorder points
  invoicing/          → Bill generation, recurring invoices
  payroll/            → Time tracking, payroll prep
```

Deployment script copies only the skills the org paid for:

```bash
hermes skills install --module ar_collections,voucher_processing
```

### 4. Business Logic — Database Schema
Per-org Supabase/PostgreSQL tables. Deployed on the org's machine.

```sql
-- AR Ledger
CREATE TABLE ar_invoices (
  id UUID PRIMARY KEY,
  customer_name TEXT NOT NULL,
  invoice_date DATE NOT NULL,
  due_date DATE NOT NULL,
  amount NUMERIC(12,2) NOT NULL,
  status TEXT DEFAULT 'open',  -- open, partial, paid, collections
  days_overdue INTEGER GENERATED ALWAYS AS (
    CASE WHEN status = 'paid' THEN 0 
    ELSE EXTRACT(DAY FROM NOW() - due_date)::INTEGER 
    END
  ) STORED
);

-- Collection Activity Log
CREATE TABLE collection_activity (
  id UUID PRIMARY KEY,
  invoice_id UUID REFERENCES ar_invoices(id),
  action TEXT,          -- letter_sent, call_attempted, payment_received
  agent_note TEXT,      -- LLM-generated summary
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Voucher Queue
CREATE TABLE voucher_queue (
  id UUID PRIMARY KEY,
  filename TEXT NOT NULL,
  file_path TEXT NOT NULL,
  status TEXT DEFAULT 'pending',  -- pending, processing, posted, needs_review
  extracted_vendor TEXT,
  extracted_amount NUMERIC(12,2),
  extracted_date DATE,
  accounting_entry_id TEXT,
  confidence FLOAT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Customer Outreach
CREATE TABLE outreach_schedule (
  id UUID PRIMARY KEY,
  customer_name TEXT NOT NULL,
  last_contact DATE,
  next_contact DATE,
  cadence_days INTEGER DEFAULT 30,
  agent_note TEXT,
  status TEXT DEFAULT 'pending'
);
```

### 5. Cron Job Definitions

```json
{
  "jobs": [
    {
      "id": "ar_daily_check",
      "schedule": "0 8 * * 1-5",
      "prompt": "Check AR ledger for invoices 90+ days past due. For each, generate a collection letter. Log activity. Report what was sent.",
      "deliver_to": "slack",
      "profile": "ar_watcher"
    },
    {
      "id": "voucher_watchdog",
      "schedule": "*/15 * * * *",
      "prompt": "Check voucher_queue for pending files. For each, run OCR extraction, determine vendor/amount/date, attempt accounting entry. Flag low-confidence items for human review.",
      "deliver_to": "slack",
      "profile": "voucher_scanner"
    },
    {
      "id": "outreach_daily",
      "schedule": "0 9 * * 1-5",
      "prompt": "Check outreach_schedule for customers due for contact today. Generate personalized outreach notes. Report who was contacted.",
      "deliver_to": "slack",
      "profile": "outreach_agent"
    }
  ]
}
```

### 6. Collection Letter Templates
Skills that the AR agent loads at runtime.

```markdown
# ar_collection_letter_friendly

## Trigger
Invoice 60-89 days past due.

## Template
Subject: Quick check-in on invoice #{invoice_id}

Hi {contact_first_name},

I noticed invoice #{invoice_id} for ${amount} dated {invoice_date} 
is showing as outstanding on our end. 

No rush — just wanted to make sure it didn't slip through the cracks. 
Let me know if you need anything from us to get this processed.

Thanks,
{user_name}

## Variables
- invoice_id, amount, invoice_date → from ar_invoices
- contact_first_name → from contacts table
- user_name → from config
```

## Phase Plan

### Phase 0: Learn Hermes (1 day)
- Install Hermes on development machine
- Run `hermes setup`, configure Discord
- Test full agent loop with DeepSeek
- Understand profiles, skills, cron, MCP
- Run `hermes claw migrate` just to see what it imports
- Verify Cognee + Google Workspace MCP servers work from Hermes

### Phase 1: Identity Migration (1 day)
- Convert `soul.md` → Hermes personality format
- Port `skills/` directory → Hermes SKILL.md format (frontmatter + content)
- Map `.env` variables → Hermes config.yaml
- Verify Discord bot works with new identity

### Phase 2: Wire Cognee (1 day)
- Add Cognee to Hermes MCP config (HTTP server, `localhost:8000`)
- Register `cognee__memorize` and `cognee__query` tools
- Lift `cognee-server/` as-is — no code changes
- Test: agent can learn facts and query the graph

### Phase 3: Wire PostgreSQL + Supabase (1 day)
- Add PostgreSQL to Hermes MCP config
- Deploy AR/voucher/outreach schema
- Test: agent can query invoices, insert vouchers

### Phase 4: Multi-Agent Profiles (1 day)
- Create 3 profiles: ar_watcher, voucher_scanner, outreach_agent
- Each with scoped skills and tools
- Each with its own personality
- Test: agent A can't see agent B's tools

### Phase 5: Cron + Business Logic (2 days)
- Define cron jobs for AR check, voucher scan, outreach
- Build collection letter templates as skills
- Build voucher extraction pipeline prompt
- Build outreach cadence logic
- Test end-to-end: overdue invoice → letter generated → Slack delivery

### Phase 6: Per-Org Deployment (2 days)
- Write provisioning script:
  ```bash
  #!/bin/bash
  # deploy-hermes-argus.sh <org_name> <modules>
  # Example: deploy-hermes-argus.sh acme-corp ar_collections,voucher_processing
  ```
- Docker Compose for Cognee + PostgreSQL (Hermes runs native)
- Config templating for org-specific settings
- ICM skill curation: copy only selected modules
- Webhook setup for Slack
- Test clean deploy → working agent

### Phase 7: Human Review Pipeline (1 day)
- Collection letters → draft → Slack review channel
- Voucher extraction with low confidence → review queue
- Approval button before delivery
- Audit log of all agent actions

**Total estimated effort: ~10 development days**

## Decision Points

1. **Cognee: MCP wrapper or HTTP?** HTTP is immediate (Cognee already exposes REST endpoints). MCP wrapper is cleaner architecture. Start HTTP, wrap later.

2. **Memory plugin: Cognee alone or Cognee + Hindsight?** Cognee for graph, Hindsight for session-level recall. Use both — Hermes supports multiple memory plugins.

3. **Slack: native or webhook-only?** Hermes has native Slack gateway. Use it for full interaction. Webhooks for cron delivery only.

4. **Google Workspace: keep or replace?** Keep `google-tools/` as-is. Hermes discovers it via MCP. No porting needed.

5. **Argus repo: archive or maintain?** Archive as reference. The rebase replaces it operationally.

## Success Criteria

- [ ] Hermes agent responds on Discord with Argus identity
- [ ] `core__memorize_graph` works → queries return graph results
- [ ] `core__query_graph` returns entity-relationship data from Cognee
- [ ] Google Workspace tools available (Gmail send, Calendar create)
- [ ] 3 agent profiles running: AR, vouchers, outreach
- [ ] Cron delivers collection letter to Slack
- [ ] Voucher PDF → OCR → accounting entry (with confidence review)
- [ ] Clean per-org deployment in under 30 minutes
- [ ] Human review gate on all outgoing agent actions
