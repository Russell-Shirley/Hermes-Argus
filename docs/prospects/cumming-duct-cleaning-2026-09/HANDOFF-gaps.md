# Handoff — what our Google Business Profile capture does NOT have

**Purpose:** give another model (Claude / ChatGPT) enough context to propose a better pull method
for the missing rows. Self-contained; no other context needed.

**Context in one paragraph:** we are prospecting local service businesses (duct cleaning / HVAC in
Cumming, GA) for a review-management offer. For each business we capture Google Business Profile
data and score it on 14 diagnostics that a review-management report needs. Capture runs through a
headless stealth browser (CloakBrowser) against public Google Maps place pages, with a hard
40-second-per-business pacing floor. Source: `capture_business.py` + `summarize_captures.py`.

---

## 1. What we DO capture (validated)

Per business, one JSON record. Verified against independently-computed values from earlier
full-population pulls:

| # | Diagnostic | How we compute it | Status |
|---|---|---|---|
| 1 | Recent response coverage — newest 10 + last 90 days | count of reviews with an owner-response block | ✅ |
| 2 | Historical coverage (up to ~110 reviews) | same, over the full pulled set | ✅ |
| 3 | Response trend | coverage of reviews ≤2y vs >2y, ±15pt band → improving / flat / deteriorating | ✅ |
| 4 | Response speed | review "age" minus response "age" | ⚠️ coarse (see §3) |
| 5 | Reply substance | median reply chars; % bare-template (`"Thank you!"`); % mentioning a service word; % naming the reviewer | ✅ |
| 6 | Critical-review handling | count of 1–3★ reviews, how many answered, their lag | ✅ |
| 7 | Review velocity | reviews within 365 days ÷ 12, in-sample | ⚠️ biased (see §3) |
| 8 | Latest-review freshness | age of newest review | ✅ |
| 9 | GBP post activity | click-through to the posts surface, read dated entries | ✅ via separate probe |
| 10 | Primary category | stable page class + regex fallback | ✅ |
| 11 | Secondary categories | — | ❌ |
| 12 | Service area | pane text "Serves …" | ⚠️ rarely rendered |
| 13 | Photos (count + owner cadence) | photo control label | ❌ (count only, unreliable; cadence not available) |
| 14 | Competitive context | re-run per competitor | ✅ mechanically, not yet run |

### Actual output for the 8 lead businesses

| Business | Revs | Pulled | Newest 10 answered | Last 90d | Lifetime | Med reply ch | Bare tpl % | Mentions service % | Critical answered | Fresh | Primary category |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Air of America Air Duct & Dryer Vent | 642 | 5* | 0/5 | 0/3 | 0% | — | — | — | 0/0 | 21d | Air duct cleaning service |
| Andy Lewis/Hobson Heating & Air | 471 | 90 | 0/10 | 0/1 | 0% | — | — | — | 0/12 | 90d | HVAC contractor |
| Technicare Home Pros | 343 | 90 | 1/10 | 0/6 | 88% | 16 | 67 | 1 | 0/0 | 30d | Carpet cleaning service |
| Jade Heating & Air | 100 | 90 | 3/10 | 2/5 | 18% | 22.5 | 25 | 6 | 0/1 | 30d | Air conditioning contractor |
| H & M Services | 74 | 5* | 0/5 | 0/2 | 0% | — | — | — | 0/0 | 30d | Plumber |
| Georgia Comfort Heating & Air | 59 | 5* | 2/5 | 0/2 | 40% | 127 | 0 | 0 | 0/1 | 30d | HVAC contractor |
| ClimateSmith | 58 | 5* | 4/5 | 0/1 | 80% | 71 | 0 | 25 | 0/0 | 60d | Heating contractor |
| Blasberg Cleaning | 34 | 34 | 0/10 | 0/3 | 26% | 90 | 0 | 56 | 1/2 | 30d | Cleaners |

`*` = expansion failed on that run; derived metrics deliberately withheld (see §3).

---

## 2. What we do NOT have — the four gaps

