"""Site headers: the bar at the top of every page with the name, the menu and the one button that matters most.

make_site_header writes a paste-in HTML block in the brand colour that follows what works on small-business sites:
the business name (or logo) on the left linking home, up to 7 menu links, and one main button on the right ("Book
now", "Call 0121 496 0000"). On a phone the links fold into a "Menu" button that opens a full-width list with a tap
and closes again, built on <details> so it needs no JavaScript and works with screen readers and the keyboard; the
main button stays visible next to it. The page you are on is marked (aria-current="page") and underlined, there is a
"Skip to content" link for keyboard users, the bar can stick to the top while scrolling (with a soft blur), every tap
target is at least 44px and every colour pair passes WCAG AA. Saves header.html and header-preview.html in
Kinetic Web Designs/<name>/web.
"""

import html
import re

import memory
from config import Settings
from design_contrast import AA, colour, fix, ratio
from design_extract import FOLDER
from design_palette import on

NAMES = {"make_site_header"}
MAX_LINKS = 7
LINK = re.compile(r"^(https://[^\s\"'<>]+|/[^\s\"'<>]*|#[\w-]*|mailto:[^\s\"'<>]+|tel:[\d+ ()-]+)$")


def safe_link(url: str, what: str) -> str:
    url = url.strip()
    if LINK.match(url):
        return url
    raise ValueError(f"The '{what}' link '{url[:60]}' isn't one I can use; give https://..., /page, #section, "
                     "mailto: or tel:.")


def links_html(links: list[tuple[str, str]], current: str, cls: str) -> str:
    e = html.escape
    rows = []
    for text, url in links:
        here = ' aria-current="page"' if current and current.lower() in (text.lower(), url.lower()) else ""
        rows.append(f'<li><a class="{cls}" href="{e(url)}"{here}>{e(text)}</a></li>')
    return "".join(rows)


