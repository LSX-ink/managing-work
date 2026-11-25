"""'How it works' sections: 3 or 4 simple steps that take the worry out of buying from a business for the first time.

make_steps_section turns 2 to 6 steps ("Book online", "We visit and quote", "Job done, pay after") into a paste-in
HTML block in the brand colour: a heading and short intro, then the steps as an ordered list, each with a numbered
circle, a short title, a sentence or two and an optional "Takes 2 minutes"-style time note. On a laptop the steps sit
side by side joined by a line; on a phone they become a vertical timeline with the line running down the numbers. An
optional reassurance line ("No call-out fee. Cancel any time.") and a button finish the section. The steps are a real
<ol>, so screen readers say "list, 3 items" and the numbers are read once (the circles are decorative). Steps fade in
one after another (not when reduced motion is on), every colour pair passes WCAG AA, and nothing needs JavaScript.
Saves steps.html and steps-preview.html in Kinetic Web Designs/<name>/web.
"""

import html
import re

import memory
from config import Settings
from design_contrast import AA, UI, colour, fix, ratio
from design_extract import FOLDER
from design_palette import on
from design_social import mix

NAMES = {"make_steps_section"}
MIN_STEPS, MAX_STEPS = 2, 6
LINK = re.compile(r"^(https://[^\s\"'<>]+|/[^\s\"'<>]*|#[\w-]*|mailto:[^\s\"'<>]+|tel:[\d+ ()-]+)$")


def step(i: int, s: dict) -> str:
    e = html.escape
    when = f'\n      <p class="st-when">{e(s["time"])}</p>' if s["time"] else ""
    return (f'    <li class="st-step">\n      <span class="st-dot" aria-hidden="true">{i + 1}</span>\n'
            f'      <h3>{e(s["title"])}</h3>\n      <p>{e(s["text"])}</p>{when}\n    </li>')


def block(d: dict) -> str:
    e = html.escape
    brand = d["brand"]
    button = brand if ratio(on(brand), brand) >= AA else fix(brand, on(brand), AA)
    tint = "#%02x%02x%02x" % mix(brand, "#ffffff", 0.85)
    line = brand if ratio(brand, "#ffffff") >= UI else fix(brand, "#ffffff", UI)
    accent = brand if ratio(brand, "#ffffff") >= AA else fix(brand, "#ffffff", AA)
    n = len(d["steps"])
    steps = "\n".join(step(i, s) for i, s in enumerate(d["steps"]))
    intro = f'\n  <p class="st-intro">{e(d["intro"])}</p>' if d["intro"] else ""
    note = f'\n  <p class="st-note">{e(d["note"])}</p>' if d["note"] else ""
    cta = f'\n  <p class="st-cta"><a href="{e(d["link"])}">{e(d["button"])}</a></p>' if d["button"] else ""
    delays = " ".join(f".st-step:nth-child({i + 1}) {{ animation-delay: {i * 0.12:.2f}s; }}" for i in range(1, n))
    return f"""<!-- How it works for {e(d["name"])}: paste this block where the steps should show. -->
<section class="steps" aria-labelledby="st-title"
         style="--st-brand:{button};--st-on:{on(button)};--st-line:{line};--st-tint:{tint};--st-accent:{accent}">
  <style>
    .steps {{ font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; color: #18181b;
             max-width: {min(72, 18 * n + 6)}rem; margin: 0 auto; padding: 0 1rem; }}
    .steps h2 {{ text-align: center; font-size: clamp(1.75rem, 4.5vw, 2.5rem); margin: 0 0 .5rem; text-wrap: balance; }}
    .st-intro {{ text-align: center; color: #52525b; margin: 0 auto 2.5rem; max-width: 40rem; line-height: 1.6; }}
    .st-list {{ list-style: none; margin: 0; padding: 0; display: grid; gap: 1.5rem;
               grid-template-columns: repeat({n}, minmax(0, 1fr)); }}
    .st-step {{ position: relative; text-align: center; padding: 0 .5rem; }}
    .st-step + .st-step::before {{ content: ""; position: absolute; top: 1.5rem; right: calc(50% + 2rem);
                                  width: calc(100% - 4rem + 1.5rem); height: 2px; background: var(--st-line);
                                  opacity: .45; }}
    .st-dot {{ position: relative; z-index: 1; display: inline-grid; place-items: center; width: 3rem; height: 3rem;
              border-radius: 50%; background: var(--st-brand); color: var(--st-on); font-weight: 800;
              font-size: 1.15rem; box-shadow: 0 0 0 6px var(--st-tint); }}
    .st-step h3 {{ margin: 1.1rem 0 .4rem; font-size: 1.15rem; }}
    .st-step p {{ margin: 0; color: #3f3f46; line-height: 1.6; }}
    .st-step .st-when {{ margin-top: .5rem; color: var(--st-accent); font-weight: 700; font-size: .9rem; }}
    .st-note {{ text-align: center; margin: 2.25rem 0 0; color: #3f3f46; font-weight: 600; }}
    .st-cta {{ text-align: center; margin: 1.25rem 0 0; }}
    .st-cta a {{ box-sizing: border-box; display: inline-flex; align-items: center; justify-content: center;
                min-height: 52px; padding: .8rem 1.6rem; border-radius: .9rem; background: var(--st-brand);
                color: var(--st-on); font-weight: 700; text-decoration: none; }}
    .st-cta a:focus-visible {{ outline: 3px solid var(--st-accent); outline-offset: 3px; }}
    @media (max-width: {12 * n + 8}rem) {{
      .st-list {{ grid-template-columns: minmax(0, 1fr); gap: 0; max-width: 34rem; margin: 0 auto; }}
      .st-step {{ text-align: left; display: grid; grid-template-columns: 3rem minmax(0, 1fr); column-gap: 1.1rem;
                 padding: 0 0 1.75rem; }}
      .st-step > :not(.st-dot) {{ grid-column: 2; }}
      .st-dot {{ grid-row: 1 / span 3; }}
      .st-step h3 {{ margin-top: .7rem; }}
      .st-step:not(:last-child)::after {{ content: ""; position: absolute; left: calc(1.5rem - 1px); top: 3rem;
                                         bottom: 0; width: 2px; background: var(--st-line); opacity: .45; }}
      .st-step + .st-step::before {{ display: none; }}
    }}
    @media (prefers-reduced-motion: no-preference) {{
      .st-step {{ animation: st-in .5s cubic-bezier(.2, .7, .2, 1) both; }}
      {delays}
    }}
    @keyframes st-in {{ from {{ opacity: 0; transform: translateY(12px); }} }}
  </style>
  <h2 id="st-title">{e(d["title"])}</h2>{intro}
  <ol class="st-list" role="list">
{steps}
  </ol>{note}{cta}
</section>
"""


