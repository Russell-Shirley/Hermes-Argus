---
name: ollama-jit-vision-model
description: |
  Pattern for JIT (just-in-time) loading of Ollama vision models on demand —
  load when image arrives, evict from VRAM immediately after, avoiding permanent
  VRAM residency.
  DO NOT use for: non-vision models, persistent model serving, batch image pipelines.
category: architecture
domain: infrastructure
intent:
  - jit-model-loading
  - vision-llm
  - vram-optimization
exclusions:
  - batch-processing
  - model-serving
  - non-vision-models
requires:
  - ollama
phase: design
compatible_with: []
conflicts_with: []
handoff_to:
  - vision-analysis
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
  - "Designing image ingestion for a document processing pipeline"
  - "Setting up occasional screenshot analysis without permanent VRAM usage"
---
# Ollama JIT Vision Model Pattern

## The Problem
Ollama models loaded with `keep_alive: -1` occupy VRAM permanently. On a system with limited VRAM (e.g., 8GB), keeping a 1.7GB vision model permanently resident blocks other workloads.

## The Pattern
Use JIT (just-in-time) lifecycle:
1. Before analysis: `ollama run moondream` loads the model
2. During analysis: model runs in VRAM
3. After analysis: model is evicted (`keep_alive: "0"` or timeout expires)

## Implementation
Set `keep_alive: "5m"` — the model stays loaded long enough for analysis, then auto-evicts. For immediate eviction after use, use `keep_alive: "0"`.
