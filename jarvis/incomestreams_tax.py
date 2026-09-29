"""Income streams part 4: UK side-income helpers in plain words. General information only, never tax advice.

The 1,000 pound trading allowance tracker, Self Assessment dates, a rough set-aside pot at a percentage the user picks,
tax year summaries, a CSV for an accountant, a record-keeping checklist and a receipts log. Figures come from what the
user logged. Rules change, so every answer points to GOV.UK ("check current rules"); nothing is filed or sent.
"""

import csv
from datetime import date

import homestore as hs
import incomestreams_store as st
import memory
import screen
from config import Settings

NAMES = {"income_tax_uk"}
ACTIONS = ["allowance_tracker", "allowance_explained", "allowance_or_expenses", "deadlines", "register_help",
           "tax_year_dates", "setaside_set", "setaside_show", "setaside_add", "taxyear_summary", "taxyear_csv",
           "records_checklist", "records_tick", "receipts_add", "receipts_list", "receipts_remove", "what_counts",
           "allowable_costs", "payments_on_account", "gov_pointers"]
CHECK = "Rules change, so check GOV.UK for the current ones. This is general information, not tax advice."
RECORDS = ["Keep a record of every payment you receive, with date, amount and where it came from",
           "Keep receipts or invoices for things you bought to earn the money",
           "Keep bank statements or PayPal/Stripe reports that show the money coming in",
           "Note what each cost was for, and keep mileage or home-use notes if you claim them",
           "Keep gifts and free products you were sent for content, with what they were worth",
           "Keep a copy of contracts and brand-deal emails that show what you agreed",
           "Keep your records for at least 5 years after the 31 January deadline",
           "Work out your totals for the tax year (6 April to 5 April)",
           "Check whether you need to register for Self Assessment (deadline 5 October)",
           "Put some money aside for tax in a separate pot"]
PAGES = {"what_counts": ("What counts as extra income", [
    "Money for things you do: selling, freelancing, brand deals and creator payments usually count as trading income.",
    "Gifts and free products sent to you to promote them can count too, at their value.",
    "Money from selling your own used things (not to make a profit) is usually not taxed, but check GOV.UK.",
    "Rent from a room, savings interest and dividends have their own rules and allowances.",
    "The 1,000 pound trading allowance is about the money you receive before costs (gross)."]),
    "allowable_costs": ("Costs you might be able to deduct", [
        "Costs must be only for earning the money: equipment, software, materials, postage, platform fees, advertising.",
        "Shared costs (phone, internet, a home office) can usually only be claimed for the business share.",
        "Keep the receipt for every cost.",
        "You either use the 1,000 pound trading allowance or deduct real costs on the same income, not both.",
        "Ask an accountant or read GOV.UK 'Expenses if you're self-employed' before claiming anything."]),
    "payments_on_account": ("Payments on account", [
        "If your Self Assessment bill is over 1,000 pounds, HMRC can ask for advance payments towards next year's bill.",
        "They are due on 31 January and 31 July, each usually half of last year's bill.",
        "It can feel like paying twice the first time; the set-aside pot helps with that.",
        "Only pay what your HMRC account says you owe. Check the details on GOV.UK."]),
    "gov_pointers": ("Where to check on GOV.UK", [
        "Search GOV.UK for: 'Tax-free allowances on property and trading income'.",
        "Search GOV.UK for: 'Register for Self Assessment' (new sole traders and side-income earners).",
        "Search GOV.UK for: 'Self Assessment tax returns deadlines'.",
        "Search GOV.UK for: 'Rent a Room Scheme' and 'Personal Savings Allowance'.",
        "Search GOV.UK for: 'Working for yourself: what records to keep'.",
        "Only use the real GOV.UK site and never pay anyone who contacts you out of the blue about tax."])}


