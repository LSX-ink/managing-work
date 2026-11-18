"""Iris, the designer: makes each lead's mock-up as convincing as it can honestly be, then checks it before anyone sees it.

The owner (23 Oct 2026): "create a bot that creates and checks the mock ups to perfection" and "make sure the mock
has maximum information that will compel them". So every mock-up gets, where Google has it:
- the shop's own photos, opening hours and three real customer reviews (Google Places; the key only ever goes in a
  request header, never in a page, a link or a log)
- what their current site gets wrong today, side by side with how this design fixes it (from our audit and
  Google PageSpeed), or, with no website, what they lose by not having one
Then Iris checks it in a real browser on a phone and a laptop (nothing cut off, every photo loads, their name and
number are right, no placeholder words), and the free AI reads it as a fussy shop owner. Anything wrong: rebuilt
without the part that failed; still wrong: held back and logged, never sent.
"""

import asyncio
import json
import re
from html import unescape
from pathlib import Path

import kinetic_find as kf
from hq import mockup

PLACE = "https://places.googleapis.com/v1/places/{}"
PHOTO = "https://places.googleapis.com/v1/{}/media"
FIELDS = "regularOpeningHours.weekdayDescriptions,photos,reviews"
PLACEHOLDER = re.compile(r"(?i:lorem|ipsum|placeholder|swap this|your (business|happy customer)|tell customers what|"
                         r"\bundefined\b|\[[^\]]{2,40}\]|\btodo\b|xxx)|\bNaN\b|\bNone\b")

FIX_RULES = [  # (words in our audit's problem, what this design does instead)
    (r"slow|pagespeed|heavy", "Built light, so it opens in about a second on a phone."),
    (r"tap|call|phone number", "One tap to call you, on every page."),
    (r"share preview|preview card|og:|social share", "A proper preview card when your link is shared on WhatsApp or Instagram."),
    (r"\bbook(ing)?\b", "A booking button front and centre, so a visitor becomes a customer in two taps."),
    (r"mobile|phone-friendly|viewport|small screen", "Designed for phones first, where most of your customers look."),
    (r"google|business details|structured|search", "Set up so Google shows your hours, rating and location properly."),
    (r"secure|https|ssl|not secure", "Secure (https), so browsers never warn customers away."),
    (r"copyright|outdated|old|dated", "A fresh, modern look that shows you're open, busy and worth the visit."),
    (r"price", "Prices shown clearly, so people stop asking and start booking."),
    (r"hours|opening", "Opening hours on the page, always up to date."),
]
NO_SITE_FIXES = [
    ("When people Google you, there's no website to land on.", "A home page that shows your work, prices and reviews."),
    ("Customers have to message or call to ask the basics.", "Hours, services and directions answered before they ask."),
    ("New customers can only judge you by a map pin.", "Your photos and your Google rating front and centre."),
    ("No easy way to book.", "One tap to call or book, from any phone."),
]


def fixes_for(p: dict, audit: dict | None) -> tuple[list[tuple[str, str]], str]:
    if not p.get("website") or kf.social_only(p):
        return NO_SITE_FIXES, "What a website would change for you."
    out, used = [], set()
    host = re.sub(r"^https?://(www\.)?", "", p["website"]).split("/")[0]
    for prob in (audit or {}).get("problems") or []:
        text = f"{prob.get('problem', '')} {prob.get('why', '')}"
        for i, (pattern, fix) in enumerate(FIX_RULES):
            if i not in used and re.search(pattern, text, re.I):
                used.add(i)
                out.append((f"{prob['problem'].rstrip('.')}.", fix))
                break
    return out[:5], f"What {host} is costing you, and what this fixes."


