---
name: local-postgres-to-supabase-migration
description: Strategy for providing SMB clients a "start local (Postgres/Docker), migrate to Supabase cloud later" path. Covers Supabase-first Docker strategy, resource tuning, migration button logic, and hard truths.
trigger: When advising clients on database scaling, planning Supabase migrations, or designing SMB deployment architectures.
category: architecture
metadata:
  hermes:
    tags: [postgres, supabase, migration, docker, smb, architecture]
    related_skills: [autonomous-memory-stack]
---

# Local Postgres → Supabase Migration for SMB Clients

## Core Philosophy: Supabase-First From Day One

Bundle the Supabase Docker Compose stack (not generic Postgres) as the base. This gives:
- **pgvector** for AI memory embeddings
- **GoTrue** for auth (no custom auth rewrite later)
- **PostgREST** for API layer
- **Schema parity** — local = cloud, so migration is config change, not schema rewrite

## Resource Guardrails for vector-heavy workloads

In the Docker image's `postgresql.conf`:

| Setting | Value | Why |
|---|---|---|
| `shared_buffers` | 25% of container RAM | Postgres buffer pool |
| `work_mem` | 64MB | Vector sorts in memory, not slow disk |
| `max_wal_size` | 1-2GB | Prevent frequent checkpoints during heavy ingestion |

## Migration Path (The "Button")

1. **Schema Sync** — Use Supabase migrations from day one (`supabase migration new`)
2. **Data Transfer** — Pipe pg_dump to remote:
   ```bash
   docker exec my_postgres_db pg_dump -U postgres | psql -h db.supabase.co -U postgres
   ```
3. **Switchover** — App updates `.env` from `localhost:5432` → `cloud:5432`

## Hard Truths to Tell Clients

1. **Backups** — Docker volumes on a single office PC will be forgotten. Build automated S3/Dropbox backup into the image.
2. **Networking/CORS** — Local Docker needs a reverse proxy (Caddy/Nginx) for SSL/HTTPS or modern AI tools won't connect.

## Business Model Angle

The migration becomes a billable "Scale-up Transition" service — a 5-minute technical move sold as a professional upgrade.

## Architecture Concerns

| Concern | Mitigation |
|---|---|
| **Auth rewrite** | Use GoTrue/Supabase Auth from day one |
| **Vector index RAM** | Test HNSW builds on target tier before promising |
| **Downtime** | pg_dump/pg_restore during maintenance window |
| **Extension drift** | Supabase stack local = Supabase cloud (1:1) |