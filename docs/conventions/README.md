# Conventions

**Living documents that describe how this project operates.** Edited as we learn.

Different from ADRs:
- **ADR** = point-in-time decision, immutable, supersedable
- **Convention** = living rules of the road

Different from Plans:
- **Plan** = one-time rollout, archived when complete
- **Convention** = ongoing operating model the plan produces

## Format
- Frontmatter: `name`, `description`, `type: convention`, `date`, `status`, `implements` (link to driving ADR)
- Body: how-we-do-it prose, updated as learnings accrue
- Footer: changelog with date + change summary (keeps "living" history visible)

## When to add
- After a Plan completes and steady-state behavior needs to live somewhere
- When a way of working has survived ≥2 sessions and should be canonized
- When multiple ADRs touch the same operating area and a synthesis is needed
