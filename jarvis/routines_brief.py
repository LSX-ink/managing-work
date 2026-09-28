"""Briefings and assistant smarts: a morning briefing, an evening wrap-up, a week planner, what's next today,
a "what can you do?" guide built from the docs, and a reflective question of the day.

Everything is gathered from the other abilities' own files (to-dos, habits, money, reminders, bills, birthdays,
steps, water) and the calendar, then shown in one pop-up.
"""

import asyncio
import datetime as dt
import re
from pathlib import Path

import agenda
import dates_saved
import growth_goals
import habits
import homehouse
import homestore as hs
import homewellbeing
import money
import reminders
import screen
import todo
from config import Settings

DOCS = Path(__file__).resolve().parent / "docs"
SNAPSHOT = ".routines-todo-snapshot.json"
ACTIONS = ["morning", "evening", "week", "next", "help", "thought"]
QUESTIONS = [
    "What made you smile today?", "What's one thing you'd like to do differently tomorrow?",
    "Who made your day a little better, and have you told them?", "What are you looking forward to this week?",
    "What drained your energy today, and what gave you energy?", "What's something you learned recently?",
    "What would make tomorrow a good day?", "What's a small win you haven't celebrated yet?",
    "What are you worrying about that you can't control?", "When did you last feel really calm?",
    "What habit would your future self thank you for?", "What's something you're proud of this month?",
    "What would you do today if you weren't afraid?", "Which conversation have you been putting off?",
    "What's one thing you could let go of?", "What does a perfect ordinary day look like for you?",
    "What are three things you're grateful for right now?", "What have you been avoiding, and why?",
    "Who do you miss, and could you reach out to them?", "What did you do today just for yourself?",
    "What advice would you give yourself a year ago?", "What is taking up too much of your time?",
    "What's the kindest thing you did this week?", "What does rest mean to you at the moment?",
    "What surprised you today?", "What's one step towards a bigger goal you could take tomorrow?",
    "What are you holding onto that you no longer need?", "What made you feel capable recently?",
    "Where did you feel most at home this week?", "What's a question you'd like answered this year?",
    "What small comfort got you through a hard moment lately?", "What are you curious about right now?",
    "What would you like more of in your life, and less of?", "How have you changed in the last year?",
    "What does success look like for you this month?", "What did you say yes to that you wish you hadn't?",
    "Which moment today would you like to remember?", "What's one boundary you'd like to keep?",
    "What would you tell a friend in your situation?", "If today had a title, what would it be?",
]


def _clock(when: dt.datetime) -> str:
    return when.strftime("%H:%M")


async def _events(http, settings: Settings, start: dt.datetime, days: int) -> list[dict] | None:
    """Calendar events from start for days, or None when no calendar is connected or it can't be read."""
    if not agenda.configured(settings):
        return None
    try:
        cal = await agenda._calendar(http, settings)
    except Exception:  # an unreachable calendar must not spoil the whole briefing
        return None
    return agenda.events_between(cal, start, start + dt.timedelta(days=days))


def _event_line(e: dict) -> str:
    where = f" at {e['where']}" if e["where"] else ""
    return f"{'all day' if e['all_day'] else _clock(e['start'])} {e['title']}{where}"


def reminders_between(settings: Settings, start: dt.datetime, end: dt.datetime) -> list[tuple[dt.datetime, str]]:
    """Every reminder in [start, end), with repeating ones repeated."""
    found = []
    for r in reminders.load(settings):
        at, repeat = reminders.parse_when(r["at"]), r.get("repeat", "once")
        while at < end:
            if at >= start:
                found.append((at, r["text"]))
            if repeat == "once":
                break
            at = reminders.next_time(at, repeat)
    return sorted(found)


def _habits_split(settings: Settings, day: dt.date) -> tuple[list[str], list[str]]:
    done, left = [], []
    for name, days in habits.load(settings).items():
        (done if day.isoformat() in days else left).append(name)
    return done, left


async def _weather(http, settings: Settings) -> str:
    import tools  # imported here: tools imports this module
    try:
        return await asyncio.wait_for(tools.get_weather(http, settings.city, 1), 10)
    except Exception as exc:
        return f"unavailable ({exc.__class__.__name__})"


def _snapshot(settings: Settings, day: dt.date, open_now: list[str]) -> None:
    """Remember this morning's open to-dos, so the evening wrap-up can tell which got done."""
    if hs.load(settings, SNAPSHOT, {}).get("date") != day.isoformat():
        hs.save(settings, SNAPSHOT, {"date": day.isoformat(), "open": open_now})


def _card(title: str, card_id: str, text: str, rows: list[list[str]], buttons=None) -> dict:
    return screen.card("table", title, card_id, text=text, columns=["", ""], rows=rows, buttons=buttons)


