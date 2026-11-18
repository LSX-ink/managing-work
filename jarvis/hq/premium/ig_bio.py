import asyncio, sys, re
from playwright.async_api import async_playwright
async def main(hs):
    async with async_playwright() as p:
        b = await p.chromium.launch(channel="msedge"); ctx = await b.new_context(locale="en-GB", viewport={"width": 1200, "height": 1000})
        for h in hs:
            pg = await ctx.new_page(); await pg.goto(f"https://www.instagram.com/{h}/", wait_until="domcontentloaded"); await pg.wait_for_timeout(4500)
            t = re.sub(r"\s+", " ", await pg.evaluate("document.body.innerText"))[:700]
            print("==", h, "|", t); await pg.close()
        await b.close()
asyncio.run(main(sys.argv[1:]))
