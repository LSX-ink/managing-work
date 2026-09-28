"""Chores and upkeep: a weekly chores rota, a cleaning schedule, home maintenance, and laundry help.

The rota hands each chore to the next person every Monday. Cleaning tasks repeat every so many days, maintenance
jobs every so many months. Laundry care symbols are a small built-in table; the laundry timer is a normal
Alfred timer that also pops up a countdown. Everything lives in household-*.json in the memory folder.
"""

import time
from datetime import date, timedelta

import homestore as hs
import household_store as hh
import screen
import timers
from config import Settings

ROTA, CLEANING, UPKEEP = "household-rota.json", "household-cleaning.json", "household-maintenance.json"
FIRST_MONDAY = date(2024, 1, 1)
MAX_PEOPLE, MAX_CHORES = 12, 40

# (symbol as people describe it, what it means, extra words people use for it)
SYMBOLS = [
    ("Tub with a hand in it", "Hand wash only, in cool water", "bucket hand"),
    ("Tub with 30 or one dot", "Machine wash cool, up to 30°C", "bucket 30 one dot cool"),
    ("Tub with 40 or two dots", "Machine wash warm, up to 40°C", "bucket 40 two dots warm"),
    ("Tub with 60 or three dots", "Machine wash hot, up to 60°C", "bucket 60 three dots hot"),
    ("Tub with 95 or six dots", "Very hot wash or boil, up to 95°C", "bucket 95 boil six dots"),
    ("Tub with one line under it", "Gentle synthetics cycle, spin short", "bucket one line bar underneath synthetic"),
    ("Tub with two lines under it", "Very gentle wool or delicates cycle", "bucket two lines bars underneath wool delicate"),
    ("Tub crossed out", "Do not wash; dry clean instead", "bucket cross crossed x no wash"),
    ("Empty triangle", "Any bleach is fine", "triangle plain bleach"),
    ("Triangle with two slanted lines", "Only non-chlorine (oxygen) bleach", "triangle lines stripes diagonal"),
    ("Triangle crossed out", "Do not bleach", "triangle cross crossed x"),
    ("Square with a circle", "Tumble drying is fine", "square circle dryer tumble"),
    ("Square with a circle and one dot", "Tumble dry on low heat", "square circle one dot dryer tumble low"),
    ("Square with a circle and two dots", "Tumble dry on normal heat", "square circle two dots dryer tumble medium"),
    ("Square with a circle crossed out", "Do not tumble dry", "square circle cross crossed x dryer tumble"),
    ("Square with a curve at the top", "Hang on a line to dry", "square curve line dry envelope"),
    ("Square with three upright lines", "Drip dry, hang up wet without spinning", "square three vertical lines drip"),
    ("Square with one flat line", "Dry flat, lay it out", "square horizontal line flat"),
    ("Square with two slanted lines in the corner", "Dry in the shade", "square corner lines diagonal shade"),
    ("Iron with one dot", "Iron on low, up to 110°C (silk, nylon)", "iron one dot low"),
    ("Iron with two dots", "Iron on medium, up to 150°C (wool, polyester)", "iron two dots medium"),
    ("Iron with three dots", "Iron on high, up to 200°C (cotton, linen)", "iron three dots high"),
    ("Iron crossed out", "Do not iron", "iron cross crossed x"),
    ("Empty circle", "Dry clean only", "circle plain dry clean"),
    ("Circle with a letter P or F", "Professional dry clean with the solvent shown", "circle letter p f solvent"),
    ("Circle with a W", "Professional wet clean", "circle letter w wet"),
    ("Circle crossed out", "Do not dry clean", "circle cross crossed x dry clean"),
]
FILLER = {"a", "an", "the", "with", "and", "in", "it", "of", "on", "what", "does", "mean", "symbol", "label", "is"}


# Chores rota

def _rota(settings: Settings) -> dict:
    found = hs.load(settings, ROTA, {})
    return {"people": [p for p in found.get("people", []) if isinstance(p, str)],
            "chores": [c for c in found.get("chores", []) if isinstance(c, str)],
            "done": {k: v for k, v in found.get("done", {}).items() if isinstance(v, list)}}


def _this_week() -> date:
    return hs.week_start(hs.today())


def _turns(rota: dict, week: date) -> list[tuple[str, str]]:
    n = (week - FIRST_MONDAY).days // 7
    people = rota["people"]
    return [(c, people[(i + n) % len(people)]) for i, c in enumerate(rota["chores"])]


