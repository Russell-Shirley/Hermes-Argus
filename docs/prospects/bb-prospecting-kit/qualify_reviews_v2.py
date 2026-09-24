"""QUALIFIER v2 — review recency + owner-response behavior for mid-list businesses.

Fixes over v1:
  * FRESH BROWSER CONTEXT per business (Google gates a warmed session with "limited view")
  * GATE DETECTION: a page with no review cards on a business that has >=30 reviews is
    recorded as status=GATED (with one retry) — never as "0 owner responses"
  * Sorts reviews by NEWEST and scrolls the review container, so the sample is the actual
    recent tail of the review stream
  * Owner responses counted over RECENT POSITIVE (4-5 star) reviews only
  * Hard floor of >=15s per business (user rule), logged as seconds_spent

Usage: python qualify_reviews_v2.py <min_rank> <max_rank> [--force]
Writes qualify_results_v3.jsonl (resumable). Deep-sample mode: scrolls to ~100 reviews.
"""
import json, os, random, re, sys, time

from cloakbrowser import launch

OUT = os.path.dirname(os.path.abspath(__file__))
# The run's data dir. Defaults to <run>/data when this toolkit is copied into
# <run>/scripts/; set RUN_DATA to run it IN PLACE against any run folder.
DATA = os.environ.get("RUN_DATA") or os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "data")
SRC = os.path.join(DATA, "ranked-feed.json")
RESULTS = os.path.join(DATA, "qualify_results.jsonl")   # appended + resumed, never versioned

MIN_RATING = 4.5
MIN_REVIEWS = 30
MIN_SECONDS_PER_BUSINESS = 40.0   # USER RULE (raised from 15s): never faster than 40s per business
SCROLL_ROUNDS = 8
MAX_REVIEWS = 120
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
  const ad = m && m.querySelector('button[data-item-id="address"]');
  o.address = ad ? (ad.getAttribute('aria-label')||'').replace(/^.*?:\\s*/, '').trim() : '';
  const wb = m && m.querySelector('a[data-item-id="authority"]');
  o.website = wb ? wb.href : '';
  o.pane_text = m ? (m.innerText||'').replace(/\\s+/g,' ').slice(0, 400) : '';
  o.limited_view = /limited view/i.test(o.pane_text) || /limited view/i.test(document.body.innerText||'');
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
    if (!stars) { const m3 = c.innerHTML.match(/aria-label="(\\d)\\s*star/i); if (m3) stars = m3[1]; }
    const ri = t.search(/Response from the owner/i);
    out.push({
      text: t.slice(0, 420),
      date_text: dm ? dm[1] : '',
      stars: stars,
      owner_response: ri >= 0,
      response_excerpt: ri >= 0 ? t.slice(ri, ri + 200) : ''
    });
  });
  const seen = new Set(); const uniq = [];
  for (const r of out) { const k = r.text.slice(0, 70); if (seen.has(k)) continue; seen.add(k); uniq.push(r); }
  return uniq;
})()"""


def load_targets(lo, hi):
    d = json.load(open(SRC, encoding="utf-8"))
    out, seen = [], set()
    for r in d["maps_full"]:
        rk = r.get("local_rank")
        if not rk or not (lo <= rk <= hi):
            continue
        if r["name"] in seen:          # feed carries a duplicate listing (All Pro x2)
            continue
        if float(r["rating"] or 0) >= MIN_RATING and int(r["reviews"] or 0) >= MIN_REVIEWS:
            seen.add(r["name"])
            out.append(r)
    return out


def dismiss_modals(page):
    """Google overlays a 'Sign-in to get the best of Google Maps' modal on repeat visits.
    The listing renders behind it but extraction returns nothing until it's dismissed."""
    hits = 0
    for _ in range(3):
        clicked = page.evaluate("""(() => {
          const d = [...document.querySelectorAll('button, [role="button"], a, span[role="button"], div[role="button"]')]
            .find(x => /^\\s*(Dismiss|Not now|No thanks)\\s*$/i.test((x.innerText||'').trim()));
          if (d) { d.click(); return true; }
          return false;
        })()""")
        if not clicked:
            break
        hits += 1
        page.wait_for_timeout(2200)
    return hits


