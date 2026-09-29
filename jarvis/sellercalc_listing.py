"""Listing helpers for resale items: title and keyword drafts, a description draft, photo, listing, condition and packing
checklists, a sold-price comparison and saved drafts. Drafts only: nothing is ever posted or sent to a marketplace.

Results pop up as lists, text or sellercalc-guide cards. Drafts are saved in sellercalc-drafts.json in the memory folder.
"""

import statistics

import screen
import sellercalc_store as sc
from config import Settings

NAMES = {"sellercalc_listing"}
ACTIONS = ["title", "keywords", "description", "photo_checklist", "listing_checklist", "condition_guide", "packing_checklist",
           "price_research", "save_draft", "drafts", "delete_draft"]
TITLE_LIMITS = {"etsy": 140, "ebay": 80, "vinted": 100, "depop": 65, "facebook": 100, "amazon": 200, "shop": 70}
TAG_LIMITS = {"etsy": (13, 20), "depop": (5, 30), "ebay": (10, 30), "vinted": (8, 30), "facebook": (8, 30), "amazon": (7, 50), "shop": (10, 30)}
PHOTOS = [
    "Shoot in daylight near a window, with no flash and no filters.",
    "A plain, uncluttered background: a white sheet or a clean floor.",
    "Front, back, side and any label, tag or size sticker.",
    "Close-ups of every flaw, mark, scuff or missing part, so the buyer isn't surprised.",
    "Something for scale (a ruler or a coin) for small items; measure and write sizes in the description.",
    "Show it working for electricals (screen on, lights on), and the serial or model number.",
    "The first photo is the thumbnail: make it the clearest and brightest.",
    "Wipe the lens, keep the phone level, and don't crop off the corners.",
    "Include the box, extras and accessories in one shot.",
    "Never use pictures from other listings: use your own photos of the actual item.",
]
CHECKLISTS = {
    "etsy": ["Title with the key words first", "All 13 tags used", "Category and attributes filled in", "Materials listed honestly",
             "Weight and dimensions for postage", "Processing time you can really meet", "Shipping profile and returns policy set",
             "Only handmade, vintage (20+ years) or craft supplies are allowed: check Etsy's rules"],
    "ebay": ["Title uses all 80 characters sensibly", "Item specifics filled in (brand, size, colour)", "Checked sold listings for price",
             "Condition chosen honestly", "Weight and package size entered", "Postage option and handling time set",
             "Returns policy set", "Not a banned or restricted item"],
    "vinted": ["Clear title with brand and size", "Category, brand, size, condition and colour picked", "Photos in daylight, first one clearest",
               "Weight of parcel picked correctly (it sets the postage)", "Price checked against similar sold items",
               "No links or contact details in the description"],
    "depop": ["Photos square and clear", "Description with brand, size, measurements and condition", "Up to 5 hashtags that match the item",
              "Postage option and parcel size chosen", "Price checked against similar items"],
    "facebook": ["Photos and a plain title", "Price and condition", "Pick-up area or shipping choice", "Meet in a public place",
                 "Don't share bank details or click links buyers send you"],
    "amazon": ["Brand approval or category approval if needed", "Product ID matches the item", "Condition notes",
               "Prep and labelling rules if using FBA", "Fees checked in Amazon's calculator"],
    "shop": ["Product photos and description", "Clear postage costs and delivery times", "Returns policy and contact details",
             "Business name and address shown (UK consumer rules)", "Card fees and plan cost included in the price"],
}
CONDITIONS = [
    ("New with tags or box", ["Never worn or used, still has tags or the original box.", "Only say this if it is true."]),
    ("New without tags", ["Unworn or unused but tags or packaging are gone."]),
    ("Excellent", ["Used once or twice and looks like new. No marks, no signs of wear."]),
    ("Good", ["Used with light wear only: a little fading, tiny scuffs. Say where."]),
    ("Fair or well used", ["Clear wear, marks or small faults. Photograph and describe every one."]),
    ("For parts or repair", ["Doesn't work fully. Say exactly what is wrong."]),
]
PACKING = [
    "Weigh and measure the packed parcel, and pick the right postage band.",
    "Use a clean, strong box or a padded bag; reuse boxes only if old labels are removed.",
    "Wrap fragile things in bubble wrap and leave space so nothing rattles.",
    "Put clothes in a poly bag first, then the outer bag, in case of rain.",
    "Seal with proper tape, and include a note with your order number if you like.",
    "Take a photo of the packed parcel and the label before you seal it.",
    "Keep proof of postage until the buyer confirms it arrived (a receipt or tracking number).",
    "For higher-value items use a tracked or signed-for service; cheap untracked post is hard to claim on.",
    "Post within the time you promised.",
]
SAFETY = "Say only what is true about the item and its condition. Don't use a brand name for something that isn't that brand."


