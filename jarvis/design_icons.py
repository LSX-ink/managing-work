"""App icons: every favicon and home-screen icon a website needs, from the brand initials or the client's own logo.

make_app_icons draws one sharp master icon (the initials tile in the brand colour, or a logo picture from a memory
folder centred on a background) and saves the whole set browsers and phones look for: favicon.ico (16, 32 and 48px
inside), favicon-32.png, apple-touch-icon.png (180px, solid, for iPhone home screens), icon-192.png and icon-512.png
for Android and installable sites, and icon-maskable-512.png with the mark inside the safe zone so Android's circle or
squircle crop never cuts it. It also writes site.webmanifest (name, colours, icons), head-tags.html to paste into the
page's <head>, and icons.html to check them on light and dark and in the circle crop. Files go in
Kinetic Web Designs/<name>/icons, next to the logo and share card.
"""

import html
import json

from PIL import Image, ImageDraw

import memory
from config import Settings
from design_contrast import colour, rgb
from design_extract import FOLDER
from design_logo import initials
from design_palette import on
from docs_tools import font

NAMES = {"make_app_icons"}
MASTER = 1024
PICTURES = {".png", ".jpg", ".jpeg", ".webp"}
MAX_PIXELS = 40_000_000
SAFE = 0.8  # maskable icons: Android may crop to a circle 80% of the width, so the mark stays inside it
SHORT_MAX = 12  # home-screen labels cut off after about 12 letters


def tile(mark: str, brand: str, size: int = MASTER, rounded: bool = True, scale: float = 1.0) -> Image.Image:
    """The initials in the brand colour; `scale` shrinks the letters (maskable icons keep them in the safe zone)."""
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(image)
    if rounded:
        d.rounded_rectangle((0, 0, size - 1, size - 1), radius=round(size * 0.22), fill=rgb(brand))
    else:
        d.rectangle((0, 0, size, size), fill=rgb(brand))
    letters = round(size * (0.46 if len(mark) == 1 else 0.4) * scale)
    d.text((size / 2, size / 2), mark, font=font(letters, True), fill=rgb(on(brand)), anchor="mm")
    return image


