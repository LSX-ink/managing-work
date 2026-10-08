"""Kinetic Web Designs sales: your prices and business details, website quotes, free home-page mock-ups to win a
client over, and first-contact outreach drafts.

quote: builds a quote for a website package (starter, business or shop) with add-ons and a monthly care plan from your
own prices (kinetic-prices.json; sensible UK freelance defaults until you set yours). If the client is a prospect Alfred
audited, the quote lists what the new site fixes. Saved as a printable HTML page in Kinetic Web Designs/Clients/<client>.

mockup: a one-page, phone-friendly concept home page for the business, in colours that suit its trade or in a design
system saved by extract_design_system (style_from). Saved in Kinetic Web Designs/Mockups/<business>/index.html. It uses
no photos or logos from the business, so it is safe to show them as a concept.

outreach: a short first message (email, letter, phone call, walk-in or social DM) built from the audit. Drafts only:
nothing is ever sent. UK rules on unsolicited marketing email (PECR) are summarised in the note it adds.
"""

import json
import re
from datetime import timedelta
from html import escape

import kinetic_store as st
import memory
import screen
from config import Settings

NAMES = {"web_design_sales"}
ACTIONS = ["prices", "set_price", "my_details", "quote", "quotes", "quote_status", "mockup", "outreach"]
QUOTE_STATUSES = ["draft", "sent", "accepted", "declined"]
CHANNELS = ["email", "letter", "phone", "visit", "dm"]
DEFAULT_PRICES = {
    "packages": {
        "starter": {"name": "Starter website", "price": 395,
                    "includes": "A one-page website made for phones, contact form, tap-to-call, Google basics "
                                "(title, description, business details) and 2 rounds of changes."},
        "business": {"name": "Business website", "price": 895,
                     "includes": "Up to 5 pages made for phones, contact form, tap-to-call, Google Business Profile "
                                 "help, share previews, a fast secure (HTTPS) setup and 3 rounds of changes."},
        "shop": {"name": "Online shop", "price": 1595,
                 "includes": "Everything in the business website plus a shop with up to 20 products, card payments "
                             "set up with your own provider, delivery options and order emails."},
    },
    "addons": {
        "logo": {"name": "Logo design", "price": 150},
        "copywriting": {"name": "Copywriting (per page)", "price": 60},
        "extra_page": {"name": "Extra page", "price": 120},
        "booking": {"name": "Online booking", "price": 200},
        "seo": {"name": "Local Google setup", "price": 150},
        "photos": {"name": "Photo editing and stock images", "price": 100},
    },
    "care_plan": {"name": "Monthly care plan", "price": 35,
                  "includes": "Hosting, security updates, backups and small text changes each month."},
    "deposit_percent": 50,
    "valid_days": 30,
}
WEEKS = {"starter": "1 to 2 weeks", "business": "2 to 4 weeks", "shop": "4 to 6 weeks"}
TRADE_LOOKS = {  # (background, ink, brand, accent, heading font, body font, tagline)
    "cafe": ("#fbf6ef", "#2b211a", "#7a4a2a", "#d99a4e", "Georgia, serif", "'Segoe UI', Arial, sans-serif",
             "Fresh coffee, homemade food and a warm welcome."),
    "restaurant": ("#fdf8f3", "#1f1a17", "#8c2f1b", "#d4a64a", "Georgia, serif", "'Segoe UI', Arial, sans-serif",
                   "Seasonal food, cooked with care."),
    "hairdresser": ("#faf7f8", "#1c1a1d", "#1c1a1d", "#c58b9b", "'Didot', Georgia, serif", "'Segoe UI', Arial, sans-serif",
                    "Cuts, colour and care you'll love."),
    "beauty": ("#fbf7f6", "#2a2024", "#a05c6d", "#e3b7a0", "Georgia, serif", "'Segoe UI', Arial, sans-serif",
               "Treatments that leave you feeling your best."),
    "trade": ("#f6f8fa", "#0f1b2d", "#0b4f8a", "#f2a516", "'Segoe UI', Arial, sans-serif", "'Segoe UI', Arial, sans-serif",
              "Reliable, tidy work at a fair price. Fully insured."),
    "garage": ("#f4f5f6", "#141619", "#c1272d", "#1e2228", "'Segoe UI', Arial, sans-serif", "'Segoe UI', Arial, sans-serif",
               "Honest servicing and repairs you can trust."),
    "fitness": ("#0f1012", "#f2f2f2", "#d7ff3a", "#ffffff", "'Segoe UI', Arial, sans-serif", "'Segoe UI', Arial, sans-serif",
                "Get stronger with people who know you by name."),
    "shop": ("#fffdf9", "#1d1d1b", "#2f6b4f", "#e9b949", "Georgia, serif", "'Segoe UI', Arial, sans-serif",
             "Independent, local and hand-picked."),
    "health": ("#f5f9fa", "#13262f", "#127a8a", "#7cc4b5", "'Segoe UI', Arial, sans-serif", "'Segoe UI', Arial, sans-serif",
               "Friendly, professional care close to home."),
    "business": ("#f8f8f6", "#16181d", "#2b4c7e", "#e07a5f", "'Segoe UI', Arial, sans-serif", "'Segoe UI', Arial, sans-serif",
                 "Local, independent and here to help."),
}
TRADE_WORDS = {"barber": "hairdresser", "cafe": "cafe", "coffee": "cafe", "bakery": "cafe", "restaurant": "restaurant", "fast food": "restaurant",
               "takeaway": "restaurant", "pub": "restaurant", "bar": "restaurant", "hair": "hairdresser",
               "beauty": "beauty", "nail": "beauty", "cosmetic": "beauty", "tattoo": "beauty",
               "plumb": "trade", "electric": "trade", "build": "trade", "carpent": "trade", "roof": "trade",
               "paint": "trade", "garden": "trade", "hvac": "trade", "tile": "trade", "plaster": "trade",
               "glaz": "trade", "car": "garage", "tyre": "garage", "garage": "garage", "fitness": "fitness",
               "gym": "fitness", "sport": "fitness", "dent": "health", "physio": "health", "chiro": "health",
               "vet": "health", "florist": "shop", "butcher": "shop", "gift": "shop", "cloth": "shop",
               "boutique": "shop", "jewel": "shop", "shop": "shop", "pet": "shop", "bicycle": "shop"}
