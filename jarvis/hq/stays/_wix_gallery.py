"""All the photos in a Wix site's slideshows: watch the image requests while clicking every 'next' arrow, then
download each one full size into <folder>/r/."""
import asyncio, json, re, sys
from io import BytesIO
from pathlib import Path
from PIL import Image
from playwright.async_api import async_playwright
ID = re.compile(r"static\.wixstatic\.com/media/([0-9a-f]{6}_[0-9a-f]{32}~mv2\.(?:jpe?g|png|webp))", re.I)

async def main(folder, urls):
    ids, order = set(), []
    def seen(u):
        m = ID.search(u)
        if m and m.group(1) not in ids: ids.add(m.group(1)); order.append((m.group(1), cur[0]))
    cur = [""]
    async with async_playwright() as pw:
        b = await pw.chromium.launch(channel="msedge"); ctx = await b.new_context(viewport={"width": 1500, "height": 950}); pg = await ctx.new_page()
        pg.on("request", lambda r: seen(r.url))
        for u in urls:
            cur[0] = u
            await pg.goto(u, wait_until="domcontentloaded", timeout=60000); await pg.wait_for_timeout(4000)
            for _ in range(14):
                await pg.mouse.wheel(0, 900); await pg.wait_for_timeout(400)
            for s in (await pg.content(),): [seen(m.group(0)) for m in ID.finditer(s)]
            nexts = pg.locator("[aria-label*='next' i], [data-hook*='nav-arrow-next'], [data-testid*='next' i]")
            n = await nexts.count()
            for i in range(n):
                el = nexts.nth(i)
                for _ in range(26):
                    try:
                        await el.scroll_into_view_if_needed(timeout=1500); await el.click(timeout=1500); await pg.wait_for_timeout(450)
                    except Exception:
                        break
            print(u, n, "arrows,", len(order), "images so far", file=sys.stderr)
        out = []
        (folder / "r").mkdir(exist_ok=True)
        for mid, page in order:
            try:
                img = Image.open(BytesIO(await (await ctx.request.get("https://static.wixstatic.com/media/" + mid)).body()))
            except Exception:
                continue
            if img.width < 700 or img.height < 400: continue
            f = folder / "r" / f"{len(out):02d}.jpg"
            img = img.convert("RGB"); img.thumbnail((1600, 1600)); img.save(f, quality=84, optimize=True)
            out.append({"file": f"r/{f.name}", "page": page, "src": mid})
        await b.close()
    json.dump(out, open(folder / "r" / "index.json", "w"), indent=1)
    print(len(out), "photos")

asyncio.run(main(Path(sys.argv[1]), sys.argv[2:]))
