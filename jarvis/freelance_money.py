"""Freelance money: day and hourly rate from a target income, project prices and price options, payment schedules, real
rate on a finished job, rate rises, billable percentage, capacity and availability planning, and late payment help
(interest calculator, plain-words explainer, polite/firm/final drafts).

All maths uses the numbers you give (saved in freelance-profile.json). Nothing is a promise of income, and UK notes are
general guidance: check GOV.UK. Results pop up as "freelance-calc" or "freelance-meter". Drafts are never sent.
"""

import math
from datetime import date, timedelta

import freelance_store as st
import screen
from config import Settings

NAMES = {"freelance_money"}
TONES = ["polite", "firm", "final"]
ACTIONS = ["set_numbers", "day_rate", "project_price", "price_options", "deposit_schedule", "real_rate", "rate_rise",
           "billable_percent", "capacity", "availability", "late_interest", "late_explainer", "late_draft"]
DEFAULTS = {"days_per_week": 5, "hours_per_day": 7.5, "holiday_weeks": 5, "bank_days": 8, "sick_days": 5, "billable_pct": 60, "overheads": 0}
NUMBER_KEYS = {"target_income": "target income", "overheads": "yearly overheads", "billable_pct": "billable percentage",
               "holiday_weeks": "holiday weeks", "bank_days": "bank holiday days", "sick_days": "sick days",
               "days_per_week": "days a week", "hours_per_day": "hours a day", "hourly_rate": "hourly rate", "day_rate": "day rate",
               "hours_week": "billable hours a week"}
GOV = "check GOV.UK for the current rules and rates"


def _p(settings: Settings, args: dict, key: str, default=None):
    """An argument, else the saved number, else the default."""
    if args.get(key) is not None:
        return st.number(args[key], NUMBER_KEYS.get(key, key), allow_zero=key not in ("target_income", "hours_per_day", "days_per_week"))
    return st.profile(settings).get(key, DEFAULTS.get(key, default))


def set_numbers(settings: Settings, args: dict) -> screen.Shown:
    saved = st.profile(settings)
    for key, what in NUMBER_KEYS.items():
        if args.get(key) is not None:
            saved[key] = st.number(args[key], what, allow_zero=key in ("overheads", "holiday_weeks", "bank_days", "sick_days"))
    if not saved:
        raise ValueError("Which numbers should I save? For example your target income, holiday weeks or billable percentage.")
    if saved.get("billable_pct", 0) > 100:
        raise ValueError("Billable percentage can't be over 100.")
    st.save(settings, st.PROFILE, saved)
    rows = [(NUMBER_KEYS[k].capitalize(), st.gbp(v) if k in ("target_income", "overheads", "hourly_rate", "day_rate") else st.num(v))
            for k, v in saved.items() if k in NUMBER_KEYS]
    return st.calc("Saved your freelance numbers.", "My freelance numbers", "Saved", "used by the rate and planning tools", rows,
                   ["Numbers you didn't give use plain defaults: 5 days a week, 7.5 hours a day, 5 weeks holiday, 8 bank holidays, 5 sick days, 60% billable."])


def day_rate(settings: Settings, args: dict) -> screen.Shown:
    target = _p(settings, args, "target_income")
    if target is None:
        raise ValueError("Tell me the yearly income you want to earn from freelancing, before tax.")
    overheads, pct = _p(settings, args, "overheads"), _p(settings, args, "billable_pct")
    holiday, bank, sick = _p(settings, args, "holiday_weeks"), _p(settings, args, "bank_days"), _p(settings, args, "sick_days")
    per_week, per_day = _p(settings, args, "days_per_week"), _p(settings, args, "hours_per_day")
    if not 0 < pct <= 100:
        raise ValueError("The billable percentage should be between 1 and 100.")
    working = (52 - holiday) * per_week - bank - sick
    billable = working * pct / 100
    if billable <= 0:
        raise ValueError("Those holidays leave no working days; check the numbers.")
    revenue = target + overheads
    day = revenue / billable
    hour = day / per_day
    if args.get("save"):
        saved = st.profile(settings)
        saved.update({"target_income": target, "hourly_rate": round(hour, 2), "day_rate": round(day, 2)})
        st.save(settings, st.PROFILE, saved)
    rows = [("Income wanted", st.gbp(target)), ("Overheads a year", st.gbp(overheads)), ("Needs to bill", st.gbp(revenue)),
            ("Working days", st.num(round(working, 1))), (f"Billable days at {st.num(pct)}%", st.num(round(billable, 1))),
            ("Day rate", st.gbp(round(day, 2))), ("Hourly rate", st.gbp(round(hour, 2)))]
    notes = ["Only billable days count: admin, chasing, marketing and quiet spells take up the rest.",
             "Your target is before tax and National Insurance, which come out of this. " + st.TAX_NOTE, st.HONEST]
    return st.calc(f"To earn {st.gbp(target)} you would charge about {st.gbp(round(day))} a day or {st.gbp(round(hour, 2))} an hour. {st.HONEST}",
                   "Day rate", f"{st.gbp(round(day))} a day", f"about {st.gbp(round(hour, 2))} an hour", rows, notes)


