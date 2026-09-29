"""Investing basics part 1: growth calculators (compound growth, cost of waiting, fees drag, inflation, rule of 72, ...).

Illustrations from numbers the user picks. Nothing is fetched, no live prices, and no advice on what to buy. Every
result says that returns are not guaranteed and capital is at risk.
"""

import math

import homestore as hs
import investlearn_store as st
import screen
from config import Settings

NAMES = {"invest_calc"}
DEFAULT_RATE = 5.0
DEFAULT_INFLATION = 2.5
SAY = "How does compound growth work?"


def _say(text: str) -> str:
    return f"{text} {st.DISCLAIMER}"


def _rate(args: dict) -> float:
    return st.check_rate(st.num(args, "rate", "yearly growth rate in percent", DEFAULT_RATE, -50, 50))


def _years(args: dict, default: int = 20) -> int:
    return st.check_years(st.num(args, "years", "number of years", default, 1, st.MAX_YEARS))


def _more(*pairs) -> list[dict]:
    return [{"label": a, "say": b} for a, b in pairs]


def compound(settings: Settings, args: dict):
    lump, monthly = st.num(args, "lump", "lump sum", 0), st.num(args, "monthly", "monthly amount", 0)
    if not lump and not monthly:
        raise ValueError("Give me a lump sum, a monthly amount, or both.")
    years, rate = _years(args), _rate(args)
    inflation = st.num(args, "inflation", "inflation", DEFAULT_INFLATION, -10, 50)
    spread = st.num(args, "spread", "range either side", 2, 0, 20)
    step = st.num(args, "step", "yearly increase in saving", 0, 0, 100)
    low, mid, high = (st.project(lump, monthly, years, r, step) for r in st.spread_rates(rate, spread))
    real = st.deflate(mid["balances"], inflation)
    series = [{"name": f"Low ({rate - spread:g}%)", "values": low["balances"]},
              {"name": f"Middle ({rate:g}%)", "values": mid["balances"]},
              {"name": f"High ({rate + spread:g}%)", "values": high["balances"]},
              {"name": f"Middle in today's money ({inflation:g}% inflation)", "values": real, "style": "dashed"},
              {"name": "Paid in", "values": mid["paid"], "style": "dotted"}]
    lines = [f"After {years} years: low {st.gbp(low['balances'][-1])}, middle {st.gbp(mid['balances'][-1])}, high {st.gbp(high['balances'][-1])}.",
             f"You would have paid in {st.gbp(mid['paid'][-1])}; the middle case is worth about {st.gbp(real[-1])} in today's money."]
    text = _say(f"An illustration at {rate:g}% a year for {years} years: about {st.gbp(mid['balances'][-1])} in the middle case, "
                f"between {st.gbp(low['balances'][-1])} and {st.gbp(high['balances'][-1])}.")
    return screen.Shown(text, st.growth_card("Compound growth", "investlearn-compound", st.year_labels(years), series, lines,
                                             buttons=_more(("Cost of waiting", "Show the cost of waiting to start investing."),
                                                           ("Fees drag", "Show how fees drag on growth over 30 years."))))


def cost_of_waiting(settings: Settings, args: dict):
    monthly, years, rate = st.num(args, "monthly", "monthly amount"), _years(args, 30), _rate(args)
    delays = [d for d in (0, 1, 5, 10) if d < years]
    finals = [st.project(0, monthly, years - d, rate)["balances"][-1] for d in delays]
    top = finals[0]
    rows = [{"label": "Start now" if d == 0 else f"Wait {d} year{'s' if d != 1 else ''}", "value": v, "max": top,
             "text": f"{st.gbp(v)}" + ("" if d == 0 else f" ({st.gbp(top - v)} less)"), "warn": d > 0}
            for d, v in zip(delays, finals)]
    worst = delays[-1]
    text = _say(f"An illustration at {rate:g}% for {years} years: paying {st.gbp(monthly)} a month, waiting {worst} years "
                f"could leave you about {st.gbp(top - finals[-1])} lower.")
    return screen.Shown(text, st.bars_card("Cost of waiting", "investlearn-waiting", rows,
                                           f"{st.gbp(monthly)} a month, same end date, {rate:g}% a year. {st.DISCLAIMER}"))


