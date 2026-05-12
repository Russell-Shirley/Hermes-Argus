# Personas (LOCAL)

Role definitions for this project. See `ai-factory/knowledge/decisions/0002-persona-contract-architecture.md`.

## Format

```yaml
---
id: <persona>
version: 0.1.0
scope: local
phase: <all|dev|test|closeout>
reads: [contracts/invariants/*, contracts/<phase>/*]
owns: [<skill>, <skill>]
handoff_to: <next-persona> | null
extends: <universal-persona>@<version> | null
---
```

Body sections (target ≤60 lines):
- `## Identity` — what this persona does
- `## Decision rights` — what it decides without escalation
- `## Escalation` — when to defer
- `## Handoff` — context-package shape it produces/consumes

## Promotion
After ≥2 projects (or ≥2 sessions) exercise a LOCAL persona stably, candidate for promotion to `ai-factory/agents/`. Versioned at promotion (`<persona>@1.0.0`).

## Inheritance
A LOCAL persona may extend a UNIVERSAL via `extends: <universal-id>@<version>`. LOCAL fields shadow UNIVERSAL fields.
