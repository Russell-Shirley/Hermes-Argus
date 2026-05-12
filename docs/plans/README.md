# Plans

**One-time implementation or rollout plans.** Archived to `plans/archive/` after completion.

Different from Conventions:
- **Plan** = one-time, archived when done
- **Convention** = ongoing operating model the plan produces

Different from Playbooks:
- **Plan** = "we will do X starting Y date"
- **Playbook** = "every time we encounter X, do Y"

## Format
- Frontmatter: `name`, `description`, `type: plan`, `date`, `status` (active | complete | abandoned), `implements` (ADR link)
- Body: sequence (Day 1 / Week 1 / Week 4), success criteria, owners
- After completion: move to `plans/archive/` and add `completed_date` + retrospective notes
