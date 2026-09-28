"""Kids' rewards: a sticker chart of goals and stars, rewards earned at so many stars, and pocket money jars.

Stars are kept per child with the day and goal they were for; a child's star balance is every star earned minus
the stars spent on rewards. Pocket money is paid into spend, save and give jars every Monday by itself.
Everything is in kids-stars.json and kids-pocket.json in the memory folder.
"""

from datetime import date, timedelta

import homestore as hs
import kids_store as ks
import screen
from config import Settings

STARS, POCKET = "kids-stars.json", "kids-pocket.json"
screen.EXTRA_KINDS.update({"kids-stars", "kids-jars"})
JARS = ("spend", "save", "give")
DEFAULT_SPLIT = {"spend": 50, "save": 40, "give": 10}
OTHER = "Other stars"
MAX_GOALS, MAX_REWARDS = 10, 10


# Sticker chart and rewards

def _kid(found: dict, name, create: bool = True) -> tuple[str, dict]:
    k = ks.child(found, name, create)
    rec = found.get(k) if isinstance(found.get(k), dict) else {}
    rec.setdefault("goals", [])
    rec.setdefault("stars", [])
    rec.setdefault("rewards", [])
    rec.setdefault("spent", 0)
    found[k] = rec
    return k, rec


def _earned(rec: dict) -> int:
    return max(0, sum(int(s.get("n", 0)) for s in rec["stars"]))


def balance(rec: dict) -> int:
    return max(0, _earned(rec) - int(rec.get("spent", 0)))


def week_stars(rec: dict, week: date) -> int:
    end = (week + timedelta(days=7)).isoformat()
    return max(0, sum(int(s.get("n", 0)) for s in rec.get("stars", []) if week.isoformat() <= s.get("date", "") < end))


def set_goals(settings: Settings, name, items) -> str:
    found = ks.load(settings, STARS)
    k, rec = _kid(found, name)
    have = {g.lower() for g in rec["goals"]}
    new = [g for g in (hs.clean(i, 40) for i in items or []) if g and g.lower() not in have]
    if not new:
        raise ValueError("Which goals? Say something like 'brushing teeth' or 'tidying up'.")
    rec["goals"] = (rec["goals"] + new)[:MAX_GOALS]
    ks.save(settings, STARS, found)
    return f"{k}'s sticker chart goals: {', '.join(rec['goals'])}."


def _goal(rec: dict, goal) -> str:
    text = hs.clean(goal, 40)
    if not text:
        return OTHER
    k = hs.find(rec["goals"], text)
    if k:
        return k
    if len(rec["goals"]) < MAX_GOALS:
        rec["goals"].append(text)
    return text


def add_star(settings: Settings, name, goal, count, when) -> screen.Shown:
    n = int(hs.number(count if count is not None else 1, "number of stars", -10, 10))
    if n == 0:
        raise ValueError("How many stars?")
    found = ks.load(settings, STARS)
    k, rec = _kid(found, name)
    day = hs.parse_day(when)
    g = _goal(rec, goal)
    rec["stars"] = ks.append(rec["stars"], {"date": day.isoformat(), "goal": g, "n": n})
    ks.save(settings, STARS, found)
    week = week_stars(rec, hs.week_start(hs.today()))
    said = (f"{'A star' if n == 1 else hs.plural(n, 'star')} for {k}" + (f" for {g}" if g != OTHER else "") + "! "
            if n > 0 else f"Took {hs.plural(-n, 'star')} off {k}. ")
    return screen.Shown(said + f"{hs.plural(week, 'star')} this week.", chart_card(k, rec))