async def enrich(ctx, p: dict, folder: Path) -> dict:
    """Real extras for the mock-up, cached in the brain: photos (saved next to the page), hours, reviews, fixes."""
    b, s, http = ctx.brain, ctx.settings, ctx.http
    key = f"design.{p['id']}"
    extra = b.get(key) or {}
    if not extra:
        if s.google_places_key and p.get("google"):
            try:
                r = await http.get(PLACE.format(p["google"]), timeout=30,
                                   headers={"X-Goog-Api-Key": s.google_places_key, "X-Goog-FieldMask": FIELDS})
                r.raise_for_status()
                d = r.json()
                extra["hours"] = (d.get("regularOpeningHours") or {}).get("weekdayDescriptions") or []
                extra["reviews"] = [{"author": ((x.get("authorAttribution") or {}).get("displayName") or "").split(" ")[0],
                                     "text": ((x.get("originalText") or x.get("text") or {}).get("text") or "").strip(),
                                     "rating": x.get("rating") or 5}
                                    for x in d.get("reviews") or [] if (x.get("rating") or 0) >= 4][:3]
                extra["photo_names"] = [x["name"] for x in (d.get("photos") or [])[:4] if x.get("name")]
            except Exception as e:
                b.log("designer", f"Google had no extra details for {p['name']} ({type(e).__name__})", "info")
        audit = p.get("audit")
        if p.get("website") and not audit:
            try:
                audit = await kf.with_pagespeed(s, http, await asyncio.wait_for(kf.audit_url(http, p["website"]), 45))
            except Exception:
                audit = None
        extra["fixes"], extra["fixes_title"] = fixes_for(p, audit)
        if p.get("website") and not kf.social_only(p):
            extra["speed"] = await kf.pagespeed(s, http, p["website"])  # Google's own phone score, or None
        b.set(key, extra)
    folder.mkdir(parents=True, exist_ok=True)
    photos = []
    for i, name in enumerate(extra.get("photo_names") or []):
        file = folder / f"photo-{i + 1}.jpg"
        if not file.exists():
            try:
                r = await http.get(PHOTO.format(name), params={"maxWidthPx": 1400}, timeout=40,
                                   headers={"X-Goog-Api-Key": s.google_places_key})
                if r.status_code == 200 and r.headers.get("content-type", "").startswith("image/"):
                    file.write_bytes(r.content)
                    slim(file)
            except Exception:
                pass
        if file.exists() and file.stat().st_size > 300_000:
            slim(file)
        if file.exists() and file.stat().st_size > 5000:
            photos.append(file.name)
    before = folder / "before.jpg"
    if not before.exists():  # every mock-up gets the before/after (owner, 23 Oct 2026: "add to one, add to all")
        try:
            if p.get("website") and not kf.social_only(p):
                await shoot(p["website"], before)
            else:  # no website: "before" is what people find today, a map pin and nothing to click
                card = folder / "_before.html"
                card.write_text(no_site_card(p), encoding="utf-8")
                await shoot(card.as_uri(), before)
                card.unlink()
        except Exception:
            pass
    brand = b.get(f"brand.{p['id']}")
    if brand is None or (p.get("website") and "nav" not in brand):  # v6 reads their layout too: redo older brands  # their own look: colours from their site (or their shop photo), fonts and logo from the site
        brand = {}
        has_site = p.get("website") and not kf.social_only(p)
        if has_site:
            brand.update(await brand_from_site(http, p["website"], folder))
            try:
                c = await site_colours(p["website"])
                if c:
                    accent = c["accent"]
                    if _saturation(accent) < 0.18:  # grey buttons: take the colour from their logo or shop instead
                        for pic in [folder / brand.get("logo", "-"), before, *(folder / x for x in photos)]:
                            vivid = vivid_colour(pic) if pic.suffix in (".png", ".jpg", ".webp") and pic.exists() else None
                            if vivid:
                                accent = vivid
                                break
                        else:
                            accent = tuple(int(mockup.TRADES[mockup.trade_for(p)][0][2][i:i + 2], 16) for i in (1, 3, 5))
                    brand.update(finish_palette(c["bg"], accent))
                    # their layout: headline, menu, hero picture and fonts, so it reads as their site, upgraded
                    h1 = re.sub(r"\s+", " ", c.get("h1") or "").strip()
                    section_words = r"\b(about|gallery|contact|why us|our team|services|welcome|home|menu|book now)\b"
                    if 8 <= len(h1) <= 70 and len(h1.split()) >= 2 and not re.search(section_words, h1, re.I):
                        brand["h1"] = h1
                    seen, nav = set(), []
                    for n in c.get("nav") or []:
                        if n.lower() in seen or re.search(r"\b(home|menu|close|skip|cart|basket|shop|log ?in|account|view)\b", n, re.I):
                            continue
                        seen.add(n.lower())
                        nav.append(n.title() if n.isupper() else n)
                    brand["nav"] = nav[:5]
                    if c.get("fonts") and not brand.get("fonts"):
                        brand["fonts"] = c["fonts"][:2]
                    if c.get("hero"):
                        try:
                            from urllib.parse import urljoin
                            got = await http.get(urljoin(p["website"], c["hero"]), timeout=25,
                                                 headers={"User-Agent": "Mozilla/5.0"})
                            if got.status_code == 200 and got.headers.get("content-type", "").startswith("image/") \
                                    and len(got.content) > 15_000:
                                (folder / "hero.jpg").write_bytes(got.content)
                                slim(folder / "hero.jpg", 1600)
                                brand["hero"] = "hero.jpg"
                        except Exception:
                            pass
            except Exception:
                pass
        source = folder / photos[0] if photos else None
        if "bg" not in brand and source and source.exists():  # no site to read: their shop photo gives the accent
            try:
                brand.update(palette_from(source, mockup.TRADES[mockup.trade_for(p)][0][0]))
            except Exception:
                pass
        b.set(f"brand.{p['id']}", brand)
    if brand.get("logo") and not (folder / brand["logo"]).exists():
        brand = {k: v for k, v in brand.items() if k != "logo"}
    if brand.get("logo", "").endswith((".png", ".webp", ".jpg")) and brand.get("bg"):
        try:  # a white logo on a light page (or dark on dark) sits on a pill in their brand colour instead
            from PIL import Image, ImageStat
            with Image.open(folder / brand["logo"]) as im:
                rgba = im.convert("RGBA")
                lum = ImageStat.Stat(rgba.convert("L"), mask=rgba.split()[3].point(lambda a: 255 if a > 128 else 0)).mean[0]
            bg_lum = _lum(tuple(int(brand["bg"][i:i + 2], 16) for i in (1, 3, 5))) * 255
            if abs(lum - bg_lum) < 90:
                brand = {**brand, "logo_pill": True}
        except Exception:
            pass
    design_speed = b.get("design.template_speed")
    speed = extra.get("speed")
    if isinstance(speed, int) and speed >= 70 and len(extra.get("fixes") or []) <= 1:
        b.set(f"strong_site.{p['id']}", True)  # their site is already decent: Blade puts them last
    return {**extra, "photos": photos, "brand": brand, "before": before.name if before.exists() else "",
            "design_speed": design_speed if isinstance(design_speed, int) else None}


