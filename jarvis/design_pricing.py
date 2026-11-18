"""Pricing tables: the "pick a plan" section on a website, with the popular plan standing out.

make_pricing_table turns 1 to 4 plans into a paste-in HTML block in the brand colour. Each plan is a card with its
name, price (and "/month" or "one-off"), a one-line who-it's-for, a tick list of what's included (up to 10, with
"not included" items shown crossed through if given) and a button. One plan can be marked "Most popular": it gets a
brand border, a badge and a filled button, which is the layout that helps people decide fastest. Cards sit side by
side on a laptop and stack on a phone with the popular plan first, prices use the right currency sign, and an
optional small print line (e.g. "Pay half to start, half when it's live") sits underneath. Buttons are real links,
every colour pair passes WCAG AA and nothing needs JavaScript. Saves pricing.html and pricing-preview.html in
Kinetic Web Designs/<name>/web.
"""

import html
import re

import memory
from config import Settings
from design_contrast import AA, colour, fix, ratio
from design_extract import FOLDER
from design_palette import on

NAMES = {"make_pricing_table"}
MAX_PLANS, MAX_FEATURES = 4, 10
SIGNS = {"GBP": "£", "USD": "$", "EUR": "€", "ZAR": "R", "AUD": "A$", "CAD": "C$", "NZD": "NZ$", "INR": "₹",
         "JPY": "¥", "NGN": "₦", "KES": "KSh "}
PERIODS = {"one-off": "one-off", "month": "/month", "year": "/year", "week": "/week", "hour": "/hour",
           "session": "/session", "night": "/night", "person": "/person"}


def money(amount, currency: str) -> str:
    if isinstance(amount, str):
        text = amount.strip()
        if not text:
            raise ValueError("Each plan needs a price.")
        if not re.fullmatch(r"[\d,]+(\.\d{1,2})?", text):
            return text  # e.g. "From £395" or "Free" or "Ask us", shown as given
        amount = float(text.replace(",", ""))
    if isinstance(amount, bool) or not isinstance(amount, (int, float)) or amount < 0:
        raise ValueError("Prices must be 0 or more.")
    shown = f"{amount:,.0f}" if float(amount).is_integer() else f"{amount:,.2f}"
    return SIGNS[currency] + shown


def safe_link(url: str) -> str:
    url = url.strip()
    if re.match(r"^(https://[^\s\"'<>]+|/[^\s\"'<>]*|#[\w-]*|mailto:[^\s\"'<>]+|tel:[\d+ ()-]+)$", url):
        return url
    raise ValueError(f"'{url[:60]}' isn't a link I can use; give https://..., /contact, #section, mailto: or tel:.")


