"""Exploring the knowledge base (knowledge.py): backlinks, tags, the note graph, orphans and broken links,
a table of every note, resurfacing an old note, and "what do I know about X?" by a local search.

The graph pops up as kind "knowledge-graph" (frontend/popup-knowledge.js): notes are nodes, links are edges.
"""

import re
from collections import Counter
from datetime import date, timedelta

import knowledge
import screen
from config import Settings

GRAPH_KIND = "knowledge-graph"
screen.EXTRA_KINDS.add(GRAPH_KIND)
MAX_NODES = 150
OLD_DAYS = 30
MAX_HITS = 8
STOP = {"what", "do", "does", "know", "about", "the", "my", "me", "and", "for", "notes", "note", "anything", "on",
        "of", "is", "are", "have", "any", "tell"}


def opener(title: str) -> dict:
    return {"label": title, "say": f"Open my note {title}"}


def edges(notes: dict) -> set[tuple[str, str]]:
    """Links between existing notes as (from, to) lower-case titles, without self-links."""
    return {(k, x.lower()) for k, n in notes.items() for x in n["links"] if x.lower() in notes and x.lower() != k}


def show_backlinks(settings: Settings, title: str) -> screen.Shown:
    notes = knowledge.index(settings)
    note = knowledge.find(notes, title)
    found = knowledge.backlinks(notes, note)
    said = (f"{len(found)} notes link to {note['title']}: {', '.join(found)}." if found
            else f"No notes link to {note['title']} yet.")
    return screen.Shown(said, screen.card("list", f"Linking to {note['title']}", f"knowledge-backlinks-{note['title']}",
                                          items=[opener(t) for t in found]))


def all_tags(settings: Settings) -> screen.Shown:
    counts = Counter(t for n in knowledge.index(settings).values() for t in n["tags"])
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    if not ranked:
        return screen.Shown("None of your notes have #tags yet.", screen.card("list", "Tags", "knowledge-tags"))
    items = [{"label": f"#{t} ({n})", "say": f"Show my notes tagged #{t}"} for t, n in ranked]
    top = ", ".join(f"{t} ({n})" for t, n in ranked[:8])
    return screen.Shown(f"{len(ranked)} tags. Most used: {top}.", screen.card("list", "Tags", "knowledge-tags", items=items))


def tagged(settings: Settings, tag: str) -> screen.Shown:
    tag = str(tag or "").strip().lstrip("#").lower()
    if not tag:
        raise ValueError("Which tag?")
    found = sorted((n["title"] for n in knowledge.index(settings).values() if tag in n["tags"]), key=str.lower)
    said = f"{len(found)} notes tagged #{tag}: {', '.join(found)}." if found else f"No notes are tagged #{tag}."
    return screen.Shown(said, screen.card("list", f"#{tag}", f"knowledge-tag-{tag}", items=[opener(t) for t in found]))


def graph(settings: Settings, title: str = "") -> screen.Shown:
    notes = knowledge.index(settings)
    links = edges(notes)
    keep = set(notes)
    focus = ""
    if title:
        focus = knowledge.find(notes, title)["title"].lower()
        near = {focus}
        for _ in range(2):
            near |= {b for a, b in links if a in near} | {a for a, b in links if b in near}
        keep = near
    degree = Counter(x for pair in links for x in pair)
    nodes = sorted(keep, key=lambda k: (-degree[k], k))[:MAX_NODES]
    at = {k: i for i, k in enumerate(nodes)}
    data = {"nodes": [{"title": notes[k]["title"], "degree": degree[k]} for k in nodes],
            "edges": sorted([at[a], at[b]] for a, b in links if a in at and b in at),
            "focus": at.get(focus, -1)}
    cut = f" (the {MAX_NODES} most linked)" if len(keep) > MAX_NODES else ""
    said = f"Your note graph: {len(nodes)} notes and {len(data['edges'])} links{cut}."
    name = f"Notes around {notes[focus]['title']}" if focus else "Note graph"
    return screen.Shown(said, screen.card(GRAPH_KIND, name, "knowledge-graph", data=data,
                                          buttons=[{"label": "Orphans", "say": "Which of my notes are orphans?"},
                                                   {"label": "Broken links", "say": "Show broken links in my notes."}]))


def orphans(settings: Settings) -> screen.Shown:
    notes = knowledge.index(settings)
    linked = {x for pair in edges(notes) for x in pair}
    found = sorted((n["title"] for k, n in notes.items() if k not in linked), key=str.lower)
    said = (f"{len(found)} notes have no links in or out: {', '.join(found[:15])}." if found
            else "Every note links to or from another note.")
    return screen.Shown(said, screen.card("list", "Orphan notes", "knowledge-orphans", items=[opener(t) for t in found]))


def broken(settings: Settings) -> screen.Shown:
    notes = knowledge.index(settings)
    missing: dict[str, list[str]] = {}
    for n in notes.values():
        for x in n["links"]:
            if x.lower() not in notes:
                missing.setdefault(x.lower(), [x]).append(n["title"])
    rows = sorted(missing.values(), key=lambda v: v[0].lower())
    items = [{"label": f"{v[0]} (linked from {', '.join(v[1:4])})", "say": f"Create a note called {v[0]}"} for v in rows]
    said = (f"{len(rows)} links point at notes that don't exist: {', '.join(v[0] for v in rows[:15])}." if rows
            else "No broken links.")
    return screen.Shown(said, screen.card("list", "Broken links", "knowledge-broken", items=items))