def target_saving(settings: Settings, args: dict):
    target, years = st.num(args, "target", "target amount", None, 1), _years(args, 10)
    lump, rate = st.num(args, "lump", "starting amount", 0), _rate(args)
    spread = st.num(args, "spread", "range either side", 2, 0, 20)
    rows = []
    for label, r in (("At 0%", 0.0), (f"Low {rate - spread:g}%", rate - spread), (f"Middle {rate:g}%", rate),
                     (f"High {rate + spread:g}%", rate + spread)):
        grown = st.project(lump, 0, years, r)["balances"][-1]
        per_pound = st.project(0, 1, years, r)["balances"][-1]
        rows.append((label, max(0.0, (target - grown) / per_pound)))
    top = max(v for _, v in rows) or 1
    bars = [{"label": label, "value": v, "max": top, "text": f"{st.gbp2(v)} a month"} for label, v in rows]
    text = _say(f"An illustration: to reach {st.gbp(target)} in {years} years you might save about {st.gbp2(rows[2][1])} a month at {rate:g}%, "
                f"or {st.gbp2(rows[0][1])} with no growth at all.")
    return screen.Shown(text, st.bars_card("Saving to a target", "investlearn-target", bars,
                                           f"Target {st.gbp(target)} in {years} years. {st.DISCLAIMER}"))


def years_to_target(settings: Settings, args: dict):
    target = st.num(args, "target", "target amount", None, 1)
    lump, monthly, rate = st.num(args, "lump", "starting amount", 0), st.num(args, "monthly", "monthly amount", 0), _rate(args)
    if not lump and not monthly:
        raise ValueError("Give me a starting amount, a monthly amount, or both.")
    balance, grow, months = lump, (1 + rate / 100) ** (1 / 12), 0
    while balance < target and months < 1200:
        balance = balance * grow + monthly
        months += 1
    if balance < target:
        return _say("At those numbers the target isn't reached within 100 years.")
    years, rest = divmod(months, 12)
    path = st.project(lump, monthly, min(st.MAX_YEARS, years + 1), rate)
    labels = st.year_labels(len(path["balances"]) - 1)
    series = [{"name": f"At {rate:g}%", "values": path["balances"]}, {"name": "Paid in", "values": path["paid"], "style": "dotted"}]
    when = " and ".join(hs.plural(n, w) for n, w in ((years, "year"), (rest, "month")) if n) or "under a month"
    text = _say(f"An illustration: about {when} to reach {st.gbp(target)} at {rate:g}% a year.")
    return screen.Shown(text, st.growth_card("Years to a target", "investlearn-years-to-target", labels, series,
                                             [f"About {when} to reach {st.gbp(target)}."]))


def fees_drag(settings: Settings, args: dict):
    lump, monthly = st.num(args, "lump", "lump sum", 0), st.num(args, "monthly", "monthly amount", 0)
    if not lump and not monthly:
        raise ValueError("Give me a lump sum, a monthly amount, or both.")
    years, rate = _years(args, 30), st.check_rate(st.num(args, "rate", "growth rate before fees", 6, -50, 50))
    fee_a, fee_b = st.num(args, "fee_low", "lower fee percent", 0.2, 0, 10), st.num(args, "fee_high", "higher fee percent", 1.0, 0, 10)
    a, b = (st.project(lump, monthly, years, rate, 0, f) for f in (fee_a, fee_b))
    gap = a["balances"][-1] - b["balances"][-1]
    series = [{"name": f"{fee_a:g}% a year in fees", "values": a["balances"]},
              {"name": f"{fee_b:g}% a year in fees", "values": b["balances"]},
              {"name": "Paid in", "values": a["paid"], "style": "dotted"}]
    lines = [f"With {fee_a:g}% fees: {st.gbp(a['balances'][-1])}. With {fee_b:g}%: {st.gbp(b['balances'][-1])}.",
             f"The difference after {years} years is {st.gbp(gap)}, before any tax."]
    text = _say(f"An illustration: at {rate:g}% before fees over {years} years, {fee_b:g}% charges instead of {fee_a:g}% "
                f"would leave you about {st.gbp(gap)} lower.")
    return screen.Shown(text, st.growth_card("Fees drag", "investlearn-fees", st.year_labels(years), series, lines))


def inflation(settings: Settings, args: dict):
    amount, years = st.num(args, "amount", "amount", None, 0.01), _years(args, 20)
    rate = st.num(args, "inflation", "inflation percent", DEFAULT_INFLATION, -10, 50)
    power = [amount / (1 + rate / 100) ** i for i in range(years + 1)]
    then = amount * (1 + rate / 100) ** years
    lines = [f"{st.gbp(amount)} today would buy what {st.gbp(power[-1])} buys in today's prices after {years} years.",
             f"Something costing {st.gbp(amount)} now might cost about {st.gbp(then)} then."]
    text = _say(f"An illustration at {rate:g}% inflation: after {years} years {st.gbp(amount)} buys about {st.gbp(power[-1])} worth of today's goods.")
    return screen.Shown(text, st.growth_card("Inflation effect", "investlearn-inflation", st.year_labels(years),
                                             [{"name": f"Buying power of {st.gbp(amount)}", "values": power}], lines))