def project_price(settings: Settings, args: dict) -> screen.Shown:
    hours = st.number(args.get("hours"), "estimated hours")
    rate = _p(settings, args, "hourly_rate")
    if not rate:
        raise ValueError("Give your hourly rate, or work it out first with a day rate calculation.")
    buffer_pct = st.number(args["buffer_pct"], "buffer", True, 200) if args.get("buffer_pct") is not None else 15.0
    costs = st.number(args["costs"], "costs", True) if args.get("costs") is not None else 0.0
    fee = st.number(args["fee_pct"], "platform fee", True, 60) if args.get("fee_pct") is not None else 0.0
    work = hours * rate
    padded = work * (1 + buffer_pct / 100) + costs
    price = math.ceil(padded / (1 - fee / 100) / 5) * 5
    rounds = st.number(args["revision_rounds"], "revision rounds", True, 20) if args.get("revision_rounds") is not None else 2.0
    extra = round(rate * (args.get("round_hours") or 2), 2)
    rows = [("Your time", f"{st.num(hours)}h at {st.gbp(rate)} = {st.gbp(round(work, 2))}"),
            (f"Buffer {st.num(buffer_pct)}%", st.gbp(round(work * buffer_pct / 100, 2))), ("Costs", st.gbp(costs))]
    if fee:
        rows.append((f"Platform fee {st.num(fee)}%", st.gbp(round(price * fee / 100, 2))))
    rows += [("Price to quote", st.gbp(price)), (f"Includes {st.num(rounds)} rounds of changes", f"extra round {st.gbp(extra)}")]
    return st.calc(f"Quote about {st.gbp(price)} for {st.num(hours)} hours of work. {st.HONEST}", "Project price", st.gbp(price),
                   "rounded up to the next £5", rows, ["Estimate hours honestly, then add the buffer: jobs nearly always take longer.",
                                                        "Say clearly how many rounds of changes the price covers."])


def _tier(price: float) -> float:
    return round(price / 5) * 5


def price_options(settings: Settings, args: dict) -> screen.Shown:
    base = st.number(args.get("price"), "middle price")
    low = st.number(args["low_pct"], "lower option", True, 99) if args.get("low_pct") is not None else 25.0
    high = st.number(args["high_pct"], "higher option", True, 300) if args.get("high_pct") is not None else 35.0
    names = args.get("tiers") or ["Basic", "Standard", "Premium"]
    if len(names) != 3:
        raise ValueError("Give three option names, or leave them out.")
    prices = [_tier(base * (1 - low / 100)), _tier(base), _tier(base * (1 + high / 100))]
    rows = [(st.clean(n, 30), st.gbp(p)) for n, p in zip(names, prices)]
    return st.calc(f"Three options: {st.gbp(prices[0])}, {st.gbp(prices[1])} and {st.gbp(prices[2])}.", "Price options",
                   f"{st.gbp(prices[0])} / {st.gbp(prices[1])} / {st.gbp(prices[2])}", "lower, middle and higher option", rows,
                   ["Make each step up worth it: more deliverables, faster delivery or more rounds of changes, not just a bigger number.",
                    "Only offer options you would be happy to deliver."])