SERVICES = {
    "cafe": ["Breakfast & brunch", "Speciality coffee", "Homemade cakes", "Takeaway & catering"],
    "restaurant": ["Lunch & dinner", "Private dining", "Takeaway", "Gift vouchers"],
    "hairdresser": ["Cuts & styling", "Colour & highlights", "Men's grooming", "Wedding hair"],
    "beauty": ["Facials", "Nails", "Lashes & brows", "Gift vouchers"],
    "trade": ["Free quotes", "Repairs", "New installations", "Emergency call-outs"],
    "garage": ["MOT & servicing", "Repairs", "Tyres", "Diagnostics"],
    "fitness": ["Classes", "Personal training", "Open gym", "Memberships"],
    "shop": ["New in", "Gifts", "Local favourites", "Click & collect"],
    "health": ["Appointments", "New patients", "Treatments", "Advice"],
    "business": ["What we do", "How we work", "Prices", "Get in touch"],
}


# ---- prices and details ------------------------------------------------------------

def prices(settings: Settings) -> dict:
    saved = st.load(settings, st.PRICES, {})
    out = json.loads(json.dumps(DEFAULT_PRICES))
    for group in ("packages", "addons"):
        for key, row in (saved.get(group) or {}).items():
            if key in out[group] and isinstance(row, dict) and isinstance(row.get("price"), (int, float)):
                out[group][key]["price"] = row["price"]
    for key in ("deposit_percent", "valid_days"):
        if isinstance(saved.get(key), (int, float)):
            out[key] = saved[key]
    if isinstance((saved.get("care_plan") or {}).get("price"), (int, float)):
        out["care_plan"]["price"] = saved["care_plan"]["price"]
    return out


def show_prices(settings: Settings, args: dict, prefix: str = "") -> screen.Shown:
    p = prices(settings)
    rows = [[v["name"], st.gbp(v["price"]), v["includes"]] for v in p["packages"].values()]
    rows += [[v["name"], st.gbp(v["price"]), "add-on"] for v in p["addons"].values()]
    rows.append([p["care_plan"]["name"], st.gbp(p["care_plan"]["price"]) + "/month", p["care_plan"]["includes"]])
    custom = " These are starting prices; say \"set my business website price to 950\" to use your own." \
        if not st.load(settings, st.PRICES, {}) else ""
    text = (f"{prefix} Your website prices: starter {st.gbp(p['packages']['starter']['price'])}, business "
            f"{st.gbp(p['packages']['business']['price'])}, shop {st.gbp(p['packages']['shop']['price'])}, care plan "
            f"{st.gbp(p['care_plan']['price'])} a month, {st.num(p['deposit_percent'])}% deposit.{custom}").strip()
    return st.table(text, "Kinetic Web Designs prices", ["Item", "Price", "Includes"], rows)


