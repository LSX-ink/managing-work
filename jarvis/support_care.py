"""Everyday support, part 3: care and safety. A "did I take it?" medicine confirmation log that checks twice, a daily
"how are you feeling?" check-in with a weekly chart for a carer, carer handover notes, the emergency card, who to
call, and the "I'm lost" card.

Everything is kept in support.json in the memory folder and never leaves the PC. This is a log only, never medical
advice. New pop-up kind: "support-big" (large lines of text), drawn by popup-support.js.
"""

from datetime import datetime, timedelta

import homestore as hs
import screen
import support_store as store
from config import Settings

screen.EXTRA_KINDS.add("support-big")
ACTIONS = ["med_add", "med_taken", "med_check", "med_today", "med_remove", "checkin", "checkin_week",
           "handover_add", "handover_show", "emergency_set", "emergency_show", "contact_set", "contact_show",
           "lost_help"]
EMERGENCY_FIELDS = {"name": "Name", "address": "Home address", "gp": "GP", "allergies": "Allergies",
                    "conditions": "Medical conditions", "emergency_contact": "Emergency contact"}
FEELINGS = {1: "very low", 2: "low", 3: "okay", 4: "good", 5: "very good"}


def big(title: str, card_id: str, lines: list[tuple[str, str]], buttons=None) -> dict:
    return screen.card("support-big", title, card_id, buttons=buttons,
                       data={"lines": [{"label": k, "value": v} for k, v in lines]})


# ---- Medicines -----------------------------------------------------------------------------------

def med_add(settings: Settings, args: dict) -> str:
    name = hs.need(args.get("name"), "medicine", 60)
    data = store.load(settings)
    key = next((k for k in data["meds"] if k.lower() == name.lower()), name)
    if key not in data["meds"] and len(data["meds"]) >= store.MAX_ITEMS:
        raise ValueError("There are too many medicines listed; remove one first.")
    data["meds"][key] = {"dose": hs.clean(args.get("dose"), 60),
                         "times": sorted(store.clock(t) for t in args.get("times") or [])}
    store.save(settings, data)
    times = data["meds"][key]["times"]
    return f"Saved {key}" + (f" at {', '.join(times)}." if times else ".")


def _taken_today(data: dict, name: str, day) -> list[str]:
    return [e["at"][11:16] for e in data["medlog"] if e["name"] == name and e["at"][:10] == day.isoformat()]


def med_taken(settings: Settings, args: dict, moment: datetime) -> str:
    data = store.load(settings)
    name = args.get("name") or ""
    key = hs.find(data["meds"], name) or hs.need(name, "medicine", 60)
    times = _taken_today(data, key, moment.date())
    allowed = max(1, len(data["meds"].get(key, {}).get("times") or []))
    if len(times) >= allowed and not args.get("confirmed"):
        return (f"Stop: {key} was already logged today at {', '.join(times)}. Tell the user not to take another "
                "just because they can't remember, and to ask their pharmacist or GP if unsure. Only if they say "
                "they really did take another, call again with confirmed true.")
    store.put(data["medlog"], {"name": key, "at": moment.strftime("%Y-%m-%d %H:%M")}, store.MAX_LOG)
    data["medlog"] = data["medlog"][-store.MAX_LOG:]
    store.save(settings, data)
    return f"Logged: {key} taken at {moment.strftime('%H:%M')}."


def med_check(settings: Settings, args: dict, moment: datetime) -> str:
    data = store.load(settings)
    key = hs.find(data["meds"], hs.need(args.get("name"), "medicine")) or hs.clean(args.get("name"), 60)
    times = _taken_today(data, key, moment.date())
    if times:
        return f"Yes, {key} was logged today at {', '.join(times)}. Don't take it again."
    return (f"Nothing is logged for {key} today. If they are not sure they took it, they should not double up; "
            "suggest checking with the pharmacist or GP.")


def med_today(settings: Settings, moment: datetime) -> screen.Shown | str:
    data = store.load(settings)
    if not data["meds"]:
        return "You haven't listed any medicines yet. Tell me the name, dose and times."
    rows = []
    for name, info in data["meds"].items():
        taken = _taken_today(data, name, moment.date())
        rows.append([name, info.get("dose") or "-", ", ".join(info.get("times") or []) or "-",
                     ", ".join(taken) if taken else "Not yet"])
    c = screen.card("table", "Medicines today", "support-meds", columns=["Medicine", "Dose", "Due", "Taken"],
                    rows=rows, buttons=[{"label": f"I took {r[0]}", "say": f"I've just taken my {r[0]}."} for r in rows[:5]])
    waiting = [r[0] for r in rows if r[3] == "Not yet"]
    return screen.Shown("Not yet taken today: " + ", ".join(waiting) + "." if waiting else "Everything is logged as taken.", c)


