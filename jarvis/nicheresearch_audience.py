"""Audience side of niche research: a saved audience persona, interview questions, a pain-point bank per niche (ranked),
solution prompts, survey question drafts, an offline keyword and topic brainstorm and a content-gap finder.

Data is in nicheresearch.json in the memory folder. The brainstorm is word combinations made on this PC: they are ideas to
check, not search volumes. Nothing is looked up, posted or sent.
"""

import re

import nicheresearch_store as nr
from config import Settings

NAMES = {"nicheresearch_audience"}
PERSONA_FIELDS = {"persona_name": "Name", "age_range": "Age range", "job": "Job or situation", "goals": "Goals",
                  "frustrations": "Frustrations", "hangouts": "Where they spend time", "buys": "Why they would pay",
                  "objections": "What holds them back", "words": "Words they use"}
INTERVIEW = [
    "Tell me about the last time you dealt with this. What happened?", "What is the hardest part of it?",
    "What have you tried already, and what did you like or dislike about it?", "How much time or money has it cost you?",
    "If you could wave a wand, what would change first?", "Who else do you ask for help?",
    "Have you ever paid for something to fix it? What, and was it worth it?", "What almost stopped you from buying?",
    "Where do you go to learn about this?", "Is there anything I should have asked and didn't?",
]
PLACES = ["Online groups and forums where people ask questions about it", "Comment sections under the biggest videos and posts",
          "Reviews of the top books and products (the 3-star ones are honest)", "Local clubs, classes and meetups",
          "Friends and family who fit the persona: ask for a 10 minute chat", "Question sites: read what people keep asking"]
MODIFIERS = ["for beginners", "tips", "mistakes to avoid", "checklist", "on a budget", "step by step", "examples", "template",
             "vs", "cost", "tools", "for busy people", "common questions", "myths", "how to start", "ideas", "planner", "guide"]
FRAMES = ["A checklist that fixes: {}", "A short guide to: {}", "A template or worksheet for: {}", "A community or chat group for people stuck with: {}",
          "A 7 day challenge that helps with: {}", "A done-for-you service for: {}", "A comparison of the tools people use for: {}"]


def _persona_view(row: dict) -> list:
    return [(label, [row["persona"].get(k) or "(not filled in yet)"]) for k, label in PERSONA_FIELDS.items()]


def persona_save(settings: Settings, args: dict):
    d, row = nr.open_niche(settings, args)
    given = {k: nr.clean(args[k], 300) for k in PERSONA_FIELDS if args.get(k)}
    if not given:
        raise ValueError("Tell me something about the person: goals, frustrations, where they spend time and so on.")
    row["persona"].update(given)
    nr.save(settings, nr.FILE, d)
    left = [v for k, v in PERSONA_FIELDS.items() if k not in row["persona"]]
    return f"Saved the audience persona for {row['name']}." + (f" Still blank: {', '.join(left[:4])}." if left else "")


def persona_show(settings: Settings, args: dict):
    d, row = nr.open_niche(settings, args)
    if not row["persona"]:
        raise ValueError(f"No persona for {row['name']} yet. Describe who it is for.")
    who = row["persona"].get("persona_name") or "your ideal person"
    return nr.sheet(f"Here is {who} for {row['name']}.", f"Persona: {row['name']}", _persona_view(row),
                    "Built from what you told me. Check it against real conversations.", headline=who)


def interview_questions(settings: Settings, args: dict):
    return nr.sheet("Ten questions for a customer chat.", "Customer interview questions",
                    [("Ask, then listen. Do not pitch", [(f"{i + 1}. {q}", "") for i, q in enumerate(INTERVIEW)]),
                     ("Where to find people to ask", PLACES)],
                    "Write their exact words down, then tell me the pain points and I will bank them.")


def pain_add(settings: Settings, args: dict):
    d, row = nr.open_niche(settings, args)
    if len(row["pains"]) >= nr.MAX_ROWS:
        raise ValueError("The pain point bank is full.")
    p = {"id": nr.next_id(row["pains"]), "text": nr.need(args.get("text"), "pain point", 200),
         "intensity": nr.rating(args.get("intensity", 3), "intensity"), "frequency": nr.rating(args.get("frequency", 3), "frequency"),
         "source": nr.clean(args.get("source"), 120)}
    row["pains"].append(p)
    nr.save(settings, nr.FILE, d)
    return f"Banked pain point {p['id']} for {row['name']}: {p['text']}."


def _pain(row: dict, args: dict) -> dict:
    return nr.pick(row["pains"], args.get("pain"), "text", "pain point")


