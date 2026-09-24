"""Check whether the SERP map block numbers its pins, across a few query shapes.
Dumps any element carrying a numeric rank label + the local-pack section text + screenshot.
"""
import json, os, re, sys

from cloakbrowser import launch

OUT = os.path.dirname(os.path.abspath(__file__))
QUERIES = [
    "air duct cleaning Cumming GA",
    "best duct cleaning in Cumming GA",
]
report = {}

PIN_JS = """(() => {
  const hits = [];
  document.querySelectorAll('[aria-label],[data-item-id],svg,g').forEach(el => {
    const al = el.getAttribute && el.getAttribute('aria-label');
    if (!al) return;
    if (/^\\s*\\d{1,2}\\s*[.:)]?\\s*[A-Z]/.test(al) || /^\\s*[A-F]\\s*[.:)]/.test(al)) {
      hits.push({tag: el.tagName, label: al.slice(0, 90)});
    }
  });
  return hits.slice(0, 25);
})()"""

browser = launch(headless=True, humanize=False)
page = browser.new_page(viewport={"width": 1440, "height": 1100})

for q in QUERIES:
    info = {}
    page.goto("https://www.google.com/?hl=en&gl=us", timeout=60000)
    page.wait_for_timeout(4500)
    box = page.query_selector('textarea[name="q"], input[name="q"]')
    box.click(); page.keyboard.type(q, delay=30); page.wait_for_timeout(600)
    page.keyboard.press("Enter"); page.wait_for_timeout(10000)
    slug = re.sub(r"\W+", "_", q)[:40]
    page.screenshot(path=os.path.join(OUT, f"serp_pin_{slug}.png"), full_page=True)
    body = page.evaluate("document.body.innerText")
    info["walled"] = bool(re.search(r"unusual traffic|not a robot", body, re.I))
    info["numeric_pin_labels"] = page.evaluate(PIN_JS)
    # locate the local-pack section: heading text + following list
    info["local_section"] = page.evaluate("""(() => {
      const out = [];
      document.querySelectorAll('h1,h2,h3,div').forEach(el => {
        const t = (el.innerText || '').trim();
        if (/^(THE )?BEST .*NEAR .*$/i.test(t) && t.length < 90) out.push(t);
      });
      return out.slice(0, 3);
    })()""")
    # count GBP cards in the pack: anchors to /maps/place/
    info["pack_links"] = page.evaluate("""(() => {
      const seen = new Set(); const out = [];
      document.querySelectorAll('a[href*="/maps/place/"]').forEach(a => {
        const n = (a.getAttribute('aria-label') || a.innerText || '').trim().split('\\n')[0];
        if (!n || n.length > 60 || seen.has(n)) return; seen.add(n); out.push(n);
      });
      return out;
    })()""")
    info["marker_count"] = page.evaluate("document.querySelectorAll('img[src*=\"maps/vt\"], div[style*=\"background-image\"]').length")
    report[q] = info
    print(f"\n=== {q} | walled={info['walled']}")
    print("  local section headings:", info["local_section"])
    print("  numeric/lettered pin labels:", info["numeric_pin_labels"][:6])
    print("  pack links (/maps/place/):", info["pack_links"][:8])

browser.close()
with open(os.path.join(OUT, "pin_number_check.json"), "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2, ensure_ascii=False)
print("\nsaved pin_number_check.json")
