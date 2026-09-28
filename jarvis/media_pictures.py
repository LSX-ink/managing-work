"""Editing pictures in the memory folders with Pillow, always saving a new copy next to the original.

Resize, rotate, convert (png/jpg/webp) and greyscale one picture; turn a folder of pictures into a PDF, an animated
GIF or a contact sheet. Each result pops up on the Alfred screen.
"""

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

import media_common as mc
import memory
import screen
from config import Settings

FORMATS = {"png": "PNG", "jpg": "JPEG", "jpeg": "JPEG", "webp": "WEBP"}
MAX_PICTURES = 100
PDF_EDGE, GIF_EDGE, CELL = 2000, 640, 200


def _open(path: Path) -> Image.Image:
    try:
        with Image.open(path) as im:
            im.load()
            return ImageOps.exif_transpose(im)
    except (OSError, Image.DecompressionBombError):
        raise ValueError(f"I can't open {path.name} as a picture.")


def _save(im: Image.Image, target: Path) -> Path:
    fmt = FORMATS.get(target.suffix.lower().lstrip("."), "PNG")
    if fmt == "JPEG" and im.mode not in ("RGB", "L"):
        im = im.convert("RGB")
    target = memory.unique_path(target)
    im.save(target, fmt)
    return target


def _picture(settings: Settings, folder: str, filename: str) -> Path:
    path = mc.user_file(settings, folder, filename)
    if path.suffix.lower() not in mc.PICTURES:
        raise ValueError(f"{path.name} isn't a picture I can edit.")
    return path


def _out(path: Path, tag: str, suffix: str = "") -> Path:
    suffix = suffix or (path.suffix if path.suffix.lower().lstrip(".") in FORMATS else ".png")
    return path.with_name(f"{path.stem} {tag}{suffix}")


def edit(settings: Settings, action: str, folder: str, filename: str, args: dict) -> screen.Shown:
    path = _picture(settings, folder, filename)
    im = _open(path)
    if action == "resize":
        width, percent = args.get("width"), args.get("percent")
        if width:
            width = int(min(max(width, 8), 10000))
            size = (width, max(1, round(im.height * width / im.width)))
        elif percent:
            scale = min(max(float(percent), 1), 400) / 100
            size = (max(1, round(im.width * scale)), max(1, round(im.height * scale)))
        else:
            raise ValueError("How big? Give a width in pixels or a percentage.")
        im, tag = im.resize(size, Image.LANCZOS), f"{size[0]}x{size[1]}"
    elif action == "rotate":
        degrees = float(args.get("degrees") or 90)
        im, tag = im.rotate(-degrees, expand=True, resample=Image.BICUBIC), f"rotated {degrees:g}"
    elif action == "greyscale":
        im, tag = ImageOps.grayscale(im), "greyscale"
    else:
        fmt = str(args.get("format") or "").lower().lstrip(".")
        if fmt not in FORMATS:
            raise ValueError("I can convert to png, jpg or webp.")
        target = _save(im, path.with_suffix("." + fmt))
        return screen.Shown(f"Saved a {fmt.upper()} copy, {target.name}.", screen.file_card(settings, target))
    target = _save(im, _out(path, tag))
    return screen.Shown(f"Saved it as {target.name}.", screen.file_card(settings, target))


def _pictures(settings: Settings, folder: str) -> list[Path]:
    found = mc.files_in(settings, folder, mc.PICTURES)[:MAX_PICTURES]
    if not found:
        raise ValueError(f"There are no pictures in {folder}.")
    return found


def _fit(im: Image.Image, edge: int) -> Image.Image:
    im = im.convert("RGB")
    im.thumbnail((edge, edge), Image.LANCZOS)
    return im


def make_pdf(settings: Settings, folder: str) -> screen.Shown:
    pictures = _pictures(settings, folder)
    pages = [_fit(_open(p), PDF_EDGE) for p in pictures]
    top = mc.folder(settings, folder)
    target = memory.unique_path(top / f"{top.name} pictures.pdf")
    pages[0].save(target, "PDF", save_all=True, append_images=pages[1:], resolution=150)
    return screen.Shown(f"Made a {len(pages)}-page PDF, {target.name}.", screen.file_card(settings, target))


