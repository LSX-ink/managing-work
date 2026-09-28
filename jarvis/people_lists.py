"""Lists of people: the holiday card list (tick off who's had one, with their addresses) and named invite lists
built from groups and names in the people notebook.

Saved only in people-cards.json and people-invites.json in the memory folder. Addresses show on the pop-up only.
"""

import homestore as hs
import people_store as ps
import screen
from config import Settings

MAX_LISTS = 50


def _year(year) -> str:
    return str(int(hs.number(year, "year", 2000, 2100))) if year else str(hs.today().year)


def _pick_people(found: dict, people, groups) -> list[str]:
    keys = [ps.person(found, n) for n in ps.words(people, 200, 60)]
    for g in ps.words(groups, 20, 40):
        members = [k for k, p in found.items() if g.lower() in (x.lower() for x in p.get("groups", []))]
        if not members:
            raise ValueError(f"Nobody is in a group called {g}.")
        keys += members
    if not keys:
        raise ValueError("Which people or groups?")
    return list(dict.fromkeys(keys))


# Holiday cards

def cards_add(settings: Settings, people, groups, year=None) -> str:
    found = ps.book(settings)
    keys = _pick_people(found, people, groups)
    lists = hs.load(settings, ps.CARDS, {})
    y = _year(year)
    sent = lists.setdefault(y, {})
    for k in keys:
        sent.setdefault(k, False)
    hs.save(settings, ps.CARDS, dict(sorted(lists.items())[-5:]))
    return f"{hs.plural(len(sent), 'person', 'people')} on the {y} card list."


def cards_sent(settings: Settings, name, year=None, done=True) -> str:
    lists = hs.load(settings, ps.CARDS, {})
    y = _year(year)
    sent = lists.get(y) or {}
    k = hs.find(sent, hs.need(name, "person", 60))
    if k is None:
        raise ValueError(f"{hs.clean(name, 60)} isn't on the {y} card list.")
    sent[k] = bool(done)
    hs.save(settings, ps.CARDS, lists)
    left = sum(not v for v in sent.values())
    return f"{k}'s card {'done' if done else 'not done yet'}. {hs.plural(left, 'card')} to go."


def cards_show(settings: Settings, year=None) -> screen.Shown | str:
    y = _year(year)
    sent = hs.load(settings, ps.CARDS, {}).get(y) or {}
    if not sent:
        return f"The {y} card list is empty. Say something like 'put my Family group on the card list'."
    found = ps.book(settings)
    items = [{"label": f"{k} - {found.get(k, {}).get('address') or 'no address saved'}", "done": bool(v),
              "say": f"Mark {k}'s holiday card as {'not done' if v else 'done'} for {y}."}
             for k, v in sorted(sent.items(), key=lambda kv: kv[0].lower())]
    card = screen.card("list", f"Holiday cards {y}", f"people-cards-{y}", items=items, checks=True)
    left = sum(not v for v in sent.values())
    return screen.Shown(f"{hs.plural(left, 'card')} to go out of {len(sent)}.", card)


def cards_remove(settings: Settings, name, year, confirmed: bool) -> str:
    lists = hs.load(settings, ps.CARDS, {})
    y = _year(year)
    sent = lists.get(y) or {}
    k = hs.find(sent, hs.need(name, "person", 60))
    if k is None:
        raise ValueError(f"{hs.clean(name, 60)} isn't on the {y} card list.")
    if not confirmed:
        return f"Ask the user to confirm taking {k} off the {y} card list, then call again with confirmed true."
    del sent[k]
    hs.save(settings, ps.CARDS, lists)
    return f"Took {k} off the {y} card list."


# Invite lists

def invite_build(settings: Settings, label, people, groups) -> str:
    label = hs.need(label, "invite list", 60)
    found = ps.book(settings)
    keys = _pick_people(found, people, groups)
    lists = hs.load(settings, ps.INVITES, {})
    k = hs.find(lists, label) or label
    if k not in lists and len(lists) >= MAX_LISTS:
        raise ValueError("That's a lot of invite lists; remove one first.")
    lists[k] = list(dict.fromkeys(lists.get(k, []) + keys))[:300]
    hs.save(settings, ps.INVITES, lists)
    return f"{hs.plural(len(lists[k]), 'person', 'people')} on the {k} invite list."


