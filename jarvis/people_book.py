"""The people notebook: who's who, a card per person, notes, groups, search, a family tree and call reminders.

Saved only in people-book.json in the memory folder and never sent anywhere. Phone numbers, emails and addresses
show on the pop-up card but stay out of what Alfred says, unless the user asks for them.
"""

import homestore as hs
import people_store as ps
import reminders
import screen
from config import Settings

NOTE_FIELDS = {"note": "notes", "like": "likes", "dislike": "dislikes", "family": "family"}
screen.EXTRA_KINDS.add("people-tree")


def add(settings: Settings, name, fields: dict) -> str:
    name = hs.need(name, "person", 60)
    found = ps.book(settings)
    k = next((n for n in found if n.lower() == name.lower()), None)
    if k is None and len(found) >= ps.MAX_PEOPLE:
        raise ValueError("Your people notebook is full; remove someone first.")
    p = found.get(k) or ps.blank()
    for field in ps.FIELDS:
        if fields.get(field):
            p[field] = hs.clean(fields[field], 200)
    found[k or name] = p
    ps.save(settings, found)
    return f"{'Updated' if k else 'Added'} {k or name} in your people notebook."


def edit(settings: Settings, name, fields: dict, new_name=None) -> str:
    found = ps.book(settings)
    k = ps.person(found, name)
    for field in ps.FIELDS:
        if fields.get(field) is not None:
            found[k][field] = hs.clean(fields[field], 200)
    new = hs.clean(new_name, 60)
    if new and new != k:
        if new.lower() in (n.lower() for n in found if n != k):
            raise ValueError(f"There's already someone called {new}.")
        found[new] = found.pop(k)
        _rename_links(found, k, new)
        k = new
    ps.save(settings, found)
    return f"Updated {k}."


def _rename_links(found: dict, old: str, new: str) -> None:
    for p in found.values():
        for rel in ("parents", "children", "partners"):
            p[rel] = [new if n == old else n for n in p.get(rel, [])]


def remove(settings: Settings, name, confirmed: bool) -> str:
    found = ps.book(settings)
    k = ps.person(found, name)
    if not confirmed:
        return f"Ask the user to confirm removing {k} and everything noted about them, then call again with confirmed true."
    del found[k]
    for p in found.values():
        for rel in ("parents", "children", "partners"):
            p[rel] = [n for n in p.get(rel, []) if n != k]
    ps.save(settings, found)
    return f"Removed {k} from your people notebook."


def listing(settings: Settings, group=None) -> screen.Shown | str:
    found = ps.book(settings)
    today = hs.today()
    if group:
        g = hs.clean(group, 40).lower()
        found = {k: p for k, p in found.items() if g in (x.lower() for x in p.get("groups", []))}
        if not found:
            return f"Nobody is in the {hs.clean(group, 40)} group yet."
    if not found:
        return "Your people notebook is empty. Tell me someone to add."
    names = sorted(found, key=str.lower)
    title = f"People: {hs.clean(group, 40)}" if group else "People"
    card = screen.card("table", title, f"people-list-{hs.clean(group, 40).lower()}",
                       columns=["Name", "How you know them", "Groups", "Last in touch"],
                       rows=[[k, found[k].get("how", ""), ", ".join(found[k].get("groups", [])),
                              ps.ago(ps.last_contact(found[k]), today)] for k in names])
    return screen.Shown(f"{hs.plural(len(names), 'person', 'people')} {'in ' + group if group else 'in your notebook'}.",
                        card)


def note(settings: Settings, name, field, text) -> str:
    found = ps.book(settings)
    k = ps.person(found, name)
    key = NOTE_FIELDS.get(field or "note", "notes")
    text = hs.need(text, "note", 300)
    if key == "notes":
        found[k]["notes"] = (found[k]["notes"] + [{"date": hs.today().isoformat(), "text": text}])[-ps.MAX_LOG:]
    else:
        found[k][key] = ps.words(found[k][key] + [text], 50, 120)
    ps.save(settings, found)
    what = {"notes": "a note", "likes": "a like", "dislikes": "a dislike", "family": "a family name"}[key]
    return f"Saved {what} about {k}."