def block(d: dict) -> str:
    e = html.escape
    brand = d["brand"]
    button = brand if ratio(on(brand), brand) >= AA else fix(brand, on(brand), AA)
    accent = brand if ratio(brand, "#ffffff") >= AA else fix(brand, "#ffffff", AA)
    if d["logo"]:
        home = (f'<img src="{e(d["logo"])}" alt="{e(d["name"])}" height="{d["logo_height"]}" '
                f'style="height:{d["logo_height"]}px;width:auto;display:block">')
    else:
        home = f"<span>{e(d['name'])}</span>"
    cta = f'<a class="s-cta" href="{e(d["link"])}">{e(d["button"])}</a>' if d["button"] else ""
    sticky = "position: sticky; top: 0; z-index: 50;" if d["sticky"] else ""
    menu = ""
    if d["links"]:
        menu = f"""
    <nav class="s-nav" aria-label="Main">
      <ul>{links_html(d["links"], d["current"], "s-a")}</ul>
    </nav>
    <details class="s-menu">
      <summary aria-label="Menu"><span class="s-bars" aria-hidden="true"></span>Menu</summary>
      <nav aria-label="Main">
        <ul>{links_html(d["links"], d["current"], "s-a")}</ul>
      </nav>
    </details>"""
    return f"""<!-- Header for {e(d["name"])}: paste this block at the very top of every page, before the hero.
     Put id="main" on the element that holds the page's own content so "Skip to content" lands there. -->
<header class="site-header" style="--s-brand:{button};--s-on:{on(button)};--s-accent:{accent}">
  <style>
    .site-header {{ font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; color: #18181b;
                   background: rgb(255 255 255 / .92); backdrop-filter: saturate(1.4) blur(10px);
                   -webkit-backdrop-filter: saturate(1.4) blur(10px); border-bottom: 1px solid #e4e4e7; {sticky} }}
    .s-skip {{ position: absolute; left: .75rem; top: -4rem; background: var(--s-brand); color: var(--s-on);
              padding: .8rem 1rem; border-radius: .6rem; font-weight: 700; z-index: 60; min-height: 44px;
              box-sizing: border-box; }}
    .s-skip:focus {{ top: .5rem; }}
    .s-bar {{ max-width: 76rem; margin: 0 auto; padding: .5rem clamp(1rem, 4vw, 2rem); display: flex;
             align-items: center; gap: 1rem; min-height: 64px; box-sizing: border-box; }}
    .s-home {{ display: inline-flex; align-items: center; min-height: 44px; margin-right: auto; color: inherit;
              text-decoration: none; font-weight: 800; font-size: 1.2rem; letter-spacing: -.01em;
              line-height: 1.15; }}
    .site-header ul {{ list-style: none; margin: 0; padding: 0; }}
    .s-nav ul {{ display: flex; gap: .25rem; }}
    .s-a {{ display: inline-flex; align-items: center; min-height: 44px; padding: 0 .75rem; border-radius: .6rem;
           color: #3f3f46; text-decoration: none; font-weight: 600; }}
    .s-a:hover {{ color: var(--s-accent); background: #f4f4f5; }}
    .s-a[aria-current="page"] {{ color: var(--s-accent); text-decoration: underline; text-decoration-thickness: 2px;
                                text-underline-offset: 6px; }}
    .s-cta {{ box-sizing: border-box; display: inline-flex; align-items: center; justify-content: center;
             min-height: 44px; padding: .55rem 1.1rem; border-radius: .75rem; background: var(--s-brand);
             color: var(--s-on); font-weight: 700; text-decoration: none; white-space: nowrap; }}
    .site-header a:focus-visible, .s-menu summary:focus-visible {{ outline: 3px solid var(--s-accent);
                                                                    outline-offset: 2px; }}
    .s-menu {{ display: none; }}
    .s-menu summary {{ list-style: none; cursor: pointer; display: inline-flex; align-items: center; gap: .5rem;
                      min-height: 44px; padding: 0 .75rem; border: 1px solid #d4d4d8; border-radius: .75rem;
                      font-weight: 700; }}
    .s-menu summary::-webkit-details-marker {{ display: none; }}
    .s-bars, .s-bars::before, .s-bars::after {{ display: block; width: 18px; height: 2px; background: currentColor;
                                               border-radius: 2px; position: relative; content: ""; }}
    .s-bars::before {{ position: absolute; top: -6px; }}
    .s-bars::after {{ position: absolute; top: 6px; }}
    .s-menu[open] .s-bars {{ background: transparent; }}
    .s-menu[open] .s-bars::before {{ top: 0; transform: rotate(45deg); }}
    .s-menu[open] .s-bars::after {{ top: 0; transform: rotate(-45deg); }}
    .s-menu nav {{ position: absolute; left: 0; right: 0; top: 100%; background: #fff; border-bottom: 1px solid #e4e4e7;
                  box-shadow: 0 16px 32px rgb(0 0 0 / .08); padding: .5rem clamp(1rem, 4vw, 2rem) 1rem; }}
    .s-menu .s-a {{ display: flex; font-size: 1.1rem; padding: 0 .5rem; }}
    @media (max-width: {d["fold"]}rem) {{
      .site-header {{ position: {"sticky" if d["sticky"] else "relative"}; }}
      .s-nav {{ display: none; }}
      .s-menu {{ display: block; order: 3; }}
      .s-cta {{ padding: .55rem .9rem; }}
    }}
    @media (max-width: 22rem) {{ .s-cta {{ display: none; }} }}
  </style>
  <a class="s-skip" href="#main">Skip to content</a>
  <div class="s-bar">
    <a class="s-home" href="{e(d["home"])}">{home}</a>{menu}
    {cta}
  </div>
</header>
"""