PHONE = {"width": 390, "height": 760}


def _lum(rgb) -> float:
    def ch(c):
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = rgb
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def _contrast(a, b) -> float:
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def _hex(rgb) -> str:
    return "#%02x%02x%02x" % tuple(int(x) for x in rgb)


def palette_from(image: Path, keep_bg: str | None = None) -> dict:
    """Their colours from a picture of their site (or their own photo): the main background, the boldest brand
    colour, text that reads on both. Adjusted so text and buttons always have enough contrast."""
    import colorsys
    from PIL import Image
    with Image.open(image) as im:
        small = im.convert("RGB").resize((120, 220))
        counts = small.quantize(colors=10, method=Image.Quantize.MEDIANCUT).convert("RGB").getcolors(120 * 220)
    counts = sorted(counts or [], reverse=True)
    if not counts:
        return {}
    bg = counts[0][1] if not keep_bg else tuple(int(keep_bg[i:i + 2], 16) for i in (1, 3, 5))

    def vivid(item):
        n, rgb = item
        h, l, s = colorsys.rgb_to_hls(*(c / 255 for c in rgb))
        return s * (0.25 + min(l, 1 - l)) * (n ** 0.5)
    options = [c for c in counts if _contrast(c[1], bg) > 1.6]
    accent = max(options, key=vivid)[1] if options else (201, 162, 77)
    h, l, s = colorsys.rgb_to_hls(*(c / 255 for c in accent))
    for _ in range(12):  # push the accent lighter or darker until it stands out from the background
        if _contrast(accent, bg) >= 3:
            break
        l = min(0.92, l + 0.06) if _lum(bg) < 0.4 else max(0.12, l - 0.06)
        accent = tuple(round(c * 255) for c in colorsys.hls_to_rgb(h, l, s))
    ink = (245, 241, 234) if _lum(bg) < 0.4 else (24, 22, 20)
    on = (17, 17, 17) if _contrast((17, 17, 17), accent) >= _contrast((255, 255, 255), accent) else (255, 255, 255)
    soft = tuple(round(b * 0.92 + i * 0.08) for b, i in zip(bg, ink))
    return {"bg": _hex(bg), "ink": _hex(ink), "accent": _hex(accent), "soft": _hex(soft), "on_accent": _hex(on)}