def block(name: str, brand: str, title: str, intro: str, plans: list[dict], note: str) -> str:
    e = html.escape
    button = brand if ratio(on(brand), brand) >= AA else fix(brand, on(brand), AA)
    accent = brand if ratio(brand, "#ffffff") >= AA else fix(brand, "#ffffff", AA)
    cards = []
    for p in plans:
        feats = "".join(f'<li class="{"no" if not ok else "yes"}"><span class="sr">{"Not included: " if not ok else ""}'
                        f"</span>{e(text)}</li>" for text, ok in p["features"])
        badge = '<p class="badge">Most popular</p>' if p["popular"] else ""
        cards.append(f"""  <article class="plan{' popular' if p['popular'] else ''}" aria-labelledby="{p['id']}">
    {badge}<h3 id="{p['id']}">{e(p['name'])}</h3>
    <p class="price"><strong>{e(p['price'])}</strong>{f' <span>{e(p["period"])}</span>' if p['period'] else ''}</p>
    {f'<p class="for">{e(p["blurb"])}</p>' if p['blurb'] else ''}
    <ul>{feats}</ul>
    <a class="btn" href="{e(p['link'])}">{e(p['button'])}<span class="sr"> for {e(p['name'])}</span></a>
  </article>""")
    return f"""<!-- Pricing for {e(name)}: paste this block where the plans should show. -->
<section class="pricing" aria-labelledby="pricing-title"
         style="--p-brand:{button};--p-on:{on(button)};--p-accent:{accent}">
  <style>
    .pricing {{ font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; color: #18181b;
               max-width: 72rem; margin: 0 auto; padding: 0 1rem; }}
    .pricing > h2 {{ text-align: center; font-size: clamp(1.75rem, 4.5vw, 2.5rem); margin: 0 0 .5rem; }}
    .pricing > .intro {{ text-align: center; color: #52525b; margin: 0 auto 2rem; max-width: 40rem; }}
    .pricing .plans {{ display: grid; gap: 1.25rem; grid-template-columns: repeat(auto-fit, minmax(15rem, 1fr));
                      align-items: start; }}
    .pricing .plan {{ position: relative; background: #fff; border: 1px solid #e4e4e7; border-radius: 1.25rem;
                     padding: 1.75rem 1.5rem; display: flex; flex-direction: column; gap: .75rem; }}
    .pricing .popular {{ border: 2px solid var(--p-accent); box-shadow: 0 18px 40px rgb(0 0 0 / .1); }}
    .pricing .badge {{ position: absolute; top: 0; left: 50%; transform: translate(-50%, -50%); margin: 0;
                      background: var(--p-brand); color: var(--p-on); font-size: .8rem; font-weight: 700;
                      padding: .3rem .8rem; border-radius: 999px; white-space: nowrap; }}
    .pricing h3 {{ margin: 0; font-size: 1.15rem; }}
    .pricing .price {{ margin: 0; }}
    .pricing .price strong {{ font-size: 2.25rem; letter-spacing: -.02em; }}
    .pricing .price span {{ color: #52525b; }}
    .pricing .for {{ margin: 0; color: #52525b; }}
    .pricing ul {{ list-style: none; margin: .25rem 0 .5rem; padding: 0; display: grid; gap: .5rem; flex: 1; }}
    .pricing li {{ padding-left: 1.6rem; position: relative; line-height: 1.45; }}
    .pricing li::before {{ position: absolute; left: 0; top: 0; font-weight: 800; }}
    .pricing li.yes::before {{ content: "✓"; color: var(--p-accent); }}
    .pricing li.no {{ color: #71717a; text-decoration: line-through; }}
    .pricing li.no::before {{ content: "✕"; color: #71717a; }}
    .pricing .btn {{ display: flex; justify-content: center; align-items: center; min-height: 48px;
                    border-radius: .75rem; font-weight: 650; text-decoration: none; border: 2px solid var(--p-accent);
                    color: var(--p-accent); background: #fff; }}
    .pricing .popular .btn {{ background: var(--p-brand); color: var(--p-on); border-color: var(--p-brand); }}
    .pricing .btn:focus-visible {{ outline: 3px solid var(--p-accent); outline-offset: 3px; }}
    .pricing .note {{ text-align: center; color: #52525b; font-size: .9rem; margin: 1.5rem 0 0; }}
    .pricing .sr {{ position: absolute; width: 1px; height: 1px; overflow: hidden; clip-path: inset(50%);
                   white-space: nowrap; }}
    @media (max-width: 40rem) {{ .pricing .popular {{ order: -1; margin-top: .75rem; }} }}
  </style>
  <h2 id="pricing-title">{e(title)}</h2>
  {f'<p class="intro">{e(intro)}</p>' if intro else ''}
  <div class="plans">
{chr(10).join(cards)}
  </div>
  {f'<p class="note">{e(note)}</p>' if note else ''}
</section>
"""


