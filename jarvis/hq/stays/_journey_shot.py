import asyncio, sys
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(channel="msedge", args=["--use-angle=d3d11", "--autoplay-policy=no-user-gesture-required"])
        for tag, vp, mob in (("d", {"width": 1440, "height": 900}, False), ("m", {"width": 390, "height": 844}, True)):
            pg = await b.new_page(viewport=vp, device_scale_factor=1 if not mob else 2, is_mobile=mob)
            errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
            await pg.goto(sys.argv[1], wait_until="domcontentloaded"); await pg.wait_for_timeout(6000)
            top = await pg.evaluate("document.querySelector('.journey-s').offsetTop"); hgt = await pg.evaluate("document.querySelector('.journey-s').offsetHeight - innerHeight")
            times = []
            for i, f in enumerate([.03, .3, .6, .85, .97]):
                await pg.evaluate(f"scrollTo(0, {top} + {hgt} * {f})"); await pg.wait_for_timeout(2200)
                times.append(round(await pg.evaluate("document.querySelector('.journey-s video').currentTime"), 2))
                if tag == "d" or i in (1, 4): await pg.screenshot(path=f"{sys.argv[2]}/j_{tag}{i}.jpg", type="jpeg", quality=55)
            print(tag, "video times", times, errs[:3], await pg.evaluate("document.documentElement.scrollWidth > innerWidth + 2"))
        await b.close()
asyncio.run(main())
