"""Seller guides in plain words: HMRC reporting of online sellers, sourcing tips and notes (car boots, charity shops), a
"most I should pay" calculator, seasonal buying, scams, records to keep, returns rules, platform summaries and a glossary.

Guides pop up as sellercalc-guide cards; sourcing notes are saved in sellercalc-sources.json. UK rules here are general
information written into Alfred and can go out of date, so every one says to check GOV.UK. Nothing is posted or sent.
"""

import screen
import sellercalc_store as sc
from config import Settings
from sellercalc_listing import platform_key

NAMES = {"sellercalc_guide"}
ACTIONS = ["hmrc_rules", "sourcing_tips", "add_source", "list_sources", "remove_source", "max_buy", "seasonal", "seller_scams",
           "records_checklist", "returns_rules", "platform_guide", "glossary"]
CHECK = "This is general information, not tax or legal advice, and rules change. Check GOV.UK for the current rules."

HMRC = [
    ("What happens", [
        "Since 1 January 2024, online platforms such as eBay, Vinted, Etsy, Depop, Amazon and Facebook Marketplace must collect "
        "details about their sellers and send them to HMRC once a year.",
        "You are reported if in a calendar year you make 30 or more sales, or receive about 1,700 pounds (2,000 euros) or more."]),
    ("What is sent", ["Your name, address and date of birth, how many sales you made and how much you were paid, usually by "
                      "calendar quarter. It doesn't include what you paid for things."]),
    ("What it does not mean", ["Being reported does not mean you owe tax, and it isn't an accusation. Many people are reported "
                               "and owe nothing."]),
    ("Do you owe tax?", ["Selling your own unwanted things, usually for less than you paid, isn't normally taxable.",
                         "Buying things to resell for a profit, or making things to sell, can count as trading, and trading "
                         "income may need to go on a tax return.",
                         "GOV.UK has a page on what to do if you sell things online, and another on tax on trading and hobby income."]),
    ("What to do now", ["Keep records from the first sale: what you paid, what it sold for, fees and postage.",
                        "Your platform's yearly summary should match your own records; check any difference.",
                        "If you're unsure, ask HMRC or a qualified adviser."]),
]
SOURCING = {
    "car boot": ["Arrive early: the best things go first, but late sellers cut prices.", "Bring cash in small notes and a bag.",
                 "Haggle politely; bundles work well for cheaper prices.", "Test electricals if you can, and check clothing labels.",
                 "Look for brands, vintage items and complete sets with all their parts."],
    "charity shop": ["Look at the shelves that have just been refilled and visit regularly.", "Check labels, seams and stains in good light.",
                     "Books, kids' brands, kitchenware and vintage tend to be sellable, but check sold prices first.",
                     "Prices can be higher than they used to be; only buy what leaves you a profit after fees and postage.",
                     "Some shops don't allow returns: test before you buy."],
    "house clearance": ["Ask what is included before you pay.", "Furniture is bulky and slow to sell; work out how you'll move it.",
                        "Never buy anything you can't identify as safe or legal to sell."],
    "online auction": ["Set a maximum price before you bid and stick to it.", "Remember buyer's premium, delivery and any VAT.",
                       "Check the photos for faults and ask questions."],
    "general": ["Check sold prices before you buy, not asking prices.", "Set a rule such as paying no more than a third of the resale price.",
                "Include fees, postage and packaging in your sums (ask me for the most you should pay).",
                "Don't buy fakes: check stitching, labels, serial numbers and where the seller got it.",
                "Avoid selling recalled goods, used cosmetics or car seats, or anything you can't show is safe and genuine.",
                "Electrical goods need to be safe and work: test them, and be honest about faults."],
}
SEASONS = {
    1: ["New Year sales: fitness kit, diaries, organisers and storage sell well.", "Buy winter coats cheaply, sell them next autumn."],
    2: ["Valentine's gifts early in the month.", "Start listing spring clothes and garden items."],
    3: ["Spring cleaning brings lots of stock but also lots of competition.", "Garden, outdoor and Easter items."],
    4: ["Bike, camping and garden gear.", "Spring and summer clothes sell as the weather turns."],
    5: ["Festival, holiday and outdoor items.", "Bank holidays are busy days for buyers."],
    6: ["Summer clothes, sandals, swimwear and paddling pools.", "Father's Day gifts."],
    7: ["School holidays: toys, games and travel items.", "Buy winter items cheap at car boots."],
    8: ["Back-to-school kit, uniform and stationery.", "Start sourcing autumn and winter stock."],
    9: ["School uniform and student items.", "Autumn clothes, boots and coats."],
    10: ["Halloween costumes and decor.", "Start listing Christmas toys, games and gifts."],
    11: ["Christmas gifts, toys and consoles peak; list early.", "Black Friday deals can pull prices down."],
    12: ["Last posting dates matter: say them clearly.", "After Christmas, the January clear-out begins."],
}
SCAMS = [
    ("Overpayment", ["A buyer 'accidentally' pays too much and asks for a refund of the difference. The first payment is fake or "
                     "reversed. Never refund before the money is really in your account."]),
    ("Fake payment emails", ["Emails that say 'payment held, send tracking to release it' are phishing. Check payment inside the "
                             "platform's own app or site, never through a link."]),
    ("Moving off the platform", ["A buyer who wants to chat on WhatsApp or pay by bank transfer skips the platform's protection. "
                                 "Keep to the platform's payment and messages."]),
    ("Courier collection", ["A buyer sending their own courier, or asking for a different address, is a warning sign."]),
    ("Item not received or not as described", ["Keep proof of postage and take photos of the item and parcel before sending."]),
    ("Fake screenshots", ["Payment screenshots can be faked. Check that the money has landed."]),
]
RECORDS = [
    "Receipts or notes of what you paid for each item (photos are fine).", "A sales record: date, item, price, platform.",
    "Fees from each platform (their statements or the fee table).", "Postage and packaging costs, and proof of postage.",
    "Mileage for sourcing trips, if you claim it: ask HMRC or an adviser what counts.",
    "The platform's own annual sales summary.", "Keep records for several years: GOV.UK says how long.",
]
RETURNS = [
    ("Private sellers", ["Selling your own used things as a private person, buyers generally have fewer rights: the item must be as "
                         "you described it. Describe faults honestly."]),
    ("Business sellers", ["If you sell as a trader online, buyers usually have a 14-day right to cancel and return, and the item must "
                          "match its description and be of satisfactory quality.",
                          "You may have to state your business name, address and returns policy."]),
    ("Platforms", ["Marketplaces can refund buyers under their own protection rules, even when the seller thinks the item was fine. "
                   "Photos of the item and proof of postage help."]),
]
PLATFORM_GUIDE = {
    "etsy": ("Handmade, vintage (20+ years) and craft supplies", "Fees on every sale plus a listing fee; ads optional",
             "Rules on what may be listed; your shop needs original or genuine items"),
    "ebay": ("Almost anything, from collectables to bargains", "Private sellers pay nothing on most items; business sellers pay a percentage",
             "Fees and rules for business sellers differ; sellers can pay for extras they didn't need"),
    "vinted": ("Second-hand clothes, kids' and home items", "Sellers pay nothing; the buyer pays a protection fee",
               "Postage weight bands are set by the site; business sellers should check its rules"),
    "depop": ("Vintage and fashion for younger buyers", "Payment processing fees; check for the current selling fee",
              "Photo quality and hashtags matter a lot"),
    "amazon": ("New or branded products in volume", "Referral fees, plan fee and fulfilment fees for FBA",
               "Approval for some categories; FBA has storage and return costs"),
    "facebook": ("Bulky and local items, free to list", "Free for local pick-up; a fee for shipped sales",
                 "Time-wasters and scams; meet safely and don't share bank details"),
    "shop": ("Your own brand and repeat buyers", "Card fees plus a monthly plan", "You must find your own customers; you handle the rules for consumers"),
}
GLOSSARY = [
    ("Margin", ["Profit as a share of the selling price. £5 profit on a £20 sale is a 25% margin."]),
    ("Markup", ["Profit as a share of what you paid. £5 profit on £15 cost is a 33% markup, even though the margin is 25%."]),
    ("ROI", ["Return on investment: profit divided by what you spent."]),
    ("Sell-through rate", ["Items sold divided by items you bought. Higher means stock moves."]),
    ("Sold comps", ["Prices similar items really sold for. They tell you more than asking prices."]),
    ("FBA and FBM", ["Amazon: Fulfilled by Amazon stores and posts for you; Fulfilled by Merchant means you post it."]),
    ("Print-on-demand", ["A printer makes and posts each item when it sells, so you hold no stock. You pay the base cost per order."]),
    ("Buyer Protection fee", ["Vinted's fee added to the buyer's bill. The seller doesn't pay it."]),
    ("VeRO", ["eBay's programme that lets brand owners remove fake or misused-brand listings."]),
    ("Days to sell", ["Days from listing (or buying) to sale. Long times mean tied-up money."]),
]