COLOURS_JS = """() => {
  const rgb = s => { const m = s && s.match(/rgba?\\(([^)]+)\\)/); if (!m) return null;
    const v = m[1].split(',').map(x => parseFloat(x)); return (v.length > 3 && v[3] < 0.5) ? null : v.slice(0, 3).map(Math.round); };
  const area = {}, accents = {};
  const add = (bag, c, w) => { if (c) { const k = c.join(','); bag[k] = (bag[k] || 0) + w; } };
  [...document.querySelectorAll('body, body *')].slice(0, 2500).forEach(el => {
    const r = el.getBoundingClientRect(); if (r.width < 2 || r.height < 2) return;
    const st = getComputedStyle(el), w = Math.min(r.width * r.height, 2e6);
    add(area, rgb(st.backgroundColor), w);
    if (el.matches('a, button, .btn, [class*=button], [class*=btn]')) { add(accents, rgb(st.backgroundColor), 4); add(accents, rgb(st.color), 2); }
    if (el.matches('h1, h2, h3, .logo, [class*=logo]')) add(accents, rgb(st.color), 3);
    if (parseFloat(st.borderTopWidth) > 1) add(accents, rgb(st.borderTopColor), 1);
  });
  // their layout cues (owner, 23 Oct 2026: "closer to their current but better")
  const fam = el => el ? getComputedStyle(el).fontFamily.split(',')[0].replace(/["']/g, '').trim() : '';
  const h1 = document.querySelector('h1');
  const navs = [...document.querySelectorAll('header a, nav a')].map(a => a.innerText.trim())
    .filter(t => t && t.length < 22 && !/^(\\+|0\\d|http)/.test(t));
  let hero = '', best = 0;
  [...document.querySelectorAll('img, header, section, div')].slice(0, 1500).forEach(el => {
    const r = el.getBoundingClientRect(); if (r.top > 700 || r.width < 500 || r.height < 250) return;
    let src = el.tagName === 'IMG' ? (el.currentSrc || el.src) : '';
    if (!src) { const m = getComputedStyle(el).backgroundImage.match(/url\\(["']?([^"')]+)/); src = m ? m[1] : ''; }
    if (src && !src.startsWith('data:') && !/\\.svg/i.test(src) && r.width * r.height > best) { best = r.width * r.height; hero = src; }
  });
  return {area, accents, body: rgb(getComputedStyle(document.body).backgroundColor),
          h1: h1 ? h1.innerText.trim().replace(/\\s+/g, ' ') : '', nav: [...new Set(navs)].slice(0, 6),
          head_font: fam(h1 || document.querySelector('h2')), body_font: fam(document.body), hero,
          dark_hero: (() => { const el = document.elementFromPoint(innerWidth / 2, 200); return el ? (rgb(getComputedStyle(el).color) || [0,0,0]).reduce((a, b) => a + b) > 500 : false })()};
}"""


