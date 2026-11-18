"""Kinetic Web Designs sales: your prices and business details, website quotes, free home-page mock-ups to win a
client over, and first-contact outreach drafts.

quote: builds a quote for a website package (starter, business or shop) with add-ons and a monthly care plan from your
own prices (kinetic-prices.json; sensible UK freelance defaults until you set yours). If the client is a prospect Alfred
audited, the quote lists what the new site fixes. Saved as a printable HTML page in Kinetic Web Designs/Clients/<client>.
Prices stay in pounds; for a client abroad the quote also shows a rough local-currency total (kinetic_world). Payment is
always half when we start building, half once everything's complete: no instalments or buy-now-pay-later.

Shopify stores: "Shopify store redesign" (£595) and "Shopify store setup" (£995) are packages like the others (set_price
changes them, the care plan and founding offer apply). The client keeps paying Shopify directly for their Shopify plan.
A Shopify store lead (kinetic_find) gets a store makeover instead of a plain mock-up: a home page in their brand with an
animated hero, scroll reveals, a product grid with motion, a reviews strip and copy with personality, and its outreach
opens with the store's top problem ("Your store uses Shopify's free default theme, so it looks like thousands of
others: no movement, nothing that feels like <brand>.").

mockup: a one-page, phone-friendly concept home page for the business, in colours that suit its trade or in a design
system saved by extract_design_system (style_from). Saved in Kinetic Web Designs/Mockups/<business>/index.html. It uses
no photos or logos from the business, so it is safe to show them as a concept.

domain_owner: once a client says yes, the details their domain name is registered with (the legal owner):
name, address, email, phone and their written OK. Shows what is still missing and a message asking the client
for it. Kept in kinetic-domain-owners.json on this PC only.

welcome_emails: after the deposit invoice, two emails for a new client: a thank-you confirming their order and what
they'll receive, then "Next steps required from you" (domain owner details, their content and the hosting and care
plan). With the client's email address they go into Alfred's drafts for the user to send.

outreach: a short first message (email, letter, phone call, walk-in, Instagram DM or WhatsApp) built from the audit.
It opens with the lead's single biggest problem in plain words (no website, a site that won't load, no online booking,
broken on phones, Instagram only...), then "so I made you this" and their free mock-up, then "see your design before
you pay anything", the starting price in the prospect's currency and the payment terms. With no channel asked for,
the lead type picks it (kinetic_world.lead_channels): no website or only a social page gets an Instagram DM and a
WhatsApp message (each under 400 characters), a weak website gets an email and a short phone script, and where cold
email isn't allowed (sole traders in the UK, Germany, Canada...) a phone script and a DM. With JARVIS_KINETIC_VIDEO
on, a 30-second phone video of the mock-up is made too (kinetic_video) and named in the draft to attach. For a prospect abroad it is written in their language
(from their country, or the one asked for) with the English version underneath. Drafts only: nothing is ever sent.
The note it adds sums up that country's rules on unasked-for marketing (PECR, GDPR, CAN-SPAM, CASL, POPIA, PIPL...),
and where cold email isn't allowed it drafts a social media DM instead. Each draft is recorded in the outreach tracker
(kinetic_outreach): nobody who opted out or said no gets a draft, and a lead already messaged gets a warning instead of
a second first message.
"""

import asyncio
import json
import re
from datetime import timedelta
from html import escape

import alfred_mail
import kinetic_outreach as tracker
import kinetic_store as st
import kinetic_world as world
import memory
import screen
from config import Settings

NAMES = {"web_design_sales"}
ACTIONS = ["prices", "set_price", "my_details", "quote", "quotes", "quote_status", "domain_owner",
           "welcome_emails", "mockup", "outreach"]
QUOTE_STATUSES = ["draft", "sent", "accepted", "declined"]
CHANNELS = ["email", "letter", "phone", "visit", "dm", "whatsapp"]
DEFAULT_PRICES = {
    "packages": {
        "starter": {"name": "Starter website", "price": 395,
                    "includes": "A one-page website made for phones, contact form, tap-to-call, Google basics "
                                "(title, description, business details) and 2 rounds of changes."},
        "business": {"name": "Business website", "price": 895,
                     "includes": "Up to 5 pages made for phones, contact form, tap-to-call, basic Google Business "
                                 "Profile linking, share previews, a fast secure (HTTPS) setup and 3 rounds of changes."},
        "shop": {"name": "Online shop", "price": 1595,
                 "includes": "Everything in the business website plus a shop with up to 20 products, card payments "
                             "set up with your own provider, delivery options and order emails."},
        "shopify_redesign": {"name": "Shopify store redesign", "price": 595,
                             "includes": "A new look for your existing Shopify store: a home page in your brand with "
                                         "movement and personality (animated hero, scroll reveals, product grid, "
                                         "reviews strip), product and collection pages styled to match, a speed "
                                         "clean-up and 2 rounds of changes. Your products, orders and customers stay "
                                         "where they are."},
        "shopify_setup": {"name": "Shopify store setup", "price": 995,
                          "includes": "A new Shopify store set up and designed for you: a theme made to feel like "
                                      "your brand, up to 25 products added, collections, payments, delivery and tax "
                                      "settings, a reviews app, Google and social sales channels and 3 rounds of "
                                      "changes."},
    },
    "addons": {
        "logo": {"name": "Logo design", "price": 150},
        "copywriting": {"name": "Copywriting (per page)", "price": 60},
        "extra_page": {"name": "Extra page", "price": 120},
        "booking": {"name": "Online booking", "price": 200},
        "seo": {"name": "Full Google Business Profile setup and optimisation", "price": 150},
        "photos": {"name": "Photo editing and stock images", "price": 100},
    },
    "care_plan": {"name": "Monthly hosting and care", "price": 20,
                  "by_package": {"starter": 20, "business": 25, "shop": 30, "shopify_redesign": 25,
                                 "shopify_setup": 30},
                  "includes": "Your domain name, hosting, security updates, backups and small text changes each "
                              "month."},
    "deposit_percent": 50,
    "valid_days": 30,
}
WEEKS = {"starter": "1 to 2 weeks", "business": "2 to 4 weeks", "shop": "4 to 6 weeks",
         "shopify_redesign": "1 to 2 weeks", "shopify_setup": "3 to 4 weeks"}
SHOPIFY_PACKAGES = ("shopify_redesign", "shopify_setup")
SHOPIFY_PLAN = ("You keep paying Shopify directly for your Shopify plan (and any paid apps), as you do now; it stays in "
                "your name and isn't part of this price.")
SHOPIFY_CARE = ("For a Shopify store, hosting is part of your Shopify plan, so care covers theme and app updates, "
                "monthly checks, theme backups and small text and image changes.")
PACKAGE_WORDS = {"one page": "starter", "one-page": "starter", "basic": "starter", "website": "business",
                 "standard": "business", "ecommerce": "shop", "e-commerce": "shop", "store": "shop",
                 "online_shop": "shop", "shopify": "shopify_redesign", "shopify_store_redesign": "shopify_redesign",
                 "store_redesign": "shopify_redesign", "store_makeover": "shopify_redesign",
                 "makeover": "shopify_redesign", "shopify_makeover": "shopify_redesign",
                 "shopify_store_setup": "shopify_setup", "new_shopify_store": "shopify_setup",
                 "shopify_store": "shopify_setup", "store_setup": "shopify_setup"}


def package_key(value, default: str = "business") -> str:
    """A package key from a name like "Shopify store redesign", "store makeover" or "business website"."""
    key = re.sub(r"[\s-]+", "_", str(value or default).strip().lower()).replace("_website", "")
    return PACKAGE_WORDS.get(key, PACKAGE_WORDS.get(key.replace("_", " "), key))
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
               "boutique": "shop", "jewel": "shop", "shop": "shop", "pet": "shop", "bicycle": "shop",
               "perfum": "beauty", "wig": "shop", "shoe": "shop", "toy": "shop", "baby": "shop", "deli": "shop",
               "wine": "shop", "chocolat": "shop", "confection": "shop", "houseware": "shop", "interior": "shop",
               "furniture": "shop", "candle": "shop", "galler": "shop", "stationer": "shop", "store": "shop"}
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
    # Care is priced per package; an old single saved price is ignored so the new tiers take effect.
    for key, val in ((saved.get("care_plan") or {}).get("by_package") or {}).items():
        if key in out["care_plan"]["by_package"] and isinstance(val, (int, float)):
            out["care_plan"]["by_package"][key] = val
    out["care_plan"]["price"] = out["care_plan"]["by_package"]["starter"]
    return out


def care_price(p: dict, package: str) -> float:
    """Monthly hosting and care for a package: £20 starter, £25 business, £30 shop by default."""
    return float(p["care_plan"]["by_package"].get(package, p["care_plan"]["by_package"]["business"]))


def care_text(p: dict) -> str:
    c = p["care_plan"]["by_package"]
    return (f"{st.gbp(c['starter'])} starter, {st.gbp(c['business'])} business, {st.gbp(c['shop'])} shop, "
            f"{st.gbp(c['shopify_redesign'])} Shopify redesign, {st.gbp(c['shopify_setup'])} Shopify setup")