def hmrc_rules(settings: Settings, args: dict):
    return sc.guide("Platforms report sellers with 30 or more sales, or about 1,700 pounds, in a year. Check GOV.UK.",
                    "Online sellers and HMRC", HMRC, CHECK)


def sourcing_tips(settings: Settings, args: dict):
    kind = sc.clean(args.get("kind")).lower()
    words = (("car boot", "boot"), ("charity shop", "charity"), ("house clearance", "clearance"), ("online auction", "auction"))
    key = next((name for name, word in words if word in kind or kind == name), "general")
    sections = [(key.title(), SOURCING[key])] + ([("Any source", SOURCING["general"])] if key != "general" else [])
    return sc.guide(f"Sourcing tips for {key}.", "Sourcing tips", sections,
                    "Always check sold prices first, and only pay what leaves a profit after fees and postage.")


def _sources(settings: Settings) -> list[dict]:
    return [s for s in sc.load(settings, sc.SOURCES, []) if isinstance(s, dict)]


def add_source(settings: Settings, args: dict):
    rows = _sources(settings)
    if len(rows) >= 500:
        raise ValueError("You have 500 sourcing notes; remove some first.")
    entry = {"id": max([r["id"] for r in rows] + [0]) + 1, "place": sc.need(args.get("place"), "place", 80),
             "kind": sc.clean(args.get("kind"), 30).lower() or "other",
             "date": (sc.parse_date(args.get("date"), "date") or sc.today()).isoformat(),
             "spent": sc.arg(args, "spent", "money spent", True, 0.0), "worth": sc.arg(args, "worth", "expected resale value", True, 0.0),
             "items": int(sc.arg(args, "count", "number of items", True, 0.0)), "note": sc.clean(args.get("note"), 300)}
    rows.append(entry)
    sc.save(settings, sc.SOURCES, rows)
    text = f"Noted {entry['place']}."
    if entry["spent"]:
        text += f" You spent {sc.gbp(entry['spent'])}" + (f" and hope to resell for about {sc.gbp(entry['worth'])}." if entry["worth"] else ".")
    return text


