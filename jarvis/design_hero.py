"""Hero sections: the first screen of a homepage, where a visitor decides in a few seconds whether to stay.

make_hero_section writes a paste-in HTML block in the brand colour that follows what works on small-business sites:
one clear headline (what you do, for whom), a supporting line, one main button and an optional second one, and an
optional proof line under the buttons ("4.9 on Google from 120 reviews", "Trusted by 300 Birmingham families"). With a
photo it lays out words on the left and the picture on the right (stacked on phones, picture second so the headline
is seen first); without one it centres the words on a soft brand-tinted background with a gentle glow. The photo
needs alt text, loads first (fetchpriority high) with its width and height set so nothing jumps while it loads.
The headline shrinks smoothly from laptop to phone, the entrance fade respects reduced motion, every colour pair
passes WCAG AA and nothing needs JavaScript. Saves hero.html and hero-preview.html in Kinetic Web Designs/<name>/web.
"""

import html
import re

import memory
from config import Settings
from design_contrast import AA, colour, fix, ratio
from design_extract import FOLDER
from design_palette import on
from design_social import mix

NAMES = {"make_hero_section"}


def safe_link(url: str, what: str) -> str:
    url = url.strip()
    if re.match(r"^(https://[^\s\"'<>]+|/[^\s\"'<>]*|#[\w-]*|mailto:[^\s\"'<>]+|tel:[\d+ ()-]+)$", url):
        return url
    raise ValueError(f"The {what} link '{url[:60]}' isn't one I can use; give https://..., /page, #section, "
                     "mailto: or tel:.")


def block(d: dict) -> str:
    e = html.escape
    brand = d["brand"]
    button = brand if ratio(on(brand), brand) >= AA else fix(brand, on(brand), AA)
    tint = "#%02x%02x%02x" % mix(brand, "#ffffff", 0.92)
    accent = brand if ratio(brand, tint) >= AA else fix(brand, tint, AA)
    second = (f'\n      <a class="h-btn ghost" href="{e(d["link2"])}">{e(d["button2"])}</a>' if d["button2"] else "")
    proof = f'\n    <p class="h-proof">{e(d["proof"])}</p>' if d["proof"] else ""
    kicker = f'<p class="h-kicker">{e(d["kicker"])}</p>\n    ' if d["kicker"] else ""
    photo = ""
    if d["image"]:
        photo = (f'\n  <img class="h-img" src="{e(d["image"])}" alt="{e(d["alt"])}" width="{d["w"]}" '
                 f'height="{d["h"]}" fetchpriority="high" decoding="async">')
    layout = "split" if d["image"] else "centre"
    return f"""<!-- Hero for {e(d["name"])}: paste this block at the very top of the home page, under the menu. -->
<section class="hero {layout}" aria-labelledby="h-title"
         style="--h-brand:{button};--h-on:{on(button)};--h-accent:{accent};--h-tint:{tint};--h-glow:{brand}33">
  <style>
    .hero {{ font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; color: #18181b;
            background: var(--h-tint); position: relative; overflow: hidden; display: grid; gap: 2.5rem;
            align-items: center; padding: clamp(3rem, 9vw, 7rem) clamp(1rem, 5vw, 4rem); }}
    .hero.centre {{ text-align: center; justify-items: center; }}
    .hero.centre::before {{ content: ""; position: absolute; inset: -40% -20% auto; height: 120%;
                           background: radial-gradient(closest-side, var(--h-glow), transparent); z-index: 0; }}
    .hero.split {{ grid-template-columns: minmax(0, 1.1fr) minmax(0, 1fr); max-width: 76rem; margin: 0 auto; }}
    .h-words {{ position: relative; z-index: 1; max-width: 42rem; }}
    .h-kicker {{ margin: 0 0 .75rem; font-weight: 700; color: var(--h-accent); letter-spacing: .06em;
                text-transform: uppercase; font-size: .85rem; }}
    .hero h1 {{ font-size: clamp(2.1rem, 5.5vw, 4rem); line-height: 1.07; letter-spacing: -.025em; margin: 0;
               text-wrap: balance; }}
    .h-line {{ font-size: clamp(1.05rem, 2.2vw, 1.3rem); line-height: 1.55; color: #3f3f46; margin: 1.1rem 0 0;
              text-wrap: pretty; }}
    .h-btns {{ display: flex; flex-wrap: wrap; gap: .75rem; margin-top: 2rem; }}
    .hero.centre .h-btns {{ justify-content: center; }}
    .h-btn {{ box-sizing: border-box; display: inline-flex; align-items: center; justify-content: center;
             min-height: 52px;
             padding: .8rem 1.6rem; border-radius: .9rem; font-weight: 700; text-decoration: none;
             background: var(--h-brand); color: var(--h-on); border: 2px solid var(--h-brand); }}
    .h-btn.ghost {{ background: transparent; color: var(--h-accent); border-color: var(--h-accent); }}
    .h-btn:focus-visible {{ outline: 3px solid var(--h-accent); outline-offset: 3px; }}
    .h-proof {{ margin: 1.25rem 0 0; color: #3f3f46; font-weight: 600; font-size: .95rem; }}
    .h-img {{ position: relative; z-index: 1; width: 100%; height: auto; aspect-ratio: {d["w"]} / {d["h"]};
             object-fit: cover; border-radius: 1.5rem; box-shadow: 0 24px 60px rgb(0 0 0 / .18); }}
    @media (max-width: 52rem) {{ .hero.split {{ grid-template-columns: 1fr; }} }}
    @media (prefers-reduced-motion: no-preference) {{
      .h-words > * {{ animation: h-up .6s cubic-bezier(.2, .7, .2, 1) both; }}
      .h-words > :nth-child(2) {{ animation-delay: .06s; }} .h-words > :nth-child(3) {{ animation-delay: .12s; }}
      .h-words > :nth-child(4) {{ animation-delay: .18s; }} .h-words > :nth-child(5) {{ animation-delay: .24s; }}
    }}
    @keyframes h-up {{ from {{ opacity: 0; transform: translateY(14px); }} }}
  </style>
  <div class="h-words">
    {kicker}<h1 id="h-title">{e(d["headline"])}</h1>
    {f'<p class="h-line">{e(d["line"])}</p>' if d["line"] else ''}
    <p class="h-btns">
      <a class="h-btn" href="{e(d["link"])}">{e(d["button"])}</a>{second}
    </p>{proof}
  </div>{photo}
</section>
"""


