"""Creator money: a rate card estimate from your own numbers, invoices (GBP) with paid/unpaid/overdue tracking, chase
drafts, and an income and expenses ledger with summaries per deal, month and tax year.

Rate cards pop up as "creatorbiz-ratecard" and invoices as "creatorbiz-invoices" (frontend/popup-creatorbiz.js).
Everything is an estimate from numbers you typed; nothing is a promise of income and UK tax notes are general
guidance only (check GOV.UK). Invoices are saved as Markdown files in the "Creator business" folder; nothing is sent.
"""

from datetime import date, timedelta

import creatorbiz_store as cb
import screen
from config import Settings

RATE_KIND = "creatorbiz-ratecard"
INVOICE_KIND = "creatorbiz-invoices"
screen.EXTRA_KINDS.update({RATE_KIND, INVOICE_KIND})
NAMES = {"creator_money"}
ACTIONS = ["rate_card", "save_rates", "package_quote", "invoice_create", "invoices", "invoice_show", "mark_paid", "overdue",
           "chase_draft", "invoice_due_date", "remove_invoice", "add_income", "add_expense", "expenses", "deal_summary",
           "month_summary", "tax_year_summary"]
# Rough starting multipliers (my assumptions, editable by asking for different numbers), relative to one main video.
FORMATS = {"main video or reel": 1.0, "short video (TikTok)": 1.0, "photo post": 0.6, "story set": 0.4, "YouTube mention": 0.7}
USAGE_UPLIFT = 0.30
EXCLUSIVITY_UPLIFT = 0.25
RUSH_UPLIFT = 0.20
DEFAULT_CPM = (10.0, 25.0)
EXPENSE_CATEGORIES = ["equipment", "software", "props and supplies", "travel", "editing help", "fees", "other"]


def _profile(settings: Settings) -> dict:
    return cb.load(settings, cb.PROFILE, {})


def _rates(settings: Settings, args: dict) -> dict:
    prof = _profile(settings)
    views = args.get("avg_views") or prof.get("avg_views")
    if not views:
        raise ValueError("Tell me your typical views per video first, and optionally your hourly rate.")
    return {"avg_views": int(views), "cpm_low": float(args.get("cpm_low") or prof.get("cpm_low") or DEFAULT_CPM[0]),
            "cpm_high": float(args.get("cpm_high") or prof.get("cpm_high") or DEFAULT_CPM[1]),
            "hourly": float(args.get("hourly_rate") or prof.get("hourly_rate") or 0),
            "hours": float(args.get("hours") or prof.get("hours") or 4)}


def _price(rates: dict, factor: float, usage: bool = False, exclusive: bool = False, rush: bool = False) -> tuple[int, int]:
    uplift = 1 + USAGE_UPLIFT * usage + EXCLUSIVITY_UPLIFT * exclusive + RUSH_UPLIFT * rush
    low = rates["avg_views"] / 1000 * rates["cpm_low"] * factor * uplift
    high = rates["avg_views"] / 1000 * rates["cpm_high"] * factor * uplift
    floor = rates["hourly"] * rates["hours"] * factor * (1 + rush * RUSH_UPLIFT)
    return round(max(low, floor)), round(max(high, floor))


def _rate_card(rates: dict, note: str = "") -> screen.Shown:
    rows = [{"format": name, "low": _price(rates, f)[0], "high": _price(rates, f)[1]} for name, f in FORMATS.items()]
    extras = [f"Paid ads or brand reuse of your content: about +{int(USAGE_UPLIFT * 100)}%",
              f"Exclusivity (no rival brands): about +{int(EXCLUSIVITY_UPLIFT * 100)}%", f"Rush job: about +{int(RUSH_UPLIFT * 100)}%"]
    first = rows[0]
    return screen.Shown(f"{note}Rate card estimate: a main video is roughly £{first['low']} to £{first['high']}. {cb.HONEST}", screen.card(
        RATE_KIND, "Rate card estimate", "creatorbiz-ratecard",
        data={"rows": rows, "extras": extras, "views": rates["avg_views"], "cpm": [rates["cpm_low"], rates["cpm_high"]],
              "note": "From your typical views and per-1,000-view rates. " + cb.HONEST + " Brands may pay less, more, or nothing."},
        buttons=[{"label": "Price a package", "say": "Quote a package of two videos and a story set with usage rights."},
                 {"label": "Media kit", "say": "Build my media kit."}]))