def pain_update(settings: Settings, args: dict):
    d, row = nr.open_niche(settings, args)
    p = _pain(row, args)
    for k in ("intensity", "frequency"):
        if args.get(k) is not None:
            p[k] = nr.rating(args[k], k)
    if args.get("text"):
        p["text"] = nr.need(args["text"], "pain point", 200)
    if args.get("source") is not None:
        p["source"] = nr.clean(args["source"], 120)
    nr.save(settings, nr.FILE, d)
    return f"Updated pain point {p['id']}."


def pain_remove(settings: Settings, args: dict):
    d, row = nr.open_niche(settings, args)
    p = _pain(row, args)
    ask = nr.confirm_first(args, f"the pain point {p['text']}")
    if ask:
        return ask
    row["pains"] = [x for x in row["pains"] if x is not p]
    nr.save(settings, nr.FILE, d)
    return "Removed that pain point."


def pain_list(settings: Settings, args: dict):
    d, row = nr.open_niche(settings, args)
    if not row["pains"]:
        raise ValueError(f"No pain points for {row['name']} yet. Say what people struggle with.")
    ranked = sorted(row["pains"], key=lambda p: -p["intensity"] * p["frequency"])
    rows = [(f"{p['id']}. {p['text']} (hurts {p['intensity']}, often {p['frequency']}"
             + (f", from {p['source']}" if p["source"] else "") + ")", f"Give me solution ideas for pain point {p['id']} in {row['name']}") for p in ranked]
    return nr.tappable(f"{len(ranked)} pain points, worst first. Tap one for solution ideas.", f"Pain points: {row['name']}", rows)


def pain_to_ideas(settings: Settings, args: dict):
    d, row = nr.open_niche(settings, args)
    if not row["pains"]:
        raise ValueError(f"Bank a pain point for {row['name']} first.")
    p = _pain(row, args) if nr.clean(args.get("pain")) else max(row["pains"], key=lambda x: x["intensity"] * x["frequency"])
    return nr.tappable(f"Seven ways to answer: {p['text']}.", "Solution prompts",
                       [(f.format(p["text"].rstrip(".")), f"Add an experiment to test: {f.format(p['text'].rstrip('.'))}") for f in FRAMES])


def survey_draft(settings: Settings, args: dict):
    d, row = nr.open_niche(settings, args)
    top = sorted(row["pains"], key=lambda p: -p["intensity"] * p["frequency"])[:3]
    qs = [f"How often do you think about {row['name']}? (daily / weekly / monthly / never)",
          f"What is your biggest struggle with {row['name']}? (open answer)"]
    qs += [f"How much does this bother you, from 1 to 5: {p['text']}?" for p in top]
    qs += ["What have you tried to fix it so far? (open answer)", "How much have you spent on it in the last year? (none / under 20 pounds / 20 to 100 / over 100)",
           "Would you pay for a solution? What would feel like a fair price? (open answer)", "Where do you usually look for help? (open answer)",
           "Is there anything else you wish existed? (open answer)", "May I contact you for a chat? (optional, leave your own contact details)"]
    row["survey"] = qs
    nr.save(settings, nr.FILE, d)
    return nr.sheet(f"Drafted {len(qs)} survey questions for {row['name']}.", f"Survey draft: {row['name']}",
                    [("Questions", [f"{i + 1}. {q}" for i, q in enumerate(qs)])],
                    "Keep surveys short, ask about the past not the future, and never ask people to pay before you have a real offer. "
                    "Sending it is up to you.")


def where_to_find(settings: Settings, args: dict):
    return nr.sheet("Six places to find your audience.", "Where to find your audience", [("Try these", PLACES)],
                    "Read and listen first. Do not post or message anyone until you have a plan.")


def keyword_brainstorm(settings: Settings, args: dict):
    seeds = nr.items(args.get("seeds"))
    d = nr.data(settings)
    if not seeds and d["niches"] and (nr.clean(args.get("niche")) or len(d["niches"]) == 1):
        seeds = [nr.niche(d, args)["name"]]
    if not seeds:
        raise ValueError("Give me a few seed words, for example 'sourdough, baking'.")
    seen, out = set(), []
    for m in MODIFIERS:
        for s in seeds[:5]:
            for phrase in ((f"{s} {m}", f"{m} {s}") if m in ("vs", "tools", "tips", "ideas", "guide") else (f"{s} {m}",)):
                if phrase.lower() not in seen:
                    seen.add(phrase.lower())
                    out.append(phrase)
    for a in seeds[:5]:
        for b in seeds[:5]:
            if a != b and f"{a} {b}".lower() not in seen:
                seen.add(f"{a} {b}".lower())
                out.append(f"{a} {b}")
    out = out[:40]
    return nr.tappable(f"{len(out)} word combinations. They are ideas to check, not search volumes.", "Keyword and topic ideas",
                       [(x, f"Add '{x}' to my topic list") for x in out])


