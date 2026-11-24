"""Link-in-bio page: one small web page with all of a business's links, for the single link Instagram and TikTok allow.

make_link_page builds a self-contained links.html in the brand colour: a round badge with the business initials (or
the logo, if given as a web address), the name, a short line, up to 8 big tap-friendly buttons (book, shop, menu,
WhatsApp, reviews...), and small social links underneath. It is phone-first (buttons at least 52px tall, one column,
max 480px wide), works with no internet libraries, honours dark mode and reduced motion, and passes WCAG AA contrast:
the button colour is darkened or lightened until its words read clearly. Only https, mailto, tel and WhatsApp links are
kept, so nothing odd can be slipped in. Upload it anywhere (Cloudflare Pages, Netlify, the client's own site at /links)
and put that address in the bio. Saved in Kinetic Web Designs/<name>/web.
"""

import html
import re

import memory
from config import Settings
from design_contrast import AA, colour, fix, ratio
from design_extract import FOLDER
from design_logo import initials
from design_palette import on

NAMES = {"make_link_page"}
MAX_LINKS = 8
SOCIALS = {  # name: (label, address pattern for a bare handle)
    "instagram": ("Instagram", "https://instagram.com/{}"),
    "tiktok": ("TikTok", "https://www.tiktok.com/@{}"),
    "facebook": ("Facebook", "https://facebook.com/{}"),
    "x": ("X", "https://x.com/{}"),
    "linkedin": ("LinkedIn", "https://www.linkedin.com/company/{}"),
    "youtube": ("YouTube", "https://www.youtube.com/@{}"),
}


def safe_url(url: str) -> str:
    """Return the link if it is a kind a visitor can safely tap, else raise."""
    url = url.strip()
    if re.match(r"^(www\.)?[\w-]+(\.[\w-]+)+(/\S*)?$", url):
        url = "https://" + url
    if re.match(r"^https://[^\s\"'<>]+$", url) or re.match(r"^mailto:[^\s\"'<>@]+@[^\s\"'<>]+$", url) \
            or re.match(r"^tel:\+?[\d\s()-]{5,}$", url):
        return url
    raise ValueError(f"'{url[:60]}' isn't a link I can use; give a https:// address, mailto: or tel:.")


def social_url(site: str, value: str) -> str:
    value = value.strip()
    if value.startswith(("http://", "https://", "www.")):
        return safe_url(value.replace("http://", "https://", 1))
    handle = value.lstrip("@")
    if not re.fullmatch(r"[\w.-]{1,60}", handle):
        raise ValueError(f"'{value[:60]}' doesn't look like a {SOCIALS[site][0]} handle.")
    return SOCIALS[site][1].format(handle)


def page(name: str, brand: str, tagline: str, links: list[tuple[str, str]], socials: list[tuple[str, str]],
         logo: str) -> str:
    e = html.escape
    paper, paper_dark = "#ffffff", "#111114"
    button = brand if ratio(on(brand), brand) >= AA else fix(brand, on(brand), AA)
    button_text = on(button)
    accent = brand if ratio(brand, paper) >= AA else fix(brand, paper, AA)
    accent_dark = brand if ratio(brand, paper_dark) >= AA else fix(brand, paper_dark, AA)
    badge = (f'<img class="badge" src="{e(logo)}" alt="{e(name)} logo" width="96" height="96">' if logo
             else f'<div class="badge" aria-hidden="true">{e(initials(name))}</div>')
    items = "\n".join(f'      <li><a class="btn" href="{e(url)}"{rel(url)}>{e(label)}</a></li>' for label, url in links)
    small = " ".join(f'<a href="{e(url)}"{rel(url)}>{e(label)}</a>' for label, url in socials)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(name)} | Links</title>
