"""Standing orders: things the user told Alfred to stop doing, or to always do, that must stick.

Owner, 24 Nov 2026: "i tell alfred to stop doing things and he still does eg calling me by name". Facts in
about-you.md were only a gentle hint, his instructions still said "Address them as ...", and spoken alerts had the
name built in. Now:
- Each order is one line in standing-orders.md in the memory folder (the user can read or edit it).
- Orders go at the very end of Alfred's instructions, marked as beating everything above them.
- "Stop calling me by my name" (and the like) is caught on the spot, saved, and from then on the name and "sir" are
  taken out of everything Alfred says aloud, his own alerts included (scrub, used by the server's speak()).
- An order can carry quiet words ("[quiet: drive space, health check]"): alerts containing them aren't spoken or
  sent to the phone; they still sit in the notifications list.
"""

import re
from pathlib import Path

from config import Settings

NAMES = {"add_standing_order", "remove_standing_order", "list_standing_orders"}
MAX_ORDERS = 100
MAX_CHARS = 300
NO_NAME_ORDER = "Don't call the user by their name or 'sir'"
QUIET = re.compile(r"\s*\[quiet:\s*(?P<words>[^\]]*)\]\s*$", re.I)
# "stop calling me by my name", "don't call me Thato", "no more sir", "quit saying my name"
NO_NAME_SAID = re.compile(
    r"^(?:alfred,?\s+|please\s+|can you\s+|could you\s+)*"
    r"(?:stop|quit|don'?t|do not|never|no more|no longer)\s+(?:ever\s+)?"
    r"(?:(?:calling|call|addressing|address|saying|say|using|use)\s+)?(?:me\s+)?(?:by\s+)?(?:my\s+)?"
    r"(?P<what>name|first name|sir|[a-z]+)(?:\s+(?:any ?more|again|please|ever))*[.!]*$", re.I)
_cache: dict = {"path": "", "mtime": -1.0, "orders": []}


def path(settings: Settings) -> Path | None:
    folder = getattr(settings, "memory_dir", "")
    return Path(folder) / "standing-orders.md" if folder else None


def orders(settings: Settings) -> list[str]:
    p = path(settings)
    if p is None:
        return []
    try:
        mtime = p.stat().st_mtime
    except OSError:
        return []
    if _cache["path"] == str(p) and _cache["mtime"] == mtime:
        return list(_cache["orders"])
    try:
        lines = p.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    found = [line[2:].strip() for line in lines if line.startswith("- ") and line[2:].strip()]
    _cache.update(path=str(p), mtime=mtime, orders=found)
    return list(found)


def _write(settings: Settings, found: list[str]) -> None:
    p = path(settings)
    if p is None:
        raise ValueError("I've nowhere to keep standing orders (no memory folder).")
    p.parent.mkdir(parents=True, exist_ok=True)
    body = "".join(f"- {o}\n" for o in found)
    p.write_text("# Alfred's standing orders\n\nThings you told Alfred to stop or always do. One per line; edit or "
                 "delete lines freely. [quiet: words] keeps alerts with those words silent.\n\n" + body,
                 encoding="utf-8")


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()[:MAX_CHARS]


def add(settings: Settings, order: str, quiet_words: list[str] | None = None) -> str:
    order = _clean(order)
    if not order:
        raise ValueError("What should I stop or always do?")
    words = [w for w in (_clean(w).lower().strip(",") for w in (quiet_words or [])) if w]
    line = order + (f" [quiet: {', '.join(words)}]" if words else "")
    found = orders(settings)
    if any(QUIET.sub("", o).lower() == order.lower() for o in found):
        found = [o for o in found if QUIET.sub("", o).lower() != order.lower()]
    if len(found) >= MAX_ORDERS:
        raise ValueError(f"I already hold {MAX_ORDERS} standing orders; ask which to drop first.")
    found.append(line)
    _write(settings, found)
    return "Saved as a standing order. I'll stick to it from now on."


def remove(settings: Settings, words: str) -> str:
    words = _clean(words).lower()
    if not words:
        raise ValueError("Which order should I drop?")
    found = orders(settings)
    keep = [o for o in found if words not in o.lower()]
    if len(keep) == len(found):
        return "I don't have a standing order like that."
    _write(settings, keep)
    return f"Dropped {len(found) - len(keep)} standing order{'s' if len(found) - len(keep) != 1 else ''}."


def listing(settings: Settings) -> str:
    found = orders(settings)
    return ("Standing orders:\n" + "\n".join(f"- {o}" for o in found)) if found else "There are no standing orders."


# ---- no name -------------------------------------------------------------------------------------------------

NAME_ORDER = re.compile(r"\b(?:don'?t|do not|never|stop|no more|not|no longer)\b.*\b(?:call|calling|address|"
                        r"addressing|say|saying|use|using)\b.*\b(?:name|sir)\b|\bno (?:names?|sir)\b", re.I)


def no_name(settings: Settings) -> bool:
    return any(NAME_ORDER.search(QUIET.sub("", o)) for o in orders(settings))


