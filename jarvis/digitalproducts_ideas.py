"""Digital products part 1: the idea list and validator checklist, the product planner, the catalogue with status
(idea, making, listed, retired) and the version log.

Everything is stored in digitalproducts.json in the memory folder. Nothing is uploaded or sold by Alfred; "listed"
just means the user has listed it somewhere themselves.
"""

import csv
import io

import digitalproducts_store as store
import homestore as hs
import screen
from config import Settings

screen.EXTRA_KINDS.add("digitalproducts-catalogue")

ACTIONS = ["idea_add", "idea_list", "idea_edit", "idea_remove", "idea_brainstorm", "idea_validate", "validate_tick",
           "idea_rank", "product_plan", "product_show", "catalogue_show", "status_set", "product_edit",
           "product_remove", "catalogue_export", "catalogue_stats", "version_log", "version_list"]
CHECKS = ["I can say who it is for in one sentence.",
          "It solves one clear, small problem.",
          "I have seen people ask for it, or buy something similar.",
          "I can make a first version in a weekend or less.",
          "I have looked at what similar products sell for.",
          "Mine is different in one way I can name.",
          "I have the right to sell every word, picture and font in it.",
          "I would be happy to answer customers' questions about it."]
ANGLES = ["a one-page {n} checklist", "a weekly {n} planner (printable)", "a {n} worksheet with prompts",
          "a beginner's {n} ebook in 10 short chapters", "a {n} tracker (habit or progress sheet)",
          "a pack of 30 {n} prompts", "a {n} budget or cost sheet", "a {n} template people fill in",
          "a mini course outline: {n} in 5 lessons", "a set of {n} phone wallpapers"]
PLAN = {
    "ebook": ("Chapters written and proof-read; a cover; a PDF export", "ebook_skeleton, cover_make, file_pdf"),
    "printable planner": ("Print-ready pages in A4 and Letter; a preview picture", "planner_make, cover_make"),
    "checklist": ("One clear page, checkboxes, a title and your name", "checklist_make"),
    "template": ("The blank template, a filled-in example, a how-to-use note", "csv_template, worksheet_make"),
    "worksheet": ("Prompts or questions with space to write; an answer key if useful", "worksheet_make"),
    "prompt pack": ("20 to 50 tested prompts grouped by job, with a short how-to", "prompt_pack"),
    "guide": ("A focused how-to with steps, screenshots or pictures you own, and a summary page",
              "ebook_skeleton"),
    "course outline": ("Lessons with a goal, key points and an exercise each", "course_outline"),
    "wallpaper pack": ("A set of matching phone or desktop pictures in the right sizes", "wallpaper_make"),
    "habit tracker": ("A month grid with room for your habits", "habit_tracker_make"),
    "budget sheet": ("A print or spreadsheet with income, spending and a summary", "budget_sheet_make, csv_template"),
    "spreadsheet": ("A CSV or spreadsheet with headings and example rows", "csv_template"),
}
STATUS_HINT = {"idea": "not started", "making": "being made", "listed": "listed for sale by you",
               "retired": "no longer sold"}


def _fmt(value) -> str:
    text = hs.clean(value, 40).lower()
    if not text:
        return ""
    return hs.find(store.FORMATS, text) or text


def _status(value, default: str = "idea") -> str:
    text = hs.clean(value).lower() or default
    if text not in store.STATUSES:
        raise ValueError("The status must be one of " + ", ".join(store.STATUSES) + ".")
    return text


def _price(value):
    return None if value in (None, "") else round(hs.number(value, "price", 0, 10000), 2)


# ---- Ideas -----------------------------------------------------------------------------------------

def _idea_line(i: dict) -> str:
    return f"{i['id']}. {i['idea']} ({len(i['checks'])}/{len(CHECKS)} checks)"



def idea_add(settings: Settings, args: dict) -> str:
    data = store.load(settings)
    idea = hs.need(args.get("idea"), "idea", 160)
    row = {"id": store.new_id(data), "idea": idea, "format": _fmt(args.get("format")),
           "niche": hs.clean(args.get("niche"), 60), "note": hs.clean(args.get("note"), 300), "checks": []}
    store.put(data["ideas"], row)
    store.save(settings, data)
    return f"Saved idea {row['id']}: {idea}. Say validate it to run the checklist."


def _ideas_card(data: dict, title: str = "Product ideas") -> screen.Shown:
    items = [{"label": _idea_line(i), "say": f"Validate product idea {i['id']}."} for i in data["ideas"]]
    return screen.Shown(f"You have {len(items)} product ideas." if items else "No product ideas yet.",
                        screen.card("list", title, "digitalproducts-ideas", items=items or [{"label": "Nothing yet"}]))


