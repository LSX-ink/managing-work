"""Share cards: the picture and tags a website shows when its link is pasted into WhatsApp, Facebook, X or LinkedIn.

make_share_card draws a 1200x630 PNG (the size those apps expect) in the brand colour, with the initials tile, the page
title, a short line under it and the web address, picking text colours with design_palette.on so they read. It also
writes meta-tags.html: the Open Graph and X (Twitter) tags to paste into the page's <head>, and warns when the title or
description is long enough to be cut off. Files go in Kinetic Web Designs/<name>/share, next to the brand kit and logos.
"""

import html
import re
from urllib.parse import urlparse

from PIL import Image, ImageDraw

import memory
from config import Settings
from design_contrast import colour, rgb
from design_extract import FOLDER
from design_logo import initials
from design_palette import on
from docs_tools import font

NAMES = {"make_share_card"}
SIZE = (1200, 630)
PAD = 80
TITLE_MAX, DESCRIPTION_MAX = 60, 160  # past these, search results and link previews start cutting text off


def mix(a: str, b: str, amount: float) -> tuple[int, int, int]:
    """a moved amount of the way towards b."""
    return tuple(round(x + (y - x) * amount) for x, y in zip(rgb(a), rgb(b)))


def wrap(draw: ImageDraw.ImageDraw, text: str, size: int, width: int, bold: bool) -> list[str]:
    f = font(size, bold)
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if line and draw.textlength(trial, font=f) > width:
            lines.append(line)
            line = word
        else:
            line = trial
    return lines + ([line] if line else [])


def fit(draw: ImageDraw.ImageDraw, text: str, width: int, sizes: tuple, max_lines: int, bold: bool):
    """The biggest size that fits in max_lines; at the smallest size, the last line ends with '...'."""
    for size in sizes:
        lines = wrap(draw, text, size, width, bold)
        if len(lines) <= max_lines:
            return size, lines
    lines = lines[:max_lines]
    f = font(size, bold)
    while lines[-1] and draw.textlength(lines[-1] + "...", font=f) > width:
        lines[-1] = lines[-1][:-1].rstrip()
    lines[-1] += "..."
    return size, lines


def card(brand: str, mark: str, title: str, tagline: str, site: str) -> Image.Image:
    text = on(brand)
    soft = mix(text, brand, 0.25)
    image = Image.new("RGB", SIZE, rgb(brand))
    draw = ImageDraw.Draw(image)
    draw.ellipse((SIZE[0] - 360, -260, SIZE[0] + 260, 360), fill=mix(brand, text, 0.08))  # a quiet shape for depth
    box = 96
    draw.rounded_rectangle((PAD, PAD, PAD + box, PAD + box), radius=22, fill=rgb(text))
    draw.text((PAD + box / 2, PAD + box / 2), mark, font=font(44 if len(mark) > 1 else 52, True), fill=rgb(brand),
              anchor="mm")
    width = SIZE[0] - PAD * 2
    top = PAD + box + 56
    bottom = SIZE[1] - PAD - (54 if site else 0)  # room for the web address line
    for title_lines in (3, 2, 1):  # give up title lines before the tagline runs into the web address
        size, lines = fit(draw, title, width, (76, 68, 60, 52), title_lines, True)
        small, rows = fit(draw, tagline, width, (34, 30), 2, False) if tagline else (0, [])
        height = len(lines) * round(size * 1.18) + (14 + len(rows) * round(small * 1.35) if rows else 0)
        if top + height <= bottom:
            break
    y = top
    for line in lines:
        draw.text((PAD, y), line, font=font(size, True), fill=rgb(text))
        y += round(size * 1.18)
    y += 14
    for row in rows:
        draw.text((PAD, y), row, font=font(small), fill=soft)
        y += round(small * 1.35)
    if site:
        draw.text((PAD, SIZE[1] - PAD), site, font=font(30, True), fill=soft, anchor="ls")
    return image


def site_of(url: str) -> str:
    if not url:
        return ""
    host = urlparse(url if "//" in url else f"https://{url}").netloc
    return re.sub(r"^www\.", "", host)


