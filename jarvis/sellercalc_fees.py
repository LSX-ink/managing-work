"""Fee and profit calculators for online selling: Etsy, eBay, Vinted, Depop, Amazon, Facebook Marketplace, your own shop and
print-on-demand. One dated fee table you can override, a platform comparer, a price solver, offers, bundles, discounts and an
editable postage table (Royal Mail and Evri size bands, approximate).

Results pop up as sellercalc-result, sellercalc-compare or sellercalc-fees (frontend/popup-sellercalc.js). Nothing is posted
and no marketplace is contacted; the rates are approximate and dated (sellercalc_store.FEES_CHECKED).
"""

import math

import screen
import sellercalc_store as sc
from config import Settings

NAMES = {"sellercalc_fees"}
ACTIONS = ["fee_table", "set_rate", "reset_rate", "profit", "compare", "target_price", "floor_price", "offer_check",
           "discount", "bundle", "vinted_explain", "amazon_fba_fbm", "pod_price", "shop_monthly", "postage_table",
           "postage_set", "postage_suggest", "postage_reset"]
SIZES = {"small": 2.50, "standard": 3.50, "large": 5.50}


def _sale(args: dict) -> dict:
    """The numbers most calculators share."""
    return {"cost": sc.arg(args, "cost", "what the item cost you", True, 0.0),
            "ship_charged": sc.arg(args, "ship_charged", "postage the buyer pays", True, 0.0),
            "ship_cost": sc.arg(args, "ship_cost", "postage you pay", True, 0.0),
            "packaging": sc.arg(args, "packaging", "packaging cost", True, 0.0),
            "extra_pct": sc.arg(args, "extra_pct", "extra fee percentage (ads)", True, 0.0, top=60)}


def _rows(p: dict, rate: dict, price: float) -> list[tuple[str, str]]:
    rows = [("Sale price", sc.gbp(price))]
    if p["ship_charged"]:
        rows.append(("Postage the buyer pays", sc.gbp(p["ship_charged"])))
    rows.append((f"Platform fees ({sc.fee_line(rate)})", "-" + sc.gbp(p["fee"])))
    if p["cost"]:
        rows.append(("Item cost", "-" + sc.gbp(p["cost"])))
    if p["ship_cost"]:
        rows.append(("Fulfilment" if rate.get("handling") is not None else "Postage you pay", "-" + sc.gbp(p["ship_cost"])))
    if p["packaging"]:
        rows.append(("Packaging", "-" + sc.gbp(p["packaging"])))
    return rows


def _note(rate: dict) -> str:
    return f"{rate['name']}: {rate['note']}"


def fee_table(settings: Settings, args: dict):
    table = sc.rates(settings)
    if args.get("platform"):
        rate = sc.platform(settings, args["platform"])
        rows = [("Fees", sc.fee_line(rate)), ("Percentage also on postage", "yes" if rate.get("on_ship") else "no"),
                ("Rates checked", sc.FEES_CHECKED)]
        if rate["mine"]:
            rows.append(("You changed", ", ".join(rate["mine"])))
        if rate.get("buyer_pct"):
            rows.append(("Buyer pays extra", f"{sc.pct_text(rate['buyer_pct'])} + {sc.gbp(rate['buyer_fixed'])}"))
        return sc.result(f"{rate['name']}: {sc.fee_line(rate)}. Fees change, check the site.", f"{rate['name']} fees",
                         sc.fee_line(rate), f"approximate, checked {sc.FEES_CHECKED}", rows, [rate["note"], sc.HONEST])
    rows = [{"key": r["key"], "name": r["name"], "fee": sc.fee_line(r), "mine": r["mine"], "note": r["note"],
             "say": f"Show the {r['name']} fee details."} for r in table.values()]
    return screen.Shown(f"Fee table, last looked over {sc.FEES_CHECKED}. Fees change, check the site.", screen.card(
        sc.FEES, "Platform fees", "sellercalc-fees", data={"checked": sc.FEES_CHECKED, "rows": rows, "note": sc.HONEST},
        buttons=[{"label": "Compare platforms", "say": "Compare my item across every selling platform."}]))