def run(settings: Settings, args: dict) -> str:
    clean = lambda v: " ".join(str(v or "").split())  # noqa: E731
    name = clean(args.get("name"))
    if not name:
        raise ValueError("Give the business name for the pricing table.")
    brand = colour(args.get("colour") or "")
    currency = clean(args.get("currency")).upper() or "GBP"
    if currency not in SIGNS:
        raise ValueError(f"Currency can be {', '.join(SIGNS)}.")
    raw = args.get("plans") or []
    if not isinstance(raw, list) or not 1 <= len(raw) <= MAX_PLANS:
        raise ValueError(f"Give 1 to {MAX_PLANS} plans (3 is easiest to choose from).")
    plans, popular = [], 0
    for i, p in enumerate(raw):
        if not isinstance(p, dict) or not clean(p.get("name")):
            raise ValueError("Each plan needs a name and a price.")
        period = clean(p.get("period")).lower()
        if period and period not in PERIODS:
            raise ValueError(f"Period can be {', '.join(PERIODS)}.")
        feats = []
        for f in p.get("features") or []:
            if isinstance(f, dict):
                text, ok = clean(f.get("text")), f.get("included", True) is not False
            else:
                text, ok = clean(f), True
            if text:
                feats.append((text[:90], ok))
        if len(feats) > MAX_FEATURES:
            raise ValueError(f"Keep each plan to {MAX_FEATURES} features; people skim.")
        popular += bool(p.get("popular"))
        plans.append({"id": f"plan-{i + 1}", "name": clean(p.get("name"))[:40],
                      "price": money(p.get("price") if p.get("price") is not None else "", currency),
                      "period": PERIODS.get(period, ""), "blurb": clean(p.get("blurb"))[:120], "features": feats,
                      "button": clean(p.get("button"))[:30] or "Get started",
                      "link": safe_link(clean(p.get("link")) or "#contact"), "popular": bool(p.get("popular"))})
    if popular > 1:
        raise ValueError("Mark just one plan as most popular, or none.")
    title = clean(args.get("title")) or "Simple, honest prices"
    code = block(name, brand, title, clean(args.get("intro")), plans, clean(args.get("note")))
    preview = (f"<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n<meta name=\"viewport\" "
               f"content=\"width=device-width, initial-scale=1\">\n<title>{html.escape(name)} | Pricing</title>\n"
               "</head>\n<body style=\"margin:0;padding:56px 0;background:#fafafa\">\n" + code + "</body>\n</html>\n")
    (memory.root(settings) / FOLDER).mkdir(parents=True, exist_ok=True)
    path = memory.folder(settings, f"{FOLDER}/{memory.safe_name(name, 'folder name')}/web", create=True)
    (path / "pricing.html").write_text(code, encoding="utf-8")
    (path / "pricing-preview.html").write_text(preview, encoding="utf-8")
    where = path.relative_to(memory.root(settings)).as_posix()
    star = next((p["name"] for p in plans if p["popular"]), "")
    return (f"Made a pricing table for {name} with {len(plans)} plan{'s' if len(plans) != 1 else ''} in {where}: "
            "pricing.html to paste into the page and pricing-preview.html to check it."
            + (f" {star} is marked Most popular and shows first on phones." if star else
               " Tip: marking one plan as most popular helps people choose.")
            + " Prices are shown exactly as given, so double-check them before it goes live.")


def tool_definitions() -> list[dict]:
    return [{
        "name": "make_pricing_table",
        "description": "Make a paste-in pricing table for a website in the brand colour: 1-4 plan cards with name, "
                       "price (currency sign, /month etc.), who it's for, ticked features (and crossed-out ones), a "
                       "button link, and one optional 'Most popular' plan that stands out and shows first on phones. "
                       "No JavaScript, AA contrast. Saves pricing.html and pricing-preview.html in "
                       "Kinetic Web Designs/<name>/web. Answer in plain words.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Business name (the folder)."},
                "colour": {"type": "string", "description": "Brand colour, e.g. '#c2410c'."},
                "title": {"type": "string", "description": "Heading (default 'Simple, honest prices')."},
                "intro": {"type": "string"},
                "currency": {"type": "string", "enum": list(SIGNS), "description": "Default GBP."},
                "plans": {"type": "array", "description": "1-4 plans, cheapest first.", "items": {
                    "type": "object", "properties": {
                        "name": {"type": "string"},
                        "price": {"type": ["number", "string"], "description": "e.g. 895, or 'Ask us'."},
                        "period": {"type": "string", "enum": list(PERIODS)},
                        "blurb": {"type": "string", "description": "Who it's for, one line."},
                        "features": {"type": "array", "items": {"anyOf": [{"type": "string"}, {
                            "type": "object", "properties": {"text": {"type": "string"},
                                                             "included": {"type": "boolean"}}}]}},
                        "button": {"type": "string", "description": "Default 'Get started'."},
                        "link": {"type": "string", "description": "Default #contact."},
                        "popular": {"type": "boolean"}},
                    "required": ["name", "price"]}},
                "note": {"type": "string", "description": "Small print under the plans."},
            },
            "required": ["name", "colour", "plans"],
            "additionalProperties": False,
        },
    }]


async def run_tool(name: str, args: dict, settings: Settings, http=None) -> str:
    try:
        return run(settings, args)
    except (TypeError, ValueError) as e:
        return str(e)