def platform_key(value) -> str:
    text = sc.clean(value).lower()
    if "shopify" in text or "own" in text or "website" in text:
        return "shop"
    return next((key for key in TITLE_LIMITS if key in text), "ebay")


def _cut(words: list[str], limit: int) -> str:
    words = [w for w in words if w]
    while words and len(" ".join(words)) > limit:
        words.pop()
    return " ".join(words)


def _drop_caps(text: str) -> str:
    return " ".join(w if not (len(w) > 3 and w.isupper()) else w.capitalize() for w in text.split())


def title(settings: Settings, args: dict):
    plat = platform_key(args.get("platform"))
    limit = TITLE_LIMITS[plat]
    item = sc.need(args.get("item"), "item", 60)
    parts = {k: sc.clean(args.get(k), 40) for k in ("brand", "colour", "size", "material", "condition")}
    extras = [sc.clean(e, 30) for e in (args.get("keywords") or [])[:6] if sc.clean(e)]
    plain = _cut([parts["brand"], item, parts["colour"], parts["size"] and f"size {parts['size']}", parts["condition"]], limit)
    rich = _cut([parts["brand"], item, parts["material"], parts["colour"], parts["size"] and f"size {parts['size']}", *extras,
                 parts["condition"]], limit)
    short = _cut([parts["brand"], item, parts["size"] and f"size {parts['size']}"], min(limit, 60))
    options, seen = [], set()
    for label, text in (("Keyword-rich", rich), ("Plain", plain), ("Short", short)):
        text = _drop_caps(text)
        if text and text.lower() not in seen:
            seen.add(text.lower())
            options.append((label, text))
    listed = [{"label": f"{label} ({len(text)} of {limit}): {text}", "say": f"Save a listing draft with the title {text}"}
              for label, text in options]
    return screen.Shown(f"Here are {len(options)} title drafts for {plat.title()}. Nothing is posted.", screen.card(
        "list", f"Title drafts for {plat.title()}", "sellercalc-titles", items=listed,
        text=f"{SAFETY} Put the words a buyer would type first. Limit here: {limit} characters."))


def keywords(settings: Settings, args: dict):
    plat = platform_key(args.get("platform"))
    count, size = TAG_LIMITS[plat]
    item = sc.need(args.get("item"), "item", 60).lower()
    mods = [sc.clean(args.get(k), 30).lower() for k in ("brand", "colour", "material", "style", "occasion") if sc.clean(args.get(k))]
    mods += [sc.clean(e, 30).lower() for e in (args.get("keywords") or [])[:8] if sc.clean(e)]
    tags = [item] + [f"{m} {item}" for m in mods] + [f"{item} {w}" for w in ("gift", "second hand", "pre loved")]
    tags += [f"{sc.clean(args.get('size'))} {item}".lower()] if args.get("size") else []
    out, seen = [], set()
    for tag in tags:
        if len(tag) <= size and tag not in seen:
            seen.add(tag)
            out.append(tag)
    out = out[:count]
    if plat == "depop":
        out = ["#" + t.replace(" ", "") for t in out]
    return screen.Shown(f"{len(out)} keyword ideas for {plat.title()}. Nothing is posted.", screen.card(
        "list", f"Keywords for {plat.title()}", "sellercalc-keywords", items=[{"label": t} for t in out],
        text=f"{plat.title()} allows about {count} tags or keywords of up to {size} characters. I can't see what buyers search "
             "for, so check what similar items that sold used. Only use words that describe your item."))