def meta_tags(title: str, description: str, url: str, image: str, brand: str, name: str) -> str:
    e = lambda s: html.escape(s, quote=True)  # noqa: E731
    image_url = f"{url.rstrip('/')}/{image}" if url else image
    tags = [f"<title>{e(title)}</title>", f'<meta name="description" content="{e(description)}">',
            f'<meta name="theme-color" content="{brand}">',
            '<meta property="og:type" content="website">', f'<meta property="og:site_name" content="{e(name)}">',
            f'<meta property="og:title" content="{e(title)}">',
            f'<meta property="og:description" content="{e(description)}">',
            f'<meta property="og:image" content="{e(image_url)}">', '<meta property="og:image:width" content="1200">',
            '<meta property="og:image:height" content="630">',
            f'<meta property="og:image:alt" content="{e(title)}">',
            '<meta name="twitter:card" content="summary_large_image">',
            f'<meta name="twitter:title" content="{e(title)}">',
            f'<meta name="twitter:description" content="{e(description)}">',
            f'<meta name="twitter:image" content="{e(image_url)}">']
    if url:
        tags[3:3] = [f'<link rel="canonical" href="{e(url)}">', f'<meta property="og:url" content="{e(url)}">']
    return ("<!-- Paste into the page's <head>. Upload " + image + " to the site's main folder"
            + (" so the image link works." if url else " and change og:image to its full web address.") + " -->\n"
            + "\n".join(tags) + "\n")


def build(settings: Settings, args: dict) -> str:
    name = str(args.get("name") or "").strip()
    if not name:
        raise ValueError("Give the brand or client a name for the share card.")
    brand = colour(args.get("colour") or "")
    title = " ".join(str(args.get("title") or name).split())
    description = " ".join(str(args.get("description") or "").split())
    tagline = " ".join(str(args.get("tagline") or description).split())
    url = str(args.get("url") or "").strip()
    page = memory.safe_name(str(args.get("page") or "home"), "page name").lower().replace(" ", "-")
    image_name = f"share-{page}.png"
    (memory.root(settings) / FOLDER).mkdir(parents=True, exist_ok=True)
    path = memory.folder(settings, f"{FOLDER}/{memory.safe_name(name, 'folder name')}/share", create=True)
    card(brand, initials(name, str(args.get("initials") or "")), title, tagline, site_of(url)).save(
        path / image_name, optimize=True)
    tags = meta_tags(title, description or tagline, url, image_name, brand, name)
    (path / f"meta-tags-{page}.html").write_text(tags, encoding="utf-8")
    where = path.relative_to(memory.root(settings)).as_posix()
    notes = []
    if len(title) > TITLE_MAX:
        notes.append(f"the title is {len(title)} letters, so Google may cut it after about {TITLE_MAX}")
    if len(description) > DESCRIPTION_MAX:
        notes.append(f"the description is {len(description)} letters; about {DESCRIPTION_MAX} shows in full")
    if not description:
        notes.append("there's no description yet, so add one for search results")
    return (f"Made the share card {image_name} (1200x630) and meta-tags-{page}.html for {name} in {where}. "
            f"Paste the tags into the page's <head> and upload the picture with the site; it shows when the link is "
            f"shared on WhatsApp, Facebook, X or LinkedIn."
            + (" Heads up: " + "; ".join(notes) + "." if notes else ""))


def tool_definitions() -> list[dict]:
    return [{
        "name": "make_share_card",
        "description": "Make a website's link preview: a 1200x630 share picture in the brand colour (initials, page "
                       "title, a short line, web address) and the Open Graph and X/Twitter meta tags for the page's "
                       "<head>, so the link looks good when shared on WhatsApp, Facebook, X or LinkedIn. Saves in "
                       "Kinetic Web Designs/<name>/share. Use one per page (home, pricing, contact). Answer in plain "
                       "words.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Brand or client name (the folder)."},
                "colour": {"type": "string", "description": "Brand colour, e.g. '#c2410c'."},
                "title": {"type": "string", "description": "Page title (defaults to the name). Under 60 letters."},
                "description": {"type": "string", "description": "One or two sentences for search and previews."},
                "tagline": {"type": "string", "description": "Short line on the picture (defaults to description)."},
                "url": {"type": "string", "description": "The page's web address, e.g. https://lebosbakery.co.uk."},
                "page": {"type": "string", "description": "Which page, e.g. 'home' or 'pricing' (default home)."},
                "initials": {"type": "string", "description": "1-2 letters instead of the name's initials."},
            },
            "required": ["name", "colour"],
            "additionalProperties": False,
        },
    }]


async def run_tool(name: str, args: dict, settings: Settings, http=None) -> str:
    try:
        return build(settings, args)
    except (TypeError, ValueError) as e:
        return str(e)
