"""Services sections: the "What we do" grid that tells a visitor in one glance whether you do the thing they need.

make_services_section turns 2 to 9 services into a paste-in HTML block in the brand colour: a heading and short intro,
then a card per service with a small line icon in a soft brand-tinted tile, the service name, one or two sentences,
an optional "From £45" price and an optional "Learn more" link (screen readers hear "Learn more about Wedding cakes",
not a row of identical links). Icons are drawn inline as SVG from a built-in set of 20 (scissors, cake, home, truck,
leaf, shield...), picked from the service name when not given, or the cards can show 01, 02, 03 instead. Cards sit
three across on a laptop and stack on a phone, the whole card lifts gently on hover (not when reduced motion is on),
an optional button under the grid leads to booking or contact, and every colour pair passes WCAG AA. No JavaScript.
Saves services.html and services-preview.html in Kinetic Web Designs/<name>/web.
"""

import html
import re

import memory
from config import Settings
from design_contrast import AA, UI, colour, fix, ratio
from design_extract import FOLDER
from design_palette import on
from design_social import mix

NAMES = {"make_services_section"}
MIN_ITEMS, MAX_ITEMS = 2, 9
LINK = re.compile(r"^(https://[^\s\"'<>]+|/[^\s\"'<>]*|#[\w-]*|mailto:[^\s\"'<>]+|tel:[\d+ ()-]+)$")
SIGNS = {"GBP": "£", "EUR": "€", "USD": "$", "ZAR": "R", "AUD": "A$", "CAD": "C$", "NZD": "NZ$"}

# 24x24 line icons, drawn with stroke="currentColor" so they take the brand colour.
ICONS = {
    "check": '<path d="M5 12l5 5L20 7"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    "home": '<path d="M3 11l9-7 9 7"/><path d="M5 10v10h14V10"/><path d="M10 20v-6h4v6"/>',
    "heart": '<path d="M12 20s-7-4.5-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.5-7 10-7 10z"/>',
    "star": '<path d="M12 3l2.8 5.8 6.2.8-4.5 4.4 1.1 6.2L12 17.2l-5.6 3 1.1-6.2L3 9.6l6.2-.8z"/>',
    "truck": '<path d="M3 6h11v10H3z"/><path d="M14 10h4l3 3v3h-7"/><circle cx="7" cy="18" r="2"/>'
             '<circle cx="17" cy="18" r="2"/>',
    "shield": '<path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"/><path d="M9 12l2 2 4-4"/>',
    "sparkle": '<path d="M12 3l2 6 6 2-6 2-2 6-2-6-6-2 6-2z"/>',
    "leaf": '<path d="M5 19C5 11 11 5 20 5c0 9-6 15-14 15"/><path d="M5 19l8-8"/>',
    "calendar": '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/>',
    "tag": '<path d="M3 12V4h8l10 10-8 8z"/><circle cx="7.5" cy="7.5" r="1.5"/>',
    "scissors": '<circle cx="6" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><path d="M8.5 7.5L20 18M8.5 16.5L20 6"/>',
    "chat": '<path d="M4 5h16v11H9l-5 4z"/>',
    "pin": '<path d="M12 21s-7-6-7-11a7 7 0 0 1 14 0c0 5-7 11-7 11z"/><circle cx="12" cy="10" r="2.5"/>',
    "bag": '<path d="M5 8h14l-1 13H6z"/><path d="M9 8V6a3 3 0 0 1 6 0v2"/>',
    "camera": '<rect x="3" y="7" width="18" height="13" rx="2"/><path d="M8 7l2-3h4l2 3"/>'
              '<circle cx="12" cy="13.5" r="3.5"/>',
    "gift": '<rect x="3" y="8" width="18" height="4"/><path d="M5 12v9h14v-9M12 8v13"/>'
            '<path d="M12 8C10 4 6 4 6 6.5S12 8 12 8zm0 0c2-4 6-4 6-1.5S12 8 12 8z"/>',
    "cake": '<path d="M4 21h16v-8H4z"/><path d="M4 16c2 1.5 4 1.5 6 0s4-1.5 6 0 4 1.5 4 0"/><path d="M12 13V9"/>'
            '<path d="M12 6.5c-.8 0-1.5-.6-1.5-1.5S12 3 12 3s1.5 1.1 1.5 2-.7 1.5-1.5 1.5z"/>',
    "book": '<path d="M4 5h6a2 2 0 0 1 2 2v13a2 2 0 0 0-2-2H4z"/>'
            '<path d="M20 5h-6a2 2 0 0 0-2 2v13a2 2 0 0 1 2-2h6z"/>',
    "brush": '<path d="M14 4l6 6-8 8-6-6z"/><path d="M6 12l-2 6 2 2 6-2"/>',
}
GUESS = [
    (("cake", "bake", "birthday", "pastr", "dessert", "cater", "food", "meal", "cook"), "cake"),
    (("class", "lesson", "course", "train", "learn", "tutor", "school", "workshop"), "book"),
    (("cut", "hair", "barber", "trim", "fade", "groom"), "scissors"),
    (("deliver", "shipping", "courier", "removal", "moving", "van"), "truck"),
    (("clean", "valet", "polish", "shine", "detail"), "sparkle"),
    (("garden", "lawn", "plant", "organic", "landscap", "tree", "eco"), "leaf"),
    (("insur", "secur", "guarant", "warrant", "safe", "protect", "certif"), "shield"),
    (("book", "event", "appointment", "wedding", "party", "plan"), "calendar"),
    (("home", "house", "build", "roof", "extension", "kitchen", "bathroom", "property"), "home"),
    (("paint", "decor", "design", "brand", "nail", "makeup"), "brush"),
    (("photo", "video", "film", "shoot"), "camera"),
    (("gift", "voucher", "present"), "gift"),
    (("shop", "retail", "store", "product", "order"), "bag"),
    (("price", "sale", "offer", "deal", "discount"), "tag"),
    (("consult", "advice", "coach", "support", "chat", "talk", "therapy"), "chat"),
    (("visit", "local", "area", "location", "mobile"), "pin"),
    (("emergency", "24", "fast", "same day", "hour", "quick"), "clock"),
    (("care", "massage", "wellness", "health", "love", "beauty"), "heart"),
    (("premium", "luxury", "vip", "best", "signature"), "star"),
]


