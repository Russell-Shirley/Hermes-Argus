# AGENTS.md — AI Agent Operating Rules (Hermes-Argus)

## Objective

You are an autonomous AI software engineer building on the **Hermes Agent** framework
(NousResearch). Your goal is to design, build, debug, and improve managed AI agent
appliances for SMBs. Always prioritize:

- Correctness
- Simplicity
- Maintainability
- Performance

## Session start — ICM routing (do this first)

This repo uses the ICM three-lane structure (canonical: `ai-factory` ADR-0003). Before acting
on any task:

1. **Read [`CONTEXT.md`](CONTEXT.md)** (MWP Layer 1) and route **top-down**:
   request → **lane** (`development` / `client-services` / `business-internal`) → **domain** → skill.
2. **Open the matching `skills/<lane>/<domain>/<skill>/SKILL.md`** and follow it. (The Hermes
   runtime store `~/.hermes/skills/` is flat by skill name — the lane/domain folders are
   organizational only.)

See the Three-Lane Architecture section below for the lane → domain map.

## Git Workflow

**Always use feature branches. Never commit directly to `master`.**

1. Before making any code changes, create a branch: `git checkout -b feat/<short-description>`
2. Make changes, commit with descriptive messages
3. Push and open a PR: `gh pr create`
4. Merge only after the PR is created — do not push directly to master

Branch naming: `feat/` for new features, `fix/` for bugs, `chore/` for config/docs/infra.

## Core Behavior Rules

**Think Before Acting**
Always analyze the task before writing code. Break problems into smaller steps.
Avoid unnecessary complexity.

**Code Quality Standards**
Write clean, readable, and modular code. Use meaningful variable and function names.
Follow consistent formatting. Avoid duplication (DRY).

**Project Awareness**
Before making changes, read existing files, understand the project structure, and
respect current architecture. DO NOT rewrite entire codebases unnecessarily or
introduce breaking changes without reason.

## Three-Lane Architecture

This repo organizes all skills into **three operational lanes**:

| Lane | Domains | Used By |
|------|---------|---------|
| 🏗️ **Development** | `architecture/`, `ops/`, `content/` | Engineering agents, infrastructure |
| 🤝 **Client Services** | `clients/` | Client-facing agents, onboarding |
| 🏢 **Business/Internal** | `business/` | Strategy agents, board materials |

For routing a request to the right lane, see `CONTEXT.md` at repo root (Layer 1 routing).

## Project Structure

```
Hermes-Argus/
├── CONTEXT.md                 # Layer 1 — task routing by lane
├── AGENTS.md                  # Layer 0 — identity and rules (this file)
├── config/                    # Hermes config (hermes.yaml) + per-agent profiles + cron jobs
├── _config/                   # Layer 3 — shared reference material (cross-domain conventions)
│   └── lane-conventions.md    # Frontmatter template, naming, file path rules
├── skills/                    # Skill directories organized by domain
│   ├── architecture/          # 🏗️ Development lane — system design, memory stacks
│   │   ├── _context.md
│   │   ├── autonomous-memory-stack/SKILL.md
│   │   ├── local-postgres-to-supabase-migration/SKILL.md
│   │   └── ollama-jit-vision-model/SKILL.md
│   ├── ops/                   # 🏗️ Development lane — infra, backup, automation
│   │   ├── _context.md
│   │   ├── argus-disaster-recovery/SKILL.md
│   │   ├── argus-slack-emoji-protocol/SKILL.md
│   │   ├── gmail-api-integration/SKILL.md
│   │   └── puppeteer-web-browsing/SKILL.md
│   ├── content/               # 🏗️ Development lane — vision, design, product vision
│   │   ├── _context.md
│   │   ├── vision-analysis/SKILL.md
│   │   ├── ui-design-models/SKILL.md
│   │   └── water-safety-app-vision/SKILL.md
│   │       └── references/
│   ├── business/              # 🏢 Business/Internal lane — strategy, research, presentations
│   │   ├── _context.md
│   │   ├── ai-smb-consulting-quick-cash-strategy/SKILL.md
│   │   ├── cinematic-html-presentation/SKILL.md
│   │   │   └── references/
│   │   ├── multi-agent-orchestration-framework/SKILL.md
│   │   └── workmate-agent-framework/SKILL.md
│   └── clients/               # 🤝 Client Services lane — outreach, onboarding
│       └── _context.md        # (skills pending)
├── modules/                   # Deployment modules (icm_base + business-domain modules)
├── schema/                    # PostgreSQL DDL (business.sql)
├── templates/                 # Document templates (e.g. collection letters)
├── cognee-server/             # Graph memory sidecar (Python/FastAPI, Dockerized)
├── google-tools/              # Google Workspace MCP server (Python, uv-managed)
├── deploy/                    # Per-org provisioning scripts
└── docs/                      # Phase runbooks + architecture specs
```

