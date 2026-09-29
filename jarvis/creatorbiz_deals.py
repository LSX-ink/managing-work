"""Brand deal pipeline and sponsorship tracker: stages, follow-ups, terms and notes.

The board pops up as a "creatorbiz-pipeline" window (frontend/popup-creatorbiz.js); its buttons send lines back to
Alfred. Kept in creatorbiz-deals.json in the memory folder. Nothing is ever sent to a brand; fees are what you
typed in, never a forecast of income.
"""

from datetime import timedelta

import creatorbiz_store as cb
import screen
from config import Settings

KIND = "creatorbiz-pipeline"
screen.EXTRA_KINDS.add(KIND)
STAGES = ["lead", "pitched", "negotiating", "agreed", "delivered", "invoiced", "paid", "declined"]
OPEN_STAGES = ["lead", "pitched", "negotiating", "agreed", "delivered", "invoiced"]
FOLLOW_UP_DAYS = 7
NAMES = {"creator_deals"}
ACTIONS = ["add", "move", "pipeline", "list", "show", "update_terms", "follow_ups", "set_follow_up", "followed_up",
           "note", "notes", "pipeline_value", "remove"]


def _stage(value, default: str | None = None) -> str:
    text = cb.clean(value).lower() or default or ""
    if text not in STAGES:
        raise ValueError(f"The stages are {', '.join(STAGES)}.")
    return text


def _log(d: dict, stage: str) -> None:
    d.setdefault("history", []).append({"stage": stage, "date": cb.today().isoformat()})


def _follow(d: dict):
    return cb.parse_date(d.get("follow_up"), "follow-up date") if d.get("follow_up") else None


def _board(deals: list[dict]) -> screen.Shown:
    cards = [{"label": cb.deal_label(d), "brand": d["brand"], "stage": d["stage"], "fee": cb.gbp(d["fee"]) if d.get("fee") else "",
              "follow_up": cb.until(_follow(d)) if _follow(d) and d["stage"] in OPEN_STAGES else ""} for d in deals]
    counts = ", ".join(f"{sum(c['stage'] == s for c in cards)} {s}" for s in STAGES if any(c["stage"] == s for c in cards))
    return screen.Shown(f"Your brand deals: {counts or 'nothing yet'}.", screen.card(
        KIND, "Brand deal pipeline", "creatorbiz-pipeline", data={"stages": STAGES, "cards": cards},
        buttons=[{"label": "Follow-ups due", "say": "Which brand deals need a follow-up?"},
                 {"label": "Pipeline value", "say": "What is my brand deal pipeline worth?"}]))


def _saved(settings: Settings, deals: list[dict], text: str) -> screen.Shown:
    cb.save(settings, cb.DEALS, deals)
    return screen.Shown(text, _board(deals).card)


def add(settings: Settings, args: dict) -> screen.Shown:
    deals = cb.deals(settings)
    brand = cb.need(args.get("brand"), "brand")
    campaign = cb.clean(args.get("campaign"), 80)
    if any(d["brand"].lower() == brand.lower() and d.get("campaign", "").lower() == campaign.lower() for d in deals):
        raise ValueError(f"You already have that deal with {brand}.")
    if len(deals) >= cb.MAX_ROWS:
        raise ValueError("That's a lot of deals; remove some old ones first.")
    stage = _stage(args.get("stage"), "lead")
    follow = cb.parse_date(args.get("follow_up"), "follow-up date")
    if not follow and stage == "pitched":
        follow = cb.today() + timedelta(days=FOLLOW_UP_DAYS)
    d = {"brand": brand, "campaign": campaign, "stage": stage, "fee": cb.money(args["fee"], "fee") if args.get("fee") else 0,
         "contact": cb.clean(args.get("contact"), 80), "usage_rights": cb.clean(args.get("usage_rights"), 120),
         "exclusivity": cb.clean(args.get("exclusivity"), 120),
         "payment_days": int(args["payment_days"]) if args.get("payment_days") else 0,
         "follow_up": follow.isoformat() if follow else "", "notes": [], "history": [], "deliverables": [], "checks": {}}
    _log(d, stage)
    if cb.clean(args.get("text")):
        d["notes"].append(cb.clean(args.get("text"), 1000))
    deals.append(d)
    return _saved(settings, deals, f"Added {cb.deal_label(d)} as {stage}.")


