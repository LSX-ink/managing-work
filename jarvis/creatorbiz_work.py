"""Deliverables with due dates, plus the gifted-product log and the affiliate log.

Deliverables live inside each brand deal (creatorbiz-deals.json); gifts and affiliate codes are in
creatorbiz-gifts.json. Affiliate earnings you type in are also added to the income ledger. Nothing is posted anywhere.
"""

from datetime import timedelta

import creatorbiz_store as cb
import screen
from config import Settings

NAMES = {"creator_work"}
GIFT_STATUS = ["received", "posted", "not posting", "returned"]
ACTIONS = ["add_deliverable", "deliverables", "due_soon", "done", "reopen", "remove_deliverable", "add_gift", "gifts",
           "gift_status", "gifts_value", "add_affiliate", "affiliates", "affiliate_earning"]
GIFT_TIP = ("If a brand gives you something for free and expects a mention, or you get paid or rewarded in any way, "
            "it usually needs a clear #ad or 'gifted' label. Check the current ASA and CMA guidance.")


def _pick_task(deal: dict, title) -> dict:
    name = cb.need(title, "deliverable")
    tasks = deal.get("deliverables", [])
    hits = [t for t in tasks if t["title"].lower() == name.lower()] or [t for t in tasks if name.lower() in t["title"].lower()]
    if not hits:
        raise ValueError(f"{cb.deal_label(deal)} has no deliverable called {name}.")
    if len(hits) > 1:
        raise ValueError(f"More than one deliverable matches {name}; be more specific.")
    return hits[0]


def _due(t: dict):
    return cb.parse_date(t.get("due"), "due date") if t.get("due") else None


def add_deliverable(settings: Settings, args: dict) -> str:
    deals = cb.deals(settings)
    d = cb.pick_deal(deals, args.get("brand"), args.get("campaign"))
    title = cb.need(args.get("title"), "deliverable", 100)
    if any(t["title"].lower() == title.lower() for t in d.setdefault("deliverables", [])):
        raise ValueError(f"{cb.deal_label(d)} already has {title}.")
    due = cb.parse_date(args.get("due"), "due date")
    d["deliverables"].append({"title": title, "platform": cb.clean(args.get("platform"), 30), "done": False,
                              "due": due.isoformat() if due else ""})
    cb.save(settings, cb.DEALS, deals)
    return f"Added {title} to {cb.deal_label(d)}" + (f", due {cb.short(due)}." if due else ".")


def deliverables(settings: Settings, args: dict) -> screen.Shown | str:
    deals = cb.deals(settings)
    if args.get("brand"):
        deals = [cb.pick_deal(deals, args.get("brand"), args.get("campaign"))]
    rows = []
    for d in deals:
        for t in d.get("deliverables", []):
            if t.get("done") and not args.get("brand"):
                continue
            due = _due(t)
            rows.append(((due or cb.today() + timedelta(days=9999)), [cb.deal_label(d), t["title"], t.get("platform", ""),
                         cb.short(due) if due else "", "done" if t.get("done") else (cb.until(due) if due else "to do")]))
    if not rows:
        return "No deliverables to do. Add one to a deal and I'll track it."
    rows.sort(key=lambda r: r[0])
    return screen.Shown(f"{len(rows)} deliverables listed.", screen.card(
        "table", "Deliverables", "creatorbiz-deliverables", columns=["Deal", "Item", "Where", "Due", "Status"],
        rows=[r[1] for r in rows], buttons=[{"label": "Due this week", "say": "What brand deliverables are due soon?"}]))


def due_soon(settings: Settings, args: dict) -> screen.Shown | str:
    limit = cb.today() + timedelta(days=int(args.get("days") or 7))
    hits = [(d, t) for d in cb.deals(settings) for t in d.get("deliverables", []) if not t.get("done") and _due(t) and _due(t) <= limit]
    if not hits:
        return "No brand deliverables are due soon."
    hits.sort(key=lambda p: _due(p[1]))
    items = [{"label": f"{t['title']} for {d['brand']} - {cb.until(_due(t))}", "say": f"I've finished {t['title']} for {d['brand']}"}
             for d, t in hits]
    return screen.Shown(f"{len(hits)} deliverables due soon, first {hits[0][1]['title']} for {hits[0][0]['brand']}.", screen.card(
        "list", "Deliverables due soon", "creatorbiz-due", items=items))