def show_prices(settings: Settings, args: dict, prefix: str = "") -> screen.Shown:
    p = prices(settings)
    rows = [[v["name"], st.gbp(v["price"]), v["includes"]] for v in p["packages"].values()]
    rows += [[v["name"], st.gbp(v["price"]), "add-on"] for v in p["addons"].values()]
    rows += [[f"{p['care_plan']['name']} ({p['packages'][k]['name']})", st.gbp(v) + "/month", p["care_plan"]["includes"]]
             for k, v in p["care_plan"]["by_package"].items()]
    custom = " These are starting prices; say \"set my business website price to 950\" to use your own." \
        if not st.load(settings, st.PRICES, {}) else ""
    text = (f"{prefix} Your website prices: starter {st.gbp(p['packages']['starter']['price'])}, business "
            f"{st.gbp(p['packages']['business']['price'])}, shop {st.gbp(p['packages']['shop']['price'])}, Shopify "
            f"store redesign {st.gbp(p['packages']['shopify_redesign']['price'])}, Shopify store setup "
            f"{st.gbp(p['packages']['shopify_setup']['price'])}, care plan a month {care_text(p)}, "
            f"{st.num(p['deposit_percent'])}% deposit. Shopify clients keep paying Shopify directly for their "
            f"plan.{custom}").strip()
    cur = world.currency_of(world.country_code(args.get("country")))
    if cur != "GBP":
        text += (f" In {world.CURRENCIES[cur][1]} that's roughly: " + ", ".join(
            f"{k} {world.local_price(v['price'], cur, '')}" for k, v in p["packages"].items()) +
            ". You still charge in pounds.")
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
        pk = package_key(args.get("package")) if args.get("package") else ""
        if pk and pk not in p["care_plan"]["by_package"]:
            raise ValueError("Care plan prices are for starter, business, shop, shopify_redesign or shopify_setup.")
        tiers = dict(p["care_plan"]["by_package"])
        for key in ([pk] if pk else tiers):
            tiers[key] = st.number(args.get("price"), "price")
        saved["care_plan"] = {"by_package": tiers}
    else:
        item = {"business_website": "business", "starter_website": "starter", "online_shop": "shop",
                "logo_design": "logo", "page": "extra_page"}.get(item, item)
        if item not in p["addons"]:
            item = package_key(item)
        group = "packages" if item in p["packages"] else "addons" if item in p["addons"] else ""
        if not group:
            raise ValueError("Which price? " + ", ".join(list(p["packages"]) + list(p["addons"])) +
                             ", care_plan or deposit.")
        saved.setdefault(group, {})[item] = {"price": st.number(args.get("price"), "price")}
    st.save(settings, st.PRICES, saved)
    return show_prices(settings, {}, "Saved.")


DETAILS = ["name", "owner", "email", "phone", "website", "address", "bank_name", "sort_code", "account_number",
           "vat_number", "plan_link"]


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


def country_of(args: dict, prospect: dict | None) -> str:
    """The client's two-letter country: the one asked for, else the prospect's, else home (the UK)."""
    asked = world.country_code(args.get("country"))
    if args.get("country") and not asked and not (prospect or {}).get("country"):
        return ""  # a country with no rules or rate on file: pounds and the general note
    return asked or (prospect or {}).get("country") or world.HOME


REBUILD_OFF = 20
REBUILD_PACKAGES = ("business", "shop")
FOUNDING_OFF = 100  # the website's founding client offer: £100 off for the first 3 clients
FOUNDING_PLACES = 3
FOUNDING_DEAL = "in return for an honest Google review and permission to show your site as an example of our work"


def founding_clients(settings: Settings) -> list[str]:
    """Clients who have the founding client offer on a quote that wasn't declined."""
    names = []
    for q in st.rows_of(settings, st.QUOTES):
        if q.get("founding_discount") and q.get("status") != "declined" and q["client"] not in names:
            names.append(q["client"])
    return names


def best_discount(settings: Settings, args: dict, name: str, package: str, first_price: float, subtotal: float
                  ) -> tuple[str, float]:
    """The one offer that saves the client most: ("rebuild" 20% off, "founding" £100 off, or "", 0). They never stack."""
    rebuild = round(first_price * REBUILD_OFF / 100, 2) \
        if args.get("existing_website") is True and package in REBUILD_PACKAGES else 0.0
    founding = 0.0
    if args.get("founding") is True:
        taken = [n for n in founding_clients(settings) if n.lower() != name.lower()]
        if len(taken) >= FOUNDING_PLACES:
            raise ValueError(f"The founding client offer is for the first {FOUNDING_PLACES} clients, and "
                             + ", ".join(taken[:FOUNDING_PLACES]) + " already have it.")
        founding = float(min(FOUNDING_OFF, subtotal))
    if founding > rebuild:
        return "founding", founding
    return ("rebuild", rebuild) if rebuild else ("", 0.0)

def quote_lines(settings: Settings, args: dict) -> tuple[list[tuple[str, int, float]], float, str]:
    """[(description, qty, unit price)], monthly care price (0 if none) and the package key."""
    p = prices(settings)
    package = package_key(args.get("package"))
    if package not in p["packages"]:
        raise ValueError("Which package? starter, business, shop, shopify_redesign or shopify_setup.")
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
            qty = max(1, int(args.get("pages") or {"starter": 1}.get(package, 5)))
        lines.append((p["addons"][key]["name"], qty, float(p["addons"][key]["price"])))
    for extra in args.get("custom_items") or []:
        if isinstance(extra, dict) and extra.get("description"):
            lines.append((st.clean(extra["description"], 160), 1, st.number(extra.get("price"), "item price")))
    care = care_price(p, package) if args.get("care_plan", True) else 0.0
    return lines, care, package


def quote(settings: Settings, args: dict) -> screen.Shown:
    name, prospect = client_and_prospect(settings, args)
    lines, care, package = quote_lines(settings, args)
    p = prices(settings)
    subtotal = sum(q * u for _, q, u in lines)
    # Clients who already have a website get 20% off a business site or shop rebuild, and the first 3 clients get the
    # founding client offer (£100 off): whichever saves them more, never both.
    offer, off = best_discount(settings, args, name, package, lines[0][2], subtotal)
    rebuild = off if offer == "rebuild" else 0.0
    founding = off if offer == "founding" else 0.0
    discount = st.number(args.get("discount"), "discount", True, subtotal - off) if args.get("discount") else 0.0
    total = round(subtotal - off - discount, 2)
    deposit = round(total * p["deposit_percent"] / 100, 2)
    cur = world.currency_of(country_of(args, prospect))
    about = f" (about {world.money(world.convert(total, cur), cur)})" if cur != "GBP" else ""
    rows = st.rows_of(settings, st.QUOTES)
    qid = st.next_id(rows)
    number = f"Q-{qid:04d}"
    valid = st.today() + timedelta(days=int(p["valid_days"]))
    fixes = [x["problem"] for x in ((prospect or {}).get("audit") or {}).get("problems", [])][:6]
    if prospect and not prospect.get("website"):
        fixes = ["You don't have a website yet, so customers who search for you find competitors instead."]
    fixes_title = "What your store makeover fixes" if package in SHOPIFY_PACKAGES else "What your new website fixes"
    body = [f"<h2>Quote {number} for {escape(name)}</h2>",
            '<div class="meta">' + "".join(f"<div><b>{k}</b>{escape(v)}</div>" for k, v in (
                ("Quote number", number), ("Date", st.short(st.today())), ("Valid until", st.short(valid)),
                ("Time to build", WEEKS[package]))) + "</div>",
            f"<p class=note><b>{escape(st.PREVIEW)}</b> You see a free design of your new home page first, and "
            "only pay once you're happy to go ahead.</p>"]
    if args.get("notes"):
        body.append(f"<p>{escape(st.clean(args['notes'], 600))}</p>")
    if fixes:
        body += [f"<h2>{fixes_title}</h2>", "<ul>" + "".join(f"<li>{escape(x)}</li>" for x in fixes) + "</ul>"]
    table = ["<table><tr><th>Item</th><th class=n>Qty</th><th class=n>Price</th><th class=n>Total</th></tr>"]
    table += [f"<tr><td>{escape(d)}</td><td class=n>{q}</td><td class=n>{st.gbp(u)}</td><td class=n>{st.gbp(q * u)}</td></tr>"
              for d, q, u in lines]
    if rebuild:
        table.append(f"<tr><td>Existing website: {REBUILD_OFF}% off the {escape(lines[0][0].split(': ')[0])}</td><td></td><td></td>"
                     f"<td class=n>-{st.gbp(rebuild)}</td></tr>")
    if founding:
        table.append(f"<tr><td>Founding client offer: {st.gbp(FOUNDING_OFF)} off</td><td></td><td></td>"
                     f"<td class=n>-{st.gbp(founding)}</td></tr>")
    if discount:
        table.append(f"<tr><td>Discount</td><td></td><td></td><td class=n>-{st.gbp(discount)}</td></tr>")
    table.append(f"<tr class=total><td>Total</td><td></td><td></td><td class=n>{st.gbp(total)}</td></tr></table>")
    body += ["<h2>Price</h2>", "".join(table)]
    if founding:
        body.append(f"<p class=note>As one of our first {FOUNDING_PLACES} clients you get {st.gbp(FOUNDING_OFF)} off "
                    f"{escape(FOUNDING_DEAL)}." + (f" (It replaces the {REBUILD_OFF}% existing-website discount, as "
                                                   "this saves you more.)" if args.get("existing_website") is True and
                                                   package in REBUILD_PACKAGES else "") + "</p>")
    terms = world.payment_terms(p["deposit_percent"])
    body.append(f"<p class=note>You pay {escape(terms, False)}. Prices are in pounds (GBP)"
                + (f"; {st.gbp(total)} is about {world.money(world.convert(total, cur), cur)} in "
                   f"{world.CURRENCIES[cur][1]} at a rough exchange rate, and your bank converts it when you pay"
                   if about else "") + ".</p>")
    if package in SHOPIFY_PACKAGES:
        body.append(f"<p class=note><b>Your Shopify plan.</b> {escape(SHOPIFY_PLAN)}</p>")
    if care:
        body.append(f"<p>Optional {escape(p['care_plan']['name'].lower())}: {st.gbp(care)} a month. "
                    f"{escape(SHOPIFY_CARE if package in SHOPIFY_PACKAGES else p['care_plan']['includes'])} "
                    "Cancel any time with a month's notice. Set it up at "
                    f"<a href=\"{escape(st.business(settings)['plan_link'])}\">{escape(st.business(settings)['plan_link'])}</a>.</p>")
    vat = st.business(settings)["vat_number"]
    body += ["<h2>How it works</h2>", "<ol>",
             f"<li>You say yes, and I send an invoice for the {st.num(p['deposit_percent'])}% deposit "
             f"({st.gbp(deposit)}) to book your start date{': half when we start building' if p['deposit_percent'] == 50 else ''}.</li>" if deposit else "<li>You say yes and we book a start date.</li>",
             "<li>A short call about your business, your customers and the look you like.</li>",
             "<li>I design and build the site, and you review it on your own phone.</li>",
             f"<li>Once you're happy, it goes live and the rest ({st.gbp(total - deposit)}) is invoiced"
             f"{': the other half, once everything is complete' if p['deposit_percent'] == 50 else ''}.</li>", "</ol>",
             "<h2>The small print</h2>", "<ul>",
             "<li>You own the finished website and its content once the final invoice is paid.</li>",
             "<li>Your domain name is registered in your name, so it is yours. It is included with hosting and "
             "care; without it, the domain and any paid plugins or shop fees are paid by you, at cost.</li>",
             "<li>Changes beyond the included rounds are charged at an agreed hourly rate.</li>",
             f"<li>Prices {'exclude VAT' if vat else 'have no VAT to add'}.</li>",
             "<li>No monthly instalments or buy-now-pay-later: you pay " + escape(terms, False) + ".</li>",
             "<li>If you are buying as a private individual rather than a business, you can cancel within 14 days "
             "of saying yes. If you ask me to start work sooner and then cancel, you pay only for the work done.</li>",
             "</ul>",
             f"<footer>Quote {number} · valid until {st.long_date(valid)}</footer>"]
    html = st.doc_html(settings, f"Quote {number} for {name}", "\n".join(body))
    path = st.write(settings, ("Clients", name), f"Quote {number}.html", html)
    rows.append({"id": qid, "number": number, "client": name, "package": package, "total": total, "deposit": deposit,
                 "care": care, "date": st.today().isoformat(), "valid_until": valid.isoformat(), "status": "draft",
                 "lines": [[d, q, u] for d, q, u in lines], "discount": discount, "rebuild_discount": rebuild,
                 "founding_discount": founding, "file": st.where(settings, path)})
    st.save(settings, st.QUOTES, rows)
    text = (f"Quote {number} for {name}: {st.gbp(total)}{about}" + (f", with a {st.gbp(deposit)} deposit" if deposit else "")
            + (f" and an optional {st.gbp(care)} a month care plan" if care else "") +
            (f", with the {st.gbp(FOUNDING_OFF)} founding client offer" if founding else
             f", with {REBUILD_OFF}% off for their existing website" if rebuild else "") +
            f". They pay {terms}." + (" They keep paying Shopify directly for their Shopify plan."
                                      if package in SHOPIFY_PACKAGES else "") +
            f" Saved in {st.where(settings, path)}; open it and print to PDF to send it. {st.NOT_SENT}")
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
                f"deposit invoice for {q['number']}\" when you're ready. Next, collect their domain owner details: "
                f"say \"domain owner details for {q['client']}\".")
    return f"Quote {q['number']} is now {status}."


