# bb-prospecting-kit

The pipeline that turns a Google Maps search for one city + one vertical into a
ranked, qualified, evidence-backed lead list with outreach copy.

**Canonical home: `Hermes-Argus/docs/prospects/bb-prospecting-kit/`** — the sibling of
`bb-audit-kit` (that one audits existing clients; this one finds new ones).

It lives **here, in one place, and serves every run.** A run folder holds data,
not code — so a fix to a script fixes it for every city instead of one copy.

```
Hermes-Argus/docs/prospects/          ← TOOLING (this repo)
├── bb-prospecting-kit/               ← the pipeline + this README + tests
│   └── ledger-location.json          ← points at the findings repo
└── RUNBOOK-city-run.md               ← the per-run checklist

bb-audit-kit/research/                ← FINDINGS (the other repo)
├── hermes/<date>-<niche>-<area>/     ← one finished city search
└── prospects/ledgers/<niche>.jsonl   ← one ledger per vertical
```

**Findings never live in this repo.** The Hermes repo is the agent system; the ledgers and run
output are client work product. `ledger-location.json` tells the tool where they are, and the tool
warns loudly if a write is ever about to land inside the kit.

## Requirements

Python 3 plus the browser stack the scrapers drive (CloakBrowser / Playwright).
Search engines (Google SERP, DDG, Bing) are CAPTCHA-walled from this IP; **Google
Maps works signed-out**, which is why every script here goes through Maps.

## Running it against a run folder

Scripts default to `<tool>/../data`, so they also work if copied into
`<run>/scripts/`. To run them **in place** against any run — the normal way —
set `RUN_DATA`:

```bash
RUN="docs/prospects/2026-10-septic-cumming-ga"
RUN_DATA="$RUN/data" python docs/prospects/bb-prospecting-kit/qualify_reviews_v2.py 9 30 --min-reviews=20
```

## The pipeline, in order

| # | Script | Writes | Notes |
|---|---|---|---|
| 1 | `local_rank_probe_v4.py "<query>"` | `data/ranked-feed.json` + `.csv` | The ranked list. Scrolls to "end of the list". **Google prints no rank number** — rank is positional list order (`pin_number_check.py` is the evidence). |
| 2 | `qualify_reviews_v2.py <lo> <hi> [--min-reviews=N]` | `data/qualify_results.jsonl` | Appends and is resumable. Waits **40s/business** — see pacing below. |
| 3 | `merge_results.py` | `data/qualify_merged.jsonl` | One record per business, best run wins. |
| 4 | `analyze_qualify.py [--area-label=<slug>] [--title=<text>]` | `data/qualify_candidates.csv`, `qualify_leads.csv`, `qualify_report.md` | Emits the leads file too. First column is `captured_by`. `--area-label` takes either `canton-ga` or `Canton-GA` (one label convention, shared with the ledger); the report header derives from it, so the report names its own run. |
| 5 | `deep_reviews.py "<name>" [...]` | `data/deep_reviews.json` | Full review population — the ground truth for validating the capture. |
| 6 | `score_deep.py` | `data/deep_scored.csv` | Scores **recent coverage (newest 10)** + reply substance. Lifetime coverage alone misleads. |
| 7 | `probe_posts_iso.py "<name>"` | merge into `data/posts_verified.json` | Authoritative post evidence. A pane-text scan gives **false negatives** — never trust it alone. |
| 8 | `capture_business.py "<name>" [--area-label=...]` | `data/captures/<slug>.json` | The 14-row diagnostic, with a per-field `gaps` map. |
| 9 | `summarize_captures.py` | `data/captures/MATRIX.txt` | Human-readable matrix. |

Diagnostics and one-offs (kept because the knowledge is load-bearing):

| Script | Why it's here |
|---|---|
| `pin_number_check.py` | Proves Maps results carry **no rank number** in the DOM — the answer to "does Google show you the ranks?" |
| `check_posts.py` | Earlier post probe, superseded by `probe_posts_iso.py`; kept for comparison |
| `oneoff_andylewis.py` | Worked example of the fallback route for a listing that kept gating |

### Per-run inputs that must not live in the toolkit