def rota_people(settings: Settings, names) -> str:
    people = hh.words(names, MAX_PEOPLE, 40)
    if not people:
        raise ValueError("Who's on the rota?")
    rota = _rota(settings)
    rota["people"] = people
    hs.save(settings, ROTA, rota)
    return f"The rota is {', '.join(people)}."


def rota_add(settings: Settings, chores) -> str:
    rota = _rota(settings)
    have = {c.lower() for c in rota["chores"]}
    new = [c for c in hh.words(chores, MAX_CHORES, 60) if c.lower() not in have]
    if not new:
        raise ValueError("Which chores? Those are already on the rota.")
    rota["chores"] = (rota["chores"] + new)[:MAX_CHORES]
    hs.save(settings, ROTA, rota)
    return f"Added {', '.join(new)}. {hs.plural(len(rota['chores']), 'chore')} on the rota."


def rota_remove(settings: Settings, chore, confirmed: bool) -> str:
    rota = _rota(settings)
    k = hh.key(dict.fromkeys(rota["chores"]), chore, "chore")
    if not confirmed:
        return f"Ask the user to confirm taking {k} off the rota, then call again with confirmed true."
    rota["chores"].remove(k)
    hs.save(settings, ROTA, rota)
    return f"Took {k} off the rota."


def _ready(settings: Settings) -> dict:
    rota = _rota(settings)
    if not rota["people"] or not rota["chores"]:
        raise ValueError("Tell me who's on the rota and which chores there are first.")
    return rota


def rota_week(settings: Settings) -> screen.Shown:
    rota = _ready(settings)
    week = _this_week()
    done = {c.lower() for c in rota["done"].get(week.isoformat(), [])}
    rows = [[c, p, "done" if c.lower() in done else ""] for c, p in _turns(rota, week)]
    left = sum(not r[2] for r in rows)
    card = screen.card("table", f"Chores, week of {hs.spoken(week)}", "household-rota",
                       columns=["Chore", "Whose turn", "Done"], rows=rows,
                       buttons=[{"label": "Next week", "say": "Who's doing which chore next week?"}])
    return screen.Shown(f"This week's rota is on the screen; {hs.plural(left, 'chore')} still to do.", card)


def rota_next(settings: Settings) -> screen.Shown:
    rota = _ready(settings)
    week = _this_week() + timedelta(days=7)
    card = screen.card("table", f"Chores, week of {hs.spoken(week)}", "household-rota-next",
                       columns=["Chore", "Whose turn"], rows=[list(t) for t in _turns(rota, week)])
    return screen.Shown("Next week's rota is on the screen.", card)


def rota_whose(settings: Settings, chore) -> str:
    rota = _ready(settings)
    turns = dict(_turns(rota, _this_week()))
    k = hh.key(turns, chore, "chore on the rota")
    return f"It's {turns[k]}'s turn to do {k} this week."


def rota_done(settings: Settings, chores) -> str:
    rota = _ready(settings)
    week = _this_week().isoformat()
    turns = dict(_turns(rota, _this_week()))
    names = [hh.key(turns, c, "chore on the rota") for c in hh.words(chores)]
    if not names:
        raise ValueError("Which chore is done?")
    done = rota["done"].get(week, [])
    done += [n for n in names if n not in done]
    keep = (_this_week() - timedelta(days=56)).isoformat()
    rota["done"] = {w: d for w, d in rota["done"].items() if w >= keep} | {week: done}
    hs.save(settings, ROTA, rota)
    left = [c for c in turns if c not in done]
    return f"Marked {', '.join(names)} done." + (f" Still to do: {', '.join(left)}." if left else " All done this week.")


# Cleaning schedule (every N days)

def _last(row: dict) -> date | None:
    return date.fromisoformat(row["last"]) if row.get("last") else None


def clean_add(settings: Settings, label, every, last=None) -> str:
    label = hs.need(label, "cleaning job", 60)
    every = int(hs.number(every, "number of days", 1, 365))
    found = hh.rows(settings, CLEANING)
    k = hs.find(found, label) or label
    done = hs.parse_day(last).isoformat() if last else (found.get(k) or {}).get("last")
    hh.put(settings, CLEANING, found, k, {"every": every, "last": done})
    return f"{k} every {hs.plural(every, 'day')}."


