import asyncio, sys
from pathlib import Path
from playwright.async_api import async_playwright


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(channel="msedge", args=["--headless=new"])
        pg = await b.new_page(viewport={"width": 1800, "height": 1300})
        for f in sys.argv[1:]:
            await pg.goto(Path(f).as_uri() + "#toolbar=0&view=Fit"); await pg.wait_for_timeout(3500)
            await pg.screenshot(path=f[:-4] + ".png")
            print("shot", f)
        await b.close()

asyncio.run(main())
