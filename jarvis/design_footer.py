"""Site footers: the band at the bottom of every page that people scroll to when they want to call, find or trust you.

make_site_footer writes a paste-in HTML block in a deep shade of the brand colour that follows what works on
small-business sites: the business name with a one-line tagline, up to four columns of links (e.g. Services, Visit,
Company), the quick ways to reach them (tap-to-call phone, email, the address and opening hours line), social links,
and a bottom bar with the copyright line, legal links (privacy, terms) and an optional "Cookie settings" button that
reopens the make_cookie_banner choices. The columns sit side by side on a laptop and stack on a phone, each link list
is a labelled <nav> so screen readers can jump to it, every link is at least 44px tall to tap, and every colour pair
passes WCAG AA on the dark background. No JavaScript apart from the cookie button's one-line click, which opens
the banner's settings when that banner is on the page. Saves footer.html and footer-preview.html in
Kinetic Web Designs/<name>/web.
"""

import datetime
import html
import re

import memory
from config import Settings
from design_contact import CODES, SOCIALS, phone_link
from design_contrast import AA, colour, fix, ratio
from design_extract import FOLDER
from design_social import mix

NAMES = {"make_site_footer"}
MAX_COLUMNS, MAX_LINKS = 4, 8
LINK = re.compile(r"^(https://[^\s\"'<>]+|/[^\s\"'<>]*|#[\w-]*|mailto:[^\s\"'<>]+|tel:[\d+ ()-]+)$")


def safe_link(url: str, what: str) -> str:
    url = url.strip()
    if LINK.match(url):
        return url
    raise ValueError(f"The '{what}' link '{url[:60]}' isn't one I can use; give https://..., /page, #section, "
                     "mailto: or tel:.")


def shades(brand: str) -> dict:
    """Deep brand background with light text, a softer line colour and a link colour that all pass AA."""
    bg = "#%02x%02x%02x" % mix(brand, "#000000", 0.78)
    text = "#f4f4f5"
    soft = fix("#a1a1aa", bg, AA) if ratio("#a1a1aa", bg) < AA else "#a1a1aa"
    tint = "#%02x%02x%02x" % mix(brand, "#ffffff", 0.55)
    link = tint if ratio(tint, bg) >= AA else fix(tint, bg, AA)
    line = "#%02x%02x%02x" % mix(bg, "#ffffff", 0.14)
    return {"bg": bg, "text": text, "soft": soft, "link": link, "line": line}


