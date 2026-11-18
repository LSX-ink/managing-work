import asyncio, sys
from playwright.async_api import async_playwright
from PIL import Image
async def main(url, out):
    async with async_playwright() as p:
        b = await p.chromium.launch(channel="msedge", args=["--use-angle=d3d11"])
        pg = await b.new_page(viewport={"width": 1440, "height": 900})
        errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
        await pg.goto(url, wait_until="domcontentloaded"); await pg.wait_for_timeout(1000)
        await pg.screenshot(path=f"{out}_0.jpg", type="jpeg", quality=55)
        await pg.wait_for_timeout(3500); await pg.screenshot(path=f"{out}_1.jpg", type="jpeg", quality=55)
        for i, sel in enumerate(["#experience", "#services", ".vip", "#gallery", "#reviews", "#visit"]):
            if await pg.locator(sel).count():
                await pg.locator(sel).scroll_into_view_if_needed(); await pg.wait_for_timeout(1500)
                await pg.screenshot(path=f"{out}_{i+2}.jpg", type="jpeg", quality=55)
        m = await b.new_page(viewport={"width": 390, "height": 844}, is_mobile=True, device_scale_factor=2)
        await m.goto(url, wait_until="domcontentloaded"); await m.wait_for_timeout(4500)
        await m.screenshot(path=f"{out}_m1.jpg", type="jpeg", quality=55)
        await m.evaluate("document.getElementById('services').scrollIntoView()"); await m.wait_for_timeout(1500)
        await m.screenshot(path=f"{out}_m2.jpg", type="jpeg", quality=55)
        print("overflow", await m.evaluate("document.documentElement.scrollWidth > innerWidth + 2"), "errors", errs)
        await b.close()
    import os; ims = [Image.open(f"{out}_{k}.jpg") for k in range(8) if os.path.exists(f"{out}_{k}.jpg")]
    s = Image.new("RGB", (4 * 480, 2 * 300 + 420), "black")
    for i, im in enumerate(ims): im.thumbnail((480, 300)); s.paste(im, ((i % 4) * 480, (i // 4) * 300))
    for i, k in enumerate(("m1", "m2")): im = Image.open(f"{out}_{k}.jpg"); im.thumbnail((200, 420)); s.paste(im, (i * 200, 600))
    s.save(f"{out}_sheet.jpg", quality=75)
asyncio.run(main(sys.argv[1], sys.argv[2]))
