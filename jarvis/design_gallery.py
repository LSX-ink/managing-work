"""Photo galleries: the "Our work" grid of real photos that sells a cake shop, a barber, a builder or a holiday let.

make_gallery_section turns 2 to 12 photos into a paste-in HTML block: a heading and short intro, then the photos as a
neat grid cropped to one shape (square, 4:3 or 3:4) or as a masonry wall that keeps each photo's own shape, with
optional captions. Tapping a photo opens it large on a dark screen with Previous, Next and Close, built with plain
links and the :target selector so it needs no JavaScript and the browser Back button closes it. Every photo needs
alt text, loads lazily with its width and height set so the page doesn't jump, and gets a gentle zoom on hover (not
when reduced motion is on). Buttons and links pass WCAG AA and are 44px to tap. Use the business's real photos only.
Saves gallery.html and gallery-preview.html in Kinetic Web Designs/<name>/web.
"""

import html
import re

import memory
from config import Settings
from design_contrast import AA, colour, fix, ratio
from design_extract import FOLDER

NAMES = {"make_gallery_section"}
MIN_PHOTOS, MAX_PHOTOS = 2, 12
SHAPES = {"square": "1 / 1", "landscape": "4 / 3", "portrait": "3 / 4"}
SRC = re.compile(r"^(https://[^\s\"'<>]+|/[^\s\"'<>]+)$")


def tile(i: int, p: dict, n: int) -> str:
    e = html.escape
    cap = f"\n      <figcaption>{e(p['caption'])}</figcaption>" if p["caption"] else ""
    return (f'    <li id="gi-{i + 1}"><figure>\n      <a class="g-open" href="#g-{i + 1}">\n        '
            f'<img src="{e(p["src"])}" alt="{e(p["alt"])}" width="{p["w"]}" '
            f'height="{p["h"]}" loading="lazy" decoding="async">\n      </a>{cap}\n    </figure></li>')


def viewer(i: int, p: dict, n: int) -> str:
    e = html.escape
    prev_n = (i - 1) % n + 1
    next_n = (i + 1) % n + 1
    cap = f'<p>{e(p["caption"])}</p>' if p["caption"] else ""
    return (f'  <div class="g-view" id="g-{i + 1}" role="dialog" aria-label="Photo {i + 1} of {n}">\n'
            f'    <img src="{e(p["full"])}" alt="{e(p["alt"])}" loading="lazy" decoding="async">\n'
            f'    <div class="g-bar">{cap}<span class="g-count">{i + 1} / {n}</span>'
            f'<a href="#g-{prev_n}">Previous</a><a href="#g-{next_n}">Next</a>'
            f'<a href="#gi-{i + 1}">Close</a></div>\n  </div>')


