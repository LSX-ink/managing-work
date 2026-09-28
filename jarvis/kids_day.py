"""Kids' days: a bedtime routine checklist, a turn taker, big visual timers, a packed lunch planner and the family's
week in one pop-up.

The turn taker remembers who went first last time for each activity. The visual timer is a shrinking coloured
circle drawn by frontend/popup-kids.js; for turns it moves on to the next child each time it runs out.
Everything is in kids-bedtime.json, kids-turns.json and kids-lunches.json in the memory folder.
"""

import random
from datetime import date, timedelta

import homestore as hs
import kids_logs
import kids_rewards
import kids_store as ks
import screen
from config import Settings
from kids_lists import LUNCH_IDEAS

BEDTIME, TURNS, LUNCHES = "kids-bedtime.json", "kids-turns.json", "kids-lunches.json"
screen.EXTRA_KINDS.add("kids-timer")
DEFAULT_STEPS = ["Bath", "Pyjamas on", "Brush teeth", "Toilet", "Story", "Cuddle and lights out"]
COLOURS = ("red", "orange", "yellow", "green", "blue", "purple", "pink")
SCHOOL_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
EVERYONE = "Everyone"
MAX_STEPS, MAX_PEOPLE, MAX_IDEAS, KEEP_NIGHTS = 12, 10, 60, 60


# Bedtime routine

def _night() -> date:
    """Tonight: before 5 in the morning still counts as last night."""
    now = hs.now()
    return (now - timedelta(days=1)).date() if now.hour < 5 else now.date()


def _routine(found: dict, name, create: bool = True) -> tuple[str, dict]:
    k = ks.child(found, name, create)
    rec = found.get(k) if isinstance(found.get(k), dict) else {}
    rec.setdefault("steps", list(DEFAULT_STEPS))
    rec.setdefault("done", {})
    found[k] = rec
    return k, rec


def bedtime_steps(settings: Settings, name, items) -> screen.Shown:
    steps = [hs.clean(i, 50) for i in items or [] if hs.clean(i)][:MAX_STEPS]
    if not steps:
        raise ValueError("Which steps? Say something like bath, pyjamas, teeth, story.")
    found = ks.load(settings, BEDTIME)
    k, rec = _routine(found, name)
    rec["steps"] = steps
    ks.save(settings, BEDTIME, found)
    return screen.Shown(f"{k}'s bedtime routine has {hs.plural(len(steps), 'step')}.", _bedtime_card(k, rec))


def _bedtime_card(k: str, rec: dict) -> dict:
    done = {s.lower() for s in rec["done"].get(_night().isoformat(), [])}
    items = [{"label": s, "done": s.lower() in done, "say": f"{k} has done {s} for bedtime."} for s in rec["steps"]]
    return screen.card("list", f"{k}'s bedtime", f"kids-bedtime-{k}", items=items, checks=True,
                       text="Tick each step as it's done.")


def _pick(settings: Settings, found: dict, name) -> str:
    return ks.child(found, name) if hs.clean(name) else ks.only_child(settings, found, name)


def bedtime(settings: Settings, name) -> screen.Shown:
    found = ks.load(settings, BEDTIME)
    k, rec = _routine(found, _pick(settings, found, name))
    ks.save(settings, BEDTIME, found)
    left = len(rec["steps"]) - len(rec["done"].get(_night().isoformat(), []))
    return screen.Shown(f"Bedtime for {k}: {hs.plural(max(0, left), 'step')} to go.", _bedtime_card(k, rec))


