# Claude Review: Our Open Brain vs Nate B Jones' OB1

> Paste this entire file into Claude. It provides everything needed to evaluate
> our Open Brain implementation against the canonical OB1 reference.

---

## What I want you to evaluate

I want you to compare our Open Brain implementation against Nate B Jones' canonical OB1 reference (https://github.com/NateBJones-Projects/OB1). Specifically:

1. **Schema design** — How do our `meeting_notes` and `sales_recordings` tables compare to OB1's `professional_contacts`/`contact_interactions`/`opportunities` pattern?
2. **OB1 conventions adopted** — We've implemented metadata.json, shared trigger functions, FTS GIN indexes, helper RPCs, and a Deno MCP tool server. What's done well? What's missing?
3. **Gaps vs OB1** — We don't have a universal `thoughts` table, pgvector embeddings, RLS, cross-table triggers, Supabase integration, or dashboard snippets. Are these intentional architectural differences or gaps we should address?
4. **MCP tool quality** — How does our Deno `index.ts` compare to OB1's `professional-crm/index.ts` in terms of tool surface, error handling, security, and completeness?
5. **What's next** — What's the single highest-leverage improvement we should make next?

---

## OUR ASSETS (read these first)

### 1. Our Schema DDL
**Path:** `Hermes-Argus/schema/openbrain-meetings.sql`

Our full DDL — read this file. It contains:
- `meeting_notes` table (topic, meeting_date, participants JSONB, duration_minutes, project, transcript_path, summary, notes, external_metadata JSONB)
- `sales_recordings` table (prospect_name, call_date, rep_name, duration_seconds, audio_file_path, transcript_path, call_outcome with CHECK constraint, notes, external_metadata JSONB)
- GIN FTS index on meeting_notes.topic
- Helper functions: `upsert_meeting_note()`, `upsert_sales_recording()`
- Joined view: `v_meetings_with_recordings`
- Shared trigger function: `update_updated_at_column()`
- Auto-update triggers on both tables

### 2. Our Extension Directory
**Path:** `Hermes-Argus/schema/openbrain-meetings-sales/`

Contains:
- `metadata.json` — OB1-style metadata (name, description, category, version, tags, difficulty, estimated_time, requires)
- `deno.json` — Imports `@modelcontextprotocol/sdk` and `pg`
- `index.ts` — MCP server with 6 tools over stdio transport:
  - `save_meeting_note` / `save_sales_recording` (upsert via helper functions)
  - `query_meetings` / `query_sales_recordings` (FTS and ILIKE search)
  - `get_meeting_stats` / `get_sales_pipeline` (aggregation queries)

### 3. Our OB1 Reference Doc
**Path:** `skills/ops/openbrain-meetings-sales/references/ob1-architecture.md`

A reference doc we wrote ourselves documenting OB1 patterns and where we differ.

### 4. Our Live Database (argus-openbrain Postgres)

Docker container, accessible via:
```bash
docker exec argus-openbrain psql -U postgres -d openbrain -c "YOUR SQL"
```

All 29 tables are in `public` schema — includes Cognee graph tables (`nodes`, `edges`, `data`, `queries`), our 2 new tables, plus auth/permission tables from Cognee. The relevant objects for this review:

**Our tables:** `meeting_notes`, `sales_recordings`
**Our functions:** `upsert_meeting_note()`, `upsert_sales_recording()`, `update_updated_at_column()`
**Our triggers:** `update_meeting_notes_updated_at`, `update_sales_recordings_updated_at`
**Our indexes:** 4 on meeting_notes (PK, date DESC, project, FTS on topic), 4 on sales_recordings (PK, date DESC, prospect, outcome)

---

## OB1 REFERENCE ASSETS (read these second)

### Core `thoughts` table (from OB1 docs/01-getting-started.md)
```sql
create table thoughts (
  id uuid default gen_random_uuid() primary key,
  content text not null,
  embedding vector(1536),
  metadata jsonb default '{}'::jsonb,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);
-- HNSW index for vector similarity
-- GIN index for metadata
-- Index on created_at desc
```

### Professional CRM Extension
**URL:** https://github.com/NateBJones-Projects/OB1/tree/main/extensions/professional-crm

Read ALL files in this directory:
- `schema.sql` — Three tables (professional_contacts, contact_interactions, opportunities) with RLS, FTS generated columns, triggers, search RPCs
- `index.ts` — Deno MCP tool implementations
- `metadata.json` — Extension metadata
- `README.md` — Documentation

### Enhanced Thoughts Schema
**URL:** https://github.com/NateBJones-Projects/OB1/blob/main/schemas/enhanced-thoughts/schema.sql

Adds columns to the core `thoughts` table: type, sensitivity_tier, importance, quality_score, source_type, enriched, status, status_updated_at. Includes FTS search RPC `search_thoughts_text()` with boolean operators, pagination, and metadata filtering.

### Agent Memory Schema
**URL:** https://github.com/NateBJones-Projects/OB1/blob/main/schemas/agent-memory/schema.sql

Sidecar tables for provenance, recall, write-back, and audit. References `thoughts` by `thought_id`. Has lifecycle_status, provenance_status, confidence scoring, review workflow.

### Brain Stats Daily Schema
**URL:** https://github.com/NateBJones-Projects/OB1/blob/main/schemas/brain-stats-daily/schema.sql

Aggregation RPCs for dashboard heatmaps — daily bucketing by source_type.

### Schema Template
**URL:** https://github.com/NateBJones-Projects/OB1/blob/main/schemas/_template/metadata.json

Standard metadata.json template with name, description, category, author, version, requires, tags, difficulty, estimated_time, created, updated.

### OB1 README
**URL:** https://github.com/NateBJones-Projects/OB1

Overall architecture: extensions/ (schema + tools), schemas/ (DDL only), primitives/ (building blocks), integrations/, dashboards/, docs/, recipes/.

---

## Key architectural differences to keep in mind

| OB1 | Bridge and Bolt | Why we differ |
|-----|----------------|--------------|
| Supabase (managed) | Docker Postgres (self-hosted) | We're single-tenant, no need for managed auth |
| `auth.uid()` RLS on every table | No RLS | Single-user system |
| `thoughts` universal table + sidecars | Cognee graph tables + our dedicated tables | Cognee already provides graph/vector storage — our tables are structured domain data on top |
| Deno MCP via OB1 server | MCP + Hermes skills | We have both access paths |
| pgvector for semantic search | Cognee graph + vector store | Different vector layer, same capability |
| Supabase dashboard snippets | Grafana (separate) | Dashboard layer, not schema |

---

## My questions for you

1. **Schema fitness** — Is the `meeting_notes` / `sales_recordings` table design idiomatic by OB1 standards? Would Nate have done it differently?
2. **Convention compliance** — We followed metadata.json, shared trigger functions, FTS GIN indexes, helper RPCs, and Deno MCP. What did we miss?
3. **MCP tool quality** — Does our `index.ts` need security hardening, better error handling, pagination at the tool level?
4. **Priority gap** — If you could add one thing from OB1 that we don't have (RLS, generated FTS columns, cross-table triggers, dashboard snippets, `thoughts` unified store), what would it be and why?
5. **Readiness** — Are we ready to wire this up for Claude Desktop / Cursor as-is, or are there blocker issues to fix first?