def _kind_rows(data: dict, rows: list, kinds: tuple, year: int) -> tuple[float, float]:
    a, b = (d.isoformat() for d in st.tax_range(year))
    gross = costs = 0.0
    for s in data["streams"]:
        if s["tax_kind"] in kinds:
            gross += st.total(rows, s["id"], since=a, until=b)
            costs += st.total(rows, s["id"], since=a, until=b, field="costs")
    return round(gross, 2), round(costs, 2)


def allowance_tracker(settings: Settings, args: dict) -> screen.Shown:
    data = st.load(settings)
    st.need_streams(data)
    year = st.pick_tax_year(args)
    rows = st.entries(settings, data)
    trade, _ = _kind_rows(data, rows, ("trading", "other"), year)
    prop, _ = _kind_rows(data, rows, ("property",), year)
    interest, _ = _kind_rows(data, rows, ("interest",), year)
    bars = [{"label": "Trading and other side income", "value": min(trade, st.ALLOWANCE), "max": st.ALLOWANCE,
             "text": f"{st.gbp(trade)} of {st.gbp(st.ALLOWANCE)}", "warn": trade > st.ALLOWANCE},
            {"label": "Property income (rent)", "value": min(prop, st.ALLOWANCE), "max": st.ALLOWANCE,
             "text": f"{st.gbp(prop)} of {st.gbp(st.ALLOWANCE)}", "warn": prop > st.ALLOWANCE}]
    if interest:
        bars.append({"label": "Savings interest (own rules)", "value": interest, "max": max(interest, st.ALLOWANCE),
                     "text": st.gbp(interest)})
    left = st.ALLOWANCE - trade
    said = (f"Tax year {st.tax_label(year)}: {st.gbp(trade)} of trading income against the {st.gbp(st.ALLOWANCE)} allowance, "
            + (f"{st.gbp(left)} to go before you'd need to register." if left >= 0 else
               f"over by {st.gbp(-left)}, so you may need to register for Self Assessment; check GOV.UK."))
    return screen.Shown(said + " " + CHECK, st.bars_card(f"Trading allowance {st.tax_label(year)}", "incomestreams-allowance", bars,
                                                         CHECK, [{"label": "Explain it", "say": "Explain the trading allowance."},
                                                                 {"label": "Deadlines", "say": "Show my tax deadlines."}]))


def _page(kind: str, settings: Settings, args: dict) -> screen.Shown:
    title, points = PAGES[kind]
    return screen.Shown(f"{title}: {len(points)} points on the screen. {CHECK}",
                        screen.card("list", title, f"incomestreams-{kind}", items=points + [CHECK]))


def what_counts(settings: Settings, args: dict):
    return _page("what_counts", settings, args)


def allowable_costs(settings: Settings, args: dict):
    return _page("allowable_costs", settings, args)


def payments_on_account(settings: Settings, args: dict):
    return _page("payments_on_account", settings, args)


def gov_pointers(settings: Settings, args: dict):
    return _page("gov_pointers", settings, args)


def allowance_explained(settings: Settings, args: dict) -> screen.Shown:
    points = ["The trading allowance lets you have up to 1,000 pounds of side-hustle income in a tax year without telling HMRC or paying tax on it.",
              "It counts the money you receive before costs, added up across all your side hustles.",
              "Over 1,000 pounds, you usually register for Self Assessment and either take 1,000 off your income or deduct your real costs, whichever is better for you.",
              "There is a separate 1,000 pound property allowance, and Rent a Room and savings interest have their own rules.",
              "It can't be used against income from your employer or a partnership you're in.", CHECK]
    return screen.Shown("The 1,000 pound trading allowance in plain words. " + CHECK,
                        screen.card("list", "The trading allowance", "incomestreams-allowance-explained", items=points,
                                    buttons=[{"label": "Track mine", "say": "How much of my trading allowance have I used?"}]))