def _click_more_reviews(page):
    return page.evaluate("""(() => {
      const b = [...document.querySelectorAll('div[role="main"] button, div[role="main"] [role="button"], div[role="main"] span[role="button"], div[role="main"] a')]
        .find(x => /more reviews/i.test((x.innerText||'') + ' ' + (x.getAttribute('aria-label')||'')));
      if (!b) return false;
      b.scrollIntoView({block:'center'});
      b.click();
      return true;
    })()""")


def open_reviews(page):
    """Reach the full review list.

    ORDER MATTERS: the 'More reviews (N)' control lives on the *Overview* pane and
    disappears once the Reviews tab is selected — clicking the tab first caps the
    sample at the 5-review preview. Expand first, fall back to the tab.
    """
    n = page.evaluate("document.querySelectorAll('div[data-review-id]').length") or 0
    for _ in range(3):
        if n >= 10:
            return n
        _click_more_reviews(page)
        page.wait_for_timeout(6000)
        n = page.evaluate("document.querySelectorAll('div[data-review-id]').length") or 0
    if n < 10:   # fallback: tab first, then expand again
        page.evaluate("""(() => {
          const t = [...document.querySelectorAll('div[role="main"] button')]
            .find(b => /^Reviews$/i.test((b.innerText||'').trim()) || /Reviews of/i.test(b.getAttribute('aria-label')||''));
          if (t) { t.scrollIntoView({block:'center'}); t.click(); }
        })()""")
        page.wait_for_timeout(4000)
        for _ in range(2):
            n = page.evaluate("document.querySelectorAll('div[data-review-id]').length") or 0
            if n >= 10:
                break
            _click_more_reviews(page)
            page.wait_for_timeout(6000)
    return page.evaluate("document.querySelectorAll('div[data-review-id]').length") or 0


def sort_newest(page):
    """Sort the review list by Newest (JS clicks). Returns True on success."""
    for _ in range(2):
        ok = page.evaluate("""(() => {
          const s = [...document.querySelectorAll('button, [role="button"]')]
            .find(x => /^\\s*(Sort|Most relevant)\\s*$/i.test(((x.innerText||'') + (x.getAttribute('aria-label')||'')).trim()));
          if (!s) return false; s.scrollIntoView({block:'center'}); s.click(); return true;
        })()""")
        if not ok:
            return False
        page.wait_for_timeout(2500)
        done = page.evaluate("""(() => {
          const o = [...document.querySelectorAll('[role="menuitemradio"], [role="menuitem"], [role="option"], div[data-index]')]
            .find(x => /newest/i.test(x.innerText||''));
          if (!o) return false; o.click(); return true;
        })()""")
        page.wait_for_timeout(4500)
        if done:
            return True
    return False


def scroll_reviews(page):
    """Load the deep review list. Scrolling EVERY scrollable div is what works:
    each round appends ~20 more review cards (20 -> 100 observed)."""
    last = page.evaluate("document.querySelectorAll('div[data-review-id]').length") or 0
    for _ in range(SCROLL_ROUNDS):
        page.evaluate("""(() => {
          const all = [...document.querySelectorAll('div')].filter(d => d.scrollHeight > d.clientHeight + 120);
          all.forEach(d => { d.scrollTop = d.scrollHeight; });
        })()""")
        page.wait_for_timeout(2300)
        n = page.evaluate("document.querySelectorAll('div[data-review-id]').length") or 0
        if n <= last and n >= MAX_REVIEWS:
            break
        last = n
    return last