def move(settings: Settings, args: dict) -> screen.Shown:
    deals = cb.deals(settings)
    d = cb.pick_deal(deals, args.get("brand"), args.get("campaign"))
    d["stage"] = _stage(args.get("stage"))
    _log(d, d["stage"])
    if d["stage"] == "pitched" and not d.get("follow_up"):
        d["follow_up"] = (cb.today() + timedelta(days=FOLLOW_UP_DAYS)).isoformat()
    if d["stage"] in ("paid", "declined"):
        d["follow_up"] = ""
    return _saved(settings, deals, f"Moved {cb.deal_label(d)} to {d['stage']}.")


def pipeline(settings: Settings) -> screen.Shown:
    return _board(cb.deals(settings))


def listing(settings: Settings, args: dict) -> screen.Shown | str:
    deals = cb.deals(settings)
    if args.get("stage"):
        deals = [d for d in deals if d["stage"] == _stage(args.get("stage"))]
    if not deals:
        return "No brand deals saved yet. Tell me about one and I'll track it."
    rows = [[cb.deal_label(d), d["stage"], cb.gbp(d["fee"]) if d.get("fee") else "", cb.short(_follow(d)) if _follow(d) else ""]
            for d in deals]
    return screen.Shown(f"{len(deals)} brand deals on the list.", screen.card(
        "table", "Brand deals", "creatorbiz-deals", columns=["Deal", "Stage", "Fee", "Follow up"], rows=rows,
        buttons=[{"label": "Pipeline", "say": "Show my brand deal pipeline."}]))


def show(settings: Settings, args: dict) -> screen.Shown:
    d = cb.pick_deal(cb.deals(settings), args.get("brand"), args.get("campaign"))
    lines = [f"Stage: {d['stage']}"]
    for key, name in (("contact", "Contact"), ("usage_rights", "Usage rights"), ("exclusivity", "Exclusivity")):
        if d.get(key):
            lines.append(f"{name}: {d[key]}")
    if d.get("fee"):
        lines.append(f"Agreed or quoted fee: {cb.gbp(d['fee'])}")
    if d.get("payment_days"):
        lines.append(f"Payment terms: {d['payment_days']} days")
    if _follow(d):
        lines.append(f"Follow up: {cb.short(_follow(d))} ({cb.until(_follow(d))})")
    open_work = [x for x in d.get("deliverables", []) if not x.get("done")]
    lines.append(f"Deliverables: {len(d.get('deliverables', [])) - len(open_work)} done, {len(open_work)} to do")
    lines.append("History: " + ", ".join(f"{h['stage']} {h['date']}" for h in d.get("history", [])))
    if d.get("notes"):
        lines += ["", "Notes:"] + [f"- {n}" for n in d["notes"]]
    return screen.Shown(f"{cb.deal_label(d)} is at the {d['stage']} stage.", screen.card(
        "text", cb.deal_label(d), f"creatorbiz-deal-{cb.deal_label(d)}", text="\n".join(lines),
        buttons=[{"label": "Contract checklist", "say": f"Show the contract checklist for {d['brand']}."},
                 {"label": "Deal profit", "say": f"How did the {d['brand']} deal work out?"}]))


def update_terms(settings: Settings, args: dict) -> screen.Shown:
    deals = cb.deals(settings)
    d = cb.pick_deal(deals, args.get("brand"), args.get("campaign"))
    if args.get("fee"):
        d["fee"] = cb.money(args["fee"], "fee")
    for key in ("contact", "usage_rights", "exclusivity"):
        if args.get(key) is not None and key in args:
            d[key] = cb.clean(args[key], 120)
    if args.get("payment_days"):
        d["payment_days"] = int(args["payment_days"])
    return _saved(settings, deals, f"Updated the terms for {cb.deal_label(d)}.")


def follow_ups(settings: Settings) -> screen.Shown | str:
    due = [d for d in cb.deals(settings) if _follow(d) and _follow(d) <= cb.today() and d["stage"] in OPEN_STAGES]
    if not due:
        return "No brand follow-ups are due today."
    due.sort(key=_follow)
    items = [{"label": f"{cb.deal_label(d)} - {cb.until(_follow(d))}", "say": f"I've followed up with {d['brand']}"} for d in due]
    return screen.Shown(f"{len(due)} follow-ups due, first {cb.deal_label(due[0])}.", screen.card(
        "list", "Brand follow-ups due", "creatorbiz-followups", items=items))


def set_follow_up(settings: Settings, args: dict) -> str:
    deals = cb.deals(settings)
    d = cb.pick_deal(deals, args.get("brand"), args.get("campaign"))
    day = cb.parse_date(args.get("follow_up"), "follow-up date")
    d["follow_up"] = day.isoformat() if day else ""
    cb.save(settings, cb.DEALS, deals)
    return f"I'll nudge you about {cb.deal_label(d)} on {cb.short(day)}." if day else f"Cleared the follow-up for {cb.deal_label(d)}."


