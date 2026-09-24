# Cumming, GA — Duct Cleaning: Local Rank + Review-Gap Prospecting Run
**Run date:** 2026-09-22 · **Researcher:** Hermes (Bridge and Bolt prospecting) · **Query:** `best duct cleaning in Cumming GA`

Method + repeatable pipeline for finding local businesses with an **unmanaged review presence**,
plus the qualified lead set, the claim-verification gate, and the A/B outreach test in flight.

---

## 1. What this run produced

| Item | Result |
|---|---|
| Google Maps ranked feed for the query | **39 ranked positions**, 38 unique businesses (`All Pro Duct & Air Cleaning` listed twice) + 2 sponsored |
| Businesses evaluated (ranks 9–37) | **29**, zero left unscored |
| Ranks 1–8 | out of scope by design (the "ignore the top 8" rule) |
| Qualified leads | **8** |
| Primary qualification signal | recent positive reviews with **few/no owner responses** |

**Headline finding — the listing is bimodal.** Every business above roughly 230 reviews runs a
systematic reply programme (most at 100%). The unworked businesses sit between 34 and 641 reviews
with a flat zero. The single best lead, `Air of America` (641 reviews, 4.9★, rank 11), has **not
one reply**.

---

## 2. Pipeline (scripts/, in order)

| Step | Script | What it does |
|---|---|---|
| 1 | `local_rank_probe_v4.py <query>` | Ranked Maps feed → rank, name, rating, review count, phone, category, ad flag. Scrolls to "end of list". |
| 2 | `qualify_reviews_v2.py <lo> <hi> [--min-reviews=N]` | Per-business place page: rating/reviews/phone + owner-response behaviour on recent positive reviews. 40s/business floor. Resumable. |
| 3 | `merge_results.py` | Merges every qualify run into one record per business (best record wins) |
| 4 | `analyze_qualify.py` | Applies the qualification gates → `qualify_candidates.csv`, `qualify_leads.csv`, `qualify_report.md` |
| 5 | `deep_reviews.py "<name>"` | Full-population review pull (all reviews, not a sample) → pattern classification |
| 6 | `score_deep.py` | Scores on recent coverage + reply substance → `deep_scored.csv` |
| 7 | `check_posts.py` / `probe_posts_iso.py` | Verifies whether the profile posts GBP updates, and how recently |

Everything runs on the Hermes venv python (system 3.14 greenlet is broken):
`C:/Users/Russell/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe`

**Pacing rule (user-mandated): never faster than 40 seconds per business.** At faster paces Google
begins serving a sign-in modal over the listing (extraction returns nothing while the page is
visually complete). Raising the pace cleared 3/3 gates that a faster run could not.

---

## 3. Qualification gates (first test, tunable)

1. **Market position** — ignore the top 8, work ranks 9–37
2. **Review strength** — rating ≥ 4.5 **and** reviews ≥ 30 (relaxed to **20** for ranks 26+; no
   business in the tail sits between 20 and 29 reviews, so the relaxation changed zero membership)
3. **Review activity** — still receiving reviews
4. **Owner interaction** — few/no owner responses on *recent positive* reviews = the signal
5. **Exclude** anyone already responding consistently

---

## 4. Qualified leads

| Rank | Business | Rating (revs) | Newest | Owner responses | Pattern |
|---|---|---|---|---|---|
| 29 | **Andy Lewis/Hobson Heating & Air** | 4.7 (471) | 120d | **0 / 110 pulled** | SILENT |
| 25 | **H & M Services** | 4.9 (74) | 30d | **1 of 74** | SILENT |
| 11 | **Air of America Air Duct & Dryer Vent** | 4.9 (641) | 21d | **0 / 5 visible** | SILENT |
| 18 | Blasberg Cleaning | 4.7 (34) | 30d | 0 / 5 visible | SILENT (house cleaning — vertical mismatch) |
| 20 | Jade Heating & Air | 4.9 (100) | 90d | 0 / 5 visible | SILENT |
| 15 | **Technicare Home Pros** | 5.0 (343) | 30d | 1 of newest 10 | DECAYED |
| 26 | Georgia Comfort | 4.6 (59) | 30d | 7 of newest 10 unanswered | SPOTTY (capable) |
| 32 | ClimateSmith | 4.9 (58) | 60d | 2 of newest 10 unanswered | SHALLOW |

