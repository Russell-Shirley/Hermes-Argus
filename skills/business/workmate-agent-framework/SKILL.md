---
name: workmate-agent-framework
description: |-
  Reference for Workmate — an on-prem agent deployment framework for enterprises.
  Covers competitive comparison with Multica and architectural considerations.
  DO NOT use for: implementation, deployment, or integration decisions.
category: business
domain: research
intent:
  - agent-orchestration
  - competitive-analysis
  - workmate-reference
exclusions:
  - implementation
  - deployment
  - integration
requires: []
phase: research
compatible_with:
  - multi-agent-orchestration-framework
conflicts_with: []
handoff_to: []
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
  - "Researching on-prem agent deployment for an enterprise client"
  - "Comparing Workmate vs Multica for a regulated industry deployment"
---

# Workmate Agent Framework

## Overview
Workmate is an on-prem agent deployment framework for enterprise use cases.
Unlike Multica (dev-managed orchestration), Workmate is designed for self-hosted,
air-gapped, or regulated environments where cloud dependency is not acceptable.

## Key Features
- On-prem deployment
- Air-gapped operation
- Regulated environment support
- Enterprise security controls

## Comparison with Multica
See `multi-agent-orchestration-framework` for the parallel reference.