def _set_done(settings: Settings, args: dict, value: bool) -> str:
    deals = cb.deals(settings)
    d = cb.pick_deal(deals, args.get("brand"), args.get("campaign"))
    t = _pick_task(d, args.get("title"))
    t["done"] = value
    cb.save(settings, cb.DEALS, deals)
    left = sum(not x.get("done") for x in d["deliverables"])
    if value:
        return f"Ticked off {t['title']} for {d['brand']}. " + (f"{left} left." if left else "That's everything for this deal; consider invoicing.")
    return f"Reopened {t['title']}."


def remove_deliverable(settings: Settings, args: dict) -> str:
    deals = cb.deals(settings)
    d = cb.pick_deal(deals, args.get("brand"), args.get("campaign"))
    t = _pick_task(d, args.get("title"))
    d["deliverables"].remove(t)
    cb.save(settings, cb.DEALS, deals)
    return f"Removed {t['title']} from {cb.deal_label(d)}."


def _gifts(settings: Settings) -> list[dict]:
    return [g for g in cb.load(settings, cb.GIFTS, []) if isinstance(g, dict)]


def _gift_rows(gifts: list[dict]) -> list[list[str]]:
    return [[g["brand"], g["item"], cb.gbp(g["value"]) if g.get("value") else "", g["status"], "yes" if g.get("labelled") else "no"]
            for g in gifts]


def add_gift(settings: Settings, args: dict) -> screen.Shown:
    gifts = _gifts(settings)
    if len(gifts) >= cb.MAX_ROWS:
        raise ValueError("The gift log is full; remove some old entries first.")
    gifts.append({"type": "gift", "brand": cb.need(args.get("brand"), "brand"), "item": cb.need(args.get("item"), "item", 100),
                  "value": cb.money(args["value"], "value") if args.get("value") else 0, "status": "received",
                  "labelled": False, "date": cb.today().isoformat()})
    cb.save(settings, cb.GIFTS, gifts)
    return _gift_card(gifts, f"Logged the gift from {gifts[-1]['brand']}. {GIFT_TIP}")


def _gift_card(gifts: list[dict], text: str) -> screen.Shown:
    return screen.Shown(text, screen.card(
        "table", "Gifted products", "creatorbiz-gifts", columns=["Brand", "Item", "Worth", "Status", "Labelled"],
        rows=_gift_rows([g for g in gifts if g.get("type") == "gift"]),
        buttons=[{"label": "Gift value", "say": "How much gifted product have I been sent?"}]))


def gifts(settings: Settings, args: dict) -> screen.Shown | str:
    rows = [g for g in _gifts(settings) if g.get("type") == "gift"]
    if args.get("brand"):
        rows = [g for g in rows if cb.clean(args["brand"]).lower() in g["brand"].lower()]
    if not rows:
        return "No gifted products logged yet."
    return _gift_card(rows, f"{len(rows)} gifted products logged.")


def gift_status(settings: Settings, args: dict) -> screen.Shown:
    rows = _gifts(settings)
    mine = [g for g in rows if g.get("type") == "gift" and cb.clean(args.get("brand")).lower() in g["brand"].lower()
            and (not args.get("item") or cb.clean(args["item"]).lower() in g["item"].lower())]
    if not mine:
        raise ValueError("I can't find that gift.")
    if len(mine) > 1:
        raise ValueError(f"{len(mine)} gifts match; say which item.")
    g = mine[0]
    status = cb.clean(args.get("status")).lower()
    if status not in GIFT_STATUS:
        raise ValueError(f"The gift statuses are {', '.join(GIFT_STATUS)}.")
    g["status"] = status
    if "labelled" in args:
        g["labelled"] = bool(args["labelled"])
    cb.save(settings, cb.GIFTS, rows)
    return _gift_card(rows, f"Marked {g['item']} from {g['brand']} as {status}.")


def gifts_value(settings: Settings) -> str:
    rows = [g for g in _gifts(settings) if g.get("type") == "gift"]
    if not rows:
        return "No gifted products logged yet."
    total = sum(g.get("value", 0) for g in rows)
    unposted = sum(g["status"] == "received" for g in rows)
    return (f"You've logged {len(rows)} gifts worth {cb.gbp(total)}, and {unposted} still to post about. "
            "Gifts can count as taxable income when there's a deal behind them, so check GOV.UK or an accountant.")


