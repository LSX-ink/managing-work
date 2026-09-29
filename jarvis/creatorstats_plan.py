"""Content calendar: plan videos per account and slot, see them on a month-grid pop-up, tap a day to hear what is
planned, mark videos as posted, and keep a posting streak.

Nothing is posted anywhere; this only records what the user plans and says they posted, in creatorstats.json.
"""

import calendar as cal
from datetime import date, timedelta

import creatorstats_store as store
import homestore as hs
import screen
from config import Settings

screen.EXTRA_KINDS.add("creatorstats-calendar")

ACTIONS = ["plan_post", "plan_edit", "plan_remove", "calendar", "day", "upcoming", "free_slots", "mark_posted",
           "streak", "posting_rate"]


def _slot_time(acct: dict, args: dict, data: dict, key: str, day: str, skip: int = 0) -> str:
    """The time asked for, else the chosen slot number, else the first free slot that day."""
    if hs.clean(args.get("time")):
        return store.parse_time(args.get("time"))
    slots = acct["slots"] or store.DEFAULT_SLOTS
    if args.get("slot") is not None:
        n = int(hs.number(args["slot"], "slot", 1, len(slots)))
        return slots[n - 1]
    taken = {store.slot_index(acct, p["planned_time"]) for p in data["posts"]
             if p["account"] == key and p["planned_date"] == day and p["id"] != skip}
    free = [s for i, s in enumerate(slots) if i not in taken]
    return free[0] if free else slots[-1]


def _clash(data: dict, key: str, day: str, time: str, skip: int = 0):
    return next((p for p in data["posts"] if p["account"] == key and p["planned_date"] == day
                 and p["planned_time"] == time and p["id"] != skip), None)


def plan_post(settings: Settings, args: dict, today: date) -> str:
    data = store.load(settings)
    key, acct = store.account(data, args.get("account"))
    title = hs.need(args.get("title"), "video title", 100)
    day = hs.parse_day(args.get("date"), today).isoformat()
    time = _slot_time(acct, args, data, key, day)
    clash = _clash(data, key, day, time)
    if clash:
        raise ValueError(f"{key} already has '{clash['title']}' at {time} that day. Pick another slot or time.")
    entry = store.new_post(data, key, title, planned_date=day, planned_time=time, theme=hs.clean(args.get("theme"), 40),
                           hook=hs.clean(args.get("hook"), 160),
                           length=store.whole(args.get("length_seconds") or 0, "length", 3600))
    store.save(settings, data)
    return f"Planned #{entry['id']} '{title}' for {key} on {hs.spoken(date.fromisoformat(day))} at {time}."


def plan_edit(settings: Settings, args: dict, today: date) -> str:
    data = store.load(settings)
    p = store.post(data, args.get("post"), args.get("account"))
    acct = data["accounts"][p["account"]]
    changed = []
    if hs.clean(args.get("title")):
        p["title"] = hs.clean(args.get("title"), 100)
        changed.append("title")
    for field, arg in (("theme", "theme"), ("hook", "hook")):
        if hs.clean(args.get(arg)):
            p[field] = hs.clean(args[arg], 160)
            changed.append(field)
    if args.get("length_seconds") is not None:
        p["length"] = store.whole(args["length_seconds"], "length", 3600)
        changed.append("length")
    if hs.clean(args.get("date")) or hs.clean(args.get("time")) or args.get("slot") is not None:
        day = hs.parse_day(args.get("date"), today).isoformat() if hs.clean(args.get("date")) else p["planned_date"]
        if not day:
            raise ValueError("Which day should it be planned for?")
        time = _slot_time(acct, args, data, p["account"], day, p["id"]) if (
            hs.clean(args.get("time")) or args.get("slot") is not None) else (p["planned_time"] or _slot_time(acct, args, data, p["account"], day, p["id"]))
        clash = _clash(data, p["account"], day, time, p["id"])
        if clash:
            raise ValueError(f"'{clash['title']}' is already planned for {time} that day.")
        p["planned_date"], p["planned_time"] = day, time
        changed.append("day and time")
    if not changed:
        raise ValueError("What should I change: the day, time, title, theme, hook or length?")
    store.save(settings, data)
    return f"Updated #{p['id']} '{p['title']}': {', '.join(changed)}."