def set_rate(settings: Settings, args: dict):
    rate = sc.platform(settings, args.get("platform"))
    new = {}
    for key, what, top in (("pct", "percentage fee", 60), ("fixed", "fixed fee per sale", 50), ("handling", "fulfilment fee", 50)):
        if args.get(key) is not None:
            new[key] = sc.number(args[key], what, allow_zero=True, top=top)
    if not new:
        raise ValueError("Give the new percentage (pct), fixed fee per sale (fixed) or fulfilment fee (handling).")
    data = sc.user_settings(settings)
    data.setdefault("rates", {}).setdefault(rate["key"], {}).update(new)
    sc.save(settings, sc.SETTINGS, data)
    now = sc.platform(settings, rate["key"])
    return f"Saved your own {rate['name']} rate: {sc.fee_line(now)}. I'll use it in every calculation."


def reset_rate(settings: Settings, args: dict):
    data = sc.user_settings(settings)
    if str(args.get("platform", "")).lower() == "all":
        data["rates"] = {}
        sc.save(settings, sc.SETTINGS, data)
        return "All fee rates are back to the built-in table."
    rate = sc.platform(settings, args.get("platform"))
    if not data.get("rates", {}).pop(rate["key"], None):
        return f"You hadn't changed the {rate['name']} rate."
    sc.save(settings, sc.SETTINGS, data)
    return f"The {rate['name']} rate is back to the built-in {sc.fee_line(sc.platform(settings, rate['key']))}."


def profit(settings: Settings, args: dict):
    rate = sc.platform(settings, args.get("platform"))
    price = sc.arg(args, "price", "selling price")
    s = _sale(args)
    p = sc.profit_on(rate, price, **s)
    notes = [_note(rate), sc.HONEST]
    if rate.get("local") or rate.get("buyer_ship"):
        notes.insert(0, "Postage isn't counted here: the buyer arranges or pays it.")
    if p["net"] < 0:
        notes.insert(0, "That sale loses money.")
    rows = _rows(p, rate, price) + [("Profit margin", f"{p['margin']}%")]
    if p["roi"] is not None:
        rows.append(("Return on what you spent", f"{p['roi']}%"))
    return sc.result(f"On {rate['name']} you'd keep about {sc.gbp(p['net'])}. Fees change, check the site.",
                     f"Profit on {rate['name']}", sc.gbp(p["net"]), "estimated profit on this sale", rows, notes)


def compare(settings: Settings, args: dict):
    price = sc.arg(args, "price", "selling price")
    s = _sale(args)
    table = sc.rates(settings)
    if args.get("platforms"):
        chosen = [sc.platform(settings, n)["key"] for n in args["platforms"]]
        table = {k: v for k, v in table.items() if k in chosen}
    rows = []
    for rate in table.values():
        p = sc.profit_on(rate, price, **s)
        rows.append({"key": rate["key"], "name": rate["name"], "fees": p["fee"], "postage": p["ship_cost"], "net": p["net"],
                     "margin": p["margin"], "note": "postage paid by buyer" if rate.get("buyer_ship") else
                     "pick-up" if rate.get("local") else "", "say": f"Show my profit on {rate['name']} at {sc.gbp(price)}."})
    rows.sort(key=lambda r: -r["net"])
    rows[0]["best"] = True
    best = rows[0]
    return screen.Shown(f"{best['name']} leaves the most, about {sc.gbp(best['net'])}. Fees change, check the site.", screen.card(
        sc.COMPARE, "Same item on every platform", "sellercalc-compare", data={
            "price": price, "cost": s["cost"], "rows": rows, "checked": sc.FEES_CHECKED,
            "note": "Postage you charge and pay is the same on each. " + sc.HONEST}))