def list_sources(settings: Settings, args: dict):
    rows = _sources(settings)
    if args.get("place"):
        rows = [r for r in rows if sc.clean(args["place"]).lower() in r["place"].lower()]
    if not rows:
        raise ValueError("No sourcing notes yet. Say where you went and what you found.")
    by: dict[str, float] = {}
    for r in rows:
        by[r["place"]] = by.get(r["place"], 0) + r["worth"] - r["spent"]
    best = max(by, key=by.get)
    text = f"{len(rows)} sourcing notes."
    if by[best] > 0:
        text += f" {best} looks best so far on your hoped-for numbers, which are guesses."
    return screen.Shown(text, screen.card(
        "table", "Sourcing notes", "sellercalc-sources", columns=["#", "Date", "Place", "Type", "Spent", "Hope to sell for", "Note"],
        rows=[[str(r["id"]), r["date"], r["place"], r["kind"], sc.gbp(r["spent"]), sc.gbp(r["worth"]), r["note"]] for r in rows[-30:][::-1]]))


def remove_source(settings: Settings, args: dict):
    rows = _sources(settings)
    ref = str(args.get("source_id") or "").lstrip("#")
    hit = next((r for r in rows if str(r["id"]) == ref), None)
    if hit is None:
        raise ValueError("Which note? Say its number.")
    if args.get("confirmed") is not True:
        return f"That deletes the note about {hit['place']}. Say yes to confirm."
    sc.save(settings, sc.SOURCES, [r for r in rows if r is not hit])
    return f"Removed the note about {hit['place']}."