def rate_card(settings: Settings, args: dict) -> screen.Shown:
    return _rate_card(_rates(settings, args))


def save_rates(settings: Settings, args: dict) -> screen.Shown:
    prof = _profile(settings)
    for key in ("avg_views", "cpm_low", "cpm_high", "hourly_rate", "hours"):
        if args.get(key) is not None:
            if float(args[key]) < 0:
                raise ValueError(f"That {key.replace('_', ' ')} doesn't look right.")
            prof[key] = float(args[key]) if key != "avg_views" else int(args[key])
    cb.save(settings, cb.PROFILE, prof)
    return _rate_card(_rates(settings, {}), "Saved your rate numbers. ")


def package_quote(settings: Settings, args: dict) -> screen.Shown:
    rates = _rates(settings, args)
    rows, low, high = [], 0, 0
    for name, factor in FORMATS.items():
        count = int(args.get("counts", {}).get(name, 0)) if isinstance(args.get("counts"), dict) else 0
        if count:
            lo, hi = _price(rates, factor, bool(args.get("usage_rights")), bool(args.get("exclusivity")), bool(args.get("rush")))
            rows.append([name, str(count), f"£{lo * count}-£{hi * count}"])
            low, high = low + lo * count, high + hi * count
    if not rows:
        raise ValueError("Which pieces are in the package? Give counts per format, e.g. main video or reel: 2.")
    discount = float(args.get("discount_pct") or 0)
    if not 0 <= discount < 100:
        raise ValueError("A discount should be between 0 and 99 percent.")
    low, high = round(low * (1 - discount / 100)), round(high * (1 - discount / 100))
    rows.append(["Total" + (f" (after {discount:g}% off)" if discount else ""), "", f"£{low}-£{high}"])
    return screen.Shown(f"That package comes out at roughly £{low} to £{high}. {cb.HONEST}", screen.card(
        "table", "Package quote (estimate)", "creatorbiz-package", columns=["Item", "Number", "Estimate"], rows=rows,
        buttons=[{"label": "Contract checklist", "say": "Show me the contract checklist."}]))


def _invoices(settings: Settings) -> list[dict]:
    return [i for i in cb.load(settings, cb.INVOICES, []) if isinstance(i, dict)]


def _status(i: dict) -> str:
    if i.get("paid"):
        return "paid"
    return "overdue" if date.fromisoformat(i["due"]) < cb.today() else "unpaid"


def _pick_invoice(rows: list[dict], args: dict) -> dict:
    if args.get("number"):
        key = cb.find([i["number"] for i in rows], args["number"])
        hits = [i for i in rows if i["number"] == key]
    else:
        name = cb.need(args.get("brand"), "invoice number or brand").lower()
        hits = [i for i in rows if name in i["brand"].lower() and not i.get("paid")] or [i for i in rows if name in i["brand"].lower()]
    if not hits:
        raise ValueError("I can't find that invoice.")
    if len(hits) > 1:
        raise ValueError(f"{len(hits)} invoices match; give the invoice number.")
    return hits[0]


def _invoice_text(i: dict, prof: dict) -> str:
    lines = [f"# Invoice {i['number']}", "", f"From: {prof.get('name') or 'Your name'}", f"To: {i['brand']}",
             f"Issued: {cb.long_date(date.fromisoformat(i['issued']))}", f"Payment due: {cb.long_date(date.fromisoformat(i['due']))}", "",
             "| Description | Amount |", "| --- | ---: |"]
    lines += [f"| {x['description']} | {cb.gbp(x['amount'])} |" for x in i["items"]]
    lines.append(f"| Subtotal | {cb.gbp(i['subtotal'])} |")
    if i["vat_percent"]:
        lines.append(f"| VAT {i['vat_percent']:g}% | {cb.gbp(i['total'] - i['subtotal'])} |")
    lines += [f"| **Total (GBP)** | **{cb.gbp(i['total'])}** |", ""]
    if prof.get("pay_to"):
        lines += [f"Please pay to: {prof['pay_to']}", ""]
    lines.append("Payment terms: " + f"{i['payment_days']} days from the invoice date." + (f" Ref: {i['campaign']}." if i.get("campaign") else ""))
    return "\n".join(lines) + "\n"


