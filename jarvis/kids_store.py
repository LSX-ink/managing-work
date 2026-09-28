"""Shared bits for the kids abilities: one JSON file per tracker (kids-*.json in the memory folder), keyed by child.

Children are just names: the first time a name is used it's added, and later any case or a unique part of it
finds the same child.
"""

import homestore as hs
from config import Settings

MAX_CHILDREN, MAX_LOG = 12, 400
FILES = ("kids-stars.json", "kids-pocket.json", "kids-reading.json", "kids-growth.json", "kids-milestones.json",
         "kids-health.json", "kids-bedtime.json")


def load(settings: Settings, name: str) -> dict:
    return {k: v for k, v in hs.load(settings, name, {}).items() if isinstance(v, (dict, list))}


def save(settings: Settings, name: str, data: dict) -> None:
    hs.save(settings, name, data)


def child(found: dict, name, create: bool = True) -> str:
    """The stored name for a child, adding them when create is true."""
    name = hs.need(name, "child", 30)
    k = hs.find(found, name)
    if k is not None:
        return k
    if not create:
        raise ValueError(f"I haven't got anything for {name} yet.")
    if len(found) >= MAX_CHILDREN:
        raise ValueError("That's as many children as I can keep track of.")
    return name[:1].upper() + name[1:]


def children(settings: Settings) -> list[str]:
    """Every child named in any kids file, in the order first seen."""
    seen: dict[str, str] = {}
    for name in FILES:
        for k in load(settings, name):
            seen.setdefault(k.lower(), k)
    return list(seen.values())


def only_child(settings: Settings, found: dict, name) -> str:
    """The named child, or the only child there is when no name is given."""
    if hs.clean(name):
        return child(found, name, create=False)
    if len(found) == 1:
        return next(iter(found))
    raise ValueError("Which child?" if found else "I haven't got anything saved for the children yet.")


def append(entries: list, entry: dict) -> list:
    return (entries + [entry])[-MAX_LOG:]


def cash(n: float, currency: str) -> str:
    symbol = {"GBP": "£", "EUR": "€", "USD": "$"}.get(currency.upper())
    return f"{'-' if n < 0 else ''}{symbol}{abs(n):,.2f}" if symbol else hs.money(n, currency)
