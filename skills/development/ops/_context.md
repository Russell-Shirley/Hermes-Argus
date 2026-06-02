---
name: skills-context-ops
description: Domain context for operations skills — automation scripts, cron jobs, browser automation, database migrations, infrastructure, backup/recovery, and Slack protocol for the Development lane.
category: ops
metadata:
  hermes:
    tags: [context, ops, domain]
    related_skills: [argus-disaster-recovery, argus-slack-emoji-protocol, gmail-api-integration, puppeteer-web-browsing]
---

# Operations Domain — 🏗️ Development Lane

This domain handles automated scripts, background cron jobs, browser automation, database migrations, infrastructure tasks, backup/disaster recovery, and Slack operational protocols.

**Lane:** Development — engineering agents and build tooling.

**Skills in this domain:**
- **argus-disaster-recovery** — Complete disaster recovery procedures for the Hermes-Argus agent stack
- **argus-slack-emoji-protocol** — Emoji-based status indicators for Slack conversations
- **gmail-api-integration** — Gmail API setup, OAuth flow, and email reading
- **puppeteer-web-browsing** — Browser navigation and page content extraction

**Rules for this domain:**
- Prioritize reliability and logging
- Any new web scraping workflow must be documented here as a skill
- Reference `_config/lane-conventions.md` for frontmatter standards
