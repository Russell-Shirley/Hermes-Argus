# Hermes-Argus

Managed AI agent appliances for SMBs. Built on [Hermes Agent](https://github.com/NousResearch/hermes-agent) with Cognee graph memory and ICM skill scaffolding.

## Architecture

```
Hermes Gateway (Discord/Slack)
├── Agent: AR Watcher     → Collections letters, aging alerts
├── Agent: Voucher Scanner → OCR → accounting entry
├── Agent: Outreach       → Customer contact cadence
├── Agent: Inventory      → Stock alerts, reorder points
├── Agent: Invoicing      → Bill generation, recurring
└── Agent: Payroll        → Time tracking, payroll prep

Cognee Graph (entity-relationship memory)
├── DeepSeek extraction
├── PostgreSQL nodes/edges
└── Graph + vector hybrid search

Supabase/PostgreSQL
├── AR ledger
├── Voucher queue
├── Outreach schedule
└── Per-module schemas
```

## Structure

```
modules/           ICM skill modules (curated per deployment)
  icm_base/        Core: memory, graph, safety (every org)
  ar_collections/  AR aging, collection letters
  voucher_processing/  OCR → accounting
  customer_outreach/   Contact cadence
  inventory/       Stock alerts, reorder points
  invoicing/       Bill generation
  payroll/         Time tracking

config/
  profiles/        Agent personality + tool scoping
  cron/            Scheduled job definitions
  hermes.yaml      Base Hermes configuration template

deploy/            Per-org provisioning scripts
schema/            PostgreSQL table definitions
templates/         Collection letters, outreach scripts, etc.
cognee-server/     Cognee graph memory (custom DeepSeek fork)
google-tools/      Google Workspace MCP server
```

## Deployment

```bash
# Provision a new org appliance
./deploy/provision.sh acme-corp ar_collections,voucher_processing,invoicing
```

## LLM Mode Toggle (DeepSeek vs Local Gemma)

The reasoning LLM (used for Cognee graph extraction) can be switched without rebuilding the container. Embedding always uses local Ollama.

| Mode | Model | Cost | Use when |
|------|-------|------|----------|
| `deepseek` | deepseek-chat (DeepSeek API) | Paid per token | Production quality extractions |
| `gemma` | gemma3:4b (local Ollama) | Free | Offline dev, low-power, cost-zero testing |

### Switching modes

```powershell
# Switch to local Gemma (free, offline)
.\scripts\switch-llm.ps1 gemma

# Switch back to DeepSeek (paid, high-quality)
.\scripts\switch-llm.ps1 deepseek
```

Then restart the container to apply:

```bash
docker compose -p hermes-argus restart cognee-server
```

### Prereq for gemma mode

```bash
ollama pull gemma3:4b
```

### How it works

`docker-compose.yml` loads two env files in order — `cognee-server/.env` (DB + embedding, always loaded) then `cognee-server/.env.llm.active` (LLM vars, overrides). The toggle script swaps `.env.llm.active` between the `deepseek` and `gemma` profiles.

**Default after fresh clone:** deepseek mode. `.env.llm.deepseek` and `.env.llm.active` are gitignored (contain the API key). Copy `.env.llm.deepseek` from your secrets store or set `LLM_API_KEY` manually. `.env.llm.gemma` is committed — no secrets.

## License

MIT