def _clean_next(row: dict) -> date:
    last = _last(row)
    return last + timedelta(days=int(row["every"])) if last else hs.today()


def clean_due(settings: Settings) -> screen.Shown | str:
    found = hh.rows(settings, CLEANING)
    if not found:
        return "No cleaning jobs set up yet."
    today = hs.today()
    due = sorted((_clean_next(r), k) for k, r in found.items() if _clean_next(r) <= today)
    items = [{"label": k + ("" if when == today else f" (due {hh.until(when, today)})"),
              "say": f"I've done the cleaning job {k}."} for when, k in due]
    card = screen.card("list", "Cleaning due today", "household-cleaning", items=items, checks=True,
                       buttons=[{"label": "Whole schedule", "say": "Show my whole cleaning schedule."}])
    said = f"Cleaning due today: {', '.join(k for _, k in due)}." if due else "No cleaning due today."
    return screen.Shown(said, card)


def clean_list(settings: Settings) -> screen.Shown | str:
    found = hh.rows(settings, CLEANING)
    if not found:
        return "No cleaning jobs set up yet."
    today = hs.today()
    rows = [[k, f"every {hs.plural(r['every'], 'day')}", hh.short(_last(r)) if _last(r) else "never",
             hh.until(_clean_next(r), today)] for k, r in sorted(found.items(), key=lambda kv: _clean_next(kv[1]))]
    card = screen.card("table", "Cleaning schedule", "household-cleaning-all",
                       columns=["Job", "How often", "Last done", "Next"], rows=rows)
    return screen.Shown(f"Your cleaning schedule has {hs.plural(len(rows), 'job')}; it's on the screen.", card)


def clean_done(settings: Settings, names) -> str:
    found = hh.rows(settings, CLEANING)
    keys = [hh.key(found, n, "cleaning job") for n in hh.words(names)]
    if not keys:
        raise ValueError("Which cleaning job is done?")
    for k in keys:
        found[k]["last"] = hs.today().isoformat()
    hs.save(settings, CLEANING, found)
    return "Done: " + "; ".join(f"{k}, next {hs.spoken(_clean_next(found[k]))}" for k in keys) + "."


# Home maintenance (every N months)

def fix_add(settings: Settings, label, months, last=None) -> str:
    label = hs.need(label, "maintenance job", 60)
    months = int(hs.number(months, "number of months", 1, 120))
    found = hh.rows(settings, UPKEEP)
    k = hs.find(found, label) or label
    done = hs.parse_day(last).isoformat() if last else (found.get(k) or {}).get("last")
    hh.put(settings, UPKEEP, found, k, {"months": months, "last": done})
    return f"{k} every {hs.plural(months, 'month')}, next due {hs.spoken(_fix_next(found[k]))}."


def _fix_next(row: dict) -> date:
    last = _last(row)
    return hh.add_months(last, int(row["months"])) if last else hs.today()


def fix_due(settings: Settings) -> screen.Shown | str:
    found = hh.rows(settings, UPKEEP)
    if not found:
        return "No maintenance jobs set up yet."
    today = hs.today()
    end = hh.month_end(today)
    rows = []
    for k, r in sorted(found.items(), key=lambda kv: _fix_next(kv[1])):
        when = _fix_next(r)
        state = "overdue" if when < today else "this month" if when <= end else ""
        rows.append([k, f"every {hs.plural(r['months'], 'month')}", hh.short(when), state])
    due = [r[0] for r in rows if r[3]]
    card = screen.card("table", "Home maintenance", "household-maintenance",
                       columns=["Job", "How often", "Next due", ""], rows=rows)
    said = f"Due this month: {', '.join(due)}." if due else "No maintenance due this month."
    return screen.Shown(said, card)


def fix_done(settings: Settings, label, last=None) -> str:
    found = hh.rows(settings, UPKEEP)
    k = hh.key(found, label, "maintenance job")
    found[k]["last"] = hs.parse_day(last).isoformat()
    hs.save(settings, UPKEEP, found)
    return f"Marked {k} done. Next due {hs.spoken(_fix_next(found[k]))} {_fix_next(found[k]).year}."


# Laundry

