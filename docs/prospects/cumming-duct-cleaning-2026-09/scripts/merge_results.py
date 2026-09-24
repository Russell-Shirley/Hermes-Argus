"""Merge every qualify run (v2/v3/v4/v5) into one record per business, best record wins:
non-GATED beats GATED, then larger review sample. Writes qualify_merged.jsonl.
"""
import json, os

OUT = os.path.dirname(os.path.abspath(__file__))
FILES = ["qualify_results_v2.jsonl", "qualify_results_v3.jsonl", "qualify_results_v4.jsonl",
         "qualify_results_v5.jsonl", "qualify_results_v6.jsonl"]

best = {}
for f in FILES:
    fp = os.path.join(OUT, f)
    if not os.path.exists(fp):
        continue
    for line in open(fp, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        key = (0 if r.get("status") == "GATED" else 1, r.get("sample_size") or 0)
        if r["name"] not in best or key > best[r["name"]][0]:
            best[r["name"]] = (key, r)

recs = sorted((v[1] for v in best.values()), key=lambda r: r.get("rank") or 99)
with open(os.path.join(OUT, "qualify_merged.jsonl"), "w", encoding="utf-8") as f:
    for r in recs:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")

print(f"merged {len(recs)} businesses from {len(FILES)} runs")
print("ranks covered:", f"{min(r.get('rank') for r in recs)}-{max(r.get('rank') for r in recs)}")
gated = [r["name"] for r in recs if r.get("status") == "GATED"]
print("still gated:", gated or "none")
deep = [f"#{r['rank']} {r['name']} ({r['sample_size']})" for r in recs if (r.get("sample_size") or 0) > 10]
print("deep samples captured:", deep or "none")