def description(settings: Settings, args: dict):
    item = sc.need(args.get("item"), "item", 60)
    facts = [("Brand", args.get("brand")), ("Size", args.get("size")), ("Colour", args.get("colour")),
             ("Material", args.get("material")), ("Measurements", args.get("measurements")), ("Condition", args.get("condition"))]
    lines = [f"{sc.clean(args.get('brand'), 40)} {item}".strip(), ""]
    lines += [f"{k}: {sc.clean(v, 80)}" for k, v in facts if sc.clean(v)]
    flaws = sc.clean(args.get("flaws"), 200)
    lines += ["", f"Flaws: {flaws}" if flaws else "Flaws: [add any marks, wear or faults here, or say none seen]",
              "Please look at all the photos: they show the actual item.", "From a smoke-free, pet-free home. [delete if not true]"]
    post = sc.clean(args.get("postage_note"), 120)
    lines += ["", post or "Posted within 2 working days. [edit to what you can really do]"]
    text = "\n".join(lines)
    return screen.Shown("Here's a description draft to edit. Nothing is posted.", screen.card(
        "text", f"Description draft: {item}", "sellercalc-description", text=text,
        buttons=[{"label": "Save as draft", "say": f"Save a listing draft for {item} with that description."}]))


def photo_checklist(settings: Settings, args: dict):
    extra = {"electrical": ["Working shot, plus the model plate and any charger."], "clothes": ["A flat lay, plus the size and care labels.",
             "Measure across the chest or waist and length; write them in."], "shoes": ["Soles, insides and heel wear."]}
    kind = sc.clean(args.get("item")).lower()
    more = next((v for k, v in extra.items() if k in kind or (k == "clothes" and any(w in kind for w in ("shirt", "dress", "jeans", "coat", "top")))), [])
    return screen.Shown("Photo checklist for a sale listing.", screen.card(
        "list", "Photo checklist", "sellercalc-photos", items=[{"label": p} for p in PHOTOS + more]))


def listing_checklist(settings: Settings, args: dict):
    plat = platform_key(args.get("platform"))
    return screen.Shown(f"Checklist before you list on {plat.title()}.", screen.card(
        "list", f"Before listing on {plat.title()}", "sellercalc-listing-" + plat, items=[{"label": c} for c in CHECKLISTS[plat]],
        text="Platform rules change, so check the site's own seller help."))


def condition_guide(settings: Settings, args: dict):
    return sc.guide("How to describe condition honestly.", "Condition wording",
                    [(name, lines) for name, lines in CONDITIONS], "Overstating condition causes returns and bad reviews. "
                    "When in doubt, pick the lower grade and show the flaws in photos.")


def packing_checklist(settings: Settings, args: dict):
    return screen.Shown("Packing and posting checklist.", screen.card(
        "list", "Pack and post", "sellercalc-packing", items=[{"label": p} for p in PACKING],
        text="Good packing and proof of postage are what protect you if a buyer says it never came."))


def price_research(settings: Settings, args: dict):
    prices = [sc.number(p, "sold price") for p in (args.get("prices") or [])[:30]]
    if len(prices) < 3:
        return sc.guide("Look up at least three sold prices, then give them to me.", "Price research", [
            ("Find real sold prices", ["eBay: search the item, then tick Sold items in the filters.",
                                      "Vinted and Depop: look at similar items marked as sold, if shown.",
                                      "Match brand, size, condition and completeness."]),
            ("Then", ["Say the sold prices, for example 12, 14 and 16, and I'll work out a sensible asking price."])],
            "Asking prices are only hopes; sold prices show what people really paid.")
    mid = statistics.median(prices)
    ask = round(mid * 1.10 * 2) / 2
    return sc.result(f"Similar items sold around {sc.gbp(mid)}; asking {sc.gbp(ask)} leaves room to haggle.", "Price research",
                     sc.gbp(ask), "suggested asking price", [("Sold prices seen", ", ".join(sc.gbp(p) for p in prices)),
                     ("Middle price", sc.gbp(mid)), ("Lowest", sc.gbp(min(prices))), ("Highest", sc.gbp(max(prices)))],
                     ["The ask is about 10% over the middle price so an offer still lands near it. Adjust for your item's condition."])


