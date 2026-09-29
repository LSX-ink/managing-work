"""Income streams part 1: register every extra-income stream, log money in by month, hours and costs.

Streams have a type (active, passive-ish or mixed) and a tax kind for the UK helpers. Money in is typed by the user;
a stream can also be linked to read creator income from creatorbiz-ledger.json or sales from digitalproducts.json
(read-only, so don't type the same money twice). Nothing is fetched or sent and nothing promises income.
"""

import homestore as hs
import incomestreams_store as st
import screen
from config import Settings

NAMES = {"income_streams"}
ACTIONS = ["stream_add", "stream_list", "stream_show", "stream_edit", "stream_status", "stream_remove", "stream_ideas",
           "income_log", "income_list", "income_edit", "income_remove", "hours_log", "hours_list", "link_check"]
IDEAS = [["TikTok creator rewards", "active", "trading", "Needs regular posting; pay varies and can stop."],
         ["Brand deals", "active", "trading", "Paid per job; declare gifts and say when it is an ad."],
         ["Affiliate links", "mixed", "trading", "Old posts can keep earning a little; commission can change."],
         ["Digital products", "mixed", "trading", "Work up front, then sales come and go."],
         ["Reselling", "active", "trading", "Buying, listing and posting take time; count costs."],
         ["Freelance work", "active", "trading", "Paid for hours; usually the steadiest of the lot."],
         ["Renting a room", "passive", "property", "Rent a Room relief may apply: check GOV.UK."],
         ["Savings interest", "passive", "interest", "Has its own allowance: check GOV.UK."],
         ["Dividends or investments", "passive", "other", "Can go down as well as up."],
         ["Tutoring or lessons", "active", "trading", "Trades hours for money."]]


def _find_or_error(data: dict, args: dict):
    return st.stream(data, args.get("stream") if args.get("stream") is not None else args.get("name"))


def _type(args: dict, default: str = "active") -> str:
    t = hs.clean(args.get("type") or default).lower()
    t = {"passive-ish": "passive", "passiveish": "passive", "part": "mixed"}.get(t, t)
    if t not in st.TYPES:
        raise ValueError("The type is active, passive (passive-ish) or mixed.")
    return t


def _tax_kind(args: dict, default: str = "trading") -> str:
    k = hs.clean(args.get("tax_kind") or default).lower()
    if k not in st.TAX_KINDS:
        raise ValueError("The tax kind is trading, property, interest or other.")
    return k


def _link(args: dict) -> tuple[str, str]:
    link = hs.clean(args.get("link")).lower()
    if link in ("none", "off"):
        return "", ""
    if link and link not in st.LINKS:
        raise ValueError("I can link a stream to creatorbiz (creator income) or digitalproducts (sales).")
    return link, hs.clean(args.get("link_category"), 40).lower() if link else ""


def stream_add(settings: Settings, args: dict):
    data = st.load(settings)
    name = hs.need(args.get("name"), "stream name", 60)
    if any(s["name"].lower() == name.lower() for s in data["streams"]):
        raise ValueError(f"You already have a stream called {name}.")
    link, cat = _link(args)
    row = {"id": st.new_id(data), "name": name, "type": _type(args), "tax_kind": _tax_kind(args), "status": "active",
           "note": hs.clean(args.get("note"), 200), "link": link, "link_category": cat,
           "started": hs.today().isoformat()}
    st.put(data["streams"], row)
    st.save(settings, data)
    return (f"Added {name} as {'an' if row['type'] == 'active' else 'a'} {st.type_word(row['type'])} stream ({row['tax_kind']} for tax). "
            "Tell me what you earn from it each month.")


def _month_totals(rows: list, sid: int, months: list[str]) -> list[float]:
    return [st.total(rows, sid, {m}) for m in months]


def stream_list(settings: Settings, args: dict) -> screen.Shown:
    data = st.load(settings)
    st.need_streams(data)
    rows, this = st.entries(settings, data), st.month_of(hs.today())
    table = [[s["name"], st.type_word(s["type"]), s["tax_kind"], s["status"], st.gbp(st.total(rows, s["id"], {this})),
              st.gbp(st.total(rows, s["id"]))] for s in data["streams"]]
    return screen.Shown(f"You have {len(table)} income streams. This month so far: {st.gbp(st.total(rows, None, {this}))}.",
                        screen.card("table", "My income streams", "incomestreams-list", columns=[
                            "Stream", "Type", "Tax", "Status", "This month", "All time"], rows=table,
                                    buttons=[{"label": "Dashboard", "say": "Show my income dashboard."},
                                             {"label": "Log income", "say": "I want to log some income."}]))


