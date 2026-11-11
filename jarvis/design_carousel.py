"""Carousels: a swipeable Instagram/LinkedIn post of 3 to 10 slides, the kind that gets saved and shared.

make_carousel turns a title and a few points ("5 signs your website is losing you customers") into 1080x1350 slides
in the brand colour: a bold cover with a "Swipe" hint, one slide per point with a big number, a heading and a short
line, and a closing slide with a call to action and the handle or web address. Every slide carries a progress bar so
people know how many are left, and the handle sits in the same corner on each. Words shrink to fit; if a point is too
long, Alfred says which. It saves 01.png, 02.png ... in Kinetic Web Designs/<name>/posts/<slug>/, ready to upload in
order, plus carousel.pdf with every slide (LinkedIn takes a PDF as a document post).
"""

import re

from PIL import Image, ImageDraw

import memory
from config import Settings
from design_contrast import UI, colour, fix, ratio, rgb
from design_extract import FOLDER
from design_palette import on
from design_social import fit, mix
from docs_tools import font

NAMES = {"make_carousel"}
SIZE = (1080, 1350)
PAD = 96
MIN_POINTS, MAX_POINTS = 1, 8  # with the cover and closing slide that's 3 to 10, Instagram's limit is 20


def frame(brand: str, index: int, total: int, handle: str, light: bool) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    """A blank slide: brand colour (or a soft tint for point slides), a progress bar and the handle."""
    background = rgb(brand) if not light else mix(brand, "#ffffff", 0.9)
    image = Image.new("RGB", SIZE, background)
    d = ImageDraw.Draw(image)
    if not light:
        d.ellipse((SIZE[0] - 420, -260, SIZE[0] + 260, 420), fill=mix(brand, on(brand), 0.08))  # quiet depth
    ink = rgb(on(brand)) if not light else (24, 24, 27)
    tint = "#%02x%02x%02x" % background
    bar = ink if not light else rgb(brand if ratio(brand, tint) >= UI else fix(brand, tint, UI))
    track = mix("#%02x%02x%02x" % background, "#%02x%02x%02x" % ink, 0.15)
    y = SIZE[1] - 70
    d.rounded_rectangle((PAD, y, SIZE[0] - PAD, y + 10), radius=5, fill=track)
    done = PAD + round((SIZE[0] - 2 * PAD) * index / total)
    d.rounded_rectangle((PAD, y, done, y + 10), radius=5, fill=bar)
    if handle:
        d.text((PAD, 80), handle, font=font(34, True), fill=mix("#%02x%02x%02x" % ink,
                                                                  "#%02x%02x%02x" % background, 0.3))
    d.text((SIZE[0] - PAD, 80), f"{index}/{total}", font=font(34), fill=mix("#%02x%02x%02x" % ink,
                                                                           "#%02x%02x%02x" % background, 0.3),
           anchor="ra")
    return image, d


def cover(brand: str, title: str, subtitle: str, total: int, handle: str) -> tuple[Image.Image, list[str]]:
    image, d = frame(brand, 1, total, handle, False)
    ink = rgb(on(brand))
    width = SIZE[0] - 2 * PAD
    size, rows = fit(d, title, width, (124, 110, 98, 86, 76), 5, True)
    sub_size, sub = fit(d, subtitle, width, (46, 42, 38), 3, False) if subtitle else (0, [])
    block = len(rows) * round(size * 1.08) + (40 + len(sub) * round(sub_size * 1.35) if sub else 0)
    y = (SIZE[1] - block) // 2 - 40
    for row in rows:
        d.text((PAD, y), row, font=font(size, True), fill=ink)
        y += round(size * 1.08)
    if sub:
        y += 40
        for row in sub:
            d.text((PAD, y), row, font=font(sub_size), fill=mix(on(brand), brand, 0.2))
            y += round(sub_size * 1.35)
    d.text((SIZE[0] - PAD, SIZE[1] - 120), "Swipe  →", font=font(40, True), fill=ink, anchor="rs")
    cut = ["the title"] if rows[-1].endswith("...") and not title.endswith("...") else []
    return image, cut