# ---- domain owner details ----------------------------------------------------------

OWNER_FIELDS = [("domain", "Domain name"), ("owner_name", "Full name or business name"),
                ("owner_address", "Postal address"), ("owner_email", "Email"), ("owner_phone", "Phone number")]


def domain_owner(settings: Settings, args: dict) -> screen.Shown:
    """The details a client's domain is registered with, so the domain legally belongs to them."""
    if not (args.get("client") or args.get("quote")):
        raise ValueError("Which client's domain? Give their name.")
    name = find_quote(st.rows_of(settings, st.QUOTES), args["quote"])["client"] if args.get("quote") \
        else client_and_prospect(settings, args)[0]
    owners = st.load(settings, st.DOMAIN_OWNERS, {})
    rec = owners.get(name, {})
    changed = False
    for key, _ in OWNER_FIELDS:
        if args.get(key):
            value = st.clean(args[key], 200)
            if key == "domain":
                value = st.domain(value) or value.lower()
            elif key == "owner_email" and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value):
                raise ValueError("That email address doesn't look right.")
            rec[key] = value
            changed = True
    if args.get("owner_ok") is not None:
        rec["owner_ok"] = st.today().isoformat() if args["owner_ok"] else ""
        changed = True
    if changed:
        owners[name] = rec
        st.save(settings, st.DOMAIN_OWNERS, owners)
    lines = [f"{'✓' if rec.get(k) else '○'} {label}: {rec.get(k) or 'still needed'}" for k, label in OWNER_FIELDS]
    lines.append(f"{'✓' if rec.get('owner_ok') else '○'} Their written OK to register it in their name: "
                 + (f"given {rec['owner_ok']}" if rec.get("owner_ok") else "still needed"))
    missing = [label.lower() for k, label in OWNER_FIELDS[1:] if not rec.get(k)]
    domain = rec.get("domain") or "your new domain name"
    if missing or not rec.get("owner_ok"):
        need = ", ".join(missing[:-1]) + " and " + missing[-1] if len(missing) > 1 else "".join(missing)
        ask = (f"Hi, I'll register {domain} so that it legally belongs to you. "
               + (f"Please send me your {need}, and reply" if missing else "Please reply")
               + f" \"Yes, register {domain} in my name.\" I'll only use these details for your domain.")
        body = "\n".join(lines) + "\n\nMessage to send them:\n" + ask
        text = (f"{name}'s domain owner details: {sum(1 for k, _ in OWNER_FIELDS if rec.get(k))} of "
                f"{len(OWNER_FIELDS)} saved" + ("" if rec.get("owner_ok") else ", and their OK is still needed")
                + ". There's a message you can send them on the card. " + st.NOT_SENT)
    else:
        body = "\n".join(lines) + ("\n\nAll set. Buy the domain in your Cloudflare account and enter these as the "
                                   "owner (registrant) details.")
        text = f"{name}'s domain owner details are complete, so you can register {domain} in their name."
    return st.text_card(text, f"Domain owner: {name}", body)


# ---- welcome emails ----------------------------------------------------------------

def welcome_emails(settings: Settings, args: dict) -> screen.Shown:
    """The two emails a new client gets after their deposit invoice: order confirmation, then next steps."""
    q = find_quote(st.rows_of(settings, st.QUOTES), args.get("quote") or args.get("client"))
    p, me = prices(settings), st.business(settings)
    name, first = q["client"], st.clean(args.get("contact_name"), 40) or "[First name]"
    package, includes = (q["lines"][0][0].split(": ", 1) + [""])[:2]
    extras = [f"{d}" + (f" × {n}" if n > 1 else "") for d, n, _ in q["lines"][1:]]
    invoices = [i for i in st.rows_of(settings, st.INVOICES) if i.get("quote") == q["number"] and i["status"] != "cancelled"]
    invoice_no = invoices[0]["number"] if invoices else "[Invoice number]"
    domain = st.load(settings, st.DOMAIN_OWNERS, {}).get(name, {}).get("domain") or "your domain name"
    care = q.get("care") or care_price(p, q.get("package") or "business")
    sign = "\n".join(x for x in ("Kind regards,", st.sign_off(me),
                                  " · ".join(x for x in (me["phone"], me["email"]) if x)) if x)
    rounds = 2 if q["package"] == "starter" else 3
    order = "\n".join([f"- {package}" + (f": {includes}" if includes else "")] + [f"- {x}" for x in extras])
    first_email = (
        f"Dear {first},\n\nThank you for choosing {me['name']}. I'm pleased to confirm your order and I'm looking "
        f"forward to building your new website.\n\nYour order\n{order}\n\n"
        f"Total: {st.gbp(q['total'])}\n"
        + (f"Deposit to start ({st.num(p['deposit_percent'])}%): {st.gbp(q['deposit'])}, invoice {invoice_no}, sent today\n"
           f"Balance: {st.gbp(q['total'] - q['deposit'])}, due when your website goes live\n" if q["deposit"] else "")
        + f"Estimated time: {WEEKS[q['package']]} from receipt of your deposit\n\n"
        f"What you'll receive\n- A website designed for phones, tablets and computers\n"
        f"- {rounds} rounds of changes so it's exactly how you want it\n"
        f"- Your domain name registered in your name, so it always belongs to you\n"
        f"- Full ownership of the finished website once the final invoice is paid\n"
        + (f"- {SHOPIFY_PLAN}\n" if q["package"] in SHOPIFY_PACKAGES else "") + "\n"
        f"I'll send a short follow-up email with a few next steps. If you have any questions in the meantime, just "
        f"reply to this email.\n\n{sign}")
    join = (f"To join, set up your plan here: {me['plan_link']}\nOr just reply \"Yes to hosting and care\" "
            f"with your details from step 1.")
    second_email = (
        f"Dear {first},\n\nTo get your website started, there are three quick things I need from you.\n\n"
        f"1. Your domain owner details\nYour domain name ({domain}) will be registered in your name, so it legally "
        f"belongs to you. Please reply with your full name or business name, postal address, email and phone number, "
        f"and the words \"Yes, register {domain} in my name.\"\n\n"
        f"2. Your content\nYour logo, any photos you'd like to use, and a few lines about your business in your own "
        f"words. Don't worry if you don't have everything; we can help.\n\n"
        f"3. Hosting and care: {st.gbp(care)} a month\nA website needs a secure home online, and it needs looking "
        f"after. Our hosting and care plan means you never have to think about it.\n\nWhat's included\n"
        f"- Your domain name and hosting: your website stays online, fast and secure.\n"
        f"- Security checks and updates: we monitor your site and keep everything up to date.\n"
        f"- Backups: if anything ever goes wrong, we can restore your site.\n"
        f"- We fix problems for you: if something breaks, we put it right at no extra cost.\n"
        f"- Small changes at no extra cost: updated prices, opening hours, text, photos or contact details. Just "
        f"email us and we'll handle it.\n\nLarger changes, such as new pages, new features or a redesign, are quoted "
        f"separately so you always know the cost before any work begins.\n\nHow it works\n"
        f"- {st.gbp(care)} a month, starting the month your website goes live.\n"
        f"- No long contract: cancel any time with one month's notice.\n"
        f"- If you leave, we hand everything over to you, including your domain.\n\n"
        f"Without a plan, you'd need to arrange and pay for your own hosting and domain and fix any problems "
        f"yourself. Most of our clients find the plan saves them time, money and worry.\n\n{join}\n\n{sign}")
    emails = [(f"Thank you for choosing {me['name']}: your order is confirmed", first_email),
              ("Next steps required from you", second_email)]
    for n, (subject, body) in enumerate(emails, 1):
        st.write(settings, ("Clients", name), f"Welcome email {n} {q['number']}.md", f"Subject: {subject}\n\n{body}\n")
    to = str(args.get("to") or "").strip()
    if to:
        ids = [alfred_mail.draft(settings, {"to": to, "subject": subject, "body": body}).card["id"]
               for subject, body in emails]
        text = (f"Both welcome emails for {name} are in my drafts to {to} and have NOT been sent. Send the order "
                f"confirmation first, then next steps. Say \"send email draft\" with its number when you're happy.")
        return st.text_card(text, f"Welcome emails: {name}", "\n\n----------\n\n".join(
            f"Subject: {s}\n\n{b}" for s, b in emails), [
            {"label": "Send order confirmation", "say": f"Yes, send email draft {ids[0].rsplit('-', 1)[-1]}."}])
    return st.text_card(
        f"Both welcome emails for {name} are written and saved in Kinetic Web Designs/Clients/{name}. {st.NOT_SENT} "
        "Give me their email address and I'll put them in my drafts ready to send.",
        f"Welcome emails: {name}", "\n\n----------\n\n".join(f"Subject: {s}\n\n{b}" for s, b in emails))


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