def chart_card(k: str, rec: dict, view: str = "week") -> dict:
    today = hs.today()
    week = hs.week_start(today)
    days = [week + timedelta(days=i) for i in range(7)]
    goals = list(rec["goals"]) + ([OTHER] if any(s.get("goal") == OTHER for s in rec["stars"]) else [])
    grid = []
    for g in goals:
        cells = [max(0, sum(int(s.get("n", 0)) for s in rec["stars"]
                            if s.get("goal", "").lower() == g.lower() and s.get("date") == d.isoformat()))
                 for d in days]
        grid.append({"goal": g, "cells": cells})
    have = balance(rec)
    rewards = [{"name": r["name"], "need": r["need"], "have": min(have, r["need"])}
               for r in rec["rewards"] if not r.get("claimed")]
    data = {"child": k, "view": view, "days": [f"{d.strftime('%a')} {d.day}" for d in days],
            "dates": [d.isoformat() for d in days], "today": today.weekday(), "grid": grid,
            "week": week_stars(rec, week), "balance": have, "rewards": rewards}
    buttons = [{"label": "Rewards", "say": f"Show {k}'s star rewards."}] if view == "week" else \
        [{"label": "Sticker chart", "say": f"Show {k}'s sticker chart."}]
    title = f"{k}'s sticker chart" if view == "week" else f"{k}'s rewards"
    return screen.card("kids-stars", title, f"kids-stars-{k}-{view}", data=data, buttons=buttons)


def star_chart(settings: Settings, name, view: str = "week") -> screen.Shown:
    found = ks.load(settings, STARS)
    k = ks.only_child(settings, found, name)
    k, rec = _kid(found, k)
    if view == "rewards":
        left = [r for r in rec["rewards"] if not r.get("claimed")]
        said = f"{k} has {hs.plural(balance(rec), 'star')} to spend" + \
            (f"; {hs.plural(len(left), 'reward')} to aim for." if left else "; no rewards set yet.")
    else:
        said = f"{k} has {hs.plural(week_stars(rec, hs.week_start(hs.today())), 'star')} this week."
    return screen.Shown(said, chart_card(k, rec, view))


def set_reward(settings: Settings, name, reward, stars) -> screen.Shown:
    found = ks.load(settings, STARS)
    k, rec = _kid(found, name)
    label = hs.need(reward, "reward", 60)
    need = int(hs.number(stars, "number of stars", 1, 500))
    rec["rewards"] = [r for r in rec["rewards"] if r["name"].lower() != label.lower() or r.get("claimed")]
    if sum(not r.get("claimed") for r in rec["rewards"]) >= MAX_REWARDS:
        raise ValueError("That's plenty of rewards to aim for; claim one first.")
    rec["rewards"].append({"name": label, "need": need, "claimed": ""})
    ks.save(settings, STARS, found)
    togo = max(0, need - balance(rec))
    said = f"{label} for {k} at {hs.plural(need, 'star')}; " + \
        (f"{togo} to go." if togo else "and there are enough stars already!")
    return screen.Shown(said, chart_card(k, rec, "rewards"))


def claim_reward(settings: Settings, name, reward) -> screen.Shown:
    found = ks.load(settings, STARS)
    k = ks.only_child(settings, found, name)
    k, rec = _kid(found, k)
    open_ = [r for r in rec["rewards"] if not r.get("claimed")]
    match = hs.find([r["name"] for r in open_], hs.need(reward, "reward", 60))
    if match is None:
        raise ValueError(f"{k} hasn't got a reward called {hs.clean(reward)}.")
    r = next(r for r in open_ if r["name"] == match)
    if balance(rec) < r["need"]:
        raise ValueError(f"{k} needs {hs.plural(r['need'] - balance(rec), 'more star')} for {match}.")
    rec["spent"] = int(rec["spent"]) + r["need"]
    r["claimed"] = hs.today().isoformat()
    ks.save(settings, STARS, found)
    return screen.Shown(f"Well done {k}! {match} claimed for {hs.plural(r['need'], 'star')}.",
                        chart_card(k, rec, "rewards"))


# Pocket money

def _split(values) -> dict:
    if not values:
        return dict(DEFAULT_SPLIT)
    nums = [int(hs.number(v, "percentage", 0, 100)) for v in list(values)[:3]]
    if len(nums) != 3 or sum(nums) != 100:
        raise ValueError("Give the spend, save and give split as three percentages that add up to 100.")
    return dict(zip(JARS, nums, strict=True))


def _pay(p: dict, amount: float, day: date, note: str) -> None:
    parts = {j: round(amount * p["split"][j] / 100, 2) for j in JARS}
    parts["spend"] = round(parts["spend"] + amount - sum(parts.values()), 2)
    for j in JARS:
        p["jars"][j] = round(p["jars"][j] + parts[j], 2)
    p["history"] = ks.append(p["history"], {"date": day.isoformat(), "jar": "all", "amount": amount, "note": note})


