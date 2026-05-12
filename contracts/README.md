# Contracts (LOCAL)

Enforceable invariants for this project. See `ai-factory/knowledge/decisions/0002-persona-contract-architecture.md` for the architecture.

## Format

Each contract is a markdown file with frontmatter:

```yaml
---
id: <phase>/<slug>
scope: local
phase: dev | test | closeout | invariant
predicate: |
  <shell snippet; exit 0 = pass, non-zero = fail>
enforcement: advisory | logging | blocking
---
```

Body sections:
- `## Rule` — the invariant in plain English
- `## Rationale` — why this exists (evidence, prior incident links)
- `## Failure remediation` — what to do when the predicate fails
- `## Examples` (optional)

## Layout
```
contracts/
  invariants/    — cross-phase rules (always loaded)
  dev/           — dev-phase rules
  test/          — test-phase rules
  closeout/      — closeout-phase rules
```

## Promotion to UNIVERSAL
After evidence from ≥2 projects with consistent behavior, a LOCAL contract is a candidate for promotion to `ai-factory/contracts/`. See operating model in `docs/conventions/` for the ceremony.

## Conflict with UNIVERSAL
Same `id` here overrides UNIVERSAL for this project. Different `id` is additive.
