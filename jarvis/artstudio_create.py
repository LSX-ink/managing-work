"""Making new pictures: a pixel art editor pop-up, collages, wallpapers (gradient or starfield), ASCII art, mood
boards and drawing prompts. Pictures are saved in a memory folder (Ideas by default) and pop up.
"""

import math
import random

from PIL import Image, ImageDraw, ImageOps

import artstudio_colours as colours
import artstudio_common as ac
import media_common as mc
import memory
import screen
from config import Settings

PIXEL_KIND, ASCII_KIND, MOOD_KIND = "art-pixel", "art-ascii", "art-moodboard"
screen.EXTRA_KINDS.update({PIXEL_KIND, ASCII_KIND, MOOD_KIND})

PIXEL_SIZES = (8, 16, 32)
# A bright 16-colour starter palette for pixel art.
PIXEL_PALETTE = ["#000000", "#1d2b53", "#7e2553", "#008751", "#ab5236", "#5f574f", "#c2c3c7", "#fff1e8",
                 "#ff004d", "#ffa300", "#ffec27", "#00e436", "#29adff", "#83769c", "#ff77a8", "#ffccaa"]
COLLAGE_CELL = 600
MAX_COLLAGE, MIN_COLLAGE = 9, 2
MAX_MOOD = 12
MAX_WALLPAPER = (7680, 4320)
ASCII_RAMP = " .:-=+*#%@"
PROMPTS = [
    "A lighthouse keeper's cat on a stormy night", "Your breakfast, drawn as a city skyline",
    "A dragon who is afraid of the dark", "The view from your window, but underwater",
    "A robot learning to garden", "A tiny house inside a teacup", "Your favourite song as a landscape",
    "A fox wearing a winter scarf", "A market stall on the moon", "An old tree with a door in its trunk",
    "A self-portrait as a chess piece", "A bicycle made of flowers", "Rain on a London bus window",
    "A whale swimming through clouds", "A wizard's messy desk", "Your shoes, drawn from three angles",
    "A snail racing a tortoise", "A castle built from books", "A street at night lit by one lamp",
    "A mushroom village", "An astronaut having a picnic", "A pair of hands holding something precious",
    "A jellyfish made of light", "A train crossing a bridge at sunset", "A bee's view of a sunflower",
    "A monster who knits", "A crowded bookshelf", "A hot-air balloon over mountains",
    "An owl reading the newspaper", "A lemon, drawn five ways", "A secret garden behind a wall",
    "A kettle with a personality", "Waves crashing on rocks", "A penguin on holiday",
    "A spaceship made from kitchen things", "Your street in a hundred years", "A sleepy dog by the fire",
    "A treehouse in autumn", "A city built on the back of a turtle", "A coffee cup with steam shapes",
    "A knight with a very small horse", "A night sky full of constellations you invent",
    "A houseplant taking over a room", "A lion in a rainstorm", "A diner at midnight",
    "A pattern made only of circles", "A bridge between two cliffs", "A bird's nest with something odd in it",
    "An umbrella for a very tall giraffe", "A skateboarding frog", "A floating island with a waterfall",
    "A still life of three things on your desk", "A clock melting over a fence", "A deer in a snowy forest",
    "A pirate ship in a bottle", "A cat that is also a cloud", "Your hand, drawn without looking at the paper",
    "A lantern festival", "A cosy reading nook", "A black-and-white starry sky over the sea",
]


def six_folder(settings: Settings, which: str) -> str:
    """One of the six memory folders by name; the pixel art editor saves into it by its position."""
    wanted = (which or "Ideas").strip().lower()
    for name in memory.names(settings):
        if name.lower() == wanted:
            return name
    raise ValueError(f"The pixel art editor saves into one of these: {', '.join(memory.names(settings))}.")