def guess(title: str) -> str:
    low = title.lower()
    for words, icon in GUESS:
        if any(w in low for w in words):
            return icon
    return "check"


def safe_link(url: str, what: str) -> str:
    url = url.strip()
    if LINK.match(url):
        return url
    raise ValueError(f"The '{what}' link '{url[:60]}' isn't one I can use; give https://..., /page, #section, "
                     "mailto: or tel:.")


def svg(icon: str) -> str:
    return (f'<svg viewBox="0 0 24 24" width="26" height="26" fill="none" stroke="currentColor" stroke-width="1.8" '
            f'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{ICONS[icon]}</svg>')


def card(i: int, s: dict, numbers: bool) -> str:
    e = html.escape
    mark = f'<span class="sv-num">{i + 1:02d}</span>' if numbers else svg(s["icon"])
    price = f'\n    <p class="sv-price">{e(s["price"])}</p>' if s["price"] else ""
    more = (f'\n    <a class="sv-more" href="{e(s["url"])}">Learn more<span class="sv-sr"> about {e(s["title"])}</span>'
            f'<span aria-hidden="true"> →</span></a>' if s["url"] else "")
    return (f'  <li class="sv-card">\n    <span class="sv-icon">{mark}</span>\n    <h3>{e(s["title"])}</h3>\n'
            f'    <p>{e(s["text"])}</p>{price}{more}\n  </li>')


