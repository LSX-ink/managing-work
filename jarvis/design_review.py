"""Review posts: a customer's kind words turned into an Instagram/Facebook post and story, in the brand colour.

make_review_post puts a real review (from Google, Facebook, Tripadvisor or a message) on a white card over the brand
colour: gold stars drawn as shapes (so they look the same everywhere), a big quote mark, the words sized to fit, the
reviewer's name as they want it shown (first name and initial is kinder to their privacy) and where the review came
from, with the business name and web address underneath. It makes a 1080x1350 feed post and a 1080x1920 story whose
words stay clear of Instagram's buttons. Long reviews are shortened at a sentence end with "..." and Alfred says so.
Only use reviews customers really wrote, with their say-so to share. Files go in Kinetic Web Designs/<name>/posts.
"""

import math
import re

from PIL import Image, ImageDraw, ImageFilter

import memory
from config import Settings
from design_contrast import AA, colour, fix, ratio, rgb
from design_extract import FOLDER
from design_palette import on
from design_social import fit, mix
from docs_tools import font

NAMES = {"make_review_post"}
POST, STORY = (1080, 1350), (1080, 1920)
STORY_TOP, STORY_BOTTOM = 250, 340  # Instagram's profile row and reply box cover these
GOLD, EMPTY = (251, 188, 4), (218, 218, 224)
INK, MUTED = (24, 24, 27), (82, 82, 91)
MAX_WORDS = 400


def star(draw: ImageDraw.ImageDraw, cx: float, cy: float, r: float, fill) -> None:
    points = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.45
        points.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    draw.polygon(points, fill=fill)


def stars(image: Image.Image, x: float, cy: float, rating: float, r: int = 30) -> None:
    """Five stars from x; a half star shows half gold."""
    draw = ImageDraw.Draw(image)
    for i in range(5):
        cx = x + r + i * (2 * r + 14)
        star(draw, cx, cy, r, EMPTY)
        part = max(0.0, min(1.0, rating - i))
        if part >= 1:
            star(draw, cx, cy, r, GOLD)
        elif part > 0:
            layer = Image.new("L", image.size, 0)
            star(ImageDraw.Draw(layer), cx, cy, r, 255)
            ImageDraw.Draw(layer).rectangle((cx - r + 2 * r * part, 0, *image.size), fill=0)  # keep the left part
            image.paste(GOLD, (0, 0), layer)


def shorten(text: str, limit: int) -> tuple[str, bool]:
    if len(text) <= limit:
        return text, False
    cut = text[:limit]
    end = max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "))
    cut = cut[:end + 1] if end > limit * 0.5 else cut.rsplit(" ", 1)[0].rstrip(",;:-")
    return cut.rstrip().rstrip(".") + "...", True  # "sourdough..." not "sourdough...."