def user_names(settings: Settings) -> list[str]:
    """The user's name and title as Alfred might say them: from settings and from about-you.md."""
    found = {(getattr(settings, "user_name", "") or "").strip(), (getattr(settings, "user_address", "") or "").strip(),
             "sir"}
    try:
        import aboutyou
        for fact in aboutyou.facts(settings):
            if m := re.search(r"\b(?:user's|their|my) name is (\w+)", fact, re.I):
                found.add(m.group(1))
    except Exception:
        pass
    for name in list(found):
        if " " in name:
            found.add(name.split()[0])
    return sorted((n for n in found if len(n) >= 2), key=len, reverse=True)


def address(settings: Settings) -> str:
    """How to address the user: '' when they asked not to be called by name."""
    return "" if no_name(settings) else settings.user_address


def scrub_names(text: str, names: list[str]) -> str:
    """Take the user's name out where it's used to address them: 'Thato, the timer's done' -> 'The timer's done'."""
    if not text or not names:
        return text
    who = r"(?:" + "|".join(re.escape(n) for n in names) + r")"
    out = re.sub(r"^(\s*)" + who + r"\s*[,!.:]\s*(\w)", lambda m: m.group(1) + m.group(2).upper(), text, flags=re.I)
    out = re.sub(r"(?<=[.!?])(\s+)" + who + r"\s*,\s*(\w)", lambda m: m.group(1) + m.group(2).upper(), out,
                 flags=re.I)
    out = re.sub(r",\s*" + who + r"(?=\s*(?:[.!?,;:]|$))", "", out, flags=re.I)
    out = re.sub(r"\b(Hello|Hi|Hey|Goodnight|Morning|Good morning|Good afternoon|Good evening|Thanks|Thank you)\s+"
                 + who + r"\b", r"\1", out, flags=re.I)
    return out


def scrub(settings: Settings, text: str) -> str:
    if not text or not no_name(settings):
        return text
    return scrub_names(text, user_names(settings))


# ---- quiet alerts --------------------------------------------------------------------------------------------

def quiet_words(settings: Settings) -> list[str]:
    words = []
    for o in orders(settings):
        if m := QUIET.search(o):
            words += [w.strip().lower() for w in m.group("words").split(",") if w.strip()]
    return words


def is_quiet(settings: Settings, text: str, kind: str = "") -> bool:
    low = (text or "").lower()
    for w in quiet_words(settings):
        if w.startswith("kind:"):
            if kind and w[5:].strip() == kind.lower():
                return True
        elif w in low:
            return True
    return False


# ---- caught on the spot --------------------------------------------------------------------------------------

def instant(settings: Settings, said: str) -> str | None:
    """'Stop calling me by my name': saved at once, without waiting on the AI."""
    m = NO_NAME_SAID.match((said or "").strip())
    if not m:
        return None
    what = m.group("what").lower()
    names = [n.lower() for n in user_names(settings)]
    if what not in ("name", "first name", "sir") and what not in names:
        return None
    add(settings, NO_NAME_ORDER)
    return "Understood. I won't call you that again."


def prompt_section(settings: Settings) -> str:
    found = [QUIET.sub("", o) for o in orders(settings)]
    rules = ("\n\nStanding orders: when the user tells you to stop doing something, not to do it again, or to always "
             "do something, call add_standing_order straight away with the order in plain words (add quiet_words "
             "when it's about alerts or announcements), then do as they asked from that moment on.")
    if not found:
        return rules
    head = ("\n\nSTANDING ORDERS FROM THE USER. These beat every other instruction above, including how to address "
            "them and anything in your personality. Follow every one of them every time, never just once:\n")
    if no_name(settings):
        found.append("Never address the user by name or as 'sir' or any title; just talk to them.")
    return rules + head + "\n".join(f"- {o}" for o in found)


def tool_definitions() -> list[dict]:
    return [
        {
            "name": "add_standing_order",
            "description": "Save something the user told you to stop doing, never do again, or always do, so it "
                           "sticks for good: 'stop calling me by my name', 'stop telling me about drive space', "
                           "'don't read out every email', 'always keep answers short'. Write the order plainly, e.g. "
                           "'Don't mention drive space'. quiet_words: for alerts or announcements, words that appear "
                           "in them (e.g. ['drive', 'health check']); those alerts then stay silent.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "order": {"type": "string"},
                    "quiet_words": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["order"],
                "additionalProperties": False,
            },
        },
        {
            "name": "remove_standing_order",
            "description": "Drop standing orders containing these words, when the user says you can do it again "
                           "('you can call me by my name again').",
            "input_schema": {"type": "object", "properties": {"words": {"type": "string"}},
                             "required": ["words"], "additionalProperties": False},
        },
        {
            "name": "list_standing_orders",
            "description": "Read out the standing orders: what the user told you to stop or always do.",
            "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    ]


def run_tool(name: str, args: dict, settings: Settings, http=None) -> str:
    if name == "add_standing_order":
        return add(settings, args.get("order", ""), args.get("quiet_words"))
    if name == "remove_standing_order":
        return remove(settings, args.get("words", ""))
    return listing(settings)