def _per_hour(data: dict, rows: list, sid: int, months: list[str]) -> float | None:
    hours = st.hours_total(data, sid, set(months))
    if not hours:
        return None
    return round((st.total(rows, sid, set(months)) - st.total(rows, sid, set(months), field="costs")) / hours, 2)


def stream_show(settings: Settings, args: dict) -> screen.Shown:
    data = st.load(settings)
    s = _find_or_error(data, args)
    rows, this = st.entries(settings, data), st.month_of(hs.today())
    six = set(st.months_back(6))
    hours = st.hours_total(data, s["id"], six)
    per = _per_hour(data, rows, s["id"], sorted(six))
    tax_from, tax_to = (d.isoformat() for d in st.tax_range(st.tax_start(hs.today())))
    table = [["Type", st.type_word(s["type"])], ["Tax kind", s["tax_kind"]], ["Status", s["status"]],
             ["This month", st.gbp(st.total(rows, s["id"], {this}))],
             ["Last 6 months", st.gbp(st.total(rows, s["id"], six))],
             ["This tax year", st.gbp(st.total(rows, s["id"], since=tax_from, until=tax_to))],
             ["Costs (all time)", st.gbp(st.total(rows, s["id"], field="costs"))],
             ["Hours (6 months)", f"{hours:g}"], ["Money per hour", st.gbp(per) if per is not None else "log hours to see"]]
    if s.get("link"):
        table.append(["Reads from", s["link"] + (f" ({s['link_category']})" if s["link_category"] else "")])
    if s.get("note"):
        table.append(["Note", s["note"]])
    return screen.Shown(f"{s['name']}: {st.gbp(st.total(rows, s['id'], six))} in the last six months. " + st.HONEST,
                        screen.card("table", s["name"], f"incomestreams-stream-{s['id']}", columns=["", ""], rows=table,
                                    buttons=[{"label": "Log money", "say": f"I earned some money from {s['name']}."},
                                             {"label": "Log hours", "say": f"I worked some hours on {s['name']}."}]))


def stream_edit(settings: Settings, args: dict) -> str:
    data = st.load(settings)
    s = _find_or_error(data, args)
    if args.get("new_name"):
        new = hs.need(args["new_name"], "new name", 60)
        if any(o["name"].lower() == new.lower() and o is not s for o in data["streams"]):
            raise ValueError(f"You already have a stream called {new}.")
        s["name"] = new
    if args.get("type"):
        s["type"] = _type(args)
    if args.get("tax_kind"):
        s["tax_kind"] = _tax_kind(args)
    if args.get("note") is not None:
        s["note"] = hs.clean(args["note"], 200)
    if args.get("link") is not None:
        s["link"], s["link_category"] = _link(args)
    st.save(settings, data)
    return f"Updated {s['name']}: {st.type_word(s['type'])}, {s['tax_kind']} for tax."


def stream_status(settings: Settings, args: dict) -> str:
    data = st.load(settings)
    s = _find_or_error(data, args)
    status = hs.clean(args.get("status")).lower()
    if status not in st.STATUSES:
        raise ValueError("The status is active, paused or ended.")
    s["status"] = status
    st.save(settings, data)
    return f"Marked {s['name']} as {status}. Its history is kept."


def stream_remove(settings: Settings, args: dict) -> str:
    data = st.load(settings)
    s = _find_or_error(data, args)
    if not args.get("confirmed"):
        return st.confirm_needed(f"the stream {s['name']} and everything logged against it")
    data["streams"].remove(s)
    for key in ("entries", "hours"):
        data[key] = [r for r in data[key] if r["stream"] != s["id"]]
    data["goals"] = [g for g in data["goals"] if g.get("stream") != s["id"]]
    st.save(settings, data)
    return f"Removed {s['name']} and what was logged for it."


def stream_ideas(settings: Settings, args: dict) -> screen.Shown:
    return screen.Shown("Common kinds of extra income and whether they are active or passive-ish. None is guaranteed.",
                        screen.card("table", "Income stream kinds", "incomestreams-ideas",
                                    columns=["Kind", "Type", "Tax kind", "Honest note"], rows=IDEAS,
                                    buttons=[{"label": "Add one", "say": "Add an income stream."}]))