def bedtime_done(settings: Settings, name, items) -> screen.Shown:
    found = ks.load(settings, BEDTIME)
    k, rec = _routine(found, _pick(settings, found, name))
    night = _night().isoformat()
    done = rec["done"].setdefault(night, [])
    ticked = []
    for item in items or []:
        step = hs.find(rec["steps"], hs.clean(item))
        if step is None:
            raise ValueError(f"{hs.clean(item)} isn't in {k}'s bedtime routine.")
        if step not in done:
            done.append(step)
        ticked.append(step)
    if not ticked:
        raise ValueError("Which step is done?")
    rec["done"] = dict(sorted(rec["done"].items())[-KEEP_NIGHTS:])
    ks.save(settings, BEDTIME, found)
    left = len(rec["steps"]) - len(done)
    said = f"All done! Sleep tight, {k}." if left <= 0 else \
        f"{', '.join(ticked)} done. {hs.plural(left, 'step')} to go."
    return screen.Shown(said, _bedtime_card(k, rec))


def bedtimes_this_week(settings: Settings) -> dict:
    week = hs.week_start(hs.today()).isoformat()
    out = {}
    for k, rec in ks.load(settings, BEDTIME).items():
        if not isinstance(rec, dict):
            continue
        steps = len(rec.get("steps", []))
        out[k] = sum(night >= week and len(done) >= steps for night, done in rec.get("done", {}).items())
    return out


# Turn taker

def whose_turn(settings: Settings, activity, people) -> screen.Shown:
    found = hs.load(settings, TURNS, {})
    label = hs.clean(activity, 40) or "Turns"
    k = hs.find(found, label) or label
    rec = found.get(k) if isinstance(found.get(k), dict) else {"people": [], "next": 0, "last": ""}
    names = [hs.clean(p, 30) for p in people or [] if hs.clean(p)][:MAX_PEOPLE]
    if names and [n.lower() for n in names] != [n.lower() for n in rec["people"]]:
        rec["people"], rec["next"] = names, 0
        if rec.get("last") and rec["last"] in names:
            rec["next"] = names.index(rec["last"]) + 1
    if len(rec["people"]) < 2:
        raise ValueError("Who's taking turns? Tell me at least two names.")
    n = len(rec["people"])
    first = rec["next"] % n
    order = [rec["people"][(first + i) % n] for i in range(n)]
    last = rec.get("last", "")
    rec.update(next=first + 1, last=order[0], when=hs.today().isoformat())
    found[k] = rec
    hs.save(settings, TURNS, found)
    said = f"{order[0]} goes first" + \
        (f" this time; {last} went first last time." if last and last != order[0] else ".")
    items = [{"label": f"{i + 1}. {p}"} for i, p in enumerate(order)]
    timer_say = f"Start a 5 minute turns timer for {', '.join(order)}."
    card = screen.card("list", f"Whose turn: {k}", f"kids-turns-{k}", items=items,
                       buttons=[{"label": "Next time", "say": f"Whose turn is it to go first at {k}?"},
                                {"label": "Turn timer", "say": timer_say}])
    return screen.Shown(said, card)


# Visual timer

def timer(minutes, seconds, label, colour, people) -> screen.Shown:
    total = int(hs.number(minutes or 0, "minutes", 0, 180) * 60 + hs.number(seconds or 0, "seconds", 0, 3600))
    if total < 5:
        raise ValueError("How long should the timer run?")
    colour = colour if colour in COLOURS else "blue"
    names = [hs.clean(p, 30) for p in people or [] if hs.clean(p)][:MAX_PEOPLE]
    what = hs.clean(label, 40) or ("Turns" if names else "Timer")
    mins, secs = divmod(total, 60)
    long = " and ".join(([hs.plural(mins, "minute")] if mins else []) + ([hs.plural(secs, "second")] if secs else []))
    said = f"{what}: {long}" + (f", {names[0]} first. Go!" if names else ". Go!")
    data = {"seconds": total, "label": what, "colour": colour, "people": names}
    return screen.Shown(said, screen.card("kids-timer", what, "kids-timer", data=data))


# Packed lunches

def _lunches(settings: Settings) -> dict:
    found = hs.load(settings, LUNCHES, {})
    return {"ideas": [i for i in found.get("ideas", []) if isinstance(i, str)],
            "plan": {d: v for d, v in found.get("plan", {}).items() if isinstance(v, dict)}}