_UNSAFE_TAGS = re.compile(r"<\s*(script|iframe|object|embed|link|meta|base|form|style)\b.*?(?:</\s*\1\s*>|/?>)",
                          re.I | re.S)
_UNSAFE_ATTRS = re.compile(r"""\s(?:on\w+|srcdoc|formaction)\s*=\s*(?:"[^"]*"|'[^']*'|[^\s>]+)""", re.I)
_JS_URLS = re.compile(r"(?:java|vb)script\s*:", re.I)


def clean_section(html: str) -> str:
    """Extra page sections (e.g. converted 21st.dev components) without scripts, frames, forms or event handlers."""
    text = str(html or "")[:20_000]
    for _ in range(3):  # nested tricks like <scr<script>ipt>
        text = _UNSAFE_TAGS.sub("", text)
    return _JS_URLS.sub("", _UNSAFE_ATTRS.sub("", text)).replace("<!--", "").strip()


def clean_css(css: str) -> str:
    """Section CSS that can't close the style tag, import other files or run anything."""
    text = str(css or "")[:12_000].replace("<", "")  # CSS never needs "<", and without it nothing can end the style tag
    text = re.sub(r"@import[^;]*;?", "", text, flags=re.I)
    return re.sub(r"expression\s*\(|(?:java|vb)script\s*:|-moz-binding", "", text, flags=re.I)


CONTACT_TEXT = "Opening hours, address and a map go here, so people can find you in seconds."


def call_button(phone: str) -> str:
    """The mock-up's call button: tap-to-call with their number, else a link to the contact section."""
    tel = re.sub(r"[^\d+]", "", phone)
    return (f'<a class="btn" href="tel:{escape(tel)}">Call {escape(phone)}</a>' if tel else
            '<a class="btn" href="#contact">Get in touch</a>')


def service_card(service: str) -> str:
    e = escape
    return (f'<div class="card"><span class="dot"></span><h3>{e(service)}</h3><p>Tell customers what makes your '
            f'{e(service.lower())} worth choosing, in a sentence or two.</p></div>')


def contact_text(address: str) -> str:
    return (f"<p>Find us at {escape(address)}. Opening hours and a map go here, so people can find you in seconds.</p>"
            if address else f"<p>{CONTACT_TEXT}</p>")


def mockup_html(name: str, trade: str, tagline: str, services: list[str], phone: str, town: str, look: dict | None,
                maker: str, sections: list[str] = (), section_css: str = "", address: str = "") -> str:
    bg, ink, brand, accent, head, body, default_tag = TRADE_LOOKS[trade]
    if look:
        bg, ink, brand, accent = (safe_css(look.get(k), d) for k, d in
                                  (("bg", bg), ("ink", ink), ("brand", brand), ("accent", accent)))
        head, body = safe_css(look.get("head"), head), safe_css(look.get("body"), body)
    tagline = tagline or default_tag
    e = escape
    call = call_button(phone)
    cards = "".join(service_card(s) for s in services[:6])
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
@media (max-width:600px){{.btn.ghost{{margin:12px 0 0}}.hero{{padding:48px 0 56px}}}}
{clean_css(section_css)}"""
    extra = "".join(f'<section class="extra">{x}</section>' for x in (clean_section(h) for h in list(sections)[:6]) if x)
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
{extra}<section><h2>What customers say</h2><p class="quote">"Space for a real review from one of your customers."<small>Your happy customer</small></p></section>
<section id="contact"><h2>Visit or get in touch</h2>{contact_text(address)}<br>{call}</section>
<footer>Concept home page for {e(name)} by {e(maker)}. Placeholder words only; not the live site.</footer></div>
</body></html>
"""


def store_lead(p: dict | None) -> bool:
    import kinetic_find  # here, not at the top: kinetic_find reaches this module through the tracker
    return kinetic_find.is_store(p or {})


def mockup(settings: Settings, args: dict) -> screen.Shown:
    name, prospect = client_and_prospect(settings, args)
    p = prospect or {}
    if (store_lead(p) or args.get("store") is True) and not (args.get("sections") or args.get("section_css")):
        path = store_mockup(settings, name, p, args)
        return st.file_shown(settings, path, f"I made a store makeover mock-up for {name}: a home page in their brand "
                             "with an animated hero, scroll reveals, a moving product grid, a reviews strip and copy "
                             f"with personality. It's in {st.where(settings, path)}; open it on your phone and PC to "
                             "check it, then show it to them as a free sample.", [
                                 {"label": "Write outreach", "say": f"Write an outreach message for {name}."},
                                 {"label": "Quote them", "say": f"Quote {name} for a Shopify store redesign."}])
    trade = trade_of(args.get("kind") or p.get("kind") or name)
    if not any(args.get(k) for k in ("style_from", "sections", "section_css", "tagline")):
        import kinetic_reach  # here, not at the top: it imports this module
        made = kinetic_reach.from_base(settings, name, p, trade, args)  # the trade's base design, swapped: fast
        if made:
            path, label = made
            return st.file_shown(settings, path, f"I made a concept home page for {name} from the {label} base design, "
                                 f"with their name, colours, phone, address and services swapped in. It's in "
                                 f"{st.where(settings, path)}; open it on your phone and PC to check it, then show it "
                                 "to them as a free sample.", [
                                     {"label": "Write outreach", "say": f"Write an outreach message for {name}."},
                                     {"label": "Quote them", "say": f"Quote {name} for a new website."}])
    services = [st.clean(s, 40) for s in (args.get("services") or []) if st.clean(s)] or SERVICES[trade]
    look = look_from(settings, str(args.get("style_from") or "").strip())
    html = mockup_html(name, trade, st.clean(args.get("tagline"), 90), services, st.clean(args.get("phone") or p.get("phone"), 30),
                       st.clean(args.get("town") or p.get("town"), 40), look, st.business(settings)["name"],
                       [x for x in args.get("sections") or [] if isinstance(x, str)], str(args.get("section_css") or ""),
                       st.clean(p.get("address"), 160))
    path = st.write(settings, ("Mockups", name), "index.html", html, replace=True)
    style = f" in the style of {args['style_from']}" if look else f" in a {trade} look"
    return st.file_shown(settings, path, f"I made a concept home page for {name}{style}. It's in {st.where(settings, path)}; "
                         "open it on your phone and PC to check it, then show it to them as a free sample.", [
                             {"label": "Write outreach", "say": f"Write an outreach email for {name} mentioning the mock-up."},
                             {"label": "Quote them", "say": f"Quote {name} for a new website."}])


# ---- store makeover mock-ups (Shopify store leads) ------------------------------------

