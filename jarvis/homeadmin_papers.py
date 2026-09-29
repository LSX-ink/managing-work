"""Home paperwork: returns and refunds, warranties with receipts, a subscription audit and important documents.

Everything is saved in homeadmin.json in the memory folder. Receipts are files you already keep in the memory folders.
"""

from datetime import date, timedelta

import homeadmin_store as store
import homestore as hs
import household_store as hh
import screen
from config import Settings

ACTIONS = ["return_add", "return_list", "return_done", "return_remove", "warranty_add", "warranty_list",
           "warranty_remove", "sub_add", "sub_used", "sub_audit", "sub_remove", "doc_add", "doc_list", "doc_remove"]
RETURN_STATES = ("to send back", "sent back", "refunded")
UNUSED_DAYS = 60
SUGGESTED_DOCS = ["Passport", "Driving licence", "TV licence", "Council tax band", "Home insurance", "Car insurance",
                  "Boiler service certificate", "Will"]


def _confirm(what: str, name: str) -> str:
    return f"Ask the user to confirm removing the {what} {name}, then call again with confirmed true."


# Returns

def return_add(settings: Settings, args: dict) -> str:
    item = hs.need(args.get("name"), "item", 60)
    row = {"name": item, "shop": hs.clean(args.get("shop"), 40).title(), "amount": round(hs.number(args.get("amount") or 0, "refund", 0, 100_000), 2),
           "return_by": store.optional_day(args.get("date")), "state": RETURN_STATES[0]}
    data = store.load(settings)
    data["returns"] = store.add(data["returns"], row)
    store.save(settings, data)
    tail = f" by {hs.spoken(date.fromisoformat(row['return_by']))}" if row["return_by"] else ""
    return f"Noted the {item} return{tail}."


def return_list(settings: Settings) -> screen.Shown:
    today, rows = hs.today(), store.load(settings)["returns"]
    if not rows:
        return screen.Shown("No returns being tracked.", screen.card("text", "Returns", "homeadmin-returns",
                            text="Nothing to send back. Say 'I need to return the boots to Next by 10 October'."))
    rows = sorted(rows, key=lambda r: (r["state"] == RETURN_STATES[2], r["return_by"] or "9999"))
    table = [[r["name"], r["shop"] or "-", store.money(r["amount"], settings) if r["amount"] else "-",
              r["return_by"] or "-", store.when(date.fromisoformat(r["return_by"]), today) if r["return_by"]
              and r["state"] == RETURN_STATES[0] else "-", r["state"].title()] for r in rows]
    open_rows = [r for r in rows if r["state"] != RETURN_STATES[2]]
    waiting = sum(r["amount"] for r in open_rows)
    card = screen.card("table", "Returns and refunds", "homeadmin-returns",
                       columns=["Item", "Shop", "Refund", "Return by", "When", "Status"], rows=table)
    urgent = [r for r in open_rows if r["state"] == RETURN_STATES[0] and r["return_by"]]
    first = f" The next deadline is {urgent[0]['name']}, {store.when(date.fromisoformat(urgent[0]['return_by']), today)}." if urgent else ""
    return screen.Shown(f"{hs.plural(len(open_rows), 'return')} still open, {store.money(waiting, settings)} to come back.{first}", card)


def return_done(settings: Settings, args: dict) -> str:
    data = store.load(settings)
    row = data["returns"][store.index(data["returns"], args.get("name"), "return")]
    state = hs.clean(args.get("state")).lower()
    row["state"] = RETURN_STATES[1] if state.startswith("sent") or state == "posted" else RETURN_STATES[2]
    store.save(settings, data)
    return f"Marked the {row['name']} return as {row['state']}."


def return_remove(settings: Settings, args: dict) -> str:
    data = store.load(settings)
    row = data["returns"][store.index(data["returns"], args.get("name"), "return")]
    if not args.get("confirmed"):
        return _confirm("return", row["name"])
    data["returns"].remove(row)
    store.save(settings, data)
    return f"Removed the {row['name']} return."


# Warranties

def warranty_add(settings: Settings, args: dict) -> str:
    name = hs.need(args.get("name"), "item", 60)
    bought = hs.parse_day(args.get("date"))
    months = round(hs.number(args.get("years") or 0, "years", 0, 50) * 12 + hs.number(args.get("months") or 0, "months", 0, 600))
    if months <= 0:
        raise ValueError("How long is the warranty: say the years or months.")
    file = store.receipt(settings, args.get("receipt"))
    row = {"name": name, "bought": bought.isoformat(), "ends": hh.add_months(bought, months).isoformat(),
           "receipt": file, "months": months}
    data = store.load(settings)
    data["warranties"] = [w for w in data["warranties"] if w["name"].lower() != name.lower()]
    data["warranties"] = store.add(data["warranties"], row)
    store.save(settings, data)
    return f"Saved the {name} warranty until {hs.spoken(date.fromisoformat(row['ends']))}."