def _card_text(settings: Settings, k: str, p: dict) -> str:
    today = hs.today()
    lines = [f"{label}: {p[f]}" for f, label in (("how", "How you know them"), ("phone", "Phone"), ("email", "Email"),
                                                 ("address", "Address")) if p.get(f)]
    if p.get("groups"):
        lines.append("Groups: " + ", ".join(p["groups"]))
    last = ps.last_contact(p)
    lines.append(f"Last in touch: {ps.ago(last, today)}" + (f" (aim: every {p['every']} days)" if p.get("every") else ""))
    born = ps.birthday(settings, k)
    if born:
        when, age = ps.next_date(born, today)
        lines.append(f"Birthday: {ps.short(when)}, {ps.until(when, today)}" + (f", turning {age}" if age else ""))
    for label, value in sorted(p.get("dates", {}).items()):
        when, years = ps.next_date(value, today)
        lines.append(f"{label.capitalize()}: {ps.short(when)}, {ps.until(when, today)}" + (f" ({years} years)" if years else ""))
    for rel, label in (("partners", "Partner"), ("parents", "Parents"), ("children", "Children")):
        if p.get(rel):
            lines.append(f"{label}: " + ", ".join(p[rel]))
    for key, label in (("family", "Family"), ("likes", "Likes"), ("dislikes", "Dislikes")):
        if p.get(key):
            lines.append(f"{label}: " + "; ".join(p[key]))
    gift = ps.gifts(settings, k)
    if gift:
        lines.append("Gift ideas: " + "; ".join(gift))
    if p.get("notes"):
        lines.append("\nNotes:\n" + "\n".join(f"- {n['text']} ({n['date']})" for n in p["notes"][-10:]))
    talks = [c for c in p.get("contacts", []) if c.get("topics")][-5:]
    if talks:
        lines.append("\nLately talked about:\n" + "\n".join(f"- {c['date']}: {', '.join(c['topics'])}" for c in talks))
    return "\n".join(lines)


def show_card(settings: Settings, name, show_contact: bool = False) -> screen.Shown:
    found = ps.book(settings)
    k = ps.person(found, name)
    p = found[k]
    card = screen.card("text", k, f"people-card-{k.lower()}", text=_card_text(settings, k, p), buttons=[
        {"label": "I've been in touch", "say": f"I've just been in touch with {k}."},
        {"label": "Conversations", "say": f"Show my conversations with {k}."},
        {"label": "Family tree", "say": f"Show {k}'s family tree."}])
    spoken = f"Here's {k}'s card. Last in touch {ps.ago(ps.last_contact(p), hs.today())}."
    if show_contact:
        details = [f"{f} {p[f]}" for f in ("phone", "email", "address") if p.get(f)]
        spoken += " " + ("; ".join(details) + "." if details else "I've no contact details saved for them.")
    return screen.Shown(spoken, card)


def _haystack(p: dict) -> list[tuple[str, str]]:
    found = [(f, p.get(f, "")) for f in ps.FIELDS]
    found += [("note", n.get("text", "")) for n in p.get("notes", [])]
    found += [(key, v) for key in ("likes", "dislikes", "family", "groups", "partners", "parents", "children")
              for v in p.get(key, [])]
    found += [("date", k) for k in p.get("dates", {})]
    found += [("talked about", t) for c in p.get("contacts", []) for t in c.get("topics", [])]
    return found


def search(settings: Settings, query) -> screen.Shown | str:
    words = hs.need(query, "detail to search for", 80).lower().split()
    found = ps.book(settings)
    hits = []
    for k in sorted(found, key=str.lower):
        stack = [(f, str(v)) for f, v in _haystack(found[k]) if v]
        where = next(((f, v) for f, v in stack if all(w in v.lower() for w in words)), None)
        if where or all(w in (k + " " + " ".join(v for _, v in stack)).lower() for w in words):
            hits.append((k, f"{where[0]}: {where[1]}" if where else ""))
    if not hits:
        return f"Nobody in your notebook matches {hs.clean(query, 80)}."
    card = screen.card("list", f"People matching {hs.clean(query, 40)}", "people-search",
                       items=[{"label": f"{k} - {why}" if why else k, "say": f"Show {k}'s person card."} for k, why in hits])
    names = ", ".join(k for k, _ in hits[:6])
    return screen.Shown(f"{hs.plural(len(hits), 'person', 'people')} match: {names}.", card)