def _pocket(settings: Settings) -> dict:
    """Every child's pocket money, with any Mondays since the last payday paid in."""
    found = ks.load(settings, POCKET)
    monday = hs.week_start(hs.today())
    changed = False
    for p in found.values():
        p.setdefault("jars", dict.fromkeys(JARS, 0.0))
        p.setdefault("history", [])
        p.setdefault("split", dict(DEFAULT_SPLIT))
        paid = date.fromisoformat(p.get("paid_to") or monday.isoformat())
        while paid + timedelta(days=7) <= monday and p.get("weekly"):
            paid += timedelta(days=7)
            _pay(p, float(p["weekly"]), paid, "Pocket money")
            changed = True
        p["paid_to"] = paid.isoformat()
    if changed:
        ks.save(settings, POCKET, found)
    return found


def pocket_set(settings: Settings, name, amount, split) -> str:
    found = _pocket(settings)
    k = ks.child(found, name)
    weekly = round(hs.number(amount, "weekly amount", 0, 1000), 2)
    new = k not in found
    p = found.setdefault(k, {"jars": dict.fromkeys(JARS, 0.0), "history": [], "split": dict(DEFAULT_SPLIT)})
    p["weekly"] = weekly
    if split:
        p["split"] = _split(split)
    if new:
        p["paid_to"] = hs.week_start(hs.today()).isoformat()
        if weekly:
            _pay(p, weekly, hs.today(), "Pocket money")
    ks.save(settings, POCKET, found)
    c = settings.currency
    s = p["split"]
    return (f"{k} gets {ks.cash(weekly, c)} a week, paid on Mondays: {s['spend']}% spend, {s['save']}% save, "
            f"{s['give']}% give." + (" This week's is in the jars already." if new and weekly else ""))


def _jar(value, default: str = "spend") -> str:
    jar = hs.clean(value).lower() or default
    if jar not in JARS:
        raise ValueError("The jars are spend, save and give.")
    return jar


def pocket_move(settings: Settings, name, amount, jar, note, spend: bool) -> screen.Shown:
    found = _pocket(settings)
    k = ks.child(found, name, create=not spend)
    p = found.setdefault(k, {"jars": dict.fromkeys(JARS, 0.0), "history": [], "split": dict(DEFAULT_SPLIT),
                             "weekly": 0, "paid_to": hs.week_start(hs.today()).isoformat()})
    n = round(hs.number(amount, "amount", 0.01, 10000), 2)
    j = _jar(jar)
    c = settings.currency
    if spend and p["jars"][j] < n:
        raise ValueError(f"{k} only has {ks.cash(p['jars'][j], c)} in the {j} jar.")
    if not spend and not hs.clean(jar):
        _pay(p, n, hs.today(), hs.clean(note, 60) or "Money in")
        said = f"Added {ks.cash(n, c)} to {k}'s jars."
    else:
        p["jars"][j] = round(p["jars"][j] + (-n if spend else n), 2)
        p["history"] = ks.append(p["history"], {"date": hs.today().isoformat(), "jar": j, "amount": -n if spend else n,
                                                "note": hs.clean(note, 60)})
        said = (f"Took {ks.cash(n, c)} from {k}'s {j} jar; {ks.cash(p['jars'][j], c)} left." if spend else
                f"Put {ks.cash(n, c)} in {k}'s {j} jar; it has {ks.cash(p['jars'][j], c)} now.")
    ks.save(settings, POCKET, found)
    return screen.Shown(said, jars_card(settings, found, k))


def jars_card(settings: Settings, found: dict, only: str = "") -> dict:
    c = settings.currency
    kids = []
    for k, p in found.items():
        if only and k != only:
            continue
        kids.append({"child": k, "weekly": ks.cash(float(p.get("weekly") or 0), c),
                     "total": ks.cash(sum(p["jars"].values()), c),
                     "jars": [{"jar": j, "amount": p["jars"][j], "text": ks.cash(p["jars"][j], c)} for j in JARS],
                     "recent": [{"date": h["date"], "text": f"{ks.cash(h['amount'], c)} {h['jar']}"
                                 + (f" – {h['note']}" if h.get("note") else "")}
                                for h in reversed(p["history"][-5:])]})
    title = f"{only}'s money jars" if only else "Pocket money jars"
    return screen.card("kids-jars", title, f"kids-jars-{only or 'all'}", data={"children": kids})