def set_price(settings: Settings, args: dict) -> screen.Shown:
    item = str(args.get("item") or "").strip().lower().replace(" ", "_")
    saved = st.load(settings, st.PRICES, {})
    p = prices(settings)
    if item in ("deposit", "deposit_percent"):
        saved["deposit_percent"] = st.number(args.get("price"), "deposit percent", True, 100)
    elif item in ("valid_days", "valid"):
        saved["valid_days"] = int(st.number(args.get("price"), "number of days", False, 365))
    elif item in ("care", "care_plan", "monthly"):
        saved["care_plan"] = {"price": st.number(args.get("price"), "price")}
    else:
        item = {"business_website": "business", "starter_website": "starter", "online_shop": "shop",
                "logo_design": "logo", "page": "extra_page"}.get(item, item)
        group = "packages" if item in p["packages"] else "addons" if item in p["addons"] else ""
        if not group:
            raise ValueError("Which price? " + ", ".join(list(p["packages"]) + list(p["addons"])) +
                             ", care_plan or deposit.")
        saved.setdefault(group, {})[item] = {"price": st.number(args.get("price"), "price")}
    st.save(settings, st.PRICES, saved)
    return show_prices(settings, {}, "Saved.")


DETAILS = ["name", "owner", "email", "phone", "website", "address", "bank_name", "sort_code", "account_number",
           "vat_number"]


def my_details(settings: Settings, args: dict) -> str:
    me = st.load(settings, st.BUSINESS, {})
    changed = []
    for key in DETAILS:
        if args.get(key) is not None:
            me[key] = st.clean(args[key], 160)
            changed.append(key.replace("_", " "))
    if changed:
        st.save(settings, st.BUSINESS, me)
    full = st.business(settings)
    missing = [k.replace("_", " ") for k in ("owner", "email", "phone", "sort_code", "account_number") if not full[k]]
    text = f"Saved your {', '.join(changed)}." if changed else \
        f"Your business is {full['name']}" + (f", run by {full['owner']}" if full["owner"] else "") + "."
    if missing:
        text += " Still missing for quotes and invoices: " + ", ".join(missing) + "."
    return text + " These details stay on this PC and only appear on documents you send yourself."


# ---- quotes ------------------------------------------------------------------------

def client_and_prospect(settings: Settings, args: dict) -> tuple[str, dict | None]:
    who = args.get("client") or args.get("business")
    p = st.find_prospect(st.rows_of(settings, st.PROSPECTS), who)
    return (p["name"] if p else st.need(who, "client", 80)), p


def quote_lines(settings: Settings, args: dict) -> tuple[list[tuple[str, int, float]], float, str]:
    """[(description, qty, unit price)], monthly care price (0 if none) and the package key."""
    p = prices(settings)
    package = str(args.get("package") or "business").lower()
    package = {"one page": "starter", "one-page": "starter", "basic": "starter", "website": "business",
               "standard": "business", "ecommerce": "shop", "e-commerce": "shop", "store": "shop"}.get(package, package)
    if package not in p["packages"]:
        raise ValueError("Which package? starter, business or shop.")
    pk = p["packages"][package]
    lines = [(f"{pk['name']}: {pk['includes']}", 1, float(pk["price"]))]
    for raw in args.get("addons") or []:
        key = str(raw).strip().lower().replace(" ", "_")
        key = {"logo_design": "logo", "copy": "copywriting", "pages": "extra_page", "extra_pages": "extra_page",
               "google": "seo", "bookings": "booking", "photo": "photos"}.get(key, key)
        if key not in p["addons"]:
            raise ValueError("Add-ons are " + ", ".join(p["addons"]) + ".")
        qty = 1
        if key == "extra_page":
            qty = max(1, int(args.get("extra_pages") or 1))
        elif key == "copywriting":
            qty = max(1, int(args.get("pages") or {"starter": 1, "business": 5, "shop": 5}[package]))
        lines.append((p["addons"][key]["name"], qty, float(p["addons"][key]["price"])))
    for extra in args.get("custom_items") or []:
        if isinstance(extra, dict) and extra.get("description"):
            lines.append((st.clean(extra["description"], 160), 1, st.number(extra.get("price"), "item price")))
    care = float(p["care_plan"]["price"]) if args.get("care_plan", True) else 0.0
    return lines, care, package