async def morning(settings: Settings, http) -> screen.Shown:
    now = hs.now()
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    weather, events = await asyncio.gather(_weather(http, settings), _events(http, settings, start, 1))
    jobs = todo.open_items(settings)
    _snapshot(settings, now.date(), jobs)
    later = [f"{_clock(at)} {t}" for at, t in reminders_between(settings, now, start + dt.timedelta(days=1))]
    _, habits_left = _habits_split(settings, now.date())
    calendar = "no calendar connected" if events is None else "; ".join(map(_event_line, events)) or "nothing"
    rows = [["Date", hs.spoken(now.date()) + f" {now.year}"], ["Weather", weather], ["Calendar", calendar],
            ["To-dos", f"{len(jobs)} open" + (f": {', '.join(jobs[:5])}" if jobs else "")],
            ["Reminders", "; ".join(later) or "none later today"],
            ["Habits to do", ", ".join(habits_left) or "none"]]
    facts = "\n".join(f"{a}: {b}" for a, b in rows)
    card = _card(f"Good morning: {hs.spoken(now.date())}", "routines-morning", "", rows,
                 buttons=[{"label": "What's next?", "say": "What's next today?"},
                          {"label": "My to-dos", "say": "Show my to-do list."}])
    return screen.Shown(f"Morning briefing (on screen). Sum it up in one short spoken sentence:\n{facts}", card)


def _done_todos(settings: Settings, day: dt.date) -> str:
    snap = hs.load(settings, SNAPSHOT, {})
    if snap.get("date") != day.isoformat():
        return "not tracked today (it starts with a morning briefing)"
    still = {j.lower() for j in todo.open_items(settings)}
    done = [j for j in snap.get("open") or [] if isinstance(j, str) and j.lower() not in still]
    return f"{len(done)} ticked off" + (f": {', '.join(done)}" if done else "")


async def evening(settings: Settings, http) -> screen.Shown:
    now = hs.now()
    today = now.date()
    tomorrow = dt.datetime.combine(today + dt.timedelta(days=1), dt.time())
    events = await _events(http, settings, tomorrow, 1)
    habits_done, habits_left = _habits_split(settings, today)
    spent = sum(s.get("amount", 0) for s in money.load(settings)["spending"] if s.get("date") == today.isoformat())
    steps = growth_goals._steps(settings)["days"].get(today.isoformat(), {}).get("steps", 0)
    well = homewellbeing.load(settings)
    water = well["water"].get(today.isoformat(), 0)
    later = [f"{_clock(at)} {t}" for at, t in reminders_between(settings, tomorrow, tomorrow + dt.timedelta(days=1))]
    calendar = "no calendar connected" if events is None else "; ".join(map(_event_line, events)) or "nothing"
    rows = [["To-dos", _done_todos(settings, today)],
            ["Habits done", ", ".join(habits_done) or "none"],
            ["Habits missed", ", ".join(habits_left) or "none"],
            ["Spent today", hs.money(spent, settings.currency)],
            ["Steps", f"{steps:,}"], ["Water", f"{water:g} of {well['goal']} glasses"],
            ["Tomorrow", calendar], ["Tomorrow's reminders", "; ".join(later) or "none"]]
    facts = "\n".join(f"{a}: {b}" for a, b in rows)
    card = _card(f"Evening wrap-up: {hs.spoken(today)}", "routines-evening", "", rows,
                 buttons=[{"label": "Thought for the day", "say": "Give me today's reflective question."}])
    return screen.Shown(f"Evening wrap-up (on screen). Sum it up in one short spoken sentence:\n{facts}", card)


def _bills(settings: Settings, start: dt.date, end: dt.date) -> list[tuple[dt.date, str]]:
    found = []
    for label, row in homehouse._rows(settings, homehouse.BILLS).items():
        year, month = start.year, start.month
        for _ in range(2):
            when = homehouse._bill_date(int(row["day"]), year, month)
            if start <= when < end:
                found.append((when, f"{label} bill, {hs.money(row['amount'], settings.currency)}"))
            year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    return found


def _birthdays(settings: Settings, start: dt.date, end: dt.date) -> list[tuple[dt.date, str]]:
    found = []
    for name, value in dates_saved.load(settings, "birthday").items():
        when, age = dates_saved._next_birthday(value, start)
        if when < end:
            found.append((when, f"{name}'s birthday" + (f" ({age})" if age is not None else "")))
    return found


async def week(settings: Settings, http) -> screen.Shown:
    now = hs.now()
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + dt.timedelta(days=7)
    events = await _events(http, settings, start, 7)
    rows = [(e["start"], "" if e["all_day"] else _clock(e["start"]), e["title"], "Calendar") for e in events or []]
    rows += [(at, _clock(at), text, "Reminder") for at, text in reminders_between(settings, now, end)]
    for day, text in _bills(settings, start.date(), end.date()):
        rows.append((dt.datetime.combine(day, dt.time()), "", text, "Bill"))
    for day, text in _birthdays(settings, start.date(), end.date()):
        rows.append((dt.datetime.combine(day, dt.time()), "", text, "Birthday"))
    rows.sort(key=lambda r: (r[0], r[1]))
    table = [[f"{r[0]:%a} {r[0].day}", r[1], r[2], r[3]] for r in rows]
    note = "" if events is not None else "No calendar is connected, so only reminders, bills and birthdays."
    card = screen.card("table", "The week ahead", "routines-week", text=note,
                       columns=["Day", "Time", "What", "Kind"], rows=table)
    lines = "\n".join(" ".join(filter(None, r)) for r in table) or "Nothing planned."
    return screen.Shown(f"Week planner (on screen), {len(table)} items. Mention the main ones briefly:\n{lines}", card)