### Pattern taxonomy (the message-selection key)

| Pattern | Test | Implication |
|---|---|---|
| **SILENT** | lifetime ≈ 0% | original gap pitch |
| **DECAYED** | high lifetime, ≈0% recent | "your replies stopped ~3 months ago" — continuity, not persuasion |
| **SHALLOW** | recent coverage fine, reply substance ≤25% | template-vs-personalised side-by-side |
| **SPOTTY** | long personalised replies, low coverage | consistency pitch |
| **SYSTEMATIC** | recent + substance both high | exclude from response offers |

**Aggregate response rate is a misleading metric.** Technicare reads as *more* covered than
ClimateSmith on lifetime (90% vs 47%), but Technicare is the better prospect — a working habit that
lapsed. Score on **recent coverage (newest 10)** and **reply substance** (share of replies
mentioning the job/service); lifetime is context only.

Median reply length and bare-template share are the substance proxies: Technicare 16 chars
(`"Thank you!"` ×28, `"Thank you!!"` ×10, 72% bare template, **1 of 99** replies mentions the job);
ClimateSmith 45 chars, **1 of 27** mentions the job.

---

## 5. The claim-verification gate (do not skip)

Cold outreach here makes factual claims about the prospect's own profile. **Every claim must be
verified against their listing first** — the owner can disprove it in ten seconds, and a false
claim costs the whole email, not just a sentence.

| Lead | (a) "nobody's responded to recent reviews" | (b) "profile not updated in a while" |
|---|---|---|
| Andy Lewis/Hobson | ✅ 10/10 newest unanswered | n/a |
| H & M Services | ✅ 9/10; 1 reply in 74 | ✅ no update posts at all |
| Jade Heating & Air | ✅ all visible recent unanswered | ✅ no update posts at all |
| Blasberg Cleaning | ✅ all visible recent unanswered | ✅ no update posts at all |
| Georgia Comfort | ✅ 7/10 unanswered | ✅ no update posts at all |
| Air of America | ✅ 10/10 visible unanswered | ❌ posts updates (6 days ago) |
| Technicare Home Pros | ⚠️ true but blunt | ❌ **posts weekly** (7d, Sep 10, Sep 3, Aug 27) |
| ClimateSmith | ❌ **8/10 newest have replies** | ❌ posts (Sep 14, Aug 25, Aug 18) |

**Discovery: claims (a) and (b) travel together.** Every business that replies also posts updates;
every business that ignores reviews has no posts either — profile maintenance is one habit, not
two. So *no replies **and** no posts* is a stronger unmanaged-profile qualifier than either alone.
Air of America is the exception (posts, never replies) — which is why it belongs in template A.

---

## 6. Outreach

Two opener templates under A/B test. Both follow the written-only, no-call pattern: the opener has
one job — offer something useful free and ask permission. No pitch, no price, no attachment.
Report is built **only** after they say yes.

**Template A** — observation pair only:

> Hi [First],
> I was looking at HVAC and duct cleaning companies around Cumming and came across Georgia Comfort.
> When you reply to a review you do it properly — you named Alvin and Ryan and thanked the customer by name. But most of your recent reviews never get one: seven of your last ten are still sitting unanswered.
> …Want me to send it over? — Russell

**Template B** — same verified observation pair, plus a consequence line and a de-risker:

> Hi [First],
> …But most of your recent reviews never get one: seven of your last ten are still sitting unanswered. That can make it harder for people to find and choose you when they search for a duct cleaning expert in Cumming. I put together a short one-page report showing a few simple changes that could help.
> Would it be all right if I sent it over?
> No charge, it's yours either way.

**Find vs Choose rule.** "Choose" is always defensible — the evidence lives on the profile
(unanswered reviews, one-line replies are literally what a homeowner reads before calling).
"Find" is a ranking claim and may only be made where the rank is itself evidence — i.e. they rank
**worse than competitors with weaker or comparable reviews**. Air of America (rank 11) gets
"choose" only; Andy Lewis (471 reviews at 4.7 sitting 29th while 50–100-review businesses rank
above it) gets both.

### A/B assignment (pattern-matched, not shuffled)

