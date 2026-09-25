"""Backfill `city` (and `website`) into capture records written before those fields existed.

The fields are derived from data each capture already stores (its `address`, its `website`),
so this is a re-derivation, not new evidence: no network call, and a capture whose address
is missing or unparseable is left with an explicit `city` gap rather than a guess.

Idempotent: records already carrying a city are skipped. Safe to re-run.

Usage: python backfill_geo_fields.py <run data dir>
"""
import glob
import json
import os
import sys

from geo_fields import city_from_address

D = sys.argv[1] if len(sys.argv) > 1 else (
    r"C:/Users/Russell/Documents/GitHub/bb-audit-kit/research/hermes/"
    r"2026-09-24-duct-cleaning-canton-ga/data")

touched = skipped = gapped = 0
cities = {}
for path in sorted(glob.glob(os.path.join(D, "captures", "*.json"))):
    rec = json.load(open(path, encoding="utf-8"))
    city = city_from_address(rec.get("address") or "")
    if rec.get("city") == city and "website" in rec:
        skipped += 1
        continue
    rec["city"] = city
    rec.setdefault("website", "")
    if city:
        cities[city] = cities.get(city, 0) + 1
    else:
        gapped += 1
        rec.setdefault("gaps", {})
        rec["gaps"].setdefault("city", ("no city: the listing shows no address, or one not "
                                        "in '<street>, <city>, <ST> <ZIP>' order"))
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rec, f, indent=2, ensure_ascii=False)
    touched += 1

print(f"{os.path.basename(D.rstrip('/'))}: backfilled {touched}, already current {skipped}, "
      f"no city derivable {gapped}")
if cities:
    print("  cities:", ", ".join(f"{c} x{n}" for c, n in sorted(cities.items())))
