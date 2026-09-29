"""Creator reports: growth charts, weekly and monthly reports, averages, comparisons between accounts and videos,
what works best (day, time, theme, length), follows per 1,000 views, a rough earnings calculator and a CSV export.

All numbers are read from creatorstats.json (typed in by the user). Nothing is fetched from a platform.
"""

import csv
from datetime import date, timedelta
from statistics import mean, median

import creatorstats_store as store
import homestore as hs
import memory
import screen
from config import Settings

ACTIONS = ["dashboard", "growth_chart", "views_trend", "weekly_report", "monthly_report", "averages",
           "compare_accounts", "compare_posts", "best_day", "best_hour", "themes", "length_check", "conversion",
           "consistency", "earnings_estimate", "export_csv"]
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def _posted(data: dict, names: list[str], start: date | None = None, end: date | None = None) -> list[dict]:
    out = []
    for p in data["posts"]:
        if p["account"] not in names or not p["posted_date"]:
            continue
        d = date.fromisoformat(p["posted_date"])
        if (start is None or d >= start) and (end is None or d <= end):
            out.append(p)
    return out


def _totals(posts: list[dict]) -> dict:
    with_stats = [p for p in posts if store.latest(p)]
    sums = {k: sum(store.latest(p).get(k) or 0 for p in with_stats) for k in store.METRICS if k != "watch"}
    watch = [store.latest(p)["watch"] for p in with_stats if store.latest(p).get("watch") is not None]
    sums["videos"], sums["with_stats"] = len(posts), len(with_stats)
    sums["watch"] = round(mean(watch), 1) if watch else None
    sums["rates"] = store.rates(sums)
    return sums


def _table(title: str, cid: str, columns: list, rows: list, said: str, buttons=None, text: str = "") -> screen.Shown:
    fields = {"columns": columns, "rows": rows, "buttons": buttons}
    if text:
        fields["text"] = text
    return screen.Shown(said, screen.card("table", title, cid, **fields))


def _no_data() -> ValueError:
    return ValueError("No videos with numbers yet. Log some stats first.")


def dashboard(settings: Settings, args: dict, today: date) -> screen.Shown:
    data = store.load(settings)
    names = store.accounts_for(data, args.get("account"))
    if not names:
        raise ValueError("You haven't added an account yet.")
    rows = []
    for key in names:
        acct = data["accounts"][key]
        tot = _totals(_posted(data, [key], today - timedelta(days=29), today))
        growth = store.daily_growth(acct, today)
        now = store.current_followers(acct)
        rows.append([key, store.count(now) if now is not None else "-", f"{growth * 7:+.0f}/wk" if growth is not None else "-",
                     str(tot["videos"]), store.count(tot["views"]), f"{tot['rates']['engagement']}%"])
    return _table("Creator dashboard", "creatorstats-dashboard",
                  ["Account", "Followers", "Growth", "Posts 30d", "Views 30d", "Eng."], rows,
                  f"{len(rows)} account{'s' if len(rows) != 1 else ''} on the dashboard, last 30 days.",
                  [store.button("Weekly report", "Give me my weekly creator report."),
                   store.button("Streak", "What's my posting streak?")])


def growth_chart(settings: Settings, args: dict, today: date) -> screen.Shown:
    data = store.load(settings)
    key, acct = store.account(data, args.get("account"))
    days = int(hs.number(args.get("days") or 30, "number of days", 7, 365))
    log = [e for e in sorted(acct["followers"], key=lambda e: e["date"])
           if (today - date.fromisoformat(e["date"])).days <= days]
    if len(log) < 2:
        raise ValueError("I need at least two follower counts to draw growth. Tell me your count on different days.")
    card = screen.card("chart", f"Followers: {key}", f"creatorstats-growth-{key}",
                       chart={"type": "line", "labels": [e["date"][5:] for e in log], "values": [e["count"] for e in log], "unit": ""})
    gain = log[-1]["count"] - log[0]["count"]
    return screen.Shown(f"{key} went from {store.count(log[0]['count'])} to {store.count(log[-1]['count'])} followers, {gain:+d} in {days} days.", card)


