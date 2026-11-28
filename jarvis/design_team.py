"""Team sections: "Meet the team", the faces behind a small business that turn a website into people you'd trust.

make_team_section turns 1 to 8 people into a paste-in HTML block in the brand colour: a heading and short intro, then a
card per person with their photo (a real photo with alt text, cropped to a soft rounded portrait) or, when there is
no photo yet, a tidy initials circle in a brand tint, then their name, their role ("Head baker", "Senior stylist"), an
optional line or two about them and an optional link (their Instagram or booking page). Cards sit up to four across on
a laptop and two or one across on a phone, photos lazy-load with their size set, and every colour pair passes WCAG AA.
Only use photos and names the people have agreed to show. No JavaScript. Saves team.html and team-preview.html in
Kinetic Web Designs/<name>/web.
"""

import html
import re

import memory
from config import Settings
from design_contrast import AA, colour, fix, ratio
from design_extract import FOLDER
from design_logo import initials
from design_social import mix

NAMES = {"make_team_section"}
MIN_PEOPLE, MAX_PEOPLE = 1, 8
SRC = re.compile(r"^(https://[^\s\"'<>]+|/[^\s\"'<>]+)$")
LINK = re.compile(r"^(https://[^\s\"'<>]+|/[^\s\"'<>]*|mailto:[^\s\"'<>]+|tel:[\d+ ()-]+)$")


def card(p: dict) -> str:
    e = html.escape
    if p["photo"]:
        face = (f'<img class="tm-photo" src="{e(p["photo"])}" alt="{e(p["alt"])}" width="600" height="750" '
                f'loading="lazy" decoding="async">')
    else:
        face = f'<span class="tm-photo tm-initials" aria-hidden="true">{e(p["initials"])}</span>'
    bio = f'\n    <p class="tm-bio">{e(p["bio"])}</p>' if p["bio"] else ""
    new_tab = ' target="_blank" rel="noopener"' if p["url"].startswith("https://") else ""
    link = (f'\n    <a class="tm-link" href="{e(p["url"])}"{new_tab}>{e(p["link_text"])}'
            f'<span class="tm-sr"> ({e(p["name"])})</span></a>' if p["url"] else "")
    return (f'  <li class="tm-card">\n    {face}\n    <h3>{e(p["name"])}</h3>\n'
            f'    <p class="tm-role">{e(p["role"])}</p>{bio}{link}\n  </li>')


def block(d: dict) -> str:
    e = html.escape
    brand = d["brand"]
    tint = "#%02x%02x%02x" % mix(brand, "#ffffff", 0.82)
    accent = brand if ratio(brand, "#ffffff") >= AA else fix(brand, "#ffffff", AA)
    letters = brand if ratio(brand, tint) >= AA else fix(brand, tint, AA)
    n = len(d["people"])
    cols = min(n, 4) if n != 5 else 3
    cards = "\n".join(card(p) for p in d["people"])
    intro = f'\n  <p class="tm-intro">{e(d["intro"])}</p>' if d["intro"] else ""
    return f"""<!-- Team for {e(d["name"])}: paste this block on the About page or the home page. -->
<section class="team" aria-labelledby="tm-title"
         style="--tm-accent:{accent};--tm-tint:{tint};--tm-letters:{letters}">
  <style>
    .team {{ font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; color: #18181b;
            max-width: {cols * 16 + 4}rem; margin: 0 auto; padding: 0 1rem; }}
    .team h2 {{ text-align: center; font-size: clamp(1.75rem, 4.5vw, 2.5rem); margin: 0 0 .5rem; text-wrap: balance; }}
    .tm-intro {{ text-align: center; color: #52525b; margin: 0 auto 2.25rem; max-width: 40rem; line-height: 1.6; }}
    .tm-grid {{ list-style: none; margin: 0; padding: 0; display: grid; gap: 2rem 1.5rem;
               grid-template-columns: repeat({cols}, minmax(0, 1fr)); }}
    .tm-card {{ text-align: center; }}
    .tm-photo {{ display: block; width: 100%; height: auto; aspect-ratio: 4 / 5; object-fit: cover;
                border-radius: 1.25rem; background: var(--tm-tint); }}
    .tm-initials {{ display: grid; place-items: center; font-size: clamp(2.5rem, 7vw, 3.5rem); font-weight: 800;
                   letter-spacing: .02em; color: var(--tm-letters); }}
    .tm-card h3 {{ margin: 1rem 0 .15rem; font-size: 1.15rem; }}
    .tm-role {{ margin: 0; color: var(--tm-accent); font-weight: 600; }}
    .tm-bio {{ margin: .6rem 0 0; color: #3f3f46; line-height: 1.55; font-size: .95rem; }}
    .tm-link {{ display: inline-flex; align-items: center; min-height: 44px; color: var(--tm-accent);
               font-weight: 700; }}
    .tm-link:focus-visible {{ outline: 3px solid var(--tm-accent); outline-offset: 2px; border-radius: 4px; }}
    .tm-sr {{ position: absolute; width: 1px; height: 1px; overflow: hidden; clip-path: inset(50%);
             white-space: nowrap; }}
    @media (max-width: 52rem) {{ .tm-grid {{ grid-template-columns: repeat({min(cols, 2)}, minmax(0, 1fr)); }} }}
    @media (max-width: 26rem) {{ .tm-grid {{ grid-template-columns: repeat({1 if n < 3 else 2}, minmax(0, 1fr));
                                           gap: 1.5rem 1rem; }} .tm-bio {{ font-size: .9rem; }} }}
  </style>
  <h2 id="tm-title">{e(d["title"])}</h2>{intro}
  <ul class="tm-grid" role="list">
{cards}
  </ul>
</section>
"""


