"""Assistant: the proactive helper for your day. A smart morning briefing, an evening wrap-up, "what should I do
next", a time-blocked plan, meeting prep, a weekly review, focus mode and today's energy.

It builds on the routines briefings: it reuses their calendar, weather, reminder and birthday readers and adds
follow-ups, promises, countdowns, nudges and the news headline count. Everything is read-only apart from the
assistant.json file (focus, energy) and the to-do snapshot the wrap-up counts from.
"""

import asyncio
from datetime import datetime, timedelta

import assistant_plan as plan
import assistant_store as st
import feeds
import habits
import homestore as hs
import routines_brief as rb
import routines_life
import screen
import todo
from config import Settings

ACTIONS = ["briefing", "wrapup", "next_task", "time_block", "meeting_prep", "weekly_review", "focus_start",
           "focus_stop", "focus_status", "energy_set"]


async def _headlines(http) -> list[str]:
    try:
        r = await asyncio.wait_for(feeds.fetch(http, feeds.BBC + feeds.SECTIONS["top"], "BBC News"), 10)
        return [title for title, _ in feeds.parse_rss(r.text)]
    except Exception:  # the news line is a bonus; the briefing stands without it
        return []


def _calendar(events) -> list[str]:
    return ["No calendar connected."] if events is None else [rb._event_line(e) for e in events] or ["Nothing in the calendar."]


def _focus_line(data: dict, now: datetime) -> list[str]:
    f = data["focus"]
    if not f.get("active"):
        return []
    left = max(0, round((datetime.fromisoformat(f["ends"]) - now).total_seconds() / 60))
    return [f"Focus mode is on, {hs.plural(left, 'minute')} left" + (f": {f['note']}" if f.get("note") else "")]


async def briefing(settings: Settings, http) -> screen.Shown:
    now = hs.now()
    today = now.date()
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    weather, events, news = await asyncio.gather(rb._weather(http, settings), rb._events(http, settings, start, 1), _headlines(http))
    data, jobs = st.load(settings), todo.open_items(settings)
    rb._snapshot(settings, today, jobs)
    top = plan.ranked(settings, data, today, plan.energy_today(data, today))[:1]
    later = [f"{rb._clock(at)} {t}" for at, t in rb.reminders_between(settings, now, start + timedelta(days=1))]
    born = [f"{text} {st.when_words(d.isoformat(), today)}" for d, text in rb._birthdays(settings, today, today + timedelta(days=7))]
    chase = [st.item_line(i, today) for i in st.due_items(data, today)]
    owed = [f"To {p['person']}: {p['what']}" for p in st.promises(settings) if p.get("due") and p["due"] <= today.isoformat()]
    sections = [
        st.section("Today", [f"{hs.spoken(today)}, {weather}", *_calendar(events)]),
        st.section("Start with", [st.line(t["text"], f"Tick off {t['text']} on my to-do list." if t["source"] == "todo" else "")
                                  for t in top]),
        st.section("Chase today", chase + owed, "alert"), st.section("Reminders later", later),
        st.section("Coming up", [*born, *st.countdown_soon(data, today)]),
        st.section("Don't forget", st.nudges(data, today), "alert"),
        st.section("Open", [f"{len(jobs)} to-dos", f"{len(st.open_items(data, 'waiting'))} waiting for",
                            f"{len(routines_life._inbox_lines(settings))} in the inbox to sort"]),
        st.section("Focus", _focus_line(data, now)),
        st.section("News", [st.line(f"{len(news)} top headlines. First: {news[0]}", "Play today's news.")] if news else []),
        st.section("I'll remember", [p["text"] for p in data["prefs"][:3]]),
    ]
    card = st.panel(f"Good morning, {hs.spoken(today)}", "assistant-briefing", f"{hs.plural(len(jobs), 'to-do')} open"
                    + (f", {len(chase + owed)} to chase" if chase + owed else ""), sections,
                    buttons=[{"label": "Plan my day", "say": "Time-block my day."}, {"label": "What next?", "say": "What should I do next?"}])
    facts = "; ".join(f"{s['title']}: {' | '.join(ln if isinstance(ln, str) else ln['text'] for ln in s['lines'])}"
                      for s in card["data"]["sections"])
    return screen.Shown(f"Morning briefing (on screen). Sum it up in two short sentences, most important first: {facts}", card)