def plan_remove(settings: Settings, args: dict, today: date) -> str:
    data = store.load(settings)
    p = store.post(data, args.get("post"), args.get("account"))
    if not args.get("confirmed"):
        return f"Ask the user to confirm deleting #{p['id']} '{p['title']}' and its numbers."
    data["posts"].remove(p)
    store.save(settings, data)
    return f"Removed #{p['id']} '{p['title']}'."


def _items(data: dict, start: date, end: date, names: list[str]) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for p in data["posts"]:
        day = p["posted_date"] or p["planned_date"]
        if p["account"] in names and day and start.isoformat() <= day <= end.isoformat():
            out.setdefault(day, []).append(p)
    for day in out:
        out[day].sort(key=lambda p: (p["posted_time"] or p["planned_time"], p["id"]))
    return out


def calendar(settings: Settings, args: dict, today: date) -> screen.Shown:
    data = store.load(settings)
    names = store.accounts_for(data, args.get("account"))
    if not names:
        raise ValueError("You haven't added an account yet.")
    first = store.month_start(args.get("month"), today)
    last = first.replace(day=cal.monthrange(first.year, first.month)[1])
    found = _items(data, first, last, names)
    days = {str(date.fromisoformat(d).day): [{"a": p["account"], "t": p["posted_time"] or p["planned_time"],
                                              "title": p["title"], "done": store.is_posted(p)} for p in ps]
            for d, ps in found.items()}
    prev = (first - timedelta(days=1)).replace(day=1)
    nxt = (last + timedelta(days=1))
    who = f" for {names[0]}" if len(names) == 1 else ""
    card = screen.card("creatorstats-calendar", f"Content calendar: {first:%B %Y}", f"creatorstats-calendar{who}", buttons=[
        store.button(f"< {prev:%b}", f"Show my content calendar for {prev:%Y-%m}{who}."),
        store.button(f"{nxt:%b} >", f"Show my content calendar for {nxt:%Y-%m}{who}."),
        store.button("Free slots", "Which posting slots are free this week?")],
        data={"year": first.year, "month": first.month, "name": f"{first:%B %Y}", "first": first.weekday(),
              "length": last.day, "today": today.day if today.year == first.year and today.month == first.month else 0,
              "days": days, "accounts": names, "say_prefix": "What's planned on ", "iso": first.isoformat()})
    total = sum(len(v) for v in found.values())
    return screen.Shown(f"{total} video{'s' if total != 1 else ''} on the calendar in {first:%B}. Tap a day for the details.", card)


def day(settings: Settings, args: dict, today: date) -> screen.Shown:
    data = store.load(settings)
    names = store.accounts_for(data, args.get("account"))
    when = hs.parse_day(args.get("date"), today)
    found = _items(data, when, when, names).get(when.isoformat(), [])
    rows = [[p["posted_time"] or p["planned_time"], p["account"], f"#{p['id']} {p['title']}",
             "Posted" if store.is_posted(p) else "Planned"] for p in found]
    card = screen.card("table", f"Planned {when:%a %d %b}", f"creatorstats-day-{when.isoformat()}",
                       columns=["Time", "Account", "Video", "Status"], rows=rows,
                       buttons=[store.button("Plan a video", f"Plan a video for {when.isoformat()}.")])
    if not found:
        return screen.Shown(f"Nothing planned for {hs.spoken(when)}.", card)
    first = found[0]
    more = f" and {len(found) - 1} more" if len(found) > 1 else ""
    return screen.Shown(f"{hs.spoken(when)}: {first['account']} at {first['posted_time'] or first['planned_time']}, "
                        f"'{first['title']}'{more}.", card)


