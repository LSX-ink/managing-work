"""Creator accounts: a list of accounts (name, platform, niche, follower goal), follower counts the user types in,
goals, milestone countdowns, three daily posting slots, UK best-time guidance (editable) and an eligibility checklist.

Everything is saved in creatorstats.json in the memory folder. Numbers come from the user, never from a platform.
"""

from datetime import date, timedelta

import creatorstats_store as store
import homestore as hs
import screen
from config import Settings

ACTIONS = ["account_add", "account_update", "account_remove", "accounts", "followers_log", "goal_set", "goal_track",
           "milestones", "slots_set", "schedule", "best_times", "best_times_edit", "eligibility_add",
           "eligibility_tick", "eligibility_remove", "eligibility"]


def account_add(settings: Settings, args: dict, today: date) -> str:
    data = store.load(settings)
    name = hs.need(args.get("account"), "account name", 40)
    if hs.find(data["accounts"], name) == name or name in data["accounts"]:
        raise ValueError(f"You already have {name}.")
    if len(data["accounts"]) >= store.MAX_ACCOUNTS:
        raise ValueError("That's plenty of accounts.")
    goal = store.whole(args.get("goal_followers") or 0, "follower goal")
    data["accounts"][name] = store.blank_account(hs.clean(args.get("platform"), 30) or "TikTok",
                                                 hs.clean(args.get("niche"), 60), goal)
    store.save(settings, data)
    return f"Added {name}. Tell me its follower count whenever you check it and I'll track growth."


def account_update(settings: Settings, args: dict, today: date) -> str:
    data = store.load(settings)
    key, acct = store.account(data, args.get("account"))
    changed = []
    if hs.clean(args.get("platform")):
        acct["platform"] = hs.clean(args.get("platform"), 30)
        changed.append("platform")
    if hs.clean(args.get("niche")):
        acct["niche"] = hs.clean(args.get("niche"), 60)
        changed.append("niche")
    if args.get("goal_followers") is not None:
        acct["goal_followers"] = store.whole(args["goal_followers"], "follower goal")
        changed.append("goal")
    if hs.clean(args.get("new_name")):
        new = hs.need(args.get("new_name"), "new name", 40)
        if new in data["accounts"]:
            raise ValueError(f"You already have {new}.")
        data["accounts"][new] = data["accounts"].pop(key)
        for p in data["posts"]:
            if p["account"] == key:
                p["account"] = new
        changed.append("name")
    if not changed:
        raise ValueError("What should I change: the platform, niche, goal or name?")
    store.save(settings, data)
    return f"Updated {key}: {', '.join(changed)}."


def account_remove(settings: Settings, args: dict, today: date) -> str:
    data = store.load(settings)
    key, _ = store.account(data, args.get("account"))
    mine = [p for p in data["posts"] if p["account"] == key]
    if not args.get("confirmed"):
        return f"Removing {key} also deletes its {len(mine)} saved videos and numbers. Ask the user to confirm first."
    del data["accounts"][key]
    data["posts"] = [p for p in data["posts"] if p["account"] != key]
    store.save(settings, data)
    return f"Removed {key} and its {len(mine)} videos."


def accounts(settings: Settings, today: date) -> screen.Shown:
    data = store.load(settings)
    if not data["accounts"]:
        raise ValueError("You haven't added an account yet. Say the name, platform and niche.")
    rows = []
    for key, a in data["accounts"].items():
        now = store.current_followers(a)
        posted = sum(1 for p in data["posts"] if p["account"] == key and store.is_posted(p))
        rows.append([key, a["platform"], a["niche"] or "-", "-" if now is None else f"{now:,}",
                     f"{a['goal_followers']:,}" if a["goal_followers"] else "-", str(posted)])
    card = screen.card("table", "My accounts", "creatorstats-accounts",
                       columns=["Account", "Platform", "Niche", "Followers", "Goal", "Posts"], rows=rows,
                       buttons=[store.button("Compare", "Compare my accounts."),
                                store.button("Calendar", "Show my content calendar.")])
    return screen.Shown(f"You have {len(rows)} account{'s' if len(rows) != 1 else ''}.", card)


def followers_log(settings: Settings, args: dict, today: date) -> str:
    data = store.load(settings)
    key, acct = store.account(data, args.get("account"))
    count = store.whole(args.get("followers"), "follower count")
    day = hs.parse_day(args.get("date"), today)
    log = [e for e in acct["followers"] if e["date"] != day.isoformat()]
    previous = sorted(log, key=lambda e: e["date"])[-1]["count"] if log else None
    acct["followers"] = sorted(log + [{"date": day.isoformat(), "count": count}], key=lambda e: e["date"])[-730:]
    store.save(settings, data)
    change = "" if previous is None else f" That's {count - previous:+,} since last time."
    return f"{key} is on {count:,} followers.{change}"