def block(d: dict) -> str:
    e = html.escape
    c = shades(d["brand"])
    new_tab = ' target="_blank" rel="noopener"'
    cols = []
    for i, (title, links) in enumerate(d["columns"]):
        items = "\n".join(f'          <li><a href="{e(u)}"{new_tab if u.startswith("https://") else ""}>{e(t)}</a></li>'
                          for t, u in links)
        cols.append(f'    <nav class="f-col" aria-labelledby="f-c{i}">\n      <h2 id="f-c{i}">{e(title)}</h2>\n'
                    f'      <ul>\n{items}\n      </ul>\n    </nav>')
    reach = []
    if d["phone"]:
        reach.append(f'<li><a href="tel:{e(d["phone_link"])}">{e(d["phone"])}</a></li>')
    if d["email"]:
        reach.append(f'<li><a href="mailto:{e(d["email"])}">{e(d["email"])}</a></li>')
    if d["address"]:
        reach.append(f'<li><address>{"<br>".join(e(x) for x in d["address"])}</address></li>')
    if d["hours"]:
        reach.append(f'<li class="f-soft">{e(d["hours"])}</li>')
    if reach:
        cols.append('    <div class="f-col">\n      <h2>Get in touch</h2>\n      <ul>\n'
                    + "\n".join(f"        {r}" for r in reach) + "\n      </ul>\n    </div>")
    soc = "".join(f'<a href="{e(u)}"{new_tab}>{e(label)}</a>' for label, u in d["socials"])
    legal = "".join(f'<a href="{e(u)}">{e(t)}</a>' for t, u in d["legal"])
    if d["cookie_button"]:
        legal += ('<button type="button" onclick="var b=document.getElementById(\'ck-open\');if(b)b.click()">'
                  'Cookie settings</button>')
    tagline = f'\n      <p class="f-soft">{e(d["tagline"])}</p>' if d["tagline"] else ""
    socials = f'\n      <p class="f-social">{soc}</p>' if soc else ""
    top = '<a class="f-top" href="#top">Back to top ↑</a>' if d["back_to_top"] else ""
    return f"""<!-- Footer for {e(d["name"])}: paste this block at the very bottom of every page. -->
<footer class="site-footer"
        style="--f-bg:{c["bg"]};--f-text:{c["text"]};--f-soft:{c["soft"]};--f-link:{c["link"]};--f-line:{c["line"]}">
  <style>
    .site-footer {{ font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; background: var(--f-bg);
                   color: var(--f-text); padding: clamp(2.5rem, 6vw, 4rem) clamp(1rem, 5vw, 3rem) 1.5rem; }}
    .f-wrap {{ max-width: 72rem; margin: 0 auto; }}
    .f-grid {{ display: grid; gap: 2rem 2.5rem; grid-template-columns: minmax(0, 1.4fr)
              repeat(auto-fit, minmax(10rem, 1fr)); }}
    .f-brand strong {{ font-size: 1.35rem; letter-spacing: -.01em; }}
    .site-footer p {{ margin: .6rem 0 0; line-height: 1.55; }}
    .f-soft {{ color: var(--f-soft); }}
    .site-footer h2 {{ font-size: .8rem; text-transform: uppercase; letter-spacing: .08em; color: var(--f-soft);
                      margin: 0 0 .5rem; }}
    .site-footer ul {{ list-style: none; margin: 0; padding: 0; }}
    .site-footer li {{ line-height: 1.5; overflow-wrap: anywhere; }}
    .site-footer address {{ font-style: normal; padding: .6rem 0; }}
    .site-footer a, .site-footer button {{ color: var(--f-link); text-decoration: none; font: inherit; }}
    .f-col a, .f-social a, .f-legal a, .f-legal button, .f-top {{ display: inline-flex; align-items: center;
                      min-height: 44px; }}
    .f-col li.f-soft {{ padding: .6rem 0; }}
    .site-footer a:hover {{ text-decoration: underline; text-underline-offset: 3px; }}
    .site-footer a:focus-visible, .site-footer button:focus-visible {{ outline: 3px solid var(--f-link);
                      outline-offset: 2px; border-radius: 4px; }}
    .f-social {{ display: flex; flex-wrap: wrap; gap: 0 1.25rem; font-weight: 600; }}
    .f-bar {{ margin-top: 2.5rem; padding-top: 1rem; border-top: 1px solid var(--f-line); display: flex;
             flex-wrap: wrap; gap: .25rem 1.5rem; align-items: center; justify-content: space-between;
             font-size: .9rem; color: var(--f-soft); }}
    .f-legal {{ display: flex; flex-wrap: wrap; gap: 0 1.25rem; }}
    .f-legal button {{ background: none; border: 0; padding: 0; cursor: pointer; }}
    @media (max-width: 40rem) {{ .f-grid {{ grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); }}
                                .f-brand {{ grid-column: 1 / -1; }} }}
  </style>
  <div class="f-wrap">
    <div class="f-grid">
    <div class="f-brand">
      <strong>{e(d["name"])}</strong>{tagline}{socials}
    </div>
{chr(10).join(cols)}
    </div>
    <div class="f-bar">
      <span>© {d["year"]} {e(d["owner"])}{(". " + e(d["company_line"])) if d["company_line"] else ""}</span>
      <span class="f-legal">{legal}{top}</span>
    </div>
  </div>
</footer>
"""