async def site_colours(url: str) -> dict:
    """Their brand colours from their live site's own styles (not the photos on it): the background that covers most
    of the page and the boldest colour on their buttons, links and headings."""
    import colorsys
    from playwright.async_api import async_playwright
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(channel="msedge")
        try:
            pg = await browser.new_page(viewport={"width": 1280, "height": 900})
            await pg.goto(url, wait_until="load", timeout=45000)
            await pg.wait_for_timeout(2000)
            got = await pg.evaluate(COLOURS_JS)
        finally:
            await browser.close()
    area = sorted(((w, tuple(map(int, k.split(",")))) for k, w in got["area"].items()), reverse=True)
    if not area:
        return {}
    bg = area[0][1]

    def sat(rgb):
        h, l, s = colorsys.rgb_to_hls(*(c / 255 for c in rgb))
        return s * min(l, 1 - l) * 2

    cands = [(w, tuple(map(int, k.split(",")))) for k, w in got["accents"].items()]
    cands += [(w / 8000, c) for w, c in area[1:6]]  # big coloured bands (a green header, a gold strip) count most
    cands = [(w, c) for w, c in cands if c not in ((0, 0, 238), (85, 26, 139), (0, 102, 204), (30, 111, 245))]  # browser-default link blues
    cands = [(w * (0.15 + sat(c)), c) for w, c in cands if _contrast(c, bg) > 1.5]
    if not cands:
        return {}
    accent = max(cands)[1]
    generic = {"serif", "sans-serif", "system-ui", "-apple-system", "arial", "helvetica", "times new roman", "inherit", ""}
    fonts = [f for f in (got.get("head_font"), got.get("body_font")) if f and f.lower() not in generic]
    return {"bg": bg, "accent": accent, "h1": got.get("h1") or "", "nav": got.get("nav") or [], "hero": got.get("hero") or "",
            "fonts": list(dict.fromkeys(fonts))}


def _saturation(rgb) -> float:
    import colorsys
    h, l, s = colorsys.rgb_to_hls(*(c / 255 for c in rgb))
    return s * min(l, 1 - l) * 2


def vivid_colour(image: Path):
    """The strongest real colour in a picture (a logo's gold, a shop sign's red), or None if it's all greys."""
    from PIL import Image
    with Image.open(image) as im:
        im = im.convert("RGBA").resize((96, 96))
        px = [(r, g, b) for r, g, b, a in im.getdata() if a > 128]
    if not px:
        return None
    small = Image.new("RGB", (len(px), 1))
    small.putdata(px)
    counts = small.quantize(colors=8, method=Image.Quantize.MEDIANCUT).convert("RGB").getcolors(len(px)) or []
    best = max(counts, key=lambda c: _saturation(c[1]) * (c[0] ** 0.5), default=None)
    return best[1] if best and _saturation(best[1]) >= 0.25 else None


def finish_palette(bg, accent) -> dict:
    """Text, soft panels and button text that read on their colours, with the accent nudged until it stands out."""
    import colorsys
    h, l, s = colorsys.rgb_to_hls(*(c / 255 for c in accent))
    for _ in range(12):
        if _contrast(accent, bg) >= 3:
            break
        l = min(0.92, l + 0.06) if _lum(bg) < 0.4 else max(0.12, l - 0.06)
        accent = tuple(round(c * 255) for c in colorsys.hls_to_rgb(h, l, s))
    ink = (245, 241, 234) if _lum(bg) < 0.4 else (24, 22, 20)
    on = (17, 17, 17) if _contrast((17, 17, 17), accent) >= _contrast((255, 255, 255), accent) else (255, 255, 255)
    soft = tuple(round(b * 0.92 + i * 0.08) for b, i in zip(bg, ink))
    return {"bg": _hex(bg), "ink": _hex(ink), "accent": _hex(accent), "soft": _hex(soft), "on_accent": _hex(on)}


GOOGLE_FONT = re.compile(r"fonts\.googleapis\.com/css2?\?family=([^\"'&>]+)", re.I)
LOGO_IMG = re.compile(r"<img[^>]+>", re.I)