def quote(settings: Settings, args: dict) -> screen.Shown:
    name, prospect = client_and_prospect(settings, args)
    lines, care, package = quote_lines(settings, args)
    p = prices(settings)
    subtotal = sum(q * u for _, q, u in lines)
    discount = st.number(args.get("discount"), "discount", True, subtotal) if args.get("discount") else 0.0
    total = round(subtotal - discount, 2)
    deposit = round(total * p["deposit_percent"] / 100, 2)
    rows = st.rows_of(settings, st.QUOTES)
    qid = st.next_id(rows)
    number = f"Q-{qid:04d}"
    valid = st.today() + timedelta(days=int(p["valid_days"]))
    fixes = [x["problem"] for x in ((prospect or {}).get("audit") or {}).get("problems", [])][:6]
    if prospect and not prospect.get("website"):
        fixes = ["You don't have a website yet, so customers who search for you find competitors instead."]
    body = [f"<h2>Quote {number} for {escape(name)}</h2>",
            '<div class="meta">' + "".join(f"<div><b>{k}</b>{escape(v)}</div>" for k, v in (
                ("Quote number", number), ("Date", st.short(st.today())), ("Valid until", st.short(valid)),
                ("Time to build", WEEKS[package]))) + "</div>"]
    if args.get("notes"):
        body.append(f"<p>{escape(st.clean(args['notes'], 600))}</p>")
    if fixes:
        body += ["<h2>What your new website fixes</h2>", "<ul>" + "".join(f"<li>{escape(x)}</li>" for x in fixes) + "</ul>"]
    table = ["<table><tr><th>Item</th><th class=n>Qty</th><th class=n>Price</th><th class=n>Total</th></tr>"]
    table += [f"<tr><td>{escape(d)}</td><td class=n>{q}</td><td class=n>{st.gbp(u)}</td><td class=n>{st.gbp(q * u)}</td></tr>"
              for d, q, u in lines]
    if discount:
        table.append(f"<tr><td>Discount</td><td></td><td></td><td class=n>-{st.gbp(discount)}</td></tr>")
    table.append(f"<tr class=total><td>Total</td><td></td><td></td><td class=n>{st.gbp(total)}</td></tr></table>")
    body += ["<h2>Price</h2>", "".join(table)]
    if care:
        body.append(f"<p>Optional {escape(p['care_plan']['name'].lower())}: {st.gbp(care)} a month. "
                    f"{escape(p['care_plan']['includes'])} Cancel any time with a month's notice.</p>")
    vat = st.business(settings)["vat_number"]
    body += ["<h2>How it works</h2>", "<ol>",
             f"<li>You say yes, and I send an invoice for the {st.num(p['deposit_percent'])}% deposit "
             f"({st.gbp(deposit)}) to book your start date.</li>" if deposit else "<li>You say yes and we book a start date.</li>",
             "<li>A short call about your business, your customers and the look you like.</li>",
             "<li>I design and build the site, and you review it on your own phone.</li>",
             f"<li>Once you're happy, it goes live and the rest ({st.gbp(total - deposit)}) is invoiced.</li>", "</ol>",
             "<h2>The small print</h2>", "<ul>",
             "<li>You own the finished website and its content once the final invoice is paid.</li>",
             "<li>Domain name and any paid plugins or shop fees are paid by you, at cost.</li>",
             "<li>Changes beyond the included rounds are charged at an agreed hourly rate.</li>",
             f"<li>Prices {'exclude VAT' if vat else 'have no VAT to add'}.</li>", "</ul>",
             f"<footer>Quote {number} · valid until {st.long_date(valid)}</footer>"]
    html = st.doc_html(settings, f"Quote {number} for {name}", "\n".join(body))
    path = st.write(settings, ("Clients", name), f"Quote {number}.html", html)
    rows.append({"id": qid, "number": number, "client": name, "package": package, "total": total, "deposit": deposit,
                 "care": care, "date": st.today().isoformat(), "valid_until": valid.isoformat(), "status": "draft",
                 "lines": [[d, q, u] for d, q, u in lines], "discount": discount, "file": st.where(settings, path)})
    st.save(settings, st.QUOTES, rows)
    text = (f"Quote {number} for {name}: {st.gbp(total)}" + (f", with a {st.gbp(deposit)} deposit" if deposit else "")
            + (f" and an optional {st.gbp(care)} a month care plan" if care else "") +
            f". Saved in {st.where(settings, path)}; open it and print to PDF to send it. {st.NOT_SENT}")
    return st.file_shown(settings, path, text, [
        {"label": "Mark as sent", "say": f"Mark quote {number} as sent."},
        {"label": "Deposit invoice", "say": f"Make the deposit invoice for quote {number}."}])