def point(brand: str, n: int, heading: str, text: str, index: int, total: int, handle: str) -> tuple:
    image, d = frame(brand, index, total, handle, True)
    width = SIZE[0] - 2 * PAD
    tint = "#%02x%02x%02x" % mix(brand, "#ffffff", 0.9)
    accent = rgb(brand if ratio(brand, tint) >= UI else fix(brand, tint, UI))  # the big number reads on the tint
    d.text((PAD, 200), f"{n:02d}", font=font(220, True), fill=accent)
    y = 520
    hsize, hrows = fit(d, heading, width, (84, 76, 68, 60), 3, True)
    for row in hrows:
        d.text((PAD, y), row, font=font(hsize, True), fill=(24, 24, 27))
        y += round(hsize * 1.12)
    cuts = []
    if text:
        y += 36
        tsize, trows = fit(d, text, width, (48, 44, 40, 36), max(1, (SIZE[1] - 160 - y) // 56), False)
        for row in trows:
            d.text((PAD, y), row, font=font(tsize), fill=(63, 63, 70))
            y += round(tsize * 1.4)
        cuts += [f"point {n}"] if trows[-1].endswith("...") and not text.endswith("...") else []
    if hrows[-1].endswith("...") and not heading.endswith("..."):
        cuts.append(f"point {n}'s heading")
    return image, cuts


def closing(brand: str, cta: str, line: str, site: str, total: int, handle: str) -> Image.Image:
    image, d = frame(brand, total, total, handle, False)
    ink = rgb(on(brand))
    width = SIZE[0] - 2 * PAD
    size, rows = fit(d, cta, width, (104, 92, 80, 70), 3, True)
    y = SIZE[1] // 2 - len(rows) * round(size * 1.1) // 2 - 80
    for row in rows:
        d.text((PAD, y), row, font=font(size, True), fill=ink)
        y += round(size * 1.1)
    if line:
        y += 36
        lsize, lrows = fit(d, line, width, (46, 42, 38), 3, False)
        for row in lrows:
            d.text((PAD, y), row, font=font(lsize), fill=mix(on(brand), brand, 0.2))
            y += round(lsize * 1.35)
    if site:
        y += 60
        f = font(42, True)
        w = round(d.textlength(site, font=f)) + 96
        d.rounded_rectangle((PAD, y, PAD + min(w, width), y + 104), radius=52, fill=ink)
        d.text((PAD + min(w, width) / 2, y + 52), site, font=f, fill=rgb(brand), anchor="mm")
    return image


def run(settings: Settings, args: dict) -> str:
    clean = lambda v: " ".join(str(v or "").split())  # noqa: E731
    name = clean(args.get("name"))
    if not name:
        raise ValueError("Give the brand or client name for the carousel.")
    brand = colour(args.get("colour") or "")
    title = clean(args.get("title"))
    if not title:
        raise ValueError("Give the carousel a title, e.g. '5 signs your website is losing you customers'.")
    raw = args.get("points") or []
    if not isinstance(raw, list):
        raise ValueError("Give the points as a list.")
    points = []
    for p in raw:
        if isinstance(p, dict):
            heading, text = clean(p.get("heading")), clean(p.get("text"))
        else:
            heading, text = clean(p), ""
        if heading:
            points.append((heading, text))
    if not MIN_POINTS <= len(points) <= MAX_POINTS:
        raise ValueError(f"Give {MIN_POINTS} to {MAX_POINTS} points (each becomes a slide).")
    handle = clean(args.get("handle"))
    if handle and not handle.startswith("@"):
        handle = "@" + handle
    site = re.sub(r"^https?://(www\.)?", "", clean(args.get("website"))).rstrip("/")
    cta = clean(args.get("cta")) or "Found this useful? Save it for later."
    total = len(points) + 2
    slides, cuts = [], []
    image, cut = cover(brand, title, clean(args.get("subtitle")), total, handle)
    slides.append(image)
    cuts += cut
    for n, (heading, text) in enumerate(points, start=1):
        image, cut = point(brand, n, heading, text, n + 1, total, handle)
        slides.append(image)
        cuts += cut
    slides.append(closing(brand, cta, clean(args.get("text")), site, total, handle))
    slug = re.sub(r"[^a-z0-9]+", "-", str(args.get("slug") or title).lower()).strip("-")
    if len(slug) > 40:
        slug = slug[:41].rsplit("-", 1)[0]  # cut at a whole word
    slug = slug or "carousel"
    (memory.root(settings) / FOLDER).mkdir(parents=True, exist_ok=True)
    path = memory.folder(settings, f"{FOLDER}/{memory.safe_name(name, 'folder name')}/posts", create=True) / slug
    path.mkdir(exist_ok=True)
    for old in path.glob("[0-9][0-9].png"):
        old.unlink()  # a shorter re-run mustn't leave stale slides behind
    for i, slide in enumerate(slides, start=1):
        slide.save(path / f"{i:02d}.png", optimize=True)
    slides[0].save(path / "carousel.pdf", "PDF", resolution=72, save_all=True, append_images=slides[1:])
    where = path.relative_to(memory.root(settings)).as_posix()
    return (f"Made a {total}-slide carousel for {name} in {where}: 01.png to {total:02d}.png (1080x1350) to upload "
            "in order on Instagram, and carousel.pdf for a LinkedIn document post. Slide 1 is the cover, the last one "
            "is the call to action, and each has a progress bar."
            + (f" Heads up: {', '.join(cuts)} didn't fit and {'was' if len(cuts) == 1 else 'were'} shortened."
               if cuts else ""))


def tool_definitions() -> list[dict]:
    return [{
        "name": "make_carousel",
        "description": "Make a swipeable Instagram/LinkedIn carousel (1080x1350 slides) in the brand colour from a "
                       "title and 1-8 points: a cover with a swipe hint, one numbered slide per point (heading and "
                       "short line), and a closing call-to-action slide with the web address, each with a progress "
                       "bar and the handle. Saves numbered PNGs and a PDF in Kinetic Web Designs/<name>/posts/<slug>. "
                       "Great for tips posts. Answer in plain words.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Brand or client name (the folder)."},
                "colour": {"type": "string", "description": "Brand colour, e.g. '#c2410c'."},
                "title": {"type": "string", "description": "Cover title, e.g. '5 signs your site loses customers'."},
                "subtitle": {"type": "string", "description": "Short line under the title."},
                "points": {"type": "array", "description": "1-8 points: text, or {heading, text}.",
                           "items": {"anyOf": [{"type": "string"}, {"type": "object", "properties": {
                               "heading": {"type": "string"}, "text": {"type": "string"}}, "required": ["heading"]}]}},
                "cta": {"type": "string", "description": "Closing slide words (default: save it for later)."},
                "text": {"type": "string", "description": "Short line under the closing words."},
                "website": {"type": "string"},
                "handle": {"type": "string", "description": "e.g. @kineticwebdesigns"},
                "slug": {"type": "string", "description": "Folder name (default from the title)."},
            },
            "required": ["name", "colour", "title", "points"],
            "additionalProperties": False,
        },
    }]


async def run_tool(name: str, args: dict, settings: Settings, http=None) -> str:
    try:
        return run(settings, args)
    except (TypeError, ValueError) as e:
        return str(e)