def deposit_schedule(settings: Settings, args: dict) -> screen.Shown:
    total = st.number(args.get("total"), "project total")
    dep = st.number(args["deposit_pct"], "deposit", True, 100) if args.get("deposit_pct") is not None else 30.0
    fin = st.number(args["final_pct"], "final payment", True, 100) if args.get("final_pct") is not None else 30.0
    steps = int(args.get("milestones") if args.get("milestones") is not None else 1)
    middle = 100 - dep - fin
    if middle < 0 or steps < 0 or steps > 10 or (steps == 0 and middle > 0):
        raise ValueError("The deposit and final payment can't add up to more than 100%, and milestones can't be negative.")
    start = st.parse_date(args.get("start")) or st.today()
    terms = int(args.get("terms_days") or 14)
    parts = [("Deposit", dep, "before work starts")] + [(f"Milestone {i + 1}", middle / steps, "when it is reached") for i in range(steps)]
    parts.append(("Final payment", fin, f"invoice on delivery, due {st.short(start + timedelta(days=terms))} if invoiced on {st.short(start)}"))
    rows = [(f"{n} ({st.num(round(pct, 1))}%)", f"{st.gbp(round(total * pct / 100, 2))}, {when}") for n, pct, when in parts if pct]
    return st.calc(f"A {st.num(dep)}% deposit on {st.gbp(total)} is {st.gbp(round(total * dep / 100, 2))}.", "Payment schedule", st.gbp(total),
                   "split across the project", rows, ["Put the schedule in your quote or terms so it is agreed before you start."])


def real_rate(settings: Settings, args: dict) -> screen.Shown:
    fee = st.number(args.get("fee"), "fee")
    hours = st.number(args.get("hours"), "hours actually spent")
    costs = st.number(args["costs"], "costs", True) if args.get("costs") is not None else 0.0
    rate = (fee - costs) / hours
    target = _p(settings, args, "hourly_rate")
    rows = [("Fee", st.gbp(fee)), ("Costs", st.gbp(costs)), ("Hours spent", st.num(hours)), ("You earned", f"{st.gbp(round(rate, 2))} an hour")]
    notes = ["Count every hour: emails, calls, changes and admin."]
    if target:
        gap = round(100 * (rate - target) / target)
        rows.append(("Your target", f"{st.gbp(target)} an hour"))
        notes.insert(0, f"That is {abs(gap)}% {'above' if gap >= 0 else 'below'} your target rate.")
    return st.calc(f"That job paid about {st.gbp(round(rate, 2))} an hour.", "Real hourly rate", f"{st.gbp(round(rate, 2))} an hour",
                   "fee minus costs, over hours", rows, notes)


def rate_rise(settings: Settings, args: dict) -> screen.Shown:
    current = st.number(args.get("current_rate"), "current rate")
    pct = st.number(args.get("rise_pct"), "rise percentage", top=200)
    new = round(current * (1 + pct / 100), 2)
    notice = int(args.get("notice_weeks") or 4)
    when = st.today() + timedelta(weeks=notice)
    yearly = st.number(args["hours_per_year"], "hours a year") if args.get("hours_per_year") else None
    who = st.clean(args.get("contact_name"), 40) or st.clean(args.get("client"), 60) or "there"
    body = (f"Hi {who},\n\nI wanted to give you plenty of notice that from {st.long_date(when)} my rate will change from "
            f"{st.gbp(current)} to {st.gbp(new)}. Work already agreed or quoted before then stays at the current price.\n\n"
            "Thank you for your business. I've enjoyed working together and hope to keep doing so. Please let me know "
            f"if you have any questions.\n\nThanks,\n{st.clean(args.get('my_name'), 40) or '[Your name]'}")
    rows = [("Current rate", st.gbp(current)), ("New rate", st.gbp(new)), ("Notice", f"{notice} weeks, from {st.short(when)}")]
    if yearly:
        rows.append(("Extra income a year", f"{st.gbp(round((new - current) * yearly))} if hours stay the same"))
    path = st.write_file(settings, f"Rate rise notice - {st.long_date(st.today())}.md", body)
    return screen.Shown(f"A {st.num(pct)}% rise takes you from {st.gbp(current)} to {st.gbp(new)}. Notice draft saved as {path.name}; nothing has been sent.",
                        screen.card(st.CALC, "Rate rise", "", data={"headline": st.gbp(new), "sub": f"up {st.num(pct)}%",
                                                                    "rows": [[a, b] for a, b in rows], "notes": ["Draft notice:", body]}))