def med_remove(settings: Settings, args: dict) -> str:
    data = store.load(settings)
    key = store.match(data["meds"], args.get("name"), "medicine")
    if not args.get("confirmed"):
        return f"Ask the user to confirm removing {key}, then call again with confirmed true."
    del data["meds"][key]
    store.save(settings, data)
    return f"Removed {key} from the list."


# ---- Check-ins and handover ----------------------------------------------------------------------

def checkin(settings: Settings, args: dict, moment: datetime) -> str:
    score = int(hs.number(args.get("score"), "feeling score", 1, 5))
    data = store.load(settings)
    store.put(data["checkins"], {"at": moment.strftime("%Y-%m-%d %H:%M"), "score": score,
                                 "note": hs.clean(args.get("text"), 200)}, store.MAX_LOG)
    data["checkins"] = data["checkins"][-store.MAX_LOG:]
    store.save(settings, data)
    said = f"Thank you. Logged feeling {FEELINGS[score]}, {score} out of 5."
    return said + (" I'm sorry it's a hard day. Would you like a calm break, or should I note it for your carer?"
                   if score <= 2 else "")


def checkin_week(settings: Settings, moment: datetime) -> screen.Shown | str:
    entries = store.load(settings)["checkins"]
    days = [(moment.date() - timedelta(days=i)) for i in range(6, -1, -1)]
    values, seen = [], 0
    for d in days:
        scores = [e["score"] for e in entries if e["at"][:10] == d.isoformat()]
        seen += len(scores)
        values.append(round(sum(scores) / len(scores), 1) if scores else 0)
    if not seen:
        return "There are no check-ins in the last week."
    notes = [f"{e['at'][:10]}: {e['note']}" for e in entries if e["note"] and e["at"][:10] >= days[0].isoformat()]
    c = screen.card("chart", "How I felt this week", "support-week", chart={
        "type": "bar", "labels": [d.strftime("%a") for d in days], "values": values, "unit": "/5"},
        buttons=[{"label": "Handover notes", "say": "Show the carer handover notes."}])
    average = sum(v for v in values if v) / sum(1 for v in values if v)
    return screen.Shown(f"Average feeling this week is {average:.1f} out of 5 over {seen} check-ins."
                        + (f" Notes: {'; '.join(notes[-3:])}" if notes else ""), c)


def handover_add(settings: Settings, args: dict, moment: datetime) -> str:
    text = hs.need(args.get("text"), "note", 300)
    data = store.load(settings)
    store.put(data["handover"], {"at": moment.strftime("%Y-%m-%d %H:%M"), "text": text}, store.MAX_LOG)
    data["handover"] = data["handover"][-store.MAX_LOG:]
    store.save(settings, data)
    return "Added to the handover notes."


def handover_show(settings: Settings, args: dict, moment: datetime) -> screen.Shown | str:
    days = int(hs.number(args.get("days") or 3, "number of days", 1, 60))
    since = (moment - timedelta(days=days)).strftime("%Y-%m-%d %H:%M")
    notes = [n for n in store.load(settings)["handover"] if n["at"] >= since]
    if not notes:
        return f"There are no handover notes from the last {days} days."
    c = screen.card("table", "Carer handover notes", "support-handover", columns=["When", "Note"],
                    rows=[[n["at"], n["text"]] for n in reversed(notes)])
    return screen.Shown(f"{len(notes)} handover notes. The latest: {notes[-1]['text']}", c)


# ---- Emergency, who to call, lost ----------------------------------------------------------------

def emergency_set(settings: Settings, args: dict) -> str:
    data = store.load(settings)
    changed = []
    for field in EMERGENCY_FIELDS:
        if args.get(field) is not None:
            data["emergency"][field] = hs.clean(args[field], 200)
            changed.append(EMERGENCY_FIELDS[field].lower())
    if not changed:
        raise ValueError("What should I save? For example name, address, GP, allergies or emergency contact.")
    store.save(settings, data)
    return "Saved on this PC only: " + ", ".join(changed) + "."