def block(d: dict) -> str:
    e = html.escape
    brand = d["brand"]
    accent = brand if ratio(brand, "#ffffff") >= AA else fix(brand, "#ffffff", AA)
    light = brand if ratio(brand, "#0b0b0f") >= AA else fix(brand, "#0b0b0f", AA)
    n = len(d["photos"])
    tiles = "\n".join(tile(i, p, n) for i, p in enumerate(d["photos"]))
    views = "\n".join(viewer(i, p, n) for i, p in enumerate(d["photos"]))
    intro = f'\n  <p class="g-intro">{e(d["intro"])}</p>' if d["intro"] else ""
    new_tab = ' target="_blank" rel="noopener"' if d["more_url"].startswith("https://") else ""
    more = (f'\n  <p class="g-more"><a href="{e(d["more_url"])}"{new_tab}>{e(d["more_text"])}</a></p>'
            if d["more_url"] else "")
    if d["layout"] == "masonry":
        grid = (".g-grid { columns: 3 16rem; column-gap: 1rem; } "
                ".g-grid li { break-inside: avoid; margin-bottom: 1rem; }")
        img = ".g-grid img { width: 100%; height: auto; }"
    else:
        grid = (".g-grid { display: grid; gap: 1rem; "
                "grid-template-columns: repeat(auto-fill, minmax(min(100%, 20rem), 1fr)); }")
        img = f".g-grid img {{ width: 100%; height: auto; aspect-ratio: {SHAPES[d['layout']]}; object-fit: cover; }}"
    return f"""<!-- Gallery for {e(d["name"])}: paste this block where the photos should show. Real photos only. -->
<section class="gallery" aria-labelledby="g-title" style="--g-accent:{accent};--g-light:{light}">
  <style>
    .gallery {{ font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; color: #18181b;
               max-width: 72rem; margin: 0 auto; padding: 0 1rem; }}
    .gallery h2 {{ text-align: center; font-size: clamp(1.75rem, 4.5vw, 2.5rem); margin: 0 0 .5rem; }}
    .g-intro {{ text-align: center; color: #52525b; margin: 0 auto 2rem; max-width: 40rem; line-height: 1.6; }}
    .g-grid {{ list-style: none; margin: 0; padding: 0; }}
    {grid}
    {img}
    .g-grid figure {{ margin: 0; }}
    .g-open {{ display: block; overflow: hidden; border-radius: 1rem; background: #f4f4f5; line-height: 0; }}
    .g-open img {{ display: block; }}
    .g-open:focus-visible {{ outline: 3px solid var(--g-accent); outline-offset: 3px; }}
    .g-grid figcaption {{ margin-top: .5rem; color: #52525b; font-size: .95rem; line-height: 1.45; }}
    .g-more {{ text-align: center; margin: 2rem 0 0; }}
    .g-more a {{ display: inline-flex; align-items: center; min-height: 44px; color: var(--g-accent);
                font-weight: 700; }}
    .g-view {{ display: none; position: fixed; inset: 0; z-index: 1000; background: rgb(9 9 11 / .97);
              padding: 1rem 1rem 0; box-sizing: border-box; flex-direction: column; align-items: center;
              justify-content: center; gap: .75rem; }}
    .g-view:target {{ display: flex; }}
    .g-view img {{ max-width: 100%; max-height: calc(100vh - 7rem); max-height: calc(100dvh - 7rem); width: auto;
                  height: auto; object-fit: contain; border-radius: .5rem; }}
    .g-bar {{ display: flex; flex-wrap: wrap; align-items: center; justify-content: center; gap: .25rem 1rem;
             color: #e4e4e7; padding-bottom: 1rem; max-width: 60rem; }}
    .g-bar p {{ margin: 0; flex-basis: 100%; text-align: center; }}
    .g-count {{ color: #a1a1aa; font-variant-numeric: tabular-nums; }}
    .g-bar a {{ display: inline-flex; align-items: center; min-height: 44px; padding: 0 .5rem; color: var(--g-light);
               font-weight: 700; text-decoration: none; }}
    .g-bar a:focus-visible {{ outline: 3px solid var(--g-light); outline-offset: 2px; border-radius: 4px; }}
    @media (prefers-reduced-motion: no-preference) {{
      .g-open img {{ transition: transform .35s ease; }}
      .g-open:hover img {{ transform: scale(1.04); }}
    }}
  </style>
  <h2 id="g-title">{e(d["title"])}</h2>{intro}
  <ul class="g-grid" role="list">
{tiles}
  </ul>{more}
{views}
</section>
"""