def idea_list(settings: Settings, args: dict) -> screen.Shown:
    return _ideas_card(store.load(settings))


def idea_edit(settings: Settings, args: dict) -> str:
    data = store.load(settings)
    row = store.by_id(data["ideas"], args, "idea")
    for key, limit in (("idea", 160), ("niche", 60), ("note", 300)):
        if args.get(key):
            row[key] = hs.clean(args[key], limit)
    if args.get("format"):
        row["format"] = _fmt(args["format"])
    store.save(settings, data)
    return f"Updated idea {row['id']}."


def idea_remove(settings: Settings, args: dict) -> str:
    data = store.load(settings)
    row = store.by_id(data["ideas"], args, "idea")
    if not args.get("confirmed"):
        return store.confirm_needed(f"idea {row['id']}, {row['idea']}")
    data["ideas"].remove(row)
    store.save(settings, data)
    return f"Removed the idea {row['idea']}."


def idea_brainstorm(settings: Settings, args: dict) -> screen.Shown:
    niche = hs.need(args.get("niche"), "topic or niche", 40)
    ideas = [a.format(n=niche) for a in ANGLES]
    items = [{"label": t, "say": f"Save a product idea: {t}."} for t in ideas]
    return screen.Shown(f"Ten starting points for {niche}. Tap one to save it, then validate it before you make it.",
                        screen.card("list", f"Ideas for {niche}", f"digitalproducts-brainstorm-{store.slug(niche)}",
                                    items=items))


def _checklist(row: dict) -> screen.Shown:
    items = [{"label": c, "done": n in row["checks"],
              "say": f"Tick item {n} of the checklist for product idea {row['id']}."}
             for n, c in enumerate(CHECKS, 1)]
    got = len(row["checks"])
    verdict = ("Looks worth a first small version." if got >= 7 else
               "Promising, but sort out the unticked ones first." if got >= 4 else
               "Not ready yet: look at a few similar products and think about who it is for.")
    return screen.Shown(f"{row['idea']}: {got} of {len(CHECKS)} ticked. {verdict} A ticked box is your own honest "
                        "answer; it is not a promise that it will sell.",
                        screen.card("list", f"Validate: {row['idea']}"[:80], f"digitalproducts-validate-{row['id']}",
                                    items=items, checks=True, text=f"{got}/{len(CHECKS)}. {verdict}"))


def idea_validate(settings: Settings, args: dict) -> screen.Shown:
    return _checklist(store.by_id(store.load(settings)["ideas"], args, "idea"))


def validate_tick(settings: Settings, args: dict) -> screen.Shown:
    data = store.load(settings)
    row = store.by_id(data["ideas"], args, "idea")
    nums = [int(hs.number(n, "checklist item", 1, len(CHECKS))) for n in (args.get("items") or [args.get("item")])]
    for n in nums:
        if args.get("done") is False:
            row["checks"] = [c for c in row["checks"] if c != n]
        elif n not in row["checks"]:
            row["checks"].append(n)
    store.save(settings, data)
    return _checklist(row)


def idea_rank(settings: Settings, args: dict) -> screen.Shown:
    data = store.load(settings)
    ranked = sorted(data["ideas"], key=lambda i: -len(i["checks"]))
    rows = [[i["id"], i["idea"], f"{len(i['checks'])}/{len(CHECKS)}", i["format"] or "-"] for i in ranked]
    return screen.Shown("Your ideas with the most ticks first." if rows else "No ideas to rank yet.",
                        screen.card("table", "Ideas ranked", "digitalproducts-rank",
                                    columns=["No.", "Idea", "Checks", "Format"], rows=rows))


# ---- Products and the catalogue ----------------------------------------------------------------------

def product_plan(settings: Settings, args: dict) -> screen.Shown:
    data = store.load(settings)
    name, fmt = hs.clean(args.get("name"), 80), _fmt(args.get("format"))
    if args.get("idea_id"):
        idea = store.by_id(data["ideas"], {"id": args["idea_id"]}, "idea")
        fmt = fmt or idea["format"]
        name = hs.clean(args.get("name") or idea["idea"], 80)
        data["ideas"].remove(idea)
    if not name:
        raise ValueError("Which product name?")
    if not fmt:
        raise ValueError("Which format? For example " + ", ".join(store.FORMATS[:6]) + ".")
    row = {"id": store.new_id(data), "name": name, "format": fmt, "status": _status(args.get("status"), "making"),
           "price": _price(args.get("price")), "audience": hs.clean(args.get("audience"), 100),
           "benefits": store.text_list(args.get("benefits")), "keywords": store.text_list(args.get("keywords"), 15, 40),
           "notes": hs.clean(args.get("notes"), 300), "files": [], "added": hs.today().isoformat()}
    store.put(data["products"], row)
    store.save(settings, data)
    return _product_card(row, f"Planned {name} as {row['status']}.")


