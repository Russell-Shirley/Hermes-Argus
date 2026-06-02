# Hermes-Argus — Context Routing

This is the **Layer 1 routing document** (MWP protocol). It maps user requests and task types to skill domains.

---

## Three Operational Lanes

The repo organizes skills into **three physical lanes** — `skills/<lane>/<domain>/<skill>/SKILL.md` —
matching how Bridge and Bolt operates (canonical: `ai-factory` ADR-0003 / `_config/lane-conventions.md`).
Note: the Hermes runtime store (`~/.hermes/skills/`) is **flat by skill name**; the lane/domain
folders are organizational only and do not change runtime layout.

### 🏗️ Lane 1: Development
*Who:* Engineering agents, infrastructure, build tooling
*Domains:* `development/architecture/` • `development/ops/` • `development/content/`
*What:* System design, deployment patterns, monitoring, backup/recovery, browser automation, vision processing, design patterns

| Request type | Domain | First skill to check |
|---|---|---|
| System architecture, memory stack design | `architecture/` | `autonomous-memory-stack` |
| Database migration, Supabase strategy | `architecture/` | `local-postgres-to-supabase-migration` |
| Ollama model loading, VRAM optimization | `architecture/` | `ollama-jit-vision-model` |
| Backup, DR, restore | `ops/` | `argus-disaster-recovery` |
| Slack status protocol, emoji conventions | `ops/` | `argus-slack-emoji-protocol` |
| Gmail API setup, email reading | `ops/` | `gmail-api-integration` |
| Browser automation, page scraping | `ops/` | `puppeteer-web-browsing` |
| Image analysis, screenshot OCR | `content/` | `vision-analysis` |
| UX/UI design patterns, design system refs | `content/` | `ui-design-models` |
| Product vision, app design docs | `content/` | `water-safety-app-vision` |

### 🤝 Lane 2: Client Services
*Who:* Client-facing agents, onboarding flows
*Domains:* `client-services/clients/`
*What:* Outreach workflows, CRM updates, onboarding playbooks, communication drafting

| Request type | Skill / Context |
|---|---|
| Client outreach, CRM tasks | `clients/_context.md` (skills pending) |
| Client communication drafts | `clients/_context.md` (skills pending) |

### 🏢 Lane 3: Business / Internal
*Who:* Strategy agents, board materials, internal operations
*Domains:* `business-internal/business/`
*What:* Revenue strategy, competitive research, agent framework comparisons, presentations

| Request type | Domain | First skill to check |
|---|---|---|
| Service offerings, pricing, revenue strategy | `business/` | `ai-smb-consulting-quick-cash-strategy` |
| Agent orchestration framework research | `business/` | `multi-agent-orchestration-framework` |
| On-prem agent deployment framework | `business/` | `workmate-agent-framework` |
| HTML presentations, cinematic decks | `business/` | `cinematic-html-presentation` |

---

## Shared Reference Material

Cross-domain conventions live in `_config/` at repo root:

- `_config/lane-conventions.yaml` — rules shared across all three lanes
- `_config/agents-conventions.yaml` — AGENTS.md invariant bindings

Each domain's `_context.md` references the `_config/` files it depends on.

---

## How to Route

1. Read the user's request
2. Match the **request type** to a lane and domain using the tables above
3. Load the domain `_context.md` for domain-specific rules
4. Load the matching skill's `SKILL.md` for the procedure
5. Load any `references/*.md` that the skill specifies