def picture(logo: Image.Image, background: str, size: int = MASTER, room: float = 0.72,
            rounded: bool = True) -> Image.Image:
    """The logo fitted inside `room` of the square, centred on the background colour."""
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(image)
    if rounded:
        d.rounded_rectangle((0, 0, size - 1, size - 1), radius=round(size * 0.22), fill=rgb(background))
    else:
        d.rectangle((0, 0, size, size), fill=rgb(background))
    box = round(size * room)
    k = box / max(logo.size)  # big logos shrink and small ones grow to fill the space
    art = logo.convert("RGBA").resize((max(1, round(logo.width * k)), max(1, round(logo.height * k))), Image.LANCZOS)
    image.alpha_composite(art, ((size - art.width) // 2, (size - art.height) // 2))
    return image


def load(path) -> Image.Image:
    if path.suffix.lower() not in PICTURES:
        raise ValueError("Use a PNG, JPG or WebP logo (an SVG can't be drawn here; export it as a PNG first).")
    try:
        with Image.open(path) as image:
            if image.width * image.height > MAX_PIXELS:
                raise ValueError("That picture is too big; use a logo under 40 megapixels.")
            logo = image.convert("RGBA")
    except OSError:
        raise ValueError("I couldn't open that picture.") from None
    if max(logo.size) < 192:
        raise ValueError("That logo is too small for app icons; use one at least 192px (512px or more is best).")
    return logo


def solid(image: Image.Image, background: str) -> Image.Image:
    """iPhones fill see-through corners with black, so the touch icon gets a solid background."""
    out = Image.new("RGB", image.size, rgb(background))
    out.paste(image, (0, 0), image)
    return out


def icons(mark: str, brand: str, logo: Image.Image | None, background: str) -> dict[str, Image.Image]:
    if logo is None:
        main, full = tile(mark, brand), tile(mark, brand, rounded=False)
        safe = tile(mark, brand, rounded=False, scale=0.8)
    else:
        main = picture(logo, background)
        full = picture(logo, background, rounded=False, room=0.8)
        safe = picture(logo, background, rounded=False, room=SAFE * 0.7)  # a square logo's corners stay in the circle
    small = lambda img, n: img.resize((n, n), Image.LANCZOS)  # noqa: E731
    fill = brand if logo is None else background
    return {"favicon-32.png": small(main, 32), "apple-touch-icon.png": solid(small(full, 180), fill),
            "icon-192.png": small(main, 192), "icon-512.png": small(main, 512),
            "icon-maskable-512.png": solid(small(safe, 512), fill), "favicon.ico": small(main, 256)}


def manifest(name: str, short: str, theme: str, background: str) -> str:
    data = {"name": name, "short_name": short, "start_url": "/", "display": "standalone", "theme_color": theme,
            "background_color": background,
            "icons": [{"src": "icon-192.png", "sizes": "192x192", "type": "image/png"},
                      {"src": "icon-512.png", "sizes": "512x512", "type": "image/png"},
                      {"src": "icon-maskable-512.png", "sizes": "512x512", "type": "image/png",
                       "purpose": "maskable"}]}
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def head_tags(theme: str) -> str:
    return ("<!-- Paste into the page's <head> and upload every file in this folder to the site's main folder. -->\n"
            '<link rel="icon" href="/favicon.ico" sizes="48x48">\n'
            '<link rel="icon" href="/favicon-32.png" type="image/png" sizes="32x32">\n'
            '<link rel="apple-touch-icon" href="/apple-touch-icon.png">\n'
            '<link rel="manifest" href="/site.webmanifest">\n'
            f'<meta name="theme-color" content="{theme}">\n')


def preview(name: str) -> str:
    cells = "".join(f'<figure><img src="{f}" width="{w}" height="{w}" alt="{f}"><figcaption>{f}</figcaption></figure>'
                    for f, w in (("favicon-32.png", 32), ("apple-touch-icon.png", 90), ("icon-192.png", 96),
                                 ("icon-512.png", 128)))
    crop = ('<figure><img class="circle" src="icon-maskable-512.png" width="128" height="128" '
            'alt="maskable icon in a circle"><figcaption>maskable, circle crop</figcaption></figure>')
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(name)} icons</title><style>
body {{ margin: 0; font-family: system-ui, sans-serif; }}
section {{ display: flex; flex-wrap: wrap; gap: 32px; align-items: end; padding: 32px; }}
.light {{ background: #ffffff; color: #3f3f46; }} .dark {{ background: #18181b; color: #d4d4d8; }}
figure {{ margin: 0; text-align: center; }} figcaption {{ font-size: 13px; margin-top: 8px; }}
.circle {{ border-radius: 50%; }}
</style></head><body>
<section class="light"><h1 style="width:100%;margin:0">{html.escape(name)} icons</h1>{cells}{crop}</section>
<section class="dark">{cells}{crop}</section>
</body></html>
"""


def run(settings: Settings, args: dict) -> str:
    name = " ".join(str(args.get("name") or "").split())
    if not name:
        raise ValueError("Give the brand or client a name for the icons.")
    brand = colour(args.get("colour") or "")
    background = colour(args.get("background") or "#ffffff")
    logo = None
    if args.get("file"):
        if not args.get("folder"):
            raise ValueError("Say which memory folder the logo picture is in.")
        logo = load(memory.file_path(settings, str(args["folder"]), str(args["file"])))
    mark = initials(name, str(args.get("initials") or ""))
    short = " ".join(str(args.get("short_name") or "").split()) or (name if len(name) <= SHORT_MAX
                                                                    else name.split()[0][:SHORT_MAX])
    (memory.root(settings) / FOLDER).mkdir(parents=True, exist_ok=True)
    path = memory.folder(settings, f"{FOLDER}/{memory.safe_name(name, 'folder name')}/icons", create=True)
    for filename, image in icons(mark, brand, logo, background).items():
        if filename == "favicon.ico":
            image.save(path / filename, sizes=[(16, 16), (32, 32), (48, 48)])
        else:
            image.save(path / filename, optimize=True)
    (path / "site.webmanifest").write_text(manifest(name, short, brand, background), encoding="utf-8")
    (path / "head-tags.html").write_text(head_tags(brand), encoding="utf-8")
    (path / "icons.html").write_text(preview(name), encoding="utf-8")
    where = path.relative_to(memory.root(settings)).as_posix()
    notes = []
    if len(short) > SHORT_MAX:
        notes.append(f"the short name is {len(short)} letters, so phones may cut it after about {SHORT_MAX}")
    return (f"Made the app icons for {name} from {'the logo ' + str(args['file']) if logo else 'the initials ' + mark} "
            f"in {where}: favicon.ico, favicon-32.png, apple-touch-icon.png, icon-192.png, icon-512.png and "
            f"icon-maskable-512.png, plus site.webmanifest (home-screen name '{short}') and head-tags.html to paste "
            "into the page's <head>. Open icons.html to check them on light and dark."
            + (" Heads up: " + "; ".join(notes) + "." if notes else ""))


def tool_definitions() -> list[dict]:
    return [{
        "name": "make_app_icons",
        "description": "Make a website's full icon set: favicon.ico, favicon-32.png, apple-touch-icon.png (iPhone home "
                       "screen), icon-192/512.png and a maskable icon for Android, plus site.webmanifest and the "
                       "<head> tags. Draws the brand initials in the brand colour, or uses the client's logo picture "
                       "from a memory folder. Saves in Kinetic Web Designs/<name>/icons with icons.html to check "
                       "them. Answer in plain words.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Brand or client name (the folder)."},
                "colour": {"type": "string", "description": "Brand colour, e.g. '#c2410c' (tile and theme colour)."},
                "folder": {"type": "string", "description": "Memory folder with a logo picture to use (optional)."},
                "file": {"type": "string", "description": "Logo PNG/JPG/WebP in that folder, at least 192px."},
                "background": {"type": "string", "description": "Background behind a logo picture (default white)."},
                "short_name": {"type": "string", "description": "Home-screen label, up to 12 letters."},
                "initials": {"type": "string", "description": "1-2 letters instead of the name's initials."},
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
