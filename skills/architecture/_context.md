---
name: skills-context-architecture
description: Domain context for architecture skills — system design, memory stacks, deployment patterns, and infrastructure strategy for the Development lane.
category: architecture
metadata:
  hermes:
    tags: [context, architecture, domain]
    related_skills: [autonomous-memory-stack, local-postgres-to-supabase-migration, ollama-jit-vision-model]
---

# Architecture Domain — 🏗️ Development Lane

This domain handles system architecture design, memory stack composition, infrastructure patterns, and deployment strategy.

**Lane:** Development — engineering agents and build tooling.

**Skills in this domain:**
- **autonomous-memory-stack** — Hermes + Cognee + OpenBrain self-improving cognitive stack
- **local-postgres-to-supabase-migration** — SMB database migration strategy from local Postgres to Supabase cloud
- **ollama-jit-vision-model** — Just-in-time Ollama vision model loading for VRAM efficiency

**Rules for this domain:**
- Prefer Supabase-first architecture for SMB deployments
- Document architecture decisions alongside implementation
- Reference `_config/lane-conventions.md` for frontmatter standards