def invite_drop(settings: Settings, label, people) -> str:
    lists = hs.load(settings, ps.INVITES, {})
    k = hs.find(lists, hs.need(label, "invite list", 60))
    if k is None:
        raise ValueError(f"There's no invite list called {hs.clean(label, 60)}.")
    drop = {n.lower() for n in ps.words(people, 200, 60)}
    lists[k] = [n for n in lists[k] if n.lower() not in drop]
    hs.save(settings, ps.INVITES, lists)
    return f"{hs.plural(len(lists[k]), 'person', 'people')} left on the {k} invite list."


def invite_show(settings: Settings, label=None) -> screen.Shown | str:
    lists = hs.load(settings, ps.INVITES, {})
    if not lists:
        return "No invite lists yet. Say something like 'make a party invite list from my Uni friends group'."
    if not label:
        card = screen.card("list", "Invite lists", "people-invites",
                           items=[{"label": f"{k} ({len(v)})", "say": f"Show my {k} invite list."} for k, v in lists.items()])
        return screen.Shown(f"{hs.plural(len(lists), 'invite list')}: {', '.join(lists)}.", card)
    k = hs.find(lists, label)
    if k is None:
        raise ValueError(f"There's no invite list called {hs.clean(label, 60)}.")
    found = ps.book(settings)
    rows = [[n, found.get(n, {}).get("how", ""), ", ".join(found.get(n, {}).get("groups", []))] for n in lists[k]]
    card = screen.card("table", f"Invite list: {k}", f"people-invite-{k.lower()}",
                       columns=["Name", "How you know them", "Groups"], rows=rows)
    return screen.Shown(f"{hs.plural(len(rows), 'person', 'people')} on the {k} list.", card)


def invite_remove(settings: Settings, label, confirmed: bool) -> str:
    lists = hs.load(settings, ps.INVITES, {})
    k = hs.find(lists, hs.need(label, "invite list", 60))
    if k is None:
        raise ValueError(f"There's no invite list called {hs.clean(label, 60)}.")
    if not confirmed:
        return f"Ask the user to confirm deleting the {k} invite list, then call again with confirmed true."
    del lists[k]
    hs.save(settings, ps.INVITES, lists)
    return f"Deleted the {k} invite list."


def tool_definitions() -> list[dict]:
    names = {"type": "array", "items": {"type": "string"}}
    return [{
        "name": "people_lists",
        "description": "Holiday / Christmas card list and invite lists from the people notebook. cards_add (people "
                       "and/or groups, optional year), card_sent (name; done false to untick), cards (tick-list "
                       "pop-up with addresses), card_remove. invite_build a named invite list by picking people and "
                       "groups ('make a birthday party list from Uni friends plus Sam'), invite_drop (people), "
                       "invites (one list by list_name, or all lists), invite_remove. Set confirmed true only after "
                       "the user confirms a remove.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["cards_add", "card_sent", "cards", "card_remove",
                                                      "invite_build", "invite_drop", "invites", "invite_remove"]},
                "name": {"type": "string", "description": "One person."},
                "people": names,
                "groups": names,
                "year": {"type": "integer"},
                "done": {"type": "boolean"},
                "list_name": {"type": "string", "description": "The invite list, e.g. 'Birthday party'."},
                "confirmed": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"people_lists"}


def run_tool(name: str, args: dict, settings: Settings, http=None):
    a = args.get
    people = a("people") or ([a("name")] if a("name") else [])
    ok, label = bool(a("confirmed")), a("list_name")
    actions = {
        "cards_add": lambda: cards_add(settings, people, a("groups"), a("year")),
        "card_sent": lambda: cards_sent(settings, a("name"), a("year"), a("done") is not False),
        "cards": lambda: cards_show(settings, a("year")),
        "card_remove": lambda: cards_remove(settings, a("name"), a("year"), ok),
        "invite_build": lambda: invite_build(settings, label, people, a("groups")),
        "invite_drop": lambda: invite_drop(settings, label, people),
        "invites": lambda: invite_show(settings, label),
        "invite_remove": lambda: invite_remove(settings, label, ok),
    }
    if a("action") not in actions:
        raise ValueError("Unknown people list action.")
    return actions[a("action")]()
