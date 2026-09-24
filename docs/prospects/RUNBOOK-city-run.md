# City-run manifest — Duct cleaning (and other local-service) prospecting

**One city + one vertical = one folder.** Everything below lives inside it, so filenames never
need to carry the city name.

| Where | What |
|---|---|
| `bb-audit-kit/research/hermes/<date>-<niche>-<area>/` | **the FINDINGS** — one finished run |
| `Hermes-Argus/docs/prospects/` | the TOOLING — `bb-prospecting-kit/` + this runbook |
| `Documents/GitHub/prospect-<city>-<vertical>-<YYYYMM>/` | archive (screenshots, raw dumps) |

**Findings never go in the Hermes repo**, and tooling never goes in the findings repo. The Hermes
repo is the agent system; a run's output is client work product.

This is the answer to "when we finish a city search, what do we save?" — the checklist is §4.

---

## 1. Folder shape

```
<city>-<vertical>-<YYYYMM>/
├── README.md                    ← the run write-up (findings, gates, patterns, how to re-run)
├── HANDOFF-gaps.md              ← only if capture coverage changed (what we couldn't pull + options)
├── data/                        ← every output (the pipeline itself lives in ../bb-prospecting-kit/)
│   ├── ranked-feed.json          ← THE ranked list (source of truth for ranks)
│   ├── ranked-feed.csv           ← same, human-readable
│   ├── qualify_results.jsonl     ← raw per-business scrape records (resumable state)
│   ├── qualify_merged.jsonl      ← one record per business, best-run-wins
│   ├── qualify_candidates.csv    ← every evaluated business + verdict
│   ├── qualify_leads.csv         ← the qualified leads only
│   ├── qualify_report.md         ← generated report
│   ├── deep_reviews.json         ← full-population review pulls
│   ├── deep_scored.csv           ← pattern scores (SILENT/DECAYED/SHALLOW/SPOTTY)
│   ├── posts_verified.json       ← GBP post evidence (click-through, authoritative)
│   ├── ab_test_tracker.csv       ← arm assignment + claim status + outcome columns
│   └── captures/
│       ├── MATRIX.txt            ← rendered 14-row diagnostic per business
│       └── <business-slug>.json  ← one capture per lead (each carries a `gaps` map)
└── outreach/
    ├── outreach_drafts.md        ← filled templates per lead
    └── outreach_ab_test.md       ← A/B design, verified-claim table, protocol
```

## 2. File-by-file

| File | Produced by | Holds | In git? |
|---|---|---|---|
| `README.md` | human + agent | what the run found, the gates, the honest caveats | ✅ |
| `HANDOFF-gaps.md` | agent | capture gaps + options for another model | ✅ |
| `scripts/*.py` | copied per run | the pipeline (see §3) | ✅ |
| `data/ranked-feed.json/.csv` | `local_rank_probe_v4.py` | ranked positions, names, ratings, review counts, phones, ad flags | ✅ |
| `data/qualify_results.jsonl` | `qualify_reviews_v2.py` | raw scrape state, resumable — **retries append here**, that's the `_vN` files in old runs | ✅ |
| `data/qualify_merged.jsonl` | `merge_results.py` | one record per business, best record wins | ✅ |
| `data/qualify_candidates.csv` | `analyze_qualify.py` | all evaluated businesses: gates, tiers, verdicts, claim status. **First column is `captured_by`** (`Cumming-GA - <business>`), so any row traces back to the search that found it | ✅ |
| `data/qualify_leads.csv` | `analyze_qualify.py` | the qualified leads only, same `captured_by` first column | ✅ |
| `data/qualify_report.md` | `analyze_qualify.py` | rendered report (same data, prose) | ✅ |
| `data/deep_reviews.json` | `deep_reviews.py` | full-population review pulls — the ground truth for validating the capture | ✅ |
| `data/deep_scored.csv` | `score_deep.py` | pattern scores on recent coverage + reply substance | ✅ |
| `data/posts_verified.json` | `probe_posts_iso.py` / `check_posts.py` | GBP post dates (authoritative; pane scan gives false negatives) | ✅ |
| `data/ab_test_tracker.csv` | assignment step | A/B arm + verified-claim status + reply outcome columns | ✅ |
| `data/captures/<slug>.json` | `capture_business.py` | the 14-row diagnostic, with per-field `gaps` | ✅ |
| `data/captures/MATRIX.txt` | `summarize_captures.py` | human-readable matrix | ✅ |
| `outreach/*.md` | agent | the actual email copy | ✅ |
| `*.png` (screenshots) | every script | evidence for claims (SERP, review panes, posts surfaces) | ❌ archive |
| `*.log` | every script | run logs | ❌ archive |
| `_archive/` | — | superseded scripts, diagnostics, raw dumps | ❌ archive |

**Why screenshots are excluded:** ~40 MB per city against a 664 KB packed repo. They live in the
archive folder; the README names the load-bearing ones.

## 3. The pipeline (canonical toolkit, not copied per run)

The scripts live in **`Hermes-Argus/docs/prospects/bb-prospecting-kit/`** — one copy, serving every city and
vertical, so a fix lands everywhere at once. A run folder holds **data only**. Read
`bb-prospecting-kit/README.md` before running anything.

