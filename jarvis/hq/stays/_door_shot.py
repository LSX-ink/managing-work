import asyncio, sys
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(channel="msedge", args=["--use-angle=d3d11"])
        for tag, vp, mob in (("d", {"width": 1440, "height": 900}, False), ("m", {"width": 390, "height": 844}, True)):
            pg = await b.new_page(viewport=vp, device_scale_factor=1 if not mob else 2, is_mobile=mob)
            errs = []; pg.on("pageerror", lambda e: errs.append(str(e))); pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
            await pg.goto(sys.argv[1], wait_until="domcontentloaded")
            for t, w in (("a", 4500), ("b", 2500), ("c", 1500), ("d", 1700)):
                if t == "c": await pg.evaluate("document.querySelector('.door .go') && document.querySelector('.door .go').click()")
                await pg.wait_for_timeout(w); await pg.screenshot(path=f"{sys.argv[2]}/door_{tag}{t}.jpg", type="jpeg", quality=55)
            print(tag, errs[:4], await pg.evaluate("document.documentElement.scrollWidth > innerWidth + 2"))
        await b.close()
asyncio.run(main())
