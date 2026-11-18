"""Daily South Africa stays scout (asked 24 Oct 2026: "Yes 2 per day").

Finds the next short-let hosts in South Africa rated 4.5+ with 15+ Google reviews and no website of their own (or a
weak DIY one), skips chains and anyone done before, and prepares a folder per lead for the stays concept:
place.json (Google details and reviews), photos from their own website (as a visitor sees them) plus their Google
photos, their logo if their site has one, their Instagram/Facebook, and a labelled contact sheet for choosing
rooms and video frames. Prices stay the same everywhere (owner, 24 Oct 2026).

Only hosts with an Instagram account are kept (owner, 24 Oct 2026: "only with instagrams, if they don't have don't make it").

Usage: python za_scout.py [count]           -> searches, prepares the folders, prints them as JSON
       python za_scout.py <place id> ...    -> prepares those Google places instead (still Instagram only)
State: za_state.json next to this file (done ids, which search ran last).
"""
import asyncio, json, re, sys
from io import BytesIO
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent.parent))
import httpx  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402
from config import Settings  # noqa: E402

LIVE = Path(r"C:\Users\Thato\kinetic-repo\kinetic-live\m")
WORK = HERE / "leads"
STATE = HERE / "za_state.json"
QUERIES = [
    "guest house Clarens", "self catering Knysna", "guest house Wilderness", "luxury villa Camps Bay", "guest house Hermanus",
    "boutique guesthouse Stellenbosch", "self catering cottage Franschhoek", "guest house Plettenberg Bay", "guest house Umhlanga",
    "self catering Ballito", "boutique guest house Pretoria", "guest house Sandton", "bush lodge Hoedspruit", "guest farm Magaliesberg",
    "guest house Paternoster", "self catering Langebaan", "guest house Mossel Bay", "guest house Dullstroom", "lodge Drakensberg self catering",
    "guest house Port Elizabeth Gqeberha", "guest house East London", "self catering St Lucia", "guest house Montagu", "guest house Robertson",
    "villa Simon's Town", "guest house Muizenberg", "apartment Sea Point short stay", "guest house Parys", "guest house Graaff-Reinet", "lodge Kruger self catering",
]
FIELDS = ("places.id,places.displayName,places.websiteUri,places.rating,places.userRatingCount,places.formattedAddress,"
          "places.photos,places.internationalPhoneNumber,places.googleMapsUri,places.reviews,places.location")
OTA = re.compile(r"airbnb\.|booking\.com|lekkeslaap|facebook|instagram|wa\.me|safarinow|travelground|expedia|tripadvisor|linktr", re.I)
CHAIN = re.compile(r"totalstay|fluentliving|hunterhotels|homesuitehotels|\bslh\b|marriott|protea|tsogo|sun international|"
                   r"city lodge|radisson|hilton|hyatt|southern sun|premier hotel|aha |anew |legacy|staylatitude|singita|londolozi|sabi ?sabi|"
                   r"virginlimitededition|ulusaba|mont rochelle|lion sands|more.co.za|thelastword|last word|dreamresorts|kapama|saxon|"
                   r"andbeyond|&beyond|molori|tintswalo|ellerman|sabisand.co|lefranschhoek|alphen", re.I)
BUILDER = re.compile(r"weebly|wixsite|wix\.com|site123|webnode|jimdo|godaddysites|wordpress\.com|squarespace|yola", re.I)
IG = re.compile(r"instagram\.com/([A-Za-z0-9_.]{2,30})", re.I)
NOT_IG = {"p", "explore", "wix", "accounts", "reel", "reels", "squarespace", "weebly", "wordpress", "stories", "tv", "jimdo", "site123"}
SLUG = lambda s: re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:48]


def state() -> dict:
    return json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {"done": [], "q": 0}


def save_state(s: dict) -> None:
    STATE.write_text(json.dumps(s, indent=1), encoding="utf-8")


def mark_done(place_id: str, slug: str = "") -> None:
    s = state()
    if place_id not in s["done"]:
        s["done"].append(place_id)
    s.setdefault("built", {})[place_id] = slug
    save_state(s)


async def site_kind(h: httpx.AsyncClient, url: str) -> tuple[str, str]:
    if not url or OTA.search(url):
        return "no website", ""
    try:
        r = await h.get(url, follow_redirects=True, timeout=20)
        hit = BUILDER.search(url + r.text[:30000])
        return ("builder site (" + hit.group(0) + ")" if hit else "own site"), r.text
    except Exception:
        return "site down", ""