Drive them in place with `RUN_DATA` (they default to `<tool>/../data`, so they also work if you
do copy them into a run):

```bash
RUN="$HOME/Documents/GitHub/bb-audit-kit/research/hermes/<date>-<niche>-<area>"
RUN_DATA="$RUN/data" python docs/prospects/bb-prospecting-kit/local_rank_probe_v4.py "<query>"
```

Record the toolkit commit SHA in the run README — that is the provenance, instead of a frozen copy.

| # | Script | Writes |
|---|---|---|
| 1 | `local_rank_probe_v4.py "<query>"` | `ranked-feed.json/.csv` |
| 2 | `qualify_reviews_v2.py <lo> <hi> [--min-reviews=N]` | `qualify_results.jsonl` (append, resumable) |
| 3 | `merge_results.py` | `qualify_merged.jsonl` |
| 4 | `analyze_qualify.py` | `qualify_candidates.csv`, `qualify_leads.csv`, `qualify_report.md` |
| 5 | `deep_reviews.py "<name>" …` | `deep_reviews.json` (append) |
| 6 | `score_deep.py` | `deep_scored.csv` |
| 7 | `probe_posts_iso.py "<name>"` | post evidence (merge into `posts_verified.json`) |
| 8 | `capture_business.py "<name>"` | `captures/<slug>.json` |
| 9 | `summarize_captures.py` | `captures/MATRIX.txt` |

`oneoff_andylewis.py` is a one-off (a listing whose place URL kept gating); kept as a worked example
of the fallback route, not part of the standard order.

## 3b. Where a run lives, and the ledger

Everything prospect-related lives in **this repo**, under `docs/prospects/`:

| Path | What | In git? |
|---|---|---|
| `Hermes-Argus/docs/prospects/bb-prospecting-kit/` | the pipeline (code) | Hermes |
| `bb-audit-kit/research/prospects/ledgers/<niche>.jsonl` | the ledger — **one per vertical** | findings |
| `bb-audit-kit/research/hermes/<date>-<niche>-<area>/` | one run (findings, data only) | findings |

**Before working a new area, check the ledger:**

```bash
python docs/prospects/bb-prospecting-kit/contacted_ledger.py check --feed <run>/data/ranked-feed.json --area alpharetta-ga --niche <vertical>
```

It prints SKIP / FLAG / NEW against `ledgers/<niche>.jsonl` — every business we have ever evaluated
in that vertical, including exclusions — matched on **phone first**, then **name+area**.

**`--niche` is required** for seed/check/mark. Ledgers are per vertical because a visit is
vertical-specific: a business excluded from a duct-cleaning run is still a valid septic prospect
with a different offer, and a shared ledger would silently skip it. A business on file for another
vertical reports as **INFO, never a skip**.

Same name in a different area is a **FLAG for a human, never an automatic skip** (two towns can each
have an "H & M Services", and merging them drops a real prospect). Outcomes never downgrade.
`cap` counts sends across all verticals — a daily limit is about the mailbox, not the vertical.

Override the ledger dir with `--ledger-dir` or `PROSPECT_LEDGER_DIR`.

## 4. End-of-run checklist

- [ ] `ranked-feed.json` written and the list scrolled to "end of the list"
- [ ] Every business in the qualified rank window has a record in `qualify_merged.jsonl`
- [ ] No record left `GATED` — gated businesses are retried, never scored as zero
- [ ] `deep_reviews.json` covers every business we intend to contact (thin pulls re-run)
- [ ] `posts_verified.json` refreshed (pane-scan alone is not acceptable evidence)
- [ ] `captures/MATRIX.txt` regenerated; every `gaps` entry reviewed
- [ ] Claim-verification pass re-applied to every draft (§5 of README)
- [ ] `outreach_drafts.md` + `ab_test_tracker.csv` current, arms pattern-matched
- [ ] Every business evaluated (including exclusions) seeded into `ledgers/<niche>.jsonl` with its `captured_by`
- [ ] `contacted_ledger.py check --niche <vertical>` re-run against the run's own feed — no unexpected NEW
- [ ] README updated with the run date, lead count, and any new corrections to earlier runs
- [ ] Tooling commit SHA recorded in the run README (provenance, in place of a copied `scripts/`)
- [ ] Screenshots/logs moved to the archive folder, not committed
- [ ] Committed in the **findings repo** (bb-audit-kit) on a branch, opened as a PR
- [ ] Nothing produced by the run committed in Hermes-Argus

## 5. Standing naming rules

1. **Generic filenames inside the run folder** — no city or vertical in file names; the folder
   carries that. (Historical: the Cumming run's `ranked_duct_cumming_v4.*` predates this rule and
   was renamed to `ranked-feed.*`; `duct_cleaning_cumming_ranks.csv` is a superseded duplicate.)
2. **One raw state file per stage.** `qualify_results.jsonl` is appended to and resumed; don't
   create `_v2`/`_v3` copies — that pattern came from iterating mid-run and left six files behind.
3. **`<business-slug>.json`** for per-business captures (lowercase, hyphens, ≤60 chars).
4. **Dates are `YYYYMM`** in the folder name, `YYYY-MM-DD` in prose.
5. **Anything a claim depends on is either committed or named in the README** — never only on disk
   in a scratch folder.
