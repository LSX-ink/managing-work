"""Social banners: matching header images for Facebook, LinkedIn, X and YouTube, in the brand colour.

make_social_banners makes the wide cover images at each site's own size, with the business name, a tagline and the
web address kept inside the part every screen shows. Each site crops differently and puts the profile picture over a
corner, so the words go where nothing covers them:
- Facebook cover 1640x624: phones cut the sides, so the words stay in the middle 1200px.
- LinkedIn banner 1584x396: the profile photo covers the bottom left, so the words sit on the right.
- X header 1500x500: phones trim the top and bottom and the photo covers the bottom left, so the words sit right
  of centre.
- YouTube channel art 2560x1440: only the middle 1546x423 shows on every device, so the words stay there.
The background is the brand colour with a soft fade and two quiet circles for depth. It saves facebook-cover.png,
linkedin-banner.png, x-header.png and youtube-banner.png in Kinetic Web Designs/<name>/social.
"""

import re

from PIL import Image, ImageDraw

import memory
from config import Settings
from design_contrast import colour, rgb
from design_extract import FOLDER
from design_palette import on
from design_social import fit, mix
from docs_tools import font

NAMES = {"make_social_banners"}
# name: (size, safe box (left, top, right, bottom), text alignment)
SITES = {
    "facebook": ((1640, 624), (220, 70, 1420, 554), "middle"),
    "linkedin": ((1584, 396), (620, 50, 1520, 346), "right"),
    "x": ((1500, 500), (560, 90, 1420, 410), "right"),
    "youtube": ((2560, 1440), (507, 509, 2053, 932), "middle"),
}
FILES = {"facebook": "facebook-cover.png", "linkedin": "linkedin-banner.png", "x": "x-header.png",
         "youtube": "youtube-banner.png"}


def background(size: tuple[int, int], brand: str) -> Image.Image:
    """Brand colour fading slightly darker to the right, with two soft circles."""
    w, h = size
    deeper = "#%02x%02x%02x" % mix(brand, "#000000", 0.18)
    strip = Image.new("RGB", (w, 1))
    strip.putdata([mix(brand, deeper, x / max(1, w - 1)) for x in range(w)])
    image = strip.resize(size)
    d = ImageDraw.Draw(image)
    lift = mix(brand, on(brand), 0.07)
    d.ellipse((w - h * 0.9, -h * 0.5, w + h * 0.4, h * 0.8), fill=lift)
    d.ellipse((-h * 0.3, h * 0.55, h * 0.5, h * 1.35), fill=mix(brand, on(brand), 0.05))
    return image


def banner(site: str, brand: str, name: str, tagline: str, web: str) -> tuple[Image.Image, list[str]]:
    size, (left, top, right, bottom), align = SITES[site]
    image = background(size, brand)
    d = ImageDraw.Draw(image)
    ink = rgb(on(brand))
    soft = mix(on(brand), brand, 0.22)
    width, height = right - left, bottom - top
    scale = height / 300  # the safe boxes run from about 300 to 480px tall
    while True:  # shrink everything together until the whole block fits the safe box
        nsize, nrows = fit(d, name, width, tuple(round(s * scale) for s in (110, 96, 84, 72, 62)), 2, True)
        tsize, trows = fit(d, tagline, width, tuple(round(s * scale) for s in (46, 42, 38, 34)), 2, False) \
            if tagline else (0, [])
        wsize = round(32 * scale)
        gap = round(18 * scale)
        block = (len(nrows) * round(nsize * 1.08) + (gap + len(trows) * round(tsize * 1.3) if trows else 0)
                 + (gap * 2 + wsize if web else 0))
        if block <= height or wsize <= 18:
            break
        scale *= 0.92
    y = top + (height - block) // 2
    x, anchor = (left + width / 2, "mt") if align == "middle" else (right, "rt")
    for row in nrows:
        d.text((x, y), row, font=font(nsize, True), fill=ink, anchor=anchor)
        y += round(nsize * 1.08)
    if trows:
        y += gap
        for row in trows:
            d.text((x, y), row, font=font(tsize), fill=soft, anchor=anchor)
            y += round(tsize * 1.3)
    if web:
        y += gap * 2
        d.text((x, y), web, font=font(wsize, True), fill=ink, anchor=anchor)
    cuts = []
    if nrows[-1].endswith("...") and not name.endswith("..."):
        cuts.append(f"the name on {site}")
    if trows and trows[-1].endswith("...") and not tagline.endswith("..."):
        cuts.append(f"the tagline on {site}")
    return image, cuts


def run(settings: Settings, args: dict) -> str:
    clean = lambda k: " ".join(str(args.get(k) or "").split())  # noqa: E731
    name = clean("name")
    if not name:
        raise ValueError("Give the business name for the banners.")
    brand = colour(args.get("colour") or "")
    tagline = clean("tagline")
    if len(tagline) > 90:
        raise ValueError("Keep the tagline short, e.g. 'Websites that win you customers' (90 letters at most).")
    web = re.sub(r"^https?://(www\.)?", "", clean("website")).rstrip("/")
    wanted = [s.lower() for s in (args.get("sites") or list(SITES))]
    bad = [s for s in wanted if s not in SITES]
    if bad or not wanted:
        raise ValueError(f"Pick from {', '.join(SITES)}.")
    (memory.root(settings) / FOLDER).mkdir(parents=True, exist_ok=True)
    path = memory.folder(settings, f"{FOLDER}/{memory.safe_name(name, 'folder name')}/social", create=True)
    made, cuts = [], []
    for site in dict.fromkeys(wanted):
        image, cut = banner(site, brand, name, tagline, web)
        image.save(path / FILES[site], optimize=True)
        made.append(FILES[site])
        cuts += cut
    where = path.relative_to(memory.root(settings)).as_posix()
    return (f"Made {len(made)} social banner{'s' if len(made) != 1 else ''} for {name} in {where}: "
            f"{', '.join(made)}. The words sit where every phone and computer shows them and clear of the profile "
            "picture. Upload each one as the cover or banner on that site."
            + (f" Heads up: {', '.join(cuts)} didn't fit and {'was' if len(cuts) == 1 else 'were'} shortened."
               if cuts else ""))


def tool_definitions() -> list[dict]:
    return [{
        "name": "make_social_banners",
        "description": "Make matching header images in the brand colour at each site's own size: Facebook cover "
                       "(1640x624), LinkedIn banner (1584x396), X header (1500x500) and YouTube channel art "
                       "(2560x1440), with the business name, tagline and web address kept inside each site's safe "
                       "area and clear of the profile picture. Saves PNGs in Kinetic Web Designs/<name>/social. "
                       "Answer in plain words.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Business name (on the banners and the folder)."},
                "colour": {"type": "string", "description": "Brand colour, e.g. '#c2410c'."},
                "tagline": {"type": "string", "description": "Short line, e.g. 'Websites that win you customers'."},
                "website": {"type": "string"},
                "sites": {"type": "array", "items": {"type": "string", "enum": list(SITES)},
                          "description": "Which banners (default all four)."},
            },
            "required": ["name", "colour"],
            "additionalProperties": False,
        },
    }]


async def run_tool(name: str, args: dict, settings: Settings, http=None) -> str:
    try:
        return run(settings, args)
    except (TypeError, ValueError) as e:
        return str(e)