A blind split confounds template with lead pattern — the first shuffle put all four SILENT leads in
one arm. Assignment is paired within pattern:

| Arm | Leads |
|---|---|
| **A** (original) | Andy Lewis/Hobson · Air of America · Blasberg |
| **B** (new) | H & M Services · Jade Heating & Air · Georgia Comfort |
| custom (outside test) | Technicare (decayed line) · ClimateSmith (shallow line) |

Core read is the **2v2 among SILENT leads** (Andy Lewis + Blasberg vs H & M + Jade).

**Power caveat:** 3 vs 3 proves nothing. 0/3 vs 2/3 is a hint; 0/3 vs 3/3 is actionable. The real
answer needs the next markets (Alpharetta, Johns Creek, Roswell) + one different trade until each
arm holds 15–20 sends.

---

## 7. Open items

- **Owner first names are unfilled for all eight leads.** Do not guess — a wrong name kills the
  email faster than no name. Source candidates: their websites, GBP owner info, or reviews
  (ClimateSmith's reviews name James and Jason).
- **Air of America needs a full-population pull** (only 5 of 641 reviews reached) so a specific
  number can replace "the recent ones".
- **Template B bundles three changes** (consequence line, "no charge" de-risker, extra
  specificity). A reply-rate win won't isolate which element did it; the cheapest follow-up test
  is A vs A+consequence-only.
- Jade, Blasberg and Air of America have **thin deep pulls** (5 reviews). Claims are worded safely,
  but the full populations aren't in hand.

---

## 8. Files

```
scripts/   9 files — the pipeline above (run in numeric order)
results/   17 files
  ranked_duct_cumming_v4.json/.csv ....... the ranked feed (source of truth for ranks)
  qualify_merged.jsonl ................... one record per business, best-run-wins
  qualify_candidates.csv ................. all 29 businesses with verdicts
  qualify_leads.csv ...................... the 8 qualified leads
  qualify_report.md ...................... generated report
  deep_reviews.json ...................... full-population review pulls (raw)
  deep_scored.csv ........................ pattern scores
  gbp_posts.json ......................... update-post verification
  ab_test_tracker.csv .................... A/B assignment + claim status + outcome columns
  qualify_results*.jsonl ................. per-run raw scrape records (resumable state)
outreach/  2 files — outreach_drafts.md, outreach_ab_test.md (client-facing copy)
```

**Naming note:** results live in `results/`, not `data/` — the repo's `.gitignore` reserves
`data/` and `*.log` for runtime output. Per-run `.log` files stay out of git (they remain in the
local archive).

**Evidence screenshots are NOT in git** (5.8 MB, plus 33 MB of raw run screenshots) — repo hygiene.
They live on disk at:

```
C:\Users\Russell\Documents\GitHub\prospect-cumming-duct-cleaning-202609\
   files/evidence/   — screenshots backing the claims (SERP map pack, review panes,
                       Technicare weekly posts, H&M no-posts)
   files/data/       — the same result files plus the run .log files
   files/_archive/   — every probe/diagnostic script and raw run screenshot
```

Load-bearing evidence: `posts_iso_Technicare_Home_Pros_Cummi.png` (weekly update posts),
`posts_iso_H_M_Services_Cumming_GA.png` (no posts surface), `rev_Air_of_America_*.png` (unanswered
reviews), `serp_v4.png` (the map module + ranked list).

---

## 9. Re-running for another market

```bash
cd <this dir>/scripts
PY="C:/Users/Russell/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe"
"$PY" local_rank_probe_v4.py "best duct cleaning in Alpharetta GA"     # ranks
"$PY" qualify_reviews_v2.py 9 40 --min-reviews=20                     # qualification (40s each)
"$PY" merge_results.py && "$PY" analyze_qualify.py                    # scored lead table
"$PY" deep_reviews.py "Business Name City GA"                         # full-population pull
"$PY" score_deep.py                                                   # pattern + substance
```

Then re-apply §5 before any email goes out.

Reusable method lives in two Hermes skills: **`local-rank-tracking`** (rank + review measurement,
deep pulls, pacing, DOM recipes) and **`review-gap-outreach`** (claim-verification gate, pattern →
message mapping, opener structure, A/B protocol).