def _items(args: dict) -> list[dict]:
    raw = args.get("items") if isinstance(args.get("items"), list) else []
    if not raw and args.get("amount"):
        raw = [{"description": args.get("description") or "Content creation services", "amount": args["amount"]}]
    items = [{"description": cb.need(x.get("description"), "description", 120), "amount": cb.money(x.get("amount"), "line amount")}
             for x in raw if isinstance(x, dict)]
    if not items:
        raise ValueError("What is the invoice for, and how much in pounds?")
    return items[:20]


def invoice_create(settings: Settings, args: dict) -> screen.Shown:
    rows = _invoices(settings)
    brand = cb.need(args.get("brand"), "brand")
    items = _items(args)
    vat = float(args.get("vat_percent") or 0)
    if not 0 <= vat <= 30:
        raise ValueError("VAT should be between 0 and 30 percent.")
    subtotal = round(sum(x["amount"] for x in items), 2)
    prof = _profile(settings)
    days = int(args.get("payment_days") or 0)
    if not days:
        deal = next((d for d in cb.deals(settings) if d["brand"].lower() == brand.lower() and d.get("payment_days")), None)
        days = deal["payment_days"] if deal else 30
    issued = cb.parse_date(args.get("issued")) or cb.today()
    number = f"INV-{issued.year}-{sum(i['number'].startswith(f'INV-{issued.year}') for i in rows) + 1:03d}"
    inv = {"number": number, "brand": brand, "campaign": cb.clean(args.get("campaign"), 80), "items": items, "subtotal": subtotal,
           "vat_percent": vat, "total": round(subtotal * (1 + vat / 100), 2), "issued": issued.isoformat(), "payment_days": days,
           "due": (issued + timedelta(days=days)).isoformat(), "paid": ""}
    path = cb.write_file(settings, f"Invoice {number} - {brand}.md", _invoice_text(inv, prof))
    inv["file"] = path.name
    rows.append(inv)
    cb.save(settings, cb.INVOICES, rows)
    _stage_after(settings, brand, "invoiced", ("agreed", "delivered"))
    tip = "" if prof.get("pay_to") else " Add your payment details to your media kit profile so they appear on invoices."
    return screen.Shown(f"Invoice {number} for {cb.gbp(inv['total'])} is saved as {path.name}, due {cb.short(issued + timedelta(days=days))}.{tip}",
                        _invoice_card(rows))


def _stage_after(settings: Settings, brand: str, stage: str, from_stages: tuple) -> None:
    deals = cb.deals(settings)
    hits = [d for d in deals if d["brand"].lower() == brand.lower() and d["stage"] in from_stages]
    if len(hits) == 1:
        hits[0]["stage"] = stage
        hits[0].setdefault("history", []).append({"stage": stage, "date": cb.today().isoformat()})
        cb.save(settings, cb.DEALS, deals)


def _invoice_card(rows: list[dict], only: str = "") -> dict:
    shown = [i for i in rows if not only or _status(i) == only]
    data = [{"number": i["number"], "brand": i["brand"], "total": cb.gbp(i["total"]), "due": cb.short(date.fromisoformat(i["due"])),
             "status": _status(i)} for i in shown]
    owed = sum(i["total"] for i in rows if not i.get("paid"))
    return screen.card(INVOICE_KIND, "Creator invoices", "creatorbiz-invoices", data={"invoices": data, "owed": cb.gbp(owed)},
                       buttons=[{"label": "Overdue", "say": "Which invoices are overdue?"},
                                {"label": "This month", "say": "Show my creator income and expenses this month."}])


def invoices(settings: Settings, args: dict) -> screen.Shown | str:
    rows = _invoices(settings)
    if not rows:
        return "No invoices yet. Tell me a brand and an amount and I'll make one."
    status = cb.clean(args.get("status")).lower()
    if status and status not in ("paid", "unpaid", "overdue"):
        raise ValueError("Invoice status is paid, unpaid or overdue.")
    card = _invoice_card(rows, status)
    return screen.Shown(f"{len(card['data']['invoices'])} invoice{'s' * (len(card['data']['invoices']) != 1)}, {card['data']['owed']} still owed in total.", card)