def make_gif(settings: Settings, folder: str, seconds) -> screen.Shown:
    pictures = _pictures(settings, folder)
    frames = [_fit(_open(p), GIF_EDGE) for p in pictures]
    w, h = max(f.width for f in frames), max(f.height for f in frames)
    canvas = []
    for f in frames:
        frame = Image.new("RGB", (w, h), "black")
        frame.paste(f, ((w - f.width) // 2, (h - f.height) // 2))
        canvas.append(frame)
    top = mc.folder(settings, folder)
    target = memory.unique_path(top / f"{top.name} animation.gif")
    ms = int(min(max(float(seconds or 0.8), 0.05), 10) * 1000)
    canvas[0].save(target, "GIF", save_all=True, append_images=canvas[1:], duration=ms, loop=0)
    return screen.Shown(f"Made a GIF of {len(frames)} pictures, {target.name}.", screen.file_card(settings, target))


def contact_sheet(settings: Settings, folder: str) -> screen.Shown:
    pictures = _pictures(settings, folder)
    cols = min(8, math.ceil(math.sqrt(len(pictures))))
    rows = math.ceil(len(pictures) / cols)
    pad, label = 10, 16
    sheet = Image.new("RGB", (cols * (CELL + pad) + pad, rows * (CELL + label + pad) + pad), "black")
    draw = ImageDraw.Draw(sheet)
    for n, p in enumerate(pictures):
        x, y = pad + (n % cols) * (CELL + pad), pad + (n // cols) * (CELL + label + pad)
        thumb = _fit(_open(p), CELL)
        sheet.paste(thumb, (x + (CELL - thumb.width) // 2, y + (CELL - thumb.height) // 2))
        draw.text((x, y + CELL + 2), p.name[:30], fill="white")
    top = mc.folder(settings, folder)
    target = memory.unique_path(top / f"{top.name} contact sheet.jpg")
    sheet.save(target, "JPEG", quality=88)
    return screen.Shown(f"Made a contact sheet of {len(pictures)} pictures.", screen.file_card(settings, target))


def tool_definitions() -> list[dict]:
    return [{
        "name": "edit_pictures",
        "description": "Edit photos and pictures in the memory folders, saving a new copy next to the original and "
                       "showing it. One picture: action 'resize' (width or percent), 'rotate' (degrees clockwise), "
                       "'convert' (to png, jpg or webp), 'greyscale' (black and white). A whole folder of pictures: "
                       "'pdf' makes one PDF, 'gif' an animated GIF, 'contact_sheet' one image of thumbnails.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["resize", "rotate", "convert", "greyscale", "pdf", "gif",
                                                      "contact_sheet"]},
                "folder": {"type": "string", "description": "Memory folder, e.g. 'Personal' or 'Personal/Holiday'."},
                "filename": {"type": "string", "description": "One-picture actions: its name or part of it."},
                "width": {"type": "integer", "description": "resize: new width in pixels."},
                "percent": {"type": "number", "description": "resize: new size as a percentage, e.g. 50."},
                "degrees": {"type": "number", "description": "rotate: degrees clockwise (default 90)."},
                "format": {"type": "string", "enum": ["png", "jpg", "webp"]},
                "seconds": {"type": "number", "description": "gif: seconds per picture (default 0.8)."},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"edit_pictures"}


def run_tool(name: str, args: dict, settings: Settings, http=None) -> screen.Shown:
    action, folder = args.get("action"), args.get("folder") or ""
    if action in ("resize", "rotate", "convert", "greyscale"):
        return edit(settings, action, folder, args.get("filename") or "", args)
    if action == "pdf":
        return make_pdf(settings, folder)
    if action == "gif":
        return make_gif(settings, folder, args.get("seconds"))
    if action == "contact_sheet":
        return contact_sheet(settings, folder)
    raise ValueError("Pick resize, rotate, convert, greyscale, pdf, gif or contact_sheet.")