def add_affiliate(settings: Settings, args: dict) -> screen.Shown:
    rows = _gifts(settings)
    brand = cb.need(args.get("brand"), "brand")
    if any(g.get("type") == "affiliate" and g["brand"].lower() == brand.lower() for g in rows):
        raise ValueError(f"{brand} is already in your affiliate log.")
    rows.append({"type": "affiliate", "brand": brand, "code": cb.clean(args.get("code"), 60),
                 "commission": cb.clean(args.get("commission"), 40), "earned": 0.0})
    cb.save(settings, cb.GIFTS, rows)
    return _affiliate_card(rows, f"Added {brand} to your affiliate log. Affiliate links need a clear #ad label too.")


def _affiliate_card(rows: list[dict], text: str) -> screen.Shown:
    aff = [g for g in rows if g.get("type") == "affiliate"]
    return screen.Shown(text, screen.card(
        "table", "Affiliate log", "creatorbiz-affiliates", columns=["Brand", "Code", "Commission", "Earned so far"],
        rows=[[g["brand"], g.get("code", ""), g.get("commission", ""), cb.gbp(g.get("earned", 0))] for g in aff]))


def affiliates(settings: Settings) -> screen.Shown | str:
    aff = [g for g in _gifts(settings) if g.get("type") == "affiliate"]
    if not aff:
        return "No affiliate codes logged yet."
    return _affiliate_card(_gifts(settings), f"{len(aff)} affiliate programmes, {cb.gbp(sum(g.get('earned', 0) for g in aff))} earned so far.")


def affiliate_earning(settings: Settings, args: dict) -> screen.Shown:
    rows = _gifts(settings)
    aff = [g for g in rows if g.get("type") == "affiliate"]
    key = cb.find([g["brand"] for g in aff], args.get("brand"))
    if key is None:
        raise ValueError("I don't have that affiliate programme; add it first.")
    g = next(x for x in aff if x["brand"] == key)
    amount = cb.money(args.get("amount"), "commission")
    g["earned"] = round(g.get("earned", 0) + amount, 2)
    cb.save(settings, cb.GIFTS, rows)
    cb.add_ledger(settings, "income", amount, key, "Affiliate commission", "affiliate")
    return _affiliate_card(rows, f"Logged {cb.gbp(amount)} commission from {key} in your income.")


def tool_definitions() -> list[dict]:
    return [{
        "name": "creator_work",
        "description": "A creator's brand deliverables and freebies: add deliverables (videos, posts, stories) with due dates to a "
                       "brand deal, list them, what's due soon, tick them off; log gifted products and whether they were posted or "
                       "labelled #ad; log affiliate codes and commission earned. Local only, never posts.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "brand": {"type": "string"},
                "campaign": {"type": "string"},
                "title": {"type": "string", "description": "The deliverable, e.g. '1 Instagram reel'."},
                "platform": {"type": "string"},
                "due": {"type": "string", "description": "YYYY-MM-DD, 'tomorrow' or 'next week'."},
                "days": {"type": "integer", "description": "For due_soon: look this many days ahead (default 7)."},
                "item": {"type": "string", "description": "A gifted product."},
                "value": {"type": "number", "description": "Pounds, what the gift is worth."},
                "status": {"type": "string", "enum": GIFT_STATUS},
                "labelled": {"type": "boolean", "description": "Whether the post was labelled as gifted or #ad."},
                "code": {"type": "string", "description": "Affiliate code or link name."},
                "commission": {"type": "string", "description": "e.g. '10% per sale'."},
                "amount": {"type": "number", "description": "Pounds of affiliate commission earned."},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


def run_tool(name: str, args: dict, settings: Settings, http=None):
    action = args.get("action")
    handlers = {"add_deliverable": add_deliverable, "deliverables": deliverables, "due_soon": due_soon,
                "remove_deliverable": remove_deliverable, "add_gift": add_gift, "gifts": gifts, "gift_status": gift_status,
                "add_affiliate": add_affiliate, "affiliate_earning": affiliate_earning}
    if action in handlers:
        return handlers[action](settings, args)
    if action == "done":
        return _set_done(settings, args, True)
    if action == "reopen":
        return _set_done(settings, args, False)
    if action == "gifts_value":
        return gifts_value(settings)
    if action == "affiliates":
        return affiliates(settings)
    return deliverables(settings, args)