def _norm(topic: str) -> set[str]:
    stop = {"a", "an", "the", "of", "to", "and", "or", "in", "on", "for", "is", "are", "my", "how", "your", "with", "what", "why"}
    return {w for w in re.findall(r"[a-z0-9]+", topic.lower()) if w not in stop}


def _covered(topic: str, others: list[str]) -> bool:
    words = _norm(topic)
    return any(topic.lower() == o.lower() or (words and _norm(o) and len(words & _norm(o)) / min(len(words), len(_norm(o))) >= 0.7) for o in others)


def content_gap(settings: Settings, args: dict):
    d, row = nr.open_niche(settings, args)
    theirs = nr.items(args.get("competitor_topics")) or [t for c in row["competitors"] for t in c.get("topics", [])]
    mine = nr.items(args.get("my_topics")) or row["my_topics"]
    if not theirs:
        raise ValueError("Give me the topics competitors cover (typed by you), or save them on competitors first.")
    if nr.clean(args.get("my_topics")):
        row["my_topics"] = mine
    gaps = list(dict.fromkeys(t for t in theirs if not _covered(t, mine)))
    shared = list(dict.fromkeys(t for t in theirs if _covered(t, mine)))
    yours = [t for t in mine if not _covered(t, theirs)]
    row["gaps"] = gaps
    nr.save(settings, nr.FILE, d)
    return nr.sheet(f"{len(gaps)} topics competitors cover that you don't.", f"Content gaps: {row['name']}", [
        ("They cover, you don't (gaps)", [(g, f"Add '{g}' to my topic list") for g in gaps] or ["None found."]),
        ("You both cover", shared or ["None."]), ("Only you cover (your angle?)", yours or ["None."])],
        "Matched by shared words in the lists you typed. A gap is a prompt to check, not proof of demand.")


def add_topic(settings: Settings, args: dict):
    d, row = nr.open_niche(settings, args)
    new = nr.items(args.get("topic"))
    if not new:
        raise ValueError("Which topic?")
    row["my_topics"] = list(dict.fromkeys(row["my_topics"] + new))[:nr.MAX_ROWS]
    nr.save(settings, nr.FILE, d)
    return f"Your topic list for {row['name']} has {len(row['my_topics'])} topics."


ACTIONS = {"persona_save": persona_save, "persona_show": persona_show, "interview_questions": interview_questions,
           "pain_add": pain_add, "pain_update": pain_update, "pain_remove": pain_remove, "pain_list": pain_list,
           "pain_to_ideas": pain_to_ideas, "survey_draft": survey_draft, "where_to_find": where_to_find,
           "keyword_brainstorm": keyword_brainstorm, "content_gap": content_gap, "add_topic": add_topic}


def tool_definitions() -> list[dict]:
    props = {k: {"type": "string", "description": f"Persona: {v}."} for k, v in PERSONA_FIELDS.items()}
    return [{
        "name": "nicheresearch_audience",
        "description": "Audience research for a niche or business idea: saved audience persona, customer interview questions, pain-point bank "
                       "(ranked), solution prompts, survey question drafts, where to find the audience, offline keyword and topic "
                       "brainstorm from seed words (not search volumes), content-gap finder from competitor topics vs the user's own. "
                       "Set confirmed only after the user agrees to pain_remove.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": list(ACTIONS)},
                "niche": {"type": "string", "description": "Niche number or name (optional when there is only one)."},
                "pain": {"type": "string", "description": "Pain point number or text."}, "text": {"type": "string", "description": "Pain point wording."},
                "intensity": {"type": "number", "description": "How much it hurts, 1-5."}, "frequency": {"type": "number", "description": "How often, 1-5."},
                "source": {"type": "string", "description": "Where the user heard it."},
                "seeds": {"type": "string", "description": "Comma-separated seed words."},
                "competitor_topics": {"type": "string", "description": "Topics competitors cover, comma or line separated."},
                "my_topics": {"type": "string"}, "topic": {"type": "string", "description": "add_topic: topics to add."},
                "confirmed": {"type": "boolean"}, **props,
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


def run_tool(name: str, args: dict, settings: Settings, http=None):
    return nr.dispatch(ACTIONS, settings, args)
