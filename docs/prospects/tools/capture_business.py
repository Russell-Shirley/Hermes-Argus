"""Full diagnostic capture for one business — the 14-row matrix.

Usage: python capture_business.py "Business Name City GA" [--slug=name]
Writes captures/<slug>.json

Every field is wrapped: a field that cannot be captured records WHY, so a gate is never
mistaken for a zero. Metrics derived from relative dates carry a `quantised: true` flag —
Google shows "a month ago", not dates, so lag figures are coarse by construction.
"""
import json, os, re, statistics, sys, time, unicodedata
from datetime import datetime, timezone

from cloakbrowser import launch

OUT = os.path.dirname(os.path.abspath(__file__))
# The run's data dir. Defaults to <run>/data when this toolkit is copied into
# <run>/scripts/; set RUN_DATA to run it IN PLACE against any run folder.
DATA = os.environ.get("RUN_DATA") or os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "data")
CAP = os.path.join(DATA, "captures")
os.makedirs(CAP, exist_ok=True)
MIN_SECONDS = 40.0
AGE_DAYS = {"day": 1, "week": 7, "month": 30, "year": 365}


def slugify(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:60]


def parse_age(text):
    t = (text or "").lower().strip()
    m = re.search(r"(\d+|a|an)\s+(day|week|month|year)s?\s+ago", t)
    if m:
        n = 1 if m.group(1) in ("a", "an") else int(m.group(1))
        return n * AGE_DAYS[m.group(2)]
    if "yesterday" in t:
        return 1
    if "hour" in t or "minute" in t or "just now" in t:
        return 0
    return None


# ---------- extraction ----------

HEADER_JS = r"""(() => {
  const m = document.querySelector('div[role="main"]');
  const o = {};
  o.name = (m && m.querySelector('h1')) ? m.querySelector('h1').innerText.trim() : '';
  o.rating = ''; o.review_count = '';
  const f7 = m && m.querySelector('div.F7nice');
  if (f7) f7.querySelectorAll('span').forEach(s => {
    const t = (s.textContent || '').trim();
    if (!o.rating && /^\d[.,]\d$/.test(t)) o.rating = t.replace(',', '.');
    const al = s.getAttribute('aria-label') || '';
    const mm = al.match(/\(?([\d,]+)\)?\s+reviews?/i);
    if (o.review_count === '' && mm) o.review_count = mm[1].replace(/,/g, '');
  });
  const g = sel => { const e = m && m.querySelector(sel);
    return e ? (e.getAttribute('aria-label') || e.innerText || '').replace(/^.*?:\s*/, '').trim() : ''; };
  o.address = g('button[data-item-id="address"]');
  o.phone = g('button[data-item-id^="phone"]');
  const w = m && m.querySelector('a[data-item-id="authority"]');
  o.website = w ? w.href : '';
  const catEl = m && m.querySelector('div.DkEaL, button.DkEaL, span.DkEaL');
  let cat = catEl ? catEl.innerText.trim() : '';
  if (!cat) {
    const cm = m ? m.innerText.match(/\n([A-Z][a-z]+(?: [a-z]+){0,3}(?:service|contractor|store|company|cleaners|installation))/) : null;
    cat = cm ? cm[1].trim() : '';
  }
  o.category_primary = cat;
  const sm = m ? m.innerText.match(/(Serves [^\n]{3,60})/) : null;
  o.service_area = sm ? sm[1].trim() : '';
  const phEl = m && m.querySelector('button[aria-label*="hoto" i]');
  o.photo_control_text = phEl ? (phEl.getAttribute('aria-label') || phEl.innerText || '').trim().slice(0, 60) : '';
  o.pane_len = m ? m.innerText.length : 0;
  return o;
})()"""


