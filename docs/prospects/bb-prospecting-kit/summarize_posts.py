"""Summarise probe_posts_iso.py output into posts_verified.json, and print the claim-(b) table.

The probe is authoritative in ONE direction only: when it reaches the posts surface and
finds dated entries, that is proof of posting. When it finds no surface, that is absence of
evidence on a signed-out pane, which the kit explicitly warns gives FALSE NEGATIVES — so
"no posts" is recorded as `no_posts_surface_found`, never as "does not post".

Usage: python summarize_posts.py [<run data dir>]
"""
import glob
import json
import os
import re
import sys

D = sys.argv[1] if len(sys.argv) > 1 else (
    r"C:/Users/Russell/Documents/GitHub/bb-audit-kit/research/hermes/"
    r"2026-09-24-duct-cleaning-canton-ga/data")

out = []
for path in sorted(glob.glob(os.path.join(D, "logs", "posts_*.log"))):
    txt = open(path, encoding="utf-8", errors="replace").read()
    name = re.search(r"^listing:\s*(.+)$", txt, re.M)
    surfaces = re.search(r"^post/update surfaces:\s*(.+)$", txt, re.M)
    attempt = re.search(r"^posts open attempt:\s*(.+)$", txt, re.M)
    dates = re.findall(r"relative dates anywhere:\s*(\[[^\]]*\])", txt)
    listing = (name.group(1).strip() if name else "")
    sup = (surfaces.group(1) if surfaces else "").strip()
    opened = (attempt.group(1) if attempt else "").strip()
    rec = {
        "query_log": os.path.basename(path),
        "listing": listing,
        "opened_posts_surface": opened.startswith("clicked"),
        "posts_control": opened,
        "owner_surface": "By owner" in sup,
        "dated_entries_seen": (dates[-1] if dates else "[]"),
        "resolution": ("ok" if listing and listing.lower() not in ("results", "search results")
                       and not listing.startswith("http")
                       else "FAILED (did not reach a listing)"),
    }
    if rec["resolution"].startswith("FAILED"):
        rec["evidence"] = "unusable — no claim may rest on this row"
    elif rec["opened_posts_surface"] and rec["dated_entries_seen"] not in ("[]", ""):
        rec["evidence"] = "posts surface reached with dated entries — may be proof of posting"
    elif rec["opened_posts_surface"]:
        rec["evidence"] = "posts surface reached, no dated entries visible"
    else:
        rec["evidence"] = "no_posts_surface_found — pane-level absence, NOT proof of no posts"
    out.append(rec)

with open(os.path.join(D, "posts_verified.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2, ensure_ascii=False)

for r in out:
    print(f"{r['listing'][:38]:<39}{r['resolution']:<10}{r['evidence']}")
print(f"\nwrote {os.path.join(D, 'posts_verified.json')} ({len(out)} listings)")