STORE_LOOKS = {  # (background, ink, brand, accent, heading font, body font, tagline, products, story)
    "fashion": ("#f7f3ee", "#151311", "#151311", "#e4572e", "'Didot', 'Bodoni MT', Georgia, serif",
                "'Helvetica Neue', Arial, sans-serif", "Wear the mood.",
                ["The everyday tee", "Oversized blazer", "Wide-leg trousers", "Weekend knit"],
                "Pieces picked by people who actually wear them, not an algorithm."),
    "beauty": ("#fff6f3", "#2b1d22", "#b5476b", "#f2b8a2", "Georgia, serif", "'Segoe UI', Arial, sans-serif",
               "Skin first. Glow always.", ["Daily glow serum", "Barrier cream", "Lip oil", "Overnight mask"],
               "Small-batch formulas we test on ourselves before they ever reach your shelf."),
    "wigs": ("#120f14", "#f6eef2", "#d9a5c4", "#f4c95d", "'Didot', Georgia, serif", "'Segoe UI', Arial, sans-serif",
             "Hair that turns heads.", ["Body wave unit", "Bob lace front", "Kinky straight bundle", "Edge care kit"],
             "Every unit is checked by hand, and we'll help you find the one that feels like you."),
    "jewellery": ("#0f1a1c", "#f3efe6", "#d4af6a", "#8fb9a8", "'Didot', 'Bodoni MT', Georgia, serif",
                  "'Helvetica Neue', Arial, sans-serif", "Small things. Big feelings.",
                  ["Signet ring", "Pearl drop earrings", "Chain necklace", "Stacking set"],
                  "Made to be worn every day and passed on one day."),
    "home": ("#f4efe6", "#23201b", "#6b7f5a", "#d98c5f", "Georgia, serif", "'Segoe UI', Arial, sans-serif",
             "Make home feel like you.", ["Hand-poured candle", "Linen throw", "Stoneware mug", "Gift box"],
             "Things we'd give to our best friends, wrapped like we mean it."),
    "food": ("#fff8ec", "#2a1b10", "#b5361f", "#f0b429", "Georgia, serif", "'Segoe UI', Arial, sans-serif",
             "Taste the good stuff.", ["Tasting box", "House blend", "Small-batch jam", "Gift hamper"],
             "Made in small batches by people who care far too much about flavour."),
    "fitness": ("#0d0f12", "#f2f4f5", "#c8ff2e", "#3dd6d0", "'Segoe UI', Arial, sans-serif",
                "'Segoe UI', Arial, sans-serif", "Built to move.",
                ["Seamless leggings", "Training tee", "Oversized hoodie", "Shaker bottle"],
                "Kit designed in the gym, tested in the gym, made for the way you train."),
    "pets": ("#f3f7f2", "#1d2a22", "#2f7a5b", "#f4a259", "Georgia, serif", "'Segoe UI', Arial, sans-serif",
             "Happy pets live here.", ["Comfy bed", "Natural treats", "Rope toy", "Walk set"],
             "Every product is tried and tested by our own very fussy dogs and cats."),
    "kids": ("#fffaf0", "#22223b", "#4361ee", "#ff6b6b", "'Trebuchet MS', 'Segoe UI', sans-serif",
             "'Segoe UI', Arial, sans-serif", "Little things, big smiles.",
             ["Wooden stacker", "Soft bunny", "Play mat", "Story book set"],
             "Toys and clothes chosen by parents, loved by kids, built to last."),
    "art": ("#faf7f2", "#1b1b1f", "#3a5a98", "#f25f5c", "Georgia, serif", "'Segoe UI', Arial, sans-serif",
            "Make something today.", ["Limited print", "Sketchbook", "Paint set", "Framed original"],
            "Original work and the tools to make your own, from artists who love what they do."),
    "store": ("#fbf8f3", "#18181b", "#2f4858", "#f6ae2d", "Georgia, serif", "'Segoe UI', Arial, sans-serif",
              "Independent. Made with personality.", ["Best seller", "New in", "Gift idea", "Staff pick"],
              "An independent shop with real people behind it, and it shows."),
}
STORE_WORDS = [("wig", "wigs"), ("hair", "wigs"), ("beauty", "beauty"), ("cosmetic", "beauty"), ("skin", "beauty"),
               ("perfum", "beauty"), ("jewel", "jewellery"), ("watch", "jewellery"), ("cloth", "fashion"),
               ("fashion", "fashion"), ("boutique", "fashion"), ("shoe", "fashion"), ("bag", "fashion"),
               ("gift", "home"), ("home", "home"), ("house", "home"), ("interior", "home"), ("candle", "home"),
               ("furniture", "home"), ("florist", "home"), ("deli", "food"), ("food", "food"), ("wine", "food"),
               ("chocolat", "food"), ("confection", "food"), ("tea", "food"), ("coffee", "food"), ("bak", "food"),
               ("sport", "fitness"), ("fitness", "fitness"), ("gym", "fitness"), ("supplement", "fitness"),
               ("outdoor", "fitness"), ("pet", "pets"), ("toy", "kids"), ("baby", "kids"), ("kid", "kids"),
               ("game", "kids"), ("art", "art"), ("craft", "art"), ("frame", "art"), ("stationer", "art")]
REVIEW_SLOTS = ["Space for a real 5-star review from one of your customers.",
                "Another happy customer, in their own words.",
                "Your best review, pulled in from your reviews app.",
                "A line about fast delivery and lovely packaging."]


def store_category(text: str) -> str:
    """The store makeover look for a kind of store: fashion, beauty, wigs, jewellery, home, food, fitness, pets,
    kids, art, or store."""
    t = str(text or "").lower()
    return next((v for k, v in STORE_WORDS if k in t), "store")


def store_mockup_file(name: str) -> str:
    """"<business> store makeover mock-up.html" (kept short enough to attach)."""
    short_name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", name).strip()[:36].strip(" .") or "Your"
    return f"{short_name} store makeover mock-up.html"