REVIEWS_JS = r"""(() => {
  const out = [];
  document.querySelectorAll('div[data-review-id]').forEach(c => {
    const flat = (c.innerText || '').replace(/\s+/g, ' ').trim();
    if (flat.length < 12) return;
    const dm = flat.match(/(\d+\s+(?:day|week|month|year)s?\s+ago|a\s+(?:day|week|month|year)\s+ago|yesterday)/i);
    let stars = '';
    const sl = c.querySelector('[aria-label*="star" i]');
    if (sl) { const m2 = (sl.getAttribute('aria-label') || '').match(/(\d)\s*star/i); if (m2) stars = m2[1]; }
    const idx = flat.search(/Response from the owner/i);
    let body = flat, resp = '', resp_date = '';
    if (idx >= 0) {
      body = flat.slice(0, idx).trim();
      const t2 = flat.slice(idx + 'Response from the owner'.length).trim();
      const rd = t2.match(/^(\d+\s+(?:day|week|month|year)s?\s+ago|a\s+(?:day|week|month|year)\s+ago|yesterday)/i);
      if (rd) { resp_date = rd[1]; resp = t2.slice(rd[1].length).trim(); } else { resp = t2; }
    }
    const nm = body.match(/^([^\d]{2,60}?)\s+(?:Local Guide|\d)/);
    out.push({ raw: flat.slice(0, 500), body: body.slice(0, 400), stars,
      date_text: dm ? dm[1] : '', reviewer: nm ? nm[1].trim() : '',
      has_response: idx >= 0, response_text: resp.slice(0, 300), response_date: resp_date });
  });
  const seen = new Set(); const uniq = [];
  for (const r of out) { const k = r.raw.slice(0, 70); if (seen.has(k)) continue; seen.add(k); uniq.push(r); }
  return uniq;
})()"""


POSTS_JS = r"""(() => {
  const m = document.querySelector('div[role="main"]');
  const txt = (m ? m.innerText : '').replace(/\s+/g, ' ');
  const absDates = (txt.match(/[A-Z][a-z]{2} \d{1,2}, \d{4}/g) || []).slice(0, 12);
  const idx = txt.search(/Latest Posts|See local posts/i);
  return {
    has_posts_surface: /See local posts|Latest Posts/i.test(txt) || absDates.length > 0,
    post_dated_entries: absDates,
    latest_posts_text: idx >= 0 ? txt.slice(idx, idx + 900) : ''
  };
})()"""


ABOUT_JS = r"""(() => {
  const m = document.querySelector('div[role="main"]');
  const t = m ? m.innerText.replace(/\s+/g, ' ') : '';
  const idx = t.search(/\b(About|Details|Services|Accessibility)\b/);
  return {
    about_text: idx >= 0 ? t.slice(idx, idx + 900) : '',
    signin_wall: /Sign in/i.test(t),
    secondary_category_hint: (t.match(/([A-Z][a-z]+(?: [a-z]+){0,3}(?:service|contractor|store|company|cleaners)) [·,] ([A-Z][a-z]+(?: [a-z]+){0,3}(?:service|contractor|store|company|cleaners))/) || [])[0] || ''
  };
})()"""



def dismiss(page):
    for _ in range(3):
        hit = page.evaluate("""(() => { const d=[...document.querySelectorAll('button,[role="button"],a')]
          .find(x => /^\\s*(Dismiss|Not now)\\s*$/i.test((x.innerText||'').trim())); if(d){d.click();return true;} return false;})()""")
        if not hit:
            return
        page.wait_for_timeout(2000)


def expand_and_scroll(page, rec):
    EXPAND = [
        "(() => {const b=[...document.querySelectorAll('button,[role=\"button\"],a')].find(x=>/more reviews/i.test((x.innerText||'')+' '+(x.getAttribute('aria-label')||''))); if(!b) return 'nf'; b.scrollIntoView({block:'center'}); b.click(); return 'ok';})()",
        "(() => {const f=document.querySelector('div.F7nice'); if(!f) return 'nf'; const c=f.querySelector('span[role=\"img\"]')||f; c.scrollIntoView({block:'center'}); c.click(); return 'ok';})()",
        "(() => {const t=[...document.querySelectorAll('button[role=\"tab\"],button')].find(b=>/^Reviews$/i.test((b.innerText||'').trim())); if(!t) return 'nf'; t.scrollIntoView({block:'center'}); t.click(); return 'ok';})()",
    ]
    n = page.evaluate("document.querySelectorAll('div[data-review-id]').length") or 0
    counts = []
    for _ in range(5):
        if n >= 10:
            break
        for js in EXPAND:
            page.evaluate(js)
            page.wait_for_timeout(5500)
            n = page.evaluate("document.querySelectorAll('div[data-review-id]').length") or 0
            counts.append(n)
            if n >= 10:
                break
    rec["expand_card_counts"] = counts
    for _ in range(8):
        page.evaluate("""(() => {[...document.querySelectorAll('div')].filter(d => d.scrollHeight > d.clientHeight + 120).forEach(d => d.scrollTop = d.scrollHeight);})()""")
        page.wait_for_timeout(2300)
    return page.evaluate("document.querySelectorAll('div[data-review-id]').length") or 0


