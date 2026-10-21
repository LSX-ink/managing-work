"""Kinetic Web Designs content calendar: when each site-series video goes out, plus a weekly before/after post idea.

The series is 15 short videos, each showing a website made for one kind of business, posted one every SPACING days at
6pm starting Tuesday 20 October 2026. The schedule lives in kinetic-content-calendar.json so the user can change it by
voice: "move post 6 to Friday", "post 6 at 7pm", "mark post 2 posted", or change a caption. Moving one post leaves the
others where they are.

"What do I post this week?" lists the week's series posts with their captions and a before/after idea for the week
that ends "Comment SITE for a free mock-up". On a post day, from an hour before it goes out (while a page is open and
it isn't marked posted), Alfred says "Post 6 goes out at 6pm: Night café — caption is in your phone page" once.
Alfred never posts anything himself.
"""

import asyncio
import re
from datetime import date, datetime, time, timedelta

import kinetic_store as st
import screen
from config import Settings

NAMES = {"content_calendar"}
ACTIONS = ["week", "schedule", "move", "posted", "unposted", "caption"]
CALENDAR = "kinetic-content-calendar.json"
START = date(2026, 10, 20)
SPACING = 3
POST_TIME = "18:00"
REMIND_BEFORE = timedelta(hours=1)
LATE = timedelta(hours=3)  # after this, a missed post shows in "what do I post this week" instead
CHECK_SECONDS = 300
FIRST_LOOK = 60  # seconds after start before the first check (a page has time to open; tests never see it)
SERIES = ["Pilates studio", "Spa & massage", "Beauty & skincare", "Wigs", "Outerwear", "Night café", "Roastery",
          "Desserts", "Honey", "Plumber", "Carpenter", "Painter & decorator", "Window cleaner", "Tool hire",
          "Grooming lounge barber"]
CTA = "Comment SITE for a free mock-up"
BEFORE_AFTER = [  # (whose site, what changed): one per week, in turn
    ("a hair salon", "an old page with no booking button, then a clean home page that books appointments"),
    ("a café", "a blurry Facebook-only menu, then a fast menu page with opening hours and directions"),
    ("a plumber", "a slow site that hides the phone number, then a one-tap call button above the fold"),
    ("a boutique", "a cluttered shop page, then big product photos and a simple basket"),
    ("a beauty studio", "a site that breaks on phones, then a page that looks right on every screen"),
    ("a barber", "no website at all, then a home page with prices, photos and walk-in times"),
    ("a bakery", "a dated template, then a warm home page with order-ahead and opening hours"),
    ("a decorator", "a page with no reviews, then before/after photos and five-star reviews up front"),
]
WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
HASHTAGS = "#smallbusiness #webdesign #newwebsite #kineticwebdesigns"


def default_caption(n: int, title: str) -> str:
    return (f"Website series {n}/{len(SERIES)}: {title}. Here's the home page we'd build for a {title.lower()}: "
            f"clear prices, easy booking and it looks great on a phone. Want one for your business? {CTA}. {HASHTAGS}")


def default_posts() -> list[dict]:
    return [{"n": i, "title": t, "date": (START + timedelta(days=SPACING * (i - 1))).isoformat(), "time": POST_TIME,
             "status": "planned", "caption": default_caption(i, t)} for i, t in enumerate(SERIES, 1)]


def load(settings: Settings, create: bool = True) -> list[dict]:
    """The schedule, made from the defaults (and saved, when create) the first time."""
    rows = [r for r in st.load(settings, CALENDAR, []) if isinstance(r, dict) and r.get("n")]
    if not rows:
        rows = default_posts()
        if create:
            st.save(settings, CALENDAR, rows)
    return sorted(rows, key=lambda r: (r["date"], r["time"], r["n"]))


def when(r: dict) -> datetime:
    return datetime.combine(date.fromisoformat(r["date"]), time.fromisoformat(r["time"]))


def clock(t: str) -> str:
    """'18:00' -> '6pm', '18:30' -> '6:30pm'."""
    hh, mm = (int(x) for x in t.split(":"))
    suffix = "am" if hh < 12 else "pm"
    h12 = hh % 12 or 12
    return f"{h12}{suffix}" if mm == 0 else f"{h12}:{mm:02d}{suffix}"


def day_name(d: date) -> str:
    return f"{d.strftime('%A')} {d.day} {d.strftime('%b')}"


def find(rows: list[dict], which) -> dict:
    key = str(which or "").strip().lower().lstrip("#").removeprefix("post").strip()
    if key.isdigit():
        hit = next((r for r in rows if r["n"] == int(key)), None)
    else:
        hit = next((r for r in rows if key and key in r["title"].lower()), None)
    if not hit:
        raise ValueError(f"Which post? Give its number, 1 to {len(SERIES)}, or its name, like Night café.")
    return hit