def income_log(settings: Settings, args: dict) -> str:
    data = st.load(settings)
    s = _find_or_error(data, args)
    if s.get("link"):
        raise ValueError(f"{s['name']} reads its money from {s['link']}, so add it there instead of typing it twice.")
    day = st.entry_date(args)
    if day > hs.today():
        raise ValueError("That date is in the future. Log money once it has come in.")
    row = {"id": st.new_id(data), "stream": s["id"], "date": day.isoformat(), "amount": st.money(args.get("amount")),
           "costs": st.money(args.get("costs"), "costs", True) if args.get("costs") else 0.0,
           "note": hs.clean(args.get("note"), 120)}
    st.put(data["entries"], row)
    st.save(settings, data)
    month = st.total(st.entries(settings, data), s["id"], {st.month_of(day)})
    return f"Logged {st.gbp(row['amount'])} for {s['name']} in {st.month_long(st.month_of(day))} (entry {row['id']}). That stream is at {st.gbp(month)} for the month."


def income_list(settings: Settings, args: dict) -> screen.Shown:
    data = st.load(settings)
    st.need_streams(data)
    rows = st.entries(settings, data)
    if args.get("stream"):
        sid = st.stream(data, args["stream"])["id"]
        rows = [e for e in rows if e["stream"] == sid]
    if args.get("month"):
        key = st.parse_month(args["month"])
        rows = [e for e in rows if e["month"] == key]
    rows.sort(key=lambda e: e["date"], reverse=True)
    if not rows:
        return screen.Shown("Nothing logged for that yet.", screen.card("table", "Money in", "incomestreams-income",
                                                                       columns=["Date"], rows=[]))
    table = [[e["id"] if e["id"] else "linked", e["date"], st.name_of(data, e["stream"]), st.gbp(e["amount"]),
              st.gbp(e["costs"]) if e["costs"] else "", e["note"]] for e in rows[:60]]
    return screen.Shown(f"{len(rows)} entries, {st.gbp(sum(e['amount'] for e in rows))} in total.",
                        screen.card("table", "Money in", "incomestreams-income",
                                    columns=["No.", "Date", "Stream", "In", "Costs", "Note"], rows=table))


def income_edit(settings: Settings, args: dict) -> str:
    data = st.load(settings)
    e = st.by_id(data["entries"], args.get("id"), "entry")
    if args.get("amount") is not None:
        e["amount"] = st.money(args["amount"])
    if args.get("costs") is not None:
        e["costs"] = st.money(args["costs"], "costs", True)
    if args.get("note") is not None:
        e["note"] = hs.clean(args["note"], 120)
    st.save(settings, data)
    return f"Updated entry {e['id']}: {st.gbp(e['amount'])} for {st.name_of(data, e['stream'])}."


def income_remove(settings: Settings, args: dict) -> str:
    data = st.load(settings)
    e = st.by_id(data["entries"], args.get("id"), "entry")
    if not args.get("confirmed"):
        return st.confirm_needed(f"entry {e['id']} ({st.gbp(e['amount'])} for {st.name_of(data, e['stream'])})")
    data["entries"].remove(e)
    st.save(settings, data)
    return f"Removed entry {e['id']}."


def hours_log(settings: Settings, args: dict) -> str:
    data = st.load(settings)
    s = _find_or_error(data, args)
    hours = hs.number(args.get("hours"), "hours", 0.01, 744)
    day = st.entry_date(args)
    st.put(data["hours"], {"id": st.new_id(data), "stream": s["id"], "month": st.month_of(day), "hours": round(hours, 2),
                           "date": day.isoformat(), "note": hs.clean(args.get("note"), 80)})
    st.save(settings, data)
    total = st.hours_total(data, s["id"], {st.month_of(day)})
    return f"Logged {hours:g} hours on {s['name']}. That is {total:g} hours in {st.month_long(st.month_of(day))}."


def hours_list(settings: Settings, args: dict) -> screen.Shown:
    data = st.load(settings)
    st.need_streams(data)
    months = st.months_back(6)
    rows = st.entries(settings, data)
    table = []
    for s in data["streams"]:
        per = _per_hour(data, rows, s["id"], months)
        table.append([s["name"], f"{st.hours_total(data, s['id'], set(months)):g}", st.gbp(st.total(rows, s["id"], set(months))),
                      st.gbp(per) if per is not None else "-"])
    return screen.Shown("Hours and money per stream over the last six months.",
                        screen.card("table", "Hours per stream (6 months)", "incomestreams-hours",
                                    columns=["Stream", "Hours", "Money in", "Per hour (after costs)"], rows=table))