def _goal_row(key: str, acct: dict, today: date) -> list:
    now, goal = store.current_followers(acct), acct["goal_followers"]
    if now is None or not goal:
        return [key, "-" if now is None else f"{now:,}", f"{goal:,}" if goal else "-", acct["goal_date"] or "-", "-", "-", "Set a goal and log followers"]
    rate = store.daily_growth(acct, today)
    pace = "-" if rate is None else f"{rate:+.1f}"
    if now >= goal:
        return [key, f"{now:,}", f"{goal:,}", acct["goal_date"] or "-", "0", pace, "Goal reached"]
    if not acct["goal_date"]:
        return [key, f"{now:,}", f"{goal:,}", "-", "-", pace, f"{goal - now:,} to go"]
    days = (date.fromisoformat(acct["goal_date"]) - today).days
    if days <= 0:
        return [key, f"{now:,}", f"{goal:,}", acct["goal_date"], "-", pace, f"Missed by {goal - now:,}"]
    need = (goal - now) / days
    verdict = "No pace yet" if rate is None else "On track" if rate >= need else "Behind"
    return [key, f"{now:,}", f"{goal:,}", acct["goal_date"], f"{need:.1f}", pace, verdict]


def goal_set(settings: Settings, args: dict, today: date) -> str:
    data = store.load(settings)
    key, acct = store.account(data, args.get("account"))
    acct["goal_followers"] = store.whole(args.get("goal_followers"), "follower goal")
    if hs.clean(args.get("goal_date")):
        acct["goal_date"] = hs.parse_day(args.get("goal_date"), today).isoformat()
    store.save(settings, data)
    when = f" by {hs.spoken(date.fromisoformat(acct['goal_date']))}" if acct["goal_date"] else ""
    return f"Goal for {key}: {acct['goal_followers']:,} followers{when}."


def goal_track(settings: Settings, args: dict, today: date) -> screen.Shown:
    data = store.load(settings)
    names = store.accounts_for(data, args.get("account"))
    if not names:
        raise ValueError("You haven't added an account yet.")
    rows = [_goal_row(k, data["accounts"][k], today) for k in names]
    first = rows[0]
    said = f"{first[0]}: {first[6].lower()}" + (f", needs {first[4]} followers a day." if first[4] not in ("-", "0") else ".")
    card = screen.card("table", "Follower goals", "creatorstats-goals",
                       columns=["Account", "Now", "Goal", "By", "Need/day", "Pace/day", "Status"], rows=rows,
                       buttons=[store.button("Milestones", "When will I hit my next milestones?"),
                                store.button("Growth chart", "Show my follower growth chart.")])
    return screen.Shown(said, card)


def _eta(now: int, target: int, rate: float | None, today: date) -> str:
    if now >= target:
        return "Done"
    if not rate or rate <= 0:
        return "No growth yet"
    days = int((target - now) / rate) + 1
    return f"{today + timedelta(days=days):%d %b %Y} (in {days} days)"


def milestones(settings: Settings, args: dict, today: date) -> screen.Shown:
    data = store.load(settings)
    names = [k for k in store.accounts_for(data, args.get("account")) if store.current_followers(data["accounts"][k]) is not None]
    if not names:
        raise ValueError("Tell me a follower count first, like: lowkey.lore has 850 followers.")
    rows, said = [], ""
    for key in names:
        acct = data["accounts"][key]
        now, rate = store.current_followers(acct), store.daily_growth(acct, today)
        for target in store.MILESTONES:
            rows.append([key, f"{target:,}", f"{max(target - now, 0):,}", _eta(now, target, rate, today)])
        nxt = next((t for t in store.MILESTONES if t > now), None)
        if nxt and not said:
            said = f"{key} needs {nxt - now:,} more for {nxt:,}: {_eta(now, nxt, rate, today)}."
    card = screen.card("table", "Milestones", "creatorstats-milestones",
                       columns=["Account", "Milestone", "To go", "At recent pace"], rows=rows,
                       buttons=[store.button("Goal tracker", "How is my follower goal going?")])
    return screen.Shown((said or "Every milestone is already passed.") + " Projections use your recent growth and can change.", card)