def target_price(settings: Settings, args: dict):
    s = _sale(args)
    margin = sc.arg(args, "target_margin_pct", "target margin", True, -1.0, top=95)
    margin = None if margin < 0 else margin
    goal = sc.arg(args, "target_profit", "profit you want", True, -1.0 if margin is not None else None)
    goal = 0.0 if goal < 0 else goal
    label = f"{sc.pct_text(margin)} margin" if margin is not None else f"{sc.gbp(goal)} profit"
    if not args.get("platform"):
        rows = []
        for rate in sc.rates(settings).values():
            price = sc.solve_price(rate, goal, margin, **s)
            rows.append([rate["name"], sc.gbp(price), sc.gbp(sc.profit_on(rate, price, **s)["net"])])
        rows.sort(key=lambda r: float(r[1].replace("£", "").replace(",", "")))
        return screen.Shown(f"To make {label}, {rows[0][0]} needs the lowest price, {rows[0][1]}. Fees change, check the site.",
                            screen.card("table", f"Price needed for {label}", "sellercalc-target", columns=["Platform", "Price", "Profit"],
                                        rows=rows, text=sc.HONEST))
    rate = sc.platform(settings, args["platform"])
    price = sc.solve_price(rate, goal, margin, **s)
    p = sc.profit_on(rate, price, **s)
    return sc.result(f"On {rate['name']}, price it at {sc.gbp(price)} to make {label}. Fees change, check the site.",
                     f"Price for {label}", sc.gbp(price), f"lowest price on {rate['name']}", _rows(p, rate, price)
                     + [("Profit", sc.gbp(p["net"])), ("Margin", f"{p['margin']}%")], [_note(rate), sc.HONEST])


def floor_price(settings: Settings, args: dict):
    rate = sc.platform(settings, args.get("platform"))
    s = _sale(args)
    price = sc.solve_price(rate, 0.0, None, **s)
    p = sc.profit_on(rate, price, **s)
    return sc.result(f"Below {sc.gbp(price)} on {rate['name']} you'd lose money. Fees change, check the site.", "Lowest price",
                     sc.gbp(price), "break-even, no profit at all", _rows(p, rate, price), [_note(rate), sc.HONEST])


def offer_check(settings: Settings, args: dict):
    rate = sc.platform(settings, args.get("platform"))
    price, offer = sc.arg(args, "price", "asking price"), sc.arg(args, "offer", "offer")
    s = _sale(args)
    ask, low = sc.profit_on(rate, price, **s), sc.profit_on(rate, offer, **s)
    floor = sc.solve_price(rate, sc.arg(args, "target_profit", "profit you want", True, 0.0), None, **s)
    counter = max(floor, math.ceil((price + offer) / 2 * 2) / 2)
    verdict = "accept" if offer >= floor else "counter"
    rows = [("Asking price profit", sc.gbp(ask["net"])), (f"Profit at {sc.gbp(offer)}", sc.gbp(low["net"])),
            ("Lowest price for your target", sc.gbp(floor)), ("Suggested counter", sc.gbp(min(counter, price)))]
    text = (f"At {sc.gbp(offer)} you'd keep {sc.gbp(low['net'])}, so " +
            ("that works." if verdict == "accept" else f"counter at about {sc.gbp(min(counter, price))}."))
    return sc.result(text, "Check an offer", sc.gbp(low["net"]), f"profit at {sc.gbp(offer)} on {rate['name']}", rows,
                     ["It's your call: the suggested counter is just halfway, rounded up to 50p.", sc.HONEST])


