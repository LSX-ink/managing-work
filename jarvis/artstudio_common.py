"""Shared helpers for the art-studio abilities: opening pictures from the memory folders, fonts and saving new ones.

Every picture Alfred makes is a new file: edits go next to the original (or into save_to), new creations into a
memory folder (Ideas by default). Nothing is ever overwritten.
"""

import re
from pathlib import Path

from PIL import Image, ImageFont, ImageOps

import media_common as mc
import memory
import screen
from config import Settings

HEIC = {".heic", ".heif"}
MAX_EDGE = 6000
FORMATS = {".png": "PNG", ".jpg": "JPEG", ".jpeg": "JPEG", ".webp": "WEBP"}
# The CSS named colours, spelt with grey (gray works too); cyan and magenta are aliases.
NAMED = {
    "alice blue": "#f0f8ff", "antique white": "#faebd7", "aqua": "#00ffff", "aquamarine": "#7fffd4",
    "azure": "#f0ffff", "beige": "#f5f5dc", "bisque": "#ffe4c4", "black": "#000000", "blanched almond": "#ffebcd",
    "blue": "#0000ff", "blue violet": "#8a2be2", "brown": "#a52a2a", "burly wood": "#deb887",
    "cadet blue": "#5f9ea0", "chartreuse": "#7fff00", "chocolate": "#d2691e", "coral": "#ff7f50",
    "cornflower blue": "#6495ed", "cornsilk": "#fff8dc", "crimson": "#dc143c", "dark blue": "#00008b",
    "dark cyan": "#008b8b", "dark goldenrod": "#b8860b", "dark grey": "#a9a9a9", "dark green": "#006400",
    "dark khaki": "#bdb76b", "dark magenta": "#8b008b", "dark olive green": "#556b2f", "dark orange": "#ff8c00",
    "dark orchid": "#9932cc", "dark red": "#8b0000", "dark salmon": "#e9967a", "dark sea green": "#8fbc8f",
    "dark slate blue": "#483d8b", "dark slate grey": "#2f4f4f", "dark turquoise": "#00ced1",
    "dark violet": "#9400d3", "deep pink": "#ff1493", "deep sky blue": "#00bfff", "dim grey": "#696969",
    "dodger blue": "#1e90ff", "fire brick": "#b22222", "floral white": "#fffaf0", "forest green": "#228b22",
    "fuchsia": "#ff00ff", "gainsboro": "#dcdcdc", "ghost white": "#f8f8ff", "gold": "#ffd700",
    "goldenrod": "#daa520", "grey": "#808080", "green": "#008000", "green yellow": "#adff2f", "honeydew": "#f0fff0",
    "hot pink": "#ff69b4", "indian red": "#cd5c5c", "indigo": "#4b0082", "ivory": "#fffff0", "khaki": "#f0e68c",
    "lavender": "#e6e6fa", "lavender blush": "#fff0f5", "lawn green": "#7cfc00", "lemon chiffon": "#fffacd",
    "light blue": "#add8e6", "light coral": "#f08080", "light cyan": "#e0ffff", "light goldenrod yellow": "#fafad2",
    "light grey": "#d3d3d3", "light green": "#90ee90", "light pink": "#ffb6c1", "light salmon": "#ffa07a",
    "light sea green": "#20b2aa", "light sky blue": "#87cefa", "light slate grey": "#778899",
    "light steel blue": "#b0c4de", "light yellow": "#ffffe0", "lime": "#00ff00", "lime green": "#32cd32",
    "linen": "#faf0e6", "maroon": "#800000", "medium aquamarine": "#66cdaa", "medium blue": "#0000cd",
    "medium orchid": "#ba55d3", "medium purple": "#9370db", "medium sea green": "#3cb371",
    "medium slate blue": "#7b68ee", "medium spring green": "#00fa9a", "medium turquoise": "#48d1cc",
    "medium violet red": "#c71585", "midnight blue": "#191970", "mint cream": "#f5fffa", "misty rose": "#ffe4e1",
    "moccasin": "#ffe4b5", "navajo white": "#ffdead", "navy": "#000080", "old lace": "#fdf5e6", "olive": "#808000",
    "olive drab": "#6b8e23", "orange": "#ffa500", "orange red": "#ff4500", "orchid": "#da70d6",
    "pale goldenrod": "#eee8aa", "pale green": "#98fb98", "pale turquoise": "#afeeee", "pale violet red": "#db7093",
    "papaya whip": "#ffefd5", "peach puff": "#ffdab9", "peru": "#cd853f", "pink": "#ffc0cb", "plum": "#dda0dd",
    "powder blue": "#b0e0e6", "purple": "#800080", "rebecca purple": "#663399", "red": "#ff0000",
    "rosy brown": "#bc8f8f", "royal blue": "#4169e1", "saddle brown": "#8b4513", "salmon": "#fa8072",
    "sandy brown": "#f4a460", "sea green": "#2e8b57", "seashell": "#fff5ee", "sienna": "#a0522d",
    "silver": "#c0c0c0", "sky blue": "#87ceeb", "slate blue": "#6a5acd", "slate grey": "#708090", "snow": "#fffafa",
    "spring green": "#00ff7f", "steel blue": "#4682b4", "tan": "#d2b48c", "teal": "#008080", "thistle": "#d8bfd8",
    "tomato": "#ff6347", "turquoise": "#40e0d0", "violet": "#ee82ee", "wheat": "#f5deb3", "white": "#ffffff",
    "white smoke": "#f5f5f5", "yellow": "#ffff00", "yellow green": "#9acd32",
}
ALIASES = {"cyan": "aqua", "magenta": "fuchsia"}
BY_KEY = {name.replace(" ", ""): name for name in NAMED}
# Bold fonts Windows ships; Pillow's own scalable font is the fallback.
FONTS = ("impact.ttf", "arialbd.ttf", "arial.ttf", "DejaVuSans-Bold.ttf")


