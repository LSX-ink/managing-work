"""Writing habits: a daily word goal, words written each day, the writing streak, timed sprints and a blog planner.

Words can be logged as a number, or counted from the stored chapters: Alfred remembers the total at the last count
and logs whatever has been added since.
"""

from datetime import datetime, timedelta

import homestore as hs
import screen
import writing_store as ws
from config import Settings

ACTIONS = ["set_daily_goal", "log_words", "progress", "sprint_start", "sprint_finish", "blog_add", "blog_update",
           "blog_list", "blog_delete"]
STATUSES = ["idea", "drafting", "published"]


def add_words(log: dict, n: int) -> int:
    day = hs.today().isoformat()
    log["days"][day] = max(0, ws.day_words(log, hs.today()) + n)
    if len(log["days"]) > 3000:
        for old in sorted(log["days"])[:-3000]:
            del log["days"][old]
    return log["days"][day]


def set_goal(settings: Settings, args: dict) -> screen.Shown:
    log = ws.load_log(settings)
    log["daily_goal"] = int(hs.number(args.get("words"), "daily word goal", 1, 100_000))
    ws.save_log(settings, log)
    return progress(settings, f"Your daily goal is {log['daily_goal']:,} words.")


def log_words(settings: Settings, args: dict) -> screen.Shown | str:
    log = ws.load_log(settings)
    total = ws.all_words(settings)
    if args.get("words") in (None, ""):
        before = log.get("counted")
        log["counted"] = total
        if not isinstance(before, int):
            ws.save_log(settings, log)
            return (f"Your projects hold {total:,} words. I've noted that; next time I'll log what's been added since. "
                    "Or tell me how many words you wrote.")
        n = total - before
        if n <= 0:
            ws.save_log(settings, log)
            return "No new words in your projects since the last count."
    else:
        n = int(hs.number(args["words"], "number of words", -100_000, 100_000))
        log["counted"] = total
    today = add_words(log, n)
    ws.save_log(settings, log)
    return progress(settings, f"Logged {ws.s(n, 'word')}; {today:,} today.")


def progress(settings: Settings, said: str = "") -> screen.Shown:
    log = ws.load_log(settings)
    today = hs.today()
    goal, done = int(log.get("daily_goal") or 0), ws.day_words(log, today)
    streak = ws.streak(log, today)
    days = [today - timedelta(days=n) for n in range(13, -1, -1)]
    sections = [{"type": "stats", "items": [{"label": "Today", "value": f"{done:,}"},
                                            {"label": "Streak", "value": ws.s(streak, "day")},
                                            {"label": "Last 7 days", "value": f"{sum(ws.day_words(log, d) for d in days[-7:]):,}"}]}]
    if goal:
        sections.append({"type": "meters", "rows": [{"label": "Daily goal", "value": done, "max": goal,
                                                     "note": f"{done:,} of {goal:,}"}]})
    sections.append({"type": "chart", "title": "Last 14 days", "chart": {
        "type": "bar", "labels": [d.strftime("%a %d") for d in days], "values": [ws.day_words(log, d) for d in days],
        "unit": "words"}})
    if not said:
        left = f", {goal - done:,} to go" if goal and done < goal else (", goal met" if goal else "")
        said = f"{ws.s(done, 'word')} today{left}. Streak: {ws.s(streak, 'day')}."
    return screen.Shown(said, ws.studio("Daily words", "writing-daily", sections,
                                        [{"label": "Count my words", "say": "Log the words I've written today from my projects."},
                                         {"label": "Start a sprint", "say": "Start a 20 minute writing sprint."}]))


def sprint_start(settings: Settings, args: dict) -> screen.Shown:
    minutes = int(hs.number(args.get("minutes") or 20, "number of minutes", 1, 180))
    log = ws.load_log(settings)
    start = hs.now()
    ends = start + timedelta(minutes=minutes)
    before = args.get("words")
    log["sprint"] = {"started": start.isoformat(timespec="seconds"), "minutes": minutes,
                     "before": int(before) if before not in (None, "") else ws.all_words(settings)}
    ws.save_log(settings, log)
    card = screen.card("timer", f"Writing sprint: {minutes} min", "writing-sprint", ends_at=ends.timestamp() * 1000,
                       buttons=[{"label": "Finish sprint", "say": "Finish my writing sprint."}])
    return screen.Shown(f"Sprint started: {minutes} minutes, ends at {ends:%H:%M}. Go!", card)


def sprint_finish(settings: Settings, args: dict) -> screen.Shown:
    log = ws.load_log(settings)
    sprint = log.get("sprint")
    if not isinstance(sprint, dict):
        raise ValueError("There's no writing sprint running. Start one first.")
    if args.get("words_after") not in (None, ""):
        n = int(hs.number(args["words_after"], "word count", 0, 10_000_000)) - int(sprint.get("before") or 0)
    elif args.get("words") not in (None, ""):
        n = int(hs.number(args["words"], "number of words", 0, 100_000))
    else:
        n = ws.all_words(settings) - int(sprint.get("before") or 0)
    n = max(0, n)
    mins = max(1, round((hs.now() - datetime.fromisoformat(sprint["started"])).total_seconds() / 60))
    today = add_words(log, n)
    log["counted"] = ws.all_words(settings)
    log.pop("sprint")
    ws.save_log(settings, log)
    pace = round(n / mins * 60)
    sections = [{"type": "stats", "items": [{"label": "Words", "value": f"{n:,}"},
                                            {"label": "Minutes", "value": str(mins)},
                                            {"label": "Words an hour", "value": f"{pace:,}"},
                                            {"label": "Today", "value": f"{today:,}"}]}]
    return screen.Shown(f"Sprint done: {ws.s(n, 'word')} in {mins} minutes, {today:,} today.",
                        ws.studio("Sprint result", "writing-sprint", sections,
                                  [{"label": "Another sprint", "say": f"Start a {sprint.get('minutes', 20)} minute writing sprint."}]))