SERVICE_WORDS = re.compile(r"duct|vent|carpet|tile|clean|hvac|furnace|system|repair|install|"
                           r"technician|tech\b|maintenance|dryer|job|work|service", re.I)
BARE = re.compile(r"(?i)^thank you[,.!]?\s*[A-Za-z]*[!.\s]*$")


def derive(rec):
    revs = rec.get("reviews", [])
    for r in revs:
        r["age_days"] = parse_age(r["date_text"])
        r["response_age_days"] = parse_age(r["response_date"]) if r["response_date"] else None
        if r["age_days"] is not None and r["response_age_days"] is not None:
            # both are relative: lag = review age - response age, quantised to day/week/month/year
            r["lag_days_approx"] = max(0, r["age_days"] - r["response_age_days"])
        stars = r.get("stars")
        r["mentions_service"] = bool(SERVICE_WORDS.search(r["response_text"])) if r["has_response"] else None
        first = (r.get("reviewer") or "").split(" ")[0].lower()
        r["mentions_reviewer_name"] = bool(first and len(first) > 2 and first in (r["response_text"] or "").lower()) if r["has_response"] else None

    dated = sorted([r for r in revs if r["age_days"] is not None], key=lambda r: r["age_days"])
    m = {}
    m["pulled"] = len(revs)
    m["unique_dated"] = len(dated)
    # A 5-card pane pull is NOT a population. Metrics that depend on the sample being
    # representative are withheld below a threshold so a thin pull can't masquerade as a finding.
    m["sample_sufficient"] = len(revs) >= 20
    m["sample_note"] = ("" if len(revs) >= 20 else
                        f"THIN SAMPLE ({len(revs)} reviews) — trend/velocity/substance withheld; "
                        "expansion failed, re-run before quoting any of these numbers")
    m["lifetime_coverage_pct"] = round(100 * sum(1 for r in revs if r["has_response"]) / len(revs)) if revs else None

    # 1. recent coverage
    new10 = dated[:10]
    m["recent10_answered"] = sum(1 for r in new10 if r["has_response"])
    m["recent10_total"] = len(new10)
    m["recent10_coverage_pct"] = round(100 * m["recent10_answered"] / len(new10)) if new10 else None
    last90 = [r for r in dated if r["age_days"] <= 90]
    m["last90_answered"] = sum(1 for r in last90 if r["has_response"])
    m["last90_total"] = len(last90)

    # 3. trend: recent 2y vs older
    recent_c = [r for r in revs if r["age_days"] is not None and r["age_days"] <= 730]
    older_c = [r for r in revs if r["age_days"] is not None and r["age_days"] > 730]
    m["trend_recent_2y_pct"] = round(100 * sum(1 for r in recent_c if r["has_response"]) / len(recent_c)) if recent_c else None
    m["trend_older_pct"] = round(100 * sum(1 for r in older_c if r["has_response"]) / len(older_c)) if older_c else None
    m["trend_verdict"] = (None if not m["sample_sufficient"] else
                          "improving" if (m["trend_recent_2y_pct"] or 0) > (m["trend_older_pct"] or 0) + 15 else
                          "deteriorating" if (m["trend_older_pct"] or 0) > (m["trend_recent_2y_pct"] or 0) + 15 else "flat")

    # 4. response speed (approximate)
    lags = [r["lag_days_approx"] for r in revs if r.get("lag_days_approx") is not None]
    lags.sort()
    m["lag_median_days_approx"] = statistics.median(lags) if lags else None
    m["lag_sample"] = len(lags)
    m["lag_quantised"] = True

    # 5. substance
    reps = [r for r in revs if r["has_response"] and r["response_text"]]
    m["replies"] = len(reps)
    if reps:
        lens = sorted(len(r["response_text"]) for r in reps)
        m["reply_len_median"] = statistics.median(lens)
        m["bare_template_pct"] = round(100 * sum(1 for r in reps if BARE.match(r["response_text"])) / len(reps))
        m["reply_mentions_service_pct"] = round(100 * sum(1 for r in reps if r["mentions_service"]) / len(reps))
        m["reply_mentions_reviewer_name_pct"] = round(100 * sum(1 for r in reps if r["mentions_reviewer_name"]) / len(reps))

    # 6. critical reviews
    crit = [r for r in revs if r.get("stars") in ("1", "2", "3")]
    m["critical_total"] = len(crit)
    m["critical_answered"] = sum(1 for r in crit if r["has_response"])
    cl = [r["lag_days_approx"] for r in crit if r.get("lag_days_approx") is not None]
    m["critical_lag_median_days_approx"] = statistics.median(cl) if cl else None

    # 7. velocity (biased by sample order — most-relevant, not chronological)
    yr = [r for r in dated if r["age_days"] <= 365]
    m["reviews_last_12mo_in_sample"] = len(yr)
    m["velocity_per_month_in_sample"] = round(len(yr) / 12, 2)
    m["velocity_bias"] = "sample is relevance-ordered, not chronological — treat as indicative"
    if not m["sample_sufficient"]:
        m["velocity_per_month_in_sample"] = None

    # 8. freshness
    m["latest_review_days"] = dated[0]["age_days"] if dated else None
    rec["metrics"] = m
    return rec