def billable_percent(settings: Settings, args: dict) -> screen.Shown:
    first, last = st.month_bounds(args.get("month")) if args.get("month") else (None, None)
    if first is None:
        first = st.week_start(args.get("week"))
        last = first + timedelta(days=6)
    weeks = ((last - first).days + 1) / 7
    available = _p(settings, args, "days_per_week") * _p(settings, args, "hours_per_day")
    rows = st.entries(settings, first, last)
    if not rows:
        raise ValueError("No time logged in that period.")
    bill = sum(e["hours"] for e in rows if e["billable"])
    total = sum(e["hours"] for e in rows)
    cap = available * weeks
    goal = _p(settings, args, "billable_pct")
    pct = round(100 * bill / cap)
    rows_out = [{"label": "Billable hours", "used": round(bill, 2), "max": round(cap, 2), "text": f"{st.num(round(bill, 1))} of {st.num(round(cap, 1))}h = {pct}%"},
                {"label": "All logged hours", "used": round(total, 2), "max": round(cap, 2), "text": f"{st.num(round(total, 1))}h"}]
    return st.meter(f"{pct}% of your available hours were billable, against a plan of {st.num(goal)}%.", f"Billable hours: from {st.short(first)}",
                    rows_out, "Available hours are your days a week times hours a day; set them with your freelance numbers.")


def _committed(settings: Settings) -> tuple[float, list[dict]]:
    live, total = [], 0.0
    for p in st.projects(settings):
        if p["status"] in ("done", "paused") or not p["est_hours"]:
            continue
        left = max(p["est_hours"] - sum(e["hours"] for e in st.entries(settings) if e["project"].lower() == p["name"].lower()
                                        and e["client"].lower() == p["client"].lower()), 0)
        live.append({**p, "left": left})
        total += left
    return total, live


def _weekly_hours(settings: Settings, args: dict) -> float:
    if args.get("hours_week") is not None:
        return st.number(args["hours_week"], "hours a week", top=100)
    if st.profile(settings).get("hours_week"):
        return st.profile(settings)["hours_week"]
    return _p(settings, args, "days_per_week") * _p(settings, args, "hours_per_day") * _p(settings, args, "billable_pct") / 100


