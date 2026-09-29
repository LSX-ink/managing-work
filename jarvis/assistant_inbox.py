"""Assistant: a quick-capture inbox to sort later, errands batched by place, and a list of wins.

Capture uses the same Inbox.md as "note that...". Sorting moves a note into the to-do list, a reminder, an
errand or a notes file (Sorted notes.md in the Ideas folder), and takes it out of the inbox.
"""

import re
from datetime import timedelta

import assistant_store as st
import homestore as hs
import memory
import reminders
import routines_life
import screen
import todo
from config import Settings

ACTIONS = ["capture", "inbox_show", "inbox_sort", "errand_add", "errands_show", "errand_done", "win_add", "wins_show"]
DESTINATIONS = ("todo", "reminder", "errand", "note")
STAMP = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2} ")
ERRAND_WORDS = ("buy", "pick up", "collect", "return", "post ", "drop off", "get some", "get a ", "shop")
REMIND_WORDS = ("remind", "tomorrow", "tonight", " at ", "monday", "tuesday", "wednesday", "thursday", "friday",
                "saturday", "sunday", "next week")
TODO_WORDS = ("call", "email", "text", "book", "pay", "fix", "send", "finish", "renew", "cancel", "sort", "ring")


def _notes(settings: Settings) -> list[str]:
    return [STAMP.sub("", line) for line in routines_life._inbox_lines(settings)]


def suggest(note: str) -> str:
    low = f" {note.lower()}"
    for words, dest in ((ERRAND_WORDS, "errand"), (REMIND_WORDS, "reminder"), (TODO_WORDS, "todo")):
        if any(w in low for w in words):
            return dest
    return "note"


def capture(settings: Settings, text) -> str:
    return routines_life.inbox_add(settings, text)


def inbox_show(settings: Settings) -> screen.Shown | str:
    notes = _notes(settings)
    if not notes:
        return "The inbox is empty."
    lines = [st.line(f"{n}. {note}  (looks like: {suggest(note)})", f"Sort inbox note {n} ({note}) into my {suggest(note)}.")
             for n, note in enumerate(notes, 1)]
    card = st.panel("Inbox to sort", "assistant-inbox", f"{hs.plural(len(notes), 'note')} waiting",
                    [st.section("Click one to sort it", lines)],
                    buttons=[{"label": "Sort them all", "say": "Sort everything in my inbox where it belongs."}])
    return screen.Shown(f"{hs.plural(len(notes), 'note')} in the inbox (on screen):\n" + "\n".join(notes), card)


def _pick(settings: Settings, item) -> tuple[int, str]:
    notes = _notes(settings)
    text = hs.need(item, "inbox note", 200)
    if text.isdigit() and 1 <= int(text) <= len(notes):
        return int(text) - 1, notes[int(text) - 1]
    found = [(n, note) for n, note in enumerate(notes) if st.matches(note, text)]
    if not found:
        raise ValueError(f"No inbox note matches {text}.")
    return found[0]


def _drop(settings: Settings, index: int) -> None:
    lines = routines_life._inbox_lines(settings)
    del lines[index]
    routines_life.inbox_path(settings).write_text("# Inbox\n\n" + "".join(f"- {line}\n" for line in lines), encoding="utf-8")


def inbox_sort(settings: Settings, item, to, when, place) -> str:
    index, note = _pick(settings, item)
    dest = to if to in DESTINATIONS else suggest(note)
    if dest == "reminder":
        said = reminders.add(settings, hs.need(when, "time for the reminder, 'YYYY-MM-DD HH:MM'", 20), note)
    elif dest == "todo":
        said = todo.add(settings, [note])
    elif dest == "errand":
        said = errand_add(settings, note, place)
    else:
        path = memory.folder(settings, 0) / "Sorted notes.md"
        old = path.read_text(encoding="utf-8") if path.exists() else "# Sorted notes\n\n"
        path.write_text(f"{old}- {hs.today()} {note}\n", encoding="utf-8")
        said = "Saved it in Sorted notes in the Ideas folder."
    _drop(settings, index)
    return f"Sorted '{note}' into your {dest}s. {said} {hs.plural(len(_notes(settings)), 'note')} left in the inbox."


def errand_add(settings: Settings, what, place) -> str:
    data = st.load(settings)
    entry = st.put(data, "errands", {"what": hs.need(what, "errand", 120), "place": hs.clean(place, 60) or "Anywhere",
                                     "made": hs.today().isoformat()})
    st.save(settings, data)
    return f"Errand saved for {entry['place']}: {entry['what']}."


