"""Post stats: the numbers the user reads off the app (views, likes, comments, shares, saves, watch time %, follows
gained) logged at 1 hour, 24 hours and 7 days, the rates worked out from them, best and worst tables, and a
hook A/B test log (two opening lines, results, a winner).

Everything is typed or spoken by the user and saved in creatorstats.json. Nothing is read from a platform.
"""

from datetime import date

import creatorstats_store as store
import homestore as hs
import screen
from config import Settings

ACTIONS = ["log_stats", "post_show", "posts", "rates", "best_posts", "worst_posts", "checkpoints_chart", "hook_add",
           "hook_result", "hook_winner", "hooks"]
ARG_FOR = {"views": "views", "likes": "likes", "comments": "comments", "shares": "shares", "saves": "saves",
           "watch": "watch_percent", "follows": "follows_gained"}
SORTS = {"views": lambda p: store.views_of(p), "engagement": lambda p: store.rates(store.latest(p))["engagement"],
         "shares": lambda p: store.rates(store.latest(p))["share"], "saves": lambda p: store.rates(store.latest(p))["save"],
         "follows": lambda p: store.latest(p).get("follows") or 0}


def _numbers(args: dict) -> dict:
    out = {}
    for key, arg in ARG_FOR.items():
        if args.get(arg) is not None:
            out[key] = (round(hs.number(args[arg], "watch time percentage", 0, 100), 1) if key == "watch"
                        else store.whole(args[arg], key))
    return out


def log_stats(settings: Settings, args: dict, today: date) -> str:
    data = store.load(settings)
    cp = args.get("checkpoint") or "24h"
    if cp not in store.CHECKPOINTS:
        raise ValueError("The checkpoint is 1h, 24h or 7d.")
    numbers = _numbers(args)
    if not numbers:
        raise ValueError("Which numbers? Give views, likes, comments, shares, saves, watch time percent or follows.")
    if hs.clean(args.get("post")):
        p = store.post(data, args.get("post"), args.get("account"))
    else:
        key = store.account(data, args.get("account"))[0]
        p = store.new_post(data, key, hs.need(args.get("title"), "video title", 100))
    if not store.is_posted(p):
        p["posted_date"] = hs.parse_day(args.get("date"), today).isoformat()
        p["posted_time"] = store.parse_time(args["time"]) if hs.clean(args.get("time")) else p["planned_time"]
    p["stats"].setdefault(cp, {}).update(numbers)
    store.save(settings, data)
    rate = store.rates(p["stats"][cp])["engagement"]
    shown = f"{store.count(p['stats'][cp]['views'])} views, {rate}% engagement" if p["stats"][cp].get("views") else ", ".join(
        f"{v:g} {k}" for k, v in numbers.items())
    return f"Logged {cp} for #{p['id']} '{p['title']}': {shown}."


def _find(data: dict, args: dict) -> dict:
    if hs.clean(args.get("post")):
        return store.post(data, args.get("post"), args.get("account"))
    with_stats = [p for p in data["posts"] if p["stats"] and (not hs.clean(args.get("account")) or p["account"].lower() == hs.clean(args["account"]).lower())]
    if not with_stats:
        raise ValueError("No videos with numbers yet. Log some stats first.")
    return max(with_stats, key=lambda p: (p["posted_date"], p["id"]))