def _product_card(row: dict, lead: str = "") -> screen.Shown:
    needs, tools = PLAN.get(row["format"], ("A finished file and a preview picture", "the make tool"))
    price = store.gbp(row["price"]) if row["price"] is not None else "not set"
    rows = [["Status", f"{row['status']} ({STATUS_HINT[row['status']]})"], ["Format", row["format"]],
            ["Price", price], ["For", row["audience"] or "not set"], ["Needs", needs], ["Alfred can make", tools],
            ["Files", ", ".join(row["files"]) or "none yet"]]
    return screen.Shown(lead or f"{row['name']}: {row['status']}, {row['format']}, {price}.",
                        screen.card("table", row["name"], f"digitalproducts-product-{row['id']}",
                                    columns=["", ""], rows=rows,
                                    buttons=[{"label": "Listing draft", "say": f"Draft a listing for {row['name']}."},
                                             {"label": "Launch list", "say": f"Start a launch checklist for {row['name']}."}]))


def product_show(settings: Settings, args: dict) -> screen.Shown:
    return _product_card(store.product(store.load(settings), args))


def catalogue_show(settings: Settings, args: dict) -> screen.Shown:
    data = store.load(settings)
    columns = []
    for st in store.STATUSES:
        items = [{"name": p["name"], "format": p["format"],
                  "price": store.gbp(p["price"]) if p["price"] is not None else "",
                  "say": f"Show the product {p['name']}."} for p in data["products"] if p["status"] == st]
        columns.append({"status": st, "items": items})
    counts = ", ".join(f"{c['status']} {len(c['items'])}" for c in columns)
    counts = ", ".join(f"{len(c['items'])} {c['status']}" for c in columns)
    return screen.Shown(f"Your catalogue: {counts}." if data["products"] else "No products in your catalogue yet.",
                        screen.card("digitalproducts-catalogue", "Product catalogue", "digitalproducts-catalogue",
                                    data={"columns": columns}))


def status_set(settings: Settings, args: dict) -> str:
    data = store.load(settings)
    row = store.product(data, args)
    row["status"] = _status(args.get("status"))
    store.save(settings, data)
    return f"{row['name']} is now {row['status']} ({STATUS_HINT[row['status']]})."


def product_edit(settings: Settings, args: dict) -> str:
    data = store.load(settings)
    row = store.product(data, args)
    for key, limit in (("name", 80), ("audience", 100), ("notes", 300)):
        if args.get(key):
            row[key] = hs.clean(args[key], limit)
    if args.get("format"):
        row["format"] = _fmt(args["format"])
    if args.get("price") not in (None, ""):
        row["price"] = _price(args["price"])
    if args.get("benefits"):
        row["benefits"] = store.text_list(args["benefits"])
    if args.get("keywords"):
        row["keywords"] = store.text_list(args["keywords"], 15, 40)
    store.save(settings, data)
    return f"Updated {row['name']}."


def product_remove(settings: Settings, args: dict) -> str:
    data = store.load(settings)
    row = store.product(data, args)
    if not args.get("confirmed"):
        return store.confirm_needed(f"the product {row['name']} from your catalogue (its files stay)")
    data["products"].remove(row)
    data["listings"].pop(str(row["id"]), None)
    data["launch"].pop(str(row["id"]), None)
    store.save(settings, data)
    return f"Removed {row['name']} from the catalogue."


def catalogue_export(settings: Settings, args: dict) -> screen.Shown:
    data = store.load(settings)
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["id", "name", "format", "status", "price_gbp", "audience", "added"])
    for p in data["products"]:
        w.writerow([p["id"], p["name"], p["format"], p["status"], "" if p["price"] is None else p["price"],
                    p["audience"], p["added"]])
    path = store.unique(store.folder(settings, "catalogue"), "catalogue", ".csv")
    path.write_text(out.getvalue(), encoding="utf-8")
    return store.shown_file(settings, path, f"Saved your catalogue of {len(data['products'])} products as a CSV.")