async def wrapup(settings: Settings, http) -> screen.Shown:
    now = hs.now()
    today = now.date()
    tomorrow = datetime.combine(today + timedelta(days=1), datetime.min.time())
    events = await rb._events(http, settings, tomorrow, 1)
    data, still = st.load(settings), {j.lower() for j in todo.open_items(settings)}
    snap = hs.load(settings, rb.SNAPSHOT, {})
    ticked = [j for j in snap.get("open") or [] if snap.get("date") == today.isoformat() and j.lower() not in still]
    closed = [i["what"] for i in data["items"] if i.get("done") == today.isoformat()]
    wins = [w["text"] for w in data["wins"] if w["date"] == today.isoformat()]
    left = [*todo.open_items(settings)[:6], *[st.item_line(i, today) for i in st.due_items(data, today)]]
    _, habits_left = rb._habits_split(settings, today)
    first = [rb._event_line(e) for e in (events or [])[:1]] or [f"{rb._clock(at)} {t}" for at, t in
                                                                rb.reminders_between(settings, tomorrow, tomorrow + timedelta(days=1))[:1]]
    best = plan.ranked(settings, data, today + timedelta(days=1))[:1]
    sections = [st.section("Done today", [*ticked, *closed, *wins]), st.section("Still open", left, "alert"),
                st.section("Habits not done", habits_left), st.section("Tomorrow's first thing", first or [b["text"] for b in best])]
    card = st.panel(f"Wrap-up, {hs.spoken(today)}", "assistant-wrapup", f"{len(ticked) + len(closed) + len(wins)} done, {len(left)} left", sections,
                    buttons=[{"label": "Log a win", "say": "Log a win from today."}])
    said = f"{len(ticked) + len(closed) + len(wins)} things done today, {len(left)} still open."
    return screen.Shown(f"Evening wrap-up (on screen). Say it warmly in one or two short sentences: {said} "
                        f"Tomorrow's first thing: {(first or [b['text'] for b in best] or ['nothing yet'])[0]}", card)


def next_task(settings: Settings, minutes, energy) -> screen.Shown | str:
    data, today = st.load(settings), hs.today()
    level = energy if energy in plan.ENERGY else plan.energy_today(data, today)
    found = plan.ranked(settings, data, today, level, int(minutes or 0))
    if not found:
        return "Nothing is waiting: your to-do list and follow-ups are clear."
    top = found[0]
    ticks = [{"label": "Done", "say": f"Tick off {top['text']} on my to-do list."}] if top["source"] == "todo" else []
    sections = [st.section("Do this now", [top["text"] + (f" ({', '.join(top['why'])})" if top["why"] else "")]),
                st.section("Then", [st.line(f["text"], f"Tick off {f['text']} on my to-do list." if f["source"] == "todo" else "") for f in found[1:5]])]
    card = st.panel("What to do next", "assistant-next", f"{level} energy" + (f", {minutes} minutes" if minutes else ""), sections, ticks)
    return screen.Shown(f"Do this next: {top['text']}.", card)


def energy_set(settings: Settings, level, mood) -> str:
    if level not in plan.ENERGY:
        raise ValueError("Energy is low, medium or high.")
    data = st.load(settings)
    data["energy"] = {"date": hs.today().isoformat(), "level": level, "mood": hs.clean(mood, 40)}
    st.save(settings, data)
    hint = {"low": "quick, light jobs first", "medium": "a steady mix", "high": "the deep, hard jobs first"}[level]
    return f"Noted, {level} energy today. I'll suggest {hint}."


def focus_start(settings: Settings, minutes, note, what) -> screen.Shown:
    data, now = st.load(settings), hs.now()
    if data["focus"].get("active"):
        return focus_status(settings)
    length = int(hs.number(minutes or 45, "focus length", 5, 240))
    data["focus"] = {"active": True, "started": now.isoformat(timespec="minutes"), "what": hs.clean(what, 80),
                     "ends": (now + timedelta(minutes=length)).isoformat(timespec="minutes"),
                     "note": hs.clean(note, 120) or "Do not disturb"}
    st.save(settings, data)
    return screen.Shown(f"Focus mode on for {length} minutes. Do not disturb: keep replies to one short sentence and "
                        f"offer nothing extra until it ends.", _focus_card(data["focus"]))


def _focus_card(f: dict) -> dict:
    ends = datetime.fromisoformat(f["ends"])
    title = f"Focus: {f['what']}" if f.get("what") else "Focus mode"
    return screen.card("timer", title, "assistant-focus", text=f"{f['note']}. Non-urgent things can wait.",
                       ends_at=int(ends.timestamp() * 1000), buttons=[{"label": "Stop focus", "say": "Stop focus mode."}])


def focus_status(settings: Settings) -> screen.Shown | str:
    f = st.load(settings)["focus"]
    if not f.get("active"):
        return "Focus mode is off."
    left = max(0, round((datetime.fromisoformat(f["ends"]) - hs.now()).total_seconds() / 60))
    return screen.Shown(f"Focus mode is on, {hs.plural(left, 'minute')} left.", _focus_card(f))


