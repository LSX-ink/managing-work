import asyncio, sys
from playwright.async_api import async_playwright
async def main(url, out):
    async with async_playwright() as p:
        b = await p.chromium.launch(channel="msedge")
        pg = await b.new_page(viewport={"width": 1440, "height": 900})
        await pg.goto(url, wait_until="domcontentloaded"); await pg.wait_for_timeout(3000)
        await pg.screenshot(path=out + "_d.jpg", type="jpeg", quality=60, full_page=True)
        pg = await b.new_page(viewport={"width": 390, "height": 844}, is_mobile=True)
        await pg.goto(url, wait_until="domcontentloaded"); await pg.wait_for_timeout(3000)
        await pg.screenshot(path=out + "_m.jpg", type="jpeg", quality=60)
        await b.close()
asyncio.run(main(sys.argv[1], sys.argv[2]))
