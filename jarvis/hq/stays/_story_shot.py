import asyncio, sys
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(channel="msedge", args=["--use-angle=d3d11"])
        for tag, vp, mob in (("d", {"width": 1440, "height": 900}, False), ("m", {"width": 390, "height": 844}, True)):
            pg = await b.new_page(viewport=vp, device_scale_factor=1 if not mob else 2, is_mobile=mob)
            errs = []; pg.on("pageerror", lambda e: errs.append(str(e))); pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
            await pg.goto(sys.argv[1], wait_until="networkidle"); await pg.wait_for_timeout(3500)
            top = await pg.evaluate("document.querySelector('.story').offsetTop"); hgt = await pg.evaluate("document.querySelector('.story').offsetHeight - innerHeight")
            for i, f in enumerate([.05, .3, .5, .7, .95]):
                await pg.evaluate(f"scrollTo(0, {top} + {hgt} * {f})"); await pg.wait_for_timeout(900)
                if tag == "d" or i in (0, 4): await pg.screenshot(path=f"{sys.argv[2]}/story_{tag}{i}.jpg", type="jpeg", quality=55)
            await pg.evaluate("document.getElementById('house').scrollIntoView()"); await pg.wait_for_timeout(700)
            await pg.screenshot(path=f"{sys.argv[2]}/grow_{tag}a.jpg", type="jpeg", quality=55); await pg.wait_for_timeout(2600)
            await pg.screenshot(path=f"{sys.argv[2]}/grow_{tag}b.jpg", type="jpeg", quality=55)
            print(tag, errs[:4], await pg.evaluate("document.documentElement.scrollWidth > innerWidth + 2"))
        await b.close()
asyncio.run(main())
