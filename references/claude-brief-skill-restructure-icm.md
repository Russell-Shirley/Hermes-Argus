# Claude Brief: Hermes-Argus Skill Restructure — ICM Alignment (PR #20)

> Use this brief to understand what was done, why, and what remains.
> Then continue from where Hermes left off.

---

## Background: What Is ICM and Why Does It Matter Here

The **Interpretable Context Methodology (ICM)**, also called the **Model Workspace Protocol (MWP)**, was authored by Jake Van Clief and David McDermott. The core idea: **the filesystem is the orchestration layer**. Instead of building a framework with code, you organize plain markdown files in a folder hierarchy. Each folder is a stage. Each file is context delivered at the right moment.

The five MWP layers are:

| Layer | File | Role |
|-------|------|------|
| **L0** | `AGENTS.md` (or `CLAUDE.md`) | Identity — "Who am I and how do I work?" |
| **L1** | `CONTEXT.md` | Task routing — "Where do I go for what?" |
| **L2** | `SKILL.md` (per skill subfolder) | Stage contract — "What do I do, what do I consume, what do I produce?" |
| **L3** | `references/*.md` per skill, plus shared `_config/` | Reference material — "What rules apply?" (stable across runs) |
| **L4** | `output/` per skill (gitignored) | Working artifacts — per-run output |

The two key documents we studied:

1. **The ICM Paper (Van Clief & McDermott)** — Defines the five-layer hierarchy, the U-shaped human intervention pattern, and the philosophy that plain markdown files (not code) should be the contract between humans and AI agents.

2. **Clief Notes Module 3.2 "Customizing for Your Use Case"** — Teaches how to adapt the three-layer architecture (L0/L1 structural, L2 stage control, L3 reference) across different domains. The layers stay the same; the naming and content adapt to the domain.

**Why this matters for Bridge and Bolt:** If we get the Hermes-Argus repo right as the canonical pattern, then Bridgeboard, AI Factory, and Claude all inherit the same structure. One pattern, three repos, consistent routing from the same five-layer architecture.

---

## What We Discovered: Three Lanes, Not One

When we mapped Hermes-Argus against the ICM layers, a structural tension appeared. The repo wasn't serving a single audience — it was serving **three different audiences** with different needs, all mixed into one skill tree:

| Lane | What It Is | Repo Domains | Who Uses It |
|------|-----------|-------------|-------------|
| 🏗️ **Development** | Platform engineering — build tooling, infrastructure, monitoring, automation, vision, design patterns | `architecture/`, `ops/`, `content/` | Engineering agents, Argus itself |
| 🤝 **Client Services** | Client-facing — onboarding, outreach, CRM, communication drafting | `clients/` | Client-facing agents |
| 🏢 **Business/Internal** | Bridge and Bolt internal — strategy docs, pricing, competitive research, presentations | `business/` | Strategy agents, board materials |

The repo already had `_context.md` files per domain that did a rough version of this routing, but the **naming was inconsistent, the folder structure was flat vs subfolder mixed, and the frontmatter had two conflicting conventions fighting each other**. That's the "two to three lanes" problem you felt.

---

## What PR #20 Actually Changed

The commit on branch `chore/skill-folder-standardization` does **six discrete things**, each corresponding to one MWP layer or convention gap:

### 1. Unified Frontmatter to ICM Lowercase-Hyphens Style (All Layers)

The repo had two conventions:
- **AI Factory style** (UPPERCASE_SNAKE with `trigger`, `governed_by`, `phase`) — used by 3 skills
- **ICM module style** (lowercase-hyphens with `name/category/domain/intent/exclusions`) — used by ~11 skills

We standardized on **ICM lowercase-hyphens** because:
- ~80% of skills already used it
- It's simpler — no need for Factory governance pipeline
- It maps cleanly to the MWP Layer 2 stage contract pattern
- The `domain` field provides the MWP Layer 1 routing that `_context.md` files consume

Three skills were converted from Factory to ICM style:
- `cinematic-html-presentation` (was `CINEMATIC_HTML_PRESENTATION`)
- `vision-analysis` (was minimal frontmatter, expanded to full ICM)
- `water-safety-app-vision` (was minimal frontmatter, expanded to full ICM)

Every skill now has: `name`, `description`, `category`, `domain`, `intent`, `exclusions`, `requires`, `phase`, `compatible_with`, `conflicts_with`, `handoff_to`, `scope`, `data_access`, `governed_by`, `version`, `compatibility`, `examples`.

### 2. Converted Flat `.md` Files to Subfolders (MWP Layer 2)

Before: mixed structure — some skills were `skills/ops/foo.md` (flat), others were `skills/business/bar/SKILL.md` (subfolder with references/).

After: **every skill is at `skills/<domain>/<skill-name>/SKILL.md`**. Fourteen skills in subfolders. Zero flat files at the domain level.

This matters because MWP Layer 2 (stage contracts) expects each skill to be a self-contained directory that can grow its own `references/` (Layer 3) and `output/` (Layer 4) without polluting the domain namespace.

### 3. Created Root `CONTEXT.md` (MWP Layer 1 — Routing)

New file at repo root. This is the **gateway** — a human or agent reads this first to decide which lane and domain to go to. It contains:
- The three-lane table with domain assignments
- Per-domain routing tables (request type → domain → first skill to check)
- How to route: read request → match lane → load domain `_context.md` → load skill `SKILL.md` → load `references/*.md`