def run(settings: Settings, args: dict) -> str:
    clean = lambda v: " ".join(str(v or "").split())  # noqa: E731
    name = clean(args.get("name"))
    if not name:
        raise ValueError("Give the business name for the steps section.")
    brand = colour(args.get("colour") or "")
    raw = args.get("steps") or []
    if not isinstance(raw, list) or not MIN_STEPS <= len(raw) <= MAX_STEPS:
        raise ValueError(f"Give {MIN_STEPS} to {MAX_STEPS} steps; 3 or 4 is easiest to take in.")
    steps = []
    for item in raw:
        if not isinstance(item, dict) or not clean(item.get("title")) or not clean(item.get("text")):
            raise ValueError("Each step needs a short title and a sentence about it, e.g. 'Book online' and "
                             "'Pick a time that suits you; it takes two minutes.'")
        title, text = clean(item["title"]), clean(item["text"])
        if len(title) > 40:
            raise ValueError(f"Keep the step title '{title[:30]}...' under 40 letters; 2 to 4 words reads best.")
        if len(text) > 200:
            raise ValueError(f"Keep the words for '{title}' under 200 letters.")
        steps.append({"title": title, "text": text, "time": clean(item.get("time"))[:40]})
    button = clean(args.get("button"))[:30]
    link = clean(args.get("link")) or "#contact"
    if button and not LINK.match(link):
        raise ValueError(f"The button link '{link[:60]}' isn't one I can use; give https://..., /page, #section, "
                         "mailto: or tel:.")
    d = {"name": name, "brand": brand, "steps": steps, "title": clean(args.get("title")) or "How it works",
         "intro": clean(args.get("intro"))[:240], "note": clean(args.get("note"))[:140], "button": button,
         "link": link if button else ""}
    code = block(d)
    preview = (f"<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n<meta name=\"viewport\" "
               f"content=\"width=device-width, initial-scale=1\">\n<title>{html.escape(name)} | How it works</title>\n"
               "</head>\n<body style=\"margin:0;padding:56px 0;background:#fff\">\n" + code + "</body>\n</html>\n")
    (memory.root(settings) / FOLDER).mkdir(parents=True, exist_ok=True)
    path = memory.folder(settings, f"{FOLDER}/{memory.safe_name(name, 'folder name')}/web", create=True)
    (path / "steps.html").write_text(code, encoding="utf-8")
    (path / "steps-preview.html").write_text(preview, encoding="utf-8")
    where = path.relative_to(memory.root(settings)).as_posix()
    tips = []
    if len(steps) > 4:
        tips.append(f"{len(steps)} steps is a lot to take in; 3 or 4 makes buying feel easy.")
    if not button:
        tips.append("Add a button (e.g. 'Book now') so the first step is one tap away.")
    return (f"Made a 'How it works' section for {name} with {len(steps)} steps in {where}: steps.html to paste into "
            "the page and steps-preview.html to check it. The steps sit side by side on a laptop and become a "
            "timeline on a phone. " + " ".join(tips)).strip()


def tool_definitions() -> list[dict]:
    return [{
        "name": "make_steps_section",
        "description": "Make a paste-in 'How it works' section for a website in the brand colour: heading, intro and "
                       "2-6 numbered steps (title, a sentence, optional time note like 'Takes 2 minutes') joined by "
                       "a line, side by side on laptops and a vertical timeline on phones, plus an optional "
                       "reassurance line and button. AA contrast, no JavaScript. Saves steps.html and a preview in "
                       "Kinetic Web Designs/<name>/web. Answer in plain words.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Business name (the folder)."},
                "colour": {"type": "string", "description": "Brand colour, e.g. '#c2410c'."},
                "title": {"type": "string", "description": "Heading (default 'How it works')."},
                "intro": {"type": "string"},
                "steps": {"type": "array", "description": "2-6 steps in order.", "items": {
                    "type": "object", "properties": {
                        "title": {"type": "string", "description": "2-4 words, e.g. 'Book online'."},
                        "text": {"type": "string"},
                        "time": {"type": "string", "description": "Optional, e.g. 'Takes 2 minutes'."}},
                    "required": ["title", "text"]}},
                "note": {"type": "string", "description": "Reassurance line, e.g. 'No call-out fee.'"},
                "button": {"type": "string", "description": "Optional button, e.g. 'Book now'."},
                "link": {"type": "string", "description": "Button link (default #contact)."},
            },
            "required": ["name", "colour", "steps"],
            "additionalProperties": False,
        },
    }]


async def run_tool(name: str, args: dict, settings: Settings, http=None) -> str:
    try:
        return run(settings, args)
    except (TypeError, ValueError) as e:
        return str(e)