def invoice_show(settings: Settings, args: dict) -> screen.Shown:
    i = _pick_invoice(_invoices(settings), args)
    text = _invoice_text(i, _profile(settings))
    return screen.Shown(f"Invoice {i['number']} to {i['brand']} for {cb.gbp(i['total'])} is {_status(i)}.", screen.card(
        "text", f"Invoice {i['number']}", f"creatorbiz-invoice-{i['number']}", text=text,
        buttons=[{"label": "Mark paid", "say": f"Invoice {i['number']} has been paid."}]))


def mark_paid(settings: Settings, args: dict) -> screen.Shown:
    rows = _invoices(settings)
    i = _pick_invoice(rows, args)
    if i.get("paid"):
        raise ValueError(f"Invoice {i['number']} is already marked paid.")
    day = cb.parse_date(args.get("date")) or cb.today()
    i["paid"] = day.isoformat()
    cb.save(settings, cb.INVOICES, rows)
    cb.add_ledger(settings, "income", i["total"], i["brand"], f"Invoice {i['number']}", "brand deal", day)
    _stage_after(settings, i["brand"], "paid", ("invoiced", "delivered", "agreed"))
    return screen.Shown(f"Marked invoice {i['number']} as paid and added {cb.gbp(i['total'])} to your income.", _invoice_card(rows))


def overdue(settings: Settings) -> screen.Shown | str:
    late = [i for i in _invoices(settings) if _status(i) == "overdue"]
    if not late:
        return "No invoices are overdue."
    late.sort(key=lambda i: i["due"])
    return screen.Shown(f"{len(late)} invoices are overdue, {cb.gbp(sum(i['total'] for i in late))} in total.",
                        _invoice_card(late))


def chase_draft(settings: Settings, args: dict) -> screen.Shown:
    i = _pick_invoice(_invoices(settings), args)
    if i.get("paid"):
        raise ValueError(f"Invoice {i['number']} is already paid.")
    level = min(max(int(args.get("level") or 1), 1), 3)
    days = (cb.today() - date.fromisoformat(i["due"])).days
    when = f"was due on {cb.long_date(date.fromisoformat(i['due']))}" if days > 0 else f"is due on {cb.long_date(date.fromisoformat(i['due']))}"
    who = _profile(settings).get("name") or "[Your name]"
    opening = {1: "I hope you're well. Just a friendly reminder that", 2: "I'm following up as I haven't yet received payment. As a reminder,",
               3: "This is my final reminder before I take further steps. Despite earlier messages,"}[level]
    lines = [f"Subject: Invoice {i['number']} - payment reminder", "", f"Hi {i['brand']} team,", "",
             f"{opening} invoice {i['number']} for {cb.gbp(i['total'])} {when}.", "",
             "Could you let me know when I can expect payment, or if you need anything from me to release it?"]
    if level == 3:
        lines += ["", "Under the Late Payment of Commercial Debts legislation, interest and fixed recovery costs may apply to overdue "
                      "business invoices. [Check GOV.UK for the current rules before quoting any figures.]"]
    lines += ["", "Thank you,", who]
    text = "\n".join(lines)
    path = cb.write_file(settings, f"Chase {i['number']} (draft).md", text + "\n")
    return screen.Shown(f"Here is a level {level} chase draft for invoice {i['number']}, saved as {path.name}. It is a draft; I have not sent anything.",
                        screen.card("text", f"Chase draft - {i['number']}", f"creatorbiz-chase-{i['number']}", text=text))


def invoice_due_date(args: dict) -> str:
    issued = cb.parse_date(args.get("issued")) or cb.today()
    days = int(args.get("payment_days") or 30)
    if not 0 < days <= 365:
        raise ValueError("Payment terms should be between 1 and 365 days.")
    due = issued + timedelta(days=days)
    return f"An invoice issued on {cb.long_date(issued)} with {days}-day terms is due on {due.strftime('%A')} {cb.long_date(due)}."


def remove_invoice(settings: Settings, args: dict) -> str:
    rows = _invoices(settings)
    i = _pick_invoice(rows, args)
    if not args.get("confirmed"):
        return f"Should I really remove invoice {i['number']} for {cb.gbp(i['total'])}? Say yes and I'll do it. The saved file stays."
    rows.remove(i)
    cb.save(settings, cb.INVOICES, rows)
    return f"Removed invoice {i['number']}."


