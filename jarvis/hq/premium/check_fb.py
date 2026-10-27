import asyncio, sys
from playwright.async_api import async_playwright
async def main(urls):
    async with async_playwright() as p:
        b = await p.chromium.launch(channel="msedge"); ctx = await b.new_context(locale="en-GB")
        for u in urls:
            pg = await ctx.new_page(); r = await pg.goto(u, wait_until="domcontentloaded"); await pg.wait_for_timeout(3500)
            print(u, "|", r.status, "|", (await pg.title())[:90]); await pg.close()
        await b.close()
asyncio.run(main(sys.argv[1:]))
