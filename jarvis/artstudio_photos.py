"""Photo effects with Pillow, always saved as a new copy that pops up: filters (sepia, vintage, blur, sharpen,
invert, posterize, pixelate, vignette, noir), brightness and contrast, borders and frames, rounded corners, a text
watermark, centred crops to a shape (square, 16:9, phone wallpaper...) and memes with top and bottom captions.
"""

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps

import artstudio_common as ac
import screen
from config import Settings

FILTERS = ("sepia", "vintage", "blur", "sharpen", "invert", "posterize", "pixelate", "vignette", "noir")
ADJUSTMENTS = ("brighten", "darken", "more_contrast", "less_contrast")
RATIOS = {"1:1": (1, 1), "16:9": (16, 9), "4:3": (4, 3), "3:2": (3, 2), "9:16": (9, 16), "4:5": (4, 5),
          "3:4": (3, 4), "21:9": (21, 9)}
POSITIONS = ("bottom_right", "bottom_left", "top_right", "top_left", "centre")
SEPIA = (0.393, 0.769, 0.189, 0, 0.349, 0.686, 0.168, 0, 0.272, 0.534, 0.131, 0)


def sepia(im: Image.Image) -> Image.Image:
    return ac.rgb(im).convert("RGB", SEPIA)


def vignette(im: Image.Image, strength: float = 0.7) -> Image.Image:
    im = ac.rgb(im)
    mask = Image.radial_gradient("L").resize(im.size, Image.BILINEAR)
    mask = mask.point(lambda v: int(max(0, v - 90) * 255 / 165 * strength))
    return Image.composite(Image.new("RGB", im.size, "black"), im, mask)