def laundry_symbol(query) -> screen.Shown:
    want = set(hs.need(query, "symbol", 120).lower().replace("-", " ").split()) - FILLER
    scored = sorted(((len(want & set(f"{a} {b} {c}".lower().split())), i) for i, (a, b, c) in enumerate(SYMBOLS)),
                    reverse=True)
    best = [SYMBOLS[i] for n, i in scored if n and n >= scored[0][0] - 1][:5]
    if not best:
        raise ValueError("I don't recognise that symbol; describe its shape, like 'triangle with two lines'.")
    card = screen.card("table", "Laundry symbols", "household-laundry-match", columns=["Symbol", "Meaning"],
                       rows=[[a, b] for a, b, _ in best])
    return screen.Shown(f"{best[0][0]}: {best[0][1]}.", card)


def laundry_symbols() -> screen.Shown:
    card = screen.card("table", "Laundry care symbols", "household-laundry", columns=["Symbol", "Meaning"],
                       rows=[[a, b] for a, b, _ in SYMBOLS])
    return screen.Shown("The laundry symbols chart is on the screen.", card)


def laundry_timer(settings: Settings, minutes, label=None) -> screen.Shown:
    minutes = hs.number(minutes, "number of minutes", 1, 600)
    label = hs.clean(label, 30) or "laundry"
    said = timers.set_timer(settings, minutes * 60, label)
    card = screen.card("timer", label.capitalize(), f"household-timer-{label}",
                       ends_at=int(time.time() * 1000 + minutes * 60_000),
                       buttons=[{"label": "Cancel", "say": f"Cancel the {label} timer."}])
    return screen.Shown(said, card)


def tool_definitions() -> list[dict]:
    text = {"type": "string"}
    return [{
        "name": "household_chores",
        "description": "Chores rota, cleaning schedule, home maintenance and laundry. rota_people (items = names), "
                       "rota_add (items = chores), rota_remove (name), rota_week shows this week's table of whose "
                       "turn it is, rota_next next week's, rota_whose (name = chore: 'whose turn is it to hoover?'), "
                       "rota_done (items = chores). Chores rotate every Monday. clean_add (name, every = days, "
                       "optional date last done), clean_due pops up today's cleaning checklist, clean_list, clean_done "
                       "(items). fix_add home maintenance like smoke alarm test or gutters (name, months, optional "
                       "date last done), fix_due what's due this month, fix_done (name, optional date). "
                       "laundry_symbol (query = the care label symbol described), laundry_symbols chart, "
                       "laundry_timer (minutes, optional name) for the washing machine or dryer. Set confirmed true "
                       "only after the user confirms a remove.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": [
                    "rota_people", "rota_add", "rota_remove", "rota_week", "rota_next", "rota_whose", "rota_done",
                    "clean_add", "clean_due", "clean_list", "clean_done", "fix_add", "fix_due", "fix_done",
                    "laundry_symbol", "laundry_symbols", "laundry_timer"]},
                "name": text,
                "items": {"type": "array", "items": text},
                "every": {"type": "integer", "description": "Days between cleans."},
                "months": {"type": "integer", "description": "Months between maintenance jobs."},
                "date": {"type": "string", "description": "YYYY-MM-DD, 'today' or 'yesterday'."},
                "query": text,
                "minutes": {"type": "number"},
                "confirmed": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"household_chores"}


async def run_tool(name: str, args: dict, settings: Settings, http=None):
    a = args.get
    label, items, ok = a("name"), a("items"), bool(a("confirmed"))
    actions = {
        "rota_people": lambda: rota_people(settings, items),
        "rota_add": lambda: rota_add(settings, items or [label]),
        "rota_remove": lambda: rota_remove(settings, label, ok),
        "rota_week": lambda: rota_week(settings),
        "rota_next": lambda: rota_next(settings),
        "rota_whose": lambda: rota_whose(settings, label),
        "rota_done": lambda: rota_done(settings, items or [label]),
        "clean_add": lambda: clean_add(settings, label, a("every"), a("date")),
        "clean_due": lambda: clean_due(settings),
        "clean_list": lambda: clean_list(settings),
        "clean_done": lambda: clean_done(settings, items or [label]),
        "fix_add": lambda: fix_add(settings, label, a("months"), a("date")),
        "fix_due": lambda: fix_due(settings),
        "fix_done": lambda: fix_done(settings, label, a("date")),
        "laundry_symbol": lambda: laundry_symbol(a("query") or label),
        "laundry_symbols": laundry_symbols,
        "laundry_timer": lambda: laundry_timer(settings, a("minutes"), label),
    }
    if a("action") not in actions:
        raise ValueError("Unknown household chores action.")
    return actions[a("action")]()
