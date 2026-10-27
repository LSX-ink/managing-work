import asyncio, sys
from playwright.async_api import async_playwright
async def main(hs):
    async with async_playwright() as p:
        b = await p.chromium.launch(channel="msedge"); ctx = await b.new_context(locale="en-GB", viewport={"width": 1200, "height": 900})
        for h in hs:
            pg = await ctx.new_page()
            try:
                r = await pg.goto(f"https://www.instagram.com/{h}/", wait_until="domcontentloaded", timeout=30000); await pg.wait_for_timeout(3500)
                t = await pg.title(); og = await pg.evaluate("(document.querySelector('meta[property=\"og:title\"]')||{}).content||''")
                d = await pg.evaluate("(document.querySelector('meta[property=\"og:description\"]')||{}).content||''")
                print(h, "|", r.status, "|", t[:80], "|", og[:80], "|", d[:120])
            except Exception as ex: print(h, "ERR", ex)
            await pg.close()
        await b.close()
asyncio.run(main(sys.argv[1:]))