def allowance_or_expenses(settings: Settings, args: dict) -> screen.Shown:
    data = st.load(settings)
    rows = st.entries(settings, data)
    year = st.pick_tax_year(args)
    g0, c0 = _kind_rows(data, rows, ("trading", "other"), year)
    gross = st.money(args["gross"], "income", True) if args.get("gross") is not None else g0
    costs = st.money(args["costs"], "costs", True) if args.get("costs") is not None else c0
    allowance = max(0.0, gross - st.ALLOWANCE)
    expenses = max(0.0, gross - costs)
    better = "the allowance" if allowance <= expenses else "deducting your real costs"
    rows_out = [["Income (before costs)", st.gbp(gross)], ["Real costs", st.gbp(costs)],
                ["Taxable if you use the allowance", st.gbp(allowance)], ["Taxable if you deduct real costs", st.gbp(expenses)]]
    said = ("Under the allowance, so probably nothing to report; check GOV.UK." if gross <= st.ALLOWANCE else
            f"On these numbers {better} leaves less to be taxed: {st.gbp(min(allowance, expenses))} instead of "
            f"{st.gbp(max(allowance, expenses))}.")
    return screen.Shown(said + " " + CHECK, screen.card("table", "Allowance or real costs?", "incomestreams-allowance-or",
                                                        columns=["", "Amount"], rows=rows_out))


def _events(year: int) -> list[tuple[date, str]]:
    return [(date(year + 1, 1, 31), f"Payment on account for {st.tax_label(year)} (only if HMRC asked for them)"),
            (date(year + 1, 7, 31), f"Second payment on account for {st.tax_label(year)} (only if asked)"),
            (date(year + 1, 10, 5), f"Register for Self Assessment for {st.tax_label(year)} if you need to"),
            (date(year + 1, 10, 31), f"Paper tax return for {st.tax_label(year)} (online is later)"),
            (date(year + 2, 1, 31), f"File the {st.tax_label(year)} return online AND pay what you owe")]


def deadlines(settings: Settings, args: dict) -> screen.Shown:
    today = hs.today()
    start = st.tax_start(today)
    found = sorted({e for y in (start - 1, start) for e in _events(y) if e[0] >= today})[:int(hs.number(args.get("count") or 6, "count", 1, 12))]
    items = [{"label": f"{d.day} {d.strftime('%B %Y')} ({(d - today).days} days): {what}", "say": ""} for d, what in found]
    nxt = found[0]
    return screen.Shown(f"Next date: {nxt[0].day} {nxt[0].strftime('%B %Y')}, in {(nxt[0] - today).days} days. "
                        "Key dates: 5 October register, 31 October paper return, 31 January file and pay, 31 July second "
                        "payment on account. " + CHECK,
                        screen.card("list", "Self Assessment dates", "incomestreams-deadlines", items=items + [CHECK],
                                    buttons=[{"label": "How to register", "say": "How do I register for Self Assessment?"}]))


def register_help(settings: Settings, args: dict) -> screen.Shown:
    today = hs.today()
    year = today.year if today <= date(today.year, 10, 5) else today.year + 1
    deadline = date(year, 10, 5)
    points = [f"If you earned over 1,000 pounds of trading income in a tax year, you usually need to register by 5 October after that tax year ends (next: {deadline.day} October {deadline.year}, {(deadline - today).days} days).",
              "You register on GOV.UK ('Register for Self Assessment'); it can take a couple of weeks to get your Unique Taxpayer Reference in the post.",
              "You'll need your National Insurance number and the date you started earning.",
              "Under 1,000 pounds gross: you usually don't need to register, but check GOV.UK.",
              "Never pay a website that isn't GOV.UK to register.", CHECK]
    return screen.Shown(f"Register for Self Assessment by 5 October if you need to: {(deadline - today).days} days from now. " + CHECK,
                        screen.card("list", "Registering for Self Assessment", "incomestreams-register", items=points))


