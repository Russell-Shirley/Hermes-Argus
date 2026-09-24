"""Validate deep review pulls against the ranked feed before anything is scored.

The deep pull reaches a listing through the Maps search box, so a query can land on a
DIFFERENT business (a namesake, or a bare `Results` page). Scoring such a pull would
fabricate a claim about the lead, so every pull is checked against the feed's
rating/review-count for that name first.

Usage:
    python validate_deep_pulls.py [<run data dir>] [--quarantine]

`--quarantine` moves unusable pulls out of `deep_reviews.json` into
`deep_reviews_rejected.json` (with a reason), so a scoring pass can never read them.
Rejected pulls stay on disk as evidence of what was tried.
"""
import csv
import json
import os
import sys

args = [a for a in sys.argv[1:] if not a.startswith("--")]
QUARANTINE = "--quarantine" in sys.argv

D = args[0] if args else (
    r"C:/Users/Russell/Documents/GitHub/bb-audit-kit/research/hermes/"
    r"2026-09-24-duct-cleaning-canton-ga/data")

pulls = json.load(open(os.path.join(D, "deep_reviews.json"), encoding="utf-8"))
feed = json.load(open(os.path.join(D, "ranked-feed.json"), encoding="utf-8"))
by_name = {r["name"]: r for r in feed["maps_full"]}
leads = {r["name"]: r for r in csv.DictReader(open(os.path.join(D, "qualify_leads.csv"), encoding="utf-8"))}


def verdict(r):
    """(usable, reason) — is this pull evidence about the lead it names?"""
    nm = (r.get("name") or "").strip()
    total = r.get("reviews") or r.get("review_count") or ""
    if nm.lower() in ("results", "search results") or nm.startswith("http"):
        return False, "landed on the search results page — no listing was opened"
    if nm not in leads:
        return False, "opened a different business (not one of this run's leads)"
    lead = leads[nm]
    if lead["reviews"] != str(total) or lead["rating"] != str(r.get("rating")):
        return False, (f"wrong listing for this name — lead is "
                       f"{lead['rating']}({lead['reviews']}), pull is {r.get('rating')}({total})")
    return True, "ok"


valid, rejected = [], []
for r in pulls:
    ok, why = verdict(r)
    (valid if ok else rejected).append((r, why))
    nm = (r.get("name") or "(blank)").strip().replace("\n", " ")
    print(f"{nm[:39]:<40}{str(r.get('rating')) + '(' + str(r.get('reviews') or '') + ')':<18}"
          f"{len(r.get('reviews_sampled') or []):>5}  {'ok' if ok else why}")

print(f"\npulls: {len(pulls)} | usable: {len(valid)} | rejected: {len(rejected)}")
covered = {r.get("name") for r, _ in valid}
print("leads with a usable pull:", f"{len(covered)}/{len(leads)}")
missing = [n for n in leads if n not in covered]
for n in missing:
    print("  NO USABLE PULL:", n)

if QUARANTINE:
    if rejected:
        rp = os.path.join(D, "deep_reviews_rejected.json")
        prior = json.load(open(rp, encoding="utf-8")) if os.path.exists(rp) else []
        prior.extend({**r, "_rejected_because": why} for r, why in rejected)
        with open(rp, "w", encoding="utf-8") as f:
            json.dump(prior, f, indent=2, ensure_ascii=False)
        with open(os.path.join(D, "deep_reviews.json"), "w", encoding="utf-8") as f:
            json.dump([r for r, _ in valid], f, indent=2, ensure_ascii=False)
        print(f"\nquarantined {len(rejected)} pull(s) -> {rp}")
        print(f"deep_reviews.json now holds {len(valid)} usable pull(s)")
    else:
        print("\nnothing to quarantine")
