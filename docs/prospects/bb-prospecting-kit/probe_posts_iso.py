"""Isolate GBP update-post activity for one listing: find the Updates/posts surface,
read what it contains, and report the most recent post date (or prove absence).
"""
import json, os, re, sys

from cloakbrowser import launch

OUT = os.path.dirname(os.path.abspath(__file__))
# The run's data dir. Defaults to <run>/data when this toolkit is copied into
# <run>/scripts/; set RUN_DATA to run it IN PLACE against any run folder.
DATA = os.environ.get("RUN_DATA") or os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "data")
os.makedirs(DATA, exist_ok=True)

QUERY = sys.argv[1] if len(sys.argv) > 1 else "Technicare Home Pros Cumming GA"

browser = launch(headless=True, humanize=False)
ctx = browser.new_context(viewport={"width": 1440, "height": 1100})
page = ctx.new_page()
page.goto("https://www.google.com/maps?hl=en", timeout=90000)
page.wait_for_timeout(7000)
box = page.query_selector('input#searchboxinput, input[name="q"]')
box.click(); page.keyboard.type(QUERY, delay=45); page.wait_for_timeout(700)
page.keyboard.press("Enter"); page.wait_for_timeout(14000)
link = page.query_selector('div[role="feed"] a.hfpxzc')
if link:
    link.click(); page.wait_for_timeout(12000)
for _ in range(3):
    hit = page.evaluate("""(() => { const d=[...document.querySelectorAll('button,[role="button"],a')]
      .find(x => /^\\s*(Dismiss|Not now)\\s*$/i.test((x.innerText||'').trim())); if(d){d.click();return true;} return false;})()""")
    if not hit:
        break
    page.wait_for_timeout(2200)

print("listing:", page.evaluate("""(() => {const m=document.querySelector("div[role='main'] h1"); return m?m.innerText.trim():'?'})()"""))
page.wait_for_timeout(3000)
# anything mentioning posts/updates anywhere on the page
hits = page.evaluate("""(() => {
  const out = [];
  document.querySelectorAll('*').forEach(x => {
    const al = x.getAttribute && x.getAttribute('aria-label');
    const t = (x.innerText || '').trim();
    const label = al || '';
    if (/local post|update|photos & videos|by owner/i.test(label) && label.length < 80) out.push({kind:'aria', v: label});
    else if (x.children.length === 0 && /^(Updates?|Posts?)$/i.test(t)) out.push({kind:'text', v: t});
  });
  const seen = new Set(); return out.filter(o => { if (seen.has(o.v)) return false; seen.add(o.v); return true; }).slice(0, 15);
})()""")
print("post/update surfaces:", hits)

# try opening the posts view
opened = page.evaluate("""(() => {
  const b = [...document.querySelectorAll('[aria-label],button,span,div')]
    .find(x => /see local posts|local post|view post/i.test((x.getAttribute && x.getAttribute('aria-label')) || x.innerText || ''));
  if (!b) return 'not found';
  b.scrollIntoView({block:'center'}); b.click();
  return 'clicked: ' + ((b.getAttribute && b.getAttribute('aria-label')) || b.innerText || '').trim().slice(0,50);
})()""")
print("posts open attempt:", opened)
page.wait_for_timeout(7000)
page.screenshot(path=os.path.join(DATA, "posts_iso_" + re.sub(r"[^A-Za-z0-9]+", "_", QUERY)[:26] + ".png"))

body = page.evaluate("""(() => {const m=document.querySelector("div[role='main']"); return m?m.innerText.replace(/\\s+/g,' '):''})()""")
print("\n--- main pane text (first 1200) ---")
print(body[:1200])
print("\nrelative dates anywhere:", re.findall(r"(\d+\s+(?:day|week|month|year)s?\s+ago|a\s+(?:day|week|month|year)\s+ago|yesterday)", body, re.I)[:12])
browser.close()