### 4. Created `_config/lane-conventions.md` (MWP Layer 3 — Shared Reference)

New shared reference file at `_config/`. Contains:
- The canonical frontmatter template (YAML block)
- File path conventions for all four MWP layers
- The three-lane mapping table
- General rules (lowercase-hyphens, no flat files, references/ for stable material)

The key: **this is the file that Bridgeboard, AI Factory, and Claude can all reference**. Change this file and every downstream repo inherits the updated convention.

### 5. Updated All 5 `_context.md` Files (MWP Layer 1 — Domain Routing)

Every domain's `_context.md` now:
- Declares which lane it belongs to (🏗️ Development, 🤝 Client Services, 🏢 Business/Internal)
- Lists all skills in the domain with their descriptions
- References `_config/lane-conventions.md` for frontmatter standards
- Has up-to-date `related_skills` lists

### 6. Updated `AGENTS.md` (MWP Layer 0 — Identity)

Added the three-lane architecture section and regenerated the complete project tree showing every skill in its subfolder location. This is the document that answers "what is this repo and how is it organized?"

---

## How This Maps to the ICM Five Layers

Here's the concrete MWP mapping for Hermes-Argus after PR #20:

| MWP Layer | Hermes-Argus Artifact | Status |
|-----------|----------------------|--------|
| **L0** — Identity | `AGENTS.md` (who I am, three-lane architecture, git workflow, tech stack) | ✅ Updated |
| **L1** — Routing | `CONTEXT.md` at repo root + `skills/*/_context.md` per domain | ✅ New + updated |
| **L2** — Stage Contracts | Each skill at `skills/<domain>/<name>/SKILL.md` (14 total) | ✅ All in subfolders |
| **L3** — Reference | `_config/lane-conventions.md` (shared) + `skills/*/<name>/references/*.md` (per skill) | ✅ New shared ref, existing per-skill refs preserved |
| **L4** — Working Artifacts | `skills/*/<name>/output/` directories | ❌ Not yet created — add when skills generate per-run output |

---

## What Claude Should Do Next (In Priority Order)

### 1. Verify the PR on GitHub

PR #20 is at: https://github.com/Russell-Shirley/Hermes-Argus/pull/20

Review the diff to ensure:
- All flat files properly deleted and subfolder equivalents exist
- Frontmatter on the 3 converted skills looks right
- No accidental file deletions or stale references

### 2. Sync Skills to Hermes Runtime and Test

```bash
cd /mnt/c/Users/Russell/Documents/GitHub/Hermes-Argus
bash scripts/sync-skills-to-hermes.sh
hermes skills list
```

Spot-check that at least one skill from each domain loads:
```bash
hermes skill view skills-architecture
hermes skill view skills-business  
```

### 3. Check `modules/icm_base/` for Drift

The `modules/` directory is a deployment tree with its own skill copies. Some have drifted:
- `modules/icm_base/ops/puppeteer.md` — does it match `skills/ops/puppeteer-web-browsing/SKILL.md`?
- `modules/icm_base/business/_context.md` — does it match `skills/business/_context.md`?
- The `modules/icm_base/` has its own `_context.md` files for `ops/`, `business/`, `clients/`, `content/` — these may need similar updating or a note that they're deployment copies inheriting from `skills/`

If they're stale, update them or add a comment at the top of each: "This is a deployment copy. Canonical source is `skills/<domain>/<name>/SKILL.md` in this repo."

### 4. Extend the Pattern to Bridgeboard

The Bridgeboard repo at `/mnt/c/Users/Russell/Documents/GitHub/Bridge-and-Bolt/` should get:
- `CONTEXT.md` with the same three-lane routing
- `_config/lane-conventions.md` (copy or symlink — references Hermes-Argus as canonical)
- Its `playbooks/` and `tools/` organized to match the lane structure

### 5. Populate the Empty Client Services Lane

`skills/clients/` has only a `_context.md` placeholder. Skills that could live here:
- `client-onboarding` — checklist and playbook for bringing new SMB clients online
- `outreach-cadence` — customer contact scheduling, email templates, follow-up timing
- `crm-update-protocol` — standard fields to maintain in CRM per client interaction

### 6. Create `_config/agents-conventions.md`

A shared reference that defines the `governed_by` invariants from `AGENTS.md` explicitly. Currently every skill has `governed_by: []`. This file would define things like:
- "All financial numbers must come from verified sources" (invariant #1)
- "No destructive action without human approval" (invariant #2)

Then skill frontmatter can reference these: `governed_by: ["AGENTS.md#invariant-1-verified-data"]`

---

## The Bigger Picture

This restructure isn't just about cleaning up Hermes-Argus. Hermes-Argus is the **canonical reference implementation** of the ICM/MWP pattern for Bridge and Bolt. The three-lane structure:
- **Development lane** — what Argus runs on (infrastructure, automation, ops)
- **Client Services lane** — what Argus *does* for clients
- **Business/Internal lane** — what Bridge and Bolt *is* as a business

When this is right in Hermes-Argus, Bridgeboard inherits it, AI Factory inherits it, and Claude inherits it. One ICM pattern, consistent across every repo, every agent, every file.
