"""Study writing and recall: an essay plan scaffold for Alfred to fill, Harvard and APA citations built from the
fields you give (no network), "quiz me on my notes" from a note in the memory folders, and study break ideas.
"""

import random
import re
from pathlib import Path

import screen
import study_store as st
from config import Settings

MAX_NOTES = 12000
ESSAYS = {
    "argue": ["Introduction: hook, define key terms, state your thesis",
              "Point 1 for your argument: point, evidence, explain, link back",
              "Point 2 for your argument: point, evidence, explain, link back",
              "Counter-argument and your response to it",
              "Conclusion: restate the thesis, sum up, final thought"],
    "compare": ["Introduction: what you compare and why it matters",
                "Similarity: point, evidence from both",
                "Difference 1: point, evidence from both",
                "Difference 2: point, evidence from both",
                "Conclusion: which matters more and your judgement"],
    "analyse": ["Introduction: the text, the question, your line of argument",
                "Paragraph 1: quote, technique, effect on the reader, context",
                "Paragraph 2: quote, technique, effect on the reader, context",
                "Paragraph 3: quote, technique, effect on the reader, context",
                "Conclusion: overall meaning and how it answers the question"],
    "evaluate": ["Introduction: what is being judged and the criteria",
                 "Strengths: evidence and explanation",
                 "Weaknesses or limits: evidence and explanation",
                 "Weighing up: which side is stronger and why",
                 "Conclusion: a clear, justified judgement"],
}
BREAKS = {
    5: ["Stand up and stretch your neck, shoulders and back", "Drink a full glass of water",
        "Look out of a window at something far away for a minute", "Walk to another room and back"],
    10: ["Step outside for fresh air", "Make a cup of tea and drink it away from your desk",
         "Do a quick tidy of your desk", "Eat a piece of fruit or a snack"],
    20: ["Go for a short walk around the block", "Call or message a friend", "Cook or eat something proper",
         "Have a proper rest with your eyes closed"],
}


def essay_plan(args: dict) -> str:
    question = st.need(args.get("question") or args.get("title"), "essay question", 300)
    kind = st.clean(args.get("essay_type") or "argue", 20).lower()
    if kind not in ESSAYS:
        kind = "argue"
    words = int(args.get("word_count") or 1000)
    share = max(50, round(words / (len(ESSAYS[kind]) + 0.5) / 10) * 10)
    subject = st.clean(args.get("subject"), 60)
    lines = "\n".join(f"{i}. {s} (about {share} words)" for i, s in enumerate(ESSAYS[kind], 1))
    return (f"Essay plan scaffold ({kind}, about {words} words{f', {subject}' if subject else ''}) for: {question}\n{lines}\n\n"
            "INSTRUCTION for Alfred: fill in every numbered section with two or three specific, short bullet points "
            "for this exact question, then show the finished plan on the screen as a list with show_on_screen. Do not "
            "write the essay itself; the student writes it. Say one short sentence aloud.")


# ---- citations -----------------------------------------------------------------------------------------

def _authors(text) -> list[tuple[str, str]]:
    """(surname, given names) for each author from 'Smith, John; Ann Jones' or 'John Smith and Ann Jones'."""
    people = [p.strip() for p in re.split(r";|\band\b|&", str(text or "")) if p.strip()]
    out = []
    for person in people[:20]:
        if "," in person:
            surname, given = [x.strip() for x in person.split(",", 1)]
        else:
            *first, surname = person.split() or [""]
            given = " ".join(first)
        out.append((surname, given))
    return out


def _initials(given: str, apa: bool) -> str:
    parts = [p[0].upper() for p in re.split(r"[\s.\-]+", given) if p]
    return (" " if apa else "").join(f"{p}." for p in parts)


def _names(authors: list[tuple[str, str]], style: str) -> str:
    def one(a):
        return f"{a[0]}, {_initials(a[1], style == 'apa')}".rstrip(", ")
    names = [one(a) for a in authors]
    if style == "apa":
        return names[0] if len(names) == 1 else ", ".join(names[:-1]) + ", & " + names[-1]
    if len(names) > 3:
        return f"{names[0]} et al."
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


def format_citation(style: str, source: str, f: dict) -> str:
    style = "apa" if style.lower().startswith("apa") else "harvard"
    authors = _authors(f.get("authors"))
    title, year = st.need(f.get("title"), "title", 300), st.clean(f.get("year"), 10) or "n.d."
    who = _names(authors, style) if authors else ""
    place = st.clean(f.get("place"), 60)
    publisher = st.clean(f.get("publisher"), 100)
    url = st.clean(f.get("url"), 300)
    accessed = st.clean(f.get("accessed"), 40)
    journal, volume, issue, pages = (st.clean(f.get(k), 100) for k in ("journal", "volume", "issue", "pages"))
    edition = st.clean(f.get("edition"), 30)
    vol = f"{volume}{f'({issue})' if issue else ''}"
    if style == "apa":
        head = f"{who} ({year}). " if who else f"{title}. ({year}). "
        body = "" if not who else f"{title}. "
        if source == "journal":
            return f"{head}{body}{journal}, {vol}{f', {pages}' if pages else ''}.{f' {url}' if url else ''}".replace(" ,", ",")
        if source == "website":
            return f"{head}{body}{url}".strip()
        return f"{head}{body}{f'({edition} ed.). ' if edition else ''}{publisher}.".strip() + (f" {url}" if url else "")
    head = f"{who} ({year}) " if who else f"{title} ({year}) "
    body = "" if not who else (f"'{title}'" if source == "journal" else f"{title}") + ("," if source == "journal" else ".")
    if source == "journal":
        return f"{head}{body} {journal}, {vol}{f', pp. {pages}' if pages else ''}.{f' Available at: {url}' if url else ''}"
    if source == "website":
        return f"{head}{body} Available at: {url}{f' (Accessed: {accessed})' if accessed else ''}.".replace("  ", " ")
    return f"{head}{body}{f' {edition} edn.' if edition else ''} {place + ': ' if place else ''}{publisher}.".replace("  ", " ")