def followed_up(settings: Settings, args: dict) -> str:
    deals = cb.deals(settings)
    d = cb.pick_deal(deals, args.get("brand"), args.get("campaign"))
    d["follow_up"] = (cb.today() + timedelta(days=FOLLOW_UP_DAYS)).isoformat()
    cb.save(settings, cb.DEALS, deals)
    return f"Noted. I'll nudge you about {cb.deal_label(d)} again in a week."


def note(settings: Settings, args: dict) -> str:
    deals = cb.deals(settings)
    d = cb.pick_deal(deals, args.get("brand"), args.get("campaign"))
    d.setdefault("notes", []).append(cb.need(args.get("text"), "note", 1000))
    cb.save(settings, cb.DEALS, deals)
    return f"Added a note to {cb.deal_label(d)}."


def notes(settings: Settings, args: dict) -> screen.Shown | str:
    d = cb.pick_deal(cb.deals(settings), args.get("brand"), args.get("campaign"))
    if not d.get("notes"):
        return f"No notes on {cb.deal_label(d)} yet."
    return screen.Shown(f"{len(d['notes'])} notes on {cb.deal_label(d)}.", screen.card(
        "list", f"Notes: {cb.deal_label(d)}", f"creatorbiz-notes-{cb.deal_label(d)}", items=[{"label": n} for n in d["notes"]]))


def pipeline_value(settings: Settings) -> screen.Shown | str:
    deals = [d for d in cb.deals(settings) if d.get("fee")]
    if not deals:
        return "None of your deals has a fee saved yet."
    rows, total_open = [], 0.0
    for stage in STAGES:
        mine = [d for d in deals if d["stage"] == stage]
        if mine:
            amount = sum(d["fee"] for d in mine)
            rows.append([stage, str(len(mine)), cb.gbp(amount)])
            total_open += amount if stage in ("agreed", "delivered", "invoiced") else 0
    return screen.Shown(f"{cb.gbp(total_open)} is agreed but not yet paid. Quoted fees are not guaranteed.", screen.card(
        "table", "Deal fees by stage", "creatorbiz-value", columns=["Stage", "Deals", "Fees"], rows=rows,
        buttons=[{"label": "Pipeline", "say": "Show my brand deal pipeline."}]))


def remove(settings: Settings, args: dict) -> str:
    deals = cb.deals(settings)
    d = cb.pick_deal(deals, args.get("brand"), args.get("campaign"))
    if not args.get("confirmed"):
        return f"Should I really remove {cb.deal_label(d)} and its deliverables and notes? Say yes and I'll do it."
    deals.remove(d)
    cb.save(settings, cb.DEALS, deals)
    return f"Removed {cb.deal_label(d)}."


def tool_definitions() -> list[dict]:
    return [{
        "name": "creator_deals",
        "description": "Track a creator's brand deals and sponsorships: add a brand deal, move it through stages (lead, pitched, "
                       "negotiating, agreed, delivered, invoiced, paid, declined), show the pipeline board, follow-ups due, "
                       "fee and terms, notes, deal list. Local only; never contacts brands. Set confirmed only after the user says yes to remove.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "brand": {"type": "string"},
                "campaign": {"type": "string", "description": "Optional, tells two deals with one brand apart."},
                "stage": {"type": "string", "enum": STAGES},
                "fee": {"type": "number", "description": "Pounds, as quoted or agreed."},
                "contact": {"type": "string"},
                "usage_rights": {"type": "string", "description": "e.g. 'brand can reuse the video on its Instagram for 3 months'."},
                "exclusivity": {"type": "string", "description": "e.g. 'no rival skincare brands for 30 days'."},
                "payment_days": {"type": "integer", "description": "Days after invoice the brand pays within."},
                "follow_up": {"type": "string", "description": "YYYY-MM-DD, 'tomorrow' or 'next week'; empty clears."},
                "text": {"type": "string", "description": "A note about the deal."},
                "confirmed": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


def run_tool(name: str, args: dict, settings: Settings, http=None):
    action = args.get("action")
    handlers = {"add": add, "move": move, "list": listing, "show": show, "update_terms": update_terms,
                "set_follow_up": set_follow_up, "followed_up": followed_up, "note": note, "notes": notes, "remove": remove}
    if action in handlers:
        return handlers[action](settings, args)
    if action == "follow_ups":
        return follow_ups(settings)
    if action == "pipeline_value":
        return pipeline_value(settings)
    return pipeline(settings)
