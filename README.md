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

## License

MIT