def discount(settings: Settings, args: dict):
    rate = sc.platform(settings, args.get("platform"))
    price, cut = sc.arg(args, "price", "current price"), sc.arg(args, "discount_pct", "discount percentage", top=95)
    s = _sale(args)
    old, new_price = sc.profit_on(rate, price, **s), round(price * (1 - cut / 100), 2)
    new = sc.profit_on(rate, new_price, **s)
    rows = [("Now", f"{sc.gbp(price)} keeps {sc.gbp(old['net'])}"), (f"{sc.pct_text(cut)} off", f"{sc.gbp(new_price)} keeps {sc.gbp(new['net'])}"),
            ("Profit given up per sale", sc.gbp(round(old["net"] - new["net"], 2)))]
    notes = [sc.HONEST]
    if new["net"] <= 0:
        text = f"At {sc.pct_text(cut)} off you'd make no profit ({sc.gbp(new['net'])})."
        notes.insert(0, "You would need to stay above break-even; try the lowest-price calculator.")
    elif old["net"] <= 0:
        text = f"The sale price keeps {sc.gbp(new['net'])} per sale."
    else:
        more = math.ceil(old["net"] / new["net"] * 100 - 100)
        text = f"Marked down to {sc.gbp(new_price)} you keep {sc.gbp(new['net'])} a sale."
        rows.append(("To earn the same in total", f"about {more}% more sales"))
    return sc.result(text + " Fees change, check the site.", "Discount check", sc.gbp(new_price), f"{sc.pct_text(cut)} off {sc.gbp(price)}",
                     rows, notes)


def bundle(settings: Settings, args: dict):
    rate = sc.platform(settings, args.get("platform"))
    lines = [i for i in args.get("items") or [] if isinstance(i, dict) and i.get("price") is not None]
    if len(lines) < 2:
        raise ValueError("Give at least two items, each with a price and what it cost you.")
    cut = sc.arg(args, "bundle_discount_pct", "bundle discount", True, 0.0, top=95)
    s = _sale(args)
    prices = [sc.number(i["price"], "item price") for i in lines[:20]]
    costs = [sc.number(i.get("cost", 0), "item cost", allow_zero=True) for i in lines[:20]]
    alone = [sc.profit_on(rate, pr, cost, s["ship_charged"], s["ship_cost"], s["packaging"], s["extra_pct"]) for pr, cost in zip(prices, costs)]
    bundle_price = round(sum(prices) * (1 - cut / 100), 2)
    one = sc.profit_on(rate, bundle_price, sum(costs), s["ship_charged"], s["ship_cost"], s["packaging"], s["extra_pct"])
    apart = round(sum(a["net"] for a in alone), 2)
    rows = [("Bundle price", f"{sc.gbp(bundle_price)} ({sc.pct_text(cut)} off {sc.gbp(sum(prices))})"),
            ("Profit as a bundle (one parcel)", sc.gbp(one["net"])), ("Profit selling separately", sc.gbp(apart)),
            ("Difference", sc.gbp(round(one["net"] - apart, 2)))]
    text = (f"The bundle keeps {sc.gbp(one['net'])} against {sc.gbp(apart)} separately. Fees change, check the site.")
    return sc.result(text, "Bundle offer", sc.gbp(one["net"]), f"{len(prices)} items in one parcel", rows,
                     ["One parcel means one lot of postage and one fixed fee, which is where a bundle saves you money.",
                      _note(rate), sc.HONEST])


def vinted_explain(settings: Settings, args: dict):
    rate = sc.platform(settings, "vinted")
    price = sc.arg(args, "price", "item price", default=20.0)
    cost = sc.arg(args, "cost", "what the item cost you", True, 0.0)
    buyer_fee = round(price * rate["buyer_pct"] / 100 + rate["buyer_fixed"], 2)
    rows = [("You list it for", sc.gbp(price)), ("Buyer also pays Buyer Protection (about)", sc.gbp(buyer_fee)),
            ("Buyer pays in total (before postage)", sc.gbp(round(price + buyer_fee, 2))),
            ("Vinted takes from you", sc.gbp(0)), ("You receive", sc.gbp(price))]
    if cost:
        rows.append(("Your profit after item cost", sc.gbp(round(price - cost, 2))))
    return sc.result(f"On Vinted the seller pays no fee: you'd receive {sc.gbp(price)}. The buyer pays the protection fee. "
                     "Fees change, check the site.", "How Vinted fees work", sc.gbp(price), "what you receive", rows,
                     ["The Buyer Protection fee is added to the buyer's bill, so it is not taken from your payout.",
                      "Buyers choose and pay for postage, so remember to price with the whole bill in mind.",
                      rate["note"], sc.HONEST])


