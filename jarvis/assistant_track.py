"""Assistant: things to chase and remember. Follow-ups, a waiting-for list, delegated jobs, promises made to
people (read from the people notebook) and a decisions log. Lists pop up as assistant-briefing windows.
"""

import uuid
from datetime import timedelta

import assistant_store as st
import homestore as hs
import reminders
import screen
from config import Settings

ACTIONS = ["followup_add", "waiting_add", "delegate_add", "track_list", "track_done", "commitments",
           "decision_log", "decisions_show"]
ADD = {"followup_add": "followup", "waiting_add": "waiting", "delegate_add": "delegated"}
SAY = {"followup": "Chase", "waiting": "Waiting for", "delegated": "Delegated"}


def _remind(settings: Settings, item: dict) -> str:
    """A 9am reminder on the due day, when that is still ahead."""
    try:
        reminders.add(settings, f"{item['by']} 09:00", f"{SAY[item['kind']]}: {item['what']}"
                      + (f" ({item['who']})" if item["who"] else ""), now=hs.now())
    except ValueError:
        return ""
    return " I'll remind you that morning."


def add(settings: Settings, kind: str, args: dict) -> str:
    data = st.load(settings)
    today = hs.today()
    by = st.upcoming_day(args["by"], today).isoformat() if args.get("by") else \
        (today + timedelta(days=3)).isoformat() if kind == "followup" else ""
    item = st.put(data, "items", {"id": uuid.uuid4().hex[:6], "kind": kind, "what": hs.need(args.get("what"), "item", 140),
                                  "who": hs.clean(args.get("who"), 60), "by": by, "made": today.isoformat(), "done": ""})
    st.save(settings, data)
    extra = _remind(settings, item) if by and args.get("remind", True) else ""
    label = {"followup": "Follow-up", "waiting": "Waiting for", "delegated": "Delegated"}[kind]
    return f"{label} saved: {st.item_line(item, today)}.{extra}"


def _sections(settings: Settings, data: dict, kind: str | None, today) -> list[dict]:
    out = []
    for k in ([kind] if kind in st.KINDS else st.KINDS):
        rows = sorted(st.open_items(data, k), key=lambda i: i["by"] or "9999")
        out.append(st.section(st.KIND_NAMES[k], [st.line(st.item_line(i, today), f"Tick off {SAY[k].lower()}: {i['what']}")
                                                 for i in rows], "alert" if any(i["by"] and i["by"] < today.isoformat() for i in rows) else ""))
    if kind in (None, "commitment"):
        out.append(st.section(st.KIND_NAMES["commitment"], [_promise_line(p, today) for p in st.promises(settings)]))
    return out


def _promise_line(p: dict, today) -> str:
    due = f", {st.when_words(p['due'], today)}" if p.get("due") else ""
    return f"To {p['person']}: {p['what']}{due}"


def listing(settings: Settings, kind: str | None = None, due_only: bool = False) -> screen.Shown | str:
    data, today = st.load(settings), hs.today()
    if due_only:
        rows = st.due_items(data, today)
        if not rows:
            return "Nothing to chase today."
        card = st.panel("Due to chase", "assistant-chase", f"{len(rows)} to chase",
                        [st.section("Due or overdue", [st.line(st.item_line(i, today), f"Tick off {SAY[i['kind']].lower()}: {i['what']}")
                                                       for i in rows], "alert")])
        return screen.Shown(f"{hs.plural(len(rows), 'thing')} due to chase (on screen): " + "; ".join(i["what"] for i in rows), card)
    sections = _sections(settings, data, kind, today)
    total = sum(len(s["lines"]) for s in sections)
    if not total:
        return "Nothing is being chased, waited for or delegated."
    overdue = sum(bool(i["by"]) and i["by"] < today.isoformat() for i in st.open_items(data))
    title = st.KIND_NAMES.get(kind or "", "Follow-ups and waiting")
    card = st.panel(title, f"assistant-track-{kind or 'all'}", f"{total} open" + (f", {overdue} overdue" if overdue else ""), sections)
    return screen.Shown(f"{hs.plural(total, 'open item')} on screen" + (f", {overdue} overdue." if overdue else "."), card)