def views_trend(settings: Settings, args: dict, today: date) -> screen.Shown:
    data = store.load(settings)
    names = store.accounts_for(data, args.get("account"))
    found = sorted([p for p in _posted(data, names) if store.latest(p)], key=lambda p: (p["posted_date"], p["id"]))
    limit = int(hs.number(args.get("limit") or 12, "number of videos", 3, 40))
    found = found[-limit:]
    if len(found) < 3:
        raise ValueError("I need numbers for at least three videos to show a trend.")
    values = [store.views_of(p) for p in found]
    card = screen.card("chart", "Views per video", "creatorstats-views-trend",
                       chart={"type": "bar", "labels": [f"#{p['id']}" for p in found], "values": values, "unit": ""})
    half = len(values) // 2
    older, newer = mean(values[:half]), mean(values[half:])
    word = "up" if newer > older else "down" if newer < older else "flat"
    return screen.Shown(f"Your newer videos average {store.count(newer)} views, {word} from {store.count(older)}.", card)


def _report(settings: Settings, args: dict, today: date, start: date, end: date, label: str) -> screen.Shown:
    data = store.load(settings)
    names = store.accounts_for(data, args.get("account"))
    span = end - start
    prev_start, prev_end = start - span - timedelta(days=1), start - timedelta(days=1)
    now_posts, before = _posted(data, names, start, end), _posted(data, names, prev_start, prev_end)
    cur, old = _totals(now_posts), _totals(before)

    def change(key):
        a, b = cur[key], old[key]
        return f"{(a - b) / b * 100:+.0f}%" if b else "-"

    rows = [["Videos posted", str(cur["videos"]), str(old["videos"]), change("videos")],
            ["Views", store.count(cur["views"]), store.count(old["views"]), change("views")],
            ["Likes", store.count(cur["likes"]), store.count(old["likes"]), change("likes")],
            ["Shares", store.count(cur["shares"]), store.count(old["shares"]), change("shares")],
            ["Saves", store.count(cur["saves"]), store.count(old["saves"]), change("saves")],
            ["Follows gained", store.count(cur["follows"]), store.count(old["follows"]), change("follows")],
            ["Engagement", f"{cur['rates']['engagement']}%", f"{old['rates']['engagement']}%", "-"]]
    gained = ""
    if len(names) == 1:
        log = [e for e in data["accounts"][names[0]]["followers"] if start.isoformat() <= e["date"] <= end.isoformat()]
        if len(log) >= 2:
            gained = f" Followers {log[-1]['count'] - log[0]['count']:+d}."
    ranked = sorted([p for p in now_posts if store.latest(p)], key=store.views_of, reverse=True)
    top = f" Top video: '{ranked[0]['title']}' with {store.count(store.views_of(ranked[0]))} views." if ranked else ""
    return _table(f"{label} report", f"creatorstats-report-{label.lower().replace(' ', '-')}",
                  ["", "This period", "Before", "Change"], rows,
                  f"{label.lower()}: {cur['videos']} videos, {store.count(cur['views'])} views.{gained}{top}",
                  [store.button("Best videos", "Which are my best videos?"), store.button("Averages", "What are my averages?")],
                  f"{start:%d %b} to {end:%d %b}, against the {span.days + 1} days before.")


def weekly_report(settings: Settings, args: dict, today: date) -> screen.Shown:
    start = hs.week_start(hs.parse_day(args.get("date"), today))
    return _report(settings, args, today, start, start + timedelta(days=6), "Weekly")


