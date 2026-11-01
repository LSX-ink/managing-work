"""Social posts: an Instagram/Facebook post and a matching story in the brand colour, ready to upload from a phone.

make_social_post draws a 1080x1350 feed post (the 4:5 shape that fills the most screen in the feed) and a 1080x1920
story from a headline, a short line and a call to action such as "Book now", with the web address. With a photo from a
memory folder, the post puts it above a brand-colour panel and the story uses it full-screen under a dark fade so the
words read. Story words stay out of the top 250px and bottom 340px, where Instagram's own buttons sit. Text colours come
from design_palette.on and big headlines shrink to fit. Files go in Kinetic Web Designs/<name>/posts as
<slug>-post.png and <slug>-story.png.
"""

import re

from PIL import Image, ImageDraw, ImageOps

import memory
from config import Settings
from design_contrast import colour, rgb
from design_extract import FOLDER
from design_palette import on
from design_social import fit, mix
from docs_tools import font

NAMES = {"make_social_post"}
POST, STORY = (1080, 1350), (1080, 1920)
PAD = 88
STORY_TOP, STORY_BOTTOM = 250, 340  # Instagram's profile row and reply box cover these
PICTURES = {".png", ".jpg", ".jpeg", ".webp"}
MAX_PIXELS = 50_000_000


def load(path) -> Image.Image:
    if path.suffix.lower() not in PICTURES:
        raise ValueError("Use a PNG, JPG or WebP photo.")
    try:
        with Image.open(path) as image:
            if image.width * image.height > MAX_PIXELS:
                raise ValueError("That photo is too big; use one under 50 megapixels.")
            return ImageOps.exif_transpose(image).convert("RGB")
    except OSError:
        raise ValueError("I couldn't open that photo.") from None


def pill(draw: ImageDraw.ImageDraw, x: int, y: int, text: str, fill, ink) -> int:
    """A rounded call-to-action button with its left edge at x; returns its bottom."""
    f = font(40, True)
    width = round(draw.textlength(text, font=f)) + 88
    draw.rounded_rectangle((x, y, x + width, y + 96), radius=48, fill=fill)
    draw.text((x + width / 2, y + 48), text, font=f, fill=ink, anchor="mm")
    return y + 96


def words(draw, image_size, top: int, bottom: int, brand: str, ink, headline: str, line: str, cta: str, site: str,
          sizes=(112, 100, 88, 76, 64)) -> list[str]:
    """Headline, line, button and web address stacked from the bottom of the area upwards; returns what was cut."""
    width = image_size[0] - PAD * 2
    soft = mix("#%02x%02x%02x" % ink, brand, 0.25)
    cuts = []
    for lines_allowed in (4, 3, 2):
        size, rows = fit(draw, headline, width, sizes, lines_allowed, True)
        small, sub = fit(draw, line, width, (44, 40, 36), 3, False) if line else (0, [])
        height = (len(rows) * round(size * 1.1) + (24 + len(sub) * round(small * 1.35) if sub else 0)
                  + (48 + 96 if cta else 0) + (64 if site else 0))
        if bottom - height >= top:
            break
    if rows and rows[-1].endswith("...") and not headline.endswith("..."):
        cuts.append("the headline")
    if sub and sub[-1].endswith("...") and not line.endswith("..."):
        cuts.append("the short line")
    y = max(top, bottom - height)
    for row in rows:
        draw.text((PAD, y), row, font=font(size, True), fill=ink)
        y += round(size * 1.1)
    if sub:
        y += 24
        for row in sub:
            draw.text((PAD, y), row, font=font(small), fill=soft)
            y += round(small * 1.35)
    if cta:
        y = pill(draw, PAD, y + 48, cta, ink, rgb(brand))
    if site:
        draw.text((PAD, y + 64), site, font=font(34, True), fill=soft, anchor="ls")
    return cuts


def cover(photo: Image.Image, size: tuple[int, int]) -> Image.Image:
    return ImageOps.fit(photo, size, Image.LANCZOS, centering=(0.5, 0.4))


def post(brand: str, headline: str, line: str, cta: str, site: str, photo: Image.Image | None) -> tuple:
    image = Image.new("RGB", POST, rgb(brand))
    d = ImageDraw.Draw(image)
    ink = rgb(on(brand))
    if photo is not None:
        image.paste(cover(photo, (POST[0], 640)), (0, 0))
        top = 640 + 64
    else:
        d.ellipse((POST[0] - 420, -300, POST[0] + 300, 420), fill=mix(brand, on(brand), 0.08))
        top = PAD + 120
    return image, words(d, POST, top, POST[1] - PAD, brand, ink, headline, line, cta, site)


