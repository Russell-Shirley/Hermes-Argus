"""Verify Template B's second claim: 'the profile doesn't look like it's been updated.'

Checks each listing for Google Business Profile update posts (the 'See local posts'
control) and reports the recency of anything found, so the claim is only used where
it holds. Usage: python check_posts.py "Business One Cumming GA" "..."
Writes gbp_posts.json
"""
import json, os, re, sys, time

from cloakbrowser import launch

OUT = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(OUT, "gbp_posts.json")
MIN_SECONDS = 40.0

browser = launch(headless=True, humanize=False)


def check(query):
    t0 = time.time()
    ctx = browser.new_context(viewport={"width": 1440, "height": 1100})
    page = ctx.new_page()
    rec = {"query": query}
    try:
        page.goto("https://www.google.com/maps?hl=en", timeout=90000)
        page.wait_for_timeout(7000)
        box = page.query_selector('input#searchboxinput, input[name="q"]')
        box.click(); page.keyboard.type(query, delay=45); page.wait_for_timeout(700)
        page.keyboard.press("Enter"); page.wait_for_timeout(14000)
        # open the listing, verifying we land on a place page
        for _ in range(3):
            link = page.query_selector('div[role="feed"] a.hfpxzc')
            if link:
                link.click()
                page.wait_for_timeout(11000)
            h1 = page.evaluate("""(() => {const m=document.querySelector("div[role='main'] h1"); return m?m.innerText.trim():''})()""")
            if h1 and h1.lower() not in ("results", "search results", "google maps") and len(h1) > 2:
                break
            page.wait_for_timeout(3500)
        for _ in range(3):
            hit = page.evaluate("""(() => { const d=[...document.querySelectorAll('button,[role="button"],a')]
              .find(x => /^\\s*(Dismiss|Not now)\\s*$/i.test((x.innerText||'').trim())); if(d){d.click();return true;} return false;})()""")
            if not hit:
                break
            page.wait_for_timeout(2200)
        rec["name"] = page.evaluate("""(() => {const m=document.querySelector("div[role='main'] h1"); return m?m.innerText.trim():''})()""")

        # is there a local-posts / updates surface at all?
        rec["post_controls"] = page.evaluate("""(() => {
          const out = [];
          document.querySelectorAll('button,[role="button"],a,div[aria-label]').forEach(x => {
            const t = ((x.innerText||'') + ' ' + (x.getAttribute('aria-label')||'')).replace(/\\s+/g,' ').trim();
            if (/local post|updates?\\b|see post|view post/i.test(t) && t.length < 70) out.push(t);
          });
          return [...new Set(out)].slice(0, 8);
        })()""")
        rec["has_posts_control"] = bool(rec["post_controls"])

        # expand posts if possible and grab text + any relative dates
        expanded = page.evaluate("""(() => {
          const b = [...document.querySelectorAll('button,[role="button"],a,div[aria-label]')]
            .find(x => /local post|see post|view post/i.test(((x.innerText||'')+' '+(x.getAttribute('aria-label')||''))));
          if (!b) return false;
          b.scrollIntoView({block:'center'}); b.click(); return true;
        })()""")
        rec["posts_expanded"] = expanded
        page.wait_for_timeout(6500)
        txt = page.evaluate("""(() => {const m=document.querySelector("div[role='main']"); return m?m.innerText.replace(/\\s+/g,' ').slice(0, 4000):''})()""")
        dates = re.findall(r"(\d+\s+(?:day|week|month|year)s?\s+ago|a\s+(?:day|week|month|year)\s+ago|yesterday)", txt, re.I)
        rec["dates_seen"] = dates[:10]
        rec["posts_snippet"] = txt[:600]
        page.screenshot(path=os.path.join(OUT, "posts_" + re.sub(r"[^A-Za-z0-9]+", "_", query)[:28] + ".png"))
        rec["status"] = "OK" if rec.get("name") else "GATED"
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
    return rec


QUERIES = sys.argv[1:] or ["Andy Lewis Hobson Heating Air Cumming GA"]
out = []
for q in QUERIES:
    r = check(q)
    out.append(r)
    print(f"\n=== {r.get('name') or q} | {r['status']}")
    print(f"    post controls: {r.get('post_controls')}")
    print(f"    posts expanded: {r.get('posts_expanded')} | dates seen: {r.get('dates_seen')}")
browser.close()

existing = json.load(open(RESULTS, encoding="utf-8")) if os.path.exists(RESULTS) else []
existing.extend(out)
json.dump(existing, open(RESULTS, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print("\nsaved:", RESULTS)
