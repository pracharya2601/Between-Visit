"""Axe + heading/title/skip-link/footer audit; exec this file and await run(page)."""
import json
BASE = open('/app/frontend/.env').read().split('REACT_APP_BACKEND_URL=')[1].split()[0]
AXE = open('/app/frontend/node_modules/axe-core/axe.min.js').read()
FOOT = "Experimental practice tool used under the practitioner's direction. It doesn't replace the cane, the dog guide or the specialist, and it isn't a safety device."
PAGES = [
    ("landing", "/"), ("research", "/research"), ("workspace", "/workspace"), ("clients", "/clients"),
    ("client", "/clients/0a8239a5-8108-4595-a916-50a172a9edac"), ("routes", "/routes"),
    ("builder", "/routes/276dc5bb-53b0-4734-83d7-c7743052d09d"), ("assign", "/routes/276dc5bb-53b0-4734-83d7-c7743052d09d/assign"),
    ("teach", "/teach/fbdcfecd-1fe2-47c9-a9b8-85bfc58d9a2b"), ("teach-review", "/teach/1b760b7e-b8ed-46e0-866e-267278bc7226/review"),
    ("review", "/review/48461db6-54af-4344-a634-30753164eb85"), ("run", "/run/7b73c71a-3a1e-413f-8ae8-9aa5b1731d5f#key=fxzAyvXAal7aa6pD6PIcJosHv58xYi-F"),
    ("demo", "/demo"), ("route-replay", "/routes/276dc5bb-53b0-4734-83d7-c7743052d09d/replay"), ("device-test", "/device-test"),
    ("note-print", "/notes/ee1fd716-6a33-41ff-90dc-82f08e574a8b/print"),
]
CHECK = """() => {
  const hs = [...document.querySelectorAll('h1,h2,h3,h4,h5,h6')].filter(h => h.offsetParent !== null || h.getClientRects().length);
  const lv = hs.map(h => +h.tagName[1]); const skips = [];
  for (let i = 1; i < lv.length; i++) if (lv[i] > lv[i-1] + 1) skips.push(hs[i-1].tagName + '>' + hs[i].tagName + ':' + hs[i].innerText.slice(0, 30));
  const skip = document.querySelector('[data-testid=skip-to-content-link]');
  const foot = document.querySelector('[data-testid=footer-disclaimer]');
  return {h1: lv.filter(l => l === 1).length, skips, title: document.title, skip: !!skip && !!document.querySelector(skip.getAttribute('href')), footer: foot ? foot.innerText.trim() : null};
}"""

async def run(page, pages=None):
    PAGES_ = pages or PAGES
    await page.set_viewport_size({"width": 1366, "height": 900})
    titles = {}
    for name, path in PAGES_:
        try:
            await page.goto(BASE + path, wait_until="domcontentloaded")
            await page.wait_for_timeout(3000)
            await page.evaluate(AXE)
            res = await page.evaluate("async () => { const r = await axe.run(document, {resultTypes: ['violations']}); return r.violations.map(v => ({id: v.id, impact: v.impact, n: v.nodes.length, t: v.nodes.slice(0, 3).map(n => n.target.join(' ') + ' | ' + (n.failureSummary || '').split('\\n').slice(1, 2).join(''))})); }")
            info = await page.evaluate(CHECK)
            titles.setdefault(info["title"], []).append(name)
            bad = [v for v in res if v["impact"] in ("serious", "critical")]
            other = [f"{v['id']}({v['impact']})" for v in res if v["impact"] not in ("serious", "critical")]
            print(f"== {name}: serious/critical {len(bad)} | h1 {info['h1']} | skips {info['skips']} | title '{info['title']}' | skiplink {info['skip']} | footer {info['footer'] == FOOT if info['footer'] is not None else 'none'} | minor {other}")
            for v in bad:
                print("   ", v["id"], v["impact"], v["n"], json.dumps(v["t"])[:400])
        except Exception as e:
            print("FAIL", name, e)
    print("duplicate titles:", {t: n for t, n in titles.items() if len(n) > 1})
