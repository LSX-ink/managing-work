"""Tech helper, your gadgets: an inventory of devices (model, serial, bought, price) with warranty dates and receipt
files linked by name from the memory folders, a battery and charge log, and software-update reminders.

Stored in techhelp-gadgets.json, techhelp-battery.json and techhelp-updates.json in the memory folder; nothing
goes online. (The general home inventory lives in household-plus; this one is for tech, with model and serial.)
"""

from datetime import date, datetime, timedelta

import homestore as hs
import household_store as hstore
import memory
import screen
import techhelp_store as store
from config import Settings

GADGETS = "techhelp-gadgets.json"
BATTERY = "techhelp-battery.json"
UPDATES = "techhelp-updates.json"
MAX_READINGS = 200
ACTIONS = ["gadget_add", "gadget_list", "gadget_show", "gadget_remove", "gadget_receipt", "receipt_show",
           "gadget_warranty", "gadget_spend", "battery_log", "battery_show", "update_add", "update_due",
           "update_done", "update_remove"]


def tool_definitions() -> list[dict]:
    text = {"type": "string"}
    return [{
        "name": "techhelp_gadgets",
        "description": "The user's tech gadgets, warranties, batteries and updates. gadget_add (name, optional kind, "
                       "model, serial, bought date, price, warranty_months or until date, shop), gadget_list, "
                       "gadget_show (name), gadget_receipt (name, folder + filename of the receipt already in a "
                       "memory folder), receipt_show (name), gadget_warranty (what's out of warranty soon, days "
                       "default 90), gadget_spend (bar chart of what gadgets cost), gadget_remove; battery_log "
                       "(device, percent, optional note) and battery_show (line chart); software update reminders: "
                       "update_add (name, every_days, optional last date), update_due (what needs updating), "
                       "update_done (name), update_remove. Removing needs confirmed true, set only after the user "
                       "confirms.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "name": {**text, "description": "Gadget, device or software name."},
                "device": text, "kind": text, "model": text, "serial": text, "shop": text, "note": text,
                "bought": {**text, "description": "YYYY-MM-DD."},
                "until": {**text, "description": "Warranty end, YYYY-MM-DD."},
                "last": {**text, "description": "update_add: when last updated, YYYY-MM-DD."},
                "price": {"type": "number"},
                "warranty_months": {"type": "integer"},
                "percent": {"type": "number", "description": "Battery percent 0 to 100."},
                "charging": {"type": "boolean"},
                "every_days": {"type": "integer", "description": "update_add: how often to update."},
                "days": {"type": "integer", "description": "How many days ahead to look."},
                "folder": text, "filename": text,
                "confirmed": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"techhelp_gadgets"}


# ---- gadgets ---------------------------------------------------------------------------------

def _warranty_end(g: dict) -> date | None:
    if g.get("until"):
        return date.fromisoformat(g["until"])
    if g.get("bought") and g.get("months"):
        return hstore.add_months(date.fromisoformat(g["bought"]), int(g["months"]))
    return None


def _status(end: date | None, today: date) -> str:
    if end is None:
        return "no warranty date"
    n = (end - today).days
    return f"ended {-n} days ago" if n < 0 else "ends today" if n == 0 else f"{n} days left"


def gadget_add(settings: Settings, args: dict) -> str:
    found = store.rows(settings, GADGETS)
    name = hs.need(args.get("name"), "gadget name", 60)
    key = next((k for k in found if k.lower() == name.lower()), name)
    old = found.get(key, {})
    g = {**old, "kind": hs.clean(args.get("kind"), 30) or old.get("kind", ""),
         "model": hs.clean(args.get("model"), 60) or old.get("model", ""),
         "serial": hs.clean(args.get("serial"), 60) or old.get("serial", ""),
         "shop": hs.clean(args.get("shop"), 40) or old.get("shop", "")}
    if args.get("bought"):
        g["bought"] = hs.parse_day(args["bought"]).isoformat()
    if args.get("price") is not None:
        g["price"] = round(hs.number(args["price"], "price", 0, 1e7), 2)
    if args.get("until"):
        g["until"] = hs.parse_day(args["until"]).isoformat()
    if args.get("warranty_months") is not None:
        g["months"] = int(hs.number(args["warranty_months"], "warranty length", 0, 600))
        if not args.get("until"):
            g.pop("until", None)
    store.put(settings, GADGETS, found, key, g)
    end = _warranty_end(g)
    tail = f" Warranty {_status(end, hs.today())}." if end else ""
    return f"Saved {key}.{tail}"


def _table(settings: Settings, found: dict) -> list[list[str]]:
    cur = settings.currency
    return [[k, g.get("kind", ""), g.get("model", ""), g.get("serial", ""), g.get("bought", ""),
             hs.money(g["price"], cur) if "price" in g else "",
             f"{e:%d %b %Y}" if (e := _warranty_end(g)) else ""] for k, g in sorted(found.items())]


def gadget_list(settings: Settings) -> screen.Shown:
    found = store.rows(settings, GADGETS)
    if not found:
        return screen.Shown("You haven't added any gadgets yet.", screen.card("text", "Gadgets", "techhelp-gadgets",
                                                                          text="No gadgets yet."))
    return screen.Shown(f"You have {len(found)} gadgets listed.", screen.card(
        "table", "My gadgets", "techhelp-gadgets", columns=["Gadget", "Type", "Model", "Serial", "Bought", "Price", "Warranty ends"],
        rows=_table(settings, found)))


def gadget_show(settings: Settings, args: dict) -> screen.Shown:
    found = store.rows(settings, GADGETS)
    k = store.key_for(found, args.get("name"), "gadget")
    g, end = found[k], _warranty_end(found[k])
    rows = [["Type", g.get("kind", "")], ["Model", g.get("model", "")], ["Serial", g.get("serial", "")],
            ["Shop", g.get("shop", "")], ["Bought", g.get("bought", "")],
            ["Price", hs.money(g["price"], settings.currency) if "price" in g else ""],
            ["Warranty", f"{end:%d %b %Y} ({_status(end, hs.today())})" if end else ""],
            ["Receipt", g.get("receipt", "").rsplit("/", 1)[-1]]]
    buttons = [{"label": "Show receipt", "say": f"Show me the receipt for my {k}."}] if g.get("receipt") else []
    return screen.Shown(f"{k}: " + (f"warranty {_status(end, hs.today())}." if end else "no warranty date saved."),
                        screen.card("table", k, f"techhelp-gadget-{k.lower()}", columns=["", ""],
                                    rows=[r for r in rows if r[1]], buttons=buttons))


def gadget_receipt(settings: Settings, args: dict) -> str:
    found = store.rows(settings, GADGETS)
    k = store.key_for(found, args.get("name"), "gadget")
    path = screen.find_file(settings, hs.clean(args.get("folder")), hs.need(args.get("filename"), "receipt file", 120))
    found[k]["receipt"] = path.resolve().relative_to(memory.root(settings).resolve()).as_posix()
    hs.save(settings, GADGETS, found)
    return f"Linked {path.name} as the receipt for {k}."


def receipt_show(settings: Settings, args: dict) -> screen.Shown:
    found = store.rows(settings, GADGETS)
    k = store.key_for(found, args.get("name"), "gadget")
    rel = found[k].get("receipt")
    if not rel:
        raise ValueError(f"There's no receipt linked to {k} yet. Tell me the folder and file name.")
    path = screen.memory_path(settings, rel)
    return screen.Shown(f"Showing the receipt for {k}.", screen.file_card(settings, path))


def gadget_warranty(settings: Settings, args: dict) -> screen.Shown:
    horizon = int(hs.number(args.get("days") or 90, "days", 1, 3650))
    today = hs.today()
    rows = sorted(((e, k) for k, g in store.rows(settings, GADGETS).items()
                   if (e := _warranty_end(g)) and -30 <= (e - today).days <= horizon))
    if not rows:
        return screen.Shown(f"Nothing runs out of warranty in the next {horizon} days.", screen.card(
            "text", "Warranties", "techhelp-warranty", text=f"No gadget warranties end in the next {horizon} days."))
    soon = [k for e, k in rows if e >= today]
    said = (f"{len(soon)} out of warranty soon: " + ", ".join(soon[:4]) + ".") if soon else "Those warranties have just ended."
    return screen.Shown(said, screen.card("table", "Out of warranty soon", "techhelp-warranty",
                                           columns=["Gadget", "Warranty ends", "Status"],
                                           rows=[[k, f"{e:%d %b %Y}", _status(e, today)] for e, k in rows]))


def gadget_spend(settings: Settings) -> screen.Shown:
    priced = sorted(((g["price"], k) for k, g in store.rows(settings, GADGETS).items() if "price" in g), reverse=True)[:12]
    if not priced:
        raise ValueError("None of your gadgets has a price yet.")
    total = sum(p for p, _ in priced)
    return screen.Shown(f"Your gadgets cost {hs.money(total, settings.currency)} in all.", screen.card(
        "chart", "What gadgets cost", "techhelp-spend", chart={"type": "bar", "labels": [k for _, k in priced],
                                                              "values": [p for p, _ in priced], "unit": settings.currency}))


# ---- battery log -----------------------------------------------------------------------------

def battery_log(settings: Settings, args: dict) -> str:
    found = store.rows(settings, BATTERY)
    device = hs.need(args.get("device") or args.get("name"), "device", 60)
    key = next((k for k in found if k.lower() == device.lower()), device)
    pct = hs.number(args.get("percent"), "battery percent", 0, 100)
    readings = found.get(key, [])[-(MAX_READINGS - 1):]
    readings.append({"at": hs.now().strftime("%Y-%m-%d %H:%M"), "pct": pct, "charging": bool(args.get("charging")),
                     "note": hs.clean(args.get("note"), 80)})
    store.put(settings, BATTERY, found, key, readings)
    warn = " That's low, time to charge." if pct < 20 and not args.get("charging") else ""
    return f"Logged {key} at {pct:g} percent.{warn}"


def battery_show(settings: Settings, args: dict) -> screen.Shown:
    found = store.rows(settings, BATTERY)
    k = store.key_for(found, args.get("device") or args.get("name"), "device")
    readings = found[k][-30:]
    labels = [datetime.strptime(r["at"], "%Y-%m-%d %H:%M").strftime("%d %b %H:%M") for r in readings]
    last = readings[-1]
    return screen.Shown(f"{k} was last logged at {last['pct']:g} percent, {len(found[k])} readings in all.", screen.card(
        "chart", f"{k} battery", f"techhelp-battery-{k.lower()}", chart={"type": "line", "labels": labels,
                                                                     "values": [r["pct"] for r in readings], "unit": "%"}))


# ---- software update reminders ---------------------------------------------------------------

def update_add(settings: Settings, args: dict) -> str:
    found = store.rows(settings, UPDATES)
    name = hs.need(args.get("name"), "software", 60)
    every = int(hs.number(args.get("every_days") or 30, "number of days", 1, 3650))
    key = next((k for k in found if k.lower() == name.lower()), name)
    last = hs.parse_day(args.get("last")) if args.get("last") else hs.today()
    store.put(settings, UPDATES, found, key, {"every": every, "last": last.isoformat(), "note": hs.clean(args.get("note"), 100)})
    return f"I'll remind you to update {key} every {every} days. Next one {hs.spoken(last + timedelta(days=every))}."


def update_due(settings: Settings, args: dict) -> screen.Shown:
    found = store.rows(settings, UPDATES)
    if not found:
        raise ValueError("You haven't set any update reminders yet. Tell me what to keep updated and how often.")
    today, horizon = hs.today(), int(hs.number(args.get("days") or 14, "days", 0, 365))
    rows = sorted(((date.fromisoformat(v["last"]) + timedelta(days=v["every"]), k, v) for k, v in found.items()))
    due = [k for d, k, _ in rows if (d - today).days <= horizon]
    said = f"{len(due)} to update: " + ", ".join(due[:5]) + "." if due else "Nothing needs updating soon."
    return screen.Shown(said, screen.card("table", "Software updates", "techhelp-updates",
                                           columns=["Software", "Last updated", "Due", "Status"],
                                           rows=[[k, v["last"], f"{d:%d %b %Y}",
                                                  "overdue" if d < today else "due today" if d == today
                                                  else f"in {(d - today).days} days"] for d, k, v in rows]))


def update_done(settings: Settings, args: dict) -> str:
    found = store.rows(settings, UPDATES)
    k = store.key_for(found, args.get("name"), "update reminder")
    found[k]["last"] = hs.today().isoformat()
    hs.save(settings, UPDATES, found)
    return f"Noted: {k} updated today. Next one {hs.spoken(hs.today() + timedelta(days=found[k]['every']))}."


def run_tool(name: str, args: dict, settings: Settings, http=None):
    action = args.get("action")
    simple = {"gadget_add": gadget_add, "gadget_receipt": gadget_receipt, "battery_log": battery_log,
              "update_add": update_add, "update_done": update_done, "receipt_show": receipt_show,
              "gadget_show": gadget_show, "gadget_warranty": gadget_warranty, "battery_show": battery_show,
              "update_due": update_due}
    if action in simple:
        return simple[action](settings, args)
    if action == "gadget_list":
        return gadget_list(settings)
    if action == "gadget_spend":
        return gadget_spend(settings)
    if action == "gadget_remove":
        return store.remove(settings, GADGETS, args.get("name"), "gadget", bool(args.get("confirmed")))
    if action == "update_remove":
        return store.remove(settings, UPDATES, args.get("name"), "update reminder", bool(args.get("confirmed")))
    raise ValueError(f"Unknown action {action}.")