def upcoming(settings: Settings, args: dict, today: date) -> screen.Shown:
    data = store.load(settings)
    names = store.accounts_for(data, args.get("account"))
    days = int(hs.number(args.get("days") or 7, "number of days", 1, 60))
    found = _items(data, today, today + timedelta(days=days - 1), names)
    items = [{"label": f"{date.fromisoformat(d):%a %d %b} {p['planned_time']} {p['account']}: {p['title']}",
              "say": f"Mark video #{p['id']} as posted."}
             for d, ps in sorted(found.items()) for p in ps if not store.is_posted(p)]
    card = screen.card("list", f"Coming up: next {days} days", "creatorstats-upcoming", items=items,
                       buttons=[store.button("Calendar", "Show my content calendar.")])
    return screen.Shown(f"{len(items)} videos planned in the next {days} days." if items else f"Nothing planned in the next {days} days.", card)


def free_slots(settings: Settings, args: dict, today: date) -> screen.Shown:
    data = store.load(settings)
    names = store.accounts_for(data, args.get("account"))
    days = int(hs.number(args.get("days") or 7, "number of days", 1, 30))
    rows, total = [], 0
    for key in names:
        acct = data["accounts"][key]
        for i in range(days):
            d = today + timedelta(days=i)
            taken = {store.slot_index(acct, p["planned_time"] or p["posted_time"]) for p in data["posts"]
                     if p["account"] == key and (p["planned_date"] == d.isoformat() or p["posted_date"] == d.isoformat())}
            free = [s for n, s in enumerate(acct["slots"]) if n not in taken]
            total += len(free)
            if free:
                rows.append([f"{d:%a %d %b}", key, ", ".join(free)])
    card = screen.card("table", "Free posting slots", "creatorstats-free", columns=["Day", "Account", "Free"], rows=rows,
                       buttons=[store.button("Calendar", "Show my content calendar.")])
    return screen.Shown(f"{total} free slots in the next {days} days.", card)


def mark_posted(settings: Settings, args: dict, today: date) -> str:
    data = store.load(settings)
    when = hs.parse_day(args.get("date"), today).isoformat()
    if hs.clean(args.get("post")):
        p = store.post(data, args.get("post"), args.get("account"))
    else:
        key = store.account(data, args.get("account"))[0]
        p = store.new_post(data, key, hs.need(args.get("title"), "video title", 100))
    p["posted_date"] = when
    p["posted_time"] = store.parse_time(args["time"]) if hs.clean(args.get("time")) else (p["planned_time"] or "")
    for field, arg in (("theme", "theme"), ("hook", "hook")):
        if hs.clean(args.get(arg)):
            p[field] = hs.clean(args[arg], 160)
    if args.get("length_seconds") is not None:
        p["length"] = store.whole(args["length_seconds"], "length", 3600)
    store.save(settings, data)
    streak = _streaks(data, p["account"], today)[0]
    return f"Marked #{p['id']} '{p['title']}' as posted. {streak}-day streak on {p['account']}."


def _streaks(data: dict, name, today: date) -> tuple[int, int]:
    """(current, longest) run of days with a posted video, for one account or all of them."""
    days = {date.fromisoformat(p["posted_date"]) for p in data["posts"]
            if p["posted_date"] and (not hs.clean(name) or p["account"] == name)}
    current, cursor = 0, today if today in days else today - timedelta(days=1)
    while cursor in days:
        current += 1
        cursor -= timedelta(days=1)
    longest = run = 0
    prev = None
    for d in sorted(days):
        run = run + 1 if prev and (d - prev).days == 1 else 1
        longest, prev = max(longest, run), d
    return current, longest