def focus_stop(settings: Settings) -> screen.Shown | str:
    data, now = st.load(settings), hs.now()
    f = data["focus"]
    if not f.get("active"):
        return "Focus mode wasn't on."
    minutes = max(1, round((now - datetime.fromisoformat(f["started"])).total_seconds() / 60))
    st.put(data, "focuslog", {"date": now.date().isoformat(), "minutes": minutes, "what": f.get("what", "")})
    data["focus"] = {}
    st.save(settings, data)
    total = sum(e["minutes"] for e in data["focuslog"] if e["date"] == now.date().isoformat())
    card = {"kind": "close", "all": False, "title": _focus_card(f)["title"]}
    return screen.Shown(f"Focus mode off after {hs.plural(minutes, 'minute')}. {total} minutes of focus today. Welcome back.", card)


def weekly_review(settings: Settings, http) -> screen.Shown:
    data, today = st.load(settings), hs.today()
    start = (today - timedelta(days=6)).isoformat()
    wins = [w["text"] for w in data["wins"] if w["date"] >= start]
    closed = [i["what"] for i in data["items"] if i.get("done") and i["done"] >= start]
    focus = sum(e["minutes"] for e in data["focuslog"] if e["date"] >= start)
    made = [d["text"] for d in data["decisions"] if d["date"] >= start]
    days = [(today - timedelta(days=n)).isoformat() for n in range(7)]
    habit = [f"{name}: {sum(d in log for d in days)} of 7 days" for name, log in habits.load(settings).items()]
    stuck = [st.item_line(i, today) for i in st.open_items(data) if i["made"] < (today - timedelta(days=7)).isoformat()]
    ahead = [*[t for _, t in rb._birthdays(settings, today, today + timedelta(days=7))], *st.countdown_soon(data, today, 7)]
    sections = [st.section("Wins", wins), st.section("Closed", closed), st.section("Decisions made", made),
                st.section("Focus", [f"{focus} minutes"] if focus else []), st.section("Habits", habit),
                st.section("Stuck for over a week", stuck, "alert"), st.section("Next week", ahead),
                st.section("Still open", [f"{len(todo.open_items(settings))} to-dos",
                                          f"{len(routines_life._inbox_lines(settings))} in the inbox"])]
    card = st.panel("Your weekly review", "assistant-review", f"{len(wins) + len(closed)} wins and closed items", sections,
                    buttons=[{"label": "Plan my week", "say": "Plan my week."}, {"label": "Sort inbox", "say": "Show my inbox to sort."}])
    return screen.Shown(f"Weekly review (on screen): {len(wins)} wins, {len(closed)} items closed, {len(stuck)} stuck, "
                        f"{focus} focus minutes. Sum it up kindly in two sentences.", card)


async def run_tool(name: str, args: dict, settings: Settings, http=None):
    action = args.get("action")
    if action == "briefing":
        return await briefing(settings, http)
    if action == "wrapup":
        return await wrapup(settings, http)
    if action == "next_task":
        return next_task(settings, args.get("minutes"), args.get("energy"))
    if action == "time_block":
        return await plan.block_day(settings, http, args)
    if action == "meeting_prep":
        return await plan.prepare(settings, http, args.get("meeting"))
    if action == "weekly_review":
        return weekly_review(settings, http)
    if action == "focus_start":
        return focus_start(settings, args.get("minutes"), args.get("note"), args.get("what"))
    if action == "focus_stop":
        return focus_stop(settings)
    if action == "focus_status":
        return focus_status(settings)
    if action == "energy_set":
        return energy_set(settings, args.get("energy"), args.get("mood"))
    raise ValueError(f"Unknown action {action}.")


def tool_definitions() -> list[dict]:
    text = {"type": "string"}
    return [{
        "name": "assistant_day",
        "description": "The proactive personal assistant for the day. briefing: 'brief me' / 'what's my day like' "
                       "(calendar, weather, what to start with, follow-ups to chase, birthdays, renewals, nudges, "
                       "news count). wrapup: 'wrap up my day' (done, left, tomorrow's first thing). next_task: "
                       "'what should I do next' (minutes free, energy). time_block: 'plan my day' / 'time-block "
                       "today' on a timeline. meeting_prep: 'prepare me for my next meeting'. weekly_review: "
                       "'weekly review'. focus_start / focus_stop / focus_status: focus mode with a do-not-disturb "
                       "note. energy_set: 'I'm tired today' (low, medium, high).",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "minutes": {"type": "integer", "description": "next_task: minutes free. focus_start: length, default 45."},
                "energy": {"type": "string", "enum": list(plan.ENERGY), "description": "next_task or energy_set."},
                "mood": {**text, "description": "energy_set: optional word like 'stressed'."},
                "day": {**text, "description": "time_block: 'today' (default), 'tomorrow' or YYYY-MM-DD."},
                "start": {**text, "description": "time_block: first hour, 'HH:MM'. Default 09:00."},
                "end": {**text, "description": "time_block: last hour, 'HH:MM'. Default 17:30."},
                "meeting": {**text, "description": "meeting_prep: words from the meeting's title. Default the next one."},
                "note": {**text, "description": "focus_start: the do-not-disturb note."},
                "what": {**text, "description": "focus_start: what you're focusing on."},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"assistant_day"}
