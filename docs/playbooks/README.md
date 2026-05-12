# Playbooks

**Reusable how-to-execute-this-class-of-work documents.**

Different from Plans:
- **Plan** = one-time, archived
- **Playbook** = reusable, evolves with each execution

Different from Runbooks:
- **Playbook** = proactive ("how to ship X")
- **Runbook** = reactive ("when X breaks, do Y")

Different from Skills:
- **Skill** = invocable workflow with executable scripts
- **Playbook** = human-readable guide; a Skill is the codified, automatable version

A mature Playbook often graduates into a Skill once the steps are stable enough to script.

Existing flat-file playbooks (if any) predate this taxonomy and remain in place for historical reference. New playbooks follow the structured-folder pattern.

## Format
- Frontmatter: `name`, `description`, `type: playbook`, `date`, `last_used`, `status` (active | deprecated)
- Body: phases, decision points, hand-off boundaries
- Changelog at footer
