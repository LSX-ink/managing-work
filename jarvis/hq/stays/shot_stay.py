import asyncio, sys
from pathlib import Path
from playwright.async_api import async_playwright

url, out = sys.argv[1], Path(sys.argv[2])


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(channel="msedge", args=["--use-angle=d3d11", "--enable-unsafe-swiftshader"])
        pg = await b.new_page(viewport={"width": 1440, "height": 900})
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
        await pg.goto(url, wait_until="networkidle"); await pg.wait_for_timeout(3500)
        await pg.screenshot(path=str(out / "s1-hero.jpg"), type="jpeg", quality=70)
        await pg.evaluate("document.getElementById('house').scrollIntoView()"); await pg.wait_for_timeout(4000)
        await pg.screenshot(path=str(out / "s2-house.jpg"), type="jpeg", quality=70)
        await pg.click("#floors button[data-f='1']"); await pg.wait_for_timeout(2500)
        await pg.screenshot(path=str(out / "s3-floor1.jpg"), type="jpeg", quality=70)
        await pg.evaluate("document.querySelectorAll('.suite')[3].click()"); await pg.wait_for_timeout(1500)
        await pg.screenshot(path=str(out / "s4-room.jpg"), type="jpeg", quality=70)
        await pg.keyboard.press("Escape"); await pg.wait_for_timeout(500)
        await pg.evaluate("document.querySelectorAll('.reveal').forEach(e=>e.classList.add('in'));document.getElementById('suites').scrollIntoView()"); await pg.wait_for_timeout(1500)
        await pg.screenshot(path=str(out / "s5-suites.jpg"), type="jpeg", quality=70)
        ph = await b.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True)
        await ph.goto(url, wait_until="networkidle"); await ph.wait_for_timeout(3500)
        await ph.screenshot(path=str(out / "s6-phone.jpg"), type="jpeg", quality=70)
        await ph.evaluate("document.getElementById('house').scrollIntoView()"); await ph.wait_for_timeout(3500)
        await ph.screenshot(path=str(out / "s7-phone-house.jpg"), type="jpeg", quality=70)
        wide = await ph.evaluate("document.documentElement.scrollWidth > innerWidth + 2")
        await b.close()
    print("errors:", errs[:6], "phone overflow:", wide)

asyncio.run(main())