def _school_week() -> list[date]:
    today = hs.today()
    monday = hs.week_start(today) + timedelta(days=7 if today.weekday() >= 5 else 0)
    return [monday + timedelta(days=i) for i in range(5)]


def _lunch_day(value, plan: dict, who: str) -> date:
    text = hs.clean(value).lower()
    if text in ("", "next"):
        for d in _school_week() + [d + timedelta(days=7) for d in _school_week()]:
            if d >= hs.today() and not plan.get(d.isoformat(), {}).get(who):
                return d
        raise ValueError("Every school day for the next two weeks already has a lunch planned.")
    day = hs.parse_day(value, _school_week()[0] if text in hs.WEEKDAYS else None)
    if day.weekday() >= 5:
        raise ValueError("Packed lunches are for school days, Monday to Friday.")
    return day


def lunch_plan(settings: Settings, day, text, name) -> screen.Shown:
    found = _lunches(settings)
    who = hs.clean(name, 30) or EVERYONE
    what = hs.need(text, "lunch", 80)
    d = _lunch_day(day, found["plan"], who)
    found["plan"].setdefault(d.isoformat(), {})[who] = what
    found["plan"] = dict(sorted(found["plan"].items())[-60:])
    hs.save(settings, LUNCHES, found)
    whose = "the packed lunch" if who == EVERYONE else f"{who}'s lunch"
    return screen.Shown(f"{what} for {whose} on {d.strftime('%A')}.", _lunch_card(found))


def _lunch_card(found: dict) -> dict:
    week = _school_week()
    who = sorted({w for d in week for w in found["plan"].get(d.isoformat(), {})}, key=lambda w: (w != EVERYONE, w)) \
        or [EVERYONE]
    rows = [[d.strftime("%a %d")] + [found["plan"].get(d.isoformat(), {}).get(w, "") for w in who] for d in week]
    return screen.card("table", f"Packed lunches, week of {hs.spoken(week[0])}", "kids-lunches",
                       columns=["Day"] + who, rows=rows,
                       buttons=[{"label": "Fill the gaps", "say": "Fill the empty packed lunch days with ideas."},
                                {"label": "Lunch ideas", "say": "Show the packed lunch ideas."}])


def lunch_week(settings: Settings, fill: bool, name) -> screen.Shown:
    found = _lunches(settings)
    said = "This week's packed lunches are on the screen."
    if fill:
        who = hs.clean(name, 30) or EVERYONE
        ideas = found["ideas"] + LUNCH_IDEAS
        used = {v for d in _school_week() for v in found["plan"].get(d.isoformat(), {}).values()}
        fresh = [i for i in dict.fromkeys(ideas) if i not in used] or ideas
        random.shuffle(fresh)
        filled = 0
        for d in _school_week():
            slot = found["plan"].setdefault(d.isoformat(), {})
            if not slot.get(who):
                slot[who] = fresh[filled % len(fresh)]
                filled += 1
        hs.save(settings, LUNCHES, found)
        said = f"Filled {hs.plural(filled, 'day')} with ideas." if filled else "Every day already has a lunch."
    return screen.Shown(said, _lunch_card(found))


def lunch_ideas(settings: Settings, items) -> screen.Shown:
    found = _lunches(settings)
    have = {i.lower() for i in found["ideas"] + LUNCH_IDEAS}
    new = [i for i in (hs.clean(x, 80) for x in items or []) if i and i.lower() not in have]
    if new:
        found["ideas"] = (found["ideas"] + new)[-MAX_IDEAS:]
        hs.save(settings, LUNCHES, found)
    ideas = found["ideas"] + LUNCH_IDEAS
    card = screen.card("list", "Packed lunch ideas", "kids-lunch-ideas",
                       items=[{"label": i, "say": f"Put {i} in the next packed lunch."} for i in ideas],
                       text="Tap one to put it in the next empty day.")
    said = f"Added {', '.join(new)}. " if new else ""
    return screen.Shown(said + f"{hs.plural(len(ideas), 'lunch idea')} on the screen.", card)


