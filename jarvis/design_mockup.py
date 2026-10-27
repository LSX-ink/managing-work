"""Device mock-ups: a website screenshot shown in a browser window and on a phone, ready for pitches and posts.

make_mockup takes a screenshot (or mock-up picture) from a memory folder and draws it inside a clean browser window
with the web address in the bar, inside a phone with rounded corners and a camera notch, and as a combined hero shot
with the phone overlapping the browser, all on a soft gradient from make_gradient in the brand colour. The phone shows
the top of the page at phone width. Pictures are saved next to the screenshot as mockup-browser.png,
mockup-phone.png and mockup-combo.png, so outreach emails and Instagram posts can show a site the way a client sees
it. Nothing is uploaded anywhere.
"""

from PIL import Image, ImageDraw, ImageFilter

import design_gradient
import memory
from config import Settings
from design_contrast import colour
from design_palette import scale
from docs_tools import font

NAMES = {"make_mockup"}
PICTURES = {".png", ".jpg", ".jpeg", ".webp"}
MAX_PIXELS = 40_000_000
BAR = 64  # browser top bar height at 1440px wide


def rounded(image: Image.Image, radius: int) -> Image.Image:
    mask = Image.new("L", image.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, image.width - 1, image.height - 1), radius=radius, fill=255)
    out = image.convert("RGBA")
    out.putalpha(mask)
    return out


