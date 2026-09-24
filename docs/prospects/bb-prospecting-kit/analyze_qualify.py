"""Score the qualification pass against the user's criteria and emit report + CSV.

Criteria (first test, from the user):
  1. Market position: ignore roughly the top 8 -> work ranks 9-30
  2. Review strength: rating >= 4.5 AND reviews >= 30
  3. Review activity: still receiving reviews (newest review recency)
  4. Owner interaction: few/no owner responses on recent POSITIVE reviews = qualified
  5. Exclude businesses that already respond consistently
Writes qualify_report.md + qualify_candidates.csv
"""
import csv, json, os, re, sys

OUT = os.path.dirname(os.path.abspath(__file__))
# The run's data dir. Defaults to <run>/data when this toolkit is copied into
# <run>/scripts/; set RUN_DATA to run it IN PLACE against any run folder.
DATA = os.environ.get("RUN_DATA") or os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "data")
SRC = os.path.join(DATA, "qualify_merged.jsonl")

EXCLUDE_ALWAYS_DEFAULT: set = set()

_AREA_ARG = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--area-label=")), "")

try:
    # One implementation of the label convention for the whole kit: 'canton-ga' and
    # 'Canton-GA' both render 'Canton-GA', so a changed convention is a one-line edit
    # in contacted_ledger rather than a hand-edit in two files.
    from contacted_ledger import area_label_for as _area_label_for
except ImportError as _e:  # pragma: no cover
    raise SystemExit(
        "analyze_qualify.py must sit beside contacted_ledger.py — run the kit in place "
        f"against a run's data dir (RUN_DATA=...), don't copy single scripts out: {_e}")

# Which search captured this business. Rendered on every row so a lead can be traced
# back to the run that found it, e.g. "Cumming-GA - Bobs Dryer Vent Cleaning".
AREA_LABEL = _area_label_for(_AREA_ARG)


def load_exclusions() -> set:
    """Per-run "never contact this one" call-outs live WITH the run, not in the toolkit.

    `<run data>/exclusions.json` — either ``["Name", ...]`` or ``{"names": [...]}``.
    Hardcoding a city's call-out here leaked that city's judgement into every other
    run the toolkit serves.
    """
    path = os.path.join(DATA, "exclusions.json")
    if not os.path.exists(path):
        return set(EXCLUDE_ALWAYS_DEFAULT)
    try:
        raw = json.load(open(path, encoding="utf-8"))
    except Exception as e:
        print(f"WARNING: could not read {path} ({e}) — using no exclusions")
        return set(EXCLUDE_ALWAYS_DEFAULT)
    names = raw.get("names") if isinstance(raw, dict) else raw
    return {str(n).strip() for n in (names or []) if str(n).strip()} or set(EXCLUDE_ALWAYS_DEFAULT)


EXCLUDE_ALWAYS = load_exclusions()


def captured_by(name: str) -> str:
    return f"{AREA_LABEL} - {name}" if AREA_LABEL else name


def tier(rate, n):
    """Owner-response tiering. Lower response rate = better fit."""
    if rate is None or n < 2:
        return "THIN", "not enough recent reviews to judge responses"
    if rate == 0:
        return "PRIME", "zero owner responses on recent positive reviews"
    if rate <= 25:
        return "STRONG", f"responds to only {rate}% of recent positive reviews"
    if rate <= 50:
        return "WATCH", f"responds to {rate}% — partial program exists"
    return "EXCLUDE", f"responds to {rate}% of recent positive reviews"


def activity(newest_days, last180, last365):
    if newest_days is None:
        return "UNKNOWN", "no dated reviews in sample"
    if newest_days <= 30:
        return "HOT", f"newest review {newest_days}d old"
    if newest_days <= 90:
        return "ACTIVE", f"newest review {newest_days}d old"
    if newest_days <= 180:
        return "SLOWING", f"newest review {newest_days}d old"
    return "DORMANT", f"newest review {newest_days}d old"


