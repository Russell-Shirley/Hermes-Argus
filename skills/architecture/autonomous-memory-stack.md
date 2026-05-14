---
name: autonomous-memory-stack
description: |
  Architecture analysis of combining Hermes, Cognee, and OpenBrain/OB1 into a
  self-improving cognitive system for persistent agent memory.
  DO NOT use for: specific memory operations, troubleshooting current memory issues.
category: architecture
domain: system-design
intent:
  - memory-architecture
  - cognitive-stack
  - agent-memory
exclusions:
  - memory-troubleshooting
  - specific-operations
requires: []
phase: design
compatible_with: []
conflicts_with: []
handoff_to:
  - local-postgres-to-supabase-migration
scope: local-only
data_access:
  mcp_servers: []
  secrets: []
  trust_level: standard
governed_by: []
version: 1.0.0
compatibility:
  min_runtime: hermes-1.0
deprecated: false
deprecation_notes: ""
examples:
  - "Designing a multi-tenant knowledge system for SMB clients"
  - "Planning memory architecture for a new agent deployment"
---
# Hermes + Cognee + Open Brain: Self-Improving Cognitive Stack

## The Four Pillars

| Component | Role | Status |
|-----------|------|--------|
| Hermes | Agent runtime, MCP loop, gateway management | ✅ Active |
| Cognee | Enterprise knowledge graph, vector memory, entity resolution | ✅ Active |
| OpenBrain (OB1) | Postgres DB — structured business data | ✅ Active |

## Architecture
Hermes orchestrates the agent loop. Cognee provides long-term memory via knowledge graphs and embeddings. OpenBrain stores structured business data (invoices, contacts, cron results).

## Key Design Decisions
- Cognee is the graph/vector layer — not the relational layer
- OpenBrain (Postgres) is the structured data layer
- Hermes bridges both via MCP
- Skills are the procedural knowledge layer (filesystem, not database)