async def candidates(settings, h, want: int, s: dict) -> list[dict]:
    found = []
    for _ in range(len(QUERIES)):
        q = QUERIES[s["q"] % len(QUERIES)]
        s["q"] += 1
        r = await h.post("https://places.googleapis.com/v1/places:searchText",
                         headers={"X-Goog-Api-Key": settings.google_places_key, "X-Goog-FieldMask": FIELDS},
                         json={"textQuery": q, "maxResultCount": 20, "regionCode": "ZA"})
        for p in r.json().get("places", []):
            name, site = p["displayName"]["text"], p.get("websiteUri", "")
            if p["id"] in s["done"] or CHAIN.search(name + " " + site) or (p.get("rating") or 0) < 4.5 or (p.get("userRatingCount") or 0) < 15:
                continue
            if len(p.get("photos", [])) < 6:
                continue
            ig = instagram_of(site)
            if ig:  # their "website" on Google is their Instagram: no site of their own
                kind, html = "no website (Instagram only)", ""
            else:
                kind, html = await site_kind(h, site)
                if kind == "own site":
                    continue  # a proper site already: not an easy win
                ig = instagram_of(html)
            if not ig:
                continue  # Instagram only (owner, 24 Oct 2026): no Instagram, no concept
            found.append({**p, "q": q, "kind": kind, "html": html, "ig": ig})
            s["done"].append(p["id"])  # never offered twice, even if the build is skipped
            if len(found) >= want:
                return found
    return found


def instagram_of(text: str) -> str:
    """Their own Instagram handle from a link or page, skipping platform accounts (Wix, Squarespace...)."""
    for m in IG.finditer(text or ""):
        if m.group(1).lower().rstrip(".") not in NOT_IG:
            return "@" + m.group(1).rstrip(".")
    return ""


async def by_ids(settings, h, ids: list[str], s: dict) -> list[dict]:
    """Prepare chosen places (from a shortlist) instead of searching. Same Instagram-only rule."""
    out = []
    for pid in ids:
        r = await h.get(f"https://places.googleapis.com/v1/places/{pid}",
                        headers={"X-Goog-Api-Key": settings.google_places_key, "X-Goog-FieldMask": FIELDS.replace("places.", "")})
        p = r.json()
        site = p.get("websiteUri", "")
        ig = instagram_of(site)
        kind, html = ("no website (Instagram only)", "") if ig else await site_kind(h, site)
        ig = ig or instagram_of(html)
        if not ig:
            print("skipped (no Instagram):", p.get("displayName", {}).get("text"), file=sys.stderr)
            continue
        out.append({**p, "q": "chosen", "kind": kind, "html": html, "ig": ig})
        if pid not in s["done"]:
            s["done"].append(pid)
    return out


async def google_photos(settings, h, p: dict, folder: Path, n: int = 10) -> list[str]:
    out = []
    for i, ph in enumerate(p.get("photos", [])[:n]):
        r = await h.get(f"https://places.googleapis.com/v1/{ph['name']}/media", params={"maxWidthPx": 1600, "skipHttpRedirect": "true"},
                        headers={"X-Goog-Api-Key": settings.google_places_key})
        uri = r.json().get("photoUri")
        if not uri:
            continue
        img = Image.open(BytesIO((await h.get(uri, timeout=60)).content)).convert("RGB")
        f = folder / "g" / f"{i:02d}.jpg"; f.parent.mkdir(parents=True, exist_ok=True)
        img.thumbnail((1400, 1400)); img.save(f, quality=82, optimize=True)
        out.append(f"g/{i:02d}.jpg")
    return out


async def site_photos(url: str, folder: Path, limit: int = 80) -> dict:
    """Visit their own website like a guest would (home page and its own links) and keep the real photos."""
    from playwright.async_api import async_playwright
    got = {"photos": [], "logo": "", "pages": {}, "instagram": "", "facebook": ""}
    async with async_playwright() as pw:
        b = await pw.chromium.launch(channel="msedge"); ctx = await b.new_context(viewport={"width": 1400, "height": 900}); pg = await ctx.new_page()
        try:
            await pg.goto(url, wait_until="domcontentloaded", timeout=45000); await pg.wait_for_timeout(4000)
        except Exception:
            await b.close(); return got
        host = re.sub(r"^www\.", "", httpx.URL(pg.url).host)
        links = await pg.evaluate("[...new Set([...document.querySelectorAll('a')].map(a => a.href))]")
        socials = " ".join(links)
        m = re.search(r"instagram\.com/([A-Za-z0-9_.]{2,30})", socials)
        got["instagram"] = "@" + m.group(1) if m and m.group(1).lower() not in ("p", "explore", "wix", "accounts", "reel", "squarespace", "weebly") else ""
        m = re.search(r"https?://(?:www\.)?facebook\.com/[^\s\"']+", socials)
        got["facebook"] = m.group(0) if m and "/wix" not in m.group(0) else ""
        pages = [pg.url] + [l for l in links if host in l and not re.search(r"\.(pdf|jpg|png|docx?)$|#|mailto:|tel:", l)][:12]
        seen = set()
        for u in pages:
            try:
                await pg.goto(u, wait_until="domcontentloaded", timeout=30000); await pg.wait_for_timeout(2500)
                for _ in range(5):
                    await pg.mouse.wheel(0, 2200); await pg.wait_for_timeout(350)
            except Exception:
                continue
            title = (await pg.title())[:80]
            got["pages"][u] = {"title": title, "text": (await pg.evaluate("document.body.innerText"))[:3000]}
            imgs = await pg.evaluate("""() => [...document.querySelectorAll('img')].map(i => ({src: i.currentSrc || i.src, w: i.naturalWidth, h: i.naturalHeight,
                logo: /logo/i.test(i.src + ' ' + i.alt + ' ' + i.className + ' ' + (i.closest('header, .logo, [class*=logo]') ? 'logo' : ''))}))""")
            for im in imgs:
                key = im["src"].split("?")[0]
                if key in seen or not im["src"].startswith("http"):
                    continue
                seen.add(key)
                try:
                    data = await (await ctx.request.get(im["src"])).body()
                    img = Image.open(BytesIO(data))
                except Exception:
                    continue
                if im["logo"] and not got["logo"] and img.width < 1400 and not re.search(r"facebook|instagram|youtube|tripadvisor|twitter|linkedin|whatsapp|tiktok|pinterest|icon", key, re.I):
                    img.save(folder / "logo.png"); got["logo"] = "logo.png"; continue
                if img.width < 500 or img.height < 300 or len(got["photos"]) >= limit:
                    continue
                f = folder / "s" / f"{len(got['photos']):02d}.jpg"; f.parent.mkdir(parents=True, exist_ok=True)
                img = img.convert("RGB"); img.thumbnail((1400, 1400)); img.save(f, quality=82, optimize=True)
                got["photos"].append({"file": f"s/{f.name}", "page": title, "src": key, "w": img.width, "h": img.height})
        await b.close()
    return got