def find_quote(rows: list[dict], which) -> dict:
    key = str(which or "").strip().upper()
    if not key:
        raise ValueError("Which quote? Give its number, e.g. Q-0001, or the client.")
    if key.isdigit():
        key = f"Q-{int(key):04d}"
    hit = next((r for r in rows if r["number"] == key), None)
    if not hit:
        hits = [r for r in rows if key.lower() in r["client"].lower()]
        hit = hits[-1] if hits else None
    if not hit:
        raise ValueError("I can't find that quote.")
    return hit


def quotes(settings: Settings, args: dict) -> screen.Shown:
    rows = st.rows_of(settings, st.QUOTES)
    if not rows:
        raise ValueError("No quotes yet. Ask me to quote a client for a website.")
    open_ = [r for r in rows if r["status"] in ("draft", "sent")]
    won = [r for r in rows if r["status"] == "accepted"]
    decided = len(won) + sum(1 for r in rows if r["status"] == "declined")
    text = (f"{len(rows)} quote{'s' if len(rows) != 1 else ''}: {len(open_)} open worth "
            f"{st.gbp(sum(r['total'] for r in open_))}, {len(won)} accepted worth {st.gbp(sum(r['total'] for r in won))}.")
    if decided:
        text += f" You win {round(100 * len(won) / decided)}% of the ones that got an answer."
    table = [[r["number"], r["client"], r["package"], st.gbp(r["total"]), r["status"], r["date"]] for r in rows[::-1][:60]]
    return st.table(text, "Website quotes", ["Quote", "Client", "Package", "Total", "Status", "Date"], table)


def quote_status(settings: Settings, args: dict) -> str:
    rows = st.rows_of(settings, st.QUOTES)
    q = find_quote(rows, args.get("quote"))
    status = args.get("status")
    if status not in QUOTE_STATUSES:
        raise ValueError("Mark the quote as " + ", ".join(QUOTE_STATUSES) + ".")
    q["status"] = status
    st.save(settings, st.QUOTES, rows)
    prospects = st.rows_of(settings, st.PROSPECTS)
    p = st.find_prospect(prospects, q["client"])
    if p and p["name"] == q["client"]:
        p["status"] = {"sent": "contacted", "accepted": "client", "declined": "not interested"}.get(status, p["status"])
        st.save(settings, st.PROSPECTS, prospects)
    if status == "accepted":
        return (f"Brilliant, {q['client']} accepted quote {q['number']} for {st.gbp(q['total'])}. Say \"make the "
                f"deposit invoice for {q['number']}\" when you're ready.")
    return f"Quote {q['number']} is now {status}."


# ---- mock-ups ----------------------------------------------------------------------

def trade_of(text: str) -> str:
    t = str(text or "").lower()
    return next((v for k, v in TRADE_WORDS.items() if k in t), "business")


def look_from(settings: Settings, style_from: str) -> dict | None:
    """Colours and fonts from a design system saved by extract_design_system, if there is one."""
    if not style_from:
        return None
    path = memory.root(settings) / st.FOLDER / memory.safe_name(style_from, "folder name") / "tokens.json"
    try:
        t = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise ValueError(f"I can't find a saved design system called {style_from}. Extract one first with "
                         "'extract the design system from <site>'.") from None
    colour = {k: v.get("$value") for k, v in (t.get("color") or {}).items() if isinstance(v, dict) and "$value" in v}
    fonts = [v.get("$value") for v in (t.get("fontFamily") or {}).values() if isinstance(v, dict)]
    stack = lambda f: ", ".join(f"'{x}'" if " " in x else x for x in f) if isinstance(f, list) else ""  # noqa: E731
    return {"bg": colour.get("background"), "ink": colour.get("text"), "brand": colour.get("brand"),
            "accent": colour.get("accent"), "head": stack(fonts[0]) if fonts else "", "body": stack(fonts[-1]) if fonts else ""}


def safe_css(value: str, fallback: str) -> str:
    value = str(value or "")
    return value if re.fullmatch(r"#[0-9a-fA-F]{3,8}|[\w\s'\",.-]{1,200}", value) and value.strip() else fallback