def group_add(settings: Settings, people, group) -> str:
    group = hs.need(group, "group", 40)
    found = ps.book(settings)
    keys = [ps.person(found, n) for n in ps.words(people, 100, 60)]
    if not keys:
        raise ValueError("Who should go in the group?")
    for k in keys:
        have = [g for g in found[k]["groups"] if g.lower() != group.lower()]
        found[k]["groups"] = (have + [group])[:20]
    ps.save(settings, found)
    return f"Added {', '.join(keys)} to {group}."


def group_leave(settings: Settings, people, group) -> str:
    group = hs.need(group, "group", 40)
    found = ps.book(settings)
    keys = [ps.person(found, n) for n in ps.words(people, 100, 60)]
    for k in keys:
        found[k]["groups"] = [g for g in found[k]["groups"] if g.lower() != group.lower()]
    ps.save(settings, found)
    return f"Took {', '.join(keys) or 'nobody'} out of {group}."


def groups(settings: Settings) -> screen.Shown | str:
    found = ps.book(settings)
    circles: dict[str, list[str]] = {}
    for k in sorted(found, key=str.lower):
        for g in found[k].get("groups", []):
            circles.setdefault(next((c for c in circles if c.lower() == g.lower()), g), []).append(k)
    if not circles:
        return "No groups yet. Say something like 'put Sam and Jo in Uni friends'."
    card = screen.card("table", "Groups", "people-groups", columns=["Group", "People", "Who"],
                       rows=[[g, str(len(n)), ", ".join(n)] for g, n in sorted(circles.items())],
                       buttons=[{"label": g[:40], "say": f"List the people in my {g} group."} for g in sorted(circles)][:6])
    return screen.Shown(f"{hs.plural(len(circles), 'group')}: {', '.join(sorted(circles))}.", card)


def _ensure(found: dict, name) -> tuple[str, bool]:
    k = hs.find(found, hs.need(name, "person", 60))
    if k is not None:
        ps.person(found, k)
        return k, False
    if len(found) >= ps.MAX_PEOPLE:
        raise ValueError("Your people notebook is full; remove someone first.")
    k = hs.clean(name, 60)
    found[k] = ps.blank()
    return k, True


PAIRS = {"parent": ("children", "parents"), "child": ("parents", "children"), "partner": ("partners", "partners")}


def link(settings: Settings, name, relation, other, confirmed: bool = False, remove: bool = False) -> str:
    """name is the relation of other: link('Jean', 'parent', 'Sam') means Jean is Sam's parent."""
    if relation not in PAIRS:
        raise ValueError("Is that a parent, child or partner?")
    found = ps.book(settings)
    if remove:
        a, b = ps.person(found, name), ps.person(found, other)
        if not confirmed:
            return f"Ask the user to confirm taking {a} off the family tree as {b}'s {relation}, then call with confirmed true."
    else:
        (a, new_a), (b, new_b) = _ensure(found, name), _ensure(found, other)
        if a == b:
            raise ValueError("Someone can't be their own relation.")
    mine, theirs = PAIRS[relation]
    for who, rel, to in ((a, mine, b), (b, theirs, a)):
        have = [n for n in found[who][rel] if n != to]
        found[who][rel] = have if remove else (have + [to])[:20]
    ps.save(settings, found)
    if remove:
        return f"{a} is no longer down as {b}'s {relation}."
    added = [n for n, new in ((a, new_a), (b, new_b)) if new]
    return f"Noted: {a} is {b}'s {relation}." + (f" I added {' and '.join(added)} to the notebook too." if added else "")


def _levels(found: dict, start: str) -> dict[str, int]:
    level, todo = {start: 0}, [start]
    while todo:
        k = todo.pop()
        p = found.get(k, {})
        for rel, step in (("parents", -1), ("children", 1), ("partners", 0)):
            for n in p.get(rel, []):
                if n in found and n not in level:
                    level[n] = level[k] + step
                    todo.append(n)
    return level


