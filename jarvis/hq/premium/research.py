"""Deep dive for a premium mock-up: their website (every page's words, real photos, logo, the colours actually used on
screen) and their Google listing (photos, reviews, hours, location, phone), saved into leads/<slug>/ with a contact
sheet, ready for writing config.json by hand. No credits used.

Usage: python research.py <slug> "<Google search text>" [website]"""
import asyncio, json, re, sys
from io import BytesIO
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent / "stays")); sys.path.insert(0, str(HERE.parent.parent))
import httpx  # noqa: E402
from PIL import Image  # noqa: E402
from config import Settings  # noqa: E402
from za_scout import FIELDS, contact_sheet, google_photos  # noqa: E402

COLOURS_JS = """() => { const c = {}; document.querySelectorAll('body *').forEach(e => { const s = getComputedStyle(e), r = e.getBoundingClientRect();
  const area = Math.min(r.width * r.height, 400000); if (!area) return;
  [[s.backgroundColor, area], [s.color, 400]].forEach(([v, w]) => { if (v && !v.includes('rgba(0, 0, 0, 0)')) c[v] = (c[v] || 0) + w; }); });
  return Object.entries(c).sort((a, b) => b[1] - a[1]).slice(0, 16); }"""


async def site(url: str, folder: Path) -> dict:
    from playwright.async_api import async_playwright
    out = {"pages": {}, "photos": [], "logos": [], "colours": []}
    async with async_playwright() as p:
        b = await p.chromium.launch(channel="msedge"); ctx = await b.new_context(viewport={"width": 1400, "height": 900}); pg = await ctx.new_page()
        try:
            await pg.goto(url, wait_until="domcontentloaded", timeout=45000); await pg.wait_for_timeout(5000)
        except Exception as ex:
            await b.close(); out["error"] = str(ex)[:200]; return out
        host = re.sub(r"^www\.", "", httpx.URL(pg.url).host)
        out["colours"] = await pg.evaluate(COLOURS_JS)
        await pg.screenshot(path=str(folder / "their_home.jpg"), type="jpeg", quality=55)
        logos = await pg.evaluate("[...document.querySelectorAll('header img, nav img, [class*=logo] img, img[class*=logo], img[alt*=ogo i], img[src*=ogo i]')].map(i => i.currentSrc || i.src)")
        links = await pg.evaluate("[...new Set([...document.querySelectorAll('a')].map(a => a.href.split('#')[0]))]")
        pages = [pg.url] + [l for l in links if host in l and not re.search(r"\.(pdf|jpe?g|png|webp)$|mailto:|tel:|cart|checkout|account|privacy|cookie|terms|login", l, re.I)][:14]
        seen = set()
        for u in dict.fromkeys(pages):
            try:
                await pg.goto(u, wait_until="domcontentloaded", timeout=30000); await pg.wait_for_timeout(2500)
                for _ in range(8):
                    await pg.mouse.wheel(0, 1600); await pg.wait_for_timeout(250)
            except Exception:
                continue
            out["pages"][u] = re.sub(r"\s+", " ", await pg.evaluate("document.body.innerText"))[:6000]
            srcs = await pg.evaluate("""() => { const s = new Set(); document.querySelectorAll('img').forEach(i => { s.add(i.currentSrc || i.src); });
              document.querySelectorAll('*').forEach(e => { const m = getComputedStyle(e).backgroundImage.match(/url\\(["']?([^"')]+)/); m && s.add(m[1]); });
              return [...s].filter(x => x && x.startsWith('http')); }""")
            for src in srcs:
                key = src.split("?")[0]
                if key in seen or len(out["photos"]) >= 60:
                    continue
                seen.add(key)
                try:
                    im = Image.open(BytesIO(await (await ctx.request.get(src)).body()))
                except Exception:
                    continue
                if im.width < 600 or im.height < 380:
                    continue
                f = folder / "s" / f"{len(out['photos']):02d}.jpg"; f.parent.mkdir(exist_ok=True)
                im = im.convert("RGB"); im.thumbnail((1800, 1800)); im.save(f, quality=84)
                out["photos"].append(f"s/{f.name}")
        for i, u in enumerate(dict.fromkeys(logos)):
            try:
                data = await (await ctx.request.get(u)).body()
                ext = "svg" if u.lower().split("?")[0].endswith(".svg") or data[:5] in (b"<?xml", b"<svg ") else "png"
                if ext == "png":
                    Image.open(BytesIO(data)).save(folder / f"logo{i}.png")
                else:
                    (folder / f"logo{i}.svg").write_bytes(data)
                out["logos"].append(f"logo{i}.{ext}")
            except Exception:
                pass
        await b.close()
    return out


async def main(slug: str, query: str, url: str = "") -> None:
    s = Settings(); folder = HERE / "leads" / slug; folder.mkdir(parents=True, exist_ok=True)
    async with httpx.AsyncClient(timeout=40) as h:
        r = await h.post("https://places.googleapis.com/v1/places:searchText",
                         headers={"X-Goog-Api-Key": s.google_places_key, "X-Goog-FieldMask": FIELDS + ",places.regularOpeningHours,places.nationalPhoneNumber"},
                         json={"textQuery": query, "maxResultCount": 1})
        place = r.json()["places"][0]
        json.dump(place, open(folder / "place.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
        g = await google_photos(s, h, place, folder, 10)
    url = url or place.get("websiteUri", "")
    info = await site(url, folder) if url and "instagram" not in url else {"pages": {}, "photos": [], "logos": [], "colours": []}
    json.dump(info, open(folder / "site.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    contact_sheet(folder, info["photos"] + g, folder / "sheet.jpg")
    print(json.dumps({"slug": slug, "name": place["displayName"]["text"], "rating": place.get("rating"), "reviews": place.get("userRatingCount"),
                      "site": url, "site_photos": len(info["photos"]), "google": len(g), "logos": info["logos"], "colours": info["colours"][:8],
                      "pages": list(info["pages"])[:15], "error": info.get("error")}, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main(*sys.argv[1:]))
