"""Check every page we send, on the live site, the way a customer would (owner, 26 Oct 2026: "check everything ... once u find
an issue fix it"): page loads, no broken images/videos/files, no script errors, every link and button goes somewhere real,
menu tabs switch, the before/after drags, the map loads, nothing spills sideways on a phone."""
import asyncio, json, sys
import httpx
from playwright.async_api import async_playwright

BASE = "https://kineticwebdesigns.co.uk/m/"


async def check(b, http, slug):
    url = BASE + slug + "/"
    issues = []
    for mobile in (False, True):
        ctx = await b.new_context(viewport={"width": 390, "height": 844} if mobile else {"width": 1440, "height": 900},
                                  is_mobile=mobile, has_touch=mobile, device_scale_factor=2 if mobile else 1)
        pg = await ctx.new_page(); bad, errs = [], []
        pg.on("response", lambda r: bad.append(f"{r.status} {r.url}") if r.status >= 400 and "kineticwebdesigns" in r.url and "favicon" not in r.url else None)
        pg.on("pageerror", lambda e: errs.append(str(e)[:150]))
        r = await pg.goto(url, wait_until="domcontentloaded", timeout=60000)
        if not r or r.status != 200:
            issues.append(f"page status {r.status if r else 'none'}")
        await pg.wait_for_timeout(3000)
        h = await pg.evaluate("document.body.scrollHeight")
        for y in range(0, h, 700):  # scroll through so lazy images and sections load
            await pg.evaluate(f"scrollTo(0,{y})"); await pg.wait_for_timeout(120)
        await pg.wait_for_timeout(1500)
        if not mobile:
            broken = await pg.evaluate("[...document.images].filter(i=>i.complete&&i.naturalWidth===0&&i.src).map(i=>i.src)")
            issues += [f"broken image {x}" for x in broken]
            title = await pg.title()
            if "Kinetic Web Designs" in title and "concept" not in title:
                issues.append("page is the Kinetic homepage (folder missing)")
            anchors = await pg.evaluate("[...document.querySelectorAll('a[href^=\"#\"]')].map(a=>a.getAttribute('href')).filter(h=>h.length>1&&!document.getElementById(h.slice(1)))")
            issues += [f"link to missing section {a}" for a in set(anchors)]
            links = await pg.evaluate("[...new Set([...document.querySelectorAll('a[href^=\"http\"]')].map(a=>a.href))]")
            for l in links:
                if any(x in l for x in ("instagram.com", "facebook.com", "wa.me", "maps.google")):
                    continue  # these block robots; checked separately
                try:
                    rr = await http.get(l, follow_redirects=True, timeout=25)
                    if rr.status_code >= 400:
                        issues.append(f"button/link goes nowhere ({rr.status_code}): {l}")
                except Exception as ex:
                    issues.append(f"button/link failed: {l} ({type(ex).__name__})")
            tabs = await pg.evaluate("document.querySelectorAll('[data-tab],.tab').length")
            if tabs > 1:
                ok = await pg.evaluate("""(()=>{const t=[...document.querySelectorAll('[data-tab],.tab')];const b=t[1];b.click();
                    const p=document.querySelector('[data-pane].on,.menu.on');return !!p && (p.dataset.pane||p.dataset.i)===(b.dataset.tab||b.dataset.i)})()""")
                if not ok:
                    issues.append("price tabs don't switch")
            if await pg.evaluate("!!document.querySelector('.ba')"):
                await pg.evaluate("document.querySelector('.ba').scrollIntoView({block:'center'})"); await pg.wait_for_timeout(6000)
                q = await pg.evaluate("(()=>{const r=document.querySelector('.ba').getBoundingClientRect();return [r.left,r.top,r.width,r.height]})()")
                await pg.mouse.move(q[0] + q[2] * .5, q[1] + q[3] * .5); await pg.mouse.down(); await pg.mouse.move(q[0] + q[2] * .2, q[1] + q[3] * .5, steps=6); await pg.mouse.up()
                x = await pg.evaluate("parseFloat(getComputedStyle(document.querySelector('.ba')).getPropertyValue('--x'))")
                if not (x < 30):
                    issues.append(f"before/after slider doesn't drag (x={x})")
            maps = await pg.evaluate("document.querySelectorAll('iframe[src*=\"maps.google\"]').length")
            if not maps:
                issues.append("no map")
            vids = await pg.evaluate("[...document.querySelectorAll('video source, video[src]')].map(v=>v.src).filter(Boolean)")
            for v in vids:
                rr = await http.head(v, timeout=25)
                if rr.status_code >= 400 or "video" not in rr.headers.get("content-type", ""):
                    issues.append(f"video broken: {v}")
        else:
            if await pg.evaluate("document.documentElement.scrollWidth > innerWidth + 2 || innerWidth > 392"):  # a too-wide part also widens the phone screen itself
                issues.append("phone: page spills sideways")
        issues += [("phone: " if mobile else "") + x for x in bad]
        issues += [("phone: " if mobile else "") + "script error: " + x for x in errs]
        await ctx.close()
    return slug, sorted(set(issues))


async def main(slugs):
    async with async_playwright() as p, httpx.AsyncClient(headers={"User-Agent": "Mozilla/5.0"}) as http:
        b = await p.chromium.launch(channel="msedge", args=["--use-angle=d3d11"])
        res = {}
        for s in slugs:
            try:
                slug, iss = await check(b, http, s)
            except Exception as ex:
                slug, iss = s, [f"checker crashed: {ex}"]
            res[slug] = iss
            print(("OK   " if not iss else "FAIL ") + slug, *(["\n     - " + i for i in iss] if iss else []), flush=True)
        await b.close()
    json.dump(res, open("full_check.json", "w"), indent=1)


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:]))