def apply_filter(im: Image.Image, effect: str) -> Image.Image:
    edge = max(im.size)
    if effect == "sepia":
        return sepia(im)
    if effect == "vintage":
        faded = ImageEnhance.Contrast(Image.blend(ac.rgb(im), sepia(im), 0.65)).enhance(0.85)
        return vignette(ImageEnhance.Brightness(faded).enhance(1.05), 0.5)
    if effect == "blur":
        return ac.rgb(im).filter(ImageFilter.GaussianBlur(max(2, edge / 250)))
    if effect == "sharpen":
        return ac.rgb(im).filter(ImageFilter.UnsharpMask(radius=2, percent=160, threshold=3))
    if effect == "invert":
        return ImageOps.invert(ac.rgb(im))
    if effect == "posterize":
        return ImageOps.posterize(ac.rgb(im), 3)
    if effect == "pixelate":
        block = max(4, edge // 64)
        small = ac.rgb(im).resize((max(1, im.width // block), max(1, im.height // block)), Image.BILINEAR)
        return small.resize(im.size, Image.NEAREST)
    if effect == "vignette":
        return vignette(im)
    if effect == "noir":
        grey = ImageOps.autocontrast(ImageOps.grayscale(ac.rgb(im)), cutoff=2)
        return ImageEnhance.Contrast(grey).enhance(1.8)
    raise ValueError(f"I know these filters: {', '.join(FILTERS)}.")


def adjust(im: Image.Image, how: str, amount) -> Image.Image:
    step = min(max(float(amount or 30), 1), 100) / 100
    im = ac.rgb(im)
    if how == "brighten":
        return ImageEnhance.Brightness(im).enhance(1 + step)
    if how == "darken":
        return ImageEnhance.Brightness(im).enhance(1 - step * 0.9)
    if how == "more_contrast":
        return ImageEnhance.Contrast(im).enhance(1 + step)
    if how == "less_contrast":
        return ImageEnhance.Contrast(im).enhance(1 - step * 0.9)
    raise ValueError("I can brighten, darken, or give more or less contrast.")


def border(im: Image.Image, colour: str, width, style: str) -> Image.Image:
    im = ac.rgb(im)
    edge = min(im.size)
    w = int(width) if width else max(4, edge // 25)
    w = min(max(w, 1), edge)
    if style == "polaroid":
        return ImageOps.expand(im, (w, w, w, w * 4), fill=colour)
    if style == "double":
        inner = ImageOps.expand(im, max(1, w // 4), fill="black" if colour != "#000000" else "white")
        return ImageOps.expand(inner, w, fill=colour)
    return ImageOps.expand(im, w, fill=colour)


def rounded(im: Image.Image, percent) -> Image.Image:
    im = im.convert("RGBA")
    radius = int(min(im.size) * min(max(float(percent or 8), 1), 50) / 100)
    mask = Image.new("L", im.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, im.width - 1, im.height - 1), radius, fill=255)
    im.putalpha(Image.composite(im.getchannel("A"), mask, mask))
    return im


def watermark(im: Image.Image, text: str, position: str, opacity) -> Image.Image:
    if not text.strip():
        raise ValueError("What should the watermark say?")
    im = im.convert("RGBA")
    size = max(12, min(im.size) // 18)
    font = ac.font(size)
    layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    tw, th = right - left, bottom - top
    pad = size
    x = {"left": pad, "right": im.width - tw - pad}.get(position.split("_")[-1], (im.width - tw) // 2)
    y = {"top": pad, "bottom": im.height - th - pad}.get(position.split("_")[0], (im.height - th) // 2)
    alpha = int(255 * min(max(float(opacity or 50), 5), 100) / 100)
    draw.text((x - left + 2, y - top + 2), text, font=font, fill=(0, 0, 0, alpha // 2))
    draw.text((x - left, y - top), text, font=font, fill=(255, 255, 255, alpha))
    return Image.alpha_composite(im, layer)


def crop(im: Image.Image, ratio: str) -> Image.Image:
    if ratio not in RATIOS:
        raise ValueError(f"I can crop to {', '.join(RATIOS)}.")
    rw, rh = RATIOS[ratio]
    w, h = im.size
    if w * rh > h * rw:
        nw, nh = h * rw // rh, h
    else:
        nw, nh = w, w * rh // rw
    x, y = (w - nw) // 2, (h - nh) // 2
    return im.crop((x, y, x + nw, y + nh))


def wrap(draw: ImageDraw.ImageDraw, text: str, font, width: int) -> list[str]:
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if line and draw.textlength(trial, font=font) > width:
            lines.append(line)
            line = word
        else:
            line = trial
    return lines + [line] if line else lines


def caption(draw: ImageDraw.ImageDraw, im: Image.Image, text: str, top: bool) -> None:
    text = " ".join(text.upper().split())
    if not text:
        return
    size = max(14, im.height // 9)
    while True:
        font = ac.font(size)
        lines = wrap(draw, text, font, int(im.width * 0.94))
        widest = max(draw.textlength(line, font=font) for line in lines)
        if (len(lines) <= 3 and widest <= im.width * 0.96) or size <= 14:
            break
        size = int(size * 0.88)
    stroke = max(1, size // 14)
    line_h = int(size * 1.1)
    y = int(im.height * 0.03) if top else im.height - int(im.height * 0.03) - line_h * len(lines)
    for line in lines:
        x = (im.width - draw.textlength(line, font=font)) / 2
        draw.text((x, y), line, font=font, fill="white", stroke_width=stroke, stroke_fill="black")
        y += line_h


def meme(im: Image.Image, top_text: str, bottom_text: str) -> Image.Image:
    if not (top_text or bottom_text).strip():
        raise ValueError("What should the meme say? Give top text, bottom text or both.")
    im = ac.rgb(im)
    if max(im.size) < 600:
        scale = 600 / max(im.size)
        im = im.resize((round(im.width * scale), round(im.height * scale)), Image.LANCZOS)
    draw = ImageDraw.Draw(im)
    caption(draw, im, top_text or "", True)
    caption(draw, im, bottom_text or "", False)
    return im


def run_edit(settings: Settings, args: dict) -> screen.Shown:
    action = args.get("action")
    path, im = ac.load(settings, args.get("folder") or "", args.get("filename") or "")
    if action == "filter":
        effect = args.get("effect") or ""
        out, tag = apply_filter(im, effect), effect
    elif action == "adjust":
        how = args.get("adjustment") or ""
        out, tag = adjust(im, how, args.get("amount")), how.replace("_", " ")
    elif action == "border":
        style = args.get("style") or "plain"
        out = border(im, ac.hex_colour(args.get("colour"), "#ffffff"), args.get("width"), style)
        tag = "polaroid" if style == "polaroid" else "border"
    elif action == "rounded_corners":
        out, tag = rounded(im, args.get("amount")), "rounded"
    elif action == "watermark":
        out, tag = watermark(im, str(args.get("text") or ""), args.get("position") or "bottom_right",
                             args.get("amount")), "watermarked"
    elif action == "crop":
        ratio = args.get("ratio") or "1:1"
        out, tag = crop(im, ratio), "square" if ratio == "1:1" else ratio.replace(":", "x")
    elif action == "meme":
        out, tag = meme(im, str(args.get("top_text") or ""), str(args.get("bottom_text") or "")), "meme"
    else:
        raise ValueError("Pick filter, adjust, border, rounded_corners, watermark, crop or meme.")
    target = ac.save_copy(settings, out, path, tag, args.get("save_to") or "")
    return ac.shown(settings, target, f"Done. I saved a new copy, {target.name}.")


def tool_definitions() -> list[dict]:
    return [{
        "name": "art_photo_effects",
        "description": "Photo effects on a picture in the memory folders, saved as a new copy that pops up (the "
                       "original is kept). action 'filter' (effect: sepia, vintage, blur, sharpen, invert, posterize, "
                       "pixelate, vignette, noir = high-contrast black and white); 'adjust' (brighten, darken, "
                       "more_contrast, less_contrast; amount 1-100); 'border' or frame (colour, width, style plain, "
                       "polaroid or double); 'rounded_corners' (amount = corner size percent); 'watermark' (text, "
                       "position, amount = opacity percent); 'crop' centred to a ratio (1:1 square, 16:9, 4:3, 9:16 "
                       "phone wallpaper...); 'meme' (top_text, bottom_text in big outlined letters).",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["filter", "adjust", "border", "rounded_corners", "watermark",
                                                      "crop", "meme"]},
                "folder": {"type": "string", "description": "Memory folder of the picture, e.g. Personal/Holiday."},
                "filename": {"type": "string", "description": "The picture's name or part of it."},
                "effect": {"type": "string", "enum": list(FILTERS)},
                "adjustment": {"type": "string", "enum": list(ADJUSTMENTS)},
                "amount": {"type": "number", "description": "Strength in percent (1-100)."},
                "colour": {"type": "string", "description": "border: colour name or hex (default white)."},
                "width": {"type": "integer", "description": "border: thickness in pixels."},
                "style": {"type": "string", "enum": ["plain", "polaroid", "double"]},
                "text": {"type": "string", "description": "watermark: the words, e.g. '© 2026 My Photos'."},
                "position": {"type": "string", "enum": list(POSITIONS)},
                "ratio": {"type": "string", "enum": list(RATIOS)},
                "top_text": {"type": "string"},
                "bottom_text": {"type": "string"},
                "save_to": {"type": "string", "description": "Folder for the copy (default: next to the original)."},
            },
            "required": ["action", "filename"],
            "additionalProperties": False,
        },
    }]


NAMES = {"art_photo_effects"}


def run_tool(name: str, args: dict, settings: Settings, http=None) -> screen.Shown:
    return run_edit(settings, args)