def tax_year_dates(settings: Settings, args: dict) -> screen.Shown:
    year = st.pick_tax_year(args)
    a, b = st.tax_range(year)
    rows = [["Tax year", st.tax_label(year)], ["Starts", f"{a.day} {a.strftime('%B %Y')}"], ["Ends", f"{b.day} {b.strftime('%B %Y')}"],
            ["Days left", str(max(0, (b - hs.today()).days))]]
    return screen.Shown(f"The {st.tax_label(year)} tax year runs from 6 April {a.year} to 5 April {b.year}.",
                        screen.card("table", f"Tax year {st.tax_label(year)}", "incomestreams-taxdates", columns=["", ""], rows=rows))


def _pct(data: dict) -> float:
    return float(data["settings"].get("setaside_pct", st.DEFAULT_SETASIDE))


def setaside_set(settings: Settings, args: dict):
    data = st.load(settings)
    data["settings"]["setaside_pct"] = hs.number(args.get("percent"), "percentage", 0, 60)
    st.save(settings, data)
    return setaside_show(settings, {}, f"Set-aside rate is now {data['settings']['setaside_pct']:g}%. ")


def setaside_show(settings: Settings, args: dict, lead: str = "") -> screen.Shown:
    data = st.load(settings)
    year = st.pick_tax_year(args)
    rows, pct = st.entries(settings, data), _pct(data)
    gross, costs = _kind_rows(data, rows, ("trading", "other", "property"), year)
    profit = max(0.0, gross - costs)
    goal = round(profit * pct / 100, 2)
    a, b = (d.isoformat() for d in st.tax_range(year))
    put = round(sum(x["amount"] for x in data["setaside"] if a <= x["date"] <= b), 2)
    bars = [{"label": "Put aside so far", "value": min(put, goal), "max": goal or 1, "text": f"{st.gbp(put)} of {st.gbp(goal)}"}]
    note = (f"Rough pot: {pct:g}% of {st.gbp(profit)} profit. Your real bill depends on your total income and the allowance. "
            "You choose the percentage. " + CHECK)
    return screen.Shown(f"{lead}At {pct:g}% a rough pot for {st.tax_label(year)} is {st.gbp(goal)}; you've put aside {st.gbp(put)}. "
                        "This is a rough guide, not tax advice.",
                        st.bars_card(f"Tax pot {st.tax_label(year)}", "incomestreams-setaside", bars, note,
                                     [{"label": "Change %", "say": "Set my tax set-aside to 25 percent."}]))


def setaside_add(settings: Settings, args: dict) -> str:
    data = st.load(settings)
    day = hs.parse_day(args.get("date"))
    row = {"id": st.new_id(data), "date": day.isoformat(), "amount": st.money(args.get("amount"))}
    st.put(data["setaside"], row)
    st.save(settings, data)
    a, b = (d.isoformat() for d in st.tax_range(st.tax_start(day)))
    return f"Recorded {st.gbp(row['amount'])} moved into your tax pot. That's {st.gbp(sum(x['amount'] for x in data['setaside'] if a <= x['date'] <= b))} this tax year."


def _summary_rows(settings: Settings, data: dict, year: int) -> list[list]:
    rows = st.entries(settings, data)
    a, b = (d.isoformat() for d in st.tax_range(year))
    out = []
    for s in data["streams"]:
        g = st.total(rows, s["id"], since=a, until=b)
        c = st.total(rows, s["id"], since=a, until=b, field="costs")
        if g or c:
            out.append([s["name"], s["tax_kind"], g, c, round(g - c, 2)])
    return out


def taxyear_summary(settings: Settings, args: dict) -> screen.Shown:
    data = st.load(settings)
    year = st.pick_tax_year(args)
    out = _summary_rows(settings, data, year)
    table = [[n, k, st.gbp(g), st.gbp(c), st.gbp(p)] for n, k, g, c, p in out]
    gross, costs = sum(r[2] for r in out), sum(r[3] for r in out)
    trade, _ = _kind_rows(data, st.entries(settings, data), ("trading", "other"), year)
    table.append(["Total", "", st.gbp(gross), st.gbp(costs), st.gbp(gross - costs)])
    table.append(["Trading allowance", "", f"{st.gbp(trade)} of {st.gbp(st.ALLOWANCE)}", "", ""])
    return screen.Shown(f"Tax year {st.tax_label(year)}: {st.gbp(gross)} in, {st.gbp(costs)} costs, {st.gbp(gross - costs)} left before tax. "
                        + CHECK, screen.card("table", f"Tax year {st.tax_label(year)} (general, not tax advice)", "incomestreams-taxyear",
                                             columns=["Stream", "Tax kind", "In", "Costs", "Left"], rows=table,
                                             buttons=[{"label": "CSV for accountant", "say": "Export my income for my accountant."}]))


