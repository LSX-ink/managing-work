"""Digital products part 4: bundles and pricing tiers, similar-product price notes typed in by the user, launch
checklists and a refund wording helper.

Prices are the user's own numbers in GBP; nothing is fetched or posted and no marketplace fees are worked out here.
Pricing help is arithmetic plus honest reminders to check what similar products sell for. Nothing is guaranteed.
"""

import statistics

import digitalproducts_store as store
import homestore as hs
import screen
from config import Settings

screen.EXTRA_KINDS.add("digitalproducts-tiers")

ACTIONS = ["bundle_make", "bundle_list", "bundle_remove", "price_tiers", "comps_add", "comps_show", "comps_remove",
           "launch_start", "launch_show", "launch_tick", "launch_remove", "refund_text"]
LAUNCH = [("Before", ["Check every file opens and prints properly", "Proof-read everything once more",
                      "Have a friend try it and tell you what confused them", "Check you own or may use every picture and font"]),
          ("Listing", ["Write the title, description and tags", "Make a cover and a preview picture", "Decide the price after "
                       "looking at similar products", "Add the licence to the download"]),
          ("Launch day", ["List it where you sell", "Tell people you already talk to, without spamming", "Save the link"]),
          ("After", ["Answer questions within a day or two", "Note what people ask for the customer FAQ",
                     "Log any fixes as a new version"])]
TIERS = [("Basic", 1.0, "The main file"), ("Plus", 1.6, "The main file plus extras (for example a second colour or size)"),
         ("Complete", 2.4, "Everything, including bonuses and the commercial licence")]
DISCOUNTS = [15, 25, 35]


def _step(price: float) -> float:
    return max(0.5, round(price * 2) / 2)


# ---- Bundles and tiers -----------------------------------------------------------------------------

def bundle_make(settings: Settings, args: dict) -> screen.Shown:
    data = store.load(settings)
    name = hs.need(args.get("name"), "bundle name", 80)
    picked = [store.product(data, {"product": p}) for p in store.text_list(args.get("products"), 20, 80)]
    if len(picked) < 2:
        raise ValueError("A bundle needs at least two catalogue products.")
    total = sum(p["price"] or 0 for p in picked)
    missing = [p["name"] for p in picked if p["price"] is None]
    row = next((b for b in data["bundles"] if b["name"].lower() == name.lower()), None)
    if row is None:
        row = {"id": store.new_id(data), "name": name}
        store.put(data["bundles"], row)
    row.update({"products": [p["name"] for p in picked], "total": round(total, 2),
                "price": _step(hs.number(args["price"], "price", 0, 10000)) if args.get("price") else None})
    store.save(settings, data)
    opts = [[f"{d}% off", store.gbp(_step(total * (100 - d) / 100))] for d in DISCOUNTS] if total else []
    rows = [[p["name"], store.gbp(p["price"]) if p["price"] is not None else "no price"] for p in picked]
    rows += [["Bought separately", store.gbp(total)]] + opts + ([["Your bundle price", store.gbp(row["price"])]] if row["price"] else [])
    note = f" Add prices for {', '.join(missing)} to compare." if missing else ""
    return screen.Shown(f"Bundle {name}: {len(picked)} products worth {store.gbp(total)} on their own.{note} "
                        + store.PRICE_NOTE,
                        screen.card("table", f"Bundle: {name}"[:80], f"digitalproducts-bundle-{row['id']}",
                                    columns=["Item", "Price"], rows=rows))


def bundle_list(settings: Settings, args: dict) -> screen.Shown:
    bundles = store.load(settings)["bundles"]
    rows = [[b["name"], ", ".join(b["products"]), store.gbp(b["price"]) if b["price"] else "not set"] for b in bundles]
    return screen.Shown(f"{len(rows)} bundles." if rows else "No bundles yet.",
                        screen.card("table", "Bundles", "digitalproducts-bundles", columns=["Bundle", "Contains", "Price"],
                                    rows=rows))