def run(settings: Settings, args: dict) -> str:
    clean = lambda v: " ".join(str(v or "").split())  # noqa: E731
    name = clean(args.get("name"))
    if not name:
        raise ValueError("Give the business name for the gallery.")
    brand = colour(args.get("colour") or "")
    layout = clean(args.get("layout")) or "landscape"
    if layout not in (*SHAPES, "masonry"):
        raise ValueError("Layout can be square, landscape (4:3), portrait (3:4) or masonry (each photo keeps its "
                         "shape).")
    raw = args.get("photos") or []
    if not isinstance(raw, list) or not MIN_PHOTOS <= len(raw) <= MAX_PHOTOS:
        raise ValueError(f"Give {MIN_PHOTOS} to {MAX_PHOTOS} photos; 6 or 9 fill the rows neatly.")
    photos = []
    for i, item in enumerate(raw, 1):
        if not isinstance(item, dict) or not clean(item.get("src")):
            raise ValueError(f"Photo {i} needs its address (src), e.g. /img/cake-1.webp.")
        src = clean(item["src"])
        full = clean(item.get("full")) or src
        for url in (src, full):
            if not SRC.match(url):
                raise ValueError(f"Give photo {i} as a https:// address or a site path like /img/cake.webp.")
        alt = clean(item.get("alt"))
        if not alt:
            raise ValueError(f"Describe photo {i} in a few words for people who can't see it (the 'alt' text), "
                             "e.g. 'Three-tier lemon wedding cake with fresh flowers'.")
        w, h = 1200, 900
        size = clean(item.get("size"))
        if size:
            m = re.fullmatch(r"(\d{2,5})\s*[x×]\s*(\d{2,5})", size)
            if not m:
                raise ValueError(f"Give photo {i}'s size like 1200x900.")
            w, h = int(m.group(1)), int(m.group(2))
        photos.append({"src": src, "full": full, "alt": alt[:150], "caption": clean(item.get("caption"))[:120],
                       "w": w, "h": h})
    more_url = clean(args.get("more_url"))
    if more_url and not re.match(r"^(https://[^\s\"'<>]+|/[^\s\"'<>]*)$", more_url):
        raise ValueError("Give the 'see more' link as a https:// address (e.g. their Instagram) or a page path.")
    d = {"name": name, "brand": brand, "layout": layout, "photos": photos,
         "title": clean(args.get("title")) or "Our work", "intro": clean(args.get("intro"))[:240],
         "more_url": more_url, "more_text": clean(args.get("more_text"))[:40] or "See more of our work"}
    code = block(d)
    preview = (f"<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n<meta name=\"viewport\" "
               f"content=\"width=device-width, initial-scale=1\">\n<title>{html.escape(name)} | Gallery</title>\n"
               "</head>\n<body style=\"margin:0;padding:56px 0;background:#fff\">\n" + code + "</body>\n</html>\n")
    (memory.root(settings) / FOLDER).mkdir(parents=True, exist_ok=True)
    path = memory.folder(settings, f"{FOLDER}/{memory.safe_name(name, 'folder name')}/web", create=True)
    (path / "gallery.html").write_text(code, encoding="utf-8")
    (path / "gallery-preview.html").write_text(preview, encoding="utf-8")
    where = path.relative_to(memory.root(settings)).as_posix()
    tips = []
    if not any(clean(p.get("size")) for p in raw if isinstance(p, dict)):
        tips.append("Give each photo's size (e.g. 1600x1200) so the page doesn't jump while they load.")
    tips.append("Keep each photo under about 200 KB (make_web_images can shrink them).")
    return (f"Made a {layout} gallery for {name} with {len(photos)} photos in {where}: gallery.html to paste into the "
            "page and gallery-preview.html to check it. Tapping a photo opens it large with Previous, Next and "
            "Close. " + " ".join(tips) + " Use the business's own photos only.")


def tool_definitions() -> list[dict]:
    return [{
        "name": "make_gallery_section",
        "description": "Make a paste-in 'Our work' photo gallery for a website: heading, intro and 2-12 real photos "
                       "as a grid cropped to one shape (square, landscape 4:3, portrait 3:4) or a masonry wall, with "
                       "optional captions; tapping a photo opens it large with Previous/Next/Close (no JavaScript). "
                       "Alt text required, lazy loading, optional 'see more' link (e.g. Instagram). Saves "
                       "gallery.html and a preview in Kinetic Web Designs/<name>/web. Answer in plain words.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Business name (the folder)."},
                "colour": {"type": "string", "description": "Brand colour, e.g. '#c2410c'."},
                "title": {"type": "string", "description": "Heading (default 'Our work')."},
                "intro": {"type": "string"},
                "layout": {"type": "string", "enum": [*SHAPES, "masonry"], "description": "Default landscape."},
                "photos": {"type": "array", "description": "2-12 real photos, best first.", "items": {
                    "type": "object", "properties": {
                        "src": {"type": "string", "description": "Photo address (https://... or /img/...)."},
                        "alt": {"type": "string", "description": "What the photo shows."},
                        "caption": {"type": "string"},
                        "full": {"type": "string", "description": "Bigger version for the enlarged view (optional)."},
                        "size": {"type": "string", "description": "Width x height, e.g. 1600x1200."}},
                    "required": ["src", "alt"]}},
                "more_url": {"type": "string", "description": "Optional 'see more' link, e.g. their Instagram."},
                "more_text": {"type": "string", "description": "Link words (default 'See more of our work')."},
            },
            "required": ["name", "colour", "photos"],
            "additionalProperties": False,
        },
    }]


async def run_tool(name: str, args: dict, settings: Settings, http=None) -> str:
    try:
        return run(settings, args)
    except (TypeError, ValueError) as e:
        return str(e)
