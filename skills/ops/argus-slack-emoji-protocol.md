---
name: argus-slack-emoji-protocol
description: |
  Emoji-based status indicators for Slack conversations — inline text only,
  no reaction API calls. Documents what Hermes handles natively vs what Argus manages.
  DO NOT use for: non-Slack platforms, reaction API troubleshooting, or memory operations.
category: ops
domain: messaging
intent:
  - slack-status
  - emoji-protocol
  - task-signaling
exclusions:
  - reaction-api-troubleshooting
  - non-slack-platforms
requires: []
phase: operations
compatible_with: []
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
  - "Starting a task — use 👀 at the start of my response"
  - "Completing a task — end my response with ✅"
  - "Saving to Cognee — include 🧠 in my message text"
---
# Argus Slack Emoji Protocol

## Reactions are fully automatic
Hermes gateway (`gateway/platforms/slack.py`) adds 👀 and ✅ via `reactions_add` natively for every @mention in Slack. Argus does NOT manage these.

## Argus manages NO reaction API calls
The brain emoji reaction via MCP Slack tools was dropped — the MCP tools lack token access and consistently return `missing_token`. Do not attempt `mcp_slack_slack_add_reaction`.

## Inline text emoji only
- 👀 = actively looking at / working on a task
- 🧠 = successfully saved something to Cognee/Open Brain memory
- ✅ = task complete
