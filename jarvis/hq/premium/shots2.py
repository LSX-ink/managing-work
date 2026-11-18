import asyncio, sys, os
from playwright.async_api import async_playwright
from PIL import Image
async def main(url, out):
    async with async_playwright() as p:
        b = await p.chromium.launch(channel="msedge", args=["--use-angle=d3d11"])
        pg = await b.new_page(viewport={"width": 1440, "height": 900}); errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
        await pg.goto(url, wait_until="domcontentloaded"); await pg.wait_for_timeout(2500)
        H = await pg.evaluate("document.body.scrollHeight"); n = 0
        for y in range(0, H, 900):
            if n >= 9: break
            await pg.evaluate(f"scrollTo(0,{y})"); await pg.wait_for_timeout(1300)
            await pg.screenshot(path=f"{out}_{n}.jpg", type="jpeg", quality=55); n += 1
        m = await b.new_page(viewport={"width": 390, "height": 844}, is_mobile=True, device_scale_factor=2)
        await m.goto(url, wait_until="domcontentloaded"); await m.wait_for_timeout(2500)
        await m.screenshot(path=f"{out}_m.jpg", type="jpeg", quality=55)
        print(url.split('/')[-2], "pages", n, "overflow", await m.evaluate("document.documentElement.scrollWidth > innerWidth + 2"), "errors", errs)
        await b.close()
    s = Image.new("RGB", (5 * 384, 2 * 240), "black")
    for i in range(min(n, 9)):
        im = Image.open(f"{out}_{i}.jpg"); im.thumbnail((384, 240)); s.paste(im, ((i % 5) * 384, (i // 5) * 240))
    im = Image.open(f"{out}_m.jpg"); im.thumbnail((110, 240)); s.paste(im, (4 * 384 + 130, 240))
    s.save(f"{out}_sheet.jpg", quality=72)
asyncio.run(main(sys.argv[1], sys.argv[2]))