def monthly_report(settings: Settings, args: dict, today: date) -> screen.Shown:
    start = store.month_start(args.get("month"), today)
    end = (start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    return _report(settings, args, today, start, end, "Monthly")


def averages(settings: Settings, args: dict, today: date) -> screen.Shown:
    data = store.load(settings)
    names = store.accounts_for(data, args.get("account"))
    found = [p for p in _posted(data, names) if store.latest(p)]
    if not found:
        raise _no_data()
    views = [store.views_of(p) for p in found]
    eng = [store.rates(store.latest(p))["engagement"] for p in found]
    tot = _totals(found)
    rows = [["Videos with numbers", str(len(found))], ["Average views", store.count(mean(views))],
            ["Median views", store.count(median(views))], ["Best views", store.count(max(views))],
            ["Average engagement", f"{mean(eng):.2f}%"], ["Follows per video", f"{tot['follows'] / len(found):.1f}"]]
    if tot["watch"] is not None:
        rows.append(["Average watched", f"{tot['watch']}%"])
    return _table("My averages", "creatorstats-averages", ["Measure", "Value"], rows,
                  f"Across {len(found)} videos: {store.count(mean(views))} views on average, {store.count(median(views))} typical.",
                  text="The median is the typical video; the average is pulled up by one big hit.")


def compare_accounts(settings: Settings, args: dict, today: date) -> screen.Shown:
    data = store.load(settings)
    names = list(data["accounts"])
    if len(names) < 2:
        raise ValueError("You need at least two accounts to compare.")
    rows = []
    for key in names:
        posts = [p for p in _posted(data, [key]) if store.latest(p)]
        tot = _totals(posts)
        growth = store.daily_growth(data["accounts"][key], today)
        rows.append([key, str(len(posts)), store.count(tot["views"] / len(posts)) if posts else "-",
                     f"{tot['rates']['engagement']}%" if posts else "-", f"{growth * 7:+.0f}" if growth is not None else "-"])
    best = max(rows, key=lambda r: float(r[3].rstrip("%")) if r[3] != "-" else -1)
    return _table("Accounts side by side", "creatorstats-compare-accounts",
                  ["Account", "Videos", "Avg views", "Eng.", "Followers/wk"], rows,
                  f"Best engagement: {best[0]} at {best[3]}.")


def compare_posts(settings: Settings, args: dict, today: date) -> screen.Shown:
    data = store.load(settings)
    refs = [r for r in (args.get("post"), args.get("post_b")) if hs.clean(r)]
    if len(refs) != 2:
        raise ValueError("Give two videos to compare: post and post_b, by number or title.")
    a, b = store.post(data, refs[0]), store.post(data, refs[1])
    ma, mb = store.latest(a), store.latest(b)
    ra, rb = store.rates(ma), store.rates(mb)
    rows = [["Account", a["account"], b["account"]],
            ["Views", store.count(ma.get("views")), store.count(mb.get("views"))],
            ["Engagement", f"{ra['engagement']}%", f"{rb['engagement']}%"],
            ["Shares", f"{ra['share']}%", f"{rb['share']}%"],
            ["Saves", f"{ra['save']}%", f"{rb['save']}%"],
            ["Follows", store.count(ma.get("follows")), store.count(mb.get("follows"))],
            ["Length (s)", str(a["length"] or "-"), str(b["length"] or "-")]]
    win = a if store.views_of(a) >= store.views_of(b) else b
    return _table(f"#{a['id']} against #{b['id']}", f"creatorstats-compare-{a['id']}-{b['id']}",
                  ["", f"#{a['id']} {a['title']}", f"#{b['id']} {b['title']}"], rows,
                  f"'{win['title']}' got more views: {store.count(store.views_of(win))}.")


def _by(posts: list[dict], key) -> dict:
    groups: dict = {}
    for p in posts:
        if store.latest(p):
            groups.setdefault(key(p), []).append(store.views_of(p))
    return groups


def best_day(settings: Settings, args: dict, today: date) -> screen.Shown:
    data = store.load(settings)
    groups = _by(_posted(data, store.accounts_for(data, args.get("account"))),
                 lambda p: date.fromisoformat(p["posted_date"]).weekday())
    if not groups:
        raise _no_data()
    avg = {d: mean(v) for d, v in groups.items()}
    card = screen.card("chart", "Average views by day posted", "creatorstats-best-day",
                       chart={"type": "bar", "labels": [d[:3] for d in DAYS], "values": [round(avg.get(i, 0)) for i in range(7)], "unit": ""})
    top = max(avg, key=avg.get)
    return screen.Shown(f"{DAYS[top]} is your best day so far, {store.count(avg[top])} views on average across {len(groups[top])} videos. Small samples can mislead.", card)


def best_hour(settings: Settings, args: dict, today: date) -> screen.Shown:
    data = store.load(settings)
    posts = [p for p in _posted(data, store.accounts_for(data, args.get("account"))) if p["posted_time"]]
    groups = _by(posts, lambda p: p["posted_time"][:2])
    if not groups:
        raise ValueError("I need posted videos with a time and numbers. Log the time you posted.")
    rows = [[f"{h}:00", str(len(v)), store.count(mean(v))] for h, v in sorted(groups.items())]
    top = max(groups, key=lambda h: mean(groups[h]))
    return _table("Views by posting hour", "creatorstats-best-hour", ["Hour", "Videos", "Avg views"], rows,
                  f"Your best hour so far is {top}:00. Try it a few more times before you trust it.")


def themes(settings: Settings, args: dict, today: date) -> screen.Shown:
    data = store.load(settings)
    groups = _by([p for p in _posted(data, store.accounts_for(data, args.get("account"))) if p["theme"]], lambda p: p["theme"].lower())
    if not groups:
        raise ValueError("I need videos with a theme and numbers. Give a theme when you plan a video.")
    order = sorted(groups, key=lambda t: mean(groups[t]), reverse=True)
    rows = [[t, str(len(groups[t])), store.count(mean(groups[t])), store.count(max(groups[t]))] for t in order]
    return _table("Themes that work", "creatorstats-themes", ["Theme", "Videos", "Avg views", "Best"], rows,
                  f"'{order[0]}' does best, {store.count(mean(groups[order[0]]))} views on average.")


def length_check(settings: Settings, args: dict, today: date) -> screen.Shown:
    data = store.load(settings)
    found = [p for p in _posted(data, store.accounts_for(data, args.get("account"))) if p["length"] and store.latest(p)]
    if not found:
        raise ValueError("I need videos with a length in seconds and numbers.")
    bands = [("Under 20s", 0, 20), ("20 to 40s", 20, 40), ("40 to 60s", 40, 60), ("Over 60s", 60, 10_000)]
    scored = []
    for label, low, high in bands:
        v = [store.views_of(p) for p in found if low <= p["length"] < high]
        if v:
            scored.append((mean(v), [label, str(len(v)), store.count(mean(v))]))
    rows = [r for _, r in scored]
    best = max(scored)[1]
    return _table("Views by video length", "creatorstats-length", ["Length", "Videos", "Avg views"], rows,
                  f"{best[0]} videos do best for you so far.")


def conversion(settings: Settings, args: dict, today: date) -> screen.Shown:
    data = store.load(settings)
    found = [p for p in _posted(data, store.accounts_for(data, args.get("account"))) if store.views_of(p) and "follows" in store.latest(p)]
    if not found:
        raise ValueError("I need videos with views and follows gained.")
    found.sort(key=lambda p: store.latest(p)["follows"] / store.views_of(p), reverse=True)
    rows = [[f"#{p['id']} {p['title']}", store.count(store.views_of(p)), str(store.latest(p)["follows"]),
             f"{store.latest(p)['follows'] / store.views_of(p) * 1000:.1f}"] for p in found[:10]]
    total = sum(store.latest(p)["follows"] for p in found) / sum(store.views_of(p) for p in found) * 1000
    return _table("Follows per 1,000 views", "creatorstats-conversion", ["Video", "Views", "Follows", "Per 1k"], rows,
                  f"You gain about {total:.1f} followers per 1,000 views.")


def consistency(settings: Settings, args: dict, today: date) -> screen.Shown:
    data = store.load(settings)
    names = store.accounts_for(data, args.get("account"))
    start = today - timedelta(days=int(hs.number(args.get("days") or 30, "number of days", 7, 180)) - 1)
    planned = [p for p in data["posts"] if p["account"] in names and p["planned_date"]
               and start.isoformat() <= p["planned_date"] <= today.isoformat()]
    kept = [p for p in planned if p["posted_date"] and p["posted_date"] <= p["planned_date"]]
    late = [p for p in planned if p["posted_date"] and p["posted_date"] > p["planned_date"]]
    missed = [p for p in planned if not p["posted_date"]]
    rows = [["Planned", str(len(planned))], ["Posted on time", str(len(kept))], ["Posted late", str(len(late))],
            ["Not posted", str(len(missed))]]
    pct = round(len(kept) / len(planned) * 100) if planned else 0
    return _table("Sticking to the plan", "creatorstats-consistency", ["", "Videos"], rows,
                  f"{pct}% of planned videos went out on time." if planned else "Nothing was planned in that period.")


def earnings_estimate(settings: Settings, args: dict, today: date) -> screen.Shown:
    data = store.load(settings)
    key, acct = store.account(data, args.get("account"))
    if args.get("rpm") is not None:
        acct["rpm"] = hs.number(args["rpm"], "earnings per 1,000 views", 0, 1000)
        store.save(settings, data)
    if not acct["rpm"]:
        raise ValueError("Tell me your own pounds per 1,000 views (RPM) from the app, and I'll do the sum. I don't guess it.")
    views = store.whole(args.get("views"), "views") if args.get("views") is not None else sum(
        store.views_of(p) for p in _posted(data, [key], today - timedelta(days=29), today))
    total = views / 1000 * acct["rpm"]
    rows = [["Views", store.count(views)], ["Your RPM", store.gbp(acct["rpm"])], ["Estimate", store.gbp(total)]]
    return _table("Rough earnings", "creatorstats-earnings", ["", "Value"], rows,
                  f"About {store.gbp(total)} on {store.count(views)} views at your rate. Only an estimate, not a promise.",
                  text="Uses the rate you typed. Rates vary a lot; UK tax on any income: check GOV.UK.")


def export_csv(settings: Settings, args: dict, today: date) -> str:
    data = store.load(settings)
    if not data["posts"]:
        raise ValueError("There are no videos to export yet.")
    path = memory.root(settings) / f"creatorstats-export-{today.isoformat()}.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "account", "title", "theme", "posted", "time", "length", "checkpoint", *store.METRICS])
        for p in data["posts"]:
            for cp in store.CHECKPOINTS if p["stats"] else [""]:
                m = p["stats"].get(cp, {})
                w.writerow([store.safe_cell(x) for x in (p["id"], p["account"], p["title"], p["theme"], p["posted_date"],
                                                         p["posted_time"], p["length"], cp, *[m.get(k, "") for k in store.METRICS])])
    return f"Saved {len(data['posts'])} videos to {path.name} in your memory folder."


def tool_definitions() -> list[dict]:
    return [{
        "name": "creator_reports",
        "description": "Reports from the numbers the user logged (never fetched). action: dashboard = accounts overview; "
                       "growth_chart = follower line chart; views_trend = views per video; weekly_report/monthly_report "
                       "= this period against the one before; averages = average and median views and engagement; "
                       "compare_accounts = accounts side by side; compare_posts = two videos (post, post_b); best_day/"
                       "best_hour/themes/length_check = what posts best by weekday, hour, theme or length; conversion = "
                       "follows per 1,000 views; consistency = planned against posted; earnings_estimate = rough pounds "
                       "from the user's own RPM (never guess one); export_csv = save a spreadsheet file.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "account": {"type": "string", "description": "May be left out to cover all accounts."},
                "post": {"type": "string"}, "post_b": {"type": "string"},
                "date": {"type": "string", "description": "weekly_report: any day in that week."},
                "month": {"type": "string", "description": "monthly_report: YYYY-MM, this month, last month."},
                "days": {"type": "integer"}, "limit": {"type": "integer"},
                "rpm": {"type": "number", "description": "earnings_estimate: the user's pounds per 1,000 views."},
                "views": {"type": "integer"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"creator_reports"}


def run_tool(name: str, args: dict, settings: Settings, http=None, today: date | None = None):
    today = today or date.today()
    action = args.get("action")
    actions = {"dashboard": dashboard, "growth_chart": growth_chart, "views_trend": views_trend,
               "weekly_report": weekly_report, "monthly_report": monthly_report, "averages": averages,
               "compare_accounts": compare_accounts, "compare_posts": compare_posts, "best_day": best_day,
               "best_hour": best_hour, "themes": themes, "length_check": length_check, "conversion": conversion,
               "consistency": consistency, "earnings_estimate": earnings_estimate, "export_csv": export_csv}
    if action not in actions:
        raise ValueError(f"Unknown creator reports action: {action}")
    return actions[action](settings, args, today)