def cite(args: dict) -> screen.Shown:
    source = st.clean(args.get("source_type") or "book", 20).lower()
    if source not in ("book", "website", "journal"):
        raise ValueError("I can cite a book, a website or a journal article.")
    style = st.clean(args.get("style") or "harvard", 20)
    text = format_citation(style, source, args)
    label = "APA 7" if style.lower().startswith("apa") else "Harvard"
    return screen.Shown(f"Here's the {label} reference: {text}", screen.card(
        "text", f"{label} reference", "study-cite", text=text,
        buttons=[{"label": "Other style", "say": f"Give me that reference in {'Harvard' if label == 'APA 7' else 'APA'} style."}]))


# ---- quiz me on my notes ------------------------------------------------------------------------------

def quiz_notes(settings: Settings, args: dict) -> screen.Shown:
    name = st.need(args.get("file") or args.get("subject"), "notes file", 100)
    path: Path = screen.find_file(settings, st.clean(args.get("folder"), 100), name)
    if path.suffix.lower() not in (".md", ".txt"):
        raise ValueError("I can only quiz you from text or Markdown notes.")
    notes = path.read_text(encoding="utf-8", errors="replace")[:MAX_NOTES].strip()
    if len(notes) < 40:
        raise ValueError("Those notes are too short to quiz you on.")
    count = max(3, min(int(args.get("questions") or 8), 20))
    said = (f"Notes: {path.name}\n{notes}\n\nINSTRUCTION for Alfred: quiz the student on ONLY these notes. Ask {count} "
            "questions, one at a time, and wait for the answer. After each answer say if it was right, correct it "
            "briefly from the notes, then ask the next. Keep every spoken turn to one or two sentences. At the end "
            "give the score and name the topics to revisit.")
    return screen.Shown(said, screen.card(
        "text", f"Quiz: {path.stem}", "study-quiz", text=f"Quizzing you on {path.name}: {count} questions, one at a time.",
        buttons=[{"label": "Hint", "say": "Give me a hint for that question."},
                 {"label": "Stop quiz", "say": "Stop the quiz and give me my score."}]))


# ---- breaks ---------------------------------------------------------------------------------------------

def study_break(args: dict) -> screen.Shown:
    minutes = min((5, 10, 20), key=lambda m: abs(m - float(args.get("minutes") or 5)))
    ideas = random.sample(BREAKS[minutes], 3)
    items = [{"label": i} for i in ideas]
    items += [{"label": "Calm breathing for 3 minutes", "say": "Guide me through a 3 minute breathing exercise."},
              {"label": f"Set a {minutes} minute break timer", "say": f"Set a timer for {minutes} minutes called break."}]
    return screen.Shown(f"Take {minutes} minutes: {ideas[0].lower()}.", screen.card(
        "list", f"{minutes} minute break", "study-break", items=items))


ACTIONS = ["essay_plan", "cite", "quiz_notes", "study_break"]


def tool_definitions() -> list[dict]:
    return [{
        "name": "study_write",
        "description": "Study writing and recall. essay_plan (question, essay_type argue/compare/analyse/evaluate, "
                       "word_count, subject) returns a scaffold you then fill in for the question. cite formats a "
                       "Harvard or APA reference from fields the user gives (source_type book, website or journal; "
                       "authors, year, title, publisher, place, edition, url, accessed, journal, volume, issue, "
                       "pages), offline. quiz_notes (file name, optional folder, questions) returns the user's notes "
                       "for you to quiz them on one question at a time. study_break (minutes 5, 10 or 20) suggests "
                       "a break with a calm option.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "question": {"type": "string", "description": "The essay question."},
                "essay_type": {"type": "string", "enum": list(ESSAYS)},
                "word_count": {"type": "integer"},
                "subject": {"type": "string"},
                "style": {"type": "string", "enum": ["harvard", "apa"]},
                "source_type": {"type": "string", "enum": ["book", "website", "journal"]},
                "authors": {"type": "string", "description": "e.g. 'Smith, John; Ann Jones'."},
                "year": {"type": "string"},
                "title": {"type": "string"},
                "publisher": {"type": "string"},
                "place": {"type": "string"},
                "edition": {"type": "string"},
                "url": {"type": "string"},
                "accessed": {"type": "string", "description": "Date accessed, e.g. 12 May 2026."},
                "journal": {"type": "string"},
                "volume": {"type": "string"},
                "issue": {"type": "string"},
                "pages": {"type": "string"},
                "file": {"type": "string", "description": "quiz_notes: notes file name, or part of it."},
                "folder": {"type": "string", "description": "quiz_notes: memory folder, e.g. Notes."},
                "questions": {"type": "integer"},
                "minutes": {"type": "number", "description": "study_break length."},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"study_write"}


def run_tool(name: str, args: dict, settings: Settings, http=None):
    action = args.get("action")
    if action == "essay_plan":
        return essay_plan(args)
    if action == "cite":
        return cite(args)
    if action == "quiz_notes":
        return quiz_notes(settings, args)
    if action == "study_break":
        return study_break(args)
    raise ValueError(f"Unknown study writing action: {action}")