def slots_set(settings: Settings, args: dict, today: date) -> str:
    data = store.load(settings)
    key, acct = store.account(data, args.get("account"))
    times = args.get("slots") or []
    if not 1 <= len(times) <= 3:
        raise ValueError("Give one to three posting times, like 07:30, 12:30 and 19:30.")
    acct["slots"] = sorted({store.parse_time(t) for t in times})
    store.save(settings, data)
    return f"{key} posts at {', '.join(acct['slots'])}."


def _week_days(start: date) -> list[date]:
    return [start + timedelta(days=i) for i in range(7)]


def schedule(settings: Settings, args: dict, today: date) -> screen.Shown:
    data = store.load(settings)
    names = store.accounts_for(data, args.get("account"))
    if not names:
        raise ValueError("You haven't added an account yet.")
    start = hs.week_start(hs.parse_day(args.get("date"), today))
    rows = []
    for key in names:
        acct = data["accounts"][key]
        for day in _week_days(start):
            cells = [f"{s} free" for s in acct["slots"]]
            for p in data["posts"]:
                if p["account"] == key and (p["posted_date"] or p["planned_date"]) == day.isoformat():
                    i = store.slot_index(acct, p["posted_time"] or p["planned_time"])
                    cells[i] = f"{acct['slots'][i]} {'✓ ' if store.is_posted(p) else ''}{p['title']}"
            rows.append([f"{day:%a %d %b}", key] + cells + [""] * (3 - len(cells)))
    free = sum(1 for r in rows for c in r[2:] if c.endswith(" free"))
    card = screen.card("table", f"Posting week from {start:%d %b}", "creatorstats-schedule",
                       columns=["Day", "Account", "Slot 1", "Slot 2", "Slot 3"], rows=rows,
                       buttons=[store.button("Calendar", "Show my content calendar."),
                                store.button("Best times", "When are the best times to post?")])
    return screen.Shown(f"{free} free slots in the week from {hs.spoken(start)}.", card)


def _windows(data: dict, key: str) -> dict:
    mine = data["best_times"].get(key) or {}
    return {"weekdays": mine.get("weekdays") or store.DEFAULT_TIMES["weekdays"],
            "weekends": mine.get("weekends") or store.DEFAULT_TIMES["weekends"]}


def best_times(settings: Settings, args: dict, today: date) -> screen.Shown:
    data = store.load(settings)
    key = store.account(data, args.get("account"))[0] if data["accounts"] and (args.get("account") or len(data["accounts"]) == 1) else ""
    wins = _windows(data, key)
    edited = bool(data["best_times"].get(key))
    rows = [["Monday to Friday", w] for w in wins["weekdays"]] + [["Saturday and Sunday", w] for w in wins["weekends"]]
    card = screen.card("table", "Best times to post (UK)", "creatorstats-best-times", columns=["Days", "Window"], rows=rows,
                       buttons=[store.button("My own best hours", "Which posting times work best for me?"),
                                store.button("Weekly schedule", "Show my posting schedule.")],
                       text=store.GUIDANCE)
    who = f" for {key}" if edited else ""
    return screen.Shown(f"Here are the usual UK windows{who}. {store.GUIDANCE}", card)


def best_times_edit(settings: Settings, args: dict, today: date) -> str:
    data = store.load(settings)
    key, _ = store.account(data, args.get("account"))
    if args.get("reset"):
        data["best_times"].pop(key, None)
        store.save(settings, data)
        return f"Back to the general UK windows for {key}."
    kind = args.get("day_type")
    windows = [hs.clean(w, 60) for w in (args.get("windows") or []) if hs.clean(w)]
    if kind not in ("weekdays", "weekends") or not windows:
        raise ValueError("Say whether it's weekdays or weekends and give the time windows, like 18:00-21:00.")
    data["best_times"].setdefault(key, {})[kind] = windows[:6]
    store.save(settings, data)
    return f"Saved your {kind} windows for {key}: {', '.join(windows[:6])}."


def eligibility_add(settings: Settings, args: dict, today: date) -> str:
    data = store.load(settings)
    text = hs.need(args.get("item"), "checklist item", 120)
    if len(data["eligibility"]) >= 40:
        raise ValueError("That's a long checklist already.")
    data["eligibility"].append({"text": text, "done": False, "note": hs.clean(args.get("note"), 120)})
    store.save(settings, data)
    return f"Added '{text}' to your eligibility checklist."


def _pick_item(data: dict, ref) -> dict:
    items, text = data["eligibility"], hs.clean(ref)
    if text.isdigit() and 1 <= int(text) <= len(items):
        return items[int(text) - 1]
    found = [i for i in items if text and text.lower() in i["text"].lower()]
    if len(found) != 1:
        raise ValueError("Which checklist item? Say its number or some of its words.")
    return found[0]


