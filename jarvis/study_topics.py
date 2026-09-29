"""Study topics: a checklist per subject with red/amber/green confidence, a heatmap of every subject, what to
revise next, topic review dates that follow your confidence, and a formula sheet per subject shown big.

Confidence is never colour alone: every topic also shows R, A or G and its word. Pop-ups "study-heatmap" and
"study-formulas" are drawn by frontend/popup-study.js. Everything is in study.json.
"""

from datetime import date

import screen
import study_store as st
from config import Settings

screen.EXTRA_KINDS.update({"study-heatmap", "study-formulas"})
MAX_TOPICS = 200
MAX_FORMULAS = 60
CYCLE = {"": "red", "red": "amber", "amber": "green", "green": "red"}


def _topics(data: dict, subject: str) -> list[dict]:
    return data["topics"].setdefault(subject, [])


def _topic(data: dict, subject: str, name) -> dict:
    found = st.gs.find(_topics(data, subject), "name", name)
    if not found:
        raise ValueError(f"I can't find that topic in {subject}.")
    return found


def add_topics(settings: Settings, args: dict) -> str:
    data = st.load(settings)
    subject = st.ensure_course(data, args.get("subject"))["name"]
    names = st.named_list(args.get("topics") or args.get("topic"))
    if not names:
        raise ValueError("Which topics?")
    topics = _topics(data, subject)
    added = 0
    for name in names:
        if not any(t["name"].lower() == name.lower() for t in topics):
            if len(topics) >= MAX_TOPICS:
                raise ValueError("That's a lot of topics for one subject.")
            topics.append({"name": name, "rag": "", "rated": "", "next": ""})
            added += 1
    st.save(settings, data)
    return f"Added {st.plural(added, 'topic')} to {subject}, {len(topics)} in all."


def rate(settings: Settings, args: dict, today: date) -> screen.Shown:
    data = st.load(settings)
    subject = st.course(data, args.get("subject"))["name"]
    rag = st.confidence(args.get("confidence"))
    topic = _topic(data, subject, args.get("topic"))
    topic.update(rag=rag, rated=today.isoformat(), next=st.review_next(rag, today))
    st.save(settings, data)
    return _checklist_card(data, subject, f"{topic['name']} is now {st.RAG[rag].lower()}. I'll bring it back "
                           f"{st.days_text(st.REVIEW_DAYS[rag])} from now.")


def _checklist_card(data: dict, subject: str, said: str) -> screen.Shown:
    topics = _topics(data, subject)
    if not topics:
        raise ValueError(f"No topics for {subject} yet. Tell me the topics and I'll add them.")
    items = [{"label": f"[{st.RAG_LETTER[t['rag']]}] {t['name']}: {st.RAG.get(t['rag'], 'not rated')}",
              "done": t["rag"] == "green",
              "say": f"Set {t['name']} in {subject} to {CYCLE[t['rag']]}."}
             for t in topics]
    counts = {r: sum(1 for t in topics if t["rag"] == r) for r in st.RAG}
    return screen.Shown(said or f"{subject}: {counts['green']} green, {counts['amber']} amber, {counts['red']} red.",
                        screen.card("list", f"{subject} topics", f"study-topics-{subject}", items=items,
                                    buttons=[{"label": "Heatmap", "say": "Show my topic heatmap."},
                                             {"label": "What next?", "say": f"What should I revise next in {subject}?"}]))


def checklist(settings: Settings, subject) -> screen.Shown:
    data = st.load(settings)
    name = st.course(data, subject)["name"]
    return _checklist_card(data, name, "")


def heatmap(settings: Settings, subject) -> screen.Shown:
    data = st.load(settings)
    chosen = [st.course(data, subject)] if st.clean(subject) else data["courses"]
    groups = [{"name": c["name"], "topics": [{"name": t["name"], "rag": t["rag"]} for t in _topics(data, c["name"])]}
              for c in chosen if _topics(data, c["name"])]
    if not groups:
        raise ValueError("No topics yet. Give me a subject and its topics first.")
    total = [t for g in groups for t in g["topics"]]
    green = sum(1 for t in total if t["rag"] == "green")
    said = f"{green} of {len(total)} topics are green."
    return screen.Shown(said, screen.card("study-heatmap", "Topic confidence", "study-heatmap", data={"courses": groups}))


def weakest(settings: Settings, args: dict, today: date) -> screen.Shown:
    data = st.load(settings)
    chosen = [st.course(data, args["subject"])] if st.clean(args.get("subject")) else data["courses"]
    order = {"red": 0, "amber": 1, "": 2}
    picks = [(order[t["rag"]], t["rated"] or "", c["name"], t["name"]) for c in chosen for t in _topics(data, c["name"])
             if t["rag"] != "green"]
    picks.sort()
    if not picks:
        raise ValueError("Nothing to work on: no topics yet, or they're all green.")
    items = [{"label": f"[{st.RAG_LETTER[['red', 'amber', ''][p[0]]]}] {p[3]} ({p[2]})",
              "say": f"Start a pomodoro for {p[2]} on {p[3]}."} for p in picks[:8]]
    return screen.Shown(f"Start with {picks[0][3]} in {picks[0][2]}.", screen.card(
        "list", "Revise next", "study-weakest", items=items))