def bundle_remove(settings: Settings, args: dict) -> str:
    data = store.load(settings)
    name = hs.need(args.get("name"), "bundle")
    row = next((b for b in data["bundles"] if b["name"].lower() == name.lower()), None)
    if row is None:
        raise ValueError(f"I can't find a bundle called {name}.")
    if not args.get("confirmed"):
        return store.confirm_needed(f"the bundle {row['name']}")
    data["bundles"].remove(row)
    store.save(settings, data)
    return f"Removed the bundle {row['name']}."


def price_tiers(settings: Settings, args: dict) -> screen.Shown:
    data = store.load(settings)
    row = store.product(data, args) if args.get("product") else None
    base = args.get("price")
    base = row["price"] if base in (None, "") and row else base
    base = hs.number(base, "starting price", 0.5, 10000)
    tiers = [{"name": n, "price": store.gbp(_step(base * m)), "what": what} for n, m, what in TIERS]
    label = row["name"] if row else "your product"
    return screen.Shown(f"Three tiers for {label}, from {tiers[0]['price']} to {tiers[-1]['price']}. These are starting "
                        "points: check what similar products sell for.",
                        screen.card("digitalproducts-tiers", f"Pricing tiers: {label}"[:80], "digitalproducts-tiers",
                                    data={"tiers": tiers, "note": store.PRICE_NOTE}))


# ---- Price comparisons -----------------------------------------------------------------------------

def comps_add(settings: Settings, args: dict) -> str:
    data = store.load(settings)
    row = {"id": store.new_id(data), "product": hs.clean(store.product(data, args)["name"] if args.get("product") else "", 80),
           "price": round(hs.number(args.get("price"), "their price", 0, 10000), 2),
           "note": hs.clean(args.get("note"), 150), "date": hs.today().isoformat()}
    store.put(data["comps"], row)
    store.save(settings, data)
    return f"Noted a similar product at {store.gbp(row['price'])} (number {row['id']})."


def comps_show(settings: Settings, args: dict) -> screen.Shown:
    data = store.load(settings)
    mine = store.product(data, args) if args.get("product") else None
    rows = [c for c in data["comps"] if not mine or c["product"] == mine["name"]]
    if not rows:
        return screen.Shown("No similar prices saved yet. Search the place you plan to sell for a few like yours, "
                            "then tell me their prices.", screen.card("text", "Price comparison", "digitalproducts-comps",
                                                                        text="Add at least three similar products."))
    prices = [c["price"] for c in rows]
    text = (f"{len(rows)} similar products: from {store.gbp(min(prices))} to {store.gbp(max(prices))}, middle "
            f"{store.gbp(statistics.median(prices))}.")
    if mine and mine["price"] is not None:
        text += f" Yours is {store.gbp(mine['price'])}."
    if len(rows) < 3:
        text += " Three or more gives a fairer picture."
    table = [[c["id"], c["price"] and store.gbp(c["price"]), c["note"] or "-"] for c in rows[-30:]]
    return screen.Shown(text + " Prices change, so look again before you list.",
                        screen.card("table", "Similar products", "digitalproducts-comps", columns=["No.", "Price", "Note"],
                                    rows=table, text=text))


def comps_remove(settings: Settings, args: dict) -> str:
    data = store.load(settings)
    row = store.by_id(data["comps"], args, "price note")
    if not args.get("confirmed"):
        return store.confirm_needed(f"price note {row['id']}")
    data["comps"].remove(row)
    store.save(settings, data)
    return "Removed it."


# ---- Launch checklist ------------------------------------------------------------------------------

def _launch_card(row: dict, ident: str, lead: str) -> screen.Shown:
    items = []
    for n, item in enumerate(row["items"], 1):
        items.append({"label": f"{item['group']}: {item['text']}", "done": item["done"],
                      "say": f"Tick launch item {n} for {row['product']}."})
    done = sum(i["done"] for i in row["items"])
    return screen.Shown(lead or f"{done} of {len(items)} launch steps done for {row['product']}.",
                        screen.card("list", f"Launch: {row['product']}"[:80], f"digitalproducts-launch-{ident}", items=items,
                                    checks=True))


def launch_start(settings: Settings, args: dict) -> screen.Shown:
    data = store.load(settings)
    prod = store.product(data, args)
    items = [{"group": g, "text": t, "done": False} for g, ts in LAUNCH for t in ts]
    data["launch"][str(prod["id"])] = {"product": prod["name"], "items": items}
    store.save(settings, data)
    return _launch_card(data["launch"][str(prod["id"])], str(prod["id"]),
                        f"Started a {len(items)}-step launch checklist for {prod['name']}. Alfred does not list or sell anything.")