def parse_day(value, current: date, today: date) -> date:
    """A weekday ('Friday': that day in the post's own week, or the next one if that's already gone), 'today',
    'tomorrow' or YYYY-MM-DD."""
    text = str(value or "").strip().lower()
    if not text:
        raise ValueError("Which day should it move to?")
    text = re.sub(r"^(on|to)\s+", "", text)
    name = re.sub(r"^(this|next)\s+", "", text)
    if name in WEEKDAYS:
        target = current - timedelta(days=current.weekday()) + timedelta(days=WEEKDAYS.index(name))
        if text.startswith("next "):
            target = today - timedelta(days=today.weekday()) + timedelta(days=7 + WEEKDAYS.index(name))
        while target < today:
            target += timedelta(days=7)
        return target
    found = st.parse_date(text, "day")
    if found < today:
        raise ValueError("That day has already gone. Pick today or a day ahead.")
    return found


def parse_time(value) -> str:
    """'7pm', '19:00', '6.30pm' -> 'HH:MM'."""
    text = str(value or "").strip().lower().replace(".", ":").replace(" ", "")
    m = re.fullmatch(r"(\d{1,2})(?::(\d{2}))?(am|pm)?", text)
    if not m:
        raise ValueError("Give the time like 6pm or 18:00.")
    hh, mm = int(m.group(1)), int(m.group(2) or 0)
    if m.group(3) == "pm" and hh < 12:
        hh += 12
    if m.group(3) == "am" and hh == 12:
        hh = 0
    if hh > 23 or mm > 59:
        raise ValueError("That time doesn't look right.")
    return f"{hh:02d}:{mm:02d}"


def week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())


