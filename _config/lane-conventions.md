# Lane Conventions — Shared Across All Three Operational Lanes

This file defines conventions that apply across all skill domains.
Each `_context.md` may reference specific sections of this file.

## General Rules

- All skills use **lowercase-hyphens** naming in frontmatter (not UPPERCASE_SNAKE).
- Every skill must have: `name`, `description`, `category`, `domain`, `intent`, `exclusions`, `requires`, `phase`, `scope`, `data_access`, `governed_by`, `version`, `compatibility`, `examples`.
- Every skill lives at `skills/<category>/<skill-name>/SKILL.md` — no flat files.
- Reference material lives in `references/` alongside the skill, not in SKILL.md body.
- Do not create the `CURRENT_STATE.md` duplicate — use `CURRENT-STATE.md` (hyphenated).

## Three-Lane Mapping

| Lane | Domain folders | Used by |
|------|---------------|---------|
| Development | architecture, ops, content | Engineering agents, infrastructure |
| Client Services | clients | Client-facing agents |
| Business/Internal | business | Strategy, board materials, internal ops |

## Frontmatter Template (ICM lowercase-hyphens style)

```yaml
---
name: skill-name
description: |-
  Brief one-paragraph description of what this skill does.
  DO NOT use for: what this skill should NOT handle.
category: <domain-folder-name>
domain: <specific-subdomain>
intent:
  - action-tag
  - another-tag
exclusions:
  - out-of-scope-tag
requires:
  - required-tool-or-dependency
phase: planning|design|operations|maintenance|research
compatible_with:
  - another-skill-name
conflicts_with: []
handoff_to:
  - downstream-skill-name
scope: local-only|liftable
data_access:
  mcp_servers: []
  secrets: []
  trust_level: standard|tenant-data|admin
governed_by: []
version: 1.0.0
compatibility:
  min_runtime: hermes-1.0
deprecated: false
deprecation_notes: ""
examples:
  - "Example task this skill handles"
---
```

## File Path Conventions

- `skills/<category>/_context.md` — domain routing (Layer 1)
- `skills/<category>/<skill-name>/SKILL.md` — skill procedure (Layer 2)
- `skills/<category>/<skill-name>/references/*.md` — reference material (Layer 3)
- `skills/<category>/<skill-name>/output/` — working artifacts (Layer 4, gitignored)
- `_config/*.yaml` — cross-domain shared reference material (Layer 3 shared)
- `CONTEXT.md` at repo root — top-level routing (Layer 1 root)