def emergency_show(settings: Settings) -> screen.Shown:
    info = store.load(settings)["emergency"]
    lines = [(label, info[k]) for k, label in EMERGENCY_FIELDS.items() if info.get(k)]
    if not lines:
        raise ValueError("Your emergency card is empty. Tell me your name, address, GP, allergies and who to contact.")
    c = big("Emergency information", "support-emergency", lines,
            [{"label": "I'm lost", "say": "I need help, I'm lost."}])
    return screen.Shown("Your emergency information is on the screen in big print. In an emergency call 999.", c)


def contact_set(settings: Settings, args: dict) -> str:
    name = hs.need(args.get("name"), "person to call")
    phone = hs.need(args.get("phone"), "phone number", 30)
    data = store.load(settings)
    data["contact"] = {"name": name, "phone": phone, "relation": hs.clean(args.get("relation"), 60)}
    store.save(settings, data)
    return f"Saved {name}, {phone}, as the person to call."


def contact_show(settings: Settings) -> screen.Shown:
    who = store.load(settings)["contact"]
    if not who.get("phone"):
        raise ValueError("I don't have a person to call saved yet. Tell me their name and number.")
    lines = [("Call", who["name"] + (f" ({who['relation']})" if who.get("relation") else "")), ("Number", who["phone"])]
    return screen.Shown(f"You can call {who['name']} on {who['phone']}. I can't dial, but the number is on the screen.",
                        big("Who to call", "support-contact", lines))


def lost_help(settings: Settings) -> screen.Shown:
    data = store.load(settings)
    info, who = data["emergency"], data["contact"]
    lines = []
    if info.get("name"):
        lines.append(("My name is", info["name"]))
    if info.get("address"):
        lines.append(("I live at", info["address"]))
    if who.get("phone"):
        lines.append((f"Please call {who['name']}", who["phone"]))
    if not lines:
        raise ValueError("I don't have your address or a contact saved yet. Tell me and I'll keep them ready.")
    lines.append(("Emergency", "999"))
    return screen.Shown("It's alright. You are safe. Show this screen to someone, or call the number on it.",
                        big("I need help", "support-lost", lines))


def tool_definitions() -> list[dict]:
    return [{
        "name": "support_care",
        "description": "Care and safety for people who find things hard, and their carers. Logs only, never medical "
                       "advice. action: med_add (name, dose, times) / med_taken = 'I took my tablet' (checks twice "
                       "and refuses a repeat dose unless confirmed true after the user insists) / med_check = 'did "
                       "I take it?' / med_today / med_remove (confirmed only after yes); checkin = 'how are you "
                       "feeling' (score 1 to 5, text note) / checkin_week = weekly chart for a carer; handover_add "
                       "(text) / handover_show (days) = carer handover notes; emergency_set (name, address, gp, "
                       "allergies, conditions, emergency_contact) / emergency_show = big emergency card; "
                       "contact_set (name, phone, relation) / contact_show = big person to call (Alfred cannot "
                       "dial); lost_help = 'I'm lost' card with address and contact.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "name": {"type": "string", "description": "med_*: the medicine; contact_set: the person."},
                "dose": {"type": "string"},
                "times": {"type": "array", "items": {"type": "string"}, "description": "med_add: like 08:00."},
                "score": {"type": "integer", "description": "checkin: 1 (very low) to 5 (very good)."},
                "text": {"type": "string", "description": "checkin or handover_add: the note."},
                "days": {"type": "integer", "description": "handover_show: how many days back. Default 3."},
                "address": {"type": "string"},
                "gp": {"type": "string"},
                "allergies": {"type": "string"},
                "conditions": {"type": "string"},
                "emergency_contact": {"type": "string"},
                "phone": {"type": "string"},
                "relation": {"type": "string"},
                "confirmed": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"support_care"}


def run_tool(name: str, args: dict, settings: Settings, http=None, now: datetime | None = None):
    moment = store.now(now)
    action = args.get("action")
    simple = {"med_add": med_add, "med_remove": med_remove, "emergency_set": emergency_set,
              "contact_set": contact_set}
    timed = {"med_taken": med_taken, "med_check": med_check, "checkin": checkin, "handover_add": handover_add,
             "handover_show": handover_show}
    if action in simple:
        return simple[action](settings, args)
    if action in timed:
        return timed[action](settings, args, moment)
    if action == "med_today":
        return med_today(settings, moment)
    if action == "checkin_week":
        return checkin_week(settings, moment)
    if action == "emergency_show":
        return emergency_show(settings)
    if action == "contact_show":
        return contact_show(settings)
    if action == "lost_help":
        return lost_help(settings)
    raise ValueError("I can't do that one.")
