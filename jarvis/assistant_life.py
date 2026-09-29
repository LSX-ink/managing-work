"""Assistant: preferences Alfred should respect, anniversary and renewal countdowns, and things you keep forgetting.

Preferences ("I don't like calls before 10") are shown back on request and used when planning the day. The
forgetting list is nudged a couple at a time in the morning briefing; countdowns show there too when close.
"""

from datetime import timedelta

import assistant_store as st
import homestore as hs
import screen
from config import Settings

ACTIONS = ["pref_set", "pref_list", "pref_remove", "countdown_add", "countdown_list", "countdown_remove",
           "forget_add", "forget_list", "forget_remove"]
CD_KINDS = ("anniversary", "renewal", "other")


def _ask_confirm(what: str) -> str:
    return f"Ask the user to confirm removing {what}, then call again with confirmed true."


def pref_set(settings: Settings, text) -> str:
    data = st.load(settings)
    text = hs.need(text, "preference", 160)
    if any(p["text"].lower() == text.lower() for p in data["prefs"]):
        return "I already have that preference."
    st.put(data, "prefs", {"text": text, "made": hs.today().isoformat()})
    st.save(settings, data)
    return f"Noted, I'll respect that: {text}."


def pref_list(settings: Settings) -> screen.Shown | str:
    prefs = st.load(settings)["prefs"]
    if not prefs:
        return "You haven't told me any preferences yet."
    card = st.panel("Your preferences", "assistant-prefs", "What I respect",
                    [st.section("Always", [st.line(p["text"], f"Forget my preference: {p['text']}") for p in prefs])])
    return screen.Shown(f"{hs.plural(len(prefs), 'preference')} on screen: " + "; ".join(p["text"] for p in prefs), card)


def _remove(settings: Settings, key: str, field: str, text, confirmed: bool, label: str) -> str:
    data = st.load(settings)
    found = [e for e in data[key] if st.matches(e[field], hs.need(text, label, 120))]
    if not found:
        raise ValueError(f"Nothing matches {hs.clean(text)}.")
    if not confirmed:
        return _ask_confirm(f"'{found[0][field]}'")
    data[key].remove(found[0])
    st.save(settings, data)
    return f"Removed {found[0][field]}."


def countdown_add(settings: Settings, args: dict) -> str:
    data = st.load(settings)
    kind = args.get("kind") if args.get("kind") in CD_KINDS else "other"
    when = st.need_date(args.get("when"), "date")
    entry = {"label": hs.need(args.get("label"), "label", 80), "date": when.isoformat(), "kind": kind,
             "yearly": bool(args.get("yearly", kind != "other")), "cost": hs.clean(args.get("cost"), 30),
             "notice": int(hs.number(args.get("notice_days") or (30 if kind == "renewal" else 0), "notice", 0, 365))}
    data["countdowns"] = [c for c in data["countdowns"] if c["label"].lower() != entry["label"].lower()]
    st.put(data, "countdowns", entry)
    st.save(settings, data)
    left = (st.countdown_date(entry, hs.today()) - hs.today()).days
    return f"{entry['label']} saved, {hs.plural(left, 'day')} to go."


def countdown_list(settings: Settings) -> screen.Shown | str:
    data, today = st.load(settings), hs.today()
    rows = st.countdown_rows(data, today)
    if not rows:
        return "No anniversaries or renewals saved."
    table = []
    for when, c in rows:
        act = ""
        if c["kind"] == "renewal" and c["notice"]:
            act = f"compare deals from {hs.spoken(when - timedelta(days=c['notice']))}"
        table.append([c["label"], c["kind"], hs.spoken(when), st.when_words(when.isoformat(), today), c["cost"], act])
    card = screen.card("table", "Anniversaries and renewals", "assistant-countdowns",
                       columns=["What", "Kind", "Date", "In", "Cost", "Note"], rows=table)
    first = rows[0]
    return screen.Shown(f"{hs.plural(len(rows), 'countdown')} on screen. Next: {first[1]['label']} "
                        f"{st.when_words(first[0].isoformat(), today)}.", card)


def forget_add(settings: Settings, text) -> str:
    data = st.load(settings)
    text = hs.need(text, "thing", 140)
    if any(f["text"].lower() == text.lower() for f in data["forgets"]):
        return "It's already on your list of things to remember."
    st.put(data, "forgets", {"text": text, "made": hs.today().isoformat()})
    st.save(settings, data)
    return f"I'll nudge you about it in the morning: {text}."


def forget_list(settings: Settings) -> screen.Shown | str:
    data, today = st.load(settings), hs.today()
    if not data["forgets"]:
        return "Your list of things you keep forgetting is empty."
    card = st.panel("Things I keep forgetting", "assistant-forgets", f"{len(data['forgets'])} nudges",
                    [st.section("Today's nudges", st.nudges(data, today), "alert"),
                     st.section("All of them", [f["text"] for f in data["forgets"]])])
    return screen.Shown(f"{hs.plural(len(data['forgets']), 'thing')} on screen. Today: " + "; ".join(st.nudges(data, today)), card)


def tool_definitions() -> list[dict]:
    text = {"type": "string"}
    return [{
        "name": "assistant_life",
        "description": "Personal preferences, countdowns and memory nudges. pref_set: 'I don't like calls before 10' "
                       "or 'never book me meetings on Fridays' (kept and used when planning). pref_list / "
                       "pref_remove. countdown_add: an anniversary or renewal ('car insurance renews on "
                       "2026-11-20, 480 pounds, 30 days notice'); countdown_list; countdown_remove. forget_add: "
                       "'things I keep forgetting: taking my keys' (nudged in the morning briefing); forget_list; "
                       "forget_remove. Removing needs confirmed true, only after the user says yes.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "text": {**text, "description": "The preference or the thing to remember (or its words, to remove)."},
                "label": {**text, "description": "countdown: e.g. 'Wedding anniversary' or 'Car insurance'."},
                "when": {**text, "description": "countdown: date YYYY-MM-DD (the first or next one)."},
                "kind": {"type": "string", "enum": list(CD_KINDS)},
                "yearly": {"type": "boolean", "description": "Comes round every year. Default true except for 'other'."},
                "cost": {**text, "description": "Renewal cost, e.g. '480 GBP'."},
                "notice_days": {"type": "integer", "description": "Renewal: start reminding this many days ahead. Default 30."},
                "confirmed": {"type": "boolean", "description": "Set only after the user confirms a removal."},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"assistant_life"}


def run_tool(name: str, args: dict, settings: Settings, http=None):
    action, text, sure = args.get("action"), args.get("text"), bool(args.get("confirmed"))
    if action == "pref_set":
        return pref_set(settings, text)
    if action == "pref_list":
        return pref_list(settings)
    if action == "pref_remove":
        return _remove(settings, "prefs", "text", text, sure, "preference")
    if action == "countdown_add":
        return countdown_add(settings, args)
    if action == "countdown_list":
        return countdown_list(settings)
    if action == "countdown_remove":
        return _remove(settings, "countdowns", "label", args.get("label") or text, sure, "countdown")
    if action == "forget_add":
        return forget_add(settings, text)
    if action == "forget_list":
        return forget_list(settings)
    if action == "forget_remove":
        return _remove(settings, "forgets", "text", text, sure, "thing")
    raise ValueError(f"Unknown action {action}.")