def warranty_list(settings: Settings, days=None) -> screen.Shown:
    today = hs.today()
    rows = sorted(store.load(settings)["warranties"], key=lambda w: w["ends"])
    if not rows:
        raise ValueError("No warranties saved yet. Say what you bought, when, how long it's covered and where the receipt is.")
    limit = today + timedelta(days=int(hs.number(days if days is not None else 90, "number of days", 1, 3650)))
    table = [[w["name"], w["bought"], w["ends"], "Expired" if date.fromisoformat(w["ends"]) < today
              else store.when(date.fromisoformat(w["ends"]), today), w["receipt"] or "-"] for w in rows]
    soon = [w for w in rows if today <= date.fromisoformat(w["ends"]) <= limit]
    buttons = [b for w in soon[:2] for b in store.file_button(w["receipt"], f"Receipt: {w['name']}"[:40])]
    card = screen.card("table", "Warranties", "homeadmin-warranties",
                       columns=["Item", "Bought", "Ends", "When", "Receipt"], rows=table, buttons=buttons)
    if not soon:
        return screen.Shown(f"{hs.plural(len(rows), 'warranty', 'warranties')} saved, none ending soon.", card)
    return screen.Shown(f"{hs.plural(len(soon), 'warranty', 'warranties')} ending soon; first is {soon[0]['name']}, "
                        f"{store.when(date.fromisoformat(soon[0]['ends']), today)}.", card)


def warranty_remove(settings: Settings, args: dict) -> str:
    data = store.load(settings)
    row = data["warranties"][store.index(data["warranties"], args.get("name"), "warranty")]
    if not args.get("confirmed"):
        return _confirm("warranty", row["name"])
    data["warranties"].remove(row)
    store.save(settings, data)
    return f"Removed the {row['name']} warranty."


# Subscription audit

def _yearly(s: dict) -> float:
    return s["amount"] * (1 if s["period"] == "yearly" else 12)


def sub_add(settings: Settings, args: dict) -> str:
    name = hs.need(args.get("name"), "subscription", 60)
    period = "yearly" if hs.clean(args.get("period")).lower().startswith(("y", "a")) else "monthly"
    row = {"name": name, "amount": round(hs.number(args.get("amount"), "price", 0, 100_000), 2), "period": period,
           "cancel_by": store.optional_day(args.get("cancel_by")),
           "last_used": store.optional_day(args.get("date")) or hs.today().isoformat()}
    data = store.load(settings)
    data["subs"] = [s for s in data["subs"] if s["name"].lower() != name.lower()]
    data["subs"] = store.add(data["subs"], row)
    store.save(settings, data)
    return f"Added {name} at {store.money(row['amount'], settings)} {row['period']}, {store.money(_yearly(row) / 12, settings)} a month."


def sub_used(settings: Settings, args: dict) -> str:
    data = store.load(settings)
    row = data["subs"][store.index(data["subs"], args.get("name"), "subscription")]
    row["last_used"] = hs.parse_day(args.get("date")).isoformat()
    store.save(settings, data)
    return f"Noted you used {row['name']} on {hs.spoken(date.fromisoformat(row['last_used']))}."


def sub_audit(settings: Settings, days=None) -> screen.Shown:
    today = hs.today()
    stale = int(hs.number(days if days is not None else UNUSED_DAYS, "number of days", 1, 3650))
    subs = store.load(settings)["subs"]
    if not subs:
        raise ValueError("No subscriptions in the audit yet. Say the name, what it costs and when you last used it.")
    yearly = sum(_yearly(s) for s in subs)
    table, unused = [], []
    for s in sorted(subs, key=lambda s: -_yearly(s)):
        idle = (today - date.fromisoformat(s["last_used"])).days
        notes = []
        if idle >= stale:
            notes.append(f"unused {idle} days")
            unused.append(s)
        if s["cancel_by"]:
            notes.append(f"cancel by {s['cancel_by']} ({store.when(date.fromisoformat(s['cancel_by']), today)})")
        table.append([s["name"], f"{store.money(s['amount'], settings)} {s['period']}", store.money(_yearly(s), settings),
                      s["last_used"], "; ".join(notes) or "in use"])
    table.append(["Total", f"{store.money(yearly / 12, settings)} a month", store.money(yearly, settings), "", ""])
    buttons = [{"label": f"Used {s['name']}"[:40], "say": f"I used {s['name']} today."} for s in unused[:3]]
    card = screen.card("table", "Subscription audit", "homeadmin-subs",
                       columns=["Subscription", "Cost", "Per year", "Last used", "Note"], rows=table, buttons=buttons)
    text = f"{hs.plural(len(subs), 'subscription')} cost {store.money(yearly / 12, settings)} a month, {store.money(yearly, settings)} a year."
    if unused:
        waste = sum(_yearly(s) for s in unused)
        text += f" You haven't used {', '.join(s['name'] for s in unused[:3])} in {stale} days: that's {store.money(waste, settings)} a year."
    return screen.Shown(text, card)


