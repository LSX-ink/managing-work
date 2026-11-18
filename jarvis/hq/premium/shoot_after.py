"""after.jpg: this design's first screen on a phone, the same size as their before.jpg (600 x 1169)."""
import asyncio, sys
from pathlib import Path
from playwright.async_api import async_playwright
async def main(pairs):
    async with async_playwright() as p:
        b = await p.chromium.launch(channel="msedge", args=["--use-angle=d3d11"])
        for url, out in pairs:
            pg = await b.new_page(viewport={"width": 390, "height": 760}, device_scale_factor=600 / 390, is_mobile=True)
            await pg.goto(url, wait_until="domcontentloaded"); await pg.wait_for_timeout(4500)
            await pg.screenshot(path=out, type="jpeg", quality=82); await pg.close(); print("shot", out)
        await b.close()
args = sys.argv[1:]; asyncio.run(main(list(zip(args[::2], args[1::2]))))
