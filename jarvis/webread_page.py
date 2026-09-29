"""Reading help: the shape of a page. Its headings as an outline to jump to, its links in plain words, its pictures
with their descriptions (and the ones with none flagged), and a quick fact sheet. Works on a public web page (url)
or a .txt/.md file (headings only). Fetching is webread_extract.py, which re-checks every link is public.
"""

from urllib.parse import unquote, urlparse

import httpx

import screen
import webread_extract as ex
from config import Settings

ACTIONS = ["headings", "links", "images", "about"]
VAGUE = {"click here", "here", "read more", "more", "learn more", "link", "this", "continue", "find out more"}
MAX_LINKS = 40


def jump_say(page: dict, heading: str) -> str:
    if page.get("url"):
        return f"Read {page['url']} from the heading {heading}."
    if page.get("filename"):
        return f"Read the file {page['filename']} from {page.get('folder') or 'my memory folders'}, starting at the heading {heading}."
    return ""


def headings(page: dict) -> screen.Shown:
    found = [b for b in page["blocks"] if b["k"].startswith("h")]
    if not found:
        raise ValueError("That has no headings, just running text.")
    items = [{"label": ("" if b["k"] in ("h1", "h2") else "└ ") + b["t"], "say": jump_say(page, b["t"])} for b in found[:80]]
    card = screen.card("list", f"Outline: {page['title']}"[:80], "webread-outline", items=items,
                       text="Tap a heading to hear the page from there.")
    return screen.Shown(f"{page['title']} has {len(found)} headings, starting with {found[0]['t']}. Tap one to read from there.", card)


def link_label(link: dict) -> str:
    host = (urlparse(link["href"]).hostname or "").removeprefix("www.")
    tail = unquote(urlparse(link["href"]).path.strip("/").split("/")[-1])[:40]
    text = link["text"]
    if text.lower().strip(" .!>›»") in VAGUE:
        return f"{text} (unclear, goes to {host}/{tail})"
    return f"{text} ({host})"


def links(page: dict) -> screen.Shown:
    seen, main, menu = set(), [], []
    for x in page["links"]:
        if x["href"] in seen or not x["href"].startswith("http"):
            continue
        seen.add(x["href"])
        (menu if x["menu"] else main).append(x)
    shown = (main + menu)[:MAX_LINKS]
    if not shown:
        raise ValueError("I couldn't find any links on that.")
    items = [{"label": link_label(x) + (" [menu]" if x["menu"] else ""), "say": f"Read the page {x['href']} on screen."}
             for x in shown]
    card = screen.card("list", f"Links: {page['title']}"[:80], "webread-links", items=items,
                       text=f"{len(main)} links in the page, {len(menu)} in menus. Tap one to read it.")
    return screen.Shown(f"I found {len(main)} links in the page and {len(menu)} in its menus; tap one to read it.", card)


def picture_name(src: str) -> str:
    return unquote(urlparse(src).path.rsplit("/", 1)[-1])[:50] or "picture"


def images(page: dict) -> screen.Shown:
    found = page["images"]
    if not found:
        raise ValueError("I couldn't find any pictures on that page.")
    rows, missing = [], 0
    for i, img in enumerate(found[:60], 1):
        if img["alt"]:
            note = img["alt"]
        elif img["decorative"]:
            note = "(decorative, no description needed)"
        else:
            note, missing = "NO DESCRIPTION", missing + 1
        rows.append([str(i), picture_name(img["src"]), note])
    card = screen.card("table", f"Pictures: {page['title']}"[:80], "webread-images", columns=["#", "Picture", "Description"],
                       rows=rows, text=f"{missing} of {len(rows)} pictures have no description." if missing else "Every picture is described.")
    said = f"There are {len(found)} pictures; " + (f"{missing} have no description." if missing else "all have descriptions.")
    return screen.Shown(said + (f" The first: {found[0]['alt']}." if found[0]["alt"] else ""), card)


def about(page: dict) -> screen.Shown:
    text = ex.plain(page["blocks"])
    count = len(ex.words_in(text))
    minutes = max(1, round(count / 200))
    undescribed = sum(1 for i in page["images"] if not i["alt"] and not i["decorative"])
    rows = [["Title", page["title"]], ["Site", page.get("site") or "your text"], ["Language", page.get("lang") or "not stated"],
            ["Words", f"{count:,}"], ["Reading time", f"about {minutes} min"],
            ["Headings", str(sum(1 for b in page["blocks"] if b["k"].startswith("h")))],
            ["Paragraphs", str(sum(1 for b in page["blocks"] if not b["k"].startswith("h")))],
            ["Pictures", f"{len(page['images'])} ({undescribed} with no description)"], ["Links", str(len(page["links"]))]]
    buttons = [{"label": "Read aloud", "say": f"Read {page['url']} aloud."}] if page.get("url") else []
    card = screen.card("table", f"About: {page['title']}"[:80], "webread-about", columns=["", ""], rows=rows, buttons=buttons)
    return screen.Shown(f"{page['title']} is about {count:,} words, roughly {minutes} minutes to read.", card)


def tool_definitions() -> list[dict]:
    return [{
        "name": "web_read_outline",
        "description": "Reading aid showing the shape of a public web page (url) or .txt/.md memory file (folder + "
                       "filename). headings: outline to tap and jump to; links: the page's links in plain words, "
                       "unclear ones flagged; images: each picture's description, flagging pictures with none; "
                       "about: words, reading time, headings, pictures and links at a glance.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "url": {"type": "string"},
                "folder": {"type": "string"},
                "filename": {"type": "string"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"web_read_outline"}


async def run_tool(name: str, args: dict, settings: Settings, http: httpx.AsyncClient):
    action = args.get("action")
    if action not in ACTIONS:
        raise ValueError(f"Pick one of: {', '.join(ACTIONS)}.")
    args = {k: v for k, v in args.items() if k in ("url", "folder", "filename")}
    page = await ex.source(settings, http, args)
    return {"headings": headings, "links": links, "images": images, "about": about}[action](page)