def mockup_html(name: str, trade: str, tagline: str, services: list[str], phone: str, town: str, look: dict | None,
                maker: str) -> str:
    bg, ink, brand, accent, head, body, default_tag = TRADE_LOOKS[trade]
    if look:
        bg, ink, brand, accent = (safe_css(look.get(k), d) for k, d in
                                  (("bg", bg), ("ink", ink), ("brand", brand), ("accent", accent)))
        head, body = safe_css(look.get("head"), head), safe_css(look.get("body"), body)
    tagline = tagline or default_tag
    e = escape
    tel = re.sub(r"[^\d+]", "", phone)
    call = f'<a class="btn" href="tel:{e(tel)}">Call {e(phone)}</a>' if tel else '<a class="btn" href="#contact">Get in touch</a>'
    cards = "".join(f'<div class="card"><span class="dot"></span><h3>{e(s)}</h3><p>Tell customers what makes your '
                    f'{e(s.lower())} worth choosing, in a sentence or two.</p></div>' for s in services[:6])
    where_ = f" in {e(town)}" if town else ""
    css = f""":root{{--bg:{bg};--ink:{ink};--brand:{brand};--accent:{accent};--head:{head};--body:{body}}}
*{{box-sizing:border-box;margin:0}}body{{background:var(--bg);color:var(--ink);font-family:var(--body);line-height:1.6}}
a{{color:inherit}}.wrap{{max-width:1080px;margin:0 auto;padding:0 20px}}
nav{{display:flex;justify-content:space-between;align-items:center;padding:18px 0;gap:12px}}
.logo{{font-family:var(--head);font-weight:700;font-size:1.25rem;letter-spacing:.01em}}
nav a.small{{text-decoration:none;font-weight:600;border-bottom:2px solid var(--accent)}}
.hero{{padding:72px 0 88px;display:grid;gap:28px}}
.hero h1{{font-family:var(--head);font-size:clamp(2.2rem,6vw,4.2rem);line-height:1.05;max-width:14ch}}
.hero p{{font-size:1.2rem;max-width:44ch;opacity:.85}}
.btn{{display:inline-block;background:var(--brand);color:var(--bg);padding:14px 26px;border-radius:999px;
text-decoration:none;font-weight:700;transition:transform .2s cubic-bezier(.2,.8,.2,1)}}.btn:hover{{transform:translateY(-2px)}}
.btn.ghost{{background:transparent;color:var(--ink);border:2px solid var(--ink);margin-left:10px}}
.band{{background:var(--brand);color:var(--bg);padding:14px 0;font-weight:600;text-align:center}}
section{{padding:72px 0}}h2{{font-family:var(--head);font-size:clamp(1.6rem,4vw,2.4rem);margin-bottom:28px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:18px}}
.card{{background:color-mix(in srgb,var(--bg) 88%,var(--ink));border-radius:18px;padding:24px}}
.card h3{{font-family:var(--head);margin:10px 0 6px}}.dot{{display:block;width:12px;height:12px;border-radius:50%;background:var(--accent)}}
.quote{{font-family:var(--head);font-size:1.4rem;max-width:36ch}}.quote small{{display:block;font-family:var(--body);font-size:.95rem;opacity:.7;margin-top:10px}}
#contact{{background:var(--ink);color:var(--bg);border-radius:28px;padding:48px 28px;margin:0 0 72px}}
#contact .btn{{background:var(--accent);color:var(--ink)}}footer{{padding:28px 0;font-size:.85rem;opacity:.65}}
@media (max-width:600px){{.btn.ghost{{margin:12px 0 0}}.hero{{padding:48px 0 56px}}}}"""
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(name)}{where_} | Concept home page</title>
<meta name="description" content="{e(tagline)}">
<style>{css}</style></head><body>
<div class="wrap"><nav><span class="logo">{e(name)}</span><a class="small" href="#contact">Contact</a></nav>
<header class="hero"><h1>{e(tagline)}</h1><p>{e(name)} is an independent {e(trade if trade != 'business' else 'local business')}{where_}.
Swap this line for what you do best and who you do it for.</p><div>{call}<a class="btn ghost" href="#services">See what we do</a></div></header></div>
<div class="band">Open today · Friendly local service{where_}</div>
<div class="wrap"><section id="services"><h2>What we do</h2><div class="grid">{cards}</div></section>
<section><h2>What customers say</h2><p class="quote">"Space for a real review from one of your customers."<small>Your happy customer</small></p></section>
<section id="contact"><h2>Visit or get in touch</h2><p>Opening hours, address and a map go here, so people can find you in seconds.</p><br>{call}</section>
<footer>Concept home page for {e(name)} by {e(maker)}. Placeholder words only; not the live site.</footer></div>
</body></html>
"""


def mockup(settings: Settings, args: dict) -> screen.Shown:
    name, prospect = client_and_prospect(settings, args)
    p = prospect or {}
    trade = trade_of(args.get("kind") or p.get("kind") or name)
    services = [st.clean(s, 40) for s in (args.get("services") or []) if st.clean(s)] or SERVICES[trade]
    look = look_from(settings, str(args.get("style_from") or "").strip())
    html = mockup_html(name, trade, st.clean(args.get("tagline"), 90), services, st.clean(args.get("phone") or p.get("phone"), 30),
                       st.clean(args.get("town") or p.get("town"), 40), look, st.business(settings)["name"])
    path = st.write(settings, ("Mockups", name), "index.html", html, replace=True)
    style = f" in the style of {args['style_from']}" if look else f" in a {trade} look"
    return st.file_shown(settings, path, f"I made a concept home page for {name}{style}. It's in {st.where(settings, path)}; "
                         "open it on your phone and PC to check it, then show it to them as a free sample.", [
                             {"label": "Write outreach", "say": f"Write an outreach email for {name} mentioning the mock-up."},
                             {"label": "Quote them", "say": f"Quote {name} for a new website."}])


# ---- outreach ----------------------------------------------------------------------

PECR = ("UK rules: you can email a limited company at a work address without asking first, but sole traders and "
        "partnerships count as people, so for them a call, visit or letter is safer. Always say who you are and how to "
        "opt out, and stop if they ask.")


def outreach(settings: Settings, args: dict) -> screen.Shown:
    name, prospect = client_and_prospect(settings, args)
    p = prospect or {}
    me = st.business(settings)
    channel = args.get("channel") or "email"
    if channel not in CHANNELS:
        raise ValueError("Which kind of message? " + ", ".join(CHANNELS) + ".")
    contact = st.clean(args.get("contact_name"), 40)
    hello = f"Hi {contact}," if contact else "Hi there,"
    sign = me["owner"] or "[your name]"
    a = p.get("audit") or {}
    if not p.get("website"):
        hook = (f"I searched for {name} online and couldn't find a website, only {'your Facebook page' if p.get('facebook') else 'a map listing'}. "
                "That means people searching on Google tonight are finding someone else first.")
        points = ["a simple site that works on phones, with your hours, prices and a tap-to-call button",
                  "set up so you show up properly on Google and Google Maps"]
    elif a.get("grade") == "down":
        hook = f"I tried to visit your website ({st.domain(p['website'])}) and it didn't load, so customers may be giving up."
        points = ["getting a fast, secure site back up", "making sure it works on phones and shows on Google"]
    elif a.get("problems"):
        hook = f"I had a look at your website ({st.domain(p['website'])}) and spotted a few quick wins."
        points = [f"{x['problem'][0].lower() + x['problem'][1:]}: {x['why'][0].lower() + x['why'][1:]}" for x in a["problems"][:3]]
    else:
        hook = f"I'm a local web designer and I'd love to help {name} win more customers online."
        points = ["a modern, phone-friendly site", "getting found on Google"]
    offer = ("I've put together a free example of what a new home page could look like for you. No obligation; happy "
             "to send it over or show you on my phone.") if args.get("mockup", True) else \
        "I'd be happy to show you some ideas, free and with no obligation."
    bullets = "\n".join(f"- {x[0].upper() + x[1:]}" for x in points)
    opt_out = "If you'd rather not hear from me, just reply 'no thanks' and I won't contact you again."
    if channel == "email":
        subject = f"A quick idea for {name}'s website" if p.get("website") else f"Helping {name} get found online"
        body = (f"Subject: {subject}\n\n{hello}\n\n{hook}\n\nA couple of things I'd suggest:\n{bullets}\n\n{offer}\n\n"
                f"Would a 10-minute chat this week be useful?\n\nThanks,\n{sign}\n{me['name']}"
                + "".join(f"\n{x}" for x in (me["phone"], me["website"], me["address"]) if x) + f"\n\n{opt_out}")
    elif channel == "letter":
        body = (f"{me['name']}\n{me['address'] or '[your address]'}\n{st.long_date(st.today())}\n\nTo the owner, {name}\n\n"
                f"{hello.replace('Hi', 'Dear')}\n\n{hook}\n\nWhat I'd suggest:\n{bullets}\n\n{offer}\n\nYou can reach me on "
                f"{me['phone'] or '[your phone]'} or {me['email'] or '[your email]'}.\n\nKind regards,\n{sign}\n\n{opt_out}")
    elif channel == "phone":
        body = (f"Phone script for {name}{(' (' + p['phone'] + ')') if p.get('phone') else ''}\n\n"
                f"1. \"Hi, is that the owner? My name's {sign} from {me['name']}, a local web designer. Have you got two minutes?\"\n"
                f"2. If yes: \"{hook}\"\n3. \"I'd suggest:\"\n{bullets}\n4. \"{offer}\"\n"
                "5. Ask: \"Could I pop in or send it over this week?\" Agree a time and get their email.\n"
                "6. If not now: thank them, ask if you can check back in a few months, and note it.\n"
                "If they say no, thank them and don't call again.")
    elif channel == "visit":
        body = (f"Walk-in script for {name}{(', ' + p['address']) if p.get('address') else ''}\n\n"
                "Go at a quiet time (mid-morning or mid-afternoon), and bring the mock-up on your phone.\n\n"
                f"\"Hi, I'm {sign}, a web designer just round the corner. {hook} I made you a free example; can I show you "
                f"in 30 seconds?\"\n\nPoints to mention:\n{bullets}\n\nLeave your card or number and ask for the best "
                "email to send the example to. If they're busy, ask when's better.")
    else:
        body = (f"{hello} {hook} I've made a free example home page for {name} to show what it could look like. Happy to "
                f"send it over? No obligation. {sign}, {me['name']}")
    path = st.write(settings, ("Clients", name), f"Outreach {channel} {st.today().isoformat()}.md", body + "\n")
    note = PECR if channel in ("email", "dm") else "Be friendly and brief, and take no for an answer."
    return st.text_card(f"I drafted a {channel} for {name} and saved it in {st.where(settings, path)}. {st.NOT_SENT} "
                        f"Once you've sent it, tell me and I'll mark them as contacted. {note}",
                        f"Outreach: {name}", body, [
                            {"label": "Mark contacted", "say": f"Mark prospect {name} as contacted."},
                            {"label": "Make the mock-up", "say": f"Mock up a home page for {name}."}])


def tool_definitions() -> list[dict]:
    return [{
        "name": "web_design_sales",
        "description": "Kinetic Web Designs sales tools for paid website work. prices / set_price: the user's "
                       "package prices (starter, business, shop), add-ons (logo, copywriting, extra_page, booking, "
                       "seo, photos), care_plan per month and deposit percent. my_details: business name, owner, "
                       "contact and bank details used on quotes and invoices. quote: a printable website quote for a "
                       "client or saved prospect (lists what their audit found). quotes / quote_status: track quotes "
                       "(draft, sent, accepted, declined). mockup: a free concept home page for a business, optionally "
                       "in a design system saved by extract_design_system (style_from). outreach: a first message "
                       "draft (email, letter, phone script, walk-in script, dm) from the audit. Drafts only: never "
                       "send anything, and only mark a quote sent when the user says they sent it.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "client": {"type": "string", "description": "Client name, or a saved prospect's number or name."},
                "package": {"type": "string", "enum": ["starter", "business", "shop"]},
                "addons": {"type": "array", "items": {"type": "string"},
                           "description": "logo, copywriting, extra_page, booking, seo, photos."},
                "extra_pages": {"type": "integer"}, "pages": {"type": "integer", "description": "Pages of copywriting."},
                "custom_items": {"type": "array", "items": {"type": "object", "properties": {
                    "description": {"type": "string"}, "price": {"type": "number"}}}},
                "care_plan": {"type": "boolean", "description": "quote: offer the monthly care plan (default true)."},
                "discount": {"type": "number", "description": "quote: pounds off."},
                "notes": {"type": "string", "description": "quote: a personal opening line."},
                "quote": {"type": "string", "description": "Quote number like Q-0001, or the client."},
                "status": {"type": "string", "enum": QUOTE_STATUSES},
                "item": {"type": "string", "description": "set_price: starter, business, shop, an add-on, care_plan, "
                                                          "deposit (percent) or valid_days."},
                "price": {"type": "number"},
                "kind": {"type": "string", "description": "mockup: the trade, e.g. cafe, barber, plumber."},
                "tagline": {"type": "string"}, "services": {"type": "array", "items": {"type": "string"}},
                "phone": {"type": "string"}, "town": {"type": "string"},
                "style_from": {"type": "string", "description": "mockup: a folder in Kinetic Web Designs saved by "
                                                                "extract_design_system, e.g. 'stripe.com'."},
                "channel": {"type": "string", "enum": CHANNELS},
                "contact_name": {"type": "string", "description": "outreach: the owner's first name if known."},
                "mockup": {"type": "boolean", "description": "outreach: offer a free mock-up (default true)."},
                **{k: {"type": "string"} for k in DETAILS},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


def run_tool(name: str, args: dict, settings: Settings, http=None):
    handlers = {"prices": show_prices, "set_price": set_price, "my_details": my_details, "quote": quote,
                "quotes": quotes, "quote_status": quote_status, "mockup": mockup, "outreach": outreach}
    return st.dispatch(handlers, args.get("action"), settings, args, "web design sales")