def run(settings: Settings, args: dict) -> str:
    clean = lambda v: " ".join(str(v or "").split())  # noqa: E731
    name = clean(args.get("name"))
    if not name:
        raise ValueError("Give the business name for the hero.")
    brand = colour(args.get("colour") or "")
    headline = clean(args.get("headline"))
    if not headline:
        raise ValueError("Give a headline that says what you do and for whom, e.g. 'Fresh sourdough, baked in "
                         "Hockley every morning'.")
    if len(headline) > 90:
        raise ValueError("Keep the headline under 90 letters; the best ones are 4 to 10 words.")
    line = clean(args.get("line"))
    if len(line) > 220:
        raise ValueError("Keep the supporting line under 220 letters.")
    button = clean(args.get("button")) or "Get in touch"
    link = safe_link(clean(args.get("link")) or "#contact", "main button")
    button2 = clean(args.get("button2"))
    link2 = safe_link(clean(args.get("link2")) or "#more", "second button") if button2 else ""
    image = clean(args.get("image"))
    alt = clean(args.get("alt"))
    w, h = 1200, 900
    if image:
        if not re.match(r"^(https://[^\s\"'<>]+|/[^\s\"'<>]+)$", image):
            raise ValueError("Give the photo as a https:// address or a site path like /img/shop.webp.")
        if not alt:
            raise ValueError("Describe the photo in a few words for people who can't see it (the 'alt' text).")
        size = clean(args.get("image_size"))
        if size:
            m = re.fullmatch(r"(\d{2,5})\s*[x×]\s*(\d{2,5})", size)
            if not m:
                raise ValueError("Give the photo size like 1200x900.")
            w, h = int(m.group(1)), int(m.group(2))
    d = {"name": name, "brand": brand, "headline": headline, "line": line, "button": button[:30], "link": link,
         "button2": button2[:30], "link2": link2, "proof": clean(args.get("proof"))[:100],
         "kicker": clean(args.get("kicker"))[:40], "image": image, "alt": alt[:150], "w": w, "h": h}
    code = block(d)
    preview = (f"<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n<meta name=\"viewport\" "
               f"content=\"width=device-width, initial-scale=1\">\n<title>{html.escape(name)} | Hero</title>\n"
               "</head>\n<body style=\"margin:0\">\n" + code + "</body>\n</html>\n")
    (memory.root(settings) / FOLDER).mkdir(parents=True, exist_ok=True)
    path = memory.folder(settings, f"{FOLDER}/{memory.safe_name(name, 'folder name')}/web", create=True)
    (path / "hero.html").write_text(code, encoding="utf-8")
    (path / "hero-preview.html").write_text(preview, encoding="utf-8")
    where = path.relative_to(memory.root(settings)).as_posix()
    words = len(headline.split())
    tip = (" Tip: the headline is long; 4 to 10 words reads fastest." if words > 12 else "")
    return (f"Made a {'photo' if image else 'centred'} hero section for {name} in {where}: hero.html to paste at "
            f"the top of the home page and hero-preview.html to check it." + tip
            + (" Use a real photo of the business, not stock, and keep it under about 200 KB (make_web_images "
               "can shrink it)." if image else ""))


def tool_definitions() -> list[dict]:
    return [{
        "name": "make_hero_section",
        "description": "Make the hero (first screen) of a homepage as a paste-in HTML block in the brand colour: "
                       "small kicker, big headline, supporting line, main and optional second button, optional "
                       "proof line (e.g. '4.9 on Google'), and an optional photo on the right (stacks on phones; "
                       "needs alt text) or a centred tinted layout. Fluid type, gentle entrance, AA contrast, no "
                       "JavaScript. Saves hero.html and a preview in Kinetic Web Designs/<name>/web. Answer in plain "
                       "words.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Business name (the folder)."},
                "colour": {"type": "string", "description": "Brand colour, e.g. '#c2410c'."},
                "kicker": {"type": "string", "description": "Tiny line above the headline, e.g. 'Birmingham bakery'."},
                "headline": {"type": "string", "description": "What you do and for whom, 4-10 words."},
                "line": {"type": "string", "description": "One or two sentences under the headline."},
                "button": {"type": "string", "description": "Main button (default 'Get in touch')."},
                "link": {"type": "string", "description": "Main button link (default #contact)."},
                "button2": {"type": "string", "description": "Optional second button, e.g. 'See our work'."},
                "link2": {"type": "string"},
                "proof": {"type": "string", "description": "e.g. '★ 4.9 on Google from 120 reviews'."},
                "image": {"type": "string", "description": "Photo address (https://... or /img/...)."},
                "alt": {"type": "string", "description": "What the photo shows, for screen readers."},
                "image_size": {"type": "string", "description": "Photo width x height, e.g. 1200x900."},
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
