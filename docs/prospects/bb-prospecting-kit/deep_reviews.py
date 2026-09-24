"""Deep review pull for a shortlist of businesses: how many reviews actually carry an
owner response, and what the responses look like (templated vs personal).

Navigates via the Maps search box (more reliable than a direct place URL when gated),
expands the review list, scrolls deep, and records every retrievable review.

Usage: python deep_reviews.py "ClimateSmith Cumming GA" "Georgia Comfort Cumming GA" ...
Writes deep_reviews.json and prints per-business response coverage + reply templates.
"""
import json, os, re, sys, time

from cloakbrowser import launch

OUT = os.path.dirname(os.path.abspath(__file__))
# The run's data dir. Defaults to <run>/data when this toolkit is copied into
# <run>/scripts/; set RUN_DATA to run it IN PLACE against any run folder.
DATA = os.environ.get("RUN_DATA") or os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "data")
RESULTS = os.path.join(DATA, "deep_reviews.json")
MIN_SECONDS_PER_BUSINESS = 40.0
SCROLL_ROUNDS = 10

AGE_DAYS = {"day": 1, "week": 7, "month": 30, "year": 365}


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


# Every review card, with the owner-response block split out of the review body
REVIEWS_JS = """(() => {
  const out = [];
  document.querySelectorAll('div[data-review-id]').forEach(c => {
    const full = (c.innerText || '').replace(/\\r/g, '').trim();
    if (full.length < 15) return;
    const flat = full.replace(/\\s+/g, ' ');
    const dm = flat.match(/(\\d+\\s+(?:day|week|month|year)s?\\s+ago|a\\s+(?:day|week|month|year)\\s+ago|yesterday)/i);
    let stars = '';
    const sl = c.querySelector('[aria-label*="star" i]');
    if (sl) { const m2 = (sl.getAttribute('aria-label')||'').match(/(\\d)\\s*star/i); if (m2) stars = m2[1]; }
    const idx = flat.search(/Response from the owner/i);
    let body = flat, resp = '', resp_date = '';
    if (idx >= 0) {
      body = flat.slice(0, idx).trim();
      const tail = flat.slice(idx + 'Response from the owner'.length).trim();
      const rd = tail.match(/^((?:\\d+\\s+(?:day|week|month|year)s?\\s+ago|a\\s+(?:day|week|month|year)\\s+ago|yesterday))/i);
      if (rd) { resp_date = rd[1]; resp = tail.slice(rd[1].length).trim(); }
      else resp = tail;
    }
    out.push({text: flat.slice(0, 600), body: body.slice(0, 420), stars, date_text: dm ? dm[1] : '',
              owner_response: idx >= 0, response_text: resp.slice(0, 300), response_date: resp_date});
  });
  const seen = new Set(); const uniq = [];
  for (const r of out) { const k = r.text.slice(0, 70); if (seen.has(k)) continue; seen.add(k); uniq.push(r); }
  return uniq;
})()"""

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
  const cat = m ? (m.innerText.match(/\\n([A-Z][a-z]+(?: [a-z]+){0,3}(?:service|contractor|store|company|cleaners))/i) || [''])[0] : '';
  o.category = cat.trim();
  return o;
})()"""


def _search_box(page, query):
    box = page.query_selector('input#searchboxinput, input[name="q"]')
    box.click()
    page.keyboard.type(query, delay=45)
    page.wait_for_timeout(800)
    page.keyboard.press("Enter")
    page.wait_for_timeout(14000)


def scrape(browser, query):
    t0 = time.time()
    ctx = browser.new_context(viewport={"width": 1440, "height": 1100})
    page = ctx.new_page()
    rec = {"query": query}
    try:
        if query.startswith("http"):
            page.goto(query, timeout=90000)
            page.wait_for_timeout(14000)
            rec["via"] = "direct-url"
        else:
            page.goto("https://www.google.com/maps?hl=en", timeout=90000)
            page.wait_for_timeout(7000)
            _search_box(page, query)
        # Open the listing and VERIFY we landed on a place page (not the results list
        # whose h1 reads "Results"). Without this check the pull silently harvests the
        # 3-6 review snippets on the search page and reports them as the business.
        opened = False
        for attempt in range(3):
            link = page.query_selector('div[role="feed"] a.hfpxzc')
            if link:
                link.click()
                page.wait_for_timeout(12000)
            h1 = page.evaluate("""(() => {const m=document.querySelector("div[role='main'] h1"); return m?m.innerText.trim():''})()""")
            if h1 and not re.match(r"^(results|search results|google maps)$", h1, re.I) and len(h1) > 2:
                opened = True
                break
            page.wait_for_timeout(4000)
        rec["opened_listing"] = opened
        rec["h1"] = page.evaluate("""(() => {const m=document.querySelector("div[role='main'] h1"); return m?m.innerText.trim():''})()""")
        for _ in range(3):
            hit = page.evaluate("""(() => {
              const d = [...document.querySelectorAll('button,[role="button"],a,span[role="button"]')]
                .find(x => /^\\s*(Dismiss|Not now|No thanks)\\s*$/i.test((x.innerText||'').trim()));
              if (d) { d.click(); return true; } return false; })()""")
            if not hit:
                break
            page.wait_for_timeout(2200)
        rec.update(page.evaluate(PROFILE_JS))
        # Expand the review list. The control that opens it differs per listing, so try
        # several in turn and keep whatever actually raises the card count.
        EXPAND = [
            "(() => {const b=[...document.querySelectorAll('button,[role=\"button\"],a')].find(x=>/more reviews/i.test((x.innerText||'')+' '+(x.getAttribute('aria-label')||''))); if(!b) return 'nf'; b.scrollIntoView({block:'center'}); b.click(); return 'ok';})()",
            "(() => {const f=document.querySelector('div.F7nice'); if(!f) return 'nf'; const c=f.querySelector('span[role=\"img\"]')||f; c.scrollIntoView({block:'center'}); c.click(); return 'ok';})()",
            "(() => {const el=[...document.querySelectorAll('button,[role=\"button\"],span,a')].find(x=>/^\\s*\\(?\\d[\\d,]*\\)?\\s*reviews?\\s*$/i.test((x.innerText||'').trim())); if(!el) return 'nf'; el.scrollIntoView({block:'center'}); el.click(); return 'ok';})()",
            "(() => {const t=[...document.querySelectorAll('button[role=\"tab\"],button')].find(b=>/^Reviews$/i.test((b.innerText||'').trim())); if(!t) return 'nf'; t.scrollIntoView({block:'center'}); t.click(); return 'ok';})()",
        ]
        n = page.evaluate("document.querySelectorAll('div[data-review-id]').length") or 0
        attempts = []
        for round_i in range(3):
            if n >= 10:
                break
            for js in EXPAND:
                page.evaluate(js)
                page.wait_for_timeout(5500)
                n = page.evaluate("document.querySelectorAll('div[data-review-id]').length") or 0
                attempts.append(n)
                if n >= 10:
                    break
        rec["expand_card_counts"] = attempts
        for _ in range(SCROLL_ROUNDS):
            page.evaluate("""(() => {[...document.querySelectorAll('div')].filter(d => d.scrollHeight > d.clientHeight + 120).forEach(d => d.scrollTop = d.scrollHeight);})()""")
            page.wait_for_timeout(2300)
        revs = page.evaluate(REVIEWS_JS)
        for r in revs:
            r["age_days"] = parse_age(r["date_text"])
        rec["reviews_sampled"] = revs   # NOTE: do not reuse "reviews" — it holds the profile count
        rec["sampled"] = len(revs)
        rec["responded"] = sum(1 for r in revs if r["owner_response"])
        rec["response_coverage_pct"] = round(100 * rec["responded"] / len(revs)) if revs else None
        # reply consistency: how many distinct reply openings vs total replies
        openings = [re.sub(r"[^a-z ]", "", (r["response_text"] or "").lower())[:40].strip() for r in revs if r["owner_response"]]
        openings = [o for o in openings if o]
        rec["distinct_reply_openings"] = len(set(openings))
        rec["reply_openings"] = sorted(set(openings))[:8]
        rec["status"] = "OK" if revs else "GATED"
        page.screenshot(path=os.path.join(DATA, "deep_" + re.sub(r"[^A-Za-z0-9]+", "_", query)[:30] + ".png"))
    except Exception as e:
        rec["status"] = "ERROR"
        rec["error"] = f"{type(e).__name__}: {e}"
    finally:
        try:
            ctx.close()
        except Exception:
            pass
    elapsed = time.time() - t0
    if elapsed < MIN_SECONDS_PER_BUSINESS:
        time.sleep(MIN_SECONDS_PER_BUSINESS - elapsed)
    rec["seconds_spent"] = round(time.time() - t0, 1)
    return rec


QUERIES = sys.argv[1:] or ["ClimateSmith Cumming GA"]
out = []
browser = launch(headless=True, humanize=False)
for q in QUERIES:
    rec = scrape(browser, q)
    out.append(rec)
    print(f"\n=== {rec.get('name') or q} | {rec.get('rating')}({rec.get('reviews')}) | {rec.get('category','')} | {rec['status']}")
    print(f"    sampled={rec.get('sampled')} responded={rec.get('responded')} coverage={rec.get('response_coverage_pct')}% "
          f"distinct reply openings={rec.get('distinct_reply_openings')} ({rec.get('seconds_spent')}s)")
    print(f"    reply openings: {rec.get('reply_openings')}")
    for r in (rec.get("reviews_sampled") or [])[:12]:
        mark = "RESP" if r["owner_response"] else "----"
        print(f"      {mark} {r['stars']}★ {r['date_text']:<14} | {r['body'][:70]}")
        if r["owner_response"] and r["response_text"]:
            print(f"            reply: {r['response_text'][:110]}")
browser.close()

existing = []
if os.path.exists(RESULTS):
    existing = json.load(open(RESULTS, encoding="utf-8"))
existing.extend(out)
with open(RESULTS, "w", encoding="utf-8") as f:
    json.dump(existing, f, indent=2, ensure_ascii=False)
print("\nsaved:", RESULTS)
