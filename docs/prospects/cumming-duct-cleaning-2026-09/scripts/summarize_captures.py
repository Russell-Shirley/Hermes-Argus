"""Summarise captures/*.json into the diagnostic matrix — one row per business, one
column per diagnostic. Anything not captured shows its GAP reason rather than a blank,
so a gate is never mistaken for a zero.
"""
import glob, json, os

OUT = os.path.dirname(os.path.abspath(__file__))
CAP = os.path.join(OUT, "captures")

ROWS = [
    ("1 recent coverage (newest 10)", lambda m, r: f"{m.get('recent10_answered')}/{m.get('recent10_total')} answered"),
    ("1b last 90 days", lambda m, r: f"{m.get('last90_answered')}/{m.get('last90_total')} answered"),
    ("2 historical coverage", lambda m, r: f"{m.get('lifetime_coverage_pct')}% of {m.get('pulled')} pulled"),
    ("3 response trend", lambda m, r: f"{m.get('trend_verdict')} (recent2y {m.get('trend_recent_2y_pct')}% vs older {m.get('trend_older_pct')}%)"),
    ("4 response speed", lambda m, r: f"~{m.get('lag_median_days_approx')}d median (n={m.get('lag_sample')}, quantised)"),
    ("5 substance", lambda m, r: f"median {m.get('reply_len_median')}ch; {m.get('bare_template_pct')}% bare; {m.get('reply_mentions_service_pct')}% mention service; {m.get('reply_mentions_reviewer_name_pct')}% name reviewer"),
    ("6 critical reviews", lambda m, r: f"{m.get('critical_answered')}/{m.get('critical_total')} answered (lag ~{m.get('critical_lag_median_days_approx')}d)"),
    ("7 velocity", lambda m, r: f"{m.get('velocity_per_month_in_sample')}/mo in-sample" if m.get('velocity_per_month_in_sample') is not None else "WITHHELD (thin sample)"),
    ("8 latest review freshness", lambda m, r: f"{m.get('latest_review_days')}d ago"),
    ("9 GBP posts", lambda m, r: ("posts present: " + ", ".join((r.get('posts') or {}).get('post_dated_entries') or []) if (r.get('posts') or {}).get('has_posts_surface') else "NO update posts found")),
    ("10 primary category", lambda m, r: r.get('category_primary') or "GAP"),
    ("11 services coverage", lambda m, r: "GAP — needs website pass / About tab (gated)"),
    ("12 service area", lambda m, r: r.get('service_area') or (r.get('gaps') or {}).get('service_area', 'GAP')),
    ("13 photos", lambda m, r: ((r.get('photo_control_text') or 'GAP') + " | owner cadence: GAP (Photos tab gated)")),
    ("14 competitive context", lambda m, r: "run per competitor"),
]

files = sorted(glob.glob(os.path.join(CAP, "*.json")))
recs = []
for f in files:
    try:
        j = json.load(open(f, encoding="utf-8"))
    except Exception:
        continue
    if j.get("status") in ("OK", "GATED", "ERROR") and j.get("name"):
        recs.append(j)

print(f"{len(recs)} captures\n")
for r in recs:
    m = r.get("metrics") or {}
    thin = "" if m.get("sample_sufficient") else "  [THIN SAMPLE — derived metrics withheld]"
    print(f"=== {r.get('name')} | {r.get('rating')}★ ({r.get('review_count')}) | {r.get('category_primary')} | {r.get('status')}{thin}")
    for label, fn in ROWS:
        try:
            val = fn(m, r)
        except Exception as e:
            val = f"ERR {e}"
        print(f"    {label:<30} {val}")
    g = r.get("gaps") or {}
    if g:
        print(f"    gaps: {', '.join(g.keys())}")
    print()