def taxyear_csv(settings: Settings, args: dict) -> screen.Shown:
    data = st.load(settings)
    year = st.pick_tax_year(args)
    a, b = (d.isoformat() for d in st.tax_range(year))
    rows = sorted((e for e in st.entries(settings, data) if a <= e["date"] <= b), key=lambda e: e["date"])
    if not rows:
        raise ValueError(f"Nothing is logged for the {st.tax_label(year)} tax year yet.")
    path = memory.unique_path(st.folder(settings) / f"income {st.tax_label(year).replace('/', '-')}.csv")
    types = {s["id"]: s for s in data["streams"]}
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Date", "Stream", "Type", "Tax kind", "Money in (GBP)", "Costs (GBP)", "Left (GBP)", "Note", "Source"])
        for e in rows:
            s = types.get(e["stream"], {})
            w.writerow([e["date"], s.get("name", ""), s.get("type", ""), s.get("tax_kind", ""), f"{e['amount']:.2f}",
                        f"{e['costs']:.2f}", f"{e['amount'] - e['costs']:.2f}", e["note"], e["source"]])
    return screen.Shown(f"Saved {len(rows)} rows for the {st.tax_label(year)} tax year as {path.name}. " + CHECK,
                        screen.file_card(settings, path))


def _ticked(data: dict, year: int) -> set[int]:
    return set(data["records"].get(str(year), []))


def records_checklist(settings: Settings, args: dict) -> screen.Shown:
    data = st.load(settings)
    year = st.pick_tax_year(args)
    ticked = _ticked(data, year)
    items = [{"label": f"{i}. {t}", "done": i in ticked,
              "say": f"{'Untick' if i in ticked else 'Tick'} record-keeping item {i} for tax year {year}."}
             for i, t in enumerate(RECORDS, 1)]
    return screen.Shown(f"Record-keeping checklist for {st.tax_label(year)}: {len(ticked)} of {len(RECORDS)} done. " + CHECK,
                        screen.card("list", f"Records {st.tax_label(year)}", f"incomestreams-records-{year}", items=items))


def records_tick(settings: Settings, args: dict) -> screen.Shown:
    data = st.load(settings)
    year = st.pick_tax_year(args)
    ticked = _ticked(data, year)
    for n in args.get("items") or []:
        if not 1 <= int(n) <= len(RECORDS):
            raise ValueError(f"The checklist has items 1 to {len(RECORDS)}.")
        (ticked.discard if args.get("done") is False else ticked.add)(int(n))
    data["records"][str(year)] = sorted(ticked)
    st.save(settings, data)
    return records_checklist(settings, args)


def receipts_add(settings: Settings, args: dict) -> str:
    data = st.load(settings)
    sid = st.stream(data, args["stream"])["id"] if args.get("stream") else None
    row = {"id": st.new_id(data), "date": hs.parse_day(args.get("date")).isoformat(), "what": hs.need(args.get("what"), "what it was for", 80),
           "amount": st.money(args.get("amount")), "stream": sid, "where": hs.clean(args.get("where"), 100)}
    st.put(data["receipts"], row)
    st.save(settings, data)
    return (f"Logged receipt {row['id']}: {row['what']}, {st.gbp(row['amount'])}"
            + (f" for {st.name_of(data, sid)}" if sid else "") + ". Keep the receipt itself for at least 5 years.")