def link_check(settings: Settings, args: dict) -> screen.Shown:
    data = st.load(settings)
    ledger = [e for e in hs.load(settings, "creatorbiz-ledger.json", []) if isinstance(e, dict) and e.get("kind") == "income"]
    sales = hs.load(settings, "digitalproducts.json", {}).get("sales")
    sales = sales if isinstance(sales, list) else []
    cats: dict[str, float] = {}
    for e in ledger:
        cats[str(e.get("category") or "other")] = cats.get(str(e.get("category") or "other"), 0) + float(e.get("amount") or 0)
    table = [[f"Creator business: {c}", st.gbp(v), "Add a stream with link creatorbiz and link_category " + c] for c, v in cats.items()]
    if sales:
        table.append(["Digital product sales", st.gbp(sum(float(x.get("amount", x.get("price", 0)) or 0) for x in sales if isinstance(x, dict))),
                      "Add a stream with link digitalproducts"])
    linked = [f"{s['name']} reads from {s['link']}" for s in data["streams"] if s.get("link")]
    if not table:
        return screen.Shown("I found no creator income or product sales saved yet, so type your money in by hand.",
                            screen.card("list", "Linked income", "incomestreams-links", items=linked or ["Nothing to link yet."]))
    return screen.Shown("I can read these totals (read-only) into streams. Don't also type the same money by hand.",
                        screen.card("table", "Income I can read", "incomestreams-links", columns=["Found", "Total", "How"],
                                    rows=table))


def tool_definitions() -> list[dict]:
    return [{
        "name": "income_streams",
        "description": "Register and log all the user's extra income streams (TikTok creator fund, brand deals, affiliate, "
                       "digital products, reselling, freelance, rent a room, interest, anything) in GBP. action: stream_add "
                       "(name, type active|passive|mixed, tax_kind trading|property|interest|other, note, link creatorbiz|"
                       "digitalproducts, link_category) / stream_list / stream_show (stream) / stream_edit (stream, new_name, "
                       "type, tax_kind, note, link) / stream_status (stream, status active|paused|ended) / stream_remove "
                       "(stream, confirmed only after yes) / stream_ideas; income_log (stream, amount, costs, month YYYY-MM or "
                       "date, note) / income_list (stream, month) / income_edit (id, amount, costs, note) / income_remove "
                       "(id, confirmed only after yes); hours_log (stream, hours, month or date) / hours_list; link_check = "
                       "what creatorbiz or digitalproducts files can feed in (read-only). Never promises income.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "stream": {"type": "string", "description": "Stream name or number."},
                "name": {"type": "string"},
                "new_name": {"type": "string"},
                "type": {"type": "string", "enum": ["active", "passive", "mixed"]},
                "tax_kind": {"type": "string", "enum": st.TAX_KINDS},
                "status": {"type": "string", "enum": st.STATUSES},
                "note": {"type": "string"},
                "link": {"type": "string", "description": "creatorbiz, digitalproducts or none."},
                "link_category": {"type": "string", "description": "Only creator ledger income with this category, e.g. affiliate."},
                "amount": {"type": "number", "description": "Pounds in."},
                "costs": {"type": "number", "description": "Pounds spent earning it."},
                "hours": {"type": "number"},
                "month": {"type": "string", "description": "YYYY-MM, this month or last month."},
                "date": {"type": "string", "description": "YYYY-MM-DD or today."},
                "id": {"type": "integer"},
                "confirmed": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


def run_tool(name: str, args: dict, settings: Settings, http=None):
    found = {"stream_add": stream_add, "stream_list": stream_list, "stream_show": stream_show, "stream_edit": stream_edit,
             "stream_status": stream_status, "stream_remove": stream_remove, "stream_ideas": stream_ideas,
             "income_log": income_log, "income_list": income_list, "income_edit": income_edit,
             "income_remove": income_remove, "hours_log": hours_log, "hours_list": hours_list,
             "link_check": link_check}.get(args.get("action"))
    if found is None:
        raise ValueError("I can't do that one.")
    return found(settings, args)
