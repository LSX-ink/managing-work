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
    if p.get("website") and not kf.social_only(p) and not before.exists():
        try:
            await shoot(p["website"], before)
        except Exception:
            pass
    design_speed = b.get("design.template_speed")
    return {**extra, "photos": photos, "before": before.name if before.exists() else "",
            "design_speed": design_speed if isinstance(design_speed, int) else None}


PHONE = {"width": 390, "height": 760}


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
            if not (site_folder / "preview.mp4").exists():
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