def streak(settings: Settings, args: dict, today: date) -> screen.Shown:
    data = store.load(settings)
    names = store.accounts_for(data, args.get("account"))
    rows = []
    for key in names:
        cur, best = _streaks(data, key, today)
        rows.append([key, f"{cur} days", f"{best} days"])
    if len(names) > 1:
        cur, best = _streaks(data, "", today)
        rows.append(["Any account", f"{cur} days", f"{best} days"])
    cur, best = _streaks(data, names[0] if len(names) == 1 else "", today)
    tail = " Post today to keep it going." if cur and not any(
        p["posted_date"] == today.isoformat() for p in data["posts"] if p["account"] in names) else ""
    card = screen.card("table", "Posting streaks", "creatorstats-streaks", columns=["Account", "Current", "Longest"], rows=rows,
                       buttons=[store.button("Mark posted", "Mark a video as posted today.")])
    return screen.Shown(f"Current streak {cur} days, longest {best}.{tail}", card)


def posting_rate(settings: Settings, args: dict, today: date) -> screen.Shown:
    data = store.load(settings)
    names = store.accounts_for(data, args.get("account"))
    weeks = int(hs.number(args.get("weeks") or 8, "number of weeks", 2, 26))
    start = hs.week_start(today) - timedelta(weeks=weeks - 1)
    counts = [0] * weeks
    for p in data["posts"]:
        if p["account"] in names and p["posted_date"]:
            n = (hs.week_start(date.fromisoformat(p["posted_date"])) - start).days // 7
            if 0 <= n < weeks:
                counts[n] += 1
    labels = [f"{(start + timedelta(weeks=i)):%d %b}" for i in range(weeks)]
    card = screen.card("chart", "Videos posted per week", "creatorstats-posting-rate",
                       chart={"type": "bar", "labels": labels, "values": counts, "unit": ""})
    return screen.Shown(f"{sum(counts)} videos in the last {weeks} weeks, {counts[-1]} this week.", card)


def tool_definitions() -> list[dict]:
    return [{
        "name": "creator_calendar",
        "description": "Content calendar for TikTok-style accounts: plan what to post when, never posts anything. "
                       "action: plan_post = plan a video (account, title, date, slot 1-3 or time, theme, hook, "
                       "length_seconds); plan_edit = move or change a planned video; plan_remove = delete a video "
                       "(confirmed true only after the user agrees); calendar = month grid pop-up; day = what is "
                       "planned on a date; upcoming = next days list; free_slots = empty posting slots; "
                       "mark_posted = the user says a video went out (or log a new one by title); streak = days "
                       "posted in a row; posting_rate = videos per week bar chart.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "account": {"type": "string", "description": "May be left out with one account, or to cover all."},
                "post": {"type": "string", "description": "A video's number (#3) or part of its title."},
                "title": {"type": "string"},
                "date": {"type": "string", "description": "YYYY-MM-DD, today, tomorrow or a weekday."},
                "time": {"type": "string", "description": "e.g. 19:30 or 7:30pm."},
                "slot": {"type": "integer", "description": "The account's posting slot, 1 to 3."},
                "theme": {"type": "string"},
                "hook": {"type": "string", "description": "The opening line or idea."},
                "length_seconds": {"type": "integer"},
                "month": {"type": "string", "description": "calendar: YYYY-MM, this month, next month."},
                "days": {"type": "integer"},
                "weeks": {"type": "integer"},
                "confirmed": {"type": "boolean", "description": "Set true only after the user confirms a deletion."},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"creator_calendar"}


def run_tool(name: str, args: dict, settings: Settings, http=None, today: date | None = None):
    today = today or date.today()
    action = args.get("action")
    actions = {"plan_post": plan_post, "plan_edit": plan_edit, "plan_remove": plan_remove, "calendar": calendar,
               "day": day, "upcoming": upcoming, "free_slots": free_slots, "mark_posted": mark_posted,
               "streak": streak, "posting_rate": posting_rate}
    if action not in actions:
        raise ValueError(f"Unknown creator calendar action: {action}")
    return actions[action](settings, args, today)