def main():
    recs = [json.loads(l) for l in open(SRC, encoding="utf-8")]

    # Feed-level truth (rating/reviews/phone from the ranked list) — a GATED page scrape
    # returns empty profile fields; scoring those as "no reputation" would be wrong.
    feed = {}
    try:
        d = json.load(open(os.path.join(DATA, "ranked-feed.json"), encoding="utf-8"))
        for r in d["maps_full"]:
            feed[r["name"]] = r
    except Exception:
        pass
    for r in recs:
        f = feed.get(r["name"], {})
        for k in ("rating", "reviews", "phone"):
            if not r.get(k):
                r[k] = f.get(k, "")
        if r.get("status") == "GATED":
            r["verdict_override"] = "NO DATA (reviews gated — rerun)"
    recs.sort(key=lambda r: r.get("rank") or 99)

    rows = []
    for r in recs:
        rate = r.get("response_rate_recent")
        n = r.get("recent_positive_n") or 0
        t, why_t = tier(rate, n)
        a, why_a = activity(r.get("newest_review_days"), r.get("reviews_last_180d"), r.get("reviews_last_365d"))
        in_scope = (r.get("rank") or 0) >= 9   # ignore roughly the top 8; no upper bound (list runs to 39)
        rating = float(r.get("rating") or 0)
        revs = int(r.get("reviews") or 0)
        strong_rep = rating >= 4.5 and revs >= 30
        excluded = r["name"] in EXCLUDE_ALWAYS or t == "EXCLUDE"
        verdict = ""
        if r.get("verdict_override"):
            verdict = r["verdict_override"]
        elif not in_scope:
            verdict = "OUT OF SCOPE (top 8)"  # ranks 1-8
        elif not strong_rep:
            verdict = "FAIL reputation gate"
        elif excluded:
            verdict = "EXCLUDE (already responds)"
        elif t == "THIN":
            verdict = "REVIEW MORE (thin sample)"
        elif a in ("HOT", "ACTIVE") and t in ("PRIME", "STRONG"):
            verdict = "QUALIFIED - PRIORITY" if t == "PRIME" else "QUALIFIED"
        elif a in ("HOT", "ACTIVE") and t == "WATCH":
            verdict = "QUALIFIED - WEAKER ANGLE"
        elif a in ("SLOWING", "DORMANT"):
            verdict = "HOLD (activity weak)"
        else:
            verdict = "REVIEW MORE"
        rows.append({**r, "tier": t, "tier_why": why_t, "activity": a, "activity_why": why_a,
                     "strong_rep": strong_rep, "verdict": verdict, "in_scope": in_scope})

    with open(os.path.join(DATA, "qualify_candidates.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["captured_by", "rank", "name", "rating", "reviews", "newest_review_days", "reviews_last_180d",
                    "sample_n", "recent_positive_n", "owner_responses", "owner_response_rate",
                    "activity", "owner_tier", "verdict", "phone", "status", "sorted_newest"])
        for r in rows:
            w.writerow([captured_by(r["name"]), r.get("rank"), r["name"], r.get("rating"), r.get("reviews"),
                        r.get("newest_review_days"), r.get("reviews_last_180d"), r.get("sample_size"),
                        r.get("recent_positive_n"), r.get("owner_responses_recent"),
                        r.get("response_rate_recent"), r["activity"], r["tier"], r["verdict"],
                        r.get("phone") or r.get("phone_feed"), r.get("status"), r.get("sorted_newest")])

    leads = [r for r in rows if str(r["verdict"]).startswith(("QUALIFIED", "HOLD"))]
    with open(os.path.join(DATA, "qualify_leads.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["captured_by", "rank", "name", "rating", "reviews", "newest_review_days",
                    "recent_positive_n", "owner_responses", "owner_response_rate", "activity",
                    "verdict", "phone"])
        for r in sorted(leads, key=lambda x: (0 if str(x["verdict"]).startswith("QUALIFIED - PRIORITY") else 1,
                                              x.get("rank") or 99)):
            w.writerow([captured_by(r["name"]), r.get("rank"), r["name"], r.get("rating"), r.get("reviews"),
                        r.get("newest_review_days"), r.get("recent_positive_n"), r.get("owner_responses_recent"),
                        r.get("response_rate_recent"), r.get("activity"), r.get("verdict"), r.get("phone")])
    print(f"leads written: {len(leads)}")

    print(f"{'rk':<3}{'business':<42}{'revs':>6}{'newest':>8}{'180d':>5}{'n':>4}{'own':>6}{'rate':>6}  {'tier':<8}{'activity':<9}verdict")
    for r in rows:
        print(f"{r.get('rank',''):<3}{r['name'][:41]:<42}{str(r.get('reviews') or ''):>6}"
              f"{str(r.get('newest_review_days') if r.get('newest_review_days') is not None else ''):>8}"
              f"{str(r.get('reviews_last_180d') or ''):>5}{str(r.get('recent_positive_n') or ''):>4}"
              f"{str(r.get('owner_responses_recent') or 0):>6}"
              f"{str(r.get('response_rate_recent') if r.get('response_rate_recent') is not None else ''):>6}  "
              f"{r['tier']:<8}{r['activity']:<9}{r['verdict']}")

    prim = [r for r in rows if r["verdict"].startswith("QUALIFIED")]
    print(f"\nqualified: {len(prim)} | of {len(rows)}")
    print("sorted_newest achieved:", sum(1 for r in rows if r.get("sorted_newest")), "/", len(rows))

    # The report header names the run, so derive it — a hardcoded city here shipped the
    # first run's title into every later one.
    title = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--title=")), "")
    if not title:
        title = (f"Duct cleaning — {AREA_LABEL}: mid-list qualification pass"
                 if AREA_LABEL else "Mid-list qualification pass")
    ranks = [r["rank"] for r in rows if r.get("rank")]
    span = f"ranks {min(ranks)}-{max(ranks)}" if ranks else "rank span unavailable"

    with open(os.path.join(DATA, "qualify_report.md"), "w", encoding="utf-8") as f:
        f.write(f"# {title}\n\n")
        f.write(f"Source list: Google Maps ranked feed (`ranked-feed.json`), {span}.\n")
        f.write(f"Businesses checked: {len(rows)}. Criteria: ignore the top 8, rating >= 4.5, reviews >= 30,\n")
        f.write("recent positive reviews with few/no owner responses.\n\n")
        f.write("| Rank | Business | Rating (revs) | Newest review | Owner resp. | Tier | Verdict |\n")
        f.write("|---|---|---|---|---|---|---|\n")
        for r in rows:
            f.write(f"| {r.get('rank')} | {r['name']} | {r.get('rating')} ({r.get('reviews')}) | "
                    f"{r.get('newest_review_days')}d | {r.get('owner_responses_recent')}/{r.get('recent_positive_n')} "
                    f"({r.get('response_rate_recent')}%) | {r['tier']} | {r['verdict']} |\n")
    print("wrote qualify_candidates.csv + qualify_report.md")


main()
