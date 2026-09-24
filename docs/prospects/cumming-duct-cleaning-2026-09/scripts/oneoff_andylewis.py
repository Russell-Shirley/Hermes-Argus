"""One-off for a business whose place URL keeps returning a gated page.
Navigates via the Maps search box (different page context than a direct place URL),
clicks into the listing, then runs the same review extraction as the batch script.
Writes a record in the batch schema to qualify_results_v6.jsonl.
"""
import json, os, random, re, time

from cloakbrowser import launch

OUT = os.path.dirname(os.path.abspath(__file__))
NAME = "Andy Lewis/Hobson Heating & Air"
QUERY = "Andy Lewis Hobson Heating Air Cumming GA"
RANK = 29
RESULTS = os.path.join(OUT, "qualify_results_v6.jsonl")

AGE_DAYS = {"day": 1, "week": 7, "month": 30, "year": 365}
MIN_SECONDS = 40.0


def parse_age(text):
    t = (text or "").lower().strip()
    m = re.search(r"(\d+|a|an)\s+(day|week|month|year)s?\s+ago", t)
    if m:
        n = 1 if m.group(1) in ("a", "an") else int(m.group(1))
        return n * AGE_DAYS[m.group(2)]
    if "yesterday" in t:
        return 1
    if "hour" in t or "minute" in t:
        return 0
    return None


PROFILE_JS = """(() => {
  const m = document.querySelector('div[role="main"]');
  const o = {};
  const h1 = m && m.querySelector('h1');
  o.name = h1 ? h1.innerText.trim() : '';
  o.rating = ''; o.reviews = '';
  const f7 = m && m.querySelector('div.F7nice');
  if (f7) f7.querySelectorAll('span').forEach(s => {
    const t = (s.textContent||'').trim();
    if (!o.rating && /^\\d[.,]\\d$/.test(t)) o.rating = t.replace(',', '.');
    const al = s.getAttribute('aria-label') || '';
    const mm = al.match(/\\(?([\\d,]+)\\)?\\s+reviews?/i);
    if (!o.reviews && mm) o.reviews = mm[1].replace(/,/g, '');
  });
  const ph = m && m.querySelector('button[data-item-id^="phone"]');
  o.phone = ph ? (ph.getAttribute('aria-label')||'').replace(/^.*?:\\s*/, '').trim() : '';
  o.cards = document.querySelectorAll('div[data-review-id]').length;
  return o;
})()"""

REVIEWS_JS = """(() => {
  const out = [];
  document.querySelectorAll('div[data-review-id]').forEach(c => {
    const t = (c.innerText || '').replace(/\\s+/g, ' ').trim();
    if (t.length < 15) return;
    const dm = t.match(/(\\d+\\s+(?:day|week|month|year)s?\\s+ago|a\\s+(?:day|week|month|year)\\s+ago|yesterday)/i);
    let stars = '';
    const sl = c.querySelector('[aria-label*="star" i]');
    if (sl) { const m2 = (sl.getAttribute('aria-label')||'').match(/(\\d)\\s*star/i); if (m2) stars = m2[1]; }
    const ri = t.search(/Response from the owner/i);
    out.push({text: t.slice(0, 420), date_text: dm ? dm[1] : '', stars: stars,
              owner_response: ri >= 0, response_excerpt: ri >= 0 ? t.slice(ri, ri + 200) : ''});
  });
  const seen = new Set(); const uniq = [];
  for (const r of out) { const k = r.text.slice(0, 70); if (seen.has(k)) continue; seen.add(k); uniq.push(r); }
  return uniq;
})()"""

t0 = time.time()
browser = launch(headless=True, humanize=False)
ctx = browser.new_context(viewport={"width": 1440, "height": 1100})
page = ctx.new_page()
rec = {"rank": RANK, "name": NAME, "via": "maps-search-box"}

page.goto("https://www.google.com/maps?hl=en", timeout=90000)
page.wait_for_timeout(7000)
box = page.query_selector('input#searchboxinput, input[name="q"]')
print("search box:", bool(box))
box.click()
page.keyboard.type(QUERY, delay=45)
page.wait_for_timeout(800)
page.keyboard.press("Enter")
page.wait_for_timeout(15000)
page.screenshot(path=os.path.join(OUT, "andylewis_feed.png"))

