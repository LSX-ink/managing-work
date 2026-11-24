"""Names Alfred must hear correctly (owner, 24 Nov 2026: "he said he knows nothing about chefmotso, can you make sure
he hears things correctly, if not process what could be meant").

Speech-to-text turns unusual names into ordinary words: "ChefMotso" came through as "chef mods" and "chef modzo",
so Alfred searched his memory for the wrong thing and opened the wrong website. This list gives him the real names,
how they tend to be misheard, and what each one is. correct() turns a misheard phrase back into the real name, so a
memory search finds it even when the words came through wrong.
"""

import difflib
import re

KNOWN = [
    # (real name, what it is, ways speech-to-text has heard it or is likely to)
    ("ChefMotso", "a Kinetic client: Kgomotso Maja's South African atchaar business, website chefmotso.com, "
                  "shop chefmotso.sumupstore.com",
     ["chef motso", "chef mods", "chef modzo", "chef mozzo", "chef moto", "chef motto", "chef mo so", "chef matso",
      "shift motso", "chef modso", "chef motor", "chef mots", "jeff motso", "chef motzo"]),
    ("Kgomotso Maja", "the owner of ChefMotso and TKS Consulting work",
     ["kgomotso", "gomotso", "comotso", "go motso", "khomotso", "homotso", "kgomo"]),
    ("TKS Consulting", "a Kinetic client: TKS Consulting Limited, finance and assurance; its draft website is "
                       "tks-draft-3.alfredw-lsx.workers.dev",
     ["tks", "t k s", "tee kay ess", "takes consulting", "tks consulting", "t.k.s"]),
    ("Sthombo Mgobhozi", "comments on the TKS website brief",
     ["sthombo", "stombo", "stumbo", "s tombo", "thombo", "mgobhozi"]),
    ("Kinetic Web Designs", "the owner's web design business, kineticwebdesigns.co.uk",
     ["kinetic", "kinetic web design", "connective web designs", "kinetic web", "kenetic"]),
    ("Vera", "the HQ agent who checks and sends Kinetic's emails", ["vera", "vira", "vero"]),
    ("Hawk", "the HQ agent who finds new leads", ["hawk", "hork"]),
    ("Blade", "the HQ agent who writes the Instagram DM list", ["blade"]),
    ("Atchaar", "ChefMotso's product, South African mango pickle (Hot, Garlic and Mix)",
     ["achar", "atchar", "atchaar", "a char", "at char", "achaar"]),
    ("Higgsfield", "the image and video generation service", ["higgs field", "hicks field", "higgsfield"]),
]

_WORD = re.compile(r"[a-z0-9.']+")


def _words(text: str) -> list[str]:
    return _WORD.findall(str(text or "").lower())


def correct(text: str) -> str:
    """The text with misheard known names put back, e.g. "open chef modzo" -> "open ChefMotso". Phrases are compared
    one to four words at a time against every way a name has been heard; close matches count."""
    words = _words(text)
    if not words:
        return str(text or "")
    out, i = [], 0
    while i < len(words):
        best = None
        for n in (4, 3, 2, 1):
            phrase = " ".join(words[i:i + n])
            if len(words[i:i + n]) < n:
                continue
            for real, _, heard in KNOWN:
                options = heard + [real.lower()]
                if phrase in options or (len(phrase) >= 6 and difflib.get_close_matches(phrase, options, 1, 0.84)):
                    best = (n, real)
                    break
            if best:
                break
        if best:
            out.append(best[1])
            i += best[0]
        else:
            out.append(words[i])
            i += 1
    return " ".join(out)


def mentioned(text: str) -> list[str]:
    """The known names a piece of text refers to, after correction."""
    fixed = correct(text).lower()
    return [real for real, _, _ in KNOWN if real.lower() in fixed]


def prompt_section() -> str:
    lines = "; ".join(f"{real} ({what}; may be heard as {', '.join(heard[:4])})" for real, what, heard in KNOWN)
    return ("\n\nHearing names: the user talks to you through speech-to-text, which often gets unusual names wrong. "
            f"These are the real names you will hear about: {lines}. When a word or phrase sounds like one of these, "
            "assume it is that one and use the real spelling (for example 'chef mods' or 'chef modzo' means ChefMotso, "
            "so its website is chefmotso.com). If what you heard makes no sense, work out what was most likely meant "
            "from these names and the conversation before answering; ask only if two things fit equally. "
            "For anything about Kinetic Web Designs work, clients or status, search long_term_memory, which holds "
            "notes titled \"Claude's work log\" that Claude saves after every job it does for the user.")


SITES = ["chefmotso.com", "chefmotso.sumupstore.com", "kineticwebdesigns.co.uk", "tks-draft-3.alfredw-lsx.workers.dev"]


def fix_url(url: str) -> str:
    """A misheard web address put right: "https://chefmodzo.com" -> "https://chefmotso.com". Other sites are left
    alone; only a host that is very close to one of ours is changed."""
    from urllib.parse import urlparse, urlunparse
    try:
        parts = urlparse(url)
    except ValueError:
        return url
    host = (parts.netloc or "").lower()
    bare = host[4:] if host.startswith("www.") else host
    if not bare or bare in SITES:
        return url
    close = difflib.get_close_matches(bare, SITES, 1, 0.8)
    return urlunparse(parts._replace(netloc=close[0])) if close else url