def capacity(settings: Settings, args: dict) -> screen.Shown:
    weeks = int(args.get("weeks") or 4)
    hours_week = _weekly_hours(settings, args)
    committed, live = _committed(settings)
    room = hours_week * weeks - committed
    buffer_pct = st.number(args["buffer_pct"], "buffer", True, 90) if args.get("buffer_pct") is not None else 20.0
    usable = max(room - hours_week * weeks * buffer_pct / 100, 0)
    rows = [("Billable hours a week", st.num(round(hours_week, 1))), (f"Hours over {weeks} weeks", st.num(round(hours_week * weeks, 1))),
            (f"Already promised ({len(live)} projects)", st.num(round(committed, 1))), ("Free hours", st.num(round(max(room, 0), 1))),
            (f"Free after {st.num(buffer_pct)}% buffer", st.num(round(usable, 1)))]
    headline = "Fully booked" if room <= 0 else f"{st.num(round(usable, 1))} spare hours"
    said = f"You have about {st.num(round(usable, 1))} hours spare over {weeks} weeks."
    if args.get("typical_hours"):
        typical = st.number(args["typical_hours"], "hours per project")
        n = int(usable // typical)
        rows.append((f"Projects of {st.num(typical)}h that fit", str(n)))
        said = f"About {n} more project{'s' if n != 1 else ''} of {st.num(typical)} hours would fit over the next {weeks} weeks."
    return st.calc(said, "Capacity", headline, f"next {weeks} weeks", rows,
                   ["Hours left on a project are its estimate minus time logged. Leave a buffer for admin and surprises.",
                    "Projects with no estimated hours aren't counted; add estimates for a truer picture."])


def availability(settings: Settings, args: dict) -> screen.Shown:
    weeks = min(int(args.get("weeks") or 4), 12)
    hours_week = _weekly_hours(settings, args)
    _, live = _committed(settings)
    start = st.week_start()
    load = [0.0] * weeks
    for p in live:
        span = max(1, math.ceil((date.fromisoformat(p["due"]) - start).days / 7)) if p["due"] else 4
        for i in range(min(span, weeks)):
            load[i] += p["left"] / span
    rows = []
    for i, h in enumerate(load):
        left = hours_week - h
        rows.append({"label": f"Week of {st.short(start + timedelta(weeks=i))}", "used": round(h, 1), "max": round(hours_week, 1),
                     "text": f"{st.num(round(h, 1))}h booked, " + (f"{st.num(round(left, 1))}h free" if left >= 0 else f"{st.num(round(-left, 1))}h over")})
    free_weeks = sum(1 for h in load if h < hours_week * 0.6)
    return st.meter(f"{free_weeks} of the next {weeks} weeks have plenty of room.", "Availability", rows,
                    "Spreads each project's remaining hours evenly up to its due date. A guide, not a promise.")


def _days(args: dict) -> tuple[int, date | None]:
    due = st.parse_date(args.get("due_date"), "due date")
    end = st.parse_date(args.get("paid_date"), "date") or st.today()
    if due:
        return max((end - due).days, 0), due
    if args.get("days_late") is None:
        raise ValueError("Give the invoice due date, or how many days late it is.")
    return int(st.number(args["days_late"], "days late", True, 5000)), None


def _compensation(amount: float) -> int:
    return 40 if amount < 1000 else 70 if amount < 10000 else 100


def late_interest(settings: Settings, args: dict) -> screen.Shown:
    amount = st.number(args.get("amount"), "invoice amount")
    days, _ = _days(args)
    if args.get("base_rate") is None:
        raise ValueError(f"Give the Bank of England base rate to use ({GOV}).")
    base = st.number(args["base_rate"], "base rate", True, 30)
    rate = 8 + base
    interest = round(amount * rate / 100 * days / 365, 2)
    fixed = _compensation(amount)
    rows = [("Invoice", st.gbp(amount)), ("Days late", str(days)), ("Interest rate", f"8% + {st.num(base)}% = {st.num(rate)}% a year"),
            ("Interest so far", st.gbp(interest)), ("Fixed recovery cost", st.gbp(fixed)), ("Extra you could claim", st.gbp(round(interest + fixed, 2)))]
    return st.calc(f"On {st.gbp(amount)}, {days} days late, statutory interest is about {st.gbp(interest)} plus {st.gbp(fixed)} fixed costs.",
                   "Late payment interest", st.gbp(round(interest + fixed, 2)), "an estimate for business-to-business invoices",
                   rows, [f"This is general guidance and only a rough calculation. Which base rate applies depends on the invoice date, so {GOV}.",
                          "It applies when a business pays another business or a public body, not a consumer. Your own written terms may set a different rate."],
                   [{"label": "Explain", "say": "Explain UK late payment interest for freelancers."}])


def late_explainer(settings: Settings, args: dict) -> screen.Shown:
    body = ("# Late payment of a freelance invoice in the UK\n\n"
            "This is general information, not legal advice. Check GOV.UK for the current rules and rates.\n\n"
            "**Who it covers.** If a business or public body pays another business late, the Late Payment of Commercial Debts "
            "(Interest) Act lets the supplier claim statutory interest and fixed recovery costs. It does not cover payments "
            "from ordinary consumers.\n\n"
            "**Interest.** The default rate is 8% a year on top of the Bank of England base rate, counted daily from when the "
            "invoice became due. GOV.UK explains which base rate applies.\n\n"
            "**Fixed costs.** A fixed sum per late invoice, on top of interest: £40 for debts under £1,000, £70 for £1,000 to "
            "£9,999.99 and £100 for £10,000 or more. Reasonable extra recovery costs may also be claimable.\n\n"
            "**Payment terms.** If nothing was agreed, payment is due within 30 days of the invoice or of delivery. Agreed terms "
            "should be fair and are limited by the Act.\n\n"
            "**Sensible steps.** Send a friendly reminder, then a firmer one, then a final notice that mentions interest and costs. "
            "Keep copies of the contract, invoice and messages. For bigger sums, ask for advice, for example from a business "
            "adviser or solicitor, before any formal step.")
    return screen.Shown("Here is a plain-words explainer on UK late payment interest. Check GOV.UK for current rates.",
                        screen.card("text", "Late payment explained", "freelance-late-explainer", text=body,
                                    buttons=[{"label": "Work it out", "say": "Work out the late payment interest on my invoice."}]))


def late_draft(settings: Settings, args: dict) -> screen.Shown:
    tone = args.get("tone") or "polite"
    if tone not in TONES:
        raise ValueError("The tone is one of " + ", ".join(TONES) + ".")
    client = st.client_name(settings, args.get("client"))
    who = st.clean(args.get("contact_name"), 40) or client
    ref = st.clean(args.get("invoice_ref"), 30) or "[invoice number]"
    amount = st.gbp(st.number(args["amount"], "amount")) if args.get("amount") is not None else "[amount]"
    due = st.parse_date(args.get("due_date"), "due date")
    late = f" It was due on {st.long_date(due)}." if due else ""
    days = (st.today() - due).days if due else 0
    me = st.clean(args.get("my_name"), 40) or "[Your name]"
    if tone == "polite":
        subject, text = (f"Invoice {ref}: a quick reminder",
                         f"Hi {who},\n\nI hope you're well. A quick reminder that invoice {ref} for {amount} is now unpaid.{late} "
                         "I'm sure it's just slipped through, but could you let me know when I can expect payment? "
                         "I'm happy to resend the invoice if that helps.\n\nThanks very much,\n" + me)
    elif tone == "firm":
        subject, text = (f"Invoice {ref}: payment overdue",
                         f"Hi {who},\n\nInvoice {ref} for {amount} is overdue{f' by {days} days' if days > 0 else ''}.{late} "
                         "I haven't had a reply to my earlier message. Please arrange payment within 7 days, or tell me by "
                         "return when it will be paid.\n\nThanks,\n" + me)
    else:
        subject, text = (f"Final reminder: invoice {ref}",
                         f"Dear {who},\n\nInvoice {ref} for {amount} remains unpaid{f', {days} days after it was due' if days > 0 else ''}. "
                         "Please pay it within 7 days. Where the Late Payment of Commercial Debts (Interest) Act applies, I may claim "
                         "statutory interest and fixed recovery costs on top of the amount owed. I would much prefer to settle this "
                         "without taking any further step, so please get in touch today if there is a problem.\n\nRegards,\n" + me)
    return st.draft(settings, f"{tone.title()} reminder: {client}", f"Subject: {subject}\n\n{text}",
                    f"Here is a {tone} payment reminder for {client}.", f"Late payment {tone} - {st.slug(client)}")


def tool_definitions() -> list[dict]:
    return [{
        "name": "freelance_money",
        "description": "Freelance pricing and planning in GBP: day rate and hourly rate from a target income (holidays, billable percentage, "
                       "overheads), project price with buffer, three price options, deposit schedule, real hourly rate on a job, rate rise "
                       "notice, billable percentage, how many projects fit (capacity), availability by week, UK late payment interest "
                       "calculator, late payment explainer, polite/firm/final chase drafts. Estimates only; drafts are never sent.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "target_income": {"type": "number", "description": "Yearly income wanted before tax."},
                "overheads": {"type": "number", "description": "Yearly business costs."},
                "billable_pct": {"type": "number", "description": "Percent of working days that are billable."},
                "holiday_weeks": {"type": "number"}, "bank_days": {"type": "number"}, "sick_days": {"type": "number"},
                "days_per_week": {"type": "number"}, "hours_per_day": {"type": "number"}, "hours_week": {"type": "number"},
                "hourly_rate": {"type": "number"}, "day_rate": {"type": "number"}, "save": {"type": "boolean", "description": "Keep the worked-out rate."},
                "hours": {"type": "number"}, "buffer_pct": {"type": "number"}, "costs": {"type": "number"}, "fee_pct": {"type": "number"},
                "revision_rounds": {"type": "number"}, "round_hours": {"type": "number"},
                "price": {"type": "number"}, "low_pct": {"type": "number"}, "high_pct": {"type": "number"},
                "tiers": {"type": "array", "items": {"type": "string"}, "description": "Three option names."},
                "total": {"type": "number"}, "deposit_pct": {"type": "number"}, "final_pct": {"type": "number"},
                "milestones": {"type": "integer"}, "start": {"type": "string"}, "terms_days": {"type": "integer"},
                "fee": {"type": "number"}, "current_rate": {"type": "number"}, "rise_pct": {"type": "number"},
                "notice_weeks": {"type": "integer"}, "hours_per_year": {"type": "number"},
                "week": {"type": "string"}, "month": {"type": "string", "description": "YYYY-MM."},
                "weeks": {"type": "integer"}, "typical_hours": {"type": "number", "description": "Hours a typical new project takes."},
                "amount": {"type": "number"}, "due_date": {"type": "string", "description": "YYYY-MM-DD."},
                "paid_date": {"type": "string"}, "days_late": {"type": "integer"},
                "base_rate": {"type": "number", "description": "Bank of England base rate percent, from the user."},
                "tone": {"type": "string", "enum": TONES}, "client": {"type": "string"}, "contact_name": {"type": "string"},
                "invoice_ref": {"type": "string"}, "my_name": {"type": "string"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


def run_tool(name: str, args: dict, settings: Settings, http=None):
    handlers = {"set_numbers": set_numbers, "day_rate": day_rate, "project_price": project_price, "price_options": price_options,
                "deposit_schedule": deposit_schedule, "real_rate": real_rate, "rate_rise": rate_rise,
                "billable_percent": billable_percent, "capacity": capacity, "availability": availability,
                "late_interest": late_interest, "late_explainer": late_explainer, "late_draft": late_draft}
    return st.dispatch(handlers, args.get("action"), settings, args, "freelance money")
