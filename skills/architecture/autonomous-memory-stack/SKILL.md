1|---
2|name: autonomous-memory-stack
3|description: |
4|  Architecture analysis of combining Hermes, Cognee, and OpenBrain/OB1 into a
5|  self-improving cognitive system for persistent agent memory.
6|  DO NOT use for: specific memory operations, troubleshooting current memory issues.
7|category: architecture
8|domain: system-design
9|intent:
10|  - memory-architecture
11|  - cognitive-stack
12|  - agent-memory
13|exclusions:
14|  - memory-troubleshooting
15|  - specific-operations
16|requires: []
17|phase: design
18|compatible_with: []
19|conflicts_with: []
20|handoff_to:
21|  - local-postgres-to-supabase-migration
22|scope: local-only
23|data_access:
24|  mcp_servers: []
25|  secrets: []
26|  trust_level: standard
27|governed_by: []
28|version: 1.0.0
29|compatibility:
30|  min_runtime: hermes-1.0
31|deprecated: false
32|deprecation_notes: ""
33|examples:
34|  - "Designing a multi-tenant knowledge system for SMB clients"
35|  - "Planning memory architecture for a new agent deployment"
36|---
37|# Hermes + Cognee + Open Brain: Self-Improving Cognitive Stack
38|
39|## The Four Pillars
40|
41|| Component | Role | Status |
42||-----------|------|--------|
43|| Hermes | Agent runtime, MCP loop, gateway management | ✅ Active |
44|| Cognee | Enterprise knowledge graph, vector memory, entity resolution | ✅ Active |
45|| OpenBrain (OB1) | Postgres DB — structured business data | ✅ Active |
46|
47|## Architecture
48|Hermes orchestrates the agent loop. Cognee provides long-term memory via knowledge graphs and embeddings. OpenBrain stores structured business data (invoices, contacts, cron results).
49|
50|## Key Design Decisions
51|- Cognee is the graph/vector layer — not the relational layer
52|- OpenBrain (Postgres) is the structured data layer
53|- Hermes bridges both via MCP
54|- Skills are the procedural knowledge layer (filesystem, not database)
55|