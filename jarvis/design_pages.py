"""Small site pages every client needs sooner or later: "page not found", "coming soon" and "back shortly".

make_site_page writes one self-contained HTML page in the brand colour, with no outside files, so it works even when
the rest of the site is down:
- not-found (404.html): a friendly "We can't find that page" with a button home, a search box if the site has a search
  page, and up to 4 popular links, so a broken link doesn't lose the customer. Cloudflare Pages and Netlify pick up a
  file called 404.html by themselves.
- coming-soon (coming-soon.html): the business name, a short line, an optional launch date with a live countdown, and
  ways to get in touch (email, phone, Instagram) while the site is built.
- maintenance (maintenance.html): "We'll be back shortly" with an optional time, and how to reach the business
  meanwhile. It tells search engines not to index it, so the stop doesn't hurt Google ranking.
Each page has the initials badge, a soft brand-coloured shape for depth, AA contrast, dark mode and reduced-motion
support. Saved in Kinetic Web Designs/<name>/web.
"""

import datetime as dt
import html
import re

import memory
from config import Settings
from design_contrast import AA, colour, fix, ratio
from design_extract import FOLDER
from design_logo import initials
from design_palette import on

NAMES = {"make_site_page"}
KINDS = {"not-found": "404.html", "coming-soon": "coming-soon.html", "maintenance": "maintenance.html"}
MAX_LINKS = 4


def safe_link(url: str) -> str:
    url = url.strip()
    if re.match(r"^(https://[^\s\"'<>]+|/[^\s\"'<>]*)$", url):
        return url
    raise ValueError(f"'{url[:60]}' isn't a link I can use; give a https:// address or a path like /contact.")


def contact_rows(email: str, phone: str, instagram: str) -> list[tuple[str, str]]:
    rows = []
    if email:
        if not re.fullmatch(r"[^\s@<>\"']+@[^\s@<>\"']+\.[^\s@<>\"']+", email):
            raise ValueError("That email address doesn't look right.")
        rows.append((email, f"mailto:{email}"))
    if phone:
        digits = re.sub(r"[^\d+]", "", phone)
        if len(re.sub(r"\D", "", digits)) < 7:
            raise ValueError("That phone number looks too short.")
        rows.append((phone, f"tel:{digits}"))
    if instagram:
        handle = instagram.strip().lstrip("@")
        if not re.fullmatch(r"[\w.]{1,30}", handle):
            raise ValueError("That doesn't look like an Instagram handle.")
        rows.append((f"@{handle} on Instagram", f"https://instagram.com/{handle}"))
    return rows


