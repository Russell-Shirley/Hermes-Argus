"""v4: correct parse.
 - Maps ranked list: card = closest div.Nv2PK (carries 'Rating(Count)' text), dedupe by href
 - SERP local pack: count + order of businesses in the map block
"""
import csv, json, os, re, sys

from cloakbrowser import launch

OUT = os.path.dirname(os.path.abspath(__file__))
# The run's data dir. Defaults to <run>/data when this toolkit is copied into
# <run>/scripts/; set RUN_DATA to run it IN PLACE against any run folder.
DATA = os.environ.get("RUN_DATA") or os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "data")
QUERY = sys.argv[1] if len(sys.argv) > 1 else "best duct cleaning in Cumming GA"

EXTRACT = """(() => {
  const out = []; const seen = new Set();
  document.querySelectorAll('div[role="feed"] a.hfpxzc').forEach(a => {
    const name = (a.getAttribute('aria-label') || '').trim();
    const href = a.href;
    if (!name || seen.has(href)) return;
    seen.add(href);
    const card = a.closest('div.Nv2PK') || a.parentElement.parentElement;
    const txt = (card.innerText || '').replace(/\\s+/g, ' ').trim();
    let rating = '', reviews = '';
    const f7 = card.querySelector('div.F7nice');
    if (f7) {
      f7.querySelectorAll('span').forEach(s => {
        const t = (s.textContent || '').trim();
        if (!rating && /^\\d[.,]\\d$/.test(t)) rating = t.replace(',', '.');
        const al = s.getAttribute('aria-label') || '';
        const m = al.match(/\\(?([\\d,]+)\\)?\\s+reviews?/i);
        if (!reviews && m) reviews = m[1].replace(/,/g, '');
      });
    }
    const m2 = txt.match(/(\\d\\.\\d)\\s*\\((\\d[\\d,]*)\\)/);
    if (!rating && m2) rating = m2[1];
    if (!reviews && m2) reviews = m2[2].replace(/,/g, '');
    const phone = (txt.match(/\\(\\d{3}\\)\\s*\\d{3}-\\d{4}/) || [''])[0];
    const cat = (txt.match(/(?:Air duct cleaning service|HVAC contractor|Dryer vent cleaning service|Carpet cleaning service|Cleaners|Air conditioning contractor|Heating contractor|Water damage restoration service|Junk removal service|Fireplace store|Plumber|[A-Z][a-z]+(?: [a-z]+){0,3} (?:service|contractor|store|company))/i) || [''])[0];
    const addr = (txt.match(/(\\d+[^·]{5,60}?)(?= Open| Closes| Open 24| \\(\\d{3}\\)| Website| Directions|$)/) || [''])[0];
    out.push({name, rating, reviews, phone, category: cat, address: addr.trim(),
              sponsored: /sponsored/i.test(txt), href, text: txt.slice(0, 300)});
  });
  return out;
})()"""

# Card text parses reliably in Python; the JS patterns above are duct/HVAC-specific
# and misfire on other verticals — on a septic search they returned the business
# NAME as the category (its own fallback matched "Carlton Septic Service") and any
# digit-led text as the address ("5.0(10) Septic system service"). Category is the
# first thing every vertical's diagnostic reads, so it has to be right.
_HOURS = re.compile(r"\s+(?:Open 24 hours|Reopens|Open|Closed|Closes soon|Closes|Opens)\b")
_PHONE = re.compile(r"\(\d{3}\)\s*\d{3}-\d{4}")
_TAIL = re.compile(r"\s+(?:Website|Directions|Book online|Order online)\b")
_RATING = re.compile(r"^(\d\.\d)\(([\d,]+)\)\s*")


def _cut_segment(s: str) -> str:
    for pat in (_HOURS, _PHONE, _TAIL):
        s = pat.split(s)[0]
    return s.strip(" ·").strip()


def parse_card_fields(rec: dict) -> dict:
    """Derive category/address from the card's own text.

    The card repeats the business name, then ``Rating(Count)`` or ``No reviews``,
    then the category, then optional ``·``-separated address, then hours/phone.
    Text position in the card is the most reliable signal we have, and it is
    vertical-agnostic.
    """
    name = " ".join((rec.get("name") or "").split())
    body = " ".join((rec.get("text") or "").split())
    for _ in range(2):
        if name and body.startswith(name):
            body = body[len(name):].strip()
    m = _RATING.match(body)
    if m:
        rec["rating"] = rec.get("rating") or m.group(1)
        rec["reviews"] = rec.get("reviews") or m.group(2).replace(",", "")
        body = body[m.end():]
    elif body.startswith("No reviews"):
        rec["reviews"] = rec.get("reviews") or "0"
        body = body[len("No reviews"):].strip()
    segs = [s for s in body.split("·") if s.strip()]
    cat = _cut_segment(segs[0]) if segs else ""
    if cat:
        rec["category"] = cat
    # the JS address pattern accepts ANY digit-led text, so it is never trusted —
    # clear it and re-derive, leaving "" when the card genuinely lists no address
    rec["address"] = ""
    for s in segs[1:]:
        cand = _cut_segment(s)
        if cand and not re.fullmatch(r"(?i)(website|directions|book online|order online)", cand):
            rec["address"] = cand
            break
    return rec