`<run data>/exclusions.json` — either `["Name", ...]` or `{"names": [...]}` — names the
run was told not to contact, whatever the numbers say. It is read by
`analyze_qualify.py` and it lives **with the run**, because a call-out made about one
city is not a rule for the next one. No file means no exclusions.

## The ledgers — one per vertical, in the findings repo

```
bb-audit-kit/research/prospects/ledgers/
├── duct-cleaning.jsonl     ← Cumming GA, 2026-09
└── septic.jsonl            ← next
```

**One file per vertical, not one shared file.** A visit is vertical-specific: a
business excluded from a duct-cleaning run because it answers its reviews is a
perfectly good *septic* prospect with a different offer, and a shared ledger would
silently skip it. It also keeps vertical name collisions apart — "One Way Septic"
exists in several states.

Check the right vertical **before** working a new area:

```bash
python docs/prospects/bb-prospecting-kit/contacted_ledger.py check \
    --feed "$RUN/data/ranked-feed.json" --area alpharetta-ga --niche duct-cleaning
```

- `--niche` is **required** for `seed`, `check` and `mark` — every write and every
  skip decision belongs to exactly one vertical. `stats` and `cap` take it
  optionally.
- Matches on **phone first**, then **name+area**. The same name in a *different*
  area **FLAGS for a human and never auto-skips** — two towns can each have an
  "H & M Services", and merging them drops a real prospect.
- A business on file for **another** vertical prints as **INFO, never a skip** —
  still in scope, different offer.
- Outcomes never downgrade, so a re-seed can't silently reset a real send.
- `stats` summarises every vertical; `stats --niche septic` details one.
- `cap --sender <address>` counts sends across **all** verticals (a daily limit is
  about the mailbox, not the vertical), ~20/day.
- Ledgers live in the **findings repo**, resolved via `ledger-location.json`
  (override: `--ledger-dir`, `PROSPECT_LEDGER_DIR`). `stats` always prints the
  directory it actually used — check it if a ledger looks empty.

## Two rules that came from getting them wrong

1. **40 seconds per business, minimum.** At 15s, 3 of 17 businesses came back
   Google-gated (a sign-in wall beat the scrape); at 40s, **0 of 17** did. Speed
   here costs coverage, and a gated business silently looks like a zero.
2. **Never score a gated business as zero.** Gated rows are retried, not scored.
   `diag_gate.py` proved the "limited view" marker is a false positive — the card
   count is the real gate signal.

## Verticals

Same pipeline, different query and qualification knobs:

- **Duct cleaning** (worked: Cumming GA, 2026-09) — 39 ranked positions, 29
  evaluated, 8 leads.
- **Septic** — next. Query pattern: `septic tank pumping <city> GA`. Septic
  prospects need a **different closing deliverable** than the duct-cleaning
  review-gap pitch: fill the missing tracker fields (owner name, email, county,
  GBP category health) and recommend a **ladder rung 1–5**. That flow, plus the
  highest-yield sources, lives in the `septic-lead-research` skill:
  - **GBP first** (Maps, signed-out) — category health, rating, claim status
  - **FMCSA Motor Carrier Census** — the email source for truck-owning septic
    firms; MCS-150 carries a mandatory email, confirmable against the GBP by
    address + phone
  - **GA SOS** (`ecorp.sos.ga.gov`) — registered agent, status, principal address
  - Email verification needs a **fake-address control** run alongside the target
- Also worth capturing for septic: category mismatch (hides them from septic
  searches), after-hours gap (owner on the truck, closes 5pm), and split listings.

## Known limits (don't rediscover these)

- **Response speed is quantised** — Google renders "a month ago", never dates, so
  every lag lands at ~0d or ~30d. Don't report it as a precise number.
- **Review velocity is relevance-ordered**, not chronological.
- **Overall coverage % misleads.** A business at 90% lifetime coverage whose
  replies *stopped* 3 months ago is a better prospect than one at 47% that was
  always shallow. Score on the newest 10 + reply substance.
- **Three capture rows are sign-in gated** on a signed-out place page: secondary
  categories, services coverage, photo counts.