# The family's week

def family_week(settings: Settings) -> screen.Shown:
    kids = ks.children(settings)
    if not kids:
        raise ValueError("I haven't got anything saved for the children yet.")
    stars = kids_rewards.stars_this_week(settings)
    money = kids_rewards.pocket_totals(settings)
    reading = kids_logs.reading_this_week(settings)
    firsts = kids_logs.milestones_this_week(settings)
    heights = kids_logs.latest_height(settings)
    beds = bedtimes_this_week(settings)
    rows = []
    for k in kids:
        mins, books = reading.get(k, (0, 0))
        rows.append([k, str(stars.get(k, 0)), f"{mins} min" + (f", {hs.plural(books, 'book')}" if books else ""),
                     str(beds.get(k, 0)), ks.cash(money[k], settings.currency) if k in money else "",
                     "; ".join(firsts.get(k, [])), heights.get(k, "")])
    total = sum(stars.values())
    card = screen.card("table", f"Family week of {hs.spoken(hs.week_start(hs.today()))}", "kids-family-week",
                       columns=["Child", "Stars", "Reading", "Bedtimes done", "Money", "Firsts", "Height"], rows=rows)
    return screen.Shown(f"The family's week is on the screen: {hs.plural(total, 'star')} so far.", card)


# The tool

ACTIONS = ("bedtime_routine", "bedtime_steps", "bedtime_done", "whose_turn", "kids_timer", "lunch_plan",
           "lunch_week", "lunch_ideas", "family_week")


def tool_definitions() -> list[dict]:
    text = {"type": "string"}
    listed = {"type": "array", "items": text}
    return [{
        "name": "kids_day",
        "description": "Everyday help with children. action: 'bedtime_routine' pop up a child's bedtime "
                       "checklist; 'bedtime_steps' set its steps (items); 'bedtime_done' tick steps (items); "
                       "'whose_turn' who goes first, remembering who went first last time (activity, people); "
                       "'kids_timer' big visual countdown for screen time, tidy-up or taking turns (minutes, "
                       "seconds, label, colour, people to rotate); 'lunch_plan' packed lunch for a school day "
                       "(day = weekday, date or 'next', text, child); 'lunch_week' the week's packed lunches, "
                       "fill true fills empty days from ideas; 'lunch_ideas' show or add ideas (items); "
                       "'family_week' weekly family summary of stars, reading, bedtimes, money and firsts.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": list(ACTIONS)},
                "child": {"type": "string", "description": "The child's first name."},
                "items": listed,
                "activity": text,
                "people": listed,
                "minutes": {"type": "number"},
                "seconds": {"type": "number"},
                "label": text,
                "colour": {"type": "string", "enum": list(COLOURS)},
                "day": text,
                "text": text,
                "fill": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"kids_day"}


def run_tool(name: str, args: dict, settings: Settings, http=None):
    a = args.get
    kid = a("child")
    actions = {
        "bedtime_routine": lambda: bedtime(settings, kid),
        "bedtime_steps": lambda: bedtime_steps(settings, kid, a("items")),
        "bedtime_done": lambda: bedtime_done(settings, kid, a("items")),
        "whose_turn": lambda: whose_turn(settings, a("activity"), a("people")),
        "kids_timer": lambda: timer(a("minutes"), a("seconds"), a("label"), a("colour"), a("people")),
        "lunch_plan": lambda: lunch_plan(settings, a("day"), a("text"), kid),
        "lunch_week": lambda: lunch_week(settings, bool(a("fill")), kid),
        "lunch_ideas": lambda: lunch_ideas(settings, a("items")),
        "family_week": lambda: family_week(settings),
    }
    if a("action") not in actions:
        raise ValueError(f"I can't do {a('action')} with the kids' day.")
    return actions[a("action")]()