def before_after(monday: date) -> dict:
    """This week's before/after post idea, taking turns through BEFORE_AFTER."""
    i = ((monday - week_start(START)).days // 7) % len(BEFORE_AFTER)
    who, change = BEFORE_AFTER[i]
    return {"day": monday + timedelta(days=6), "idea": f"Before/after for {who}: {change}.",
            "caption": f"Before and after: what a proper website does for {who}. Swipe to see the difference. {CTA}."}


# ---- actions -----------------------------------------------------------------------

def week(settings: Settings, args: dict) -> screen.Shown:
    today = st.today()
    monday = week_start(today) + timedelta(days=7 * max(0, min(int(args.get("weeks_ahead") or 0), 12)))
    sunday = monday + timedelta(days=6)
    rows = load(settings)
    posts = [r for r in rows if monday <= date.fromisoformat(r["date"]) <= sunday]
    missed = [r for r in rows if date.fromisoformat(r["date"]) < monday and r["status"] != "posted"
              and not args.get("weeks_ahead")]
    idea = before_after(monday)
    label = "This week" if monday == week_start(today) else f"Week of {day_name(monday)}"
    if posts:
        said = "; ".join(f"post {r['n']}, {r['title']}, {day_name(date.fromisoformat(r['date']))} at {clock(r['time'])}"
                         + (" (posted)" if r["status"] == "posted" else "") for r in posts)
        text = f"{label}: {said}."
    else:
        text = f"{label} there are no series videos."
    if missed:
        text += " Not marked posted yet from before: " + ", ".join(f"post {r['n']} {r['title']}" for r in missed) + "."
    text += f" Plus a before/after on {day_name(idea['day'])}: {idea['idea']} Captions are on the screen."
    body = [f"{label} ({day_name(monday)} to {day_name(sunday)})", ""]
    for r in missed + posts:
        body += [f"Post {r['n']}: {r['title']} — {day_name(date.fromisoformat(r['date']))}, {clock(r['time'])}"
                 f" [{r['status']}]", r["caption"], ""]
    body += [f"Before/after idea — {day_name(idea['day'])}", idea["idea"], idea["caption"]]
    buttons = [{"label": f"Mark post {r['n']} posted", "say": f"Mark post {r['n']} posted."}
               for r in posts if r["status"] != "posted"][:3]
    return screen.Shown(text, screen.card("text", "What to post", "kinetic-calendar-week", text="\n".join(body),
                                          buttons=buttons or None))


def schedule(settings: Settings, args: dict) -> screen.Shown:
    rows = load(settings)
    left = [r for r in rows if r["status"] != "posted"]
    nxt = left[0] if left else None
    text = (f"{len(rows) - len(left)} of {len(rows)} series posts are marked posted."
            + (f" Next: post {nxt['n']}, {nxt['title']}, {day_name(date.fromisoformat(nxt['date']))} at "
               f"{clock(nxt['time'])}." if nxt else " The series is done."))
    table = [[str(r["n"]), r["title"], day_name(date.fromisoformat(r["date"])), clock(r["time"]), r["status"]]
             for r in sorted(rows, key=lambda r: r["n"])]
    return st.table(text, "Website series schedule", ["#", "Video", "Day", "Time", "Status"], table)


def move(settings: Settings, args: dict) -> str:
    rows = load(settings)
    r = find(rows, args.get("post"))
    today = st.today()
    old = f"{day_name(date.fromisoformat(r['date']))} at {clock(r['time'])}"
    if args.get("day"):
        r["date"] = parse_day(args["day"], date.fromisoformat(r["date"]), today).isoformat()
    if args.get("time"):
        r["time"] = parse_time(args["time"])
    if not (args.get("day") or args.get("time")):
        raise ValueError("Move it to which day or time?")
    r.pop("reminded", None)
    st.save(settings, CALENDAR, rows)
    clash = [x for x in rows if x is not r and x["date"] == r["date"]]
    note = (" Heads up: post " + " and ".join(f"{x['n']} ({x['title']})" for x in clash) + " is on that day too."
            if clash else "")
    return (f"Moved post {r['n']}, {r['title']}, from {old} to {day_name(date.fromisoformat(r['date']))} at "
            f"{clock(r['time'])}. The others stay where they are.{note}")


def posted(settings: Settings, args: dict) -> str:
    rows = load(settings)
    r = find(rows, args.get("post"))
    if r["status"] == "posted":
        return f"Post {r['n']}, {r['title']}, was already marked posted."
    r.update(status="posted", posted_on=st.today().isoformat())
    st.save(settings, CALENDAR, rows)
    left = [x for x in rows if x["status"] != "posted"]
    nxt = f" Next up: post {left[0]['n']}, {left[0]['title']}, {day_name(date.fromisoformat(left[0]['date']))}." \
        if left else " That's the whole series posted."
    return f"Marked post {r['n']}, {r['title']}, as posted.{nxt}"


def unposted(settings: Settings, args: dict) -> str:
    rows = load(settings)
    r = find(rows, args.get("post"))
    r["status"] = "planned"
    r.pop("posted_on", None)
    st.save(settings, CALENDAR, rows)
    return f"Post {r['n']}, {r['title']}, is back to planned."


def caption(settings: Settings, args: dict) -> screen.Shown:
    rows = load(settings)
    r = find(rows, args.get("post"))
    new = st.clean(args.get("caption"), 2200)
    if new:
        r["caption"] = new
        st.save(settings, CALENDAR, rows)
    text = (f"Saved the new caption for post {r['n']}, {r['title']}." if new else
            f"The caption for post {r['n']}, {r['title']}, is on the screen.")
    return st.text_card(text, f"Post {r['n']}: {r['title']}", r["caption"])


# ---- the post-day reminder ------------------------------------------------------------

def reminder_line(settings: Settings, now: datetime | None = None) -> str:
    """From an hour before a post goes out (until LATE after it), once, unless it's marked posted."""
    now = now or datetime.now()
    rows = load(settings, create=False)
    due = [r for r in rows if r["status"] != "posted" and not r.get("reminded") and r["date"] == now.date().isoformat()
           and when(r) - REMIND_BEFORE <= now < when(r) + LATE]
    if not due:
        return ""
    for r in due:
        r["reminded"] = now.date().isoformat()
    st.save(settings, CALENDAR, rows)
    return " ".join(f"Post {r['n']} goes out at {clock(r['time'])}: {r['title']} — caption is in your phone page."
                    for r in due)


async def watch(settings: Settings, announce, someone_there) -> None:
    """Remind on post days, waiting until a page is open."""
    await asyncio.sleep(FIRST_LOOK)
    while True:
        try:
            if someone_there() and (text := await asyncio.to_thread(reminder_line, settings)):
                await announce(text, "content")
        except Exception as exc:  # a bad file must not stop the watcher
            print(f"[jarvis] Content calendar reminder: {exc!r}", flush=True)
        await asyncio.sleep(CHECK_SECONDS)


def tool_definitions() -> list[dict]:
    return [{
        "name": "content_calendar",
        "description": "Kinetic Web Designs content calendar for the 15-video website series (one every 3 days at "
                       "6pm from Tue 20 Oct 2026) plus a weekly before/after post idea. week: \"what do I post this "
                       "week?\" with captions (weeks_ahead 1 for next week). schedule: the whole series and what's "
                       "posted. move: change a post's day and/or time (\"move post 6 to Friday\"); others stay put. "
                       "posted / unposted: mark a post (\"mark post 2 posted\"). caption: show a post's caption, or "
                       "set a new one. Alfred reminds the user an hour before each post. He never posts anything.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "post": {"type": "string", "description": "The post's number (1-15) or name, e.g. 'Night café'."},
                "day": {"type": "string", "description": "move: a weekday like 'Friday', 'tomorrow' or YYYY-MM-DD."},
                "time": {"type": "string", "description": "move: a time like '7pm' or '19:00'."},
                "caption": {"type": "string", "description": "caption: the new caption (leave out to just show it)."},
                "weeks_ahead": {"type": "integer", "description": "week: 0 this week (default), 1 next week."},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


async def run_tool(name: str, args: dict, settings: Settings, http=None):
    handlers = {"week": week, "schedule": schedule, "move": move, "posted": posted, "unposted": unposted,
                "caption": caption}
    return await asyncio.to_thread(st.dispatch, handlers, args.get("action"), settings, args, "content calendar")
