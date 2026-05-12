# Runbooks

**Single-scenario operational response procedures.** "If X happens, do Y."

Different from Playbooks:
- **Playbook** = proactive work execution
- **Runbook** = reactive incident response

## When to add
- An incident occurred and recovery steps are now known
- An external dependency has a documented failure mode
- A scheduled operation (cron, deploy) needs a fail-safe procedure

## Format
- Frontmatter: `name`, `description`, `type: runbook`, `date`, `severity` (sev-1..sev-3), `last_drill`
- Body: trigger, diagnosis steps, recovery steps, escalation, post-incident actions
