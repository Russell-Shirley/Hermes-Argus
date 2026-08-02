---
version: 1.0.0
scope: liftable
data_access: { trust_level: elevated }
---

# BridgeBoard Sync

> **Synced from AI Factory** — canonical source is
> [`ai-factory/skills/_shared/bridgeboard-sync/SKILL.md`](https://github.com/Russell-Shirley/ai-factory/blob/main/skills/_shared/bridgeboard-sync/SKILL.md).
> Do not hand-edit divergently; if this copy and the canonical source disagree, the canonical
> source wins (NSI-10). It lives here as a file rather than a `CONTEXT.md` block so it loads
> on demand instead of consuming context in every session.

Agent-facing procedure for the **cross-platform** memory seam: pulling what a claude.ai
chat session decided into a Claude Code session, and pushing what a Claude Code session
changed back out so chat can see it.

## Purpose

Claude Code and claude.ai chat cannot see each other's sessions. Work lands in a repo from
Code; scope and architecture decisions get made in chat; neither side learns about the other
until a human retells it. BridgeBoard is the shared store that removes that retelling.

## Which memory layer — read this before calling any tool

| Store | Reach | Authority |
|---|---|---|
| **BridgeBoard** | Cloud; claude.ai, Code, ChatGPT, Gemini, Granola | Advisory |
| **Hindsight** | Local machine only, per-project bank | Advisory |
| `knowledge/` | Git, portfolio-wide | **System of record (NSI-1)** |

**Tool-name collision — the trap.** BridgeBoard and Hindsight both expose MCP tools named
`remember`, `recall`, `search_memory`, `recent_context`, and `get_thread`. Selecting by
tool-name suffix will silently write to the wrong store, and neither server errors when it
receives the other's payload.

Disambiguate by the tool **description**:

- BridgeBoard's `remember` reads *"Save content to your BridgeBoard Second Brain for
  cross-platform recall."* Its `search_memory` accepts a `source` filter (`claude`,
  `chatgpt`, `gemini`, `granola`) — Hindsight's does not.
- Hindsight's tools are backed by `http://localhost:8888` and partition by bank
  (`claude-code::<project>`).

A session summary landing in the local Hindsight bank is invisible to chat, which defeats
the entire purpose of the push.

## When to Use

- **Session start**, before beginning work — pull recent cross-platform context so a
  chat-side decision isn't unknowingly contradicted.
- **Immediately after a merge lands** — push what changed so the next chat session starts
  informed. Invoked from this repo's closeout / delivery step.
- The user asks what was decided **in a chat session**.
- A read-only investigation session produced findings worth carrying forward. Findings are
  decisions' raw material; they push too.

## When NOT to Use

- **Durable knowledge that must survive forever** → deposit into `knowledge/`. BridgeBoard
  is advisory and never authoritative (NSI-1). A genuinely durable learning gets both.
- **Current repo state** → read the repo. BridgeBoard lags; git does not.
- **Code structure questions** (callers, impact, call paths) → CodeGraph.

## Process

### Pull — session start

1. `search_memory` with the repo name plus `code-session` (e.g. `"<repo> code-session"`).
   Add a second query for `decision` scoped to the repo — architecture and scope calls made
   in chat often never reached the code.
2. Read what returns. Compare against the repo's actual state.
3. **If a BridgeBoard entry conflicts with the repo, stop and flag it to Russell.** Do not
   silently pick a side. The store is advisory; the repo is authoritative; but a conflict
   means someone's model of the work is wrong.
4. If nothing returns, say so plainly and continue. An empty pull is normal.

### Push — after each merge

Fires once per merge, not once per PR-open. At PR-open the work has not landed: the branch
may still be revised, the PR may be closed, and a chat session reading that entry would act
on state that never shipped.

1. Confirm the merge actually landed (`gh pr view <N> --json state,mergedAt`).
2. Compose the body, under ~15 lines — this is a handoff, not a changelog:
   - **WHAT CHANGED** — PR number, files or migrations touched
   - **DECISIONS MADE** — anything a future chat or Code session needs. If it replaces a
     prior decision, say so: `supersedes <BridgeBoard ID>`
   - **OPEN ITEMS** — what's incomplete or deferred, stated plainly
   - **VERIFIED vs ASSUMED** — mark every claim not directly verified by a test run, query,
     or file read as `ASSUMED`
3. **Scrub before sending.** This exports repo content past the repo boundary to a cloud
   store. Remove credentials, customer PII, and — for client work — client-identifying
   detail the engagement doesn't permit sharing. Summarize client work by shape, not by name.
4. Call `remember`:
   - `title`: `"<repo> — <one-line description> — <YYYY-MM-DD>"`
   - `content`: the body above. **The tool takes no `tags` parameter** — the repo name and
     the literal string `code-session` must appear in the title or content text, or the
     session-start pull will never find this entry.
   - `content_type`: `ai-chat`
   - `session_id`: the conversation UUID. **Pass the same value for every push in a session.**
     This is what makes per-merge granularity safe — BridgeBoard groups the saves into one
     session, so a three-merge session reads as one narrative rather than three orphaned
     fragments.
5. Report the returned record ID.

### When BridgeBoard is unreachable

The MCP connector is optional and is frequently absent in headless, cron, and orchestrator
runs. When it is:

- **Do not block the closeout.** An unreachable advisory store must never gate a merge that
  has already landed.
- Post the same summary as a comment on the merged PR instead. GitHub is the system of
  record (NSI-1), so the content survives; only the cross-platform reach is lost.
- Say so explicitly in the session close-out: *"BridgeBoard push not made — connector
  unavailable; summary recorded on PR #N instead."*

## Done Looks Like

- **Pull:** recent cross-platform context was queried and either summarized (named as
  advisory, from BridgeBoard) or reported as empty — and any conflict with repo state was
  surfaced to Russell rather than silently resolved.
- **Push:** `remember` returned a record ID, and that ID is reported in the session
  close-out. **Never report a summary as saved without a returned record ID.**
- Or: the push was explicitly skipped with a stated reason and the summary landed on the
  merged PR instead.
- The correct store was written to — BridgeBoard, not Hindsight.

## Common Failure Modes

- **Wrote to Hindsight instead of BridgeBoard.** The tool names are identical. The summary
  is now on the local machine, invisible to chat, and the loop is still broken while
  appearing closed. Verify the server by tool description.
- **Claimed the push succeeded without a record ID.** The most damaging failure: the next
  chat session trusts a summary that does not exist.
- **Pushed at PR-open instead of at merge.** Chat then acts on unlanded work.
- **Passed a fresh `session_id` per merge.** Fragments one session's work into unrelated
  entries.
- **Omitted `code-session` and the repo name from the text.** With no `tags` parameter, the
  entry is effectively unfindable by the standard session-start query.
- **Let a missing connector block a merge.** Advisory infrastructure does not get veto power
  over landed work.
- **Treated a BridgeBoard entry as ground truth** and built on a stale chat-side decision
  instead of checking the repo.
- **Pushed raw client detail** into a cloud store.
