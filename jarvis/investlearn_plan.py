"""Investing basics part 3: long-term planning calculators and goals (FIRE, drawdown, UK pension and ISA sums, goal planner).

Illustrations from numbers the user picks, no advice on what to buy. UK figures are general information and change:
check GOV.UK for the current limits. Goals are saved in investlearn.json; the projections are not promises.
"""

from datetime import date

import homestore as hs
import investlearn_store as st
import screen
from config import Settings

NAMES = {"invest_plan"}
ISA_ALLOWANCE = 20000
LISA_LIMIT = 4000
BASIC, HIGHER, ADDITIONAL = 20, 40, 45
KINDS = ["house_deposit", "retirement", "other"]
CAVEAT = "The 4% rule is a rule of thumb from past US data, not a promise."


def _say(text: str) -> str:
    return f"{text} {st.DISCLAIMER}"


def _rate(args: dict, default: float = 5.0) -> float:
    return st.check_rate(st.num(args, "rate", "yearly growth rate in percent", default, -50, 50))


def _infl(args: dict) -> float:
    return st.num(args, "inflation", "inflation percent", 2.5, -10, 50)


def _real(rate: float, infl: float) -> float:
    return ((1 + rate / 100) / (1 + infl / 100) - 1) * 100


def fire_number(settings: Settings, args: dict):
    spend = st.num(args, "spending", "yearly spending", None, 1)
    wr = st.num(args, "withdrawal", "withdrawal rate percent", 4, 0.5, 20)
    balance = st.num(args, "balance", "current invested amount", 0)
    need = spend * 100 / wr
    rows = [[f"{r:g}%", st.gbp(spend * 100 / r), f"{100 / r:.0f} x spending"] for r in (3, 3.5, 4, 5)]
    bars = [{"label": "FIRE number", "value": min(balance, need), "max": need, "text": f"{st.gbp(balance)} of {st.gbp(need)}"}]
    text = _say(f"Spending {st.gbp(spend)} a year and withdrawing {wr:g}%, the FIRE number is about {st.gbp(need)}, {100 / wr:.0f} times your spending. {CAVEAT}")
    if balance:
        text += f" You have {round(100 * balance / need)} percent of it."
    return screen.Shown(text, screen.card("table", "FIRE number", "investlearn-fire", columns=["Withdrawal rate", "Pot needed", "Multiple"], rows=rows,
                                          text=f"{CAVEAT} Longer retirements, fees, tax and bad early years can mean a lower rate is safer.",
                                          buttons=[{"label": "4% rule explained", "say": "Explain the 4% rule."},
                                                   {"label": "Years to FI", "say": "How many years until financial independence?"}]))


