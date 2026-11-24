"""Web-ready pictures: the photos a client sends, turned into small, sharp files a website loads fast.

make_web_images takes one picture or every picture in a memory folder and saves WebP copies at a few widths (480, 960
and 1600px by default, never wider than the original), plus one JPG (or PNG for see-through pictures) for old browsers,
in a web/ folder beside them. Photos are turned the right way up, and their hidden camera details (GPS location, phone
model) are left out, so a client's home address never goes online by accident. It writes pictures.html with a ready
<picture> tag for each one (srcset, sizes, width and height so the page doesn't jump, lazy loading below the first
picture) and says how much smaller the files got. Use it on a client's photos before they go into a site.
"""

import html
import re

from PIL import Image, ImageOps

import memory
from config import Settings

NAMES = {"make_web_images"}
PICTURES = {".png", ".jpg", ".jpeg", ".webp"}
WIDTHS = (480, 960, 1600)
MAX_FILES = 30
MAX_PIXELS = 50_000_000
BIG = 300 * 1024  # a page picture over about 300KB slows phones down


def widths(original: int, wanted) -> list[int]:
    """The wanted widths the picture can fill without being stretched, plus its own width when it is smaller."""
    out = sorted({int(w) for w in wanted if 64 <= int(w) <= 4000})
    if not out:
        raise ValueError("Use widths between 64 and 4000 pixels, e.g. 480, 960 and 1600.")
    fit = [w for w in out if w < original]
    if original <= out[-1]:
        fit.append(original)
    return fit