def done(settings: Settings, what) -> str:
    text = hs.need(what, "item", 140)
    data, today = st.load(settings), hs.today()
    found = [i for i in st.open_items(data) if st.matches(f"{i['what']} {i['who']}", text)]
    if found:
        found[0]["done"] = today.isoformat()
        st.save(settings, data)
        return f"Ticked off: {found[0]['what']}. {hs.plural(len(st.open_items(data)), 'item')} still open."
    people = hs.load(settings, "people-promises.json", [])
    promise = next((p for p in people if isinstance(p, dict) and not p.get("done") and st.matches(f"{p.get('what')} {p.get('person')}", text)), None)
    if promise:
        promise["done"] = today.isoformat()
        hs.save(settings, "people-promises.json", people)
        return f"Ticked off your promise to {promise['person']}: {promise['what']}."
    raise ValueError(f"Nothing open matches {text}.")


def decision_log(settings: Settings, text, why) -> str:
    data = st.load(settings)
    entry = st.put(data, "decisions", {"date": hs.today().isoformat(), "text": hs.need(text, "decision", 200),
                                       "why": hs.clean(why, 200)})
    st.save(settings, data)
    return f"Logged the decision: {entry['text']}."


def decisions_show(settings: Settings, query) -> screen.Shown | str:
    data = st.load(settings)
    rows = [d for d in reversed(data["decisions"]) if not hs.clean(query) or st.matches(f"{d['text']} {d.get('why', '')}", query)]
    if not rows:
        return "No decisions logged" + (f" about {hs.clean(query)}." if hs.clean(query) else " yet.")
    card = screen.card("table", "Decisions log", "assistant-decisions", columns=["Date", "Decision", "Why"],
                       rows=[[d["date"], d["text"], d.get("why", "")] for d in rows[:60]])
    return screen.Shown(f"{hs.plural(len(rows), 'decision')} on screen. Latest: {rows[0]['text']}.", card)


def tool_definitions() -> list[dict]:
    text = {"type": "string"}
    return [{
        "name": "assistant_track",
        "description": "Things to chase and remember. followup_add: 'remind me to chase Sam if he hasn't replied by "
                       "Friday' (what, who, by; adds a 9am reminder that day). waiting_add: 'I'm waiting for the "
                       "plumber's quote'. delegate_add: 'I asked Priya to book the venue'. track_list: the "
                       "follow-up, waiting-for and delegated lists (kind optional; due_only for what to chase "
                       "today). track_done: tick one off (words from it; also ticks a promise to someone). "
                       "commitments: what I promised people. decision_log: 'note that we decided to go with "
                       "option B' (text, why). decisions_show: the decisions log, optionally about a word.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "what": {**text, "description": "The thing to chase, wait for or delegate; or the item to tick off."},
                "who": {**text, "description": "The person involved."},
                "by": {**text, "description": "Due date YYYY-MM-DD, 'tomorrow' or a weekday name."},
                "remind": {"type": "boolean", "description": "Add a reminder on the due day. Default true."},
                "kind": {"type": "string", "enum": [*st.KINDS, "commitment"], "description": "track_list: one list only."},
                "due_only": {"type": "boolean", "description": "track_list: only what is due or overdue."},
                "text": {**text, "description": "decision_log: the decision."},
                "why": {**text, "description": "decision_log: the reason."},
                "query": {**text, "description": "decisions_show: a word to look for."},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"assistant_track"}


def run_tool(name: str, args: dict, settings: Settings, http=None):
    action = args.get("action")
    if action in ADD:
        return add(settings, ADD[action], args)
    if action == "track_list":
        return listing(settings, args.get("kind"), bool(args.get("due_only")))
    if action == "commitments":
        return listing(settings, "commitment")
    if action == "track_done":
        return done(settings, args.get("what"))
    if action == "decision_log":
        return decision_log(settings, args.get("text") or args.get("what"), args.get("why"))
    if action == "decisions_show":
        return decisions_show(settings, args.get("query"))
    raise ValueError(f"Unknown action {action}.")