def add_income(settings: Settings, args: dict) -> str:
    amount = cb.money(args.get("amount"), "income")
    cb.add_ledger(settings, "income", amount, cb.clean(args.get("brand")), cb.clean(args.get("note"), 120),
                  cb.clean(args.get("category"), 30) or "other", cb.parse_date(args.get("date")))
    return f"Logged {cb.gbp(amount)} of income" + (f" from {cb.clean(args.get('brand'))}." if args.get("brand") else ".")


def add_expense(settings: Settings, args: dict) -> str:
    amount = cb.money(args.get("amount"), "expense")
    category = cb.clean(args.get("category"), 30).lower() or "other"
    cb.add_ledger(settings, "expense", amount, cb.clean(args.get("brand")), cb.clean(args.get("note"), 120), category,
                  cb.parse_date(args.get("date")))
    return f"Logged a {cb.gbp(amount)} {category} expense. Keep the receipt."


def _total(rows: list[dict], kind: str) -> float:
    return round(sum(e["amount"] for e in rows if e["kind"] == kind), 2)


def expenses(settings: Settings, args: dict) -> screen.Shown | str:
    rows = [e for e in cb.ledger(settings) if e["kind"] == "expense"]
    if args.get("category"):
        rows = [e for e in rows if e["category"] == cb.clean(args["category"]).lower()]
    if not rows:
        return "No creator expenses logged yet."
    by: dict[str, float] = {}
    for e in rows:
        by[e["category"]] = by.get(e["category"], 0) + e["amount"]
    labels = sorted(by, key=by.get, reverse=True)[:12]
    return screen.Shown(f"You've logged {cb.gbp(sum(by.values()))} of creator expenses across {len(by)} categories.", screen.card(
        "chart", "Creator expenses by category", "creatorbiz-expenses",
        chart={"type": "bar", "labels": labels, "values": [round(by[k], 2) for k in labels], "unit": "£"}))


def deal_summary(settings: Settings, args: dict) -> screen.Shown:
    d = cb.pick_deal(cb.deals(settings), args.get("brand"), args.get("campaign"))
    mine = [e for e in cb.ledger(settings) if e["brand"].lower() == d["brand"].lower()]
    income, spent = _total(mine, "income"), _total(mine, "expense")
    invoiced = sum(i["total"] for i in _invoices(settings) if i["brand"].lower() == d["brand"].lower())
    net = round(income - spent, 2)
    rows = [["Quoted or agreed fee", cb.gbp(d.get("fee", 0))], ["Invoiced", cb.gbp(invoiced)], ["Received", cb.gbp(income)],
            ["Expenses", cb.gbp(spent)], ["Left after expenses", cb.gbp(net)]]
    return screen.Shown(f"{cb.deal_label(d)}: {cb.gbp(income)} received, {cb.gbp(spent)} spent, {cb.gbp(net)} left over.",
                        screen.card("table", f"Deal summary: {cb.deal_label(d)}", f"creatorbiz-summary-{d['brand']}",
                                    columns=["Item", "Amount"], rows=rows))


def _month_key(day: date) -> str:
    return day.strftime("%Y-%m")


def month_summary(settings: Settings, args: dict) -> screen.Shown:
    rows = cb.ledger(settings)
    month = cb.clean(args.get("month")) or _month_key(cb.today())
    mine = [e for e in rows if e["date"].startswith(month)]
    if len(month) != 7 or not month[:4].isdigit():
        raise ValueError("Give the month as YYYY-MM.")
    income, spent = _total(mine, "income"), _total(mine, "expense")
    labels, values = [], []
    cursor = date.fromisoformat(month + "-01")
    for _ in range(6):
        labels.insert(0, cursor.strftime("%b"))
        key = _month_key(cursor)
        values.insert(0, round(_total([e for e in rows if e["date"].startswith(key)], "income")
                               - _total([e for e in rows if e["date"].startswith(key)], "expense"), 2))
        cursor = (cursor - timedelta(days=1)).replace(day=1)
    return screen.Shown(f"{month}: {cb.gbp(income)} in, {cb.gbp(spent)} out, {cb.gbp(income - spent)} left.", screen.card(
        "chart", f"Creator income minus expenses, to {month}", "creatorbiz-months",
        chart={"type": "bar", "labels": labels, "values": values, "unit": "£"}))


