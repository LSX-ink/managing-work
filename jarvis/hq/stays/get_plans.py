"""List every drawing on Birmingham planning application 2023/07524/PA and save the floor plans (approved first),
by browsing the council's public page normally and opening each document like a visitor would."""
import asyncio, json, re, sys
from pathlib import Path
from playwright.async_api import async_playwright

OUT = Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)
URL = ("https://planning.birmingham.gov.uk/NECSWS/ES/Presentation/Planning/OnlinePlanning/OnlinePlanningOverview"
       "?applicationNumber=2023%2F07524%2FPA&guid=2de01756-276f-41d2-983e-aa95c2fb1116")


async def main():
    async with async_playwright() as pw:
        b = await pw.chromium.launch(channel="msedge")
        ctx = await b.new_context(accept_downloads=True)
        pg = await ctx.new_page()
        await pg.goto(URL, wait_until="networkidle")
        await pg.click("a[href='#tabDocuments']"); await pg.wait_for_timeout(2500)
        docs = {}
        for page_no in range(1, 5):
            rows = await pg.evaluate("""() => [...document.querySelectorAll('a[href*=DisplaySearchDocument]')].map(a0 => { const tr = a0.closest('tr') || a0.parentElement;
                const a = tr.querySelector('a[href*=DisplaySearchDocument]'); if (!a) return null;
                return {name: a.innerText.trim(), href: a.href, type: (tr.innerText.split('\\t').pop() || '').trim(), row: tr.innerText.replace(/\\s+/g,' ')}; }).filter(Boolean)""")
            for r in rows:
                docs[r["href"]] = r
            nxt = pg.locator(f"a:text-is('{page_no + 1}')")
            if await nxt.count() == 0:
                break
            await nxt.first.click(); await pg.wait_for_timeout(2000)
        docs = list(docs.values())
        for d in docs:
            print("-", d["row"][:150])
        wanted = [d for d in docs if re.search(r"floor|basement|elevation|layout", d["name"], re.I)]
        saved = []
        for d in wanted:
            got = await ctx.request.get(d["href"])
            body = await got.body()
            kind = got.headers.get("content-type", "")
            name = re.sub(r"[^A-Za-z0-9]+", "-", d["name"])[:70] + ".pdf"
            if "pdf" in kind or body[:4] == b"%PDF":
                (OUT / name).write_bytes(body); saved.append({**d, "file": name})
            else:
                print("not a pdf:", d["name"], kind, len(body))
        json.dump(saved, open(OUT / "plans.json", "w"), indent=1)
        print("saved", [s["file"] for s in saved])
        await b.close()

asyncio.run(main())
