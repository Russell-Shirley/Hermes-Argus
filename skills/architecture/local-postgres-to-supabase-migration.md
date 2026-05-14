---
name: local-postgres-to-supabase-migration
description: |
  Strategy for providing SMB clients a "start local (Postgres/Docker), migrate to
  Supabase cloud later" path. Covers Supabase-first Docker strategy, resource tuning,
  migration button logic, and hard truths.
  DO NOT use for: production migration execution, or non-SMB scale scenarios.
category: architecture
domain: infrastructure
intent:
  - database-migration
  - supabase-deployment
  - smb-architecture
exclusions:
  - production-migration
  - enterprise-scale
requires:
  - docker
  - supabase-cli
phase: planning
compatible_with:
  - autonomous-memory-stack
conflicts_with: []
handoff_to: []
scope: liftable
data_access:
  mcp_servers: []
  secrets: [SUPABASE_API_KEY]
  trust_level: tenant-data
governed_by: []
version: 1.0.0
compatibility:
  min_runtime: hermes-1.0
deprecated: false
deprecation_notes: ""
examples:
  - "Advising a clinic client on scaling from local Docker to Supabase cloud"
  - "Planning a migration path for a multi-location veterinary practice starting local"
---
# Local Postgres → Supabase Migration for SMB Clients

## Core Philosophy: Supabase-First From Day One

Bundle the **Supabase Docker stack** (not raw Postgres) so local = cloud parity from day zero. Migration is a config change — update API_URL and API key. No schema drift, no compatibility surprises.

## Strategy
1. Start with Supabase Docker for local dev
2. Tune shared_buffers (25% RAM), work_mem (64MB), max_wal_size (1-2GB)
3. Use `supabase db push` for schema, `pg_dump` pipe for data
4. Include S3 backup + reverse proxy in Docker image
5. Bill as "Scale-up Transition" service

## Hard Truths
- Migration is still a production event — test thoroughly
- Supabase managed Postgres has different resource limits than local Docker
- Row-level security (RLS) must be designed upfront, not added at migration