def run(settings: Settings, args: dict) -> str:
    clean = lambda v: " ".join(str(v or "").split())  # noqa: E731
    name = clean(args.get("name"))
    if not name:
        raise ValueError("Give the business name for the footer.")
    if len(name) > 60:
        raise ValueError("Keep the business name under 60 letters.")
    brand = colour(args.get("colour") or "")
    raw = args.get("columns") or []
    if not isinstance(raw, list) or len(raw) > MAX_COLUMNS:
        raise ValueError(f"Give up to {MAX_COLUMNS} link columns, each with a title and links.")
    columns = []
    for col in raw:
        if not isinstance(col, dict) or not clean(col.get("title")):
            raise ValueError("Each column needs a title, e.g. 'Services', and its links.")
        links = col.get("links") or []
        if not isinstance(links, list) or not 1 <= len(links) <= MAX_LINKS:
            raise ValueError(f"Give the '{clean(col.get('title'))[:30]}' column 1 to {MAX_LINKS} links.")
        pairs = []
        for link in links:
            if not isinstance(link, dict) or not clean(link.get("text")) or not clean(link.get("url")):
                raise ValueError("Each link needs its words and where it goes, e.g. {text: 'Prices', url: '/prices'}.")
            pairs.append((clean(link["text"])[:40], safe_link(clean(link["url"]), clean(link["text"])[:30])))
        columns.append((clean(col["title"])[:30], pairs))
    country = clean(args.get("country")).upper()
    if country and country not in CODES:
        raise ValueError(f"Country can be {', '.join(CODES)} (it sets the phone code).")
    phone = clean(args.get("phone"))
    email = clean(args.get("email"))
    if email and not re.fullmatch(r"[^\s@<>\"']+@[^\s@<>\"']+\.[^\s@<>\"']+", email):
        raise ValueError("That email address doesn't look right.")
    addr = args.get("address") or []
    lines = [clean(x) for x in (addr if isinstance(addr, list) else str(addr).split(","))]
    socials = []
    for key, value in (args.get("socials") or {}).items():
        if key.lower() not in SOCIALS:
            raise ValueError(f"Socials can be {', '.join(SOCIALS)}.")
        handle = clean(value).lstrip("@")
        if handle and not re.fullmatch(r"[\w.-]{1,60}", handle):
            raise ValueError(f"'{handle[:40]}' doesn't look like a {SOCIALS[key.lower()][0]} handle.")
        if handle:
            socials.append((SOCIALS[key.lower()][0], SOCIALS[key.lower()][1].format(handle)))
    legal = [("Privacy", safe_link(clean(args.get("privacy_url")) or "/privacy", "Privacy"))]
    if clean(args.get("terms_url")):
        legal.append(("Terms", safe_link(clean(args.get("terms_url")), "Terms")))
    year = args.get("year") or datetime.date.today().year
    if not isinstance(year, int) or not 1990 <= year <= 2100:
        raise ValueError("Give the copyright year as a number, e.g. 2026.")
    d = {"name": name, "brand": brand, "tagline": clean(args.get("tagline"))[:120], "columns": columns,
         "phone": phone, "phone_link": phone_link(phone, country) if phone else "", "email": email,
         "address": [x for x in lines if x][:6], "hours": clean(args.get("hours"))[:120], "socials": socials,
         "legal": legal, "cookie_button": args.get("cookie_button", True) is not False,
         "back_to_top": args.get("back_to_top", True) is not False, "year": year,
         "owner": clean(args.get("legal_name")) or name, "company_line": clean(args.get("company_line"))[:120]}
    code = block(d)
    preview = (f"<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n<meta name=\"viewport\" "
               f"content=\"width=device-width, initial-scale=1\">\n<title>{html.escape(name)} | Footer</title>\n"
               "</head>\n<body id=\"top\" style=\"margin:0;background:#fff\">\n<main style=\"min-height:60vh;"
               "display:grid;place-items:center;font-family:system-ui;color:#71717a\">Page content</main>\n"
               + code + "</body>\n</html>\n")
    (memory.root(settings) / FOLDER).mkdir(parents=True, exist_ok=True)
    path = memory.folder(settings, f"{FOLDER}/{memory.safe_name(name, 'folder name')}/web", create=True)
    (path / "footer.html").write_text(code, encoding="utf-8")
    (path / "footer-preview.html").write_text(preview, encoding="utf-8")
    where = path.relative_to(memory.root(settings)).as_posix()
    tips = []
    if not (phone or email or d["address"]):
        tips.append("Add a phone, email or address so people can reach you from any page.")
    if d["back_to_top"]:
        tips.append("Give the page's <body> id=\"top\" so 'Back to top' jumps there.")
    if d["cookie_button"]:
        tips.append("The Cookie settings button works once make_cookie_banner's block is on the page.")
    if country == "GB" and not d["company_line"]:
        tips.append("UK limited companies must show their registered number and office; add it as company_line.")
    return (f"Made a footer for {name} with {len(columns)} link column{'s' if len(columns) != 1 else ''} in {where}: "
            "footer.html to paste at the bottom of every page and footer-preview.html to check it. "
            + " ".join(tips)).strip()


def tool_definitions() -> list[dict]:
    return [{
        "name": "make_site_footer",
        "description": "Make a paste-in website footer in a deep shade of the brand colour: name and tagline, up to "
                       "4 link columns, tap-to-call phone, email, address and hours, socials, and a bottom bar with "
                       "copyright, privacy/terms links, a Cookie settings button and Back to top. Stacks on phones, "
                       "44px tap targets, AA contrast, no JavaScript. Saves footer.html and a preview in "
                       "Kinetic Web Designs/<name>/web. Answer in plain words.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Business name (the folder)."},
                "colour": {"type": "string", "description": "Brand colour, e.g. '#c2410c'."},
                "tagline": {"type": "string", "description": "One line, e.g. 'Sourdough baked in Hockley'."},
                "columns": {"type": "array", "description": "Up to 4 link columns.", "items": {
                    "type": "object", "properties": {
                        "title": {"type": "string"},
                        "links": {"type": "array", "items": {"type": "object", "properties": {
                            "text": {"type": "string"}, "url": {"type": "string"}}, "required": ["text", "url"]}}},
                    "required": ["title", "links"]}},
                "country": {"type": "string", "enum": list(CODES), "description": "Sets the phone code, e.g. GB."},
                "phone": {"type": "string"},
                "email": {"type": "string"},
                "address": {"type": "array", "items": {"type": "string"}},
                "hours": {"type": "string", "description": "e.g. 'Mon-Sat 9am-5:30pm'."},
                "socials": {"type": "object", "properties": {k: {"type": "string"} for k in SOCIALS}},
                "privacy_url": {"type": "string", "description": "Default /privacy."},
                "terms_url": {"type": "string"},
                "cookie_button": {"type": "boolean", "description": "Show 'Cookie settings' (default yes)."},
                "back_to_top": {"type": "boolean", "description": "Show 'Back to top' (default yes)."},
                "legal_name": {"type": "string", "description": "Name in the copyright line, e.g. 'Lebo Ltd'."},
                "company_line": {"type": "string",
                                 "description": "e.g. 'Registered in England No. 12345678, 21 Hockley Hill'."},
                "year": {"type": "integer", "description": "Copyright year (default this year)."},
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
