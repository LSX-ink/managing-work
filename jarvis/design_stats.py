"""Stats bands: the strip of 2 to 4 big numbers that proves a business is real ("15 years", "2,000+ jobs", "4.9★").

make_stats_band turns 2 to 4 numbers with short labels into a paste-in HTML block in the brand colour: either a solid
brand-colour band with light text (style "band") or a light band with the numbers in the brand colour (style
"light"). Each number is big and bold with its label under it, an optional small source line sits underneath
("Google rating, May 2026") so the claim can be checked, and the numbers sit in one row on a laptop and two by two on
a phone. It is a real list with each number and label read together ("2,000+ jobs done"), numbers use tabular figures
so they line up, the fade-in respects reduced motion, every colour pair passes WCAG AA, and nothing needs JavaScript.
Saves stats.html and stats-preview.html in Kinetic Web Designs/<name>/web.
"""

import html
import re

import memory
from config import Settings
from design_contrast import AA, colour, fix, ratio
from design_extract import FOLDER
from design_palette import on
from design_social import mix

NAMES = {"make_stats_band"}
MIN_STATS, MAX_STATS = 2, 4
DIGIT = re.compile(r"\d")


def colours(brand: str, style: str) -> dict:
    if style == "band":
        bg = brand if ratio(on(brand), brand) >= AA else fix(brand, on(brand), AA)
        text = on(bg)
        return {"bg": bg, "num": text, "label": text, "soft": text}
    bg = "#%02x%02x%02x" % mix(brand, "#ffffff", 0.93)
    num = brand if ratio(brand, bg) >= AA else fix(brand, bg, AA)
    return {"bg": bg, "num": num, "label": "#27272a", "soft": "#52525b"}


def block(d: dict) -> str:
    e = html.escape
    c = colours(d["brand"], d["style"])
    n = len(d["stats"])
    items = "\n".join(f'    <li class="sb-item"><strong>{e(s["value"])}</strong> <span>{e(s["label"])}</span></li>'
                      for s in d["stats"])
    title = f'\n  <h2 class="sb-title">{e(d["title"])}</h2>' if d["title"] else ""
    source = f'\n  <p class="sb-source">{e(d["source"])}</p>' if d["source"] else ""
    label = 'aria-labelledby="sb-title"' if d["title"] else f'aria-label="{e(d["name"])} in numbers"'
    title = title.replace('class="sb-title"', 'class="sb-title" id="sb-title"')
    return f"""<!-- Numbers for {e(d["name"])}: paste this block under the hero. Keep every number true. -->
<section class="stats-band" {label}
         style="--sb-bg:{c["bg"]};--sb-num:{c["num"]};--sb-label:{c["label"]};--sb-soft:{c["soft"]}">
  <style>
    .stats-band {{ font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; background: var(--sb-bg);
                  color: var(--sb-label); padding: clamp(2.25rem, 6vw, 3.5rem) 1rem; text-align: center; }}
    .sb-title {{ margin: 0 auto 2.25rem; font-size: clamp(1.35rem, 3.5vw, 1.9rem); max-width: 40rem;
                text-wrap: balance; color: var(--sb-label); }}
    .sb-list {{ list-style: none; margin: 0 auto; padding: 0; max-width: {16 * n + 4}rem; display: grid;
               gap: 2rem 1.5rem;
               grid-template-columns: repeat({n}, minmax(0, 1fr)); }}
    .sb-item {{ display: flex; flex-direction: column; gap: .35rem; align-items: center; }}
    .sb-item strong {{ color: var(--sb-num); font-size: clamp(2.2rem, 6vw, 3.4rem); line-height: 1; font-weight: 800;
                      letter-spacing: -.03em; font-variant-numeric: tabular-nums; }}
    .sb-item span {{ font-size: 1rem; font-weight: 600; line-height: 1.35; max-width: 14rem; }}
    .sb-source {{ margin: 1.75rem 0 0; font-size: .85rem; color: var(--sb-soft); }}
    @media (max-width: 40rem) {{ .sb-list {{ grid-template-columns: repeat({2 if n != 3 else 1}, minmax(0, 1fr)); }} }}
    @media (prefers-reduced-motion: no-preference) {{
      .sb-item {{ animation: sb-in .6s cubic-bezier(.2, .7, .2, 1) both; }}
      .sb-item:nth-child(2) {{ animation-delay: .08s; }} .sb-item:nth-child(3) {{ animation-delay: .16s; }}
      .sb-item:nth-child(4) {{ animation-delay: .24s; }}
    }}
    @keyframes sb-in {{ from {{ opacity: 0; transform: translateY(10px); }} }}
  </style>{title}
  <ul class="sb-list" role="list">
{items}
  </ul>{source}
</section>
"""