def max_buy(settings: Settings, args: dict):
    rate = sc.platform(settings, args.get("platform"))
    resale = sc.arg(args, "price", "price you expect to sell for")
    base = sc.profit_on(rate, resale, 0.0, sc.arg(args, "ship_charged", "postage the buyer pays", True, 0.0),
                        sc.arg(args, "ship_cost", "postage you pay", True, 0.0), sc.arg(args, "packaging", "packaging cost", True, 0.0),
                        sc.arg(args, "extra_pct", "extra fee percentage", True, 0.0, top=60))
    margin = sc.arg(args, "target_margin_pct", "target margin", True, -1.0, top=95)
    goal = sc.arg(args, "target_profit", "profit you want", True, 3.0 if margin < 0 else 0.0)
    ceiling = base["net"] - (base["income"] * margin / 100 if margin >= 0 else goal)
    if ceiling <= 0:
        return sc.result(f"Even for free that wouldn't leave your target on {rate['name']}. Skip it or find a cheaper way to post.",
                         "Most to pay", sc.gbp(0), "not worth buying at that price", [("Left after fees and postage", sc.gbp(base["net"]))],
                         [sc.HONEST])
    rows = [("Expected sale price", sc.gbp(resale)), ("Left after fees and postage", sc.gbp(base["net"])),
            ("A third of the sale price", sc.gbp(round(resale / 3, 2)))]
    return sc.result(f"Pay no more than {sc.gbp(round(ceiling, 2))} to hit your target. Fees change, check the site.", "Most to pay",
                     sc.gbp(round(ceiling, 2)), f"to still profit when selling on {rate['name']}", rows,
                     ["This assumes it sells at the price you gave. Check sold prices, not asking prices.", sc.HONEST])


def seasonal(settings: Settings, args: dict):
    month = int(sc.number(args["month"], "month number", top=12)) if args.get("month") else sc.today().month
    nxt = month % 12 + 1
    return sc.guide(f"Seasonal ideas for month {month}.", "What sells this time of year",
                    [("This month", SEASONS[month]), ("Buy or list for next month", SEASONS[nxt])],
                    "General UK patterns only, not a forecast. Check sold prices for the items you have.")


def seller_scams(settings: Settings, args: dict):
    return sc.guide("Common scams that catch online sellers.", "Seller scams to watch for", SCAMS,
                    "If something feels off, stop and use the platform's own help. Never give out bank logins.")


def records_checklist(settings: Settings, args: dict):
    return screen.Shown("Records worth keeping as a seller.", screen.card(
        "list", "Seller records", "sellercalc-records", items=[{"label": r} for r in RECORDS], text=CHECK))


def returns_rules(settings: Settings, args: dict):
    return sc.guide("How returns rights differ for private and business sellers.", "Returns and refunds", RETURNS, CHECK)


def platform_guide(settings: Settings, args: dict):
    key = platform_key(args.get("platform"))
    good, fees, watch = PLATFORM_GUIDE[key]
    table = sc.rates(settings)
    prefix = {"shop": "own_shop"}.get(key, key)
    names = [r["name"] for r in table.values() if r["key"].startswith(prefix)]
    return sc.guide(f"{key.title()} in brief.", key.title(), [("Good for", [good]), ("Fees", [fees, "See the fee table for: " + ", ".join(names)]),
                                                          ("Watch out", [watch])], sc.HONEST)


def glossary(settings: Settings, args: dict):
    term = sc.clean(args.get("term")).lower()
    hits = [g for g in GLOSSARY if term in g[0].lower()] if term else GLOSSARY
    return sc.guide("Seller words in plain English.", "Seller glossary", hits or GLOSSARY)


def tool_definitions() -> list[dict]:
    return [{
        "name": "sellercalc_guide",
        "description": "Plain-words guides for online sellers and resellers in the UK: HMRC reporting of platform sellers (30+ sales or "
                       "about 1,700 pounds a year), sourcing tips and notes (car boots, charity shops), the most to pay for stock, "
                       "seasonal ideas, seller scams, records to keep, returns rules, platform summaries, glossary (margin vs markup). "
                       "General information, check GOV.UK. Set confirmed only after the user agrees to remove_source.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "kind": {"type": "string", "description": "car boot, charity shop, house clearance, online auction or general."},
                "platform": {"type": "string"}, "place": {"type": "string"}, "date": {"type": "string"},
                "spent": {"type": "number"}, "worth": {"type": "number", "description": "What you hope to resell it for."},
                "count": {"type": "number", "description": "Items bought."}, "note": {"type": "string"},
                "price": {"type": "number", "description": "max_buy: expected resale price."},
                "ship_charged": {"type": "number"}, "ship_cost": {"type": "number"}, "packaging": {"type": "number"},
                "extra_pct": {"type": "number"}, "target_profit": {"type": "number"}, "target_margin_pct": {"type": "number"},
                "month": {"type": "number", "description": "1 to 12."}, "term": {"type": "string"},
                "source_id": {"type": "string"}, "confirmed": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


def run_tool(name: str, args: dict, settings: Settings, http=None):
    handlers = {a: globals()[a] for a in ACTIONS}
    action = args.get("action")
    if action not in handlers:
        raise ValueError("Which seller guide? " + ", ".join(ACTIONS))
    return handlers[action](settings, args)