def post_show(settings: Settings, args: dict, today: date) -> screen.Shown:
    data = store.load(settings)
    p = _find(data, args)
    rows = []
    for label, key in (("Views", "views"), ("Likes", "likes"), ("Comments", "comments"), ("Shares", "shares"),
                       ("Saves", "saves"), ("Avg watched %", "watch"), ("Follows gained", "follows")):
        rows.append([label] + [f"{p['stats'][cp][key]:g}" if key in p["stats"].get(cp, {}) else "-" for cp in store.CHECKPOINTS])
    for label, key in (("Engagement %", "engagement"), ("Share rate %", "share"), ("Save rate %", "save")):
        rows.append([label] + [f"{store.rates(p['stats'][cp])[key]}" if p["stats"].get(cp, {}).get("views") else "-" for cp in store.CHECKPOINTS])
    card = screen.card("table", f"#{p['id']} {p['title']}", f"creatorstats-post-{p['id']}",
                       columns=["", "1h", "24h", "7d"], rows=rows, text=f"{p['account']} - {p['theme'] or 'no theme'}",
                       buttons=[store.button("Log 24h", f"Log 24 hour stats for video #{p['id']}."),
                                store.button("Log 7d", f"Log 7 day stats for video #{p['id']}."),
                                store.button("Views curve", f"Show the views curve for video #{p['id']}.")])
    m = store.latest(p)
    said = (f"#{p['id']} '{p['title']}': {store.count(m.get('views'))} views, {store.rates(m)['engagement']}% engagement."
            if m else f"#{p['id']} '{p['title']}' has no numbers yet.")
    return screen.Shown(said, card)


def posts(settings: Settings, args: dict, today: date) -> screen.Shown:
    data = store.load(settings)
    names = store.accounts_for(data, args.get("account"))
    status = args.get("status") or "all"
    limit = int(hs.number(args.get("limit") or 20, "limit", 1, 100))
    found = [p for p in data["posts"] if p["account"] in names and (
        status == "all" or (status == "posted") == store.is_posted(p))]
    found = sorted(found, key=lambda p: (p["posted_date"] or p["planned_date"], p["id"]), reverse=True)[:limit]
    rows = [[f"#{p['id']}", p["posted_date"] or p["planned_date"] or "-", p["account"], p["title"],
             store.count(store.views_of(p)) if p["stats"] else "-",
             f"{store.rates(store.latest(p))['engagement']}%" if p["stats"] else "-"] for p in found]
    card = screen.card("table", "My videos", "creatorstats-posts", columns=["#", "Date", "Account", "Video", "Views", "Eng."],
                       rows=rows, buttons=[store.button("Best", "Which are my best videos?"),
                                           store.button("Worst", "Which are my worst videos?")])
    return screen.Shown(f"{len(rows)} videos shown." if rows else "No videos yet.", card)


def rates_calc(settings: Settings, args: dict, today: date) -> screen.Shown:
    numbers = _numbers(args)
    if not numbers.get("views"):
        if not (hs.clean(args.get("post")) or args.get("checkpoint")):
            raise ValueError("Give the views and at least one of likes, comments, shares or saves.")
        p = _find(store.load(settings), args)
        numbers = store.latest(p)
    r = store.rates(numbers)
    rows = [["Engagement rate", f"{r['engagement']}%"], ["Like rate", f"{r['like']}%"], ["Comment rate", f"{r['comment']}%"],
            ["Share rate", f"{r['share']}%"], ["Save rate", f"{r['save']}%"]]
    card = screen.card("table", "Rates", "creatorstats-rates", columns=["Rate", "Of views"], rows=rows,
                       text="Engagement = likes + comments + shares + saves, divided by views.")
    return screen.Shown(f"Engagement {r['engagement']}%, share rate {r['share']}%, save rate {r['save']}%.", card)


def _ranked(settings: Settings, args: dict, worst: bool) -> screen.Shown:
    data = store.load(settings)
    names = store.accounts_for(data, args.get("account"))
    sort = args.get("metric") or "views"
    if sort not in SORTS:
        raise ValueError("Rank by views, engagement, shares, saves or follows.")
    found = [p for p in data["posts"] if p["account"] in names and store.latest(p)]
    if not found:
        raise ValueError("No videos with numbers yet. Log some stats first.")
    limit = int(hs.number(args.get("limit") or 5, "limit", 1, 20))
    found = sorted(found, key=SORTS[sort], reverse=not worst)[:limit]
    rows = [[str(n), f"#{p['id']} {p['title']}", p["account"], store.count(store.views_of(p)),
             f"{store.rates(store.latest(p))['engagement']}%", f"{store.rates(store.latest(p))['share']}%",
             f"{store.rates(store.latest(p))['save']}%", str(store.latest(p).get("follows") or 0)]
            for n, p in enumerate(found, 1)]
    title = f"{'Worst' if worst else 'Best'} videos by {sort}"
    card = screen.card("table", title, f"creatorstats-{'worst' if worst else 'best'}-{sort}",
                       columns=["", "Video", "Account", "Views", "Eng.", "Shares", "Saves", "Follows"], rows=rows,
                       buttons=[store.button("What's working", "What's working for me?")])
    return screen.Shown(f"{'Weakest' if worst else 'Top'} by {sort}: '{found[0]['title']}' with {store.count(store.views_of(found[0]))} views.", card)