def amazon_fba_fbm(settings: Settings, args: dict):
    price = sc.arg(args, "price", "selling price")
    s = _sale(args)
    fba, fbm = sc.platform(settings, "amazon_fba"), sc.platform(settings, "amazon_fbm")
    if args.get("size") and args["size"] in SIZES and args.get("fba_fee") is None:
        fba = {**fba, "handling": SIZES[args["size"]]}
    if args.get("fba_fee") is not None:
        fba = {**fba, "handling": sc.number(args["fba_fee"], "FBA fee", allow_zero=True, top=50)}
    storage = sc.arg(args, "storage", "storage cost per unit", True, 0.0)
    a = sc.profit_on(fba, price, s["cost"], s["ship_charged"], 0.0, s["packaging"], s["extra_pct"])
    b = sc.profit_on(fbm, price, s["cost"], s["ship_charged"], s["ship_cost"], s["packaging"], s["extra_pct"])
    fba_net = round(a["net"] - storage, 2)
    rows = [("FBA: fees + fulfilment", sc.gbp(a["fee"] + a["ship_cost"] + storage)), ("FBA profit", sc.gbp(fba_net)),
            ("FBM: fees + your postage", sc.gbp(b["fee"] + b["ship_cost"])), ("FBM profit", sc.gbp(b["net"]))]
    better = "FBA" if fba_net > b["net"] else "FBM"
    return sc.result(f"On these rough numbers {better} keeps more: FBA {sc.gbp(fba_net)}, FBM {sc.gbp(b['net'])}. Fees change, check the site.",
                     "Amazon FBA or FBM", better, "rough comparison only", rows,
                     ["FBA also has storage fees, removal and return costs, and Amazon's own rules; FBM means you pack and post.",
                      "Fulfilment fees depend on size and weight. Use Amazon's own fee calculator before you buy stock.", sc.HONEST])


def pod_price(settings: Settings, args: dict):
    base = sc.arg(args, "base_cost", "printer's base cost")
    if args.get("markup_pct") is not None:
        cut = sc.number(args["markup_pct"], "your markup percentage", top=500)
        earn = round(base * cut / 100, 2)
        return sc.result(f"With a {sc.pct_text(cut)} markup you'd earn about {sc.gbp(earn)} a sale. Fees change, check the site.",
                         "Print-on-demand markup", sc.gbp(earn), "your share per sale",
                         [("Base cost", sc.gbp(base)), (f"Your markup {sc.pct_text(cut)}", sc.gbp(earn)),
                          ("Buyer sees (before tax and postage)", sc.gbp(round(base + earn, 2)))],
                         ["On Redbubble-style sites the site takes the base price and you earn your markup; details and "
                          "payout rules differ, so check the site.", sc.HONEST])
    rate = sc.platform(settings, args.get("platform") or "own_shop")
    s = {"cost": base, "ship_charged": sc.arg(args, "ship_charged", "postage the buyer pays", True, 0.0),
         "ship_cost": sc.arg(args, "printer_shipping", "printer's postage to the buyer", True, 0.0), "packaging": 0.0,
         "extra_pct": sc.arg(args, "extra_pct", "ad percentage", True, 0.0, top=60)}
    margin = sc.arg(args, "target_margin_pct", "target margin", True, -1.0, top=95)
    goal = sc.arg(args, "target_profit", "profit per item", True, 3.0 if margin < 0 else 0.0)
    price = sc.solve_price(rate, goal, None if margin < 0 else margin, **s)
    p = sc.profit_on(rate, price, **s)
    return sc.result(f"Sell it at {sc.gbp(price)} to keep about {sc.gbp(p['net'])} a sale. Fees change, check the site.",
                     "Print-on-demand price", sc.gbp(price), f"base cost {sc.gbp(base)} plus fees and margin",
                     _rows(p, rate, price) + [("Profit", sc.gbp(p["net"])), ("Margin", f"{p['margin']}%")],
                     ["Printful-style printers bill the base cost and postage per order; you keep the rest after fees.",
                      "Order a sample first so you know the real quality.", _note(rate), sc.HONEST])