def store_mockup_html(name: str, category: str, tagline: str, phone: str, town: str, look: dict | None, maker: str,
                      address: str = "", theme: str = "") -> str:
    """A store makeover home page in their brand: an announcement bar that moves, an animated hero, scroll reveals,
    a product grid with motion, a reviews strip and copy with personality. CSS only (no scripts), and it keeps still
    for anyone who has reduced motion turned on."""
    bg, ink, brand, accent, head, body, default_tag, products, story = STORE_LOOKS.get(category, STORE_LOOKS["store"])
    if look:
        bg, ink, brand, accent = (safe_css(look.get(k), d) for k, d in
                                  (("bg", bg), ("ink", ink), ("brand", brand), ("accent", accent)))
        head, body = safe_css(look.get("head"), head), safe_css(look.get("body"), body)
    e = escape
    tagline = tagline or default_tag
    words = "".join(f'<span style="animation-delay:{0.15 + i * 0.12:.2f}s">{e(w)}</span> '
                    for i, w in enumerate(tagline.split()))
    where_ = f" in {e(town)}" if town else ""
    news = [f"New drop at {e(name)}", "Free delivery over £50", "Gift wrapping on every order", "Easy 30-day returns",
            f"Made with love{where_}"]
    bar = "".join(f"<span>{x}</span><span>✦</span>" for x in news * 2)
    cards = "".join(f'<a class="product reveal" href="#shop" style="--d:{i * 0.08:.2f}s"><div class="pic p{i % 4}">'
                    f'<span class="tag">{"New" if i == 0 else "Best seller" if i == 1 else "Just in"}</span></div>'
                    f'<h3>{e(x)}</h3><p>£— <small>your price</small></p></a>' for i, x in enumerate(products[:6]))
    reviews = "".join(f'<figure><div class="stars">★★★★★</div><blockquote>"{e(x)}"</blockquote>'
                      f'<figcaption>Verified buyer</figcaption></figure>' for x in REVIEW_SLOTS * 2)
    tel = re.sub(r"[^\d+]", "", phone)
    contact = (f'<a class="btn ghost" href="tel:{e(tel)}">Call {e(phone)}</a>' if tel else
               '<a class="btn ghost" href="#story">Our story</a>')
    visit = f"<p>Visit us at {e(address)}, or shop online any time.</p>" if address else ""
    was = f" It replaces the {e(theme)} theme's standard home page." if theme else ""
    css = f""":root{{--bg:{bg};--ink:{ink};--brand:{brand};--accent:{accent};--head:{head};--body:{body}}}
*{{box-sizing:border-box;margin:0}}html{{scroll-behavior:smooth}}
body{{background:var(--bg);color:var(--ink);font-family:var(--body);line-height:1.6;overflow-x:hidden}}
a{{color:inherit;text-decoration:none}}.wrap{{max-width:1120px;margin:0 auto;padding:0 20px}}
.bar{{background:var(--ink);color:var(--bg);overflow:hidden;white-space:nowrap;font-size:.85rem;letter-spacing:.06em;
text-transform:uppercase}}.bar div{{display:inline-flex;gap:28px;padding:9px 0;animation:slide 26s linear infinite}}
nav{{display:flex;justify-content:space-between;align-items:center;padding:18px 0}}
.logo{{font-family:var(--head);font-size:1.5rem;font-weight:700;letter-spacing:.02em}}
nav .links{{display:flex;gap:18px;font-weight:600}}nav .links a{{background:linear-gradient(var(--accent),var(--accent))
0 100%/0 2px no-repeat;transition:background-size .35s}}nav .links a:hover{{background-size:100% 2px}}
.hero{{position:relative;min-height:78vh;display:grid;align-items:center;overflow:hidden;border-radius:0 0 40px 40px;
background:linear-gradient(120deg,var(--brand),color-mix(in srgb,var(--brand) 55%,var(--accent)),var(--accent));
background-size:220% 220%;animation:shift 14s ease-in-out infinite;color:var(--bg)}}
.blob{{position:absolute;border-radius:50%;filter:blur(40px);opacity:.55;animation:float 12s ease-in-out infinite}}
.b1{{width:340px;height:340px;background:var(--accent);top:-80px;right:-60px}}
.b2{{width:260px;height:260px;background:var(--bg);bottom:-90px;left:8%;animation-delay:-5s;opacity:.25}}
.hero .wrap{{position:relative;padding-top:64px;padding-bottom:72px}}
.hero h1{{font-family:var(--head);font-size:clamp(2.6rem,8vw,5.6rem);line-height:1;max-width:12ch}}
.hero h1 span{{display:inline-block;opacity:0;transform:translateY(40px);animation:rise .8s cubic-bezier(.2,.8,.2,1) forwards}}
.hero p{{font-size:1.2rem;max-width:42ch;margin:22px 0 30px;opacity:0;animation:rise .8s .7s forwards}}
.cta{{opacity:0;animation:rise .8s .9s forwards}}
.btn{{display:inline-block;background:var(--bg);color:var(--ink);padding:15px 28px;border-radius:999px;font-weight:700;
transition:transform .25s cubic-bezier(.2,.8,.2,1),box-shadow .25s}}.btn:hover{{transform:translateY(-3px);
box-shadow:0 12px 30px rgba(0,0,0,.25)}}.btn.ghost{{background:transparent;color:inherit;border:2px solid currentColor;
margin-left:10px}}
section{{padding:84px 0}}h2{{font-family:var(--head);font-size:clamp(1.8rem,4.5vw,3rem);line-height:1.1;margin-bottom:30px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:22px}}
.product{{display:block;transition:transform .35s cubic-bezier(.2,.8,.2,1)}}.product:hover{{transform:translateY(-6px)}}
.pic{{position:relative;aspect-ratio:4/5;border-radius:22px;overflow:hidden;margin-bottom:12px;
background:color-mix(in srgb,var(--bg) 70%,var(--brand))}}
.pic::after{{content:"";position:absolute;inset:18%;border-radius:40% 60% 55% 45%;background:var(--accent);opacity:.8;
transition:transform .6s cubic-bezier(.2,.8,.2,1);animation:morph 9s ease-in-out infinite}}.product:hover .pic::after{{transform:scale(1.12) rotate(8deg)}}
.p1::after{{background:var(--brand)}}.p2::after{{border-radius:50%}}.p3::after{{background:var(--ink);opacity:.6}}
.tag{{position:absolute;top:12px;left:12px;z-index:1;background:var(--ink);color:var(--bg);font-size:.75rem;
padding:4px 10px;border-radius:999px;text-transform:uppercase;letter-spacing:.06em}}
.product h3{{font-family:var(--head);font-size:1.15rem}}.product p{{opacity:.8}}
.reviews{{background:var(--ink);color:var(--bg);overflow:hidden;padding:56px 0}}
.reviews h2{{text-align:center}}.track{{display:flex;gap:18px;width:max-content;animation:slide 40s linear infinite}}
.reviews:hover .track{{animation-play-state:paused}}
figure{{width:300px;background:color-mix(in srgb,var(--ink) 80%,var(--bg));border-radius:20px;padding:22px}}
.stars{{color:var(--accent);letter-spacing:.15em}}blockquote{{margin:10px 0;font-family:var(--head);font-size:1.05rem}}
figcaption{{font-size:.85rem;opacity:.7}}
.story{{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:36px;align-items:center}}
.story .big{{font-family:var(--head);font-size:clamp(1.6rem,4vw,2.6rem);line-height:1.15}}
.badge{{width:150px;height:150px;border-radius:50%;display:grid;place-items:center;text-align:center;font-weight:700;
background:var(--accent);color:var(--ink);animation:spin 18s linear infinite;font-size:.9rem;padding:16px}}
footer{{padding:36px 0;font-size:.85rem;opacity:.7}}
@keyframes slide{{to{{transform:translateX(-50%)}}}}@keyframes shift{{50%{{background-position:100% 50%}}}}
@keyframes float{{50%{{transform:translate(30px,40px) scale(1.1)}}}}@keyframes rise{{to{{opacity:1;transform:none}}}}
@keyframes morph{{50%{{border-radius:60% 40% 45% 55%}}}}@keyframes spin{{to{{transform:rotate(360deg)}}}}
@keyframes reveal{{from{{opacity:0;transform:translateY(48px) scale(.97)}}to{{opacity:1;transform:none}}}}
@supports (animation-timeline: view()){{.reveal{{animation:reveal linear both;animation-timeline:view();
animation-range:entry 0% cover 28%}}}}
@media (prefers-reduced-motion:reduce){{*,*::before,*::after{{animation:none!important;transition:none!important}}
.hero h1 span,.hero p,.cta{{opacity:1;transform:none}}}}
@media (max-width:640px){{nav .links{{display:none}}.btn.ghost{{margin:12px 0 0}}.hero{{min-height:70vh}}}}"""
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(name)} | Store makeover concept</title>
<meta name="description" content="{e(tagline)}">
<style>{css}</style></head><body>
<div class="bar"><div>{bar}</div></div>
<div class="wrap"><nav><span class="logo">{e(name)}</span><span class="links"><a href="#shop">Shop</a>
<a href="#story">Our story</a><a href="#reviews">Reviews</a></span></nav></div>
<header class="hero"><span class="blob b1"></span><span class="blob b2"></span><div class="wrap">
<h1>{words}</h1><p>{e(name)}{where_}: a store with movement and personality, made to feel like you, not like a
template.</p><div class="cta"><a class="btn" href="#shop">Shop the new drop</a>{contact}</div></div></header>
<div class="wrap"><section id="shop"><h2 class="reveal">Fresh in this week</h2><div class="grid">{cards}</div></section>
<section id="story" class="story"><div class="reveal"><p class="big">{e(story)}</p>
<p style="margin-top:16px">Swap this for your story in your own words: who you are, why you started and what makes
{e(name)} different.</p>{visit}</div><div class="badge reveal">Independent · Since day one · {e(name)}</div></section></div>
<section id="reviews" class="reviews"><h2 class="reveal">Loved by our customers</h2><div class="track">{reviews}</div></section>
<div class="wrap"><footer>Store makeover concept for {e(name)} by {e(maker)}.{was} Placeholder words, products and
reviews only; not the live store. Built to drop into your Shopify theme, so your products, orders and customers stay
where they are.</footer></div>
</body></html>
"""


def store_look(settings: Settings, p: dict) -> dict | None:
    """Their own colours when known (saved on the prospect, or a design system saved for their website)."""
    own = p.get("colours") if isinstance(p.get("colours"), dict) else {}
    site = st.domain(p.get("website", ""))
    if not own and site:
        try:
            own = look_from(settings, site) or {}
        except ValueError:  # no design system saved for their site
            own = {}
    return {k: v for k, v in own.items() if v} or None


def store_mockup(settings: Settings, name: str, p: dict, args: dict) -> object:
    """Write a Shopify store lead's makeover mock-up to Mockups/<business>/index.html."""
    look = look_from(settings, str(args.get("style_from") or "").strip()) or store_look(settings, p)
    shop = (p.get("audit") or {}).get("shopify") or {}
    html = store_mockup_html(name, store_category(args.get("kind") or f"{p.get('kind', '')} {name}"),
                             st.clean(args.get("tagline"), 90), st.clean(args.get("phone") or p.get("phone"), 30),
                             st.clean(args.get("town") or p.get("town"), 40), look, st.business(settings)["name"],
                             st.clean(p.get("address"), 160), st.clean(shop.get("theme"), 60))
    return st.write(settings, ("Mockups", name), "index.html", html, replace=True)


# ---- outreach ----------------------------------------------------------------------

TRANSLATED = ("email", "letter", "dm", "whatsapp")  # what the prospect reads; phone and walk-in scripts are for the user
DM_LIMIT = 400  # a DM or WhatsApp message stays under this many characters (before the opt-out line)
LABELS = {"email": "Email", "letter": "Letter", "phone": "Phone script", "visit": "Walk-in script",
          "dm": "Instagram DM", "whatsapp": "WhatsApp message"}


def mockup_file(name: str) -> str:
    """The mock-up copy's file name, fit to attach: "<business> home page mock-up.html" (kept under 60 characters)."""
    short_name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", name).strip()[:36].strip(" .") or "Your"
    return f"{short_name} home page mock-up.html"


def outreach_mockup(settings: Settings, args: dict) -> str:
    """Make the free home page mock-up that goes with a first message, plus a copy with a name fit to attach.
    Returns the copy's place in the memory folder."""
    name, prospect = client_and_prospect(settings, args)
    mockup(settings, {k: v for k, v in args.items() if k in ("client", "business", "kind", "tagline", "services",
                                                                "phone", "town", "style_from", "sections", "section_css")})
    html = (st.folder(settings, "Mockups", name) / "index.html").read_text(encoding="utf-8")
    file = store_mockup_file(name) if store_lead(prospect) else mockup_file(name)
    return st.where(settings, st.write(settings, ("Mockups", name), file, html, replace=True))


def no_site(p: dict) -> bool:
    import kinetic_find  # here, not at the top: kinetic_find reaches this module through the tracker
    return not p.get("website") or bool(kinetic_find.social_only(p))


def channels_for(args: dict, prospect: dict | None, country: str, name: str) -> list[str]:
    """Which messages to draft, first one first: the one asked for, else by lead type (kinetic_world.lead_channels:
    a DM and WhatsApp for no website or social only, an email and a phone script for a weak website, and a phone
    script and a DM where cold email isn't allowed), else the country's default for a business not in the finder."""
    if args.get("channel"):
        if args["channel"] not in CHANNELS:
            raise ValueError("Which kind of message? " + ", ".join(CHANNELS) + ".")
        return [args["channel"]]
    if prospect:
        return world.lead_channels(country, no_site(prospect), name)
    return [world.default_channel(country)]


def hook_of(name: str, p: dict, designer: str, short: bool = False) -> str:
    """The first line: the lead's single biggest problem in plain words (from the audit); short for a DM."""
    import kinetic_find  # here, not at the top: kinetic_find reaches this module through the tracker
    found = kinetic_find.biggest_problem({**p, "name": name})
    return found.get("short" if short else "line") or (
        f"I'm with Kinetic Web Designs and I'd love to help {name} win more customers online." if short else
        f"I'm with Kinetic Web Designs, {designer}, and I'd love to help {name} win more customers online.")


def short_message(hello: str, intro: str, hook: str, made: str, attached: str, video: str, start: str, terms: str,
                  sign: str) -> str:
    """A DM or WhatsApp message under DM_LIMIT characters: shortened (file name, then price) only if it must be."""
    for file_part, price in ((attached, True), ("", True), ("", False)):
        text = " ".join(x for x in (hello, intro, hook, f"{made}{file_part if made else ''}{video}." if made else "",
                                    st.PREVIEW, f"From {start}, you pay {terms}." if price else "", sign) if x)
        if len(text) <= DM_LIMIT:
            break
    return text


