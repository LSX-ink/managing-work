"""Grab the real photos from chosen pages of their site (img tags and CSS backgrounds) into <folder>/r/."""
import asyncio, json, sys
from io import BytesIO
from pathlib import Path
from PIL import Image
from playwright.async_api import async_playwright

async def main(folder, urls):
    out, seen = [], set()
    (folder / "r").mkdir(exist_ok=True)
    async with async_playwright() as pw:
        b = await pw.chromium.launch(channel="msedge"); ctx = await b.new_context(viewport={"width": 1400, "height": 900}); pg = await ctx.new_page()
        for u in urls:
            await pg.goto(u, wait_until="domcontentloaded", timeout=45000); await pg.wait_for_timeout(3000)
            for _ in range(10):
                await pg.mouse.wheel(0, 1500); await pg.wait_for_timeout(300)
            srcs = await pg.evaluate("""() => { const s = new Set();
              document.querySelectorAll('img').forEach(i => { s.add(i.currentSrc || i.src); (i.srcset||'').split(',').forEach(x => x.trim() && s.add(x.trim().split(' ')[0])); (i.dataset.src) && s.add(i.dataset.src); });
              document.querySelectorAll('*').forEach(e => { const m = getComputedStyle(e).backgroundImage.match(/url\(["']?([^"')]+)/); m && s.add(m[1]); });
              document.querySelectorAll('a[href$=".jpg"],a[href$=".jpeg"],a[href$=".webp"]').forEach(a => s.add(a.href));
              return [...s].filter(x => x && x.startsWith('http')); }""")
            for src in srcs:
                key = src.split("?")[0]
                if key in seen: continue
                seen.add(key)
                try:
                    img = Image.open(BytesIO(await (await ctx.request.get(src)).body()))
                except Exception:
                    continue
                if img.width < 700 or img.height < 400: continue
                f = folder / "r" / f"{len(out):02d}.jpg"
                img = img.convert("RGB"); img.thumbnail((1600, 1600)); img.save(f, quality=84, optimize=True)
                out.append({"file": f"r/{f.name}", "page": u, "src": key})
        await b.close()
    json.dump(out, open(folder / "r" / "index.json", "w"), indent=1)
    print(len(out), "photos")

asyncio.run(main(Path(sys.argv[1]), sys.argv[2:]))
