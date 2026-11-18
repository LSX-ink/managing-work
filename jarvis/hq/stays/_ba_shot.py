import asyncio, sys
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(channel="msedge")
        for tag, vp, mob in (("d", {"width": 1440, "height": 900}, False), ("m", {"width": 390, "height": 844}, True)):
            pg = await b.new_page(viewport=vp, is_mobile=mob, device_scale_factor=2 if mob else 1)
            await pg.goto(sys.argv[1], wait_until="domcontentloaded"); await pg.wait_for_timeout(2500)
            await pg.evaluate("document.querySelectorAll('.reveal').forEach(e=>e.classList.add('in')); document.getElementById('compare').scrollIntoView()")
            await pg.wait_for_timeout(1500); await pg.screenshot(path=f"{sys.argv[2]}_{tag}.jpg", type="jpeg", quality=60)
            print(tag, await pg.evaluate("document.documentElement.scrollWidth > innerWidth + 2"))
        await b.close()
asyncio.run(main())