def pocket_show(settings: Settings, name) -> screen.Shown:
    found = _pocket(settings)
    if not found:
        raise ValueError("No pocket money set up yet. Say something like 'Mia gets 3 pounds a week'.")
    k = ks.child(found, name, create=False) if hs.clean(name) else ""
    c = settings.currency
    if k:
        said = f"{k} has {ks.cash(sum(found[k]['jars'].values()), c)} altogether."
    else:
        said = "; ".join(f"{n} has {ks.cash(sum(p['jars'].values()), c)}" for n, p in found.items()) + "."
    return screen.Shown(said, jars_card(settings, found, k))


def stars_this_week(settings: Settings) -> dict:
    week = hs.week_start(hs.today())
    return {k: week_stars(rec, week) for k, rec in ks.load(settings, STARS).items() if isinstance(rec, dict)}


def pocket_totals(settings: Settings) -> dict:
    return {k: sum(p["jars"].values()) for k, p in _pocket(settings).items()}


# The tool

ACTIONS = ("star_goals", "add_star", "sticker_chart", "set_reward", "star_rewards", "claim_reward",
           "pocket_money_set", "pocket_money_add", "pocket_money_spend", "pocket_money_jars")


def tool_definitions() -> list[dict]:
    text = {"type": "string"}
    return [{
        "name": "kids_rewards",
        "description": "Children's reward sticker chart, star rewards and pocket money, per child. action: "
                       "'star_goals' set a child's chart goals (items); 'add_star' give a gold star or sticker "
                       "(goal, count, negative takes stars away, date); 'sticker_chart' pop up the week grid of "
                       "stars; 'set_reward' a reward at so many stars (reward, stars); 'star_rewards' progress "
                       "bars towards rewards; 'claim_reward' spend stars on a reward; 'pocket_money_set' weekly "
                       "pocket money (amount, split = spend/save/give percentages); 'pocket_money_add' money in, "
                       "e.g. birthday money (amount, jar optional); 'pocket_money_spend' money out of a jar "
                       "(amount, jar spend/save/give, note); 'pocket_money_jars' balances pop-up.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": list(ACTIONS)},
                "child": {"type": "string", "description": "The child's first name."},
                "items": {"type": "array", "items": text},
                "goal": text,
                "count": {"type": "integer"},
                "date": {"type": "string", "description": "YYYY-MM-DD, today, yesterday or a weekday."},
                "reward": text,
                "stars": {"type": "integer"},
                "amount": {"type": "number"},
                "split": {"type": "array", "items": {"type": "integer"},
                          "description": "Spend, save, give percentages, e.g. [60, 30, 10]."},
                "jar": {"type": "string", "enum": list(JARS)},
                "note": text,
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"kids_rewards"}


def run_tool(name: str, args: dict, settings: Settings, http=None):
    a = args.get
    kid = a("child")
    actions = {
        "star_goals": lambda: set_goals(settings, kid, a("items")),
        "add_star": lambda: add_star(settings, kid, a("goal"), a("count"), a("date")),
        "sticker_chart": lambda: star_chart(settings, kid),
        "set_reward": lambda: set_reward(settings, kid, a("reward"), a("stars")),
        "star_rewards": lambda: star_chart(settings, kid, "rewards"),
        "claim_reward": lambda: claim_reward(settings, kid, a("reward")),
        "pocket_money_set": lambda: pocket_set(settings, kid, a("amount"), a("split")),
        "pocket_money_add": lambda: pocket_move(settings, kid, a("amount"), a("jar"), a("note"), False),
        "pocket_money_spend": lambda: pocket_move(settings, kid, a("amount"), a("jar"), a("note"), True),
        "pocket_money_jars": lambda: pocket_show(settings, kid),
    }
    if a("action") not in actions:
        raise ValueError(f"I can't do {a('action')} with the kids' rewards.")
    return actions[a("action")]()
