import asyncio, sys
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(channel="msedge", args=["--use-angle=d3d11"])
        pg = await b.new_page(viewport={"width": 1440, "height": 900})
        await pg.goto(sys.argv[1], wait_until="domcontentloaded"); await pg.wait_for_timeout(3000)
        await pg.evaluate("document.querySelectorAll('.reveal').forEach(e=>e.classList.add('in')); document.getElementById('hood').scrollIntoView()")
        await pg.wait_for_timeout(9000); await pg.screenshot(path=sys.argv[2], type="jpeg", quality=60)
        await b.close()
asyncio.run(main())