# ---- Blog planner --------------------------------------------------------------------------------

def blog_key(log: dict, title) -> str:
    key = hs.find(log["blog"], hs.need(title, "blog post"))
    if key is None:
        raise ValueError(f"There's no blog post called {hs.clean(title)} in the planner.")
    return key


def blog_fields(post: dict, args: dict) -> None:
    if args.get("status") in STATUSES:
        post["status"] = args["status"]
    if hs.clean(args.get("publish_date")):
        post["date"] = hs.parse_day(args["publish_date"]).isoformat()
    if hs.clean(args.get("notes"), 300):
        post["notes"] = hs.clean(args["notes"], 300)


def blog_add(settings: Settings, args: dict) -> screen.Shown:
    log = ws.load_log(settings)
    title = hs.need(args.get("title"), "blog post title", 120)
    if any(k.lower() == title.lower() for k in log["blog"]):
        raise ValueError(f"{title} is already in the planner.")
    if len(log["blog"]) >= ws.MAX_ENTRIES:
        raise ValueError("The blog planner is full; remove a post first.")
    post = {"status": "idea", "date": "", "notes": ""}
    blog_fields(post, args)
    log["blog"][title] = post
    ws.save_log(settings, log)
    return blog_list(settings, f"Added {title} to the blog planner as {post['status']}.")


def blog_update(settings: Settings, args: dict) -> screen.Shown:
    log = ws.load_log(settings)
    key = blog_key(log, args.get("title"))
    blog_fields(log["blog"][key], args)
    ws.save_log(settings, log)
    post = log["blog"][key]
    when = f", {post['date']}" if post.get("date") else ""
    return blog_list(settings, f"{key} is now {post['status']}{when}.")


def blog_delete(settings: Settings, args: dict) -> screen.Shown | str:
    log = ws.load_log(settings)
    key = blog_key(log, args.get("title"))
    if args.get("confirmed") is not True:
        return f"Ask the user to confirm removing {key} from the blog planner, then call again with confirmed true."
    del log["blog"][key]
    ws.save_log(settings, log)
    return blog_list(settings, f"Removed {key} from the blog planner.")


def blog_list(settings: Settings, said: str = "") -> screen.Shown | str:
    log = ws.load_log(settings)
    posts = sorted(log["blog"].items(), key=lambda kv: (STATUSES.index(kv[1].get("status", "idea"))
                                                        if kv[1].get("status") in STATUSES else 0,
                                                        kv[1].get("date") or "9999", kv[0].lower()))
    if not posts:
        return said or "The blog planner is empty."
    sections = []
    for status in STATUSES:
        items = [{"label": t, "note": " · ".join(x for x in (p.get("date"), p.get("notes")) if x),
                  "say": f"Start drafting my blog post {t}." if status == "idea" else
                  (f"Mark my blog post {t} as published." if status == "drafting" else "")}
                 for t, p in posts if p.get("status", "idea") == status]
        if items:
            sections.append({"type": "list", "title": f"{status.title()} ({len(items)})", "items": items})
    today = hs.today().isoformat()
    upcoming = [(p["date"], t) for t, p in posts if p.get("status") != "published" and (p.get("date") or "") >= today]
    nxt = f" Next up: {min(upcoming)[1]} on {min(upcoming)[0]}." if upcoming else ""
    counts = ", ".join(f"{sum(1 for _, p in posts if p.get('status', 'idea') == st)} {st}" for st in STATUSES)
    return screen.Shown(said or f"Blog planner: {counts}.{nxt}", ws.studio("Blog planner", "writing-blog", sections))


def tool_definitions() -> list[dict]:
    return [{
        "name": "writing_goal",
        "description": "Writing habits: set_daily_goal (words a day); log_words (words written today, or leave words "
                       "out to count what's new in the stored chapters); progress (today's progress bar, writing "
                       "streak, last 14 days); sprint_start (a timed writing sprint of N minutes with a timer) and "
                       "sprint_finish (words written, or words_after; else counted from the chapters); blog post planner: blog_add, blog_update (status idea/"
                       "drafting/published, publish date), blog_list, blog_delete (confirmed true only after the "
                       "user says yes).",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "words": {"type": "integer", "description": "Daily goal, words written, or sprint_start: the "
                                                            "document's word count before (else stored counts)."},
                "words_after": {"type": "integer", "description": "sprint_finish: the word count now."},
                "minutes": {"type": "integer"},
                "title": {"type": "string", "description": "Blog post title."},
                "status": {"type": "string", "enum": STATUSES},
                "publish_date": {"type": "string", "description": "YYYY-MM-DD."},
                "notes": {"type": "string"},
                "confirmed": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"writing_goal"}


def run_tool(name: str, args: dict, settings: Settings, http=None):
    action = args.get("action")
    if action == "progress":
        return progress(settings)
    if action == "blog_list":
        return blog_list(settings)
    handler = {"set_daily_goal": set_goal, "log_words": log_words, "sprint_start": sprint_start,
               "sprint_finish": sprint_finish, "blog_add": blog_add, "blog_update": blog_update,
               "blog_delete": blog_delete}.get(action)
    if not handler:
        raise ValueError(f"Unknown action {action}.")
    return handler(settings, args)