def tree(settings: Settings, name=None) -> screen.Shown | str:
    found = ps.book(settings)
    linked = [k for k in sorted(found, key=str.lower)
              if any(found[k].get(r) for r in ("parents", "children", "partners"))]
    focus = ps.person(found, name) if name else None
    starts = [focus] if focus else linked
    if not starts or (focus and focus not in linked):
        return "No family links yet. Say something like 'Jean is Sam's mum'."
    levels: dict[str, int] = {}
    for k in starts:
        if k not in levels:
            levels.update(_levels(found, k))
    low = min(levels.values())
    rows: list[list[str]] = [[] for _ in range(max(levels.values()) - low + 1)]
    for k in sorted(levels, key=str.lower):
        row = rows[levels[k] - low]
        if k not in row:
            row.append(k)
            row += [n for n in found[k].get("partners", []) if levels.get(n) == levels[k] and n not in row]
    edges = sorted({(k, c) for k in levels for c in found[k].get("children", []) if c in levels})
    couples = sorted({tuple(sorted((k, n))) for k in levels for n in found[k].get("partners", []) if n in levels})
    title = f"{focus}'s family tree" if focus else "Family tree"
    card = screen.card("people-tree", title, "people-tree", data={
        "rows": rows, "edges": [list(e) for e in edges], "partners": [list(c) for c in couples], "focus": focus or ""})
    return screen.Shown(f"The family tree has {hs.plural(len(levels), 'person', 'people')} over "
                        f"{hs.plural(len(rows), 'generation')}.", card)


def call_reminder(settings: Settings, name, when, repeat=None) -> str:
    found = ps.book(settings)
    k = hs.find(found, hs.need(name, "person", 60)) or hs.clean(name, 60)
    return reminders.add(settings, when, f"Call {k}", repeat or "once", now=hs.now())


def tool_definitions() -> list[dict]:
    text = {"type": "string"}
    return [{
        "name": "people_book",
        "description": "The user's people notebook (friends, family, colleagues), kept only on this PC. add a person "
                       "(name, how_known, optional phone, email, address), edit (also new_name), remove, list (table; "
                       "group lists who's in one group), card (person card: notes, likes, family, last contact, "
                       "birthday, gift ideas), note ('Sam's daughter is called Mia and loves horses': field note, "
                       "like, dislike or family), search people by any detail (query), group_add / group_leave "
                       "(people, group, e.g. Uni friends), groups (all circles), link family tree (name is the "
                       "relation of other: 'Jean is Sam's mum' = name Jean, relation parent, other Sam), unlink, "
                       "tree (family tree pop-up), call_reminder ('remind me to call Mum Sunday at 6': when). "
                       "Phone numbers and addresses show on the card but are not spoken unless the user asks "
                       "(then show_contact true). Set confirmed true only after the user confirms remove or unlink.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": [
                    "add", "edit", "remove", "list", "card", "note", "search", "group_add", "group_leave", "groups",
                    "link", "unlink", "tree", "call_reminder"]},
                "name": {"type": "string", "description": "The person."},
                "new_name": text,
                "how_known": {"type": "string", "description": "How the user knows them, e.g. 'school friend'."},
                "phone": text,
                "email": text,
                "address": text,
                "field": {"type": "string", "enum": list(NOTE_FIELDS)},
                "text": text,
                "query": text,
                "people": {"type": "array", "items": text},
                "group": text,
                "relation": {"type": "string", "enum": list(PAIRS)},
                "other": {"type": "string", "description": "link: the person name is related to."},
                "when": {"type": "string", "description": "call_reminder: 'YYYY-MM-DD HH:MM' local time."},
                "repeat": {"type": "string", "enum": list(reminders.REPEATS)},
                "show_contact": {"type": "boolean"},
                "confirmed": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"people_book"}


def run_tool(name: str, args: dict, settings: Settings, http=None):
    a = args.get
    who, ok = a("name"), bool(a("confirmed"))
    fields = {"how": a("how_known"), "phone": a("phone"), "email": a("email"), "address": a("address")}
    actions = {
        "add": lambda: add(settings, who, fields),
        "edit": lambda: edit(settings, who, fields, a("new_name")),
        "remove": lambda: remove(settings, who, ok),
        "list": lambda: listing(settings, a("group")),
        "card": lambda: show_card(settings, who, bool(a("show_contact"))),
        "note": lambda: note(settings, who, a("field"), a("text")),
        "search": lambda: search(settings, a("query") or a("text")),
        "group_add": lambda: group_add(settings, a("people") or who, a("group")),
        "group_leave": lambda: group_leave(settings, a("people") or who, a("group")),
        "groups": lambda: groups(settings),
        "link": lambda: link(settings, who, a("relation"), a("other")),
        "unlink": lambda: link(settings, who, a("relation"), a("other"), ok, remove=True),
        "tree": lambda: tree(settings, who),
        "call_reminder": lambda: call_reminder(settings, who, a("when"), a("repeat")),
    }
    if a("action") not in actions:
        raise ValueError("Unknown people action.")
    return actions[a("action")]()
