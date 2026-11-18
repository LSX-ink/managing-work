import asyncio, sys
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(channel="msedge", args=["--use-angle=d3d11", "--autoplay-policy=no-user-gesture-required"])
        for tag, vp, mob in (("d", {"width": 1440, "height": 900}, False), ("m", {"width": 390, "height": 844}, True)):
            pg = await b.new_page(viewport=vp, is_mobile=mob)
            await pg.goto(sys.argv[1], wait_until="domcontentloaded"); await pg.wait_for_timeout(4500)
            await pg.click(".door .go"); await pg.wait_for_timeout(13000)
            await pg.screenshot(path=f"{sys.argv[2]}_{tag}.jpg", type="jpeg", quality=60)
            if tag == "d":
                await pg.evaluate("document.querySelectorAll('.reveal').forEach(e=>e.classList.add('in')); (document.querySelector('.plan')||document.getElementById('compare')||document.body).scrollIntoView()")
                await pg.wait_for_timeout(1200); await pg.screenshot(path=f"{sys.argv[2]}_plan.jpg", type="jpeg", quality=60)
        await b.close()
asyncio.run(main())
