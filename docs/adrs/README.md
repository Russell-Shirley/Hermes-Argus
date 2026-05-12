# ADRs — Architecture Decision Records

ADRs live in `knowledge/decisions/` (numbered, immutable, supersedable).

This folder exists for taxonomy completeness. Legacy ADRs (if any) at flatter paths predate the `knowledge/` convention; new ADRs follow `knowledge/decisions/NNNN-slug.md`.

UNIVERSAL ADRs inherited from `../ai-factory/knowledge/decisions/` apply per the project's `factory.json` bindings. See `ai-factory/knowledge/decisions/0002-persona-contract-architecture.md` for the architectural decision driving this taxonomy.

## Format
See `ai-factory/knowledge/decisions/0001-security-posture-beta-vs-ga.md` for the canonical example.

Frontmatter fields:
- `name` — slug
- `description` — one-line summary
- `type: decision`
- `date` — ISO date
- `status` — proposed | active | superseded
- `supersedes` — link to prior ADR if any