def real_return(settings: Settings, args: dict):
    rate = st.check_rate(st.num(args, "rate", "growth rate", None, -50, 50))
    infl = st.num(args, "inflation", "inflation percent", DEFAULT_INFLATION, -10, 50)
    real = ((1 + rate / 100) / (1 + infl / 100) - 1) * 100
    return screen.Shown(_say(f"An illustration: {rate:g}% growth with {infl:g}% inflation is a real return of about {real:.2f}%."),
                        st.bars_card("Real return", "investlearn-real",
                                     [{"label": "Growth before inflation", "value": max(rate, 0), "max": max(rate, infl, 1), "text": f"{rate:g}%"},
                                      {"label": "Inflation", "value": max(infl, 0), "max": max(rate, infl, 1), "text": f"{infl:g}%", "warn": True},
                                      {"label": "Real return", "value": max(real, 0), "max": max(rate, infl, 1), "text": f"{real:.2f}%"}]))


def rule72(settings: Settings, args: dict):
    if args.get("rate") is not None:
        rate = st.check_rate(args["rate"])
        if rate <= 0:
            raise ValueError("The rule of 72 needs a growth rate above zero.")
        rough, exact = 72 / rate, math.log(2) / math.log(1 + rate / 100)
        text = _say(f"Rule of 72 illustration: at {rate:g}% a year money doubles in roughly {rough:.1f} years ({exact:.1f} by exact maths).")
    elif args.get("years") is not None:
        years = st.check_years(args["years"])
        text = _say(f"Rule of 72 illustration: to double in {years} years you'd need about {72 / years:.1f}% a year.")
    else:
        raise ValueError("Give me a growth rate, or a number of years to double in.")
    rows = [[f"{r}%", f"{72 / r:.1f}", f"{math.log(2) / math.log(1 + r / 100):.1f}"] for r in (1, 2, 3, 4, 5, 6, 8, 10)]
    return screen.Shown(text, st.table("Rule of 72", "investlearn-rule72", ["Rate", "Rule of 72 years", "Exact years"], rows))


def cagr(settings: Settings, args: dict):
    start, end = st.num(args, "start", "starting amount", None, 0.01), st.num(args, "end", "ending amount", None, 0)
    years = _years(args, 10)
    rate = ((end / start) ** (1 / years) - 1) * 100
    return screen.Shown(_say(f"An illustration: going from {st.gbp(start)} to {st.gbp(end)} over {years} years is about {rate:.2f}% a year on average."
                             " Real years are never that smooth."),
                        st.growth_card("Average yearly growth", "investlearn-cagr", st.year_labels(years),
                                       [{"name": "Steady path", "values": [start * (1 + rate / 100) ** i for i in range(years + 1)]}],
                                       [f"{rate:.2f}% a year on average (compound annual growth rate)."]))


def loss_recovery(settings: Settings, args: dict):
    fall = st.num(args, "fall", "fall in percent", None, 0.1, 99.9)
    need = fall / (100 - fall) * 100
    rows = [[f"{f}%", f"{f / (100 - f) * 100:.1f}%"] for f in (10, 20, 30, 40, 50, 60)]
    text = _say(f"An illustration: after a {fall:g}% fall you need a gain of about {need:.1f}% just to get back to where you were.")
    return screen.Shown(text, st.table("Recovering from a fall", "investlearn-recovery", ["Fall", "Gain to recover"], rows))


def extra_saving(settings: Settings, args: dict):
    lump, monthly = st.num(args, "lump", "lump sum", 0), st.num(args, "monthly", "monthly amount", 0)
    extra, years, rate = st.num(args, "extra", "extra monthly amount", None, 0.01), _years(args, 20), _rate(args)
    base, more = st.project(lump, monthly, years, rate), st.project(lump, monthly + extra, years, rate)
    gain = more["balances"][-1] - base["balances"][-1]
    series = [{"name": f"Saving {st.gbp(monthly)} a month", "values": base["balances"]},
              {"name": f"Saving {st.gbp(monthly + extra)} a month", "values": more["balances"]}]
    text = _say(f"An illustration at {rate:g}% over {years} years: an extra {st.gbp(extra)} a month could add about {st.gbp(gain)}, "
                f"of which {st.gbp(extra * 12 * years)} is your own money.")
    return screen.Shown(text, st.growth_card("Effect of saving a bit more", "investlearn-extra", st.year_labels(years), series,
                                             [f"Extra paid in: {st.gbp(extra * 12 * years)}.", f"Extra pot: {st.gbp(gain)}."]))


