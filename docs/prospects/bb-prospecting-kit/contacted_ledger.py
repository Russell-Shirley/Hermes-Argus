#!/usr/bin/env python3
"""contacted_ledger — cross-city dedupe + send tracking for prospect runs.

Ledger is append/upsert JSONL, one record per business:
    research/prospects/contacted.jsonl

Why one file: git keeps the history, it diffs line-by-line, and any run (or any
agent) can read it without a database.

Match keys (in priority order):
    1. phone_digits  — a business's phone is the reliable join. Same phone = same
                       business, even across cities.
    2. name_norm + area — catches duplicate listings of one business in one market.
    3. name_norm alone, different area — FLAG, never auto-skip. Two towns can each
                       have an "H & M Services"; assuming they're the same business
                       would silently drop a real prospect.

Usage
    python contacted_ledger.py seed  --from-candidates <qualify_candidates.csv> \\
        --run hermes/2026-09-22-duct-cleaning-cumming-ga --area cumming-ga --niche duct-cleaning
    python contacted_ledger.py check --feed <ranked-feed.json> --area alpharetta-ga
    python contacted_ledger.py mark  --name "Air of America" --phone 7708003152 \\
        --status contacted --sender acct-1 --date 2026-09-23
    python contacted_ledger.py stats
    python contacted_ledger.py cap    --sender acct-1 --date 2026-09-23 --limit 20
    python contacted_ledger.py --selftest
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from datetime import date

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))


def default_ledger() -> str:
    """Where ``contacted.jsonl`` lives.

    The ledger sits with the prospect DATA, not with this tool, so the default is
    derived from the tool's location instead of being hard-coded — that is what
    lets the toolkit live in one place and serve every run:

      * ``<prospects>/tools/contacted_ledger.py`` -> ``<prospects>/contacted.jsonl``
      * ``<research>/tools/contacted_ledger.py``  -> ``<research>/prospects/contacted.jsonl``

    Override with ``--ledger`` or ``PROSPECT_LEDGER`` to share one ledger across
    workspaces, or to point at a ledger kept elsewhere.
    """
    env = os.environ.get("PROSPECT_LEDGER")
    if env:
        return env
    parent = os.path.dirname(TOOLS_DIR)
    if os.path.isdir(os.path.join(parent, "prospects")):
        return os.path.join(parent, "prospects", "contacted.jsonl")
    return os.path.join(parent, "contacted.jsonl")


LEDGER = default_ledger()

# outcomes that mean "already handled — do not re-prospect this business"
SKIP_OUTCOMES = {"contacted", "replied", "won", "lost", "disqualified", "excluded", "drafted"}
SUFFIXES = {"llc", "inc", "co", "corp", "ltd", "company", "incorporated", "limited"}


def norm_name(name: str) -> str:
    """lowercase, punctuation -> spaces, drop legal suffixes and a leading 'the'."""
    s = re.sub(r"[^a-z0-9 ]+", " ", (name or "").lower())
    toks = [t for t in s.split() if t and t not in SUFFIXES]
    if toks and toks[0] == "the":
        toks = toks[1:]
    return " ".join(toks)


def norm_phone(phone: str) -> str:
    """digits only; drop a leading US country code so 11- and 10-digit forms match."""
    d = re.sub(r"\D", "", phone or "")
    if len(d) == 11 and d.startswith("1"):
        d = d[1:]
    return d


def key_for(name: str, phone: str) -> str:
    return f"{norm_name(name)}|{norm_phone(phone)}"


def area_label_for(area: str, label: str = "") -> str:
    """Human label for the area slug.

    'cumming-ga' -> 'Cumming-GA'; 'forsyth-county-ga' -> 'Forsyth-County-GA'.
    2-letter tokens are state codes and stay uppercase — the state is what
    disambiguates one town's search from another's. Pass `label` to override
    (e.g. 'Forsyth-County' when the run was county-framed rather than town-framed).
    """
    if label:
        return label
    toks = [t for t in (area or "").replace("_", "-").split("-") if t]
    return "-".join(t.upper() if len(t) <= 2 else t.capitalize() for t in toks)


def captured_by(name: str, area: str, label: str = "") -> str:
    """The association string: which search captured this business, e.g.
    'Cumming - Bobs Dryer Vent Cleaning' or 'Forsyth County - Bobs Dryer Vent Cleaning'."""
    return f"{area_label_for(area, label)} - {name}".strip()


def load() -> list[dict]:
    if not os.path.exists(LEDGER):
        return []
    out = []
    with open(LEDGER, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def save(recs: list[dict]) -> None:
    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    tmp = LEDGER + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        for r in sorted(recs, key=lambda x: x["key"]):
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=False) + "\n")
    os.replace(tmp, LEDGER)


def find(recs: list[dict], name: str, phone: str, area: str | None = None):
    """Return (record, match_type) or (None, None). Priority: phone, name+area, name."""
    p = norm_phone(phone)
    if p:
        for r in recs:
            if r.get("phone_digits") and r["phone_digits"] == p:
                return r, "phone"
    n = norm_name(name)
    if n and area:
        for r in recs:
            if r.get("name_norm") == n and r.get("area") == area:
                return r, "name+area"
    if n:
        for r in recs:
            if r.get("name_norm") == n:
                return r, "name-only"
    return None, None


def find_strict(recs: list[dict], name: str, phone: str, area: str | None = None):
    """Write-path matching. Phone, or name+area only.

    The name-only fallback is deliberately excluded: two towns can each have an
    'H & M Services', and merging them would silently drop a real prospect and
    corrupt an outcome. Name-only matches are surfaced by `check` as FLAG.
    """
    p = norm_phone(phone)
    if p:
        for r in recs:
            if r.get("phone_digits") and r["phone_digits"] == p:
                return r, "phone"
    n = norm_name(name)
    if n and area:
        for r in recs:
            if r.get("name_norm") == n and r.get("area") == area:
                return r, "name+area"
    return None, None


def upsert(recs: list[dict], name: str, phone: str, area: str, niche: str, run: str,
           outcome: str, reason: str = "", **extra) -> tuple[dict, bool]:
    """Insert or advance a record. Existing records are never downgraded."""
    existing, mtype = find_strict(recs, name, phone, area)
    if existing:
        changed = False
        if outcome and _rank_outcome(outcome) > _rank_outcome(existing.get("outcome", "")):
            existing["outcome"] = outcome
            changed = True
        if reason and not existing.get("outcome_reason"):
            existing["outcome_reason"] = reason
            changed = True
        for k, v in extra.items():
            if v not in (None, "") and existing.get(k) in (None, ""):
                existing[k] = v
                changed = True
        existing.setdefault("also_seen_in", [])
        if run and run not in existing["also_seen_in"] and existing.get("run") != run:
            existing["also_seen_in"].append(run)
            changed = True
        return existing, changed
    rec = {
        "key": key_for(name, phone),
        "name": name,
        "name_norm": norm_name(name),
        "captured_by": captured_by(name, area),
        "phone": phone or "",
        "phone_digits": norm_phone(phone),
        "area": area,
        "area_label": area_label_for(area),
        "niche": niche,
        "run": run,
        "outcome": outcome,
        "outcome_reason": reason,
        "first_seen": date.today().isoformat(),
        "contacted": None,
        "replied": None,
        "notes": "",
    }
    rec.update({k: v for k, v in extra.items() if v not in (None, "")})
    recs.append(rec)
    return rec, True


_OUTCOME_ORDER = ["", "excluded", "disqualified", "qualified", "drafted", "contacted", "replied", "won", "lost"]


def _rank_outcome(o: str) -> int:
    try:
        return _OUTCOME_ORDER.index(o or "")
    except ValueError:
        return 0


def cmd_seed(a) -> int:
    recs = load()
    added = advanced = 0
    with open(a.from_candidates, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            verdict = (row.get("verdict") or "").strip()
            outcome = ("excluded" if verdict.upper().startswith("EXCLUDE")
                       else "disqualified" if verdict.upper().startswith(("FAIL", "OUT OF SCOPE"))
                       else "qualified" if verdict.upper().startswith("QUALIFIED")
                       else "excluded" if verdict.upper().startswith("NO DATA")
                       else "review")
            nm = row.get("name", "")
            _, changed = upsert(recs, nm, row.get("phone", ""), a.area, a.niche, a.run,
                                outcome, reason=verdict, rank=row.get("rank"), rating=row.get("rating"),
                                reviews=row.get("reviews"),
                                area_label=area_label_for(a.area, a.area_label),
                                captured_by=captured_by(nm, a.area, a.area_label))
            if a.relabel:
                rec = find_strict(recs, nm, row.get("phone", ""), a.area)[0]
                if rec:
                    rec["area_label"] = area_label_for(a.area, a.area_label)
                    rec["captured_by"] = captured_by(nm, a.area, a.area_label)
            added += 1 if changed else 0
    save(recs)
    print(f"seed: {added} records written from {a.from_candidates} -> {LEDGER} ({len(recs)} total)")
    return 0


def cmd_check(a) -> int:
    recs = load()
    feed = json.load(open(a.feed, encoding="utf-8"))
    entries = feed.get("maps_full") or feed.get("top_of_list") or []
    new, seen, flagged = [], [], []
    for e in entries:
        name, phone = e.get("name", ""), e.get("phone", "")
        rec, mtype = find(recs, name, phone, a.area)
        if not rec:
            new.append((e.get("local_rank"), name, phone))
        elif mtype == "name-only":
            # same name in another area: never auto-skip, whatever its outcome
            flagged.append((e.get("local_rank"), name, phone, rec.get("area"), rec.get("outcome")))
        else:
            seen.append((e.get("local_rank"), name, rec.get("outcome"), rec.get("area"), mtype))

    print(f"check against {LEDGER} ({len(recs)} businesses on file) — area={a.area}")
    print(f"\n  SKIP — already processed ({len(seen)}):")
    for r, n, o, ar, mt in seen:
        flag = "" if ar == a.area else f"  [from {ar}]"
        print(f"    #{str(r):<3} {n[:40]:<42} {o:<14} matched by {mt}{flag}")
    if flagged:
        print(f"\n  FLAG — same name, different area, not skipped ({len(flagged)}):")
        for r, n, ph, ar, o in flagged:
            print(f"    #{str(r):<3} {n[:40]:<42} seen in {ar} as {o}")
    print(f"\n  NEW — safe to process ({len(new)}):")
    for r, n, ph in new:
        print(f"    #{str(r):<3} {n[:40]:<42} {ph or '(no phone listed)'}")
    out = os.path.join(os.path.dirname(a.feed), "seen-skip.txt")
    with open(out, "w", encoding="utf-8") as f:
        for r, n, o, ar, mt in seen:
            f.write(f"{r}\t{n}\t{o}\t{ar}\t{mt}\n")
    print(f"\n  wrote {out}")
    return 0 if new else 3


def cmd_mark(a) -> int:
    recs = load()
    rec, mtype = find_strict(recs, a.name, a.phone, a.area or None)
    if not rec:
        if not a.create:
            print(f"not found: {a.name} / {a.phone} — pass --phone or --area to match, or --create to add it")
            return 2
        rec, _ = upsert(recs, a.name, a.phone, a.area or "unknown", a.niche or "unknown", "", a.status)
    if _rank_outcome(a.status) < _rank_outcome(rec.get("outcome", "")) and not a.force:
        print(f"refusing to downgrade {rec['name']}: {rec.get('outcome')} -> {a.status}")
        print("  (a status regression is a data error, not a discovery — pass --force if it is deliberate)")
        return 4
    rec["outcome"] = a.status
    if a.status == "contacted":
        rec["contacted"] = {"date": a.date or date.today().isoformat(), "sender": a.sender,
                            "channel": a.channel, "template_arm": a.arm}
    elif a.status == "replied":
        rec["replied"] = {"date": a.date or date.today().isoformat(), "snippet": a.notes}
    if a.notes:
        rec["notes"] = (rec.get("notes") or "") + ("" if not rec.get("notes") else " | ") + a.notes
    save(recs)
    print(f"mark: {rec['name']} -> {a.status} (matched by {mtype or 'new'})")
    return 0


def cmd_stats(a) -> int:
    recs = load()
    by_outcome, by_area = {}, {}
    for r in recs:
        by_outcome[r.get("outcome", "?")] = by_outcome.get(r.get("outcome", "?"), 0) + 1
        by_area[r.get("area", "?")] = by_area.get(r.get("area", "?"), 0) + 1
    print(f"ledger: {len(recs)} businesses")
    print("  by outcome:", dict(sorted(by_outcome.items(), key=lambda kv: -kv[1])))
    print("  by area:   ", by_area)
    return 0


def cmd_cap(a) -> int:
    recs = load()
    day = a.date or date.today().isoformat()
    n = sum(1 for r in recs if (r.get("contacted") or {}).get("date") == day
            and (r.get("contacted") or {}).get("sender") == a.sender)
    state = "OK" if n < a.limit else "CAP REACHED"
    print(f"sender {a.sender} on {day}: {n}/{a.limit} sends — {state}")
    return 0 if n < a.limit else 1


def cmd_selftest(a) -> int:
    checks = []
    checks.append(("phone: 11-digit country code matches 10-digit",
                   norm_phone("1-770-800-3152") == norm_phone("(770) 800-3152") == "7708003152"))
    checks.append(("name: punctuation + LLC dropped",
                   norm_name("Simply Clean Ducts & Vents LLC") == "simply clean ducts vents"))
    checks.append(("name: leading 'the' dropped", norm_name("The Honest Guys") == "honest guys"))
    checks.append(("label: 'cumming-ga' -> 'Cumming-GA' (state kept uppercase)",
                   area_label_for("cumming-ga") == "Cumming-GA"))
    checks.append(("label: 'forsyth-county-ga' -> 'Forsyth-County-GA'",
                   area_label_for("forsyth-county-ga") == "Forsyth-County-GA"))
    checks.append(("label: override honoured",
                   area_label_for("cumming-ga", "Forsyth-County") == "Forsyth-County"))
    checks.append(("captured_by association string",
                   captured_by("Bobs Dryer Vent Cleaning", "cumming-ga") == "Cumming-GA - Bobs Dryer Vent Cleaning"))
    recs = []
    r1, _ = upsert(recs, "Air of America Air Duct & Dryer Vent Cleaning Services", "(770) 800-3152",
                   "cumming-ga", "duct-cleaning", "run1", "qualified")
    r2, _ = upsert(recs, "Air of America", "7708003152", "alpharetta-ga", "duct-cleaning", "run2", "qualified")
    checks.append(("phone match skips across cities", r1 is r2 and len(recs) == 1))
    r3, _ = upsert(recs, "H & M Services", "(470) 111-2222", "cumming-ga", "duct-cleaning", "run1", "excluded")
    r4, _ = upsert(recs, "H & M Services", "(678) 999-8888", "alpharetta-ga", "duct-cleaning", "run2", "qualified")
    checks.append(("same name + different phone + different area = different business", r3 is not r4))
    r5, mtype = find(recs, "H&M Services", "", None)
    checks.append(("name-only lookup flags (never auto-merges)",
                   mtype == "name-only" and r5 in (r3, r4)))
    _, sm = find_strict(recs, "H&M Services", "", "alpharetta-ga")
    checks.append(("write path ignores bare name when area differs",
                   len([r for r in recs if r.get("name_norm") == "h m services"]) == 2))
    recs_c = []
    upsert(recs_c, "H & M Services", "(470) 111-2222", "cumming-ga", "duct-cleaning", "r", "contacted")
    _, mt = find(recs_c, "H&M Services", "(678) 999-8888", "alpharetta-ga")
    checks.append(("name-only match is reported as name-only (check must FLAG, not skip)", mt == "name-only"))
    recs2 = []
    ex, _ = upsert(recs2, "Tester Co", "4045551212", "cumming-ga", "duct-cleaning", "r", "excluded")
    adv, ch = upsert(recs2, "Tester Co", "(404) 555-1212", "cumming-ga", "duct-cleaning", "r", "contacted")
    checks.append(("outcome advances excluded -> contacted, no duplicate", ch and adv is ex and len(recs2) == 1))
    back, ch2 = upsert(recs2, "Tester Co", "4045551212", "cumming-ga", "duct-cleaning", "r", "excluded")
    checks.append(("outcome never downgrades", not ch2 and back["outcome"] == "contacted"))
    ok = True
    for label, passed in checks:
        print(f"  [{'PASS' if passed else 'FAIL'}] {label}")
        ok = ok and passed
    print("\nselftest:", "all passed" if ok else "FAILURES")
    return 0 if ok else 1


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--selftest", action="store_true")
    sub = p.add_subparsers(dest="cmd")

    s = sub.add_parser("seed"); s.add_argument("--from-candidates", required=True)
    s.add_argument("--run", required=True); s.add_argument("--area", required=True)
    s.add_argument("--niche", required=True); s.set_defaults(fn=cmd_seed)
    s.add_argument("--area-label", default="", help="override the display label, e.g. 'Forsyth-County'")
    s.add_argument("--relabel", action="store_true", help="re-apply area_label/captured_by to existing records")

    c = sub.add_parser("check"); c.add_argument("--feed", required=True)
    c.add_argument("--area", required=True); c.set_defaults(fn=cmd_check)

    m = sub.add_parser("mark"); m.add_argument("--name", required=True); m.add_argument("--phone", default="")
    m.add_argument("--status", required=True, choices=["qualified", "drafted", "contacted", "replied", "won", "lost", "disqualified", "excluded"])
    m.add_argument("--sender", default=""); m.add_argument("--channel", default="email")
    m.add_argument("--arm", default=""); m.add_argument("--date", default=""); m.add_argument("--notes", default="")
    m.add_argument("--area", default=""); m.add_argument("--niche", default="")
    m.add_argument("--create", action="store_true"); m.set_defaults(fn=cmd_mark)
    m.add_argument("--force", action="store_true", help="allow an intentional status downgrade")

    st = sub.add_parser("stats"); st.set_defaults(fn=cmd_stats)
    cap = sub.add_parser("cap"); cap.add_argument("--sender", required=True)
    cap.add_argument("--date", default=""); cap.add_argument("--limit", type=int, default=20)
    cap.set_defaults(fn=cmd_cap)

    for sp in (s, c, m, st, cap):
        sp.add_argument("--ledger", default="",
                        help="path to contacted.jsonl (default: alongside the prospect data)")

    a = p.parse_args()
    if a.selftest:
        return cmd_selftest(a)
    if not getattr(a, "fn", None):
        p.print_help()
        return 1
    if getattr(a, "ledger", ""):
        global LEDGER
        LEDGER = a.ledger
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