def outreach_draft(settings: Settings, args: dict, channel: str = "", video: str = "") -> dict:
    """The English draft and what goes with it: who, which channel, the country, its rules note and language.
    Every first message opens with the lead's biggest problem, then "so I made you this" and the free home page
    mock-up (unless mockup is false), and says "see your design before you pay anything". video is the mock-up
    video's file name, when there is one."""
    name, prospect = client_and_prospect(settings, args)
    p = prospect or {}
    me = st.business(settings)
    country = country_of(args, prospect)
    home = country in ("", world.HOME)
    plan = channels_for(args, prospect, country, name)
    channel = channel or plan[0]
    if channel not in CHANNELS:
        raise ValueError("Which kind of message? " + ", ".join(CHANNELS) + ".")
    language = world.language_code(args.get("language"), country)
    contact = st.clean(args.get("contact_name"), 40)
    hello = f"Hi {contact}," if contact else "Hi there,"
    sign = st.sign_off(me)
    designer = "a local web designer" if home else "a web designer based in the UK, working with businesses worldwide"
    a = p.get("audit") or {}
    if not p.get("website"):
        points = ["a simple site that works on phones, with your hours, prices and a tap-to-call button",
                  "set up so you show up properly on Google and Google Maps"]
    elif a.get("grade") == "down":
        points = ["getting a fast, secure site back up", "making sure it works on phones and shows on Google"]
    elif a.get("problems"):
        points = [f"{x['problem'][0].lower() + x['problem'][1:]}: {x['why'][0].lower() + x['why'][1:]}" for x in a["problems"][:3]]
    else:
        points = ["a modern, phone-friendly site", "getting found on Google"]
    hook = hook_of(name, p, designer)
    gift = args.get("mockup", True)
    store = store_lead(p)
    file = store_mockup_file(name) if store else mockup_file(name)
    made = (f"So I made you this: a free store makeover for {name}, a new home page in your brand with movement and "
            "personality." if store else f"So I made you this: a free example of a new home page for {name}.")
    film = f" There's a 30-second video of it on a phone too ({video})." if video and gift else ""
    opener = {"email": f"{made} It's attached ({file}), so you can open it on your phone. No obligation at all.{film}",
              "letter": f"{made} It's printed and enclosed with this letter ({file}), and I'm happy to email you the "
                        "live version to open on your phone. No obligation at all.",
              }.get(channel, made) if gift else ""
    offer = "" if gift else "I'd be happy to show you some ideas, free and with no obligation."
    pr = prices(settings)
    start = world.local_price(pr["packages"]["shopify_redesign" if store else "starter"]["price"],
                              world.currency_of(country))
    terms = world.payment_terms(pr["deposit_percent"])
    price = (f"A Shopify store redesign is {start}, and you pay {terms}. You keep your Shopify plan and pay Shopify "
             "directly for it, as you do now." if store else f"Websites start from {start}, and you pay {terms}.")
    bullets = "\n".join(f"- {x[0].upper() + x[1:]}" for x in points)
    opt_out = world.OPT_OUT
    first = f"{hook} {opener}" if opener else f"{hook}\n\n{offer}"
    if channel == "email":
        subject = f"I made this for {name}" if gift else \
            (f"A quick idea for {name}'s website" if p.get("website") else f"Helping {name} get found online")
        # CAN-SPAM and CASL want a postal address in every sales email
        address = me["address"] or ("[your postal address]" if world.rules_of(country) in ("us", "ca") else "")
        body = (f"Subject: {subject}\n\n{hello}\n\n{first}\n\n{st.PREVIEW}\n\n"
                f"A couple of things I'd suggest:\n{bullets}\n\n{price}\n\n"
                f"Would a 10-minute chat this week be useful?\n\nThanks,\n{sign}"
                + "".join(f"\n{x}" for x in (me["phone"], me["website"], address) if x) + f"\n\n{opt_out}")
    elif channel == "letter":
        body = (f"{me['name']}\n{me['address'] or '[your address]'}\n{st.long_date(st.today())}\n\nTo the owner, {name}\n\n"
                f"{hello.replace('Hi', 'Dear')}\n\n{first}\n\n{st.PREVIEW}\n\n"
                f"What I'd suggest:\n{bullets}\n\n{price}\n\n"
                f"You can reach us on {me['phone'] or '[your phone]'} or {me['email'] or '[your email]'}.\n\n"
                f"Kind regards,\n{sign}\n\n{opt_out}")
    elif channel == "phone":
        ask = f"{hook} {made} Could I send it over so you can see it on your phone?" if gift else f"{hook} {offer}"
        body = (f"Phone script for {name}{(' (' + p['phone'] + ')') if p.get('phone') else ''}\n\n"
                f"1. \"Hi, is that the owner? I'm calling from {me['name']}, {designer}. Have you got two minutes?\"\n"
                f"2. If yes: \"{ask}\"\n3. \"{st.PREVIEW}\"\n4. \"I'd suggest:\"\n{bullets}\n"
                f"5. If they ask about price: \"{price}\"\n"
                "6. Ask: \"What's the best way to send it: WhatsApp or email?\" Agree a time to talk it through.\n"
                "7. If not now: thank them, ask if you can check back in a few months, and note it.\n"
                "If they say no, thank them and don't call again.")
    elif channel == "visit":
        body = (f"Walk-in script for {name}{(', ' + p['address']) if p.get('address') else ''}\n\n"
                "Go at a quiet time (mid-morning or mid-afternoon), and bring the mock-up on your phone"
                + (f" ({file})" if gift else "") + ".\n\n"
                f"\"Hi, I'm from {me['name']}, a web designer just round the corner. {hook} "
                + (f"{made} Can I show you in 30 seconds? " if gift else f"{offer} ") + f"{st.PREVIEW}\"\n\n"
                f"Points to mention:\n{bullets}\n\nIf they ask about price: \"{price}\"\n\nLeave your card or "
                "number and ask for the best WhatsApp or email to send the example to. If they're busy, ask when's "
                "better.\nIf they say no, thank them and don't come back.")
    else:  # dm or whatsapp: short, with the same hook
        hi = hello[:-1] + "!"
        intro = f"It's {st.SIGNER} from {me['name']}." if channel == "whatsapp" else ""
        brief = hook_of(name, p, designer, short=True)
        clip = " and a 30-second video of it" if video and gift else ""
        if gift:
            text = short_message(hi, intro, brief, "So I made you this: a free store makeover mock-up" if store else
                                 "So I made you this: a free home page mock-up", f" ({file})", clip, start, terms, sign)
        else:
            text = short_message(hi, intro, f"{brief} {offer}", "", "", "", start, terms, sign)
        body = f"{text}\n\n{opt_out}"
    written = channel in ("email", "dm", "whatsapp", "letter") or any(c in ("dm", "whatsapp") for c in plan)
    note = world.compliance_note(country) if written else "Be friendly and brief, and take no for an answer."
    return {"name": name, "channel": channel, "channels": plan, "country": country, "language": language,
            "body": body, "note": note, "hook": hook, "store": store}


def next_weekly_lead(settings: Settings) -> str:
    """The best uncontacted lead of the trade of the week, as a prospect number ("" when there isn't one)."""
    import kinetic_find  # here, not at the top: kinetic_find reaches this module through the tracker
    week = st.trade_of_week(settings)
    if not week:
        return ""
    fresh = {r.get("prospect") for r in tracker.all_leads(settings) if r.get("status") == "new" and r.get("prospect")}
    stores = week.get("kind") == "stores" or week.get("kind") in kinetic_find.STORE_KINDS
    rows = [p for p in st.rows_of(settings, st.PROSPECTS) if p.get("id") in fresh and
            (trade_of(f"{p.get('kind', '')} {p['name']}") == week["trade"] or (stores and kinetic_find.is_store(p)))]
    if "shopify" in str(week.get("label", "")).lower():  # "shopify stores": only leads that run on Shopify
        rows = [p for p in rows if kinetic_find.is_store(p)]
    return str(sorted(rows, key=kinetic_find.rank_key)[0]["id"]) if rows else ""


async def translated(settings: Settings, body: str, language: str, channel: str) -> tuple[str, str]:
    """(the draft, how it was written) in the lead's language with the English underneath, where they read it."""
    if language == "en" or channel not in TRANSLATED:
        return body, ""
    local = await world.translate(settings, body, language)
    if local:
        return f"{local}\n\n----------\nEnglish version:\n\n{body}", f" in {world.LANGUAGES[language]} with the English underneath"
    return body, f" in English only, as I couldn't translate it into {world.LANGUAGES[language]} just now"