def best_posts(settings: Settings, args: dict, today: date) -> screen.Shown:
    return _ranked(settings, args, False)


def worst_posts(settings: Settings, args: dict, today: date) -> screen.Shown:
    return _ranked(settings, args, True)


def checkpoints_chart(settings: Settings, args: dict, today: date) -> screen.Shown:
    p = _find(store.load(settings), args)
    cps = [cp for cp in store.CHECKPOINTS if p["stats"].get(cp, {}).get("views") is not None]
    if len(cps) < 2:
        raise ValueError("I need views at two checkpoints (1h, 24h, 7d) to draw a curve.")
    card = screen.card("chart", f"Views over time: {p['title']}", f"creatorstats-curve-{p['id']}",
                       chart={"type": "line", "labels": cps, "values": [p["stats"][cp]["views"] for cp in cps], "unit": ""})
    return screen.Shown(f"'{p['title']}' went from {store.count(p['stats'][cps[0]]['views'])} to {store.count(p['stats'][cps[-1]]['views'])} views by {cps[-1]}.", card)


def _hook(data: dict, ref) -> dict:
    text = hs.clean(ref)
    found = [h for h in data["hooks"] if text.lstrip("#").isdigit() and h["id"] == int(text.lstrip("#"))]
    if not found:
        raise ValueError("Which hook test? Give its number.")
    return found[0]


def hook_add(settings: Settings, args: dict, today: date) -> str:
    data = store.load(settings)
    key = store.account(data, args.get("account"))[0]
    if len(data["hooks"]) >= store.MAX_HOOKS:
        raise ValueError("That's a lot of hook tests; finish a few first.")
    a, b = hs.need(args.get("hook_a"), "first hook", 160), hs.need(args.get("hook_b"), "second hook", 160)
    n = max([h["id"] for h in data["hooks"]] + [0]) + 1
    data["hooks"].append({"id": n, "account": key, "date": today.isoformat(), "a": a, "b": b, "results": {}, "winner": ""})
    store.save(settings, data)
    return f"Started hook test {n} for {key}: A '{a}' against B '{b}'."


def hook_result(settings: Settings, args: dict, today: date) -> str:
    data = store.load(settings)
    h = _hook(data, args.get("hook"))
    variant = hs.clean(args.get("variant")).lower()
    if variant not in ("a", "b"):
        raise ValueError("Which hook: A or B?")
    numbers = _numbers(args)
    if not numbers:
        raise ValueError("Give the views (and if you have them, watch time percent, likes or shares).")
    h["results"].setdefault(variant, {}).update(numbers)
    store.save(settings, data)
    return f"Saved the result for hook {variant.upper()} in test {h['id']}: " + ", ".join(f"{v:g} {k}" for k, v in numbers.items()) + "."


def _score(result: dict, metric: str) -> float:
    if metric == "engagement":
        return store.rates(result)["engagement"]
    return float(result.get(metric) or 0)


def hook_winner(settings: Settings, args: dict, today: date) -> str:
    data = store.load(settings)
    h = _hook(data, args.get("hook"))
    if hs.clean(args.get("variant")).lower() in ("a", "b"):
        h["winner"] = hs.clean(args["variant"]).lower()
        store.save(settings, data)
        return f"Hook {h['winner'].upper()} wins test {h['id']}: '{h[h['winner']]}'."
    if not (h["results"].get("a") and h["results"].get("b")):
        raise ValueError("I need results for both hooks first, or tell me which one won.")
    metric = args.get("metric") or "views"
    if metric not in ("views", "watch", "engagement", "shares", "likes"):
        raise ValueError("Judge by views, watch time, engagement, shares or likes.")
    a, b = _score(h["results"]["a"], metric), _score(h["results"]["b"], metric)
    if a == b:
        return f"It's a tie on {metric}. One test on its own isn't proof; try again with new videos."
    h["winner"] = "a" if a > b else "b"
    store.save(settings, data)
    top, low = max(a, b), min(a, b)
    edge = f" by {round((top - low) / low * 100)}%" if low else ""
    return (f"Hook {h['winner'].upper()} wins on {metric}{edge}: '{h[h['winner']]}'. One test is a small sample, "
            "so run it again before you rely on it.")