<meta name="description" content="{e(tagline or name)}">
<meta property="og:title" content="{e(name)}">
<meta name="theme-color" content="{button}">
<style>
  :root {{ --paper: {paper}; --ink: #18181b; --muted: #52525b; --brand: {button}; --on-brand: {button_text};
          --accent: {accent}; --line: #e4e4e7; }}
  @media (prefers-color-scheme: dark) {{
    :root {{ --paper: {paper_dark}; --ink: #f4f4f5; --muted: #a1a1aa; --accent: {accent_dark}; --line: #27272a; }}
  }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; min-height: 100vh; background: var(--paper); color: var(--ink);
         font: 16px/1.5 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }}
  main {{ max-width: 480px; margin: 0 auto; padding: 48px 20px 32px; text-align: center; }}
  .badge {{ width: 96px; height: 96px; border-radius: 50%; margin: 0 auto 16px; display: grid; place-items: center;
           background: var(--brand); color: var(--on-brand); font-weight: 800; font-size: 34px; object-fit: cover; }}
  h1 {{ font-size: 24px; margin: 0 0 6px; }}
  p {{ margin: 0 0 28px; color: var(--muted); }}
  ul {{ list-style: none; margin: 0; padding: 0; display: grid; gap: 12px; }}
  .btn {{ display: flex; align-items: center; justify-content: center; min-height: 52px; padding: 12px 20px;
         border-radius: 14px; background: var(--brand); color: var(--on-brand); font-weight: 650;
         text-decoration: none; transition: transform .15s ease, box-shadow .15s ease; }}
  .btn:hover {{ transform: translateY(-2px); box-shadow: 0 8px 20px rgb(0 0 0 / .15); }}
  .btn:focus-visible, footer a:focus-visible {{ outline: 3px solid var(--accent); outline-offset: 3px; }}
  footer {{ margin-top: 32px; padding-top: 20px; border-top: 1px solid var(--line); display: flex; flex-wrap: wrap;
           justify-content: center; gap: 8px 18px; }}
  footer a {{ color: var(--accent); font-weight: 600; text-decoration: none; padding: 6px 2px; }}
  @media (prefers-reduced-motion: reduce) {{ .btn {{ transition: none; }} .btn:hover {{ transform: none; }} }}
</style>
</head>
<body>
  <main>
    {badge}
    <h1>{e(name)}</h1>
    {f'<p>{e(tagline)}</p>' if tagline else ''}
    <ul>
{items}
    </ul>
    {f'<footer>{small}</footer>' if socials else ''}
  </main>
</body>
</html>
"""


def rel(url: str) -> str:
    return ' target="_blank" rel="noopener"' if url.startswith("https://") else ""


def run(settings: Settings, args: dict) -> str:
    clean = lambda v: " ".join(str(v or "").split())  # noqa: E731
    name = clean(args.get("name"))
    if not name:
        raise ValueError("Give the business name for the link page.")
    brand = colour(args.get("colour") or "")
    tagline = clean(args.get("tagline"))
    if len(tagline) > 120:
        raise ValueError("Keep the short line under 120 letters.")
    raw = args.get("links") or []
    if not isinstance(raw, list):
        raise ValueError("Give the links as a list of {label, url}.")
    links = []
    for item in raw:
        if not isinstance(item, dict):
            raise ValueError("Each link needs a label and a url, e.g. {label: 'Book now', url: 'https://...'}.")
        label, url = clean(item.get("label"))[:40], clean(item.get("url"))
        if not label or not url:
            raise ValueError("Each link needs a label and a url.")
        links.append((label, safe_url(url)))
    if not 1 <= len(links) <= MAX_LINKS:
        raise ValueError(f"Give 1 to {MAX_LINKS} links (more than that and people stop reading).")
    whatsapp = re.sub(r"[^\d]", "", str(args.get("whatsapp") or ""))
    if whatsapp:
        if not 7 <= len(whatsapp) <= 15:
            raise ValueError("Give the WhatsApp number with the country code, e.g. 447700900123.")
        links.append(("Message us on WhatsApp", f"https://wa.me/{whatsapp}"))
    given = args.get("socials") or {}
    if not isinstance(given, dict):
        raise ValueError("Give socials like {instagram: '@name'}.")
    bad = [k for k in given if k.lower() not in SOCIALS]
    if bad:
        raise ValueError(f"Socials can be {', '.join(SOCIALS)}.")
    socials = [(SOCIALS[k.lower()][0], social_url(k.lower(), str(v))) for k, v in given.items() if clean(v)]
    logo = safe_url(clean(args.get("logo"))) if clean(args.get("logo")) else ""
    if logo and not logo.startswith("https://"):
        raise ValueError("The logo must be a https:// image address.")
    (memory.root(settings) / FOLDER).mkdir(parents=True, exist_ok=True)
    path = memory.folder(settings, f"{FOLDER}/{memory.safe_name(name, 'folder name')}/web", create=True)
    (path / "links.html").write_text(page(name, brand, tagline, links, socials, logo), encoding="utf-8")
    where = path.relative_to(memory.root(settings)).as_posix()
    return (f"Made a link-in-bio page for {name} in {where}/links.html with {len(links)} button"
            f"{'s' if len(links) != 1 else ''}{f' and {len(socials)} social links' if socials else ''}. It's one "
            "file that works on any phone, in light and dark mode. Upload it (Cloudflare Pages, Netlify or their "
            "own site at /links) and put that address in the Instagram and TikTok bio.")


def tool_definitions() -> list[dict]:
    return [{
        "name": "make_link_page",
        "description": "Make a link-in-bio page (like Linktree, but the client owns it): one self-contained HTML file "
                       "in the brand colour with initials or logo, name, short line, up to 8 big phone-friendly "
                       "buttons, an optional WhatsApp button and social links. Dark mode and AA contrast built in. "
                       "Saves links.html in Kinetic Web Designs/<name>/web. Answer in plain words.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Business name (page and folder)."},
                "colour": {"type": "string", "description": "Brand colour, e.g. '#c2410c'."},
                "tagline": {"type": "string", "description": "Short line under the name."},
                "links": {"type": "array", "description": "1-8 buttons, top first.", "items": {
                    "type": "object", "properties": {"label": {"type": "string"}, "url": {"type": "string"}},
                    "required": ["label", "url"]}},
                "whatsapp": {"type": "string", "description": "Number with country code for a WhatsApp button."},
                "socials": {"type": "object", "description": "e.g. {instagram: '@name', tiktok: '@name'}.",
                            "properties": {k: {"type": "string"} for k in SOCIALS}},
                "logo": {"type": "string", "description": "https address of a square logo image (optional)."},
            },
            "required": ["name", "colour", "links"],
            "additionalProperties": False,
        },
    }]


async def run_tool(name: str, args: dict, settings: Settings, http=None) -> str:
    try:
        return run(settings, args)
    except (TypeError, ValueError) as e:
        return str(e)
