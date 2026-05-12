# Hermes-Argus — Current State

> Single source of truth for session orientation.
> Read at session start. Update before every PR.

## Last Updated
- **Date:** 2026-05-12
- **By:** Claude Code (persona-contract architecture rollout session)
- **Triggering work:** ADR-0002 scaffold

## Where We Are

Hermes-Argus is the active gateway / orchestration / agent runtime — successor to the Argus repo (renamed from Hermeclaw earlier). Houses cognee-server with MCP wrappers (slack, postgres, vision) — the superset of code originally in Argus. Production-grade with Phase 3–7 runbooks deployed (watchdog, deployment hardening, agent system prompt).

As of 2026-05-12, persona + contract architecture (ADR-0002) scaffolded. Hermes-Argus is a strong candidate for early persona-contract adoption since its job IS multi-agent orchestration.

## Active Work
- _(check `git branch` and open PRs for in-flight state)_
- Untracked working tree: `config/hermes.yaml` modified, plus `cognee-server/vision_mcp.py`, `gh-comment-5.txt`, `skills/content/vision-analysis/`, `thumbnail.jpg` untracked — clarify before committing

## Recent Wins (last 7 days)
- **2026-05-12:** Persona + contract architecture scaffold (PR #6)
- **2026-05-12:** factory.json pinned to ai-factory @9c6c537 (PR #7)
- **2026-05-11:** Gateway outage recovery; Slack + Discord reconnected at 14:31 UTC
- **Earlier:** Phase 3–7 runbooks shipped (Slack reactions, watchdog, deployment hardening, agent system prompt)

## Open Items
| Issue | What | Status |
|---|---|---|
| _add when next session opens_ | check GitHub | — |

## Live State

- **Default branch:** `master` (NOT `main`)
- **Stack:** Python (cognee-server), TypeScript (src/), Docker
- **cognee-server modules:** main.py + mcp_wrapper.py + postgres_mcp.py + slack_mcp.py + vision_mcp.py + entrypoint.sh
- **Gateway PID (when running):** 25800 was the last known on 2026-05-11 after manual restart
- **Auto-start:** none yet — gateway needs manual restart after machine sleep/reboot (Windows Task Scheduler entry or startup script proposed but not yet built)
- **Factory binding:** ai-factory @9c6c537 (LOCAL-only mode)
- **Personas active:** none yet
- **Contracts active:** none yet

## Pointers

- **Factory binding:** [`factory.json`](factory.json)
- **Universal ADR-0002:** `ai-factory/knowledge/decisions/0002-persona-contract-architecture.md`
- **CURRENT-STATE.md playbook:** `ai-factory/docs/playbooks/current-state-md.md`
- **Predecessor repo:** [Russell-Shirley/Argus](https://github.com/Russell-Shirley/Argus) (archived — cognee code superseded here)

## Runbook candidates (not yet authored)
- Gateway recovery after Discord shard teardown / Slack DNS executor death (May 8 2026 incident pattern)
- Auto-start via Windows Task Scheduler
- cognee-server health check + restart

## Next Session Checklist
1. Read this file
2. `git status` — clarify untracked working tree before committing anything
3. Check gateway running (`tasklist | findstr <pid>`)
4. Update "Active Work" with what you're starting
5. Before PR, refresh "Last Updated"