async def next_up(settings: Settings, http) -> str | screen.Shown:
    now = hs.now()
    end = now.replace(hour=0, minute=0, second=0, microsecond=0) + dt.timedelta(days=1)
    events = await _events(http, settings, now.replace(hour=0, minute=0, second=0, microsecond=0), 1) or []
    coming = [(e["start"], e["title"]) for e in events if not e["all_day"] and e["start"] > now]
    coming += reminders_between(settings, now, end)
    if not coming:
        return "Nothing else in the calendar or reminders today."
    at, title = min(coming)
    minutes = round((at - now).total_seconds() / 60)
    left = f"{minutes // 60} hour{'s' if minutes >= 120 else ''} {minutes % 60} minutes" if minutes >= 60 \
        else hs.plural(minutes, "minute")
    card = screen.card("timer", f"Next: {title} at {_clock(at)}", "routines-next",
                       ends_at=int(at.astimezone().timestamp() * 1000))
    return screen.Shown(f"Next up today: {title} at {_clock(at)}, in {left}.", card)


# ---- "What can you do?" ------------------------------------------------------------------------

LINE = re.compile(r"^\s*(?:[-*]|\d+\.)\s+(?:\*\*(?P<bold>[^*]+?)\*\*|(?P<plain>[A-Z][^:\"]{1,50}):)")


def guide() -> dict[str, list[tuple[str, str]]]:
    """{topic: [(label, first example phrase)]} from the docs/*.md files."""
    topics = {}
    for path in sorted(DOCS.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        head = re.search(r"^#\s+(.+)$", text, re.M)
        found = []
        for line in text.splitlines():
            m = LINE.match(line)
            said = re.search(r"\"([^\"]+)\"", line)
            if m and said:
                found.append(((m.group("bold") or m.group("plain")).strip().rstrip(":"), said.group(1)))
        if found:
            topics[head.group(1).split(":")[0].strip() if head else path.stem] = found
    return topics


def help_card(topic: str = "") -> screen.Shown:
    topics = guide()
    want = hs.clean(topic).lower()
    match = next((t for t in topics if want and (want in t.lower() or t.lower() in want)), None)
    if match is None:
        items = [{"label": f"{t} ({len(v)} things)", "say": f"What can you do for {t.lower()}?"} for t, v in topics.items()]
        card = screen.card("list", "What I can do", "routines-help", items=items)
        return screen.Shown(f"The topics are on screen: {', '.join(topics)}. Click one for examples.", card)
    items = [{"label": f"{label}: \"{said}\"", "say": said} for label, said in topics[match]]
    card = screen.card("list", match, "routines-help", items=items,
                       buttons=[{"label": "All topics", "say": "What can you do?"}])
    return screen.Shown(f"{len(items)} things for {match} are on screen, each with something to say.", card)


def thought(settings: Settings) -> screen.Shown:
    day = hs.today()
    question = QUESTIONS[day.toordinal() % len(QUESTIONS)]
    card = screen.card("text", "Thought of the day", "routines-thought", text=question,
                       buttons=[{"label": "Answer in my diary", "say": f"Add to my diary, answering '{question}': "}])
    return screen.Shown(f"Today's reflective question: {question}", card)


def tool_definitions() -> list[dict]:
    return [{
        "name": "daily_briefing",
        "description": "Briefings and help, each popped up on the screen. action 'morning' (morning briefing: date, "
                       "weather, today's calendar, to-dos, reminders, habits still to do), 'evening' (evening "
                       "wrap-up: what got done today, spending, steps, water, tomorrow's calendar and reminders), "
                       "'week' (week planner: next 7 days of calendar, reminders, bills and birthdays), 'next' "
                       "(what's next today, with a countdown), 'help' ('what can you do?', optional topic), "
                       "'thought' (thought of the day: a reflective journaling question).",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "topic": {"type": "string", "description": "help: a topic such as 'calculators' or 'PC control'."},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"daily_briefing"}


async def run_tool(name: str, args: dict, settings: Settings, http=None):
    action = args.get("action")
    if action == "morning":
        return await morning(settings, http)
    if action == "evening":
        return await evening(settings, http)
    if action == "week":
        return await week(settings, http)
    if action == "next":
        return await next_up(settings, http)
    if action == "thought":
        return await asyncio.to_thread(thought, settings)
    return await asyncio.to_thread(help_card, args.get("topic") or "")
