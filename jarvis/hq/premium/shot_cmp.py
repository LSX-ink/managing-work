import asyncio, sys
from playwright.async_api import async_playwright
from PIL import Image
async def main(slugs):
    ims = []
    async with async_playwright() as p:
        b = await p.chromium.launch(channel="msedge")
        for s in slugs:
            pg = await b.new_page(viewport={"width": 1440, "height": 900}); errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
            await pg.goto(f"http://127.0.0.1:8765/{s}-v2/", wait_until="domcontentloaded"); await pg.wait_for_timeout(2500)
            await pg.evaluate("document.getElementById('compare').scrollIntoView()"); await pg.wait_for_timeout(1500)
            await pg.screenshot(path=f"shots2/cmp_{s}.jpg", type="jpeg", quality=55); ims.append(f"shots2/cmp_{s}.jpg")
            m = await b.new_page(viewport={"width": 390, "height": 844}, is_mobile=True, device_scale_factor=2)
            await m.goto(f"http://127.0.0.1:8765/{s}-v2/", wait_until="domcontentloaded"); await m.wait_for_timeout(2000)
            await m.evaluate("document.getElementById('compare').scrollIntoView()"); await m.wait_for_timeout(1200)
            await m.screenshot(path=f"shots2/cmpm_{s}.jpg", type="jpeg", quality=55)
            print(s, "overflow", await m.evaluate("document.documentElement.scrollWidth > innerWidth + 2"), errs)
        await b.close()
    S = Image.new("RGB", (4 * 480, ((len(slugs) + 1) // 2) * 300), "black")
    for i, s in enumerate(slugs):
        a = Image.open(f"shots2/cmp_{s}.jpg"); a.thumbnail((480, 300)); S.paste(a, ((i % 2) * 960, (i // 2) * 300))
        m = Image.open(f"shots2/cmpm_{s}.jpg"); m.thumbnail((140, 300)); S.paste(m, ((i % 2) * 960 + 490, (i // 2) * 300))
    S.save("shots2/cmp_all.jpg", quality=70)
asyncio.run(main(sys.argv[1:]))