async def brand_from_site(http, site: str, folder: Path) -> dict:
    """Fonts (Google Fonts they load) and their logo, read off their own website. The logo is saved next to the page."""
    try:
        r = await http.get(site, timeout=25, headers={"User-Agent": "Mozilla/5.0"})
        html = r.text
    except Exception:
        return {}
    fonts = []
    for m in GOOGLE_FONT.findall(html):
        for fam in re.split(r"\|", m.replace("+", " ")):
            fam = re.sub(r"[:%].*", "", fam).strip()
            if fam and fam not in fonts and re.fullmatch(r"[A-Za-z0-9 ]{2,40}", fam):
                fonts.append(fam)
    logo_url = ""
    for tag in LOGO_IMG.findall(html):
        if re.search(r"logo", tag, re.I):
            m = re.search(r"""(?:data-src|src)=["']([^"']+)""", tag)
            if m and not m.group(1).startswith("data:"):
                logo_url = m.group(1)
                break
    out = {"fonts": fonts[:2]}
    if logo_url:
        from urllib.parse import urljoin
        try:
            got = await http.get(urljoin(str(r.url), logo_url), timeout=20, headers={"User-Agent": "Mozilla/5.0"})
            kind = got.headers.get("content-type", "")
            ext = ".svg" if "svg" in kind else ".png" if "png" in kind else ".webp" if "webp" in kind else \
                ".jpg" if "jpeg" in kind or "jpg" in kind else ""
            if got.status_code == 200 and ext and 300 < len(got.content) < 800_000:
                (folder / f"logo{ext}").write_bytes(got.content)
                out["logo"] = f"logo{ext}"
        except Exception:
            pass
    return out