def run(settings: Settings, args: dict) -> str:
    clean = lambda v: " ".join(str(v or "").split())  # noqa: E731
    name = clean(args.get("name"))
    if not name:
        raise ValueError("Give the business name for the header.")
    if len(name) > 40:
        raise ValueError("Keep the name in the header under 40 letters, or give a logo instead.")
    brand = colour(args.get("colour") or "")
    raw = args.get("links") or []
    if not isinstance(raw, list) or len(raw) > MAX_LINKS:
        raise ValueError(f"Give up to {MAX_LINKS} menu links; more than that is hard to scan on a phone.")
    links = []
    for link in raw:
        if not isinstance(link, dict) or not clean(link.get("text")) or not clean(link.get("url")):
            raise ValueError("Each menu link needs its words and where it goes, e.g. {text: 'Prices', url: '/prices'}.")
        text = clean(link["text"])
        if len(text) > 24:
            raise ValueError(f"Keep the menu word '{text[:30]}' short (under 24 letters).")
        links.append((text, safe_link(clean(link["url"]), text)))
    if len({t.lower() for t, _ in links}) != len(links):
        raise ValueError("Two menu links have the same words; give each its own.")
    button = clean(args.get("button"))
    if len(button) > 24:
        raise ValueError("Keep the button under 24 letters, e.g. 'Book now'.")
    link = safe_link(clean(args.get("link")) or "#contact", "button") if button else ""
    logo = clean(args.get("logo"))
    if logo and not re.match(r"^(https://[^\s\"'<>]+|/[^\s\"'<>]+)$", logo):
        raise ValueError("Give the logo as a https:// address or a site path like /img/logo.svg.")
    height = args.get("logo_height") or 40
    if not isinstance(height, int) or not 20 <= height <= 64:
        raise ValueError("Give the logo height in pixels between 20 and 64.")
    chars = sum(len(t) for t, _ in links) + len(name if not logo else "") + len(button)
    fold = max(40, min(64, round(chars * 0.62 + len(links) * 1.6 + 8)))
    d = {"name": name, "brand": brand, "links": links, "current": clean(args.get("current")), "button": button,
         "link": link, "logo": logo, "logo_height": height, "home": safe_link(clean(args.get("home")) or "/", "home"),
         "sticky": args.get("sticky", True) is not False, "fold": fold}
    code = block(d)
    filler = "".join(f"<p>Page content line {i}.</p>" for i in range(1, 41))
    preview = (f"<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n<meta name=\"viewport\" "
               f"content=\"width=device-width, initial-scale=1\">\n<title>{html.escape(name)} | Header</title>\n"
               "</head>\n<body style=\"margin:0;background:#fff\">\n" + code
               + "<main id=\"main\" style=\"max-width:76rem;margin:0 auto;padding:2rem 1rem;font-family:system-ui;"
               f"color:#71717a\">{filler}</main>\n</body>\n</html>\n")
    (memory.root(settings) / FOLDER).mkdir(parents=True, exist_ok=True)
    path = memory.folder(settings, f"{FOLDER}/{memory.safe_name(name, 'folder name')}/web", create=True)
    (path / "header.html").write_text(code, encoding="utf-8")
    (path / "header-preview.html").write_text(preview, encoding="utf-8")
    where = path.relative_to(memory.root(settings)).as_posix()
    tips = ['Put id="main" on the page\'s main content so "Skip to content" works.']
    if d["current"] and not any(d["current"].lower() in (t.lower(), u.lower()) for t, u in links):
        tips.append(f"'{d['current']}' isn't one of the menu links, so no page is marked as current.")
    if not button:
        tips.append("Add a main button (e.g. 'Book now') so the next step is always one tap away.")
    return (f"Made a header for {name} with {len(links)} menu link{'s' if len(links) != 1 else ''} in {where}: "
            f"header.html to paste at the top of every page and header-preview.html to check it. On screens under "
            f"about {fold * 16}px wide the links fold into a Menu button. " + " ".join(tips))


def tool_definitions() -> list[dict]:
    return [{
        "name": "make_site_header",
        "description": "Make a paste-in website header (top bar) in the brand colour: name or logo linking home, up "
                       "to 7 menu links with the current page marked, and one main button (e.g. 'Book now'). On "
                       "phones the links fold into a Menu button (no JavaScript); optional sticky bar with blur, "
                       "Skip to content link, 44px tap targets, AA contrast. Saves header.html and a preview in "
                       "Kinetic Web Designs/<name>/web. Answer in plain words.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Business name (the folder, and the home link text)."},
                "colour": {"type": "string", "description": "Brand colour, e.g. '#c2410c'."},
                "links": {"type": "array", "description": "Up to 7 menu links, in order.", "items": {
                    "type": "object", "properties": {"text": {"type": "string"}, "url": {"type": "string"}},
                    "required": ["text", "url"]}},
                "current": {"type": "string", "description": "Menu word or link of the page this header is for."},
                "button": {"type": "string", "description": "Main button, e.g. 'Book now'."},
                "link": {"type": "string", "description": "Main button link (default #contact)."},
                "logo": {"type": "string", "description": "Logo address instead of the name (https or /img/...)."},
                "logo_height": {"type": "integer", "description": "Logo height in px, 20-64 (default 40)."},
                "home": {"type": "string", "description": "Home link (default /)."},
                "sticky": {"type": "boolean", "description": "Stay at the top while scrolling (default yes)."},
            },
            "required": ["name", "colour"],
            "additionalProperties": False,
        },
    }]


async def run_tool(name: str, args: dict, settings: Settings, http=None) -> str:
    try:
        return run(settings, args)
    except (TypeError, ValueError) as e:
        return str(e)