def errands_show(settings: Settings) -> screen.Shown | str:
    data = st.load(settings)
    if not data["errands"]:
        return "No errands saved."
    places: dict[str, list[dict]] = {}
    for e in data["errands"]:
        places.setdefault(e["place"], []).append(e)
    order = sorted(places, key=lambda p: (p == "Anywhere", -len(places[p]), p))
    sections = [st.section(f"{p} ({len(places[p])})", [st.line(e["what"], f"Tick off errand: {e['what']}") for e in places[p]])
                for p in order]
    stops = [p for p in order if p != "Anywhere"]
    card = st.panel("Errands by place", "assistant-errands", f"{len(data['errands'])} errands, {len(stops)} stops", sections)
    return screen.Shown(f"{hs.plural(len(data['errands']), 'errand')} in {hs.plural(len(stops), 'stop')} (on screen). "
                        f"Biggest batch: {order[0]}.", card)


def errand_done(settings: Settings, what) -> str:
    data = st.load(settings)
    text = hs.need(what, "errand", 120)
    found = [e for e in data["errands"] if st.matches(e["what"], text)]
    if not found:
        raise ValueError(f"No errand matches {text}.")
    data["errands"].remove(found[0])
    st.save(settings, data)
    return f"Done: {found[0]['what']}. {hs.plural(len(data['errands']), 'errand')} left."


def win_add(settings: Settings, text) -> str:
    data = st.load(settings)
    entry = st.put(data, "wins", {"date": hs.today().isoformat(), "text": hs.need(text, "win", 160)})
    st.save(settings, data)
    return f"Win logged: {entry['text']}. Well done."


def wins_show(settings: Settings, period) -> screen.Shown | str:
    data, today = st.load(settings), hs.today()
    days = 30 if period == "month" else 7
    start = (today - timedelta(days=days - 1)).isoformat()
    wins = [w["text"] for w in data["wins"] if w["date"] >= start]
    closed = [i["what"] for i in data["items"] if i.get("done") and i["done"] >= start]
    focus = sum(f.get("minutes", 0) for f in data["focuslog"] if f["date"] >= start)
    if not (wins or closed or focus):
        return "No wins logged yet. Tell me one and I'll keep it."
    sections = [st.section("Wins", wins), st.section("Chased, waited for and delegated: closed", closed),
                st.section("Focus", [f"{focus} minutes of focus time"] if focus else [])]
    head = f"Your wins this {'month' if days == 30 else 'week'}"
    card = st.panel(head, f"assistant-wins-{days}", f"{len(wins) + len(closed)} things to be proud of", sections)
    return screen.Shown(f"{head} (on screen): {len(wins)} logged, {len(closed)} items closed, {focus} focus minutes.", card)


def tool_definitions() -> list[dict]:
    text = {"type": "string"}
    return [{
        "name": "assistant_inbox",
        "description": "Quick capture, errands and wins. capture: 'capture: ring the dentist' (saved to the inbox to "
                       "sort later). inbox_show: the inbox with a suggested place for each note. inbox_sort: move "
                       "an inbox note (number or words) into a to-do, reminder (give when), errand (place) or "
                       "note. errand_add / errands_show / errand_done: errands batched by place ('pick up parcel "
                       "at the post office'). win_add / wins_show: 'log a win: finished the report', the "
                       "end-of-week wins list (period week or month).",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "text": {**text, "description": "capture or win_add: the words. errand_add / errand_done: the errand."},
                "item": {**text, "description": "inbox_sort: the note's number or words from it."},
                "to": {"type": "string", "enum": list(DESTINATIONS), "description": "inbox_sort: where it goes. Default: best guess."},
                "when": {**text, "description": "inbox_sort to a reminder: local 'YYYY-MM-DD HH:MM'."},
                "place": {**text, "description": "Where the errand is done, e.g. 'Boots' or 'town'."},
                "period": {"type": "string", "enum": ["week", "month"]},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"assistant_inbox"}


def run_tool(name: str, args: dict, settings: Settings, http=None):
    action, text = args.get("action"), args.get("text")
    if action == "capture":
        return capture(settings, text)
    if action == "inbox_show":
        return inbox_show(settings)
    if action == "inbox_sort":
        return inbox_sort(settings, args.get("item"), args.get("to"), args.get("when"), args.get("place"))
    if action == "errand_add":
        return errand_add(settings, text, args.get("place"))
    if action == "errands_show":
        return errands_show(settings)
    if action == "errand_done":
        return errand_done(settings, text)
    if action == "win_add":
        return win_add(settings, text)
    if action == "wins_show":
        return wins_show(settings, args.get("period"))
    raise ValueError(f"Unknown action {action}.")
