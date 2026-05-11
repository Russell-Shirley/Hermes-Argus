---
name: argus-slack-emoji-protocol
description: Emoji-based status indicators for Slack — inline text only, no reaction API calls.
trigger: any Slack message requiring work, status updates, or memory operations
category: ops
metadata:
  hermes:
    tags: [slack, emoji, protocol, status]
    related_skills: []
---

# Argus Slack Emoji Protocol

## Reactions are fully automatic
Hermes gateway (`gateway/platforms/slack.py`) adds 👀 and ✅ via `reactions_add` natively for every @mention in Slack. Argus does NOT manage these.

## Argus manages NO reaction API calls
The brain emoji reaction via MCP Slack tools was dropped — the MCP tools lack token access and consistently return `missing_token`. Do not attempt `mcp_slack_slack_add_reaction`.

## Inline text emoji only
When sharing state in messages, use inline text emoji in your response body:

| Emoji | Meaning | When to Use |
|-------|---------|-------------|
| 👀 | Working / Actively processing | At the very start of your response when a task begins |
| 🧠 | Saved to Cognee memory | After a successful memory write |
| ✅ | Task complete | After completing a multi-step task |

## Sequence Rules
- 👀 first message when a task starts. Subsequent replies in the same task don't repeat it.
- 🧠 replaces ✅ when the action was exclusively a memory/knowledge graph operation.
- ✅ is the terminal marker. Don't put ✅ and then more work.

## What "not working" means
If a Cognee write fails or returns an error, just say so inline. Don't try fallback reaction mechanisms, don't retry the API, don't escalate. Just tell Russell: "Cognee write failed, skipping."