def run(settings: Settings, args: dict) -> str:
    clean = lambda v: " ".join(str(v or "").split())  # noqa: E731
    name = clean(args.get("name"))
    if not name:
        raise ValueError("Give the business name for the numbers band.")
    brand = colour(args.get("colour") or "")
    style = clean(args.get("style")) or "band"
    if style not in ("band", "light"):
        raise ValueError("Style can be band (brand-colour strip) or light (pale strip, brand-colour numbers).")
    raw = args.get("stats") or []
    if not isinstance(raw, list) or not MIN_STATS <= len(raw) <= MAX_STATS:
        raise ValueError(f"Give {MIN_STATS} to {MAX_STATS} numbers; 3 or 4 fills the row best.")
    stats = []
    for item in raw:
        if not isinstance(item, dict) or not clean(item.get("value")) or not clean(item.get("label")):
            raise ValueError("Each number needs the number and a few words, e.g. {value: '2,000+', "
                             "label: 'jobs done'}.")
        value, label = clean(item["value"]), clean(item["label"])
        if len(value) > 10:
            raise ValueError(f"Keep '{value[:20]}' short (under 10 characters), e.g. '15 yrs' or '2,000+'.")
        if not DIGIT.search(value):
            raise ValueError(f"'{value}' has no number in it; this band is for numbers like '15' or '4.9★'.")
        if len(label) > 40:
            raise ValueError(f"Keep the label '{label[:30]}...' under 40 letters.")
        stats.append({"value": value, "label": label})
    d = {"name": name, "brand": brand, "style": style, "stats": stats, "title": clean(args.get("title"))[:80],
         "source": clean(args.get("source"))[:120]}
    code = block(d)
    preview = (f"<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n<meta name=\"viewport\" "
               f"content=\"width=device-width, initial-scale=1\">\n<title>{html.escape(name)} | Numbers</title>\n"
               "</head>\n<body style=\"margin:0;padding:48px 0;background:#fff\">\n" + code + "</body>\n</html>\n")
    (memory.root(settings) / FOLDER).mkdir(parents=True, exist_ok=True)
    path = memory.folder(settings, f"{FOLDER}/{memory.safe_name(name, 'folder name')}/web", create=True)
    (path / "stats.html").write_text(code, encoding="utf-8")
    (path / "stats-preview.html").write_text(preview, encoding="utf-8")
    where = path.relative_to(memory.root(settings)).as_posix()
    tip = ("" if d["source"] else " Add a source line (e.g. 'Google rating, May 2026') so people can check the "
           "numbers.")
    return (f"Made a numbers band for {name} with {len(stats)} numbers in {where}: stats.html to paste under the hero "
            f"or above the reviews, and stats-preview.html to check it.{tip} Only use numbers that are true and that "
            "the business can back up; UK advertising rules (CAP code) apply to claims on websites.")


def tool_definitions() -> list[dict]:
    return [{
        "name": "make_stats_band",
        "description": "Make a paste-in 'numbers that prove it' band for a website in the brand colour: 2-4 big "
                       "numbers with short labels (e.g. '15 years in business', '2,000+ jobs done', '4.9★ on "
                       "Google'), optional heading and source line, as a solid brand strip or a light strip. One row "
                       "on laptops, two by two on phones, AA contrast, no JavaScript. Saves stats.html and a preview "
                       "in Kinetic Web Designs/<name>/web. Answer in plain words.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Business name (the folder)."},
                "colour": {"type": "string", "description": "Brand colour, e.g. '#c2410c'."},
                "stats": {"type": "array", "description": "2-4 true numbers.", "items": {
                    "type": "object", "properties": {
                        "value": {"type": "string", "description": "e.g. '2,000+', '15', '4.9★'."},
                        "label": {"type": "string", "description": "e.g. 'jobs done'."}},
                    "required": ["value", "label"]}},
                "style": {"type": "string", "enum": ["band", "light"], "description": "Default band."},
                "title": {"type": "string", "description": "Optional heading above the numbers."},
                "source": {"type": "string", "description": "Where the numbers come from, e.g. 'Google, May 2026'."},
            },
            "required": ["name", "colour", "stats"],
            "additionalProperties": False,
        },
    }]


async def run_tool(name: str, args: dict, settings: Settings, http=None) -> str:
    try:
        return run(settings, args)
    except (TypeError, ValueError) as e:
        return str(e)