def card(size: tuple[int, int], brand: str, quote: str, rating: float, who: str, source: str, business: str,
         site: str, top: int, bottom: int) -> tuple[Image.Image, bool]:
    image = Image.new("RGB", size, rgb(brand))
    d = ImageDraw.Draw(image)
    text = rgb(on(brand))
    d.ellipse((size[0] - 380, top - 340, size[0] + 300, top + 340), fill=mix(brand, on(brand), 0.07))
    pad, inner_pad = 72, 72
    foot = 150 if site else 100
    box = (pad, top, size[0] - pad, bottom - foot)
    shadow = Image.new("RGBA", size, (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle((box[0], box[1] + 18, box[2], box[3] + 18), radius=44,
                                             fill=(0, 0, 0, 70))
    soft = shadow.filter(ImageFilter.GaussianBlur(22))
    image.paste(soft, (0, 0), soft)
    d.rounded_rectangle(box, radius=44, fill=(255, 255, 255))
    accent = rgb(brand if ratio(brand, "#ffffff") >= AA else fix(brand, "#ffffff", AA))
    x, y = box[0] + inner_pad, box[1] + inner_pad
    width = box[2] - box[0] - 2 * inner_pad
    stars(image, x, y + 30, rating)
    d.text((box[2] - inner_pad, y - 40), "“", font=font(260, True), fill=mix("#ffffff", "#%02x%02x%02x" % accent,
                                                                                      0.35), anchor="ra")
    y += 110
    name_h = 150
    room = box[3] - inner_pad - name_h - y
    cut = False
    for limit in (len(quote), 420, 320, 240):
        shown, cut = shorten(quote, limit)
        for size_ in (64, 58, 52, 46, 42, 38):
            qsize, rows = fit(d, shown, width, (size_,), 99, False)
            if len(rows) * round(qsize * 1.35) <= room:
                break
        else:
            continue
        break
    for row in rows:
        d.text((x, y), row, font=font(qsize), fill=INK)
        y += round(qsize * 1.35)
    ny = box[3] - inner_pad - name_h + 40
    d.line((x, ny - 24, x + 90, ny - 24), fill=accent, width=6)
    nsize, nrows = fit(d, who, width, (46, 40, 36), 1, True)
    d.text((x, ny), nrows[0], font=font(nsize, True), fill=INK)
    if source:
        d.text((x, ny + 60), source, font=font(34), fill=MUTED)
    bsize, brows = fit(d, business, size[0] - 2 * pad, (52, 46, 40), 1, True)
    fy = bottom - foot + 44
    d.text((size[0] / 2, fy), brows[0], font=font(bsize, True), fill=text, anchor="mt")
    if site:
        d.text((size[0] / 2, fy + 66), site, font=font(34), fill=mix("#%02x%02x%02x" % text, brand, 0.25),
               anchor="mt")
    return image, cut


def run(settings: Settings, args: dict) -> str:
    clean = lambda k: " ".join(str(args.get(k) or "").split())  # noqa: E731
    business = clean("name")
    if not business:
        raise ValueError("Give the business name for the review post.")
    brand = colour(args.get("colour") or "")
    quote = clean("quote").strip("\"'“”")
    if not quote:
        raise ValueError("Paste the customer's review words.")
    if len(quote.split()) > MAX_WORDS:
        raise ValueError("That review is very long; pick the best few sentences.")
    who = clean("reviewer")
    if not who:
        raise ValueError("Give the reviewer's name as they'd like it shown, e.g. 'Sarah K.'.")
    rating = float(args.get("stars") if args.get("stars") is not None else 5)
    if not 1 <= rating <= 5 or rating * 2 != int(rating * 2):
        raise ValueError("Stars go from 1 to 5, in halves (e.g. 4.5).")
    source = clean("source") or "Google review"
    site = re.sub(r"^https?://(www\.)?", "", clean("website")).rstrip("/")
    formats = [f for f in (args.get("formats") or ["post", "story"]) if f in ("post", "story")]
    if not formats:
        raise ValueError("Pick post, story or both.")
    slug = "review-" + (re.sub(r"[^a-z0-9]+", "-", who.lower()).strip("-")[:30] or "customer")
    (memory.root(settings) / FOLDER).mkdir(parents=True, exist_ok=True)
    path = memory.folder(settings, f"{FOLDER}/{memory.safe_name(business, 'folder name')}/posts", create=True)
    made, cut = [], False
    for kind in formats:
        size = POST if kind == "post" else STORY
        top, bottom = (110, POST[1] - 40) if kind == "post" else (STORY_TOP + 40, STORY[1] - STORY_BOTTOM)
        image, was_cut = card(size, brand, quote, rating, who, source, business, site, top, bottom)
        image.save(path / f"{slug}-{kind}.png", optimize=True)
        made.append(f"{slug}-{kind}.png")
        cut = cut or was_cut
    where = path.relative_to(memory.root(settings)).as_posix()
    shown = f"{rating:g} star{'s' if rating != 1 else ''}"
    return (f"Made a {shown} review post from {who} for {business} in {where} ({', '.join(made)}). "
            + ("The review was long, so it was shortened with '...' at a sentence end; check it still reads right. "
               if cut else "")
            + "Only post reviews customers really wrote, and ask before using their full name.")


def tool_definitions() -> list[dict]:
    return [{
        "name": "make_review_post",
        "description": "Turn a real customer review into an Instagram/Facebook feed post (1080x1350) and story "
                       "(1080x1920): gold stars, the quote on a white card over the brand colour, the reviewer's name "
                       "and where it came from, the business name and web address. Long reviews are shortened at a "
                       "sentence end. Saves PNGs in Kinetic Web Designs/<name>/posts. Answer in plain words.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Business name (footer and folder)."},
                "colour": {"type": "string", "description": "Brand colour, e.g. '#c2410c'."},
                "quote": {"type": "string", "description": "The review words, exactly as the customer wrote them."},
                "reviewer": {"type": "string", "description": "Name as shown, e.g. 'Sarah K.'."},
                "stars": {"type": "number", "description": "1-5 in halves (default 5)."},
                "source": {"type": "string", "description": "Where it's from (default 'Google review')."},
                "website": {"type": "string"},
                "formats": {"type": "array", "items": {"type": "string", "enum": ["post", "story"]},
                            "description": "Default both."},
            },
            "required": ["name", "colour", "quote", "reviewer"],
            "additionalProperties": False,
        },
    }]


async def run_tool(name: str, args: dict, settings: Settings, http=None) -> str:
    try:
        return run(settings, args)
    except (TypeError, ValueError) as e:
        return str(e)