def picture(settings: Settings, folder: str, filename: str) -> Path:
    """A picture in the memory folders by name, refusing iPhone HEIC photos politely."""
    path = mc.user_file(settings, folder, filename)
    suffix = path.suffix.lower()
    if suffix in HEIC:
        raise ValueError(f"{path.name} is an iPhone HEIC photo, which I can't open. On the iPhone, Settings, Camera, "
                         "Formats, Most Compatible saves new photos as JPEG; or convert it first in the Photos app.")
    if suffix not in mc.PICTURES:
        raise ValueError(f"{path.name} isn't a picture I can use.")
    return path


def open_image(path: Path) -> Image.Image:
    try:
        with Image.open(path) as im:
            im.load()
            im = ImageOps.exif_transpose(im)
    except (OSError, Image.DecompressionBombError):
        raise ValueError(f"I can't open {path.name} as a picture.")
    if max(im.size) > MAX_EDGE:
        im.thumbnail((MAX_EDGE, MAX_EDGE), Image.LANCZOS)
    return im


def load(settings: Settings, folder: str, filename: str) -> tuple[Path, Image.Image]:
    path = picture(settings, folder, filename)
    return path, open_image(path)


def rgb(im: Image.Image, background: str = "white") -> Image.Image:
    """RGB, with any transparency laid on the background colour."""
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        flat = Image.new("RGB", im.size, background)
        flat.paste(im, mask=im.getchannel("A"))
        return flat
    return im.convert("RGB")


def pictures_in(settings: Settings, folder: str, limit: int) -> list[Path]:
    found = mc.files_in(settings, folder, mc.PICTURES)[:limit]
    if not found:
        raise ValueError(f"There are no pictures in {folder or 'that folder'}.")
    return found


def font(size: int) -> ImageFont.ImageFont:
    size = max(8, int(size))
    for name in FONTS:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # Pillow before 10.1 has only the small bitmap font
        return ImageFont.load_default()


def file_name(text: str, fallback: str = "Picture") -> str:
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", str(text or "")).strip().strip(".")[:50].strip()
    return name or fallback


def save(im: Image.Image, target: Path) -> Path:
    fmt = FORMATS.get(target.suffix.lower())
    if not fmt:
        target, fmt = target.with_suffix(".png"), "PNG"
    if fmt == "JPEG":
        im = rgb(im)
    target = memory.unique_path(target)
    im.save(target, fmt, **({"quality": 92} if fmt == "JPEG" else {}))
    return target


def save_new(settings: Settings, im: Image.Image, save_to: str, name: str, suffix: str = ".png") -> Path:
    """A new picture in a memory folder (Ideas by default)."""
    top = mc.folder(settings, save_to or "Ideas")
    top.mkdir(parents=True, exist_ok=True)
    return save(im, top / f"{file_name(name)}{suffix}")


def save_copy(settings: Settings, im: Image.Image, original: Path, tag: str, save_to: str = "") -> Path:
    """An edited copy next to the original (or in save_to), named '<original> <tag>'."""
    top = mc.folder(settings, save_to) if save_to else original.parent
    suffix = original.suffix.lower() if original.suffix.lower() in FORMATS else ".png"
    if im.mode in ("RGBA", "LA") and suffix in (".jpg", ".jpeg"):
        suffix = ".png"
    return save(im, top / f"{file_name(original.stem)} {tag}{suffix}")


def shown(settings: Settings, path: Path, said: str) -> screen.Shown:
    return screen.Shown(said, screen.file_card(settings, path))


def hex_colour(value, fallback: str = "") -> str:
    """'#rrggbb' from a hex code like 3fa9ff or #3FA9FF, or a CSS colour name."""
    text = str(value or "").strip()
    if not text:
        if fallback:
            return fallback
        raise ValueError("Which colour? Say a name like teal or a hex code like #3fa9ff.")
    if re.fullmatch(r"#?[0-9a-fA-F]{6}", text):
        return "#" + text.lstrip("#").lower()
    if re.fullmatch(r"#?[0-9a-fA-F]{3}", text):
        return "#" + "".join(c * 2 for c in text.lstrip("#").lower())
    key = re.sub(r"[\s_-]", "", text.lower()).replace("gray", "grey")
    name = BY_KEY.get(key) or ALIASES.get(key)
    if not name:
        raise ValueError(f"I don't know the colour {text}; give a hex code like #3fa9ff.")
    return NAMED[name]