browser = launch(headless=True, humanize=False)
page = browser.new_page(viewport={"width": 1440, "height": 1100})
res = {"query": QUERY}

page.goto("https://www.google.com/maps/search/" + QUERY.replace(" ", "+") + "/", timeout=90000)
page.wait_for_timeout(16000)
top = page.evaluate(EXTRACT)
page.screenshot(path=os.path.join(DATA, "maps_top_v4.png"))

prev, stable = -1, 0
for _ in range(16):
    page.evaluate("""(() => { const f = document.querySelector('div[role="feed"]');
        if (f) f.scrollTop = f.scrollHeight;
        const e = document.querySelector('span.HlvSq, p.fontBodyMedium'); if (e) e.scrollIntoView();
        window.scrollTo(0, document.body.scrollHeight); })()""")
    page.wait_for_timeout(2400)
    n = page.evaluate("document.querySelectorAll('div[role=feed] a.hfpxzc').length") or 0
    if n == prev:
        stable += 1
        if stable >= 2: break
    else:
        stable = 0
    prev = n
full = page.evaluate(EXTRACT)
reached_end = page.evaluate("!!document.body.innerText.match(/reached the end of the list/i)")

rank = 0
for i, r in enumerate(full, 1):
    parse_card_fields(r)
    r["feed_pos"] = i
    if r["sponsored"]:
        r["local_rank"] = None
    else:
        rank += 1
        r["local_rank"] = rank
res["maps_top"] = top[:12]
res["maps_full"] = full
res["reached_end_of_list"] = reached_end

# ---- SERP local pack ----
serp = {}
page.goto("https://www.google.com/?hl=en&gl=us", timeout=60000)
page.wait_for_timeout(5000)
box = page.query_selector('textarea[name="q"], input[name="q"]')
box.click(); page.keyboard.type(QUERY, delay=35); page.wait_for_timeout(700)
page.keyboard.press("Enter"); page.wait_for_timeout(10000)
body = page.evaluate("document.body.innerText")
serp["walled"] = bool(re.search(r"unusual traffic|not a robot", body, re.I))
pack = page.evaluate("""(() => {
  const out = []; const seen = new Set();
  // map pack entries: anchors to /maps/place/, or elements carrying data-cid
  document.querySelectorAll('a[href*="/maps/place/"]').forEach(a => {
    const nm = (a.getAttribute('aria-label') || a.innerText || '').replace(/\\s+/g,' ').trim().split('\\n')[0];
    if (!nm || nm.length > 60 || seen.has(nm)) return;
    seen.add(nm);
    let node = a, txt = '';
    for (let k=0;k<6 && node;k++){ node=node.parentElement; if(!node) break;
      const it=(node.innerText||'').replace(/\\s+/g,' ').trim();
      if (it.length>25 && it.length<700) txt=it; }
    out.push({name: nm, text: txt.slice(0,300)});
  });
  return out;
})()""")
serp["local_pack_entries"] = pack
serp["local_pack_count"] = len(pack)
# is there an actual embedded map element?
serp["has_map_element"] = page.evaluate("!!document.querySelector('div[data-attrid=\"map\"], div[jscontroller][data-maps-embed], .lu-fs, div.kno-mf')")
page.screenshot(path=os.path.join(DATA, "serp_v4.png"), full_page=True)
res["serp"] = serp
browser.close()

with open(os.path.join(DATA, "ranked-feed.json"), "w", encoding="utf-8") as f:
    json.dump(res, f, indent=2, ensure_ascii=False)

with open(os.path.join(DATA, "ranked-feed.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["rank", "name", "rating", "reviews", "phone", "category", "address", "ad", "feed_pos"])
    for r in full:
        w.writerow([r["local_rank"] or "AD", r["name"], r["rating"], r["reviews"], r["phone"],
                    r["category"], r["address"], r["sponsored"], r["feed_pos"]])

print(f"FULL={len(full)} organic={len([r for r in full if not r['sponsored']])} ads={len([r for r in full if r['sponsored']])} reached_end={reached_end}")
print("RANKED (organic):")
for r in full:
    tag = "AD " if r["sponsored"] else f"#{r['local_rank']}"
    print(f"  {tag:<4} {r['name'][:44]:<44} {r['rating']}({r['reviews']}) {r['phone']:<15} {r['category'][:28]}")
print("\nSERP walled:", serp["walled"], "| local_pack_count:", serp["local_pack_count"], "| has_map_element:", serp["has_map_element"])
for e in pack:
    print("   -", e["name"], "||", e["text"][:90])