def scrape_one(browser, t):
    ctx = browser.new_context(viewport={"width": 1440, "height": 1100})
    page = ctx.new_page()
    rec = {"rank": t["local_rank"], "name": t["name"], "phone": t["phone"], "href": t["href"]}
    try:
        page.goto(t["href"], timeout=90000)
        page.wait_for_timeout(13000)
        rec["modals_dismissed"] = dismiss_modals(page)
        page.wait_for_timeout(1500)
        rec.update(page.evaluate(PROFILE_JS))
        cards = open_reviews(page)
        if cards:
            dismiss_modals(page)
            rec["sorted_newest"] = sort_newest(page)
            scroll_reviews(page)
            revs = page.evaluate(REVIEWS_JS)
        else:
            revs = []
        for rv in revs:
            rv["age_days"] = parse_age(rv["date_text"])
        rec["reviews_sample"] = revs
        rec["sample_size"] = len(revs)
        ages = [r["age_days"] for r in revs if r["age_days"] is not None]
        rec["newest_review_days"] = min(ages) if ages else None
        rec["reviews_last_180d"] = sum(1 for a in ages if a <= 180)
        rec["reviews_last_365d"] = sum(1 for a in ages if a <= 365)
        rec["oldest_in_sample_days"] = max(ages) if ages else None
        recent = [r for r in revs if r["age_days"] is not None and r["age_days"] <= 365]
        pos = [r for r in recent if r["stars"] in ("4", "5") or r["stars"] == ""]
        rec["recent_n"] = len(recent)
        rec["recent_positive_n"] = len(pos)
        rec["owner_responses_recent"] = sum(1 for r in pos if r["owner_response"])
        rec["response_rate_recent"] = (round(100 * rec["owner_responses_recent"] / len(pos)) if pos else None)
        # gate: no cards at all on a business with a real review count
        if not revs and int(rec.get("reviews") or t.get("reviews") or 0) >= MIN_REVIEWS:
            rec["status"] = "GATED"
        else:
            rec["status"] = "OK"
    except Exception as e:
        rec["status"] = "ERROR"
        rec["error"] = f"{type(e).__name__}: {e}"
    finally:
        try:
            ctx.close()
        except Exception:
            pass
    return rec


def main():
    global MIN_REVIEWS
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    force = "--force" in sys.argv
    for a in sys.argv[1:]:
        if a.startswith("--min-reviews="):
            MIN_REVIEWS = int(a.split("=")[1])
    lo, hi = int(args[0]), int(args[1])
    print(f"rank range {lo}-{hi} | gate: rating>={MIN_RATING}, reviews>={MIN_REVIEWS}")
    done = set()
    if os.path.exists(RESULTS) and not force:
        for line in open(RESULTS, encoding="utf-8"):
            try:
                j = json.loads(line)
                if j.get("status") != "GATED":   # gated rows are retried
                    done.add(j["name"])
            except Exception:
                pass
    targets = [t for t in load_targets(lo, hi) if t["name"] not in done]
    print(f"to do: {len(targets)}")
    if not targets:
        return
    browser = launch(headless=True, humanize=False)
    for t in targets:
        t0 = time.time()
        rec = scrape_one(browser, t)
        if rec.get("status") == "GATED":
            print(f"   GATED -> cooling off 70s, retrying {rec['name']}")
            time.sleep(70)
            rec2 = scrape_one(browser, t)
            if rec2.get("status") == "OK":
                rec = rec2
        elapsed = time.time() - t0
        if elapsed < MIN_SECONDS_PER_BUSINESS:
            time.sleep(MIN_SECONDS_PER_BUSINESS - elapsed + random.uniform(0.5, 3.0))
        rec["seconds_spent"] = round(time.time() - t0, 1)
        with open(RESULTS, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(f"#{rec['rank']:>2} {rec['name'][:34]:<34} {rec['status']:<6} rating={rec.get('rating')} "
              f"revs={rec.get('reviews')} sample={rec.get('sample_size')} newest={rec.get('newest_review_days')}d "
              f"last180={rec.get('reviews_last_180d')} owner={rec.get('owner_responses_recent')}/{rec.get('recent_positive_n')} "
              f"({rec.get('response_rate_recent')}%) {rec.get('seconds_spent')}s", flush=True)
    browser.close()
    print("saved:", RESULTS)


main()