def block(d: dict) -> str:
    e = html.escape
    brand = d["brand"]
    button = brand if ratio(on(brand), brand) >= AA else fix(brand, on(brand), AA)
    tint = "#%02x%02x%02x" % mix(brand, "#ffffff", 0.88)
    accent = brand if ratio(brand, "#ffffff") >= AA else fix(brand, "#ffffff", AA)
    icon = brand if ratio(brand, tint) >= UI else fix(brand, tint, UI)
    cards = "\n".join(card(i, s, d["numbers"]) for i, s in enumerate(d["services"]))
    intro = f'\n  <p class="sv-intro">{e(d["intro"])}</p>' if d["intro"] else ""
    cta = (f'\n  <p class="sv-cta"><a href="{e(d["link"])}">{e(d["button"])}</a></p>' if d["button"] else "")
    cols = 2 if len(d["services"]) in (2, 4) else 3
    return f"""<!-- Services for {e(d["name"])}: paste this block where "What we do" should show. -->
<section class="services" aria-labelledby="sv-title"
         style="--sv-brand:{button};--sv-on:{on(button)};--sv-accent:{accent};--sv-tint:{tint};--sv-icon:{icon}">
  <style>
    .services {{ font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; color: #18181b;
                max-width: {"40" if cols == 2 else "60"}rem; margin: 0 auto; padding: 0 1rem; }}
    .services h2 {{ text-align: center; font-size: clamp(1.75rem, 4.5vw, 2.5rem); margin: 0 0 .5rem;
                   text-wrap: balance; }}
    .sv-intro {{ text-align: center; color: #52525b; margin: 0 auto 2rem; max-width: 40rem; line-height: 1.6; }}
    .sv-grid {{ list-style: none; margin: 0; padding: 0; display: grid; gap: 1.25rem;
               grid-template-columns: repeat(auto-fit, minmax(min(100%, 17rem), 1fr)); }}
    .sv-card {{ position: relative; display: flex; flex-direction: column; gap: .6rem; padding: 1.5rem;
               background: #fff; border: 1px solid #e4e4e7; border-radius: 1.25rem;
               box-shadow: 0 6px 20px rgb(0 0 0 / .05); }}
    .sv-icon {{ display: grid; place-items: center; width: 3rem; height: 3rem; border-radius: .9rem;
               background: var(--sv-tint); color: var(--sv-icon); }}
    .sv-num {{ font-weight: 800; font-size: 1.05rem; color: var(--sv-accent); }}
    .sv-card h3 {{ margin: .4rem 0 0; font-size: 1.2rem; }}
    .sv-card p {{ margin: 0; color: #3f3f46; line-height: 1.6; }}
    .sv-card .sv-price {{ color: #18181b; font-weight: 700; }}
    .sv-more {{ margin-top: auto; padding-top: .4rem; display: inline-flex; align-items: center; min-height: 44px;
               color: var(--sv-accent); font-weight: 700; text-decoration: none; }}
    .sv-more::after {{ content: ""; position: absolute; inset: 0; border-radius: inherit; }}
    .sv-more:hover {{ text-decoration: underline; text-underline-offset: 3px; }}
    .sv-card:has(.sv-more:focus-visible) {{ outline: 3px solid var(--sv-accent); outline-offset: 3px; }}
    .sv-more:focus-visible {{ outline: none; }}
    .sv-sr {{ position: absolute; width: 1px; height: 1px; overflow: hidden; clip-path: inset(50%);
             white-space: nowrap; }}
    .sv-cta {{ text-align: center; margin: 2rem 0 0; }}
    .sv-cta a {{ box-sizing: border-box; display: inline-flex; align-items: center; justify-content: center;
                min-height: 52px; padding: .8rem 1.6rem; border-radius: .9rem; background: var(--sv-brand);
                color: var(--sv-on); font-weight: 700; text-decoration: none; }}
    .sv-cta a:focus-visible {{ outline: 3px solid var(--sv-accent); outline-offset: 3px; }}
    @media (prefers-reduced-motion: no-preference) {{
      .sv-card {{ transition: transform .2s ease, box-shadow .2s ease; }}
      .sv-card:has(.sv-more):hover {{ transform: translateY(-3px); box-shadow: 0 14px 32px rgb(0 0 0 / .09); }}
    }}
  </style>
  <h2 id="sv-title">{e(d["title"])}</h2>{intro}
  <ul class="sv-grid" role="list">
{cards}
  </ul>{cta}
</section>
"""


def price_text(raw, currency: str) -> str:
    if raw in (None, ""):
        return ""
    if isinstance(raw, (int, float)) and not isinstance(raw, bool):
        if raw < 0:
            raise ValueError("Prices can't be below zero.")
        amount = f"{raw:,.2f}".removesuffix(".00")
        return f"From {SIGNS[currency]}{amount}"
    text = " ".join(str(raw).split())
    if len(text) > 30:
        raise ValueError("Keep each price short, e.g. 'From £45' or '£30 an hour'.")
    return text