def shop_monthly(settings: Settings, args: dict):
    rate = sc.platform(settings, args.get("platform") or "own_shop")
    price, plan = sc.arg(args, "price", "average order price"), sc.arg(args, "plan_cost", "monthly shop plan cost", True, 0.0)
    orders = int(sc.arg(args, "orders", "orders per month", True, 10.0))
    s = _sale(args)
    p = sc.profit_on(rate, price, **s)
    month = round(orders * p["net"] - plan, 2)
    even = math.ceil(plan / p["net"]) if p["net"] > 0 and plan else 0
    rows = [("Profit per order", sc.gbp(p["net"])), ("Orders a month", str(orders)), ("Shop plan and apps", "-" + sc.gbp(plan)),
            ("Profit for the month", sc.gbp(month))]
    if even:
        rows.append(("Orders to cover the plan", str(even)))
    notes = [_note(rate), "Advertising, your time and tax are not included.", sc.HONEST]
    if p["net"] <= 0:
        notes.insert(0, "Each order loses money, so more orders won't help until the price or costs change.")
    return sc.result(f"{orders} orders a month would leave about {sc.gbp(month)}. Fees change, check the site.", "Own shop month",
                     sc.gbp(month), "a guess from your numbers, not a forecast", rows, notes)


def _band_row(b: dict) -> list[str]:
    return [b["name"], f"{b.get('max_g', '?')} g", f"{b.get('max_cm', '?')} cm", sc.gbp(b["price"])]


def postage_table(settings: Settings, args: dict):
    bands = sc.postage_bands(settings)
    mine = bool(sc.user_settings(settings).get("postage"))
    return screen.Shown("Approximate postage bands. Check the carrier for real prices.", screen.card(
        "table", "Postage bands" + (" (edited by you)" if mine else ""), "sellercalc-postage",
        columns=["Service", "Up to", "Longest side", "Price"], rows=[_band_row(b) for b in bands], text=sc.POSTAGE_NOTE,
        buttons=[{"label": "Suggest postage", "say": "Which postage is cheapest for a 600 gram parcel?"}]))


def postage_set(settings: Settings, args: dict):
    bands = sc.postage_bands(settings)
    name = sc.need(args.get("service") or args.get("name"), "postage service")
    key = sc.find([b["name"] for b in bands] + [b["id"] for b in bands], name)
    hit = next((b for b in bands if key in (b["name"], b["id"])), None)
    if hit is None:
        hit = {"id": "custom_" + "".join(c for c in name.lower() if c.isalnum())[:20], "name": name, "max_g": 0, "max_cm": 0, "price": 0}
        bands.append(hit)
        if args.get("max_g") is None or args.get("price") is None:
            raise ValueError(f"{name} is new: give its price and its top weight in grams (max_g).")
    if args.get("price") is not None:
        hit["price"] = sc.number(args["price"], "price", allow_zero=True, top=200)
    if args.get("max_g") is not None:
        hit["max_g"] = int(sc.number(args["max_g"], "top weight in grams", top=40000))
    if args.get("max_cm") is not None:
        hit["max_cm"] = int(sc.number(args["max_cm"], "longest side in cm", top=300))
    data = sc.user_settings(settings)
    data["postage"] = bands
    sc.save(settings, sc.SETTINGS, data)
    return f"Saved {hit['name']} at {sc.gbp(hit['price'])}. Check the carrier for real prices."


def postage_reset(settings: Settings, args: dict):
    if args.get("confirmed") is not True:
        return "That throws away your edited postage prices. Say yes to confirm and I'll reset them."
    data = sc.user_settings(settings)
    data.pop("postage", None)
    sc.save(settings, sc.SETTINGS, data)
    return "Postage bands are back to the built-in table."