def review_due(settings: Settings, today: date) -> screen.Shown:
    data = st.load(settings)
    due = [(t["next"], c["name"], t["name"], t["rag"]) for c in data["courses"] for t in _topics(data, c["name"])
           if t["next"] and t["next"] <= today.isoformat()]
    if not due:
        return screen.Shown("Nothing is due for review today.", screen.card("list", "Topics to review", "study-review", items=[]))
    due.sort()
    items = [{"label": f"[{st.RAG_LETTER[r]}] {t} ({c})", "say": f"Quiz me on {t} in {c}."} for _, c, t, r in due[:20]]
    return screen.Shown(f"{st.plural(len(due), 'topic')} due for review.", screen.card(
        "list", "Topics to review", "study-review", items=items))


def remove_topic(settings: Settings, args: dict) -> str:
    data = st.load(settings)
    subject = st.course(data, args.get("subject"))["name"]
    topic = _topic(data, subject, args.get("topic"))
    if not args.get("confirmed"):
        return f"Ask the user to confirm removing {topic['name']} from {subject}, then call again with confirmed true."
    _topics(data, subject).remove(topic)
    st.save(settings, data)
    return f"Removed {topic['name']}."


# ---- formula sheet --------------------------------------------------------------------------------------

def add_formula(settings: Settings, args: dict) -> str:
    data = st.load(settings)
    subject = st.ensure_course(data, args.get("subject"))["name"]
    name = st.need(args.get("name"), "formula name", 80)
    formula = st.need(args.get("formula"), "formula", 300)
    sheet = data["formulas"].setdefault(subject, [])
    found = next((f for f in sheet if f["name"].lower() == name.lower()), None)
    if found:
        found["formula"] = formula
    elif len(sheet) >= MAX_FORMULAS:
        raise ValueError("That's a lot of formulas for one sheet.")
    else:
        sheet.append({"name": name, "formula": formula})
    st.save(settings, data)
    return f"Saved {name} on your {subject} formula sheet."


def formula_sheet(settings: Settings, subject) -> screen.Shown:
    data = st.load(settings)
    name = st.course(data, subject)["name"]
    sheet = data["formulas"].get(name) or []
    if not sheet:
        raise ValueError(f"Your {name} formula sheet is empty. Tell me a formula to add.")
    return screen.Shown(f"Your {name} formula sheet is up, {st.plural(len(sheet), 'formula')}.", screen.card(
        "study-formulas", f"{name} formulas", f"study-formulas-{name}", data={"course": name, "items": sheet}))


def remove_formula(settings: Settings, args: dict) -> str:
    data = st.load(settings)
    subject = st.course(data, args.get("subject"))["name"]
    sheet = data["formulas"].get(subject) or []
    found = st.gs.find(sheet, "name", args.get("name"))
    if not found:
        raise ValueError("I can't find that formula.")
    if not args.get("confirmed"):
        return f"Ask the user to confirm removing {found['name']}, then call again with confirmed true."
    sheet.remove(found)
    st.save(settings, data)
    return f"Removed {found['name']}."


ACTIONS = ["add_topics", "rate", "checklist", "heatmap", "revise_next", "review_due", "remove_topic",
           "add_formula", "formula_sheet", "remove_formula"]


def tool_definitions() -> list[dict]:
    return [{
        "name": "study_topics",
        "description": "Revision topics and formulas per subject. add_topics (subject, topics list); rate a topic "
                       "red, amber or green confidence (subject, topic, confidence); checklist of a subject's topics "
                       "with R/A/G labels; heatmap of every subject as a pop-up; revise_next gives the weakest "
                       "topics; review_due gives topics due back; remove_topic (confirmed only after the user says "
                       "yes). Formula sheet: add_formula (subject, name, formula), formula_sheet shows it big, "
                       "remove_formula (confirmed only after yes).",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "subject": {"type": "string"},
                "topics": {"type": "array", "items": {"type": "string"}},
                "topic": {"type": "string"},
                "confidence": {"type": "string", "enum": ["red", "amber", "green"]},
                "name": {"type": "string", "description": "Formula name, e.g. Area of a circle."},
                "formula": {"type": "string", "description": "e.g. A = pi r^2"},
                "confirmed": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"study_topics"}


def run_tool(name: str, args: dict, settings: Settings, http=None, today: date | None = None):
    today = today or st.today()
    action = args.get("action")
    if action == "add_topics":
        return add_topics(settings, args)
    if action == "rate":
        return rate(settings, args, today)
    if action == "checklist":
        return checklist(settings, args.get("subject"))
    if action == "heatmap":
        return heatmap(settings, args.get("subject"))
    if action == "revise_next":
        return weakest(settings, args, today)
    if action == "review_due":
        return review_due(settings, today)
    if action == "remove_topic":
        return remove_topic(settings, args)
    if action == "add_formula":
        return add_formula(settings, args)
    if action == "formula_sheet":
        return formula_sheet(settings, args.get("subject"))
    if action == "remove_formula":
        return remove_formula(settings, args)
    raise ValueError(f"Unknown study topics action: {action}")