def slug(stem: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", stem.lower()).strip("-") or "picture"


def open_picture(path) -> Image.Image:
    try:
        with Image.open(path) as image:
            if image.width * image.height > MAX_PIXELS:
                raise ValueError(f"{path.name} is too big; use pictures under 50 megapixels.")
            image = ImageOps.exif_transpose(image)  # phone photos are stored sideways with a note to turn them
            see_through = image.mode in ("RGBA", "LA", "PA") or "transparency" in image.info
            return image.convert("RGBA" if see_through else "RGB")
    except OSError:
        raise ValueError(f"I couldn't open {path.name}.") from None


def convert(path, out_dir, wanted, quality: int) -> dict:
    image = open_picture(path)
    name = slug(path.stem)
    sizes, made = widths(image.width, wanted), []
    for w in sizes:
        h = max(1, round(image.height * w / image.width))
        copy = image if w == image.width else image.resize((w, h), Image.LANCZOS)
        target = out_dir / f"{name}-{w}.webp"
        copy.save(target, "WEBP", quality=quality, method=6)  # no exif= given, so camera details are dropped
        made.append((w, h, target))
    w, h, _ = made[-1]
    largest = image if w == image.width else image.resize((w, h), Image.LANCZOS)
    if image.mode == "RGBA":
        fallback = out_dir / f"{name}-{w}.png"
        largest.save(fallback, "PNG", optimize=True)
    else:
        fallback = out_dir / f"{name}-{w}.jpg"
        largest.save(fallback, "JPEG", quality=quality, optimize=True, progressive=True)
    return {"source": path, "name": name, "made": made, "fallback": fallback, "width": w, "height": h,
            "before": path.stat().st_size, "after": made[-1][2].stat().st_size}


def tag(item: dict, alt: str, first: bool, sizes: str) -> str:
    srcset = ", ".join(f"{t.name} {w}w" for w, _, t in item["made"])
    load = 'fetchpriority="high"' if first else 'loading="lazy"'
    return (f'<picture>\n  <source type="image/webp" srcset="{srcset}" sizes="{html.escape(sizes, quote=True)}">\n'
            f'  <img src="{item["fallback"].name}" width="{item["width"]}" height="{item["height"]}" '
            f'alt="{html.escape(alt, quote=True)}" {load} decoding="async">\n</picture>')


def page(items: list[dict], tags: list[str]) -> str:
    blocks = "".join(f"<h2>{html.escape(i['source'].name)}</h2>\n<pre>{html.escape(t)}</pre>\n{t}\n"
                     for i, t in zip(items, tags))
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Web pictures</title><style>
body {{ margin: 0 auto; max-width: 960px; padding: 24px; font-family: system-ui, sans-serif; color: #18181b; }}
pre {{ background: #f4f4f5; padding: 12px; border-radius: 8px; overflow-x: auto; font-size: 13px; }}
img {{ max-width: 100%; height: auto; border-radius: 8px; }}
</style></head><body>
<h1>Web pictures</h1>
<p>Copy each &lt;picture&gt; tag into the site and upload the files in this folder next to the page. Change the alt
words to say what each picture shows.</p>
{blocks}</body></html>
"""


def kb(n: int) -> str:
    return f"{n / 1024 / 1024:.1f}MB" if n >= 1024 * 1024 else f"{max(1, round(n / 1024))}KB"


def run(settings: Settings, args: dict) -> str:
    folder = str(args.get("folder") or "").strip()
    if not folder:
        raise ValueError("Say which memory folder the pictures are in, e.g. 'Kinetic Web Designs/Lebo's Bakery'.")
    base = memory.folder(settings, folder)
    if args.get("file"):
        paths = [memory.file_path(settings, folder, str(args["file"]))]
    else:
        paths = sorted(p for p in base.iterdir() if p.is_file() and p.suffix.lower() in PICTURES)[:MAX_FILES + 1]
        if not paths:
            raise ValueError("There are no PNG, JPG or WebP pictures in that folder.")
        if len(paths) > MAX_FILES:
            raise ValueError(f"That folder has more than {MAX_FILES} pictures; do them one at a time or split the "
                             "folder.")
    if any(p.suffix.lower() not in PICTURES for p in paths):
        raise ValueError("Use PNG, JPG or WebP pictures.")
    quality = int(args.get("quality") or 80)
    if not 40 <= quality <= 95:
        raise ValueError("Keep the quality between 40 and 95 (80 is the usual).")
    wanted = args.get("widths") or WIDTHS
    sizes = str(args.get("sizes") or "100vw")
    out_dir = base / "web"
    out_dir.mkdir(exist_ok=True)
    items = [convert(p, out_dir, wanted, quality) for p in paths]
    alt = str(args.get("alt") or "")
    tags = [tag(i, alt or i["source"].stem.replace("-", " ").replace("_", " "), n == 0, sizes)
            for n, i in enumerate(items)]
    (out_dir / "pictures.html").write_text(page(items, tags), encoding="utf-8")
    before, after = sum(i["before"] for i in items), sum(i["after"] for i in items)
    where = out_dir.relative_to(memory.root(settings)).as_posix()
    heavy = [i["made"][-1][2].name for i in items if i["after"] > BIG]
    saved = f"{round(100 * (1 - after / before))}% smaller" if after < before else "about the same size"
    return (f"Made web copies of {len(items)} picture{'s' if len(items) > 1 else ''} in {where}: WebP at "
            f"{', '.join(str(w) for w, _, _ in items[0]['made'])}px wide"
            + (" (for the first one)" if len(items) > 1 else "")
            + f" plus a JPG/PNG fallback. The largest copies are {kb(after)} against {kb(before)} before ({saved}). "
            "Camera details like GPS location were left out and photos are the right way up. pictures.html has a "
            "ready <picture> tag for each one; change the alt words to say what each shows."
            + (f" Heads up: {', '.join(heavy)} {'is' if len(heavy) == 1 else 'are'} still over 300KB; try quality 70 "
               "or a smaller widest size." if heavy else ""))


def tool_definitions() -> list[dict]:
    return [{
        "name": "make_web_images",
        "description": "Make a client's photos web-ready: WebP copies at several widths (480/960/1600px by default) "
                       "plus a JPG or PNG fallback, turned the right way up with GPS and camera details removed, "
                       "saved in a web/ folder beside them, with pictures.html giving a ready <picture> tag (srcset, "
                       "sizes, width/height, lazy loading) for each. Does one picture or a whole memory folder (up to "
                       "30). Use before pictures go into a Kinetic site. Answer in plain words.",
        "input_schema": {
            "type": "object",
            "properties": {
                "folder": {"type": "string", "description": "Memory folder with the pictures, e.g. 'Kinetic Web "
                                                            "Designs/Lebo's Bakery/photos'."},
                "file": {"type": "string", "description": "One picture in that folder (default: all of them)."},
                "widths": {"type": "array", "items": {"type": "integer"}, "description": "Widths in px (default "
                                                                                          "480, 960, 1600)."},
                "quality": {"type": "integer", "minimum": 40, "maximum": 95, "description": "Default 80."},
                "sizes": {"type": "string", "description": "CSS sizes, e.g. '(min-width: 1024px) 50vw, 100vw' "
                                                          "for a half-width picture (default 100vw)."},
                "alt": {"type": "string", "description": "Alt words for the picture (default from the file name)."},
            },
            "required": ["folder"],
            "additionalProperties": False,
        },
    }]


async def run_tool(name: str, args: dict, settings: Settings, http=None) -> str:
    try:
        return run(settings, args)
    except (TypeError, ValueError) as e:
        return str(e)