def table(settings: Settings) -> screen.Shown:
    notes = knowledge.index(settings)
    incoming = Counter(b for _, b in edges(notes))
    ordered = sorted(notes.values(), key=lambda n: n["title"].lower())
    rows = [[n["title"], " ".join(f"#{t}" for t in n["tags"]), str(len(n["links"])),
             str(incoming[n["title"].lower()]), f"{n['updated']:%d %b %Y}"] for n in ordered]
    return screen.Shown(f"You have {len(rows)} notes.", screen.card(
        "table", "All notes", "knowledge-table", columns=["Title", "Tags", "Links", "Linked from", "Updated"], rows=rows,
        buttons=[{"label": "Note graph", "say": "Show my note graph."}, {"label": "Tags", "say": "List my note tags."}]))


def resurface(settings: Settings, today: date) -> screen.Shown | str:
    seen = knowledge.views(settings)
    cutoff = today - timedelta(days=OLD_DAYS)

    def last(n):
        try:
            return date.fromisoformat(seen[n["title"].lower()])
        except (KeyError, ValueError):
            return n["updated"].date()

    old = [(last(n), n["title"]) for n in knowledge.index(settings).values() if last(n) <= cutoff]
    if not old:
        return f"Every note has been looked at or changed in the last {OLD_DAYS} days."
    when, title = min(old)
    return knowledge.show(settings, title, today, f"Here's an old note, {title}, last seen {when:%d %B %Y}.")


def first_lines(note: dict) -> str:
    lines = [x.strip() for x in knowledge.body_of(note["text"], note["title"]).splitlines()]
    useful = [x for x in lines if x and not x.startswith("#") and x not in ("-", "- [ ]", "1.") and not x.endswith(":")]
    return re.sub(r"\s+", " ", " ".join(useful[:2]))[:200]


def search(settings: Settings, query: str) -> list[tuple[int, dict]]:
    words = [w for w in re.findall(r"\w+", str(query).lower()) if len(w) > 1 and w not in STOP]
    if not words:
        raise ValueError("What should I look for?")
    hits = []
    for n in knowledge.index(settings).values():
        title, body = n["title"].lower(), n["text"].lower()
        score = 10 * (" ".join(words) in title)
        score += sum(5 * (w in title) + 3 * any(w in t for t in n["tags"]) + min(body.count(w), 10) for w in words)
        if score:
            hits.append((score, n))
    return sorted(hits, key=lambda h: (-h[0], h[1]["title"].lower()))[:MAX_HITS]


def what_i_know(settings: Settings, query: str) -> screen.Shown | str:
    hits = search(settings, query)
    if not hits:
        return f"None of your notes mention {query}."
    lines = [f"- {n['title']}: {first_lines(n) or '(no text yet)'}" for _, n in hits]
    return screen.Shown(f"{len(hits)} notes about {query}, best first (summarise them for the user):\n" + "\n".join(lines),
                        screen.card("list", f"About {query}", "knowledge-search",
                                    items=[opener(n["title"]) for _, n in hits]))


def tool_definitions() -> list[dict]:
    return [{
        "name": "knowledge_explore",
        "description": "Explore the user's wiki notes / knowledge base (the Notes folder). Actions: backlinks "
                       "(which notes link to a note), tags (list #tags with counts), tagged (notes with a tag), "
                       "graph (pop-up map of notes and their links; title for the notes around one note), orphans "
                       "(notes with no links in or out), broken_links (links to notes that don't exist, to create "
                       "them), all_notes (table of every note), resurface ('show me an old note' I haven't looked at "
                       "for 30+ days), know ('what do I know about X?': matching notes' titles and first lines to "
                       "summarise).",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["backlinks", "tags", "tagged", "graph", "orphans",
                                                      "broken_links", "all_notes", "resurface", "know"]},
                "title": {"type": "string", "description": "backlinks or graph: a note's title."},
                "tag": {"type": "string"},
                "query": {"type": "string", "description": "know: the topic."},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"knowledge_explore"}


def run_tool(name: str, args: dict, settings: Settings, http=None, today: date | None = None):
    action = args.get("action")
    if action == "backlinks":
        return show_backlinks(settings, args.get("title") or "")
    if action == "tags":
        return all_tags(settings)
    if action == "tagged":
        return tagged(settings, args.get("tag") or "")
    if action == "graph":
        return graph(settings, args.get("title") or "")
    if action == "orphans":
        return orphans(settings)
    if action == "broken_links":
        return broken(settings)
    if action == "all_notes":
        return table(settings)
    if action == "resurface":
        return resurface(settings, today or date.today())
    if action == "know":
        return what_i_know(settings, args.get("query") or "")
    raise ValueError("Pick an action: backlinks, tags, tagged, graph, orphans, broken_links, all_notes, resurface "
                     "or know.")