def no_site_card(p: dict) -> str:
    """The "before" for a business with no website: a plain phone screen of what a search finds today."""
    from html import escape as e
    name, town = mockup.clean_name(p), str(p.get("town") or "")
    stars = f"{float(p['rating']):.1f} ★ ({int(p.get('reviews') or 0):,})" if p.get("rating") else ""
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<style>body{{margin:0;font:15px/1.4 Arial,sans-serif;background:#f1f3f4;color:#202124}}
.bar{{background:#fff;padding:14px 16px;border-bottom:1px solid #ddd;font-size:16px;color:#5f6368}}
.box{{background:#fff;margin:12px;border-radius:12px;padding:16px;box-shadow:0 1px 3px rgba(0,0,0,.15)}}
.map{{height:150px;border-radius:10px;background:repeating-linear-gradient(45deg,#e8eaed 0 12px,#dfe1e5 12px 24px);
display:grid;place-items:center;font-size:34px}}h2{{font-size:20px;margin:12px 0 4px}}.s{{color:#5f6368}}
.btns{{display:flex;gap:8px;margin-top:14px}}.btns span{{flex:1;text-align:center;border:1px solid #dadce0;border-radius:18px;
padding:8px 0;color:#1a73e8}}.btns .no{{color:#bbb;border-style:dashed}}.note{{margin:18px 14px;padding:14px;border-radius:10px;
background:#fde8e8;color:#a52a2a;font-weight:bold;text-align:center}}</style></head><body>
<div class="bar">{e(name)} {e(town)}</div><div class="box"><div class="map">\U0001F4CD</div><h2>{e(name)}</h2>
<div class="s">{e(stars)} &middot; {e(p.get('kind') or 'Local business')}</div><div class="s">{e(p.get('address') or town)}</div>
<div class="btns"><span>Directions</span><span>Call</span><span class="no">No website</span></div></div>
<div class="note">No website: no prices, no photos of your work, no booking.</div></body></html>"""


def slim(file: Path, width: int = 960) -> None:
    """Shrink a photo so the page stays fast on phones (the speed score is part of the pitch)."""
    from PIL import Image
    with Image.open(file) as im:
        im = im.convert("RGB")
        if im.width > width:
            im = im.resize((width, round(im.height * width / im.width)))
        im.save(file, "JPEG", quality=72, optimize=True, progressive=True)


async def shoot(url: str, out: Path) -> None:
    """The top of a page as it looks on a phone, as a JPEG (their current site, or our design)."""
    from playwright.async_api import async_playwright
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(channel="msedge")
        try:
            pg = await browser.new_page(viewport=PHONE, device_scale_factor=2, is_mobile=True)
            await pg.goto(url, wait_until="load", timeout=45000)
            await pg.wait_for_timeout(2500)
            await pg.screenshot(path=str(out), type="jpeg", quality=78)
            slim(out, 600)
        finally:
            await browser.close()


FPS, SECONDS = 15, 18


async def film(page: Path) -> None:
    """An 18-second, silent, phone-shaped video of the mock-up scrolling, saved next to it as preview.mp4. Free: frames
    from the browser joined by ffmpeg on this PC, no voice or video credits."""
    import subprocess
    import tempfile
    from playwright.async_api import async_playwright
    from tiktokstudio_video import ffmpeg
    with tempfile.TemporaryDirectory(prefix="iris-video-") as tmp:
        frames = FPS * SECONDS
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(channel="msedge")
            try:
                pg = await browser.new_page(viewport={"width": 405, "height": 720}, device_scale_factor=2, is_mobile=True)
                await pg.goto(page.as_uri(), wait_until="networkidle")
                await pg.evaluate("[...document.images].forEach(i => i.loading = 'eager')")
                await pg.wait_for_timeout(1800)
                tall = await pg.evaluate("document.documentElement.scrollHeight - innerHeight")
                hold = FPS * 2  # still at the top, then a smooth scroll, then still at the bottom
                for i in range(frames):
                    t = min(1, max(0, (i - hold) / max(1, frames - 2 * hold)))
                    ease = t * t * (3 - 2 * t)
                    await pg.evaluate(f"window.scrollTo(0, {round(tall * ease)})")
                    await pg.screenshot(path=f"{tmp}/f{i:04d}.jpg", type="jpeg", quality=82)
            finally:
                await browser.close()
        r = await asyncio.to_thread(subprocess.run, [
            ffmpeg(), "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", f"{tmp}/f%04d.jpg",
            "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,format=yuv420p",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "24", "-movflags", "+faststart",
            str(page.parent / "preview.mp4")], capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode != 0:
            raise RuntimeError(r.stderr[-160:])


async def check(ctx, p: dict, page: Path) -> list[str]:
    """Iris's checks in a real browser, on a phone and a laptop. [] means it passed."""
    from playwright.async_api import async_playwright
    html = unescape(page.read_text(encoding="utf-8"))
    name = mockup.clean_name(p)
    problems = []
    if name.lower() not in html.lower():
        problems.append("their name is missing")
    if p.get("phone") and re.sub(r"\D", "", p["phone"])[-6:] not in re.sub(r"\D", "", html):
        problems.append("their phone number is missing")
    visible = ""
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(channel="msedge")
        try:
            for label, vp in (("phone", {"width": 390, "height": 844}), ("laptop", {"width": 1440, "height": 900})):
                pg = await browser.new_page(viewport=vp)
                errors = []
                pg.on("pageerror", lambda e: errors.append(str(e)))
                await pg.goto(page.as_uri(), wait_until="networkidle", timeout=45000)
                await pg.evaluate("""async () => {
                    document.querySelectorAll('.reveal').forEach(e => e.classList.add('in'));
                    const imgs = [...document.images]; imgs.forEach(i => i.loading = 'eager');
                    await Promise.all(imgs.map(i => i.complete ? 0 : new Promise(r => { i.onload = i.onerror = r; })));
                }""")
                await pg.wait_for_timeout(800)
                state = await pg.evaluate("""() => ({
                    wide: document.documentElement.scrollWidth > innerWidth + 2,
                    broken: [...document.images].filter(i => !i.complete || i.naturalWidth === 0).length,
                    h1: (() => { const r = document.querySelector('h1').getBoundingClientRect(); return r.width > 40 && r.height > 20 })(),
                    text: document.body.innerText })""")
                if state["wide"]:
                    problems.append(f"something sticks out sideways on a {label}")
                if state["broken"]:
                    problems.append(f"{state['broken']} photo(s) don't load on a {label}")
                if not state["h1"]:
                    problems.append(f"the headline isn't showing on a {label}")
                if errors:
                    problems.append(f"a script error on a {label}")
                visible = state["text"]
                await pg.close()
        finally:
            await browser.close()
    bad = PLACEHOLDER.search(visible)
    if bad:
        problems.append(f"placeholder-looking words: '{bad.group(0)}'")
    return problems


async def critique(ctx, p: dict, page: Path) -> str:
    """The free AI reads the page as the shop owner would. "" = approved, else the reason."""
    text = re.sub(r"<[^>]+>", " ", re.sub(r"(?s)<(style|script)\b.*?</\1>", "", page.read_text(encoding="utf-8")))
    text = re.sub(r"\s+", " ", text)[:6000]
    prompt = (f"You are the owner of {p['name']}, a {p.get('kind') or 'local business'} in {p.get('town') or 'the UK'}. "
              "A web designer made you this free concept home page (its text is below). Judge it strictly: is anything "
              "wrong, made up, embarrassing, generic, placeholder-like, or the wrong services for your trade? Reviews, "
              "rating, hours and photos come from your own Google listing, so they are real. The section headed 'A note for "
              "... from Kinetic Web Designs' is meant for you, the owner: it compares your current site with this design, "
              "so judge whether it's accurate and persuasive, not whether it belongs on a home page. Answer with JSON only: "
              '{"verdict": "APPROVE" or "FIX", "reason": "one short sentence"}.\n\nPAGE TEXT:\n' + text)
    try:
        raw = await ctx.ask_ai(prompt, 300)
        m = re.search(r"\{.*\}", raw, re.S)
        got = json.loads(m.group(0)) if m else {}
        return "" if str(got.get("verdict", "")).upper().startswith("APPROVE") else (got.get("reason") or "no clear verdict")
    except Exception:
        return ""  # the free AI being down never blocks a mock-up that passed the browser checks


async def build(ctx, p: dict, site_folder: Path, maker: str) -> tuple[bool, list[str]]:
    """Make, check and (if needed) rebuild the mock-up in site_folder/index.html. (passed, problems)."""
    extra = await enrich(ctx, p, site_folder)
    attempts = [extra, {**extra, "photos": [], "before": ""},
                {"fixes": extra.get("fixes"), "fixes_title": extra.get("fixes_title")}]
    problems: list[str] = []
    page = site_folder / "index.html"
    before = page.read_bytes() if page.exists() else None  # put back if nothing passes, so a link never breaks
    for i, ex in enumerate(attempts):
        after = site_folder / "after.jpg"
        if ex.get("before"):  # the "after" picture is our own design on a phone: shoot it, then add the slider
            page.write_text(mockup.html_for(p, maker, {**ex, "before": ""}), encoding="utf-8")
            try:
                await shoot(page.as_uri(), after)
                ex = {**ex, "after": after.name}
            except Exception:
                pass
        page.write_text(mockup.html_for(p, maker, ex), encoding="utf-8")
        problems = await check(ctx, p, page)
        if not problems:
            if ctx.brain.get("settings.mockup_video", False) and not (site_folder / "preview.mp4").exists():  # off: owner, 23 Oct
                try:
                    await film(page)
                except Exception as e:
                    ctx.brain.log("designer", f"no video for {p['name']} this time ({str(e)[:80]})", "info")
            why = await critique(ctx, p, page)
            note = f" Editor's note: {why}" if why else ""
            ctx.brain.log("designer", f"mock-up for {p['name']} passed every check" + (" (rebuilt)" if i else "") + note,
                          "win", {"lead": p["name"], "photos": len(ex.get("photos") or []),
                                  "reviews": len(ex.get("reviews") or [])})
            return True, []
    if before is not None:
        page.write_bytes(before)
    elif page.exists():
        page.unlink()
    ctx.brain.log("designer", f"held back the mock-up for {p['name']}: " + "; ".join(problems), "warn")
    return False, problems