def years_to_fi(settings: Settings, args: dict):
    spend = st.num(args, "spending", "yearly spending", None, 1)
    wr = st.num(args, "withdrawal", "withdrawal rate percent", 4, 0.5, 20)
    balance, monthly = st.num(args, "balance", "current invested amount", 0), st.num(args, "monthly", "monthly amount", 0)
    if not balance and not monthly:
        raise ValueError("Give me what you have invested, a monthly amount, or both.")
    rate, infl = _rate(args), _infl(args)
    real = _real(rate, infl)
    need = spend * 100 / wr
    months = st.months_to(need, balance, monthly, real)
    if months is None:
        return _say(f"At those numbers the FIRE number of {st.gbp(need)} isn't reached within 100 years (results are in today's money).")
    years = max(1, min(st.MAX_YEARS, -(-months // 12)))
    path = st.project(balance, monthly, years, real)
    when = " and ".join(hs.plural(n, w) for n, w in ((months // 12, "year"), (months % 12, "month")) if n) or "under a month"
    series = [{"name": "Invested, in today's money", "values": path["balances"]}, {"name": "FIRE number", "values": [need] * (years + 1), "style": "dashed"}]
    text = _say(f"An illustration at {rate:g}% growth and {infl:g}% inflation: about {when} to reach {st.gbp(need)}, in today's money. {CAVEAT}")
    return screen.Shown(text, st.growth_card("Years to financial independence", "investlearn-years-to-fi", st.year_labels(years), series,
                                             [f"About {when} to a {st.gbp(need)} pot.", CAVEAT]))


def drawdown(settings: Settings, args: dict):
    balance, spend = st.num(args, "balance", "pot size", None, 1), st.num(args, "withdrawal", "yearly withdrawal", None, 1)
    rate, infl = _rate(args, 4), _infl(args)
    spread = st.num(args, "spread", "range either side", 2, 0, 20)
    horizon = 60
    runs = {}
    for label, r in (("Low", rate - spread), ("Middle", rate), ("High", rate + spread)):
        bal, take, values, lasted = balance, spend, [balance], None
        for year in range(1, horizon + 1):
            bal = (bal - take) * (1 + r / 100)
            take *= 1 + infl / 100
            if bal <= 0 and lasted is None:
                lasted = year
            values.append(max(bal, 0))
        runs[label] = (r, values, lasted)
    series = [{"name": f"{label} ({r:g}%)", "values": v} for label, (r, v, _l) in runs.items()]
    def phrase(item):
        return f"{item[2]} years" if item[2] else f"beyond {horizon} years"
    lines = [f"{label} case: lasts {phrase(item)}." for label, item in runs.items()]
    text = _say(f"An illustration: taking {st.gbp(spend)} a year, rising with {infl:g}% inflation, from {st.gbp(balance)}, the middle case lasts {phrase(runs['Middle'])} "
                f"and the low case {phrase(runs['Low'])}. Real markets are bumpy, so treat this as a rough guide.")
    return screen.Shown(text, st.growth_card("Drawdown longevity", "investlearn-drawdown", st.year_labels(horizon), series, lines))


def pension_match(settings: Settings, args: dict):
    salary = st.num(args, "salary", "yearly salary", None, 1)
    mine, theirs = st.num(args, "employee_pct", "your contribution percent", None, 0, 100), st.num(args, "employer_pct", "employer contribution percent", None, 0, 100)
    more, more_theirs = st.num(args, "more_employee_pct", "higher contribution percent", mine, 0, 100), st.num(args, "more_employer_pct", "employer percent at the higher level", theirs, 0, 100)
    rows = [["Now", f"{mine:g}%", st.gbp(salary * mine / 100), f"{theirs:g}%", st.gbp(salary * theirs / 100)],
            ["Higher", f"{more:g}%", st.gbp(salary * more / 100), f"{more_theirs:g}%", st.gbp(salary * more_theirs / 100)]]
    extra_theirs = salary * (more_theirs - theirs) / 100
    extra_mine = salary * (more - mine) / 100
    text = _say(f"Paying {more - mine:g}% more yourself ({st.gbp(extra_mine)} a year before tax relief) would bring {st.gbp(extra_theirs)} a year more from your employer, "
                f"if your scheme works that way. Check your own scheme's terms and GOV.UK.")
    return screen.Shown(text, screen.card("table", "Workplace pension match", "investlearn-match", columns=["Level", "You %", "You a year", "Employer %", "Employer a year"], rows=rows,
                                          text=f"Tax relief lowers what it costs you. {st.CHECK} How relief is given depends on your scheme."))


def pension_relief(settings: Settings, args: dict):
    net = st.num(args, "amount", "amount you pay in", None, 0.01)
    band = hs.clean(args.get("band") or "basic").lower()
    rates = {"basic": BASIC, "higher": HIGHER, "additional": ADDITIONAL}
    if band not in rates:
        raise ValueError("The tax band is basic, higher or additional.")
    gross = net / (1 - BASIC / 100)
    claim = gross * (rates[band] - BASIC) / 100
    rows = [["You pay in", st.gbp2(net)], ["Basic-rate relief added (20%)", st.gbp2(gross - net)], ["Total in the pension", st.gbp2(gross)],
            [f"Extra you may claim back ({band})", st.gbp2(claim)], ["Cost to you after claiming", st.gbp2(net - claim)]]
    text = _say(f"Illustration of relief at source: paying in {st.gbp2(net)} makes {st.gbp2(gross)} in the pot, and a {band}-rate taxpayer may claim about {st.gbp2(claim)} back. {st.CHECK}")
    return screen.Shown(text, screen.card("table", "Pension tax relief", "investlearn-relief", columns=["Item", "Amount"], rows=rows,
                                          text=f"General information only; rates and rules change. {st.CHECK}"))


def lisa(settings: Settings, args: dict):
    paid = st.num(args, "amount", "amount paid in", None, 0.01)
    bonus = min(paid, LISA_LIMIT) * 0.25
    pot = paid + bonus
    charge = pot * 0.25
    rows = [["You pay in", st.gbp2(paid)], ["Government bonus (25%)", st.gbp2(bonus)], ["Pot before any growth", st.gbp2(pot)],
            ["Charge if withdrawn for a non-qualifying reason (25%)", st.gbp2(charge)], ["Left after the charge", st.gbp2(pot - charge)]]
    text = _say(f"Lifetime ISA illustration: {st.gbp2(paid)} in earns about {st.gbp2(bonus)} bonus (up to the yearly limit). Withdrawing early for a non-qualifying reason costs 25% of the pot, "
                f"which leaves you about {st.gbp2(pot - charge)}, less than you paid in. {st.CHECK}")
    return screen.Shown(text, screen.card("table", "Lifetime ISA bonus and penalty", "investlearn-lisa", columns=["Item", "Amount"], rows=rows,
                                          text=f"Ignores growth. Rules for a first home or age 60 apply. {st.CHECK}"))


def _tax_year_end(today: date) -> date:
    end = date(today.year, 4, 5)
    return end if today <= end else date(today.year + 1, 4, 5)


def isa_allowance(settings: Settings, args: dict):
    allowance = st.num(args, "allowance", "ISA allowance", ISA_ALLOWANCE, 1)
    used = st.num(args, "used", "amount already paid into ISAs this tax year", 0)
    left = max(0.0, allowance - used)
    end = _tax_year_end(hs.today())
    months = max(1, (end.year - hs.today().year) * 12 + end.month - hs.today().month)
    text = (f"ISA allowance check: you have about {st.gbp(left)} left of {st.gbp(allowance)} before 5 April {end.year}, "
            f"which is roughly {st.gbp(left / months)} a month. The allowance is shared across all your ISAs. {st.CHECK}")
    return screen.Shown(text, st.bars_card("ISA allowance", "investlearn-isa", [{"label": "Used this tax year", "value": min(used, allowance), "max": allowance,
                                                                             "text": f"{st.gbp(used)} of {st.gbp(allowance)}"}],
                                           f"The default {st.gbp(ISA_ALLOWANCE)} may be out of date. {st.CHECK}"))


def emergency_fund(settings: Settings, args: dict):
    essentials = st.num(args, "essentials", "monthly essential spending", None, 1)
    savings = st.num(args, "savings", "easy-access savings", 0)
    goal = st.num(args, "months", "months of cover", 3, 1, 24)
    months = savings / essentials
    bars = [{"label": "Cover now", "value": min(months, 6), "max": 6, "text": f"{months:.1f} months", "warn": months < goal},
            {"label": f"{goal:g} months target", "value": min(goal, 6), "max": 6, "text": st.gbp(essentials * goal)}]
    verdict = "You are past your target." if months >= goal else f"You'd need about {st.gbp(essentials * goal - savings)} more to reach {goal:g} months."
    text = f"Emergency fund check: your savings cover about {months:.1f} months of essentials. {verdict} Many people aim for three to six months before investing; it depends on your situation. {st.DISCLAIMER}"
    return screen.Shown(text, st.bars_card("Emergency fund first", "investlearn-emergency", bars, f"Not advice. {st.DISCLAIMER}",
                                           [{"label": "Why first?", "say": "Explain why an emergency fund comes first."}]))


# Goals -------------------------------------------------------------------

def _goal(data: dict, name) -> dict:
    if not data["goals"]:
        raise ValueError("You haven't set a goal yet, for example: goal house deposit, 20,000 pounds, saving 300 a month.")
    if not hs.clean(name):
        return data["goals"][0]
    names = {g["name"]: g for g in data["goals"]}
    found = hs.find(names, name)
    if found is None:
        raise ValueError(f"I can't find a goal called {hs.clean(name)}.")
    return names[found]


def goal_add(settings: Settings, args: dict):
    data = st.load(settings)
    name = hs.need(args.get("name"), "goal name", 60)
    kind = hs.clean(args.get("kind") or "other").lower().replace(" ", "_")
    if kind not in KINDS:
        raise ValueError("The kind is house_deposit, retirement or other.")
    goal = next((g for g in data["goals"] if g["name"].lower() == name.lower()), None)
    if goal is None:
        goal = {"id": st.new_id(data), "name": name}
        st.put(data["goals"], goal)
    goal.update({"kind": kind, "target": st.num(args, "target", "target amount", None, 1), "saved": st.num(args, "saved", "amount saved so far", goal.get("saved", 0)),
                 "monthly": st.num(args, "monthly", "monthly amount", goal.get("monthly", 0)), "rate": _rate(args, goal.get("rate", 4.0)),
                 "date": hs.parse_day(args["date"]).isoformat() if args.get("date") else goal.get("date", "")})
    st.save(settings, data)
    return goal_show(settings, {"name": name}, "Goal saved. ")


def _path(goal: dict, rate: float, years: int) -> list:
    return st.project(goal["saved"], goal["monthly"], years, rate)["balances"]


def _horizon(goal: dict) -> int:
    if goal.get("date"):
        days = (date.fromisoformat(goal["date"]) - hs.today()).days
        return max(1, min(st.MAX_YEARS, -(-days // 365)))
    months = st.months_to(goal["target"], goal["saved"], goal["monthly"], goal["rate"])
    return max(2, min(st.MAX_YEARS, (months or 240) // 12 + 2))


def goal_show(settings: Settings, args: dict, lead: str = ""):
    data = st.load(settings)
    if not hs.clean(args.get("name")) and len(data["goals"]) != 1:
        _goal(data, "")
        bars = [{"label": f"{g['name']} ({g['kind'].replace('_', ' ')})", "value": min(g["saved"], g["target"]), "max": g["target"],
                 "text": f"{st.gbp(g['saved'])} of {st.gbp(g['target'])}", "say": f"Show my {g['name']} goal."} for g in data["goals"]]
        return screen.Shown(f"{lead}You have {len(bars)} goals. Projections are illustrations, not promises.", st.bars_card("Goal planner", "investlearn-goals", bars, st.DISCLAIMER))
    goal = _goal(data, args.get("name"))
    years = _horizon(goal)
    spread = 2
    series = [{"name": f"Low ({goal['rate'] - spread:g}%)", "values": _path(goal, goal["rate"] - spread, years)},
              {"name": f"Middle ({goal['rate']:g}%)", "values": _path(goal, goal["rate"], years)},
              {"name": f"High ({goal['rate'] + spread:g}%)", "values": _path(goal, goal["rate"] + spread, years)},
              {"name": "Target", "values": [goal["target"]] * (years + 1), "style": "dashed"}]
    end = series[1]["values"][-1]
    lines = [f"Saved so far {st.gbp(goal['saved'])}, adding {st.gbp(goal['monthly'])} a month, target {st.gbp(goal['target'])}.",
             f"After {years} years the middle case is about {st.gbp(end)}, low {st.gbp(series[0]['values'][-1])}, high {st.gbp(series[2]['values'][-1])}."]
    text = _say(f"{lead}{goal['name']}: {st.gbp(goal['saved'])} of {st.gbp(goal['target'])}. In the middle case you'd have about {st.gbp(end)} after {years} years.")
    return screen.Shown(text, st.growth_card(goal["name"], f"investlearn-goal-{goal['id']}", st.year_labels(years), series, lines,
                                             buttons=[{"label": "Milestones", "say": f"Show milestones for my {goal['name']} goal."},
                                                      {"label": "All goals", "say": "Show all my investing goals."}]))


def goal_update(settings: Settings, args: dict):
    data = st.load(settings)
    goal = _goal(data, args.get("name"))
    if args.get("saved") is not None:
        goal["saved"] = st.num(args, "saved", "amount saved so far")
    if args.get("add") is not None:
        goal["saved"] += st.num(args, "add", "amount to add")
    if args.get("monthly") is not None:
        goal["monthly"] = st.num(args, "monthly", "monthly amount")
    if args.get("target") is not None:
        goal["target"] = st.num(args, "target", "target amount", None, 1)
    st.save(settings, data)
    return goal_show(settings, {"name": goal["name"]}, "Updated. ")


def goal_remove(settings: Settings, args: dict):
    data = st.load(settings)
    goal = _goal(data, args.get("name"))
    if args.get("confirmed") is not True:
        return st.confirm_needed(f"removing the goal {goal['name']}")
    data["goals"].remove(goal)
    st.save(settings, data)
    return f"Removed the goal {goal['name']}."


def milestones(settings: Settings, args: dict):
    data = st.load(settings)
    goal = _goal(data, args.get("name"))
    rows = []
    for pct in (25, 50, 75, 100):
        amount = goal["target"] * pct / 100
        if goal["saved"] >= amount:
            rows.append([f"{pct}%", st.gbp(amount), "reached"])
            continue
        months = st.months_to(amount, goal["saved"], goal["monthly"], goal["rate"])
        rows.append([f"{pct}%", st.gbp(amount), st.add_months(hs.today(), months).strftime("%b %Y") if months is not None else "not within 100 years"])
    text = _say(f"Milestones for {goal['name']} at {goal['rate']:g}% growth: 25, 50, 75 and 100 percent of {st.gbp(goal['target'])}. These dates are estimates, not promises.")
    return screen.Shown(text, screen.card("table", f"Milestones: {goal['name']}", f"investlearn-milestones-{goal['id']}", columns=["Milestone", "Amount", "Estimated"], rows=rows,
                                          text=st.DISCLAIMER))


def house_deposit(settings: Settings, args: dict):
    price = st.num(args, "price", "house price", None, 1)
    saved, monthly = st.num(args, "saved", "amount saved so far", 0), st.num(args, "monthly", "monthly amount", 0)
    rate = _rate(args, 3.0)
    rows = []
    for pct in (5, 10, 15, 20):
        need = price * pct / 100
        months = st.months_to(need, saved, monthly, rate)
        when = "already there" if saved >= need else st.add_months(hs.today(), months).strftime("%b %Y") if months is not None else "not within 100 years"
        rows.append([f"{pct}%", st.gbp(need), when])
    text = _say(f"House deposit illustration for {st.gbp(price)}: a 10 percent deposit is {st.gbp(price * 0.1)}. Saving {st.gbp(monthly)} a month at {rate:g}% gets there by {rows[1][2]}. "
                f"Also budget for stamp duty and fees; check GOV.UK.")
    return screen.Shown(text, screen.card("table", "House deposit planner", "investlearn-house", columns=["Deposit", "Amount", "Estimated"], rows=rows,
                                          text=f"A Lifetime ISA bonus may help a first home: {st.CHECK}",
                                          buttons=[{"label": "Save as goal", "say": f"Add a house deposit goal of {round(price * 0.1)} pounds, saving {round(monthly)} a month."},
                                                   {"label": "LISA explained", "say": "Explain the Lifetime ISA bonus and penalty."}]))


def retirement_plan(settings: Settings, args: dict):
    age, retire = int(st.num(args, "age", "current age", None, 16, 100)), int(st.num(args, "retire_age", "retirement age", 67, 30, 100))
    if retire <= age:
        raise ValueError("The retirement age must be later than your age now.")
    spend = st.num(args, "spending", "yearly spending in retirement, in today's money", None, 1)
    balance, monthly = st.num(args, "balance", "current pension and savings", 0), st.num(args, "monthly", "monthly amount", 0)
    rate, infl = _rate(args, 5), _infl(args)
    wr, spread = st.num(args, "withdrawal", "withdrawal rate percent", 4, 0.5, 20), 2
    years = retire - age
    need = spend * 100 / wr
    series, ends = [], {}
    for label, r in (("Low", rate - spread), ("Middle", rate), ("High", rate + spread)):
        real = st.project(balance, monthly, years, _real(r, infl))["balances"]
        series.append({"name": f"{label} ({r:g}%)", "values": real})
        ends[label] = real[-1]
    series.append({"name": "Pot needed (4% rule style)", "values": [need] * (years + 1), "style": "dashed"})
    gap = need - ends["Middle"]
    verdict = f"about {st.gbp(gap)} short" if gap > 0 else f"about {st.gbp(-gap)} above"
    text = _say(f"Retirement illustration in today's money: at {retire}, the middle case gives about {st.gbp(ends['Middle'])} against {st.gbp(need)} for {st.gbp(spend)} a year, {verdict}. "
                f"The state pension isn't counted; check your forecast on GOV.UK.")
    return screen.Shown(text, st.growth_card("Retirement planner", "investlearn-retirement", [f"Age {age + i}" for i in range(years + 1)], series,
                                             [f"Low {st.gbp(ends['Low'])}, middle {st.gbp(ends['Middle'])}, high {st.gbp(ends['High'])} at age {retire}, in today's money.",
                                              f"{CAVEAT} State pension not included."],
                                             buttons=[{"label": "Save as goal", "say": f"Add a retirement goal of {round(need)} pounds, saving {round(monthly)} a month."}]))


ACTIONS = {"fire_number": fire_number, "years_to_fi": years_to_fi, "drawdown": drawdown, "pension_match": pension_match,
           "pension_relief": pension_relief, "lisa": lisa, "isa_allowance": isa_allowance, "emergency_fund": emergency_fund,
           "goal_add": goal_add, "goal_show": goal_show, "goal_update": goal_update, "goal_remove": goal_remove,
           "milestones": milestones, "house_deposit": house_deposit, "retirement_plan": retirement_plan}


def tool_definitions() -> list[dict]:
    number = {"type": "number"}
    return [{
        "name": "invest_plan",
        "description": "Long-term money planning calculators and goals for learning, never advice on what to buy; illustrations only, "
                       "returns not guaranteed, UK rules change so say check GOV.UK. action: fire_number (spending, withdrawal 4, balance) / "
                       "years_to_fi (spending, balance, monthly, rate, inflation) / drawdown (balance, withdrawal yearly, rate, inflation) = how "
                       "long a pot lasts / pension_match (salary, employee_pct, employer_pct, more_employee_pct, more_employer_pct) / "
                       "pension_relief (amount paid, band basic|higher|additional) / lisa (amount) = bonus and penalty / isa_allowance (used) / "
                       "emergency_fund (essentials monthly, savings, months) / goal_add (name, kind house_deposit|retirement|other, target, "
                       "saved, monthly, rate, date) / goal_show (name) / goal_update (name, saved, add, monthly, target) / goal_remove "
                       "(name, confirmed only after yes) / milestones (name) / house_deposit (price, saved, monthly, rate) / "
                       "retirement_plan (age, retire_age, spending, balance, monthly, rate, inflation).",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": list(ACTIONS)},
                "spending": number, "withdrawal": number, "balance": number, "monthly": number, "rate": number,
                "inflation": number, "spread": number, "salary": number, "employee_pct": number, "employer_pct": number,
                "more_employee_pct": number, "more_employer_pct": number, "amount": number, "band": {"type": "string", "enum": ["basic", "higher", "additional"]},
                "used": number, "allowance": number, "essentials": number, "savings": number, "months": number,
                "name": {"type": "string"}, "kind": {"type": "string", "enum": KINDS}, "target": number, "saved": number,
                "add": number, "date": {"type": "string"}, "price": number, "age": number, "retire_age": number,
                "confirmed": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


def run_tool(name: str, args: dict, settings: Settings, http=None):
    found = ACTIONS.get(args.get("action"))
    if found is None:
        raise ValueError("I can't do that one.")
    return found(settings, args)
