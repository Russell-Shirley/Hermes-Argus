"""Score leads on the metrics that actually predict the message:
  1. recent coverage — share of the NEWEST 10 reviews with a reply
  2. reply substance  — share of replies that mention the job/service/tech, and reply length
  3. lifetime coverage — context only
Assigns a pattern: DECAYED / SHALLOW / SILENT / SYSTEMATIC / THIN
Writes deep_scored.csv
"""
import csv, json, os, re, statistics
from collections import defaultdict

OUT = os.path.dirname(os.path.abspath(__file__))
# The run's data dir. Defaults to <run>/data when this toolkit is copied into
# <run>/scripts/; set RUN_DATA to run it IN PLACE against any run folder.
DATA = os.environ.get("RUN_DATA") or os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "data")
src = json.load(open(os.path.join(DATA, "deep_reviews.json"), encoding="utf-8"))

# keep the pull with the most reviews per business
best = {}
for r in src:
    nm = r.get("name") or r.get("query")
    revs = r.get("reviews_sampled") or r.get("reviews") or []
    # a pull that landed on the search page reports the pane title "Results" (or the raw URL)
    # and belongs to a DIFFERENT company — never score it
    if not nm or nm.strip().lower() in ("results", "search results") or nm.startswith("http"):
        continue
    if not revs and r.get("status") == "GATED":
        continue
    if nm not in best or len(revs) > len(best[nm].get("reviews_sampled") or best[nm].get("reviews") or []):
        best[nm] = r

SERVICE_WORDS = re.compile(r"duct|vent|carpet|tile|clean|hvac|furnace|system|repair|install|"
                           r"technician|tech\b|service|maintenance|dryer|air|job", re.I)
BARE_TEMPLATE = re.compile(r"(?i)^thank you[,.!]?\s*[A-Za-z]*[!.\s]*$")

rows = []
for nm, rec in best.items():
    revs = rec.get("reviews_sampled") or rec.get("reviews") or []
    if not revs:
        continue
    n = len(revs)
    responded = sum(1 for r in revs if r["owner_response"])
    lifetime = round(100 * responded / n)
    dated = sorted([r for r in revs if r["age_days"] is not None], key=lambda r: r["age_days"])
    newest10 = dated[:10]
    recent_cov = round(100 * sum(1 for r in newest10 if r["owner_response"]) / len(newest10)) if newest10 else None
    reps = [r["response_text"].strip() for r in revs if r["owner_response"] and r["response_text"]]
    substance = round(100 * sum(1 for x in reps if SERVICE_WORDS.search(x)) / len(reps)) if reps else None
    bare = round(100 * sum(1 for x in reps if BARE_TEMPLATE.match(x)) / len(reps)) if reps else None
    med_len = round(statistics.median([len(x) for x in reps])) if reps else None
    total_reviews = rec.get("reviews") if isinstance(rec.get("reviews"), str) else None

    if n < 10:
        pattern, why = "THIN", f"only {n} reviews surfaced — pull again before pitching"
    elif recent_cov is not None and recent_cov <= 20:
        pattern = "DECAYED" if lifetime >= 60 else "SILENT"
        why = (f"lifetime {lifetime}% but newest 10 only {recent_cov}% — "
               + ("program lapsed recently" if lifetime >= 60 else "never really replied"))
    elif recent_cov is not None and recent_cov >= 70:
        pattern, why = ("SHALLOW" if (substance is not None and substance <= 25) else "SYSTEMATIC",
                        f"recent {recent_cov}% but only {substance}% of replies mention the job")
    else:
        pattern, why = "SPOTTY", f"recent {recent_cov}%, lifetime {lifetime}% — inconsistent"

    rows.append({"rank": rec.get("rank"), "business": nm, "reviews_total": total_reviews,
                 "pulled": n, "lifetime_coverage_pct": lifetime, "recent10_coverage_pct": recent_cov,
                 "replies": len(reps), "reply_substance_pct": substance, "bare_template_pct": bare,
                 "median_reply_chars": med_len, "pattern": pattern, "why": why})

rows.sort(key=lambda r: (r["pattern"] != "DECAYED", r["pattern"] != "SILENT", r["pattern"] != "SHALLOW",
                         r["pattern"] != "SPOTTY", r["rank"] or 99))

cols = ["rank", "business", "reviews_total", "pulled", "lifetime_coverage_pct", "recent10_coverage_pct",
        "replies", "reply_substance_pct", "bare_template_pct", "median_reply_chars", "pattern", "why"]
with open(os.path.join(DATA, "deep_scored.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
    w.writeheader()
    for r in rows:
        w.writerow(r)

print(f"{'business':<44}{'pulled':>7}{'life%':>7}{'new10%':>8}{'subst%':>8}{'medch':>6}  pattern")
for r in rows:
    print(f"{r['business'][:43]:<44}{r['pulled']:>7}{r['lifetime_coverage_pct']:>7}"
          f"{str(r['recent10_coverage_pct']):>8}{str(r['reply_substance_pct']):>8}"
          f"{str(r['median_reply_chars']):>6}  {r['pattern']} — {r['why']}")
print("\nwrote deep_scored.csv")