def catalogue_stats(settings: Settings, args: dict) -> screen.Shown:
    data = store.load(settings)
    counts = [sum(1 for p in data["products"] if p["status"] == s) for s in store.STATUSES]
    priced = [p["price"] for p in data["products"] if p["price"] is not None and p["status"] == "listed"]
    text = f"{len(data['products'])} products: " + ", ".join(f"{n} {s}" for n, s in zip(counts, store.STATUSES))
    if priced:
        text += f". Listed average price {store.gbp(sum(priced) / len(priced))}"
    return screen.Shown(text + ".", screen.card("chart", "Products by status", "digitalproducts-stats",
                                                chart={"type": "bar", "labels": store.STATUSES, "values": counts}))


# ---- Versions --------------------------------------------------------------------------------------

def version_log(settings: Settings, args: dict) -> str:
    data = store.load(settings)
    row = store.product(data, args)
    change = hs.need(args.get("change"), "change", 200)
    mine = [v for v in data["versions"] if v["product"] == row["name"]]
    number = hs.clean(args.get("version"), 12) or f"v{len(mine) + 1}.0"
    store.put(data["versions"], {"product": row["name"], "version": number, "change": change,
                                 "date": hs.today().isoformat()})
    store.save(settings, data)
    return f"Logged {row['name']} {number}: {change}."


def version_list(settings: Settings, args: dict) -> screen.Shown:
    data = store.load(settings)
    rows = [v for v in data["versions"] if not args.get("product") or v["product"].lower() == str(args["product"]).lower()
            or str(args["product"]).lower() in v["product"].lower()]
    table = [[v["product"], v["version"], v["date"], v["change"]] for v in rows[-40:]]
    return screen.Shown(f"{len(rows)} updates logged." if rows else "No updates logged yet.",
                        screen.card("table", "Version log", "digitalproducts-versions",
                                    columns=["Product", "Version", "Date", "What changed"], rows=table))


# ---- Tool ------------------------------------------------------------------------------------------

def tool_definitions() -> list[dict]:
    return [{
        "name": "digitalproducts_catalogue",
        "description": "Plan and track digital products the user sells themselves (ebooks, printable planners, "
                      "checklists, templates, worksheets, prompt packs, wallpaper packs). Nothing is uploaded or "
                      "sold by Alfred. action: idea_add (idea, format, niche, note) / idea_list / idea_edit (id) / "
                      "idea_remove (id, confirmed only after yes) / idea_brainstorm (niche) / idea_validate (id) = "
                      "checklist / validate_tick (id, items [numbers], done) / idea_rank; product_plan (name, "
                      "format, idea_id, price, audience, benefits, keywords, status) / product_show (product) / "
                      "catalogue_show = board by status idea, making, listed, retired / status_set (product, "
                      "status) / product_edit (product, ...) / product_remove (product, confirmed only after yes) / "
                      "catalogue_export = CSV / catalogue_stats; version_log (product, change, version) / "
                      "version_list (product). Prices are GBP.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "idea": {"type": "string"},
                "id": {"type": "integer"},
                "idea_id": {"type": "integer"},
                "items": {"type": "array", "items": {"type": "integer"}},
                "done": {"type": "boolean"},
                "name": {"type": "string"},
                "product": {"type": "string", "description": "Product name or number."},
                "format": {"type": "string"},
                "niche": {"type": "string"},
                "note": {"type": "string"},
                "notes": {"type": "string"},
                "price": {"type": "number"},
                "audience": {"type": "string"},
                "benefits": {"type": "array", "items": {"type": "string"}},
                "keywords": {"type": "array", "items": {"type": "string"}},
                "status": {"type": "string", "enum": store.STATUSES},
                "change": {"type": "string"},
                "version": {"type": "string"},
                "confirmed": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"digitalproducts_catalogue"}


def run_tool(name: str, args: dict, settings: Settings, http=None):
    found = {"idea_add": idea_add, "idea_list": idea_list, "idea_edit": idea_edit, "idea_remove": idea_remove,
             "idea_brainstorm": idea_brainstorm, "idea_validate": idea_validate, "validate_tick": validate_tick,
             "idea_rank": idea_rank, "product_plan": product_plan, "product_show": product_show,
             "catalogue_show": catalogue_show, "status_set": status_set, "product_edit": product_edit,
             "product_remove": product_remove, "catalogue_export": catalogue_export,
             "catalogue_stats": catalogue_stats, "version_log": version_log,
             "version_list": version_list}.get(args.get("action"))
    if found is None:
        raise ValueError("I can't do that one.")
    return found(settings, args)