def _drafts(settings: Settings) -> list[dict]:
    return [d for d in sc.load(settings, sc.DRAFTS, []) if isinstance(d, dict)]


def save_draft(settings: Settings, args: dict):
    rows = _drafts(settings)
    if len(rows) >= 200:
        raise ValueError("You have 200 drafts saved; delete some first.")
    text = sc.need(args.get("title") or args.get("item"), "title", 140)
    draft = {"id": max([d["id"] for d in rows] + [0]) + 1, "title": text, "platform": sc.clean(args.get("platform"), 30),
             "price": sc.number(args["price"], "price") if args.get("price") is not None else None,
             "description": sc.clean(args.get("text"), 2000), "saved": sc.today().isoformat()}
    rows.append(draft)
    sc.save(settings, sc.DRAFTS, rows)
    return f"Saved listing draft {draft['id']}: {text}. It stays on this PC; nothing is posted."


def drafts(settings: Settings, args: dict):
    rows = _drafts(settings)
    if not rows:
        raise ValueError("No listing drafts saved yet.")
    return screen.Shown(f"You have {len(rows)} listing drafts.", screen.card(
        "table", "Listing drafts", "sellercalc-drafts", columns=["#", "Title", "Platform", "Price", "Saved"],
        rows=[[str(d["id"]), d["title"], d["platform"], sc.gbp(d["price"]) if d["price"] else "", d["saved"]] for d in rows[-30:][::-1]]))


def delete_draft(settings: Settings, args: dict):
    rows = _drafts(settings)
    ref = str(args.get("draft_id") or "").lstrip("#")
    hit = next((d for d in rows if str(d["id"]) == ref), None)
    if hit is None:
        raise ValueError("Which draft? Say its number.")
    if args.get("confirmed") is not True:
        return f"That deletes draft {hit['id']}, {hit['title']}. Say yes to confirm."
    sc.save(settings, sc.DRAFTS, [d for d in rows if d is not hit])
    return f"Deleted draft {hit['id']}."


def tool_definitions() -> list[dict]:
    return [{
        "name": "sellercalc_listing",
        "description": "Help writing resale listings (drafts only, nothing is posted): listing title drafts and keywords for eBay, "
                       "Vinted, Etsy, Depop, Facebook, description draft, photo checklist, before-you-list checklist per platform, "
                       "honest condition wording, packing and posting checklist, price research from sold prices, saved drafts. "
                       "Set confirmed only after the user agrees to delete_draft.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "platform": {"type": "string", "description": "ebay, vinted, etsy, depop, facebook, amazon or shop."},
                "item": {"type": "string", "description": "What it is, e.g. denim jacket."},
                "brand": {"type": "string"}, "colour": {"type": "string"}, "size": {"type": "string"},
                "material": {"type": "string"}, "condition": {"type": "string"}, "style": {"type": "string"},
                "occasion": {"type": "string"}, "measurements": {"type": "string"}, "flaws": {"type": "string"},
                "postage_note": {"type": "string"}, "keywords": {"type": "array", "items": {"type": "string"}},
                "prices": {"type": "array", "items": {"type": "number"}, "description": "Sold prices of similar items."},
                "title": {"type": "string", "description": "save_draft: the title."}, "price": {"type": "number"},
                "text": {"type": "string", "description": "save_draft: the description."},
                "draft_id": {"type": "string"}, "confirmed": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


def run_tool(name: str, args: dict, settings: Settings, http=None):
    handlers = {a: globals()[a] for a in ACTIONS}
    action = args.get("action")
    if action not in handlers:
        raise ValueError("Which listing help? " + ", ".join(ACTIONS))
    return handlers[action](settings, args)