def eligibility_tick(settings: Settings, args: dict, today: date) -> str:
    data = store.load(settings)
    item = _pick_item(data, args.get("item"))
    item["done"] = args.get("done") is not False
    store.save(settings, data)
    return f"{'Ticked' if item['done'] else 'Unticked'} '{item['text']}'."


def eligibility_remove(settings: Settings, args: dict, today: date) -> str:
    data = store.load(settings)
    item = _pick_item(data, args.get("item"))
    if not args.get("confirmed"):
        return f"Ask the user to confirm removing '{item['text']}' from the checklist."
    data["eligibility"].remove(item)
    store.save(settings, data)
    return f"Removed '{item['text']}'."


def eligibility(settings: Settings, today: date) -> screen.Shown:
    data = store.load(settings)
    items = data["eligibility"]
    if not items:
        raise ValueError("Your checklist is empty. Add items with your own notes, like: 10,000 followers (check the current rules).")
    rows = [{"label": f"{i.get('text')}" + (f" ({i['note']})" if i.get("note") else ""), "done": i["done"],
             "say": f"Tick eligibility item {n}." if not i["done"] else f"Untick eligibility item {n}."}
            for n, i in enumerate(items, 1)]
    done = sum(1 for i in items if i["done"])
    card = screen.card("list", "Creator programme checklist", "creatorstats-eligibility", items=rows, checks=True,
                       buttons=[store.button("Add item", "Add an item to my eligibility checklist.")])
    return screen.Shown(f"{done} of {len(items)} ticked. These are your own notes; check the platform's current rules.", card)


def tool_definitions() -> list[dict]:
    return [{
        "name": "creator_accounts",
        "description": "Creator accounts and growth (TikTok etc). Numbers are typed or spoken by the user, never fetched. "
                       "action: account_add/account_update/account_remove = accounts with platform, niche, follower "
                       "goal (remove needs confirmed true only after the user agrees); accounts = table; "
                       "followers_log = today's follower count; goal_set/goal_track = follower goal by a date and "
                       "the daily growth needed; milestones = 1k, 10k, 100k countdown from recent growth; slots_set = "
                       "up to 3 daily posting times; schedule = weekly posting slots table; best_times = general UK "
                       "best times to post; best_times_edit = the user's own windows or reset; eligibility_add/"
                       "eligibility_tick/eligibility_remove/eligibility = creator fund or Creativity Program "
                       "checklist of the user's own notes (not claims).",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "account": {"type": "string", "description": "Account name; may be left out with one account."},
                "new_name": {"type": "string"},
                "platform": {"type": "string"},
                "niche": {"type": "string"},
                "goal_followers": {"type": "integer"},
                "goal_date": {"type": "string", "description": "YYYY-MM-DD."},
                "followers": {"type": "integer", "description": "followers_log: the count now."},
                "date": {"type": "string", "description": "YYYY-MM-DD, today, yesterday; default today."},
                "slots": {"type": "array", "items": {"type": "string"}, "description": "slots_set: up to 3 times like 19:30."},
                "day_type": {"type": "string", "enum": ["weekdays", "weekends"]},
                "windows": {"type": "array", "items": {"type": "string"}, "description": "e.g. 18:00-21:00."},
                "reset": {"type": "boolean"},
                "item": {"type": "string", "description": "Checklist item text, or its number."},
                "note": {"type": "string", "description": "e.g. the threshold the user noted."},
                "done": {"type": "boolean", "description": "eligibility_tick: false to untick."},
                "confirmed": {"type": "boolean", "description": "Set true only after the user confirms a removal."},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"creator_accounts"}


def run_tool(name: str, args: dict, settings: Settings, http=None, today: date | None = None):
    today = today or date.today()
    action = args.get("action")
    if action == "accounts":
        return accounts(settings, today)
    if action == "eligibility":
        return eligibility(settings, today)
    actions = {"account_add": account_add, "account_update": account_update, "account_remove": account_remove,
               "followers_log": followers_log, "goal_set": goal_set, "goal_track": goal_track,
               "milestones": milestones, "slots_set": slots_set, "schedule": schedule, "best_times": best_times,
               "best_times_edit": best_times_edit, "eligibility_add": eligibility_add,
               "eligibility_tick": eligibility_tick, "eligibility_remove": eligibility_remove}
    if action not in actions:
        raise ValueError(f"Unknown creator accounts action: {action}")
    return actions[action](settings, args, today)