def receipts_list(settings: Settings, args: dict) -> screen.Shown:
    data = st.load(settings)
    rows = sorted(data["receipts"], key=lambda r: r["date"], reverse=True)
    if args.get("tax_year_start"):
        a, b = (d.isoformat() for d in st.tax_range(st.pick_tax_year(args)))
        rows = [r for r in rows if a <= r["date"] <= b]
    if args.get("stream"):
        sid = st.stream(data, args["stream"])["id"]
        rows = [r for r in rows if r["stream"] == sid]
    table = [[r["id"], r["date"], r["what"], st.gbp(r["amount"]), st.name_of(data, r["stream"]) if r["stream"] else "", r["where"]]
             for r in rows[:60]]
    return screen.Shown(f"{len(rows)} receipts logged, {st.gbp(sum(r['amount'] for r in rows))} in total.",
                        screen.card("table", "Receipts", "incomestreams-receipts", columns=["No.", "Date", "For", "Cost", "Stream", "Where kept"],
                                    rows=table))


def receipts_remove(settings: Settings, args: dict) -> str:
    data = st.load(settings)
    r = st.by_id(data["receipts"], args.get("id"), "receipt")
    if not args.get("confirmed"):
        return st.confirm_needed(f"receipt {r['id']} ({r['what']})")
    data["receipts"].remove(r)
    st.save(settings, data)
    return f"Removed receipt {r['id']} from the log."


def tool_definitions() -> list[dict]:
    return [{
        "name": "income_tax_uk",
        "description": "UK side-income helpers in plain words, general info only, always say check GOV.UK. action: "
                       "allowance_tracker (GBP 1,000 trading allowance used this tax year) / allowance_explained / "
                       "allowance_or_expenses (gross, costs) / deadlines (5 Oct register, 31 Jan file and pay, 31 Jul) / "
                       "register_help / tax_year_dates / setaside_set (percent the user picks) / setaside_show / setaside_add "
                       "(amount moved into a tax pot) / taxyear_summary / taxyear_csv (file for an accountant) / "
                       "records_checklist / records_tick (items [numbers], done) / receipts_add (what, amount, date, stream, "
                       "where kept) / receipts_list / receipts_remove (id, confirmed only after yes) / what_counts / "
                       "allowable_costs / payments_on_account / gov_pointers. tax_year_start = year the tax year begins "
                       "(6 April). Never tax advice; nothing is filed or sent.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "tax_year_start": {"type": "integer", "description": "2026 means 2026/27."},
                "percent": {"type": "number"},
                "amount": {"type": "number"},
                "gross": {"type": "number"},
                "costs": {"type": "number"},
                "count": {"type": "integer"},
                "items": {"type": "array", "items": {"type": "integer"}},
                "done": {"type": "boolean"},
                "what": {"type": "string"},
                "stream": {"type": "string"},
                "where": {"type": "string", "description": "Where the receipt is kept."},
                "date": {"type": "string", "description": "YYYY-MM-DD or today."},
                "id": {"type": "integer"},
                "confirmed": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


def run_tool(name: str, args: dict, settings: Settings, http=None):
    found = {"allowance_tracker": allowance_tracker, "allowance_explained": allowance_explained,
             "allowance_or_expenses": allowance_or_expenses, "deadlines": deadlines, "register_help": register_help,
             "tax_year_dates": tax_year_dates, "setaside_set": setaside_set, "setaside_show": setaside_show,
             "setaside_add": setaside_add, "taxyear_summary": taxyear_summary, "taxyear_csv": taxyear_csv,
             "records_checklist": records_checklist, "records_tick": records_tick, "receipts_add": receipts_add,
             "receipts_list": receipts_list, "receipts_remove": receipts_remove, "what_counts": what_counts,
             "allowable_costs": allowable_costs, "payments_on_account": payments_on_account,
             "gov_pointers": gov_pointers}.get(args.get("action"))
    if found is None:
        raise ValueError("I can't do that one.")
    return found(settings, args)
