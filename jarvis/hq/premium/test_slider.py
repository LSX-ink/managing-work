import asyncio, sys
from playwright.async_api import async_playwright
async def main(urls):
    async with async_playwright() as p:
        b = await p.chromium.launch(channel="msedge")
        for u in urls:
            ctx = await b.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True, device_scale_factor=2)
            pg = await ctx.new_page(); await pg.goto(u, wait_until="domcontentloaded"); await pg.wait_for_timeout(2500)
            await pg.evaluate("document.querySelector('.ba').scrollIntoView({block:'center'})"); await pg.wait_for_timeout(600)
            x0 = await pg.evaluate("getComputedStyle(document.querySelector('.ba')).getPropertyValue('--x')")
            await pg.wait_for_timeout(1500); sweep = await pg.evaluate("getComputedStyle(document.querySelector('.ba')).getPropertyValue('--x')")
            await pg.wait_for_timeout(4500)
            r = await pg.evaluate("(()=>{const q=document.querySelector('.ba').getBoundingClientRect();return [q.left,q.top,q.width,q.height]})()")
            cdp = await ctx.new_cdp_session(pg)
            y = r[1] + r[3] / 2; pts = [(r[0] + r[2] * f, y) for f in (0.5, 0.4, 0.3, 0.2, 0.15)]
            await cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": pts[0][0], "y": pts[0][1]}]})
            for x_, y_ in pts[1:]:
                await cdp.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x": x_, "y": y_}]}); await pg.wait_for_timeout(60)
            await cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
            x1 = await pg.evaluate("getComputedStyle(document.querySelector('.ba')).getPropertyValue('--x')")
            print(u.split('/')[-2], "start", x0, "| auto-sweep", sweep, "| after finger drag", x1)
            await ctx.close()
        await b.close()
asyncio.run(main(sys.argv[1:]))