def postage_suggest(settings: Settings, args: dict):
    grams = sc.arg(args, "weight_g", "parcel weight in grams", top=40000)
    side = sc.arg(args, "longest_cm", "longest side in cm", True, 0.0, top=300)
    fits = sorted((b for b in sc.postage_bands(settings) if b.get("max_g", 0) >= grams and (not side or b.get("max_cm", 0) >= side)),
                  key=lambda b: b["price"])
    if not fits:
        raise ValueError("Nothing in your postage table takes a parcel that heavy or long. Add a band with postage_set.")
    best = fits[0]
    return sc.result(f"Cheapest fit is {best['name']}, about {sc.gbp(best['price'])}. Prices are approximate.", "Postage suggestion",
                     sc.gbp(best["price"]), best["name"], [(b["name"], sc.gbp(b["price"])) for b in fits[:5]],
                     [sc.POSTAGE_NOTE, "Measure the packed parcel, and include the box and padding in the weight."])


def tool_definitions() -> list[dict]:
    line = {"type": "object", "properties": {"price": {"type": "number"}, "cost": {"type": "number"}}, "required": ["price"],
            "additionalProperties": False}
    return [{
        "name": "sellercalc_fees",
        "description": "Selling fee and profit calculators in GBP for Etsy, eBay (private or business), Vinted (buyer pays the "
                       "fee), Depop, Amazon (FBA or FBM), Facebook Marketplace, own Shopify-style shop and print-on-demand. Fee "
                       "table (dated, overridable), profit on a sale, compare platforms, price to hit target profit or margin, "
                       "lowest price, check an offer, discount, bundle, shop month, Royal Mail and Evri postage bands. "
                       "Estimates only; nothing is posted. Set confirmed only after the user agrees to postage_reset.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "platform": {"type": "string", "description": "etsy, ebay, ebay business, vinted, depop, amazon, fba, facebook, own shop."},
                "platforms": {"type": "array", "items": {"type": "string"}, "description": "Limit compare to these."},
                "price": {"type": "number", "description": "Selling or asking price."}, "cost": {"type": "number", "description": "What the item cost you."},
                "ship_charged": {"type": "number", "description": "Postage the buyer pays."},
                "ship_cost": {"type": "number", "description": "Postage you pay."}, "packaging": {"type": "number"},
                "extra_pct": {"type": "number", "description": "Extra fee percent such as Etsy offsite ads or promoted listings."},
                "target_profit": {"type": "number"}, "target_margin_pct": {"type": "number"},
                "offer": {"type": "number"}, "discount_pct": {"type": "number"}, "bundle_discount_pct": {"type": "number"},
                "items": {"type": "array", "items": line, "description": "Items for a bundle."},
                "pct": {"type": "number", "description": "set_rate: percentage fee."},
                "fixed": {"type": "number", "description": "set_rate: fixed fee per sale."},
                "handling": {"type": "number", "description": "set_rate: fulfilment fee (FBA)."},
                "fba_fee": {"type": "number"}, "size": {"type": "string", "enum": ["small", "standard", "large"]},
                "storage": {"type": "number"}, "base_cost": {"type": "number", "description": "Print-on-demand base cost."},
                "printer_shipping": {"type": "number"}, "markup_pct": {"type": "number", "description": "Redbubble-style markup percent."},
                "plan_cost": {"type": "number", "description": "Monthly shop plan cost."}, "orders": {"type": "number"},
                "service": {"type": "string", "description": "Postage service name."}, "max_g": {"type": "number"},
                "max_cm": {"type": "number"}, "weight_g": {"type": "number"}, "longest_cm": {"type": "number"},
                "confirmed": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


def run_tool(name: str, args: dict, settings: Settings, http=None):
    handlers = {"fee_table": fee_table, "set_rate": set_rate, "reset_rate": reset_rate, "profit": profit, "compare": compare,
                "target_price": target_price, "floor_price": floor_price, "offer_check": offer_check, "discount": discount,
                "bundle": bundle, "vinted_explain": vinted_explain, "amazon_fba_fbm": amazon_fba_fbm, "pod_price": pod_price,
                "shop_monthly": shop_monthly, "postage_table": postage_table, "postage_set": postage_set,
                "postage_suggest": postage_suggest, "postage_reset": postage_reset}
    action = args.get("action")
    if action not in handlers:
        raise ValueError("Which seller calculation? " + ", ".join(ACTIONS))
    return handlers[action](settings, args)