def shadow(size: tuple[int, int], radius: int, blur: int, strength: int = 90) -> Image.Image:
    pad = blur * 3
    layer = Image.new("RGBA", (size[0] + pad * 2, size[1] + pad * 2), (0, 0, 0, 0))
    ImageDraw.Draw(layer).rounded_rectangle((pad, pad + blur // 2, pad + size[0], pad + size[1] + blur // 2),
                                            radius=radius, fill=(0, 0, 0, strength))
    return layer.filter(ImageFilter.GaussianBlur(blur))


def top(shot: Image.Image, width: int, height: int) -> Image.Image:
    """The page scaled to `width`, cut to its top `height` pixels (white below a short page)."""
    page = shot.convert("RGB").resize((width, max(1, round(shot.height * width / shot.width))), Image.LANCZOS)
    out = Image.new("RGB", (width, height), (255, 255, 255))
    out.paste(page.crop((0, 0, width, min(height, page.height))), (0, 0))
    return out


def browser(shot: Image.Image, address: str, width: int = 1440, view: int = 900) -> Image.Image:
    """The top `view` pixels of the page in a light browser window."""
    page = top(shot, width, view)
    window = Image.new("RGB", (width, view + BAR), (246, 246, 247))
    d = ImageDraw.Draw(window)
    for i, dot in enumerate([(255, 95, 87), (254, 188, 46), (40, 200, 64)]):
        x = 28 + i * 26
        d.ellipse((x, BAR / 2 - 7, x + 14, BAR / 2 + 7), fill=dot)
    d.rounded_rectangle((140, 14, width - 140, BAR - 14), radius=(BAR - 28) // 2, fill=(255, 255, 255),
                        outline=(225, 225, 228))
    d.text((width / 2, BAR / 2), address or "your-site.co.uk", font=font(20), fill=(90, 90, 96), anchor="mm")
    d.line((0, BAR - 1, width, BAR - 1), fill=(225, 225, 228))
    window.paste(page, (0, BAR))
    return rounded(window, 14)


def phone(shot: Image.Image, width: int = 390, height: int = 844) -> Image.Image:
    """The top of the page squeezed to phone width inside a dark phone body with a camera notch."""
    screen = top(shot, width, height)
    bezel = 14
    body = Image.new("RGBA", (width + bezel * 2, height + bezel * 2), (0, 0, 0, 0))
    ImageDraw.Draw(body).rounded_rectangle((0, 0, body.width - 1, body.height - 1), radius=62, fill=(17, 17, 20))
    body.alpha_composite(rounded(screen, 48), (bezel, bezel))
    ImageDraw.Draw(body).rounded_rectangle((body.width / 2 - 62, bezel + 10, body.width / 2 + 62, bezel + 44),
                                           radius=17, fill=(17, 17, 20))
    return body


def backdrop(brand: str, size: tuple[int, int]) -> Image.Image:
    shades = scale(brand)
    g = design_gradient.build([shades[100], shades[300]], "linear", 135)
    return design_gradient.draw(g, size).convert("RGBA")


def place(canvas: Image.Image, item: Image.Image, xy: tuple[int, int], radius: int):
    blur = max(12, item.width // 40)
    s = shadow(item.size, radius, blur)
    canvas.alpha_composite(s, (xy[0] - blur * 3, xy[1] - blur * 3))
    canvas.alpha_composite(item, xy)


def build(shot: Image.Image, brand: str, address: str, small: Image.Image | None = None) -> dict[str, Image.Image]:
    win, mobile = browser(shot, address), phone(small or shot)
    out = {}
    c = backdrop(brand, (win.width + 240, win.height + 240))
    place(c, win, (120, 120), 14)
    out["mockup-browser.png"] = c
    c = backdrop(brand, (mobile.width + 240, mobile.height + 240))
    place(c, mobile, (120, 120), 62)
    out["mockup-phone.png"] = c
    c = backdrop(brand, (1920, 1200))
    wide = win.resize((1500, round(win.height * 1500 / win.width)), Image.LANCZOS)
    place(c, wide, (120, (1200 - wide.height) // 2 - 40), 12)
    tall = mobile.resize((round(mobile.width * 0.95), round(mobile.height * 0.95)), Image.LANCZOS)
    place(c, tall, (1920 - tall.width - 110, 1200 - tall.height - 70), 60)
    out["mockup-combo.png"] = c
    return out


def load(path) -> Image.Image:
    if path.suffix.lower() not in PICTURES:
        raise ValueError("Use a PNG, JPG or WebP screenshot.")
    try:
        with Image.open(path) as image:
            if image.width * image.height > MAX_PIXELS:
                raise ValueError("That picture is too big; use a screenshot under 40 megapixels.")
            shot = image.convert("RGB")
    except OSError:
        raise ValueError("I couldn't open that picture.") from None
    if shot.width < 320 or shot.height < 200:
        raise ValueError("That picture is too small for a mock-up; use a full-page or full-screen screenshot.")
    return shot


def run(settings: Settings, args: dict) -> str:
    folder, name = str(args.get("folder") or "").strip(), str(args.get("file") or "").strip()
    if not folder or not name:
        raise ValueError("Say which memory folder and picture to use, e.g. folder 'Kinetic Web Designs/Lebo's "
                         "Bakery' and file 'home.png'.")
    path = memory.file_path(settings, folder, name)
    shot = load(path)
    small = load(memory.file_path(settings, folder, str(args["phone_file"]))) if args.get("phone_file") else None
    brand = colour(args.get("colour") or "#6366f1")
    made = build(shot, brand, str(args.get("address") or "").strip(), small)
    for filename, image in made.items():
        image.convert("RGB").save(path.parent / filename, optimize=True)
    where = path.parent.relative_to(memory.root(settings)).as_posix()
    return (f"Made {', '.join(made)} from {name} in {where}: the site in a browser window, on a phone, and both "
            "together on a soft background in the brand colour. Use them in outreach emails, proposals or posts.")


def tool_definitions() -> list[dict]:
    return [{
        "name": "make_mockup",
        "description": "Turn a website screenshot or mock-up picture in a memory folder into device mock-ups: the "
                       "site in a browser window (with its web address), on a phone, and both together on a soft "
                       "gradient in the brand colour. Saves mockup-browser.png, mockup-phone.png and "
                       "mockup-combo.png next to the screenshot. Use for Kinetic outreach, proposals and social posts. "
                       "Answer in plain words.",
        "input_schema": {
            "type": "object",
            "properties": {
                "folder": {"type": "string", "description": "Memory folder with the screenshot, e.g. 'Kinetic Web "
                                                            "Designs/Lebo's Bakery'."},
                "file": {"type": "string", "description": "The screenshot file, e.g. 'home.png'."},
                "phone_file": {"type": "string", "description": "Optional phone-width screenshot for the phone "
                                                                "(otherwise the main one is scaled down)."},
                "address": {"type": "string", "description": "Web address for the browser bar, e.g. lebos.co.uk."},
                "colour": {"type": "string", "description": "Brand colour for the background, e.g. '#c2410c'."},
            },
            "required": ["folder", "file"],
            "additionalProperties": False,
        },
    }]


async def run_tool(name: str, args: dict, settings: Settings, http=None) -> str:
    try:
        return run(settings, args)
    except (TypeError, ValueError) as e:
        return str(e)