link = page.query_selector('div[role="feed"] a.hfpxzc')
print("feed result:", bool(link), link.get_attribute("aria-label") if link else "")
if link:
    link.click()
    page.wait_for_timeout(13000)
page.screenshot(path=os.path.join(OUT, "andylewis_place.png"))

# dismiss any sign-in modal
for _ in range(3):
    hit = page.evaluate("""(() => {
      const d = [...document.querySelectorAll('button,[role="button"],a,span[role="button"]')]
        .find(x => /^\\s*(Dismiss|Not now|No thanks)\\s*$/i.test((x.innerText||'').trim()));
      if (d) { d.click(); return true; } return false; })()""")
    if not hit:
        break
    page.wait_for_timeout(2200)

rec.update(page.evaluate(PROFILE_JS))
print("profile:", {k: rec[k] for k in ("name", "rating", "reviews", "phone", "cards")})

# expand to the full review list (Overview pane first)
n = rec.get("cards") or 0
for _ in range(3):
    if n >= 10:
        break
    page.evaluate("""(() => {
      const b = [...document.querySelectorAll('div[role="main"] button, div[role="main"] [role="button"], div[role="main"] a')]
        .find(x => /more reviews/i.test((x.innerText||'') + ' ' + (x.getAttribute('aria-label')||'')));
      if (b) { b.scrollIntoView({block:'center'}); b.click(); } })()""")
    page.wait_for_timeout(6000)
    n = page.evaluate("document.querySelectorAll('div[data-review-id]').length") or 0
print("cards after expand:", n)
page.screenshot(path=os.path.join(OUT, "andylewis_reviews.png"))

for _ in range(8):
    page.evaluate("""(() => {[...document.querySelectorAll('div')].filter(d => d.scrollHeight > d.clientHeight + 120).forEach(d => d.scrollTop = d.scrollHeight);})()""")
    page.wait_for_timeout(2300)
print("cards after scroll:", page.evaluate("document.querySelectorAll('div[data-review-id]').length"))

revs = page.evaluate(REVIEWS_JS)
for rv in revs:
    rv["age_days"] = parse_age(rv["date_text"])
rec["reviews_sample"] = revs
rec["sample_size"] = len(revs)
ages = [r["age_days"] for r in revs if r["age_days"] is not None]
rec["newest_review_days"] = min(ages) if ages else None
rec["reviews_last_180d"] = sum(1 for x in ages if x <= 180)
rec["reviews_last_365d"] = sum(1 for x in ages if x <= 365)
rec["oldest_in_sample_days"] = max(ages) if ages else None
recent = [r for r in revs if r["age_days"] is not None and r["age_days"] <= 365]
pos = [r for r in recent if r["stars"] in ("4", "5") or r["stars"] == ""]
rec["recent_n"] = len(recent)
rec["recent_positive_n"] = len(pos)
rec["owner_responses_recent"] = sum(1 for r in pos if r["owner_response"])
rec["response_rate_recent"] = round(100 * rec["owner_responses_recent"] / len(pos)) if pos else None
rec["status"] = "OK" if revs else "GATED"
elapsed = time.time() - t0
if elapsed < MIN_SECONDS:
    time.sleep(MIN_SECONDS - elapsed + random.uniform(0.5, 3))
rec["seconds_spent"] = round(time.time() - t0, 1)
browser.close()

with open(RESULTS, "a", encoding="utf-8") as f:
    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
print(f"\n{rec['status']} | {rec.get('name')} {rec.get('rating')}({rec.get('reviews')}) "
      f"sample={rec['sample_size']} newest={rec.get('newest_review_days')}d "
      f"owner={rec.get('owner_responses_recent')}/{rec.get('recent_positive_n')} ({rec.get('response_rate_recent')}%) "
      f"{rec['seconds_spent']}s")
for rv in revs[:6]:
    print(f"   {rv['stars']}★ {rv['date_text']:<14} owner={rv['owner_response']} | {rv['text'][:80]}")