def hooks(settings: Settings, args: dict, today: date) -> screen.Shown:
    data = store.load(settings)
    names = store.accounts_for(data, args.get("account"))
    found = [h for h in data["hooks"] if h["account"] in names]
    if not found:
        raise ValueError("No hook tests yet. Say the two hooks you want to compare.")

    def cell(h, v):
        r = h["results"].get(v, {})
        return store.count(r["views"]) if r.get("views") is not None else "-"

    rows = [[str(h["id"]), h["account"], h["a"], h["b"], cell(h, "a"), cell(h, "b"),
             h["winner"].upper() if h["winner"] else "open"] for h in found]
    card = screen.card("table", "Hook tests", "creatorstats-hooks",
                       columns=["#", "Account", "Hook A", "Hook B", "A views", "B views", "Winner"], rows=rows,
                       buttons=[store.button("New test", "Start a hook test.")])
    return screen.Shown(f"{len(found)} hook tests, {sum(1 for h in found if h['winner'])} decided.", card)


def tool_definitions() -> list[dict]:
    number = {"type": "integer"}
    return [{
        "name": "creator_stats",
        "description": "Log and read how videos performed, from numbers the user reads out (never fetched). action: "
                       "log_stats = views, likes, comments, shares, saves, watch_percent, follows_gained at "
                       "checkpoint 1h, 24h or 7d for a video (post = number or title; a new title creates it as "
                       "posted); post_show = one video's scorecard; posts = table of videos; rates = engagement, "
                       "share and save rate calculation; best_posts/worst_posts = ranked tables; checkpoints_chart "
                       "= views 1h to 7d line; hook_add = hook A/B test with two hooks; hook_result = numbers for "
                       "A or B; hook_winner = pick or work out the winner; hooks = table of tests.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "account": {"type": "string"},
                "post": {"type": "string", "description": "A video's number (#3) or part of its title."},
                "title": {"type": "string", "description": "log_stats: a new video's title."},
                "checkpoint": {"type": "string", "enum": store.CHECKPOINTS},
                "date": {"type": "string", "description": "When it was posted, YYYY-MM-DD; default today."},
                "time": {"type": "string", "description": "When it was posted, e.g. 19:30."},
                "views": number, "likes": number, "comments": number, "shares": number, "saves": number,
                "watch_percent": {"type": "number", "description": "Average watched, 0 to 100."},
                "follows_gained": number,
                "status": {"type": "string", "enum": ["all", "posted", "planned"]},
                "metric": {"type": "string", "description": "best/worst: views, engagement, shares, saves, follows. "
                                                            "hook_winner: views, watch, engagement, shares, likes."},
                "limit": number,
                "hook": {"type": "string", "description": "A hook test's number."},
                "hook_a": {"type": "string"}, "hook_b": {"type": "string"},
                "variant": {"type": "string", "enum": ["a", "b"]},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"creator_stats"}


def run_tool(name: str, args: dict, settings: Settings, http=None, today: date | None = None):
    today = today or date.today()
    action = args.get("action")
    actions = {"log_stats": log_stats, "post_show": post_show, "posts": posts, "rates": rates_calc,
               "best_posts": best_posts, "worst_posts": worst_posts, "checkpoints_chart": checkpoints_chart,
               "hook_add": hook_add, "hook_result": hook_result, "hook_winner": hook_winner, "hooks": hooks}
    if action not in actions:
        raise ValueError(f"Unknown creator stats action: {action}")
    return actions[action](settings, args, today)