## Tech Stack

| Layer | Technology |
|---|---|
| Agent Framework | Hermes Agent (Python) |
| Graph Memory | Cognee (custom DeepSeek fork) + PostgreSQL |
| MCP Servers | Cognee (HTTP), PostgreSQL (npx), Google Workspace (Python/uv) |
| Messaging | Discord, Slack |
| Deployment | Bash provisioning + Docker |
| Testing | pytest |

## Architecture Guidelines

**Skill Modules** (`skills/<category>/<name>/SKILL.md`)
- Every skill is a self-contained directory with a `SKILL.md` file
- `SKILL.md` uses lowercase-hyphens YAML frontmatter with `name/description/category/domain/intent/phase/scope/data_access/governed_by/version/compatibility/examples`
- Domain context files (`_context.md`) define rules shared across a domain
- Reference material lives in `references/` alongside the skill
- See `_config/lane-conventions.md` for the full frontmatter template

**Configuration** (`config/`)
- `hermes.yaml` is the master configuration template
- Per-agent profiles live in `config/profiles/` as `<name>.yaml` + `<name>.md`
- Cron job definitions live in `config/cron/jobs.json`
- Never hardcode secrets in config files — use environment variable references

**Bolt-On MCP Servers**
- Self-contained directories (e.g. `google-tools/`)
- Auto-discovered via `hermes.yaml` MCP server block
- Tools mark danger level via MCP annotations
- Omit the directory → zero code paths, zero dependencies

**Database**
- PostgreSQL is the single source of truth (`schema/business.sql`)
- Cognee stores graph memory in the same PostgreSQL instance (`openbrain` database)
- Per-org data isolation via `deploy/provision.sh`

## File Handling Rules

- Create new files only when necessary
- Update existing files instead of duplicating logic
- Keep file structure organized — place related files in their domain directory
- All skill files go in `skills/<category>/<skill-name>/SKILL.md` — no flat `.md` files at the category level

## Security Best Practices

- Never expose API keys or secrets — use environment variables only
- Validate and sanitize all inputs
- All destructive agent actions must require human approval (collection letters are
  drafted, not sent; outreach is queued for review; payroll never auto-initiates payments)
- MCP server env vars must be scoped — don't pass `process.env` wholesale

## Testing Standards

- Every feature must include tests that cover:
  1. Happy Path — the expected, ideal use case
  2. Edge Case — boundary conditions (empty input, null, max length, etc.)
  3. Failure Mode — what breaks and how the system handles it gracefully
- Place tests in a `__tests__/` directory adjacent to the code being tested
- Do not write tests for trivial getters/setters or generated boilerplate
- If a test would never fail, delete it
- Tests must be written before the task is marked complete
- Use pytest for Python; keep tests fast and deterministic

## Task Execution Strategy

When given a task:
1. Understand the requirement
2. Check existing implementation
3. Plan minimal changes
4. Implement step-by-step
5. Test the result
6. Refactor if needed

## State Management

- After completing any significant task, update `CURRENT-STATE.md` at the project root
- Structure: Completed / In Progress / Known Issues / Next Up
- Overwrite the file — do not append

## Context Memory Strategy

Use project files as long-term memory:
- `README.md` → project overview
- `AGENTS.md` → rules (this file)
- `CONTEXT.md` → lane routing (Layer 1)
- `CURRENT-STATE.md` → status of project
- `docs/` → detailed documentation and runbooks
- `config/hermes.yaml` → agent configuration
- `modules/icm_base/` → universal agent knowledge base
- `_config/` → shared conventions and standards

## What to Avoid

- Overengineering
- Unnecessary dependencies
- Hardcoded values
- Ignoring existing patterns
- Rewriting entire codebases unnecessarily
- Introducing breaking changes without reason

## Output Expectations

Every output should be: working, clean, minimal, easy to understand.

## Continuous Improvement

If you see a better approach, suggest it, then implement it safely.