def _launch(data: dict, args: dict) -> tuple[dict, dict, str]:
    prod = store.product(data, args)
    row = data["launch"].get(str(prod["id"]))
    if not row:
        raise ValueError(f"There is no launch checklist for {prod['name']} yet. Ask me to start one.")
    return prod, row, str(prod["id"])


def launch_show(settings: Settings, args: dict) -> screen.Shown:
    _, row, ident = _launch(store.load(settings), args)
    return _launch_card(row, ident, "")


def launch_tick(settings: Settings, args: dict) -> screen.Shown:
    data = store.load(settings)
    _, row, ident = _launch(data, args)
    for n in [int(hs.number(x, "step number", 1, len(row["items"]))) for x in (args.get("items") or [args.get("item")])]:
        row["items"][n - 1]["done"] = args.get("done") is not False
    store.save(settings, data)
    return _launch_card(row, ident, "")


def launch_remove(settings: Settings, args: dict) -> str:
    data = store.load(settings)
    prod, _, ident = _launch(data, args)
    if not args.get("confirmed"):
        return store.confirm_needed(f"the launch checklist for {prod['name']}")
    del data["launch"][ident]
    store.save(settings, data)
    return "Removed the launch checklist."


def refund_text(settings: Settings, args: dict) -> screen.Shown:
    text = ("Refund and problems policy (draft)\n\nThis is a digital download, so nothing is posted to you.\n"
            "If the file is damaged, will not open or is not what the listing describes, message me and I will fix it "
            "or refund you.\nBecause the file is delivered instantly and cannot be returned, I do not normally refund "
            "for a change of mind once it is downloaded.\nPlease message me first if anything is wrong.\n\n"
            "Check before you use this: where you sell, the site's own refund rules apply, and UK consumer law gives "
            "buyers rights over faulty digital content. See GOV.UK on consumer rights for digital content. This is "
            "general guidance, not legal advice.")
    return screen.Shown("Drafted refund wording for a digital product. Check GOV.UK and the site's rules before you use it.",
                        screen.card("text", "Refund wording (draft)", "digitalproducts-refund", text=text))


# ---- Tool ------------------------------------------------------------------------------------------

def tool_definitions() -> list[dict]:
    return [{
        "name": "digitalproducts_launch",
        "description": "Pricing, bundles and launch help for digital products the user sells (arithmetic on their own "
                      "GBP prices; no guarantees, no marketplace fees, nothing is posted). action: bundle_make (name, "
                      "products [names], price) = value and discount options / bundle_list / bundle_remove (name, "
                      "confirmed only after yes); price_tiers (product or price) = Basic, Plus, Complete; comps_add "
                      "(price of a similar product the user found, product, note) / comps_show (product) = range and "
                      "middle / comps_remove (id, confirmed only after yes); launch_start (product) = launch "
                      "checklist / launch_show / launch_tick (product, items [numbers], done) / launch_remove "
                      "(product, confirmed only after yes); refund_text = draft policy wording.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "name": {"type": "string"},
                "product": {"type": "string"},
                "products": {"type": "array", "items": {"type": "string"}},
                "price": {"type": "number"},
                "note": {"type": "string"},
                "id": {"type": "integer"},
                "items": {"type": "array", "items": {"type": "integer"}},
                "done": {"type": "boolean"},
                "confirmed": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"digitalproducts_launch"}


def run_tool(name: str, args: dict, settings: Settings, http=None):
    found = {"bundle_make": bundle_make, "bundle_list": bundle_list, "bundle_remove": bundle_remove,
             "price_tiers": price_tiers, "comps_add": comps_add, "comps_show": comps_show,
             "comps_remove": comps_remove, "launch_start": launch_start, "launch_show": launch_show,
             "launch_tick": launch_tick, "launch_remove": launch_remove, "refund_text": refund_text}.get(args.get("action"))
    if found is None:
        raise ValueError("I can't do that one.")
    return found(settings, args)