def pixel_art(settings: Settings, args: dict) -> screen.Shown:
    size = int(args.get("size") or 16)
    if size not in PIXEL_SIZES:
        raise ValueError("The grid can be 8, 16 or 32 squares across.")
    palette = [ac.hex_colour(c) for c in (args.get("colours") or [])[:16]] or PIXEL_PALETTE
    data = {"size": size, "palette": palette, "folder": six_folder(settings, args.get("save_to") or "Ideas"),
            "name": ac.file_name(args.get("name") or "", "Pixel art"), "scale": max(8, 512 // size)}
    c = screen.card(PIXEL_KIND, "Pixel art", "art-pixel", data=data)
    return screen.Shown(f"Here's a {size} by {size} pixel art grid. Save puts it in {data['folder']}.", c)


def collage(settings: Settings, args: dict) -> screen.Shown:
    folder = args.get("folder") or ""
    names = [str(n) for n in args.get("filenames") or []]
    if names:
        paths = [ac.picture(settings, folder, n) for n in names]
    else:
        paths = ac.pictures_in(settings, folder, int(args.get("count") or MAX_COLLAGE))
    if not MIN_COLLAGE <= len(paths) <= MAX_COLLAGE:
        raise ValueError(f"A collage takes {MIN_COLLAGE} to {MAX_COLLAGE} pictures.")
    cols = math.ceil(math.sqrt(len(paths)))
    rows = math.ceil(len(paths) / cols)
    gap = min(max(int(args.get("gap") if args.get("gap") is not None else 16), 0), 100)
    background = ac.hex_colour(args.get("colour"), "#ffffff")
    sheet = Image.new("RGB", (cols * COLLAGE_CELL + (cols + 1) * gap, rows * COLLAGE_CELL + (rows + 1) * gap),
                      background)
    for n, path in enumerate(paths):
        cell = ImageOps.fit(ac.rgb(ac.open_image(path)), (COLLAGE_CELL, COLLAGE_CELL), Image.LANCZOS)
        row, col = divmod(n, cols)
        offset = (cols * rows - len(paths)) * (COLLAGE_CELL + gap) // 2 if row == rows - 1 else 0
        sheet.paste(cell, (gap + col * (COLLAGE_CELL + gap) + offset, gap + row * (COLLAGE_CELL + gap)))
    target = ac.save_new(settings, sheet, args.get("save_to") or "", args.get("name") or "Collage", ".jpg")
    return ac.shown(settings, target, f"Made a collage of {len(paths)} pictures, {target.name}.")


def gradient(size: tuple[int, int], start: str, end: str, direction: str) -> Image.Image:
    if direction == "radial":
        mask = Image.radial_gradient("L").resize(size, Image.BICUBIC)
    else:
        mask = Image.linear_gradient("L")
        if direction == "horizontal":
            mask = mask.rotate(90)
        mask = mask.resize(size, Image.BICUBIC)
    return Image.composite(Image.new("RGB", size, end), Image.new("RGB", size, start), mask)


def starfield(size: tuple[int, int], black_and_white: bool, seed=None) -> Image.Image:
    """Black sky, white stars of different sizes and brightness (a few tinted ones unless black_and_white)."""
    rng = random.Random(seed)
    w, h = size
    im = Image.new("RGB", size, "black")
    draw = ImageDraw.Draw(im)
    for _ in range(w * h // 500):
        x, y = rng.randrange(w), rng.randrange(h)
        level = int(40 + 215 * rng.random() ** 1.8)
        tint = (level, level, level)
        if not black_and_white and rng.random() < 0.15:
            tint = rng.choice([(level * 0.7, level * 0.8, level), (level, level * 0.85, level * 0.6)])
        draw.point((x, y), fill=tuple(int(c) for c in tint))
    for _ in range(max(3, w * h // 40000)):
        x, y = rng.randrange(w), rng.randrange(h)
        r = rng.choice((1, 1, 2, 2, 3))
        glow = rng.randint(180, 255)
        draw.ellipse((x - r, y - r, x + r, y + r), fill=(glow, glow, glow))
        if r >= 2:  # a little cross of light on the bigger stars
            draw.line((x - r * 4, y, x + r * 4, y), fill=(glow // 2,) * 3)
            draw.line((x, y - r * 4, x, y + r * 4), fill=(glow // 2,) * 3)
    return im


def wallpaper(settings: Settings, args: dict) -> screen.Shown:
    w, h = int(args.get("width") or 1920), int(args.get("height") or 1080)
    if not (16 <= w <= MAX_WALLPAPER[0] and 16 <= h <= MAX_WALLPAPER[0]) or w * h > MAX_WALLPAPER[0] * MAX_WALLPAPER[1]:
        raise ValueError("Give a screen size up to 7680 by 4320, like 1920 by 1080.")
    style = args.get("style") or "starfield"
    if style == "starfield":
        im = starfield((w, h), args.get("black_and_white", True) is not False)
    elif style == "gradient":
        im = gradient((w, h), ac.hex_colour(args.get("colour"), "#000000"),
                      ac.hex_colour(args.get("colour2"), "#3a3a3a"), args.get("direction") or "vertical")
    else:
        raise ValueError("I can make a starfield or a gradient wallpaper.")
    target = ac.save_new(settings, im, args.get("save_to") or "", args.get("name") or f"Wallpaper {style} {w}x{h}")
    return ac.shown(settings, target, f"Made a {w} by {h} {style} wallpaper, {target.name}.")


def ascii_text(im: Image.Image, width: int, invert: bool) -> str:
    grey = ImageOps.grayscale(ac.rgb(im, "black" if not invert else "white"))
    height = max(1, round(grey.height * width / grey.width * 0.5))
    grey = ImageOps.autocontrast(grey.resize((width, height), Image.LANCZOS))
    ramp = ASCII_RAMP[::-1] if invert else ASCII_RAMP
    pixels = grey.tobytes()
    rows = ("".join(ramp[p * (len(ramp) - 1) // 255] for p in pixels[y * width:(y + 1) * width]).rstrip()
            for y in range(height))
    return "\n".join(rows)


def ascii_art(settings: Settings, args: dict) -> screen.Shown:
    path, im = ac.load(settings, args.get("folder") or "", args.get("filename") or "")
    width = min(max(int(args.get("width") or 80), 20), 160)
    text = ascii_text(im, width, bool(args.get("invert")))
    data = {"text": text, "name": path.stem}
    save = {"label": "Save as note", "say": f"Save the ASCII art of {path.name} as a note in Ideas."}
    c = screen.card(ASCII_KIND, f"ASCII {path.stem}", "art-ascii", data=data, buttons=[save])
    if args.get("save_to"):
        note = memory.save_note(settings, args["save_to"], f"ASCII {ac.file_name(path.stem)}", text)
        return screen.Shown(f"Here's {path.name} in ASCII art, saved as {note.name}.", c)
    return screen.Shown(f"Here's {path.name} in ASCII art.", c)


def moodboard(settings: Settings, args: dict) -> screen.Shown:
    folder = args.get("folder") or ""
    paths = ac.pictures_in(settings, folder, MAX_MOOD)
    thumbs = Image.new("RGB", (100 * len(paths), 100))
    for n, path in enumerate(paths):
        thumbs.paste(ImageOps.fit(ac.rgb(ac.open_image(path)), (100, 100)), (100 * n, 0))
    swatches = [colours.swatch(h, share) for h, share in colours.picture_colours(thumbs)]
    items = [{"src": mc.src(settings, p), "name": p.name, "say": mc.show_line(settings, p)} for p in paths]
    title = args.get("name") or f"{mc.folder(settings, folder).name} mood board"
    c = screen.card(MOOD_KIND, title, f"art-mood-{folder}", data={"items": items, "swatches": swatches},
                    buttons=[{"label": "Make a collage", "say": f"Make a collage from the pictures in {folder}."}])
    return screen.Shown(f"Here's a mood board of {len(paths)} pictures from {folder}.", c)


def drawing_prompt(args: dict) -> screen.Shown:
    count = min(max(int(args.get("count") or 1), 1), 5)
    picks = random.sample(PROMPTS, count)
    c = screen.card("list", "Drawing prompts" if count > 1 else "Drawing prompt", "art-prompt",
                    items=[{"label": p} for p in picks],
                    buttons=[{"label": "Another", "say": "Give me another drawing prompt."},
                             {"label": "Pixel art", "say": "Open the pixel art editor."},
                             {"label": "Sketch pad", "say": "Open the sketch pad."}])
    return screen.Shown(f"Try this: {picks[0]}." if count == 1 else "Here are some ideas: " + "; ".join(picks) + ".", c)


ACTIONS = ("pixel_art", "collage", "wallpaper", "ascii_art", "moodboard", "drawing_prompt")


def tool_definitions() -> list[dict]:
    return [{
        "name": "art_create",
        "description": "Make art on the Alfred screen. action 'pixel_art' opens a pixel art editor (8, 16 or 32 grid, "
                       "palette, fill bucket, eraser) that saves a scaled-up PNG; 'collage' puts 2-9 pictures from a "
                       "folder in a grid (gap, background colour); 'wallpaper' makes a desktop or phone wallpaper "
                       "(width x height, style starfield or gradient); 'ascii_art' turns a picture into text "
                       "characters; 'moodboard' shows a folder's pictures with a colour palette row; "
                       "'drawing_prompt' suggests something to draw. New pictures are saved in Ideas unless save_to.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": list(ACTIONS)},
                "folder": {"type": "string", "description": "Memory folder of the pictures, e.g. Personal/Holiday."},
                "filename": {"type": "string", "description": "ascii_art: the picture's name or part of it."},
                "filenames": {"type": "array", "items": {"type": "string"},
                              "description": "collage: which pictures (default: the first ones in the folder)."},
                "count": {"type": "integer", "description": "collage: how many pictures; drawing_prompt: 1-5."},
                "size": {"type": "integer", "enum": list(PIXEL_SIZES), "description": "pixel_art grid size."},
                "colours": {"type": "array", "items": {"type": "string"},
                            "description": "pixel_art: palette as hex codes or names (default 16 bright colours)."},
                "gap": {"type": "integer", "description": "collage: gap in pixels (default 16)."},
                "colour": {"type": "string", "description": "collage background, or gradient start colour."},
                "colour2": {"type": "string", "description": "gradient end colour."},
                "style": {"type": "string", "enum": ["starfield", "gradient"]},
                "direction": {"type": "string", "enum": ["vertical", "horizontal", "radial"]},
                "black_and_white": {"type": "boolean", "description": "starfield: white stars only (default true)."},
                "width": {"type": "integer", "description": "wallpaper width in pixels; ascii_art characters across."},
                "height": {"type": "integer", "description": "wallpaper height in pixels."},
                "invert": {"type": "boolean", "description": "ascii_art: for dark text on white paper."},
                "name": {"type": "string", "description": "Name for the new picture or mood board."},
                "save_to": {"type": "string", "description": "Memory folder to save into (default Ideas); "
                                                              "ascii_art saves a text note only when given."},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"art_create"}


def run_tool(name: str, args: dict, settings: Settings, http=None) -> screen.Shown:
    action = args.get("action")
    if action == "pixel_art":
        return pixel_art(settings, args)
    if action == "collage":
        return collage(settings, args)
    if action == "wallpaper":
        return wallpaper(settings, args)
    if action == "ascii_art":
        return ascii_art(settings, args)
    if action == "moodboard":
        return moodboard(settings, args)
    if action == "drawing_prompt":
        return drawing_prompt(args)
    raise ValueError(f"Pick one of {', '.join(ACTIONS)}.")