def page(kind: str, name: str, brand: str, headline: str, text: str, home: str, links: list[tuple[str, str]],
         search: str, contacts: list[tuple[str, str]], when: dt.datetime | None) -> str:
    e = html.escape
    paper, paper_dark = "#ffffff", "#111114"
    button = brand if ratio(on(brand), brand) >= AA else fix(brand, on(brand), AA)
    accent = brand if ratio(brand, paper) >= AA else fix(brand, paper, AA)
    accent_dark = brand if ratio(brand, paper_dark) >= AA else fix(brand, paper_dark, AA)
    title = {"not-found": "Page not found", "coming-soon": "Coming soon", "maintenance": "Back shortly"}[kind]
    body = []
    if kind == "not-found":
        body.append('<p class="code" aria-hidden="true">404</p>')
    body.append(f"<h1>{e(headline)}</h1>")
    if text:
        body.append(f"<p class=\"lead\">{e(text)}</p>")
    if when:
        nice = f"{when:%A} {when.day} {when:%B %Y}" + (f" at {when:%H:%M}" if when.hour or when.minute else "")
        lead = "Opening" if kind == "coming-soon" else "Back by"
        body.append(f'<p class="when">{lead} <time datetime="{when.isoformat()}">{e(nice)}</time></p>')
        if kind == "coming-soon":
            body.append('<p class="count" id="count" aria-live="polite"></p>')
    if kind == "not-found":
        body.append(f'<p><a class="btn" href="{e(home)}">Go to the home page</a></p>')
        if search:
            body.append(f'<form class="search" action="{e(search)}" role="search"><label for="q">Search the site'
                        '</label><div><input id="q" name="q" type="search" autocomplete="off">'
                        '<button type="submit">Search</button></div></form>')
        if links:
            items = "".join(f'<li><a href="{e(u)}">{e(label)}</a></li>' for label, u in links)
            body.append(f'<nav aria-label="Popular pages"><h2>Popular pages</h2><ul>{items}</ul></nav>')
    if contacts:
        items = "".join(f'<li><a href="{e(u)}">{e(label)}</a></li>' for label, u in contacts)
        lead = "Get in touch" if kind != "not-found" else "Need a hand?"
        body.append(f'<nav aria-label="Contact"><h2>{lead}</h2><ul>{items}</ul></nav>')
    robots = '<meta name="robots" content="noindex">\n' if kind != "coming-soon" else ""
    script = ""
    if when and kind == "coming-soon":
        script = f"""<script>
(() => {{
  const end = new Date("{when.isoformat()}").getTime(), out = document.getElementById("count");
  const tick = () => {{
    const left = Math.max(0, end - Date.now());
    if (!left) {{ out.textContent = "We're open!"; return; }}
    const d = Math.floor(left / 864e5), h = Math.floor(left / 36e5) % 24, m = Math.floor(left / 6e4) % 60;
    out.textContent = (d ? d + (d === 1 ? " day, " : " days, ") : "") + h + (h === 1 ? " hour, " : " hours, ")
      + m + (m === 1 ? " minute" : " minutes") + " to go";
    setTimeout(tick, 30000);
  }};
  tick();
}})();
</script>
"""
    content = "\n    ".join(body)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
{robots}<title>{e(title)} | {e(name)}</title>
<meta name="theme-color" content="{button}">
<style>
  :root {{ --paper: {paper}; --ink: #18181b; --muted: #52525b; --brand: {button}; --on-brand: {on(button)};
          --accent: {accent}; --line: #e4e4e7; --soft: {brand}1f; }}
  @media (prefers-color-scheme: dark) {{
    :root {{ --paper: {paper_dark}; --ink: #f4f4f5; --muted: #a1a1aa; --accent: {accent_dark}; --line: #27272a; }}
  }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; min-height: 100vh; display: grid; grid-template-columns: minmax(0, 1fr);
         place-items: center; background: var(--paper);
         color: var(--ink); font: 17px/1.55 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
         overflow-x: hidden; }}
  body::before {{ content: ""; position: fixed; width: 70vmax; height: 70vmax; right: -25vmax; top: -30vmax;
                 border-radius: 50%; background: var(--soft); z-index: -1; }}
  main {{ width: min(560px, 100%); padding: 48px 20px; text-align: center; }}
  .badge {{ width: 64px; height: 64px; margin: 0 auto 28px; border-radius: 50%; display: grid; place-items: center;
           background: var(--brand); color: var(--on-brand); font-weight: 800; font-size: 24px; }}
  .code {{ font-size: clamp(72px, 22vw, 140px); font-weight: 900; line-height: 1; margin: 0 0 8px;
          color: var(--accent); letter-spacing: -.04em; }}
  h1 {{ font-size: clamp(26px, 6vw, 38px); line-height: 1.15; margin: 0 0 12px; }}
  .lead {{ color: var(--muted); margin: 0 0 24px; }}
  .when {{ font-weight: 650; margin: 0 0 4px; }}
  .count {{ color: var(--accent); font-weight: 700; margin: 0 0 24px; min-height: 1.5em; }}
  .btn, .search button {{ display: inline-flex; align-items: center; justify-content: center; min-height: 48px;
         padding: 12px 24px; border-radius: 12px; border: 0; background: var(--brand); color: var(--on-brand);
         font: inherit; font-weight: 650; text-decoration: none; cursor: pointer; }}
  .search {{ margin: 24px 0; text-align: left; }}
  .search label {{ display: block; font-weight: 600; margin-bottom: 6px; }}
  .search div {{ display: flex; gap: 8px; }}
  .search button {{ flex: none; }}
  .search input {{ flex: 1; min-width: 0; min-height: 48px; padding: 10px 14px; border-radius: 12px;
                  border: 1px solid #8a8a93; background: var(--paper); color: var(--ink); font: inherit; }}
  nav {{ margin-top: 28px; padding-top: 20px; border-top: 1px solid var(--line); }}
  h2 {{ font-size: 15px; text-transform: uppercase; letter-spacing: .08em; color: var(--muted); margin: 0 0 10px; }}
  ul {{ list-style: none; margin: 0; padding: 0; display: flex; flex-wrap: wrap; justify-content: center;
       gap: 6px 20px; }}
  nav a {{ color: var(--accent); font-weight: 600; display: inline-block; padding: 6px 0; }}
  a:focus-visible, button:focus-visible, input:focus-visible {{ outline: 3px solid var(--accent);
       outline-offset: 3px; }}
  @media (prefers-reduced-motion: no-preference) {{ main {{ animation: rise .5s ease-out both; }} }}
  @keyframes rise {{ from {{ opacity: 0; transform: translateY(14px); }} }}
</style>
</head>
<body>
  <main>
    <div class="badge" aria-hidden="true">{e(initials(name))}</div>
    {content}
  </main>
{script}</body>
</html>
"""


def when_of(value: str) -> dt.datetime | None:
    value = value.strip()
    if not value:
        return None
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M", "%Y-%m-%d"):
        try:
            return dt.datetime.strptime(value, fmt)
        except ValueError:
            pass
    raise ValueError("Give the date like 2026-12-01, or 2026-12-01 18:00 with a time.")


def run(settings: Settings, args: dict) -> str:
    clean = lambda v: " ".join(str(v or "").split())  # noqa: E731
    name = clean(args.get("name"))
    if not name:
        raise ValueError("Give the business name for the page.")
    brand = colour(args.get("colour") or "")
    kind = clean(args.get("kind")).lower() or "not-found"
    if kind not in KINDS:
        raise ValueError(f"Pick a page: {', '.join(KINDS)}.")
    default = {"not-found": ("We can't find that page", "It may have moved, or the link has a typo."),
               "coming-soon": (f"{name} is coming soon", "Our new website is nearly ready."),
               "maintenance": ("We'll be back shortly", "We're making a few improvements to the site.")}[kind]
    headline = clean(args.get("headline")) or default[0]
    text = clean(args.get("text")) if args.get("text") is not None else default[1]
    if len(headline) > 80 or len(text) > 240:
        raise ValueError("Keep the headline under 80 letters and the line under 240.")
    home = safe_link(clean(args.get("home")) or "/")
    search = safe_link(clean(args.get("search_url"))) if clean(args.get("search_url")) else ""
    raw = args.get("links") or []
    if not isinstance(raw, list) or len(raw) > MAX_LINKS:
        raise ValueError(f"Give up to {MAX_LINKS} popular links as {{label, url}}.")
    links = []
    for item in raw:
        if not isinstance(item, dict) or not clean(item.get("label")) or not clean(item.get("url")):
            raise ValueError("Each link needs a label and a url.")
        links.append((clean(item.get("label"))[:30], safe_link(clean(item.get("url")))))
    contacts = contact_rows(clean(args.get("email")), clean(args.get("phone")), clean(args.get("instagram")))
    when = when_of(clean(args.get("date")))
    if when and kind == "not-found":
        raise ValueError("A date only fits a coming-soon or maintenance page.")
    (memory.root(settings) / FOLDER).mkdir(parents=True, exist_ok=True)
    path = memory.folder(settings, f"{FOLDER}/{memory.safe_name(name, 'folder name')}/web", create=True)
    file = KINDS[kind]
    (path / file).write_text(page(kind, name, brand, headline, text, home, links, search, contacts, when),
                             encoding="utf-8")
    where = path.relative_to(memory.root(settings)).as_posix()
    tip = {"not-found": "Put it at the top of the site as 404.html; Cloudflare Pages and Netlify use it by "
                        "themselves for any missing page.",
           "coming-soon": "Put it up as the home page until the real site is ready."
                          + (" The countdown updates by itself." if when else ""),
           "maintenance": "Show it while the site is being worked on; it tells Google not to index it, so rankings "
                          "aren't hurt."}[kind]
    return f"Made a {kind.replace('-', ' ')} page for {name} in {where}/{file}. {tip}"


def tool_definitions() -> list[dict]:
    return [{
        "name": "make_site_page",
        "description": "Make a branded, self-contained site page: 'not-found' (404.html with a home button, optional "
                       "search box and up to 4 popular links), 'coming-soon' (with optional launch date and live "
                       "countdown) or 'maintenance' (back shortly, not indexed by Google). Brand colour, initials "
                       "badge, contact links, dark mode and AA contrast. Saves in Kinetic Web Designs/<name>/web. "
                       "Answer in plain words.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Business name (page and folder)."},
                "colour": {"type": "string", "description": "Brand colour, e.g. '#c2410c'."},
                "kind": {"type": "string", "enum": list(KINDS), "description": "Default not-found."},
                "headline": {"type": "string"},
                "text": {"type": "string", "description": "Short line under the headline ('' for none)."},
                "date": {"type": "string", "description": "Launch or return time, e.g. '2026-12-01 18:00'."},
                "home": {"type": "string", "description": "Home page link (default /)."},
                "search_url": {"type": "string", "description": "Search page, e.g. /search (adds a search box)."},
                "links": {"type": "array", "description": "Up to 4 popular pages.", "items": {
                    "type": "object", "properties": {"label": {"type": "string"}, "url": {"type": "string"}},
                    "required": ["label", "url"]}},
                "email": {"type": "string"},
                "phone": {"type": "string"},
                "instagram": {"type": "string", "description": "Handle, e.g. @kineticwebdesigns."},
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