def main():
    query = sys.argv[1]
    area_label = next((a.split("=", 1)[1] for a in sys.argv[2:] if a.startswith("--area-label=")), "")
    slug = None
    for a in sys.argv[2:]:
        if a.startswith("--slug="):
            slug = a.split("=", 1)[1]
    slug = slug or slugify(query)
    t0 = time.time()
    rec = {"query": query, "captured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "area_label": area_label, "gaps": {}}

    browser = launch(headless=True, humanize=False)
    ctx = browser.new_context(viewport={"width": 1440, "height": 1100})
    page = ctx.new_page()
    try:
        page.goto("https://www.google.com/maps?hl=en", timeout=90000)
        page.wait_for_timeout(7000)
        box = page.query_selector('input#searchboxinput, input[name="q"]')
        box.click(); page.keyboard.type(query, delay=45); page.wait_for_timeout(800)
        page.keyboard.press("Enter"); page.wait_for_timeout(14000)

        opened = False
        for _ in range(3):
            link = page.query_selector('div[role="feed"] a.hfpxzc')
            if link:
                link.click(); page.wait_for_timeout(12000)
            h1 = page.evaluate("""(() => {const m=document.querySelector("div[role='main'] h1"); return m?m.innerText.trim():''})()""")
            if h1 and h1.lower() not in ("results", "search results", "google maps") and len(h1) > 2:
                opened = True
                break
            page.wait_for_timeout(3500)
        rec["opened_listing"] = opened
        dismiss(page)
        rec.update(page.evaluate(HEADER_JS))
        # which search captured this business — traceable on every record
        rec["captured_by"] = f"{area_label} - {rec.get('name') or query}".strip(" -")

        # posts surface (row 9) — the section renders late, so sample early AND again after
        # the review work; a single early read produced a FALSE NEGATIVE on a business that
        # posts weekly, which is the worst direction to be wrong in.
        rec["posts_early"] = page.evaluate(POSTS_JS)

        # about / categories / services probe (rows 10-12)
        rec["about"] = page.evaluate(ABOUT_JS)

        # reviews (rows 1-8, 13)
        cards = expand_and_scroll(page, rec)
        # Expansion is intermittent (throttle-dependent). If we got a preview-sized pull on a
        # business that has plenty of reviews, pause and re-attempt before accepting it.
        declared = int(rec.get("review_count") or 0)
        if cards < 20 and declared > 30:
            page.wait_for_timeout(30000)
            dismiss(page)
            cards = expand_and_scroll(page, rec)
            rec["retry_used"] = True
        rec["cards_seen"] = cards
        rec["posts_late"] = page.evaluate(POSTS_JS)
        early, late = rec.get("posts_early", {}), rec.get("posts_late", {})
        rec["posts"] = {
            "has_posts_surface": bool(early.get("has_posts_surface") or late.get("has_posts_surface")),
            "post_dated_entries": sorted(set((early.get("post_dated_entries") or []) + (late.get("post_dated_entries") or []))),
            "detected_early": bool(early.get("has_posts_surface")),
            "detected_late": bool(late.get("has_posts_surface")),
            "latest_posts_text": (late.get("latest_posts_text") or early.get("latest_posts_text") or "")[:600],
        }
        revs = page.evaluate(REVIEWS_JS)
        rec["reviews"] = revs
        rec["status"] = "OK" if revs else "GATED"
        page.screenshot(path=os.path.join(CAP, slug + ".png"))

        # gaps: explicit, so a gate is never read as a zero
        if not revs:
            rec["gaps"]["reviews"] = "GATED — no review cards rendered (sign-in modal or throttle)"
        if not rec.get("category_primary"):
            rec["gaps"]["category_secondary"] = "not parsed from main pane"
        if not rec["about"].get("secondary_category_hint"):
            rec["gaps"]["secondary_category"] = "About/Details service area is sign-in gated on Maps"
        if not rec["about"].get("about_text"):
            rec["gaps"]["services_list"] = "About/Details sign-in gated — needs website pass"
        # absence of a posts surface IS the finding — never overwrite it with a default
        rec["gaps"]["photos_owner_cadence"] = "photo upload recency lives in the Photos tab (sign-in gated)"
        rec["gaps"]["service_area"] = ("parsed from pane text" if rec.get("service_area") else "not shown for this listing")
        rec["gaps"]["competitive_context"] = "run capture_business.py for each competitor"
        rec["gaps"]["services_vs_website"] = "needs a website pass — not available from the Maps pane"
        derive(rec)
    except Exception as e:
        rec["status"] = "ERROR"
        rec["error"] = f"{type(e).__name__}: {e}"
    finally:
        try:
            ctx.close()
        except Exception:
            pass

    el = time.time() - t0
    if el < MIN_SECONDS:
        time.sleep(MIN_SECONDS - el)
    rec["seconds_spent"] = round(time.time() - t0, 1)
    browser.close()

    with open(os.path.join(CAP, slug + ".json"), "w", encoding="utf-8") as f:
        json.dump(rec, f, indent=2, ensure_ascii=False)

    m = rec.get("metrics", {})
    print(f"\n=== {rec.get('name') or query} | {rec.get('rating')}★ ({rec.get('review_count')}) | {rec['status']}")
    print(f"  category={rec.get('category_primary')!r} service_area={rec.get('service_area')!r} photos={rec.get('photo_control_text')!r}")
    if m:
        print(f"  recent10={m.get('recent10_answered')}/{m.get('recent10_total')}  last90={m.get('last90_answered')}/{m.get('last90_total')}  lifetime={m.get('lifetime_coverage_pct')}%")
        print(f"  trend: recent2y={m.get('trend_recent_2y_pct')}% vs older={m.get('trend_older_pct')}% -> {m.get('trend_verdict')}")
        if not m.get("sample_sufficient"):
            print(f"  !! {m.get('sample_note')}")
        print(f"  lag_median≈{m.get('lag_median_days_approx')}d (n={m.get('lag_sample')}, quantised)  reply_len_median={m.get('reply_len_median')}")
        print(f"  bare_template={m.get('bare_template_pct')}%  mentions_service={m.get('reply_mentions_service_pct')}%  names_reviewer={m.get('reply_mentions_reviewer_name_pct')}%")
        print(f"  critical={m.get('critical_answered')}/{m.get('critical_total')} answered  critical_lag≈{m.get('critical_lag_median_days_approx')}d")
        print(f"  velocity≈{m.get('velocity_per_month_in_sample')}/mo (in-sample, biased)  latest_review={m.get('latest_review_days')}d")
    print(f"  posts: surface={rec['posts'].get('has_posts_surface')} dated_entries={rec['posts'].get('post_dated_entries')[:5]}")
    print(f"  gaps: {list(rec['gaps'].keys())}")
    print(f"  saved: {os.path.join(CAP, slug + '.json')}  ({rec['seconds_spent']}s)")


main()
