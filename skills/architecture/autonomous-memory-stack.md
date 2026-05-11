---
name: autonomous-memory-stack
description: Architecture analysis of combining Hermes (agent runtime), ICM (curiosity-driven learning), Cognee (enterprise knowledge graph), and Open Brain/OB1 (personal episodic memory) into a self-improving cognitive system.
trigger: When designing or discussing the memory architecture, self-improving agent loops, or multi-tenant knowledge systems.
category: architecture
metadata:
  hermes:
    tags: [architecture, memory, cognee, ob1, icm, hermes, self-improving]
    related_skills: [argus-slack-emoji-protocol, local-postgres-to-supabase-migration]
---

# Hermes + ICM + Cognee + Open Brain: Self-Improving Cognitive Stack

## The Four Pillars

| Component | Role |
|---|---|
| **Hermes** | Agent runtime / task orchestration. Executes tool calls, manages sessions, handles delivery. |
| **ICM (Intrinsic Curiosity Module)** | Boredom/exploration engine — drives the system to explore uncertain or novel states rather than just optimizing for reward. |
| **Cognee** | Enterprise knowledge graph / long-term relational memory. Structured, multi-tenant, ontology-aware. |
| **Open Brain (OB1)** | Personal episodic memory + pattern discovery. Contradiction detection, wiki compilation, semantic search via Supabase/pgvector. |

## Two-Tier Memory Architecture (Episodic + Semantic)

- **Open Brain (Episodic):** Raw thoughts, decisions, meetings, contradictions. Temporal context. Queries: "What did I decide about X last quarter?"
- **Cognee (Semantic):** Entities, relationships, ontologies, pipelines. Structured graph. Queries: "Which entities relate to X and how?"

Combined: Agent can recall facts (Cognee) AND the context/why behind them (OB1).

## ICM-Driven Self-Improving Agent Loop

1. Hermes runs task → logs interaction
2. OB1 captures episode with type (decision/insight/failure/etc.)
3. Cognee stores structured relationships (tools ↔ skills ↔ outcomes)
4. ICM analyzes: prediction error spikes → which task types/tools/domains consistently surprise
5. High novelty/failure → trigger skill creation:
   - Pull past episodes from OB1
   - Query Cognee for related entities
   - Compile new skill via skill_manage
   - Skill becomes part of memory → loop repeats

## Contradiction-Proof Knowledge

OB1 detects contradictions → Cognee graph edges locked pending resolution → timestamped overrides → validates memories against each other.

## Multi-Tenant Personalization

- Each tenant gets OB1 episodic store + shared Cognee global graph
- ICM adapts per-tenant (one team's novel is another's routine)
- Contradictions tenant-scoped but can bubble to global ontology

## Architecture Concerns

| Concern | Mitigation |
|---|---|
| **Latency** | Async writes, batch contradictions |
| **Storage bloat** | Compaction/archival via wiki compilation summarization |
| **ICM false positives** | Threshold/triage layer + graph_metrics as confidence signal |
| **Skill quality** | Human-in-the-loop review for auto-generated skills |

## Elevator Pitch

"You get an agentic system that doesn't just remember — it learns how to improve its own skills by exploring uncertainty (ICM), storing both facts (Cognee) and context (OB1), and closing the loop through Hermes execution."

Cognee = textbook. OB1 = journal. ICM = curiosity. Hermes = the hands doing the work.