def tax_year_summary(settings: Settings, args: dict) -> screen.Shown:
    today = cb.today()
    start_year = int(args.get("tax_year_start") or (today.year if (today.month, today.day) >= (4, 6) else today.year - 1))
    start, end = date(start_year, 4, 6), date(start_year + 1, 4, 5)
    mine = [e for e in cb.ledger(settings) if start.isoformat() <= e["date"] <= end.isoformat()]
    income, spent = _total(mine, "income"), _total(mine, "expense")
    rows = [["Income", cb.gbp(income)], ["Expenses", cb.gbp(spent)], ["Profit before tax", cb.gbp(income - spent)]]
    return screen.Shown(f"Tax year {start_year}/{str(start_year + 1)[2:]}: {cb.gbp(income)} in, {cb.gbp(spent)} expenses. "
                        "General information only; check GOV.UK or an accountant.", screen.card(
        "table", f"Tax year {start_year}/{str(start_year + 1)[2:]} (general, not tax advice)", "creatorbiz-taxyear",
        columns=["Item", "Amount"], rows=rows,
        buttons=[{"label": "UK tax basics", "say": "Explain UK tax basics for creators."}]))


def tool_definitions() -> list[dict]:
    return [{
        "name": "creator_money",
        "description": "A creator's money: rate card estimate from typed-in views and rates, package quotes, invoices in GBP "
                       "(create, list, paid/unpaid/overdue, mark paid, chase reminder draft), creator income and expenses, "
                       "profit per brand deal, monthly and UK tax-year summaries. Estimates only, never promises income. "
                       "Set confirmed only after the user says yes to remove an invoice.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "brand": {"type": "string"},
                "campaign": {"type": "string"},
                "number": {"type": "string", "description": "Invoice number like INV-2026-001."},
                "avg_views": {"type": "integer", "description": "Typical views per video, as the user says."},
                "cpm_low": {"type": "number", "description": "Pounds per 1,000 views, low end."},
                "cpm_high": {"type": "number", "description": "Pounds per 1,000 views, high end."},
                "hourly_rate": {"type": "number", "description": "Pounds per hour, sets a minimum price."},
                "hours": {"type": "number", "description": "Hours to make one main video."},
                "counts": {"type": "object", "description": "For package_quote: pieces per format, keys are 'main video or reel', "
                           "'short video (TikTok)', 'photo post', 'story set', 'YouTube mention'.",
                           "additionalProperties": {"type": "integer"}},
                "usage_rights": {"type": "boolean"}, "exclusivity": {"type": "boolean"}, "rush": {"type": "boolean"},
                "discount_pct": {"type": "number"},
                "items": {"type": "array", "description": "Invoice lines.", "items": {
                    "type": "object", "properties": {"description": {"type": "string"}, "amount": {"type": "number"}},
                    "required": ["description", "amount"], "additionalProperties": False}},
                "amount": {"type": "number", "description": "Pounds (single invoice line, income or expense)."},
                "description": {"type": "string"},
                "vat_percent": {"type": "number"},
                "payment_days": {"type": "integer"},
                "issued": {"type": "string", "description": "YYYY-MM-DD; default today."},
                "date": {"type": "string", "description": "YYYY-MM-DD, 'today' or 'yesterday'."},
                "status": {"type": "string", "enum": ["paid", "unpaid", "overdue"]},
                "level": {"type": "integer", "description": "Chase tone 1 (friendly) to 3 (firm)."},
                "category": {"type": "string", "description": "Expense category, e.g. equipment, software, travel."},
                "note": {"type": "string"},
                "month": {"type": "string", "description": "YYYY-MM."},
                "tax_year_start": {"type": "integer", "description": "Year the UK tax year starts, e.g. 2026 for 2026/27."},
                "confirmed": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


def run_tool(name: str, args: dict, settings: Settings, http=None):
    action = args.get("action")
    handlers = {"rate_card": rate_card, "save_rates": save_rates, "package_quote": package_quote, "invoice_create": invoice_create,
                "invoices": invoices, "invoice_show": invoice_show, "mark_paid": mark_paid, "chase_draft": chase_draft,
                "remove_invoice": remove_invoice, "add_income": add_income, "add_expense": add_expense, "expenses": expenses,
                "deal_summary": deal_summary, "month_summary": month_summary, "tax_year_summary": tax_year_summary}
    if action in handlers:
        return handlers[action](settings, args)
    if action == "overdue":
        return overdue(settings)
    if action == "invoice_due_date":
        return invoice_due_date(args)
    return invoices(settings, args)