### Gap A — Secondary categories (row 11)
**Where it lives:** the profile's About/Details section.
**Why we can't get it:** that section is sign-in gated on Google Maps for signed-out clients. The
public place pane exposes only the primary category.
**What we want from the other model:** confirm whether Google Places API (New) `Place Details`
returns the full `types[]` array (primary + secondary) for a place_id, and whether that array is a
faithful mirror of the profile's categories or a different taxonomy. If it works, it's a one-field
addition keyed on place_id.
**Fallback if no API:** infer from reviews + website (customers name the services they bought).

### Gap B — Services coverage (profile services vs website offering)
**Where it lives:** the profile's owner-editable Services list; the business's own website.
**Why we can't get it:** the Services list is not exposed in the public Maps pane, and is not (to
our knowledge) exposed by any public API. It is owner-authored content.
**What we want:** (1) confirm whether any commercial endpoint (SerpApi Google Maps, DataForSEO
Business Data, Outscraper) returns GBP *services*; (2) propose the cheapest defensible substitute —
our working idea is a **website crawl** (services advertised on site) diffed against the *primary
category* + services named in reviews, so the report can still say "three services you advertise
aren't represented on the profile" with an explicit evidence basis.

### Gap C — Photos: count and owner-upload cadence (row 13)
**Where it lives:** the Photos tab (count, uploader attribution, dates).
**Why we can't get it:** the Photos tab is sign-in gated; the pane only gives an unusable label
("Photo of <business>") rather than a count.
**What we want:** confirm whether the Places API photo objects (or a commercial wrapper) expose
photo count, `authorAttributions`, and dates — i.e. whether "68 photos, newest owner photo 3 years
old" is obtainable, or whether only a raw count is.

### Gap D — GBP post activity, reliable version (row 9)
**Status:** we HAVE this, but the cheap method is unreliable and the reliable method is slow.
**The failure mode:** reading the place pane for post text returned "no posts" for a business that
posts **weekly**. False negative, and the worst direction — we would tell a posting business their
profile looks abandoned.
**What works:** clicking through to the posts surface and reading dated entries (separate probe,
slower).
**What we want:** whether any API returns GBP posts (`posts` / `localPosts`) with dates and a
cadence — DataForSEO has a Business Posts endpoint (to verify: coverage, freshness, cost).

---

## 3. Two caveats that are not gaps but limit the numbers

1. **Response speed is quantised.** Google renders relative ages ("a month ago"), never dates. Our
   lag figures come out as ~0d or ~30d and cannot support "typical response time is X days" — they
   can only separate fast from slow. **The only fix is a source with exact timestamps.**
   Open question for the other model: does any API expose (a) exact review timestamps and (b) exact
   owner-response timestamps? Without (b) the row stays unusable.
2. **Thin pulls.** The review-list expansion is throttle-dependent and intermittently returns only
   the ~5-review preview instead of the full list (4 of 8 businesses this pass). We gate this
   (metrics withheld below 20 reviews, flagged `THIN SAMPLE`), so a thin pull never presents as a
   finding — but it means a capture pass often has to be re-run. Fixes are retry/pacing, not parsing.
3. **Velocity is in-sample and relevance-ordered**, not chronological. Exact timestamps (see 1)
   would make it exact.

---

## 4. The ask

For each of Gaps A–D and the timestamp question in §3.1, we want:

1. whether a public/commercial API actually returns it (name the endpoint + field),
2. the cheapest source that does, with a rough cost per business,
3. or, if nothing does, the best defensible proxy and how to label it honestly in a client report.

We are not building anything yet — this is a "what are our options" pass.

---

## 5. Files

- `scripts/capture_business.py` — the capture (one business per invocation)
- `scripts/summarize_captures.py` — renders the matrix
- `results/captures/*.json` — per-business records, each with an explicit `gaps` map
- `results/captures/MATRIX.txt` — the rendered matrix
- `results/posts_verified.json` — the reliable click-through post evidence (row 9)
- `results/deep_reviews.json` — earlier full-population review pulls (ground truth for validation)