def run(settings: Settings, args: dict) -> str:
    clean = lambda v: " ".join(str(v or "").split())  # noqa: E731
    name = clean(args.get("name"))
    if not name:
        raise ValueError("Give the business name for the services section.")
    brand = colour(args.get("colour") or "")
    currency = clean(args.get("currency")).upper() or "GBP"
    if currency not in SIGNS:
        raise ValueError(f"Currency can be {', '.join(SIGNS)}.")
    raw = args.get("services") or []
    if not isinstance(raw, list) or not MIN_ITEMS <= len(raw) <= MAX_ITEMS:
        raise ValueError(f"Give {MIN_ITEMS} to {MAX_ITEMS} services (3 or 6 fill the rows neatly).")
    services = []
    for item in raw:
        if not isinstance(item, dict) or not clean(item.get("title")) or not clean(item.get("text")):
            raise ValueError("Each service needs a name and a sentence or two about it.")
        title, text = clean(item["title"]), clean(item["text"])
        if len(title) > 50:
            raise ValueError(f"Keep the service name '{title[:30]}...' under 50 letters.")
        if len(text) > 260:
            raise ValueError(f"Keep the words for '{title}' under 260 letters; one or two sentences reads best.")
        icon = clean(item.get("icon")).lower() or guess(title)
        if icon not in ICONS:
            raise ValueError(f"Icons can be {', '.join(ICONS)}.")
        url = safe_link(clean(item.get("url")), title) if clean(item.get("url")) else ""
        services.append({"title": title, "text": text, "icon": icon, "url": url,
                         "price": price_text(item.get("price"), currency)})
    if len({s["title"].lower() for s in services}) != len(services):
        raise ValueError("Two services have the same name; give each its own.")
    button = clean(args.get("button"))[:30]
    d = {"name": name, "brand": brand, "services": services, "numbers": args.get("style") == "numbers",
         "title": clean(args.get("title")) or "What we do", "intro": clean(args.get("intro"))[:240],
         "button": button, "link": safe_link(clean(args.get("link")) or "#contact", "button") if button else ""}
    code = block(d)
    preview = (f"<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n<meta name=\"viewport\" "
               f"content=\"width=device-width, initial-scale=1\">\n<title>{html.escape(name)} | Services</title>\n"
               "</head>\n<body style=\"margin:0;padding:56px 0;background:#fafafa\">\n" + code + "</body>\n</html>\n")
    (memory.root(settings) / FOLDER).mkdir(parents=True, exist_ok=True)
    path = memory.folder(settings, f"{FOLDER}/{memory.safe_name(name, 'folder name')}/web", create=True)
    (path / "services.html").write_text(code, encoding="utf-8")
    (path / "services-preview.html").write_text(preview, encoding="utf-8")
    where = path.relative_to(memory.root(settings)).as_posix()
    tips = []
    if len(services) in (5, 7, 8):
        tips.append(f"{len(services)} cards leave a gap on the last row; 3, 6 or 9 fill it neatly.")
    if not button:
        tips.append("Add a button (e.g. 'Book a visit') so people can act right after reading.")
    icons = "" if d["numbers"] else " Icons: " + ", ".join(f"{s['title']} = {s['icon']}" for s in services) + "."
    return (f"Made a services section for {name} with {len(services)} services in {where}: services.html to paste "
            f"into the page and services-preview.html to check it.{icons} " + " ".join(tips)).strip()


def tool_definitions() -> list[dict]:
    return [{
        "name": "make_services_section",
        "description": "Make a paste-in 'What we do' services section for a website in the brand colour: heading, "
                       "intro and 2-9 cards, each with a line icon (picked from the name, or 01/02/03 numbers), the "
                       "service, a sentence or two, optional 'From £45' price and 'Learn more' link, plus an "
                       "optional button under the grid. Stacks on phones, AA contrast, no JavaScript. Saves "
                       "services.html and a preview in Kinetic Web Designs/<name>/web. Answer in plain words.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Business name (the folder)."},
                "colour": {"type": "string", "description": "Brand colour, e.g. '#c2410c'."},
                "title": {"type": "string", "description": "Heading (default 'What we do')."},
                "intro": {"type": "string"},
                "services": {"type": "array", "description": "2-9 services, most popular first.", "items": {
                    "type": "object", "properties": {
                        "title": {"type": "string"}, "text": {"type": "string"},
                        "price": {"type": ["number", "string"], "description": "45 -> 'From £45', or own words."},
                        "url": {"type": "string", "description": "Optional page for 'Learn more'."},
                        "icon": {"type": "string", "enum": list(ICONS)}},
                    "required": ["title", "text"]}},
                "style": {"type": "string", "enum": ["icons", "numbers"], "description": "Default icons."},
                "currency": {"type": "string", "enum": list(SIGNS), "description": "Default GBP."},
                "button": {"type": "string", "description": "Optional button under the cards, e.g. 'Book now'."},
                "link": {"type": "string", "description": "Button link (default #contact)."},
            },
            "required": ["name", "colour", "services"],
            "additionalProperties": False,
        },
    }]


async def run_tool(name: str, args: dict, settings: Settings, http=None) -> str:
    try:
        return run(settings, args)
    except (TypeError, ValueError) as e:
        return str(e)