def contact_sheet(folder: Path, files: list[str], out: Path) -> None:
    W, cols = 230, 8
    rows = (len(files) + cols - 1) // cols or 1
    sheet = Image.new("RGB", (W * cols, 165 * rows), "white"); d = ImageDraw.Draw(sheet)
    for i, f in enumerate(files):
        im = Image.open(folder / f); im.thumbnail((W, 155))
        sheet.paste(im, ((i % cols) * W, (i // cols) * 165)); d.text(((i % cols) * W + 3, (i // cols) * 165 + 2), f, fill="red")
    sheet.save(out, quality=70)


async def main(want: int) -> list[dict]:
    settings, s = Settings(), state()
    out = []
    async with httpx.AsyncClient(timeout=40) as h:
        chosen = [a for a in sys.argv[1:] if a.startswith("ChIJ")]
        for p in (await by_ids(settings, h, chosen, s) if chosen else await candidates(settings, h, want, s)):
            name = p["displayName"]["text"]
            slug = SLUG(name)
            folder = LIVE / slug; folder.mkdir(parents=True, exist_ok=True)
            place = {"id": p["id"], "name": name, "rating": p.get("rating"), "reviews": p.get("userRatingCount"),
                     "address": p.get("formattedAddress", ""), "phone": p.get("internationalPhoneNumber", ""),
                     "maps": p.get("googleMapsUri", ""), "website": p.get("websiteUri", ""), "site_kind": p["kind"], "loc": p.get("location"),
                     "quotes": [{"text": (v.get("originalText") or v.get("text") or {}).get("text", ""), "rating": v.get("rating"),
                                 "author": v.get("authorAttribution", {}).get("displayName", "")} for v in p.get("reviews", [])]}
            json.dump(place, open(folder / "place.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
            site = await site_photos(place["website"], folder) if place["website"] and not OTA.search(place["website"]) else {"photos": [], "logo": "", "pages": {}, "instagram": "", "facebook": ""}
            site["instagram"] = p["ig"]
            g = await google_photos(settings, h, p, folder)
            files = [x["file"] for x in site["photos"]] + g
            work = WORK / slug; work.mkdir(parents=True, exist_ok=True)
            contact_sheet(folder, files, work / "sheet.jpg")
            lead = {"slug": slug, "folder": str(folder), "sheet": str(work / "sheet.jpg"), "place": {k: v for k, v in place.items() if k != "quotes"},
                    "photos": files, "site_photos": site["photos"], "logo": site["logo"], "instagram": site["instagram"],
                    "facebook": site["facebook"], "pages": {u: v["title"] for u, v in site["pages"].items()}, "query": p["q"]}
            json.dump({**lead, "page_text": site["pages"]}, open(work / "lead.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
            out.append(lead)
    save_state(s)
    return out


if __name__ == "__main__":
    leads = asyncio.run(main(int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 2))
    print(json.dumps([{"slug": x["slug"], "name": x["place"]["name"], "rating": x["place"]["rating"], "reviews": x["place"]["reviews"],
                       "site": x["place"]["site_kind"], "photos": len(x["photos"]), "logo": bool(x["logo"]), "instagram": x["instagram"],
                       "facebook": x["facebook"], "folder": x["folder"], "sheet": x["sheet"],
                       "lead": str(WORK / x["slug"] / "lead.json")} for x in leads], indent=1, ensure_ascii=False))