async def outreach(settings: Settings, args: dict) -> screen.Shown | str:
    if not (args.get("client") or args.get("business")):  # no lead named: the best one of the trade of the week
        pick = await asyncio.to_thread(next_weekly_lead, settings)
        if pick:
            args = {**args, "client": pick}
    warning = await asyncio.to_thread(tracker.before_draft, settings, *client_and_prospect(settings, args))
    if warning:  # already messaged or already talking: no second first message
        return warning
    gift = args.get("mockup", True)
    attach = await asyncio.to_thread(outreach_mockup, settings, args) if gift else ""
    first = outreach_draft(settings, args)
    name = first["name"]
    video, video_note = None, ""
    if gift and settings.kinetic_video and args.get("video", True) is not False:
        import kinetic_video
        video, video_note = await kinetic_video.make(settings, name, first["hook"],
                                                     st.folder(settings, "Mockups", name) / "index.html",
                                                     "a store makeover, full of movement" if first["store"] else "")
    film = video.name if video else ""
    drafts = [outreach_draft(settings, args, c, film) for c in first["channels"]]
    paths, bodies, said = [], [], ""
    for i, d in enumerate(drafts):
        body, how = await translated(settings, d["body"], d["language"], d["channel"])
        if i == 0:
            said = how
        bodies.append(body)
        paths.append(await asyncio.to_thread(st.write, settings, ("Clients", name),
                                             f"Outreach {d['channel']} {st.today().isoformat()}.md", body + "\n"))
    d, channel = drafts[0], drafts[0]["channel"]
    await asyncio.to_thread(tracker.drafted, settings, name, client_and_prospect(settings, args)[1], channel,
                            d["country"], st.clean(args.get("contact_name"), 40), bool(attach))
    where_ = f" ({world.country_name(d['country'])})" if d["country"] not in ("", world.HOME) else ""
    kind = {"phone": "phone script", "visit": "walk-in script", "whatsapp": "WhatsApp message"}.get(channel, channel)
    article = "an" if channel == "email" else "a"
    how = {"email": "Attach it to the email", "dm": "Attach it to the message", "whatsapp": "Attach it to the message",
           "letter": "Print it and enclose it", "phone": "Have it ready to send them",
           "visit": "Open it on your phone to show them"}[channel]
    what = "store makeover mock-up" if d["store"] else "home page mock-up"
    gift_text = (f" I also made their free {what}: {attach}. {how}; drafts can't carry attachments."
                 if attach else "")
    if video:
        gift_text += f" Attach this video too: {st.where(settings, video)} (30 seconds, made for phones)."
    elif video_note:
        gift_text += f" {video_note}"
    also = ""
    if len(drafts) > 1:
        names = " and ".join(("an " if LABELS[x["channel"]][0] in "AEIOU" else "a ") + LABELS[x["channel"]]
                             for x in drafts[1:])
        why = ("They have no website, so they live on their phone" if no_site(client_and_prospect(settings, args)[1] or {})
               else "A cold email isn't the safe choice for them here" if channel != "email"
               else "They have a website, so email suits them")
        also = f" {why}: there's also {names.lower().replace('instagram dm', 'Instagram DM').replace('whatsapp', 'WhatsApp')} saved next to it."
    text = (f"I drafted {article} {kind} for {name}{where_}{said} and saved it in {st.where(settings, paths[0])}."
            f"{also}{gift_text} {st.NOT_SENT} Once you've sent it, tell me and I'll mark them as contacted. {d['note']}")
    card = bodies[0] + "".join(f"\n\n----------\n{LABELS[x['channel']]}:\n\n{b}" for x, b in zip(drafts[1:], bodies[1:]))
    return st.text_card(text, f"Outreach: {name}", card, [
        {"label": "Mark contacted", "say": f"I sent the outreach {channel} to {name}."},
        {"label": "Redo the mock-up", "say": f"Mock up a home page for {name}."}])


def tool_definitions() -> list[dict]:
    return [{
        "name": "web_design_sales",
        "description": "Kinetic Web Designs sales tools for paid website work. prices / set_price: the user's "
                       "package prices (starter, business, shop, shopify_redesign £595, shopify_setup £995; Shopify "
                       "clients keep paying Shopify directly for their plan), add-ons (logo, copywriting, extra_page, "
                       "booking, "
                       "seo, photos), care_plan per month and deposit percent. my_details: business name, owner, "
                       "contact and bank details used on quotes and invoices. quote: a printable website quote for a "
                       "client or saved prospect (lists what their audit found). quotes / quote_status: track quotes "
                       "(draft, sent, accepted, declined). domain_owner: save and check a client's domain owner details "
                       "(domain, owner_name, owner_address, owner_email, owner_phone, owner_ok) so the domain is "
                       "registered in the client's name; only set owner_ok when the user says the client agreed in "
                       "writing. welcome_emails: after the deposit invoice, the order "
                       "confirmation and next-steps emails for a quote (contact_name, to puts them in drafts; the "
                       "user sends them). mockup: a free concept home page for a business, optionally "
                       "in a design system saved by extract_design_system (style_from); for a creative one, read the "
                       "client-websites design guide first and add 21st.dev sections (sections, section_css); "
                       "a trade with a base design (web_design_reach trade_of_week) reuses it with the lead's details "
                       "swapped in. outreach: a first message "
                       "draft (email, letter, phone script, walk-in script, dm, whatsapp) that opens with the lead's "
                       "biggest audited problem, then \"so I made you this\" and a free home page mock-up Alfred makes "
                       "(for a Shopify store lead: a store makeover mock-up with movement and personality, opening "
                       "with the store's top problem such as Shopify's free default theme) "
                       "for them (the user attaches it) and \"see your design before you pay anything\"; leave channel "
                       "out to let the lead type pick (no website or social only: Instagram DM + WhatsApp; weak "
                       "website: email + phone script; phone + DM where cold email isn't allowed); with no client it "
                       "takes the best new lead of the trade of the week; a 30-second mock-up video is made to attach "
                       "when the PC can (video false skips it), for "
                       "prospects anywhere "
                       "in the world: the price in their currency, written in their language (from their country, or "
                       "language) with English underneath, and a note on that country's email rules. Payment terms "
                       "are always half when we start building, half once everything's complete; never offer "
                       "monthly instalments or Klarna. Drafts are signed \"Alfred, Kinetic Web Designs\", never "
                       "with the user's own name. quote founding: the founding client offer. outreach is recorded as drafted in the outreach tracker "
                       "(web_design_outreach), which refuses anyone opted out or not interested and warns when a lead "
                       "was already messaged. Drafts only: never "
                       "send anything, and only mark a quote sent when the user says they sent it.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "client": {"type": "string", "description": "Client name, or a saved prospect's number or name."},
                "package": {"type": "string", "enum": ["starter", "business", "shop", "shopify_redesign",
                                                       "shopify_setup"]},
                "store": {"type": "boolean", "description": "mockup: make a store makeover (a Shopify store's home "
                                                           "page with movement) even for a business not in the finder."},
                "addons": {"type": "array", "items": {"type": "string"},
                           "description": "logo, copywriting, extra_page, booking, seo, photos."},
                "extra_pages": {"type": "integer"}, "pages": {"type": "integer", "description": "Pages of copywriting."},
                "custom_items": {"type": "array", "items": {"type": "object", "properties": {
                    "description": {"type": "string"}, "price": {"type": "number"}}}},
                "care_plan": {"type": "boolean", "description": "quote: offer the monthly care plan (default true)."},
                "discount": {"type": "number", "description": "quote: pounds off."},
                "existing_website": {"type": "boolean", "description": "quote: true when the client already has a "
                                     "website; takes 20% off a business or shop package, as the Kinetic website offers."},
                "notes": {"type": "string", "description": "quote: a personal opening line."},
                "quote": {"type": "string", "description": "Quote number like Q-0001, or the client."},
                "status": {"type": "string", "enum": QUOTE_STATUSES},
                "domain": {"type": "string", "description": "domain_owner: the client's domain, e.g. joes.co.uk."},
                "owner_name": {"type": "string", "description": "domain_owner: the client's full or business name."},
                "owner_address": {"type": "string"}, "owner_email": {"type": "string"},
                "owner_phone": {"type": "string"},
                "to": {"type": "string", "description": "welcome_emails: the client's email address, to put both "
                                                        "emails in Alfred's drafts."},
                "owner_ok": {"type": "boolean", "description": "domain_owner: true once the client has said in "
                                                               "writing to register it in their name."},
                "item": {"type": "string", "description": "set_price: starter, business, shop, an add-on, care_plan "
                                                          "(add package to change one tier), deposit (percent) or valid_days."},
                "price": {"type": "number"},
                "kind": {"type": "string", "description": "mockup: the trade, e.g. cafe, barber, plumber."},
                "tagline": {"type": "string"}, "services": {"type": "array", "items": {"type": "string"}},
                "phone": {"type": "string"}, "town": {"type": "string"},
                "style_from": {"type": "string", "description": "mockup: a folder in Kinetic Web Designs saved by "
                                                                "extract_design_system, e.g. 'stripe.com'."},
                "sections": {"type": "array", "items": {"type": "string"},
                             "description": "mockup: up to 6 extra sections as plain HTML (e.g. 21st.dev components "
                                            "converted from React/Tailwind; see the client-websites design guide). "
                                            "Scripts and event handlers are removed."},
                "section_css": {"type": "string", "description": "mockup: plain CSS for those sections; use var(--bg), "
                                                                "var(--ink), var(--brand), var(--accent), var(--head)."},
                "channel": {"type": "string", "enum": CHANNELS},
                "contact_name": {"type": "string", "description": "outreach: the owner's first name if known."},
                "country": {"type": "string", "description": "prices, quote, outreach: the client's country, e.g. "
                                                             "'Nigeria', 'USA', 'South Korea' (default: the saved "
                                                             "prospect's country, else the UK)."},
                "language": {"type": "string", "description": "outreach: write it in this language (a code like fr, "
                                                              "de, es, pt, zh, ko, or a name); default the country's."},
                "mockup": {"type": "boolean", "description": "outreach: make the free home page mock-up and open the "
                                                            "message with it (default true; only false if the user "
                                                            "says so)."},
                "video": {"type": "boolean", "description": "outreach: also make the 30-second mock-up video to "
                                                           "attach (default true when Playwright and ffmpeg are there)."},
                "founding": {"type": "boolean", "description": "quote: the founding client offer, £100 off for the "
                                                              "first 3 clients in return for an honest Google review "
                                                              "and permission to show their site. Doesn't stack with "
                                                              "existing_website: the bigger saving wins."},
                **{k: {"type": "string"} for k in DETAILS},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


async def run_tool(name: str, args: dict, settings: Settings, http=None):
    if args.get("action") == "outreach":  # async: it may ask Claude for a translation
        return await outreach(settings, args)
    handlers = {"prices": show_prices, "set_price": set_price, "my_details": my_details, "quote": quote,
                "quotes": quotes, "quote_status": quote_status, "domain_owner": domain_owner,
                "welcome_emails": welcome_emails, "mockup": mockup, "outreach": outreach}
    return await asyncio.to_thread(st.dispatch, handlers, args.get("action"), settings, args, "web design sales")