def run(settings: Settings, args: dict) -> str:
    clean = lambda v: " ".join(str(v or "").split())  # noqa: E731
    name = clean(args.get("name"))
    if not name:
        raise ValueError("Give the business name for the team section.")
    brand = colour(args.get("colour") or "")
    raw = args.get("people") or []
    if not isinstance(raw, list) or not MIN_PEOPLE <= len(raw) <= MAX_PEOPLE:
        raise ValueError(f"Give {MIN_PEOPLE} to {MAX_PEOPLE} people.")
    people = []
    for i, item in enumerate(raw, 1):
        if not isinstance(item, dict) or not clean(item.get("name")) or not clean(item.get("role")):
            raise ValueError(f"Person {i} needs a name and a role, e.g. 'Lebo' and 'Head baker'.")
        who, role = clean(item["name"])[:50], clean(item["role"])[:50]
        photo = clean(item.get("photo"))
        if photo and not SRC.match(photo):
            raise ValueError(f"Give {who}'s photo as a https:// address or a site path like /img/lebo.webp.")
        bio = clean(item.get("bio"))
        if len(bio) > 220:
            raise ValueError(f"Keep {who}'s line under 220 letters; one or two sentences reads best.")
        url = clean(item.get("url"))
        if url and not LINK.match(url):
            raise ValueError(f"{who}'s link '{url[:60]}' isn't one I can use; give https://..., /page, mailto: "
                             "or tel:.")
        people.append({"name": who, "role": role, "photo": photo,
                       "alt": clean(item.get("alt"))[:150] or f"{who}, {role}", "initials": initials(who),
                       "bio": bio, "url": url, "link_text": clean(item.get("link_text"))[:30] or "Say hello"})
    if len({p["name"].lower() for p in people}) != len(people):
        raise ValueError("Two people have the same name; add a surname initial to tell them apart.")
    d = {"name": name, "brand": brand, "people": people, "title": clean(args.get("title")) or "Meet the team",
         "intro": clean(args.get("intro"))[:240]}
    code = block(d)
    preview = (f"<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n<meta name=\"viewport\" "
               f"content=\"width=device-width, initial-scale=1\">\n<title>{html.escape(name)} | Team</title>\n"
               "</head>\n<body style=\"margin:0;padding:56px 0;background:#fff\">\n" + code + "</body>\n</html>\n")
    (memory.root(settings) / FOLDER).mkdir(parents=True, exist_ok=True)
    path = memory.folder(settings, f"{FOLDER}/{memory.safe_name(name, 'folder name')}/web", create=True)
    (path / "team.html").write_text(code, encoding="utf-8")
    (path / "team-preview.html").write_text(preview, encoding="utf-8")
    where = path.relative_to(memory.root(settings)).as_posix()
    missing = [p["name"] for p in people if not p["photo"]]
    tip = (f" {', '.join(missing)} {'has' if len(missing) == 1 else 'have'} initials for now; a friendly real photo "
           "(portrait, about 600x750) works best." if missing else "")
    return (f"Made a team section for {name} with {len(people)} {'person' if len(people) == 1 else 'people'} in "
            f"{where}: team.html to paste on the About or home page and team-preview.html to check it.{tip} Only use "
            "names and photos each person has agreed to show.")


def tool_definitions() -> list[dict]:
    return [{
        "name": "make_team_section",
        "description": "Make a paste-in 'Meet the team' section for a website in the brand colour: heading, intro "
                       "and 1-8 people, each with a photo (or an initials circle if none yet), name, role, optional "
                       "short line about them and optional link (e.g. their Instagram or booking page). Up to 4 "
                       "across on laptops, 2 or 1 on phones, AA contrast, no JavaScript. Saves team.html and a "
                       "preview in Kinetic Web Designs/<name>/web. Answer in plain words.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Business name (the folder)."},
                "colour": {"type": "string", "description": "Brand colour, e.g. '#c2410c'."},
                "title": {"type": "string", "description": "Heading (default 'Meet the team')."},
                "intro": {"type": "string"},
                "people": {"type": "array", "description": "1-8 people, owner first.", "items": {
                    "type": "object", "properties": {
                        "name": {"type": "string"}, "role": {"type": "string", "description": "e.g. 'Head baker'."},
                        "photo": {"type": "string", "description": "Portrait photo address (https or /img/...)."},
                        "alt": {"type": "string", "description": "What the photo shows (default 'Name, role')."},
                        "bio": {"type": "string", "description": "One or two sentences."},
                        "url": {"type": "string", "description": "Optional link, e.g. their Instagram."},
                        "link_text": {"type": "string", "description": "Link words (default 'Say hello')."}},
                    "required": ["name", "role"]}},
            },
            "required": ["name", "colour", "people"],
            "additionalProperties": False,
        },
    }]


async def run_tool(name: str, args: dict, settings: Settings, http=None) -> str:
    try:
        return run(settings, args)
    except (TypeError, ValueError) as e:
        return str(e)