def sub_remove(settings: Settings, args: dict) -> str:
    data = store.load(settings)
    row = data["subs"][store.index(data["subs"], args.get("name"), "subscription")]
    if not args.get("confirmed"):
        return _confirm("subscription", row["name"])
    data["subs"].remove(row)
    store.save(settings, data)
    return f"Removed {row['name']}; that's {store.money(_yearly(row), settings)} a year saved. Remember to cancel it with them too."


# Important documents

def doc_add(settings: Settings, args: dict) -> str:
    name = hs.need(args.get("name"), "document", 60)
    row = {"name": name, "expires": store.optional_day(args.get("date")), "note": hs.clean(args.get("note"), 200)}
    data = store.load(settings)
    data["docs"] = [d for d in data["docs"] if d["name"].lower() != name.lower()]
    data["docs"] = store.add(data["docs"], row)
    store.save(settings, data)
    return f"Saved {name}" + (f", renew by {hs.spoken(date.fromisoformat(row['expires']))}." if row["expires"] else ".")


def doc_list(settings: Settings) -> screen.Shown:
    today, docs = hs.today(), store.load(settings)["docs"]
    if not docs:
        items = [{"label": d, "say": f"Add {d} to my important documents."} for d in SUGGESTED_DOCS]
        card = screen.card("list", "Important documents to note", "homeadmin-docs", items=items)
        return screen.Shown("You haven't saved any yet. Here are the usual ones; tap one to add it.", card)
    docs = sorted(docs, key=lambda d: d["expires"] or "9999")
    table = [[d["name"], d["expires"] or "-", store.when(date.fromisoformat(d["expires"]), today) if d["expires"] else "-",
              d["note"] or "-"] for d in docs]
    card = screen.card("table", "Important documents", "homeadmin-docs", columns=["Document", "Renew by", "When", "Note"], rows=table)
    soon = [d for d in docs if d["expires"] and date.fromisoformat(d["expires"]) <= today + timedelta(days=90)]
    if not soon:
        return screen.Shown(f"{hs.plural(len(docs), 'document')} saved, nothing needs renewing in the next 3 months.", card)
    return screen.Shown(f"{soon[0]['name']} needs renewing {store.when(date.fromisoformat(soon[0]['expires']), today)}.", card)


def doc_remove(settings: Settings, args: dict) -> str:
    data = store.load(settings)
    row = data["docs"][store.index(data["docs"], args.get("name"), "document")]
    if not args.get("confirmed"):
        return _confirm("document", row["name"])
    data["docs"].remove(row)
    store.save(settings, data)
    return f"Removed {row['name']}."


def tool_definitions() -> list[dict]:
    text = {"type": "string"}
    return [{
        "name": "homeadmin_papers",
        "description": "Home paperwork. Returns: return_add (name, shop, amount = refund, date = return by), "
                       "return_list table with deadlines, return_done (name, state 'sent back' or 'refunded'), "
                       "return_remove. Warranties: warranty_add (name, date bought, years or months, receipt = file "
                       "path in the memory folders), warranty_list expiring soon (days), warranty_remove. Subscription "
                       "audit: sub_add (name, amount, period monthly/yearly, cancel_by, date last used), sub_used "
                       "(name, date), sub_audit totals per month and year and which I haven't used, sub_remove. "
                       "Important documents: doc_add (name e.g. passport, TV licence, council tax band; date = expiry "
                       "or renewal; note), doc_list, doc_remove. Set confirmed true only after the user confirms a remove.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "name": text,
                "shop": text,
                "amount": {"type": "number"},
                "date": {"type": "string", "description": "YYYY-MM-DD or 'today'."},
                "state": {"type": "string", "enum": ["sent back", "refunded"]},
                "years": {"type": "number"},
                "months": {"type": "integer"},
                "receipt": {"type": "string", "description": "e.g. Home/Receipts/tv.pdf"},
                "period": {"type": "string", "enum": ["monthly", "yearly"]},
                "cancel_by": {"type": "string", "description": "YYYY-MM-DD."},
                "days": {"type": "integer"},
                "note": text,
                "confirmed": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"homeadmin_papers"}


def run_tool(name: str, args: dict, settings: Settings, http=None):
    action = args.get("action")
    if action == "return_list":
        return return_list(settings)
    if action == "warranty_list":
        return warranty_list(settings, args.get("days"))
    if action == "sub_audit":
        return sub_audit(settings, args.get("days"))
    if action == "doc_list":
        return doc_list(settings)
    handlers = {"return_add": return_add, "return_done": return_done, "return_remove": return_remove,
                "warranty_add": warranty_add, "warranty_remove": warranty_remove, "sub_add": sub_add,
                "sub_used": sub_used, "sub_remove": sub_remove, "doc_add": doc_add, "doc_remove": doc_remove}
    if action not in handlers:
        raise ValueError(f"Unknown home paperwork action: {action}")
    return handlers[action](settings, args)