def compare_rates(settings: Settings, args: dict):
    lump, monthly = st.num(args, "lump", "lump sum", 0), st.num(args, "monthly", "monthly amount", 0)
    if not lump and not monthly:
        raise ValueError("Give me a lump sum, a monthly amount, or both.")
    years = _years(args, 20)
    rates = [st.check_rate(r) for r in (args.get("rates") or [2, 4, 6, 8])[:6]]
    rows = [[f"{r:g}%", st.gbp(st.project(lump, monthly, years, r)["balances"][-1])] for r in rates]
    top = max(st.project(lump, monthly, years, r)["balances"][-1] for r in rates)
    bars = [{"label": f"{r:g}% a year", "value": max(0, st.project(lump, monthly, years, r)["balances"][-1]), "max": top or 1,
             "text": row[1]} for r, row in zip(rates, rows)]
    return screen.Shown(_say(f"An illustration over {years} years: small differences in yearly growth make a big difference, and nobody can promise any rate."),
                        st.bars_card("Compare growth rates", "investlearn-compare", bars))


def pound_cost_averaging(settings: Settings, args: dict):
    prices = [hs.number(p, "price", 0.0001, 1_000_000) for p in (args.get("prices") or [])][:36]
    if len(prices) < 2:
        raise ValueError("Give me at least two made-up prices, for example 10, 8, 6, 9, 12.")
    each = st.num(args, "amount", "amount per period", 100, 0.01)
    units = [each / p for p in prices]
    total, spent = sum(units), each * len(prices)
    lump_units = spent / prices[0]
    average = spent / total
    rows = [[f"Period {i + 1}", st.gbp2(p), f"{u:.3f}"] for i, (p, u) in enumerate(zip(prices, units))]
    rows.append(["Regular total", f"average cost {st.gbp2(average)}", f"{total:.3f}"])
    rows.append(["Lump sum at the first price", st.gbp2(prices[0]), f"{lump_units:.3f}"])
    text = (f"Practice figures you made up: regular investing bought {total:.2f} units at an average {st.gbp2(average)}; "
            f"putting it all in at the start bought {lump_units:.2f}. {st.DISCLAIMER}")
    return screen.Shown(text, st.table("Pound-cost averaging", "investlearn-pca", ["Step", "Price", "Units"], rows,
                                       buttons=_more(("Explain it", "Explain pound-cost averaging."))))


ACTIONS = {"compound": compound, "cost_of_waiting": cost_of_waiting, "target_saving": target_saving,
           "years_to_target": years_to_target, "fees_drag": fees_drag, "inflation": inflation, "real_return": real_return,
           "rule72": rule72, "cagr": cagr, "loss_recovery": loss_recovery, "extra_saving": extra_saving,
           "compare_rates": compare_rates, "pound_cost_averaging": pound_cost_averaging}


def tool_definitions() -> list[dict]:
    number = {"type": "number"}
    return [{
        "name": "invest_calc",
        "description": "Investing-basics calculators for learning, never advice on what to buy. Every result is an illustration: "
                       "returns not guaranteed, capital at risk. The user picks the yearly growth rate. action: compound "
                       "(lump, monthly, years, rate, inflation, spread, step; chart with low/middle/high and inflation-adjusted line) "
                       "/ cost_of_waiting (monthly, years, rate) / target_saving (target, years, lump, rate) = monthly needed / "
                       "years_to_target (target, lump, monthly, rate) / fees_drag (lump, monthly, years, rate, fee_low 0.2, fee_high 1) "
                       "/ inflation (amount, years, inflation) / real_return (rate, inflation) / rule72 (rate or years) / cagr "
                       "(start, end, years) / loss_recovery (fall percent) / extra_saving (extra, lump, monthly, years, rate) / "
                       "compare_rates (lump, monthly, years, rates list) / pound_cost_averaging (prices = made-up list, amount).",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": list(ACTIONS)},
                "lump": number, "monthly": number, "extra": number, "years": number, "rate": number,
                "inflation": number, "spread": number, "step": number, "target": number, "amount": number,
                "start": number, "end": number, "fall": number, "fee_low": number, "fee_high": number,
                "rates": {"type": "array", "items": number}, "prices": {"type": "array", "items": number},
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