def story(brand: str, headline: str, line: str, cta: str, site: str, photo: Image.Image | None) -> tuple:
    if photo is not None:
        image = cover(photo, STORY)
        shade = Image.new("L", (1, 256))
        shade.putdata([round(min(1, max(0, (y / 255 - 0.15) / 0.35)) * 215 + max(0, y / 255 - 0.5) * 60)
                       for y in range(256)])
        image.paste((12, 12, 16), (0, 0), shade.resize(STORY))  # dark fade towards the bottom so words read
        text_brand, ink = "#0c0c10", (255, 255, 255)
    else:
        image = Image.new("RGB", STORY, rgb(brand))
        ImageDraw.Draw(image).ellipse((-360, STORY_TOP + 120, 640, STORY_TOP + 1120),
                                      fill=mix(brand, on(brand), 0.07))
        text_brand, ink = brand, rgb(on(brand))
    d = ImageDraw.Draw(image)
    return image, words(d, STORY, STORY_TOP + 80, STORY[1] - STORY_BOTTOM, text_brand, ink, headline, line, cta, site,
                        sizes=(124, 112, 100, 88, 76))


def run(settings: Settings, args: dict) -> str:
    name = " ".join(str(args.get("name") or "").split())
    if not name:
        raise ValueError("Give the brand or client a name for the post.")
    brand = colour(args.get("colour") or "")
    headline = " ".join(str(args.get("headline") or "").split())
    if not headline:
        raise ValueError("What should the post say? Give a short headline, e.g. 'Fresh sourdough every morning'.")
    line, cta = " ".join(str(args.get("text") or "").split()), " ".join(str(args.get("cta") or "").split())
    if len(cta) > 24:
        raise ValueError("Keep the button words short, e.g. 'Book now' (24 letters at most).")
    site = re.sub(r"^https?://(www\.)?", "", str(args.get("website") or "").strip()).rstrip("/")
    photo = None
    if args.get("photo"):
        if not args.get("folder"):
            raise ValueError("Say which memory folder the photo is in.")
        photo = load(memory.file_path(settings, str(args["folder"]), str(args["photo"])))
    formats = [f for f in (args.get("formats") or ["post", "story"]) if f in ("post", "story")]
    if not formats:
        raise ValueError("Pick post, story or both.")
    slug = re.sub(r"[^a-z0-9]+", "-", str(args.get("slug") or headline).lower()).strip("-")[:40].strip("-") or "post"
    (memory.root(settings) / FOLDER).mkdir(parents=True, exist_ok=True)
    path = memory.folder(settings, f"{FOLDER}/{memory.safe_name(name, 'folder name')}/posts", create=True)
    made, cuts = [], []
    for kind in formats:
        image, cut = (post if kind == "post" else story)(brand, headline, line, cta, site, photo)
        image.save(path / f"{slug}-{kind}.png", optimize=True)
        made.append(f"{slug}-{kind}.png")
        cuts += [c for c in cut if c not in cuts]
    where = path.relative_to(memory.root(settings)).as_posix()
    sizes = {"post": "1080x1350 feed post", "story": "1080x1920 story"}
    return (f"Made {' and '.join(sizes[k] for k in formats)} for {name} in {where} ({', '.join(made)})"
            f"{' using the photo ' + str(args['photo']) if photo else ''}. Story words stay clear of Instagram's "
            "buttons. Send them to the phone and post from the Instagram app."
            + (f" Heads up: {' and '.join(cuts)} didn't fit and {'was' if len(cuts) == 1 else 'were'} shortened."
               if cuts else ""))


def tool_definitions() -> list[dict]:
    return [{
        "name": "make_social_post",
        "description": "Make an Instagram/Facebook feed post (1080x1350) and matching story (1080x1920) in the brand "
                       "colour: headline, short line, a call-to-action button and web address, optionally with a "
                       "photo from a memory folder. Story words stay out of Instagram's button areas. Saves PNGs in "
                       "Kinetic Web Designs/<name>/posts. Use for a client's offers and news, or Kinetic's own posts. "
                       "Answer in plain words.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Brand or client name (the folder)."},
                "colour": {"type": "string", "description": "Brand colour, e.g. '#c2410c'."},
                "headline": {"type": "string", "description": "Big words, e.g. 'Fresh sourdough every morning'."},
                "text": {"type": "string", "description": "Short line under the headline."},
                "cta": {"type": "string", "description": "Button words, e.g. 'Order now' (24 letters at most)."},
                "website": {"type": "string", "description": "Web address shown at the bottom."},
                "folder": {"type": "string", "description": "Memory folder with the photo (optional)."},
                "photo": {"type": "string", "description": "Photo in that folder (PNG/JPG/WebP)."},
                "formats": {"type": "array", "items": {"type": "string", "enum": ["post", "story"]},
                            "description": "Default both."},
                "slug": {"type": "string", "description": "File name start (default from the headline)."},
            },
            "required": ["name", "colour", "headline"],
            "additionalProperties": False,
        },
    }]


async def run_tool(name: str, args: dict, settings: Settings, http=None) -> str:
    try:
        return run(settings, args)
    except (TypeError, ValueError) as e:
        return str(e)
