"""Instant PC commands: "scroll down", "next tab", "close this tab", "go back", "press enter", "open Spotify",
"open Spotify and search Drake", "search YouTube for lo-fi" and the like.

The user asked (25 Nov 2026) for simple commands to happen at once, faster than doing it by hand, with no AI
thinking step. brain.Brain.handle checks these straight after the instant answers: a match is done on the spot
with a fixed key press or a mouse-wheel scroll, and anything else (or anything risky) goes to the AI as before.

Only plain whole commands match ("scroll down a bit", not "scroll down and click the second link"). Enter in an
email or messaging app is never pressed here: that goes to the AI, which asks first. Windows only.
"""

import asyncio
import re
import sys
import time

from config import Settings

WINDOWS = sys.platform == "win32"
WHEEL = 600  # one "scroll down": about five notches of the mouse wheel
AMOUNTS = {"a bit": 0.4, "a little": 0.4, "a little bit": 0.4, "slightly": 0.4, "a touch": 0.4, "more": 1.0,
           "a lot": 3.0, "loads": 3.0, "lots": 3.0, "a load": 3.0, "a page": 1.5, "way down": 3.0, "way up": 3.0}
TIMES = {"once": 1, "twice": 2, "two times": 2, "three times": 3, "thrice": 3, "four times": 4, "five times": 5}

_LEAD = re.compile(r"^(?:(?:hey|ok|okay|right|now|and|then|so|just|can you|could you|will you|please|alfred|alfie|"
                   r"jarvis)[,!]?\s+)+", re.I)
_TRAIL = re.compile(r"(?:[,\s]+(?:please|now|for me|thanks|thank you|alfred|mate|again))+$", re.I)
_SCROLL = re.compile(r"^(?:scroll|go|move)(?: the page)? (?P<dir>down|up|left|right)(?: the page)?"
                     r"(?: (?P<amount>a bit|a little(?: bit)?|slightly|a touch|more|a lot|loads|lots|a load|a page))?"
                     r"(?: (?P<times>once|twice|two times|three times|thrice|four times|five times|\d+ times))?$"
                     r"|^(?P<bare>scroll)(?: (?P<more>more|again))?$|^(?:keep scrolling|scroll more)$", re.I)

# (pattern, keys, what Alfred says, needs a browser in front)
KEYS = [
    (r"(?:next|the next|go to the next|switch to the next) tab", "ctrl+tab", "Next tab.", True),
    (r"(?:previous|last|the previous|the last|go to the previous|go back a) tab", "ctrl+shift+tab", "Previous tab.", True),
    (r"close (?:this|the|that|the current|my current|current) tab|close tab", "ctrl+w", "Closed it.", True),
    (r"(?:open )?(?:a )?new tab|open (?:a )?tab", "ctrl+t", "New tab.", True),
    (r"(?:re-?open|bring back|undo close)(?: the)? (?:last |closed |last closed )?tab", "ctrl+shift+t", "Brought it back.", True),
    (r"go back|back|go back a page|previous page|back a page", "alt+left", "Back.", True),
    (r"go forward|forward|next page|forward a page", "alt+right", "Forward.", True),
    (r"refresh|reload|refresh (?:the|this) page|reload (?:the|this) page", "f5", "Refreshed.", True),
    (r"go to (?:the )?top(?: of (?:the|this) page)?|top of (?:the|this) page|scroll (?:right )?to (?:the )?top|back to (?:the )?top",
     "home", "Top of the page.", False),
    (r"go to (?:the )?bottom(?: of (?:the|this) page)?|bottom of (?:the|this) page|scroll (?:right )?to (?:the )?bottom",
     "end", "Bottom of the page.", False),
    (r"page down", "pagedown", "Page down.", False),
    (r"page up", "pageup", "Page up.", False),
    (r"zoom in", "ctrl+=", "Zoomed in.", False),
    (r"zoom out", "ctrl+-", "Zoomed out.", False),
    (r"(?:reset|normal) zoom|zoom (?:to )?(?:normal|100(?: percent| %|%)?)", "ctrl+0", "Normal size.", False),
    (r"full ?screen|go full ?screen|exit full ?screen", "f11", "Done.", False),
    (r"press enter|hit enter|press return|enter", "enter", "Done.", False),
    (r"press escape|hit escape|escape|press esc", "esc", "Done.", False),
    (r"press tab|hit tab", "tab", "Done.", False),
    (r"press space|hit space|press the space ?bar", "space", "Done.", False),
    (r"press (?:delete|del)|hit delete", "delete", "Done.", False),
    (r"press backspace|hit backspace", "backspace", "Done.", False),
    (r"press (?:the )?(?:down|down arrow)", "down", "Done.", False),
    (r"press (?:the )?(?:up|up arrow)", "up", "Done.", False),
    (r"press (?:the )?(?:left|left arrow)", "left", "Done.", False),
    (r"press (?:the )?(?:right|right arrow)", "right", "Done.", False),
    (r"select all|highlight (?:it )?all|select everything", "ctrl+a", "Selected.", False),
    (r"copy(?: (?:that|it|this))?", "ctrl+c", "Copied.", False),
    (r"paste(?: (?:that|it|this))?", "ctrl+v", "Pasted.", False),
    (r"(?:find|search) (?:on |in )?(?:this|the) page", "ctrl+f", "Find box open.", False),
    (r"(?:switch|change) (?:app|apps|window|windows)|alt tab", "alt+tab", "Switched.", False),
    (r"show (?:me )?(?:the )?desktop|minimi[sz]e everything", "win+d", "Desktop.", False),
]
KEYS = [(re.compile(f"^(?:{p})$", re.I), keys, said, browser) for p, keys, said, browser in KEYS]
SENDS = {"enter", "ctrl+enter"}

_OPEN = re.compile(r"^(?:open|launch|start|load|bring up|pull up|run|fire up|switch to|go to)(?: up)? (?:the |my |up )?"
                   r"(?P<what>[\w .&'+-]{2,40}?)(?: app| application| program| window)?"
                   r"(?:,? (?:and|then|and then) (?:search|look up|find|search for|look for)(?: for)? (?P<q>.+))?$", re.I)
_SEARCH = re.compile(r"^(?:search|look up|find|look for)(?: on)? (?P<where>[\w ]{2,20}?) for (?P<q>.+)$"
                     r"|^(?:search|look up|find)(?: for)? (?P<q2>.+?) on (?P<where2>[\w ]{2,20})$"
                     r"|^google (?P<q3>.+)$", re.I)
NOT_APPS = re.compile(r"\b(?:tab|tabs|link|links|email|emails|message|messages|files? called|the file|it|that|this|them|"
                      r"door|window for|page|pages|the first|the second|the last|result|results)\b", re.I)
SITES = {"youtube": "https://www.youtube.com", "gmail": "https://mail.google.com", "netflix": "https://www.netflix.com",
         "amazon": "https://www.amazon.co.uk", "bbc": "https://www.bbc.co.uk", "bbc news": "https://www.bbc.co.uk/news",
         "facebook": "https://www.facebook.com", "instagram": "https://www.instagram.com",
         "tiktok": "https://www.tiktok.com", "google": "https://www.google.com", "google maps": "https://maps.google.com",
         "maps": "https://maps.google.com", "twitter": "https://x.com", "x": "https://x.com",
         "linkedin": "https://www.linkedin.com", "chatgpt": "https://chatgpt.com", "ebay": "https://www.ebay.co.uk",
         "wikipedia": "https://en.wikipedia.org", "github": "https://github.com", "reddit": "https://www.reddit.com",
         "whatsapp web": "https://web.whatsapp.com", "google drive": "https://drive.google.com",
         "my drive": "https://drive.google.com", "calendar": "https://calendar.google.com"}
# Apps whose search box UI Automation can't name: the key that opens their search.
SEARCH_KEYS = {"spotify": "ctrl+k", "discord": "ctrl+k", "slack": "ctrl+k", "whatsapp": "ctrl+f", "teams": "ctrl+e",
               "outlook": "ctrl+e", "code": "ctrl+p", "vs code": "ctrl+p", "steam": "ctrl+f", "file explorer": "ctrl+e",
               "explorer": "ctrl+e", "settings": "ctrl+e"}


def plain(text: str) -> str:
    said = re.sub(r"\s+", " ", (text or "").strip()).strip(" .!?,")
    for _ in range(3):
        said = _TRAIL.sub("", _LEAD.sub("", said)).strip(" .!?,")
    return said.lower()


def command(text: str) -> dict | None:
    """The instant command a phrase means, or None: {"scroll": direction, "amount": n} or {"keys", "say", "browser"}."""
    if not text or text.startswith("["):
        return None
    said = plain(text)
    if not said or len(said.split()) > 9:
        return None
    m = _SCROLL.match(said)
    if m:
        direction = (m.group("dir") or "down").lower()
        amount = AMOUNTS.get((m.group("amount") or "").lower(), 1.0)
        times = (m.group("times") or "").lower()
        if times:
            amount *= TIMES.get(times) or min(int(re.match(r"\d+", times).group()), 10)
        return {"scroll": direction, "amount": amount, "say": f"Scrolled {direction}."}
    for pattern, keys, say, browser in KEYS:
        if pattern.match(said):
            return {"keys": keys, "say": say, "browser": browser}
    m = re.match(r"^(?:search (?:for )?(?P<q>.+?) on (?:windows|my pc|the pc)|search (?:windows|my pc|the pc) for (?P<q2>.+))$", said)
    if m:
        return {"windows": (m.group("q") or m.group("q2")).strip()}
    m = _SEARCH.match(said)
    if m:
        where = (m.group("where") or m.group("where2") or "google").strip()
        query = (m.group("q") or m.group("q2") or m.group("q3") or "").strip()
        if where in ("it", "that", "this", "the web", "the internet", "online"):
            where = "google"
        return {"open": where, "query": query} if query and where not in ("windows", "my pc", "the pc") else None
    m = _OPEN.match(said)
    if m and not NOT_APPS.search(m.group("what")) and len(m.group("what").split()) <= 4:
        return {"open": m.group("what").strip(), "query": (m.group("q") or "").strip()}
    return None


def _wait_window(name: str, seconds: float = 8.0):
    import desktop
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        win = desktop.match_window(desktop._all_windows(), name)
        if win:
            return win
        time.sleep(0.3)
    return None


def _search_app(name: str, query: str) -> str:
    """Type the query into the app's own search: its search box, else its search key."""
    import desktop
    win = _wait_window(name)
    if not win:
        return f"Opened {name}, but its window didn't come up in time to search."
    desktop._bring(win)
    time.sleep(0.6)  # the app finishes drawing
    try:
        said = desktop._search_here({"text": query, "window": win["title"]})
    except Exception:
        said = "I can't find a search box"
    if not said.startswith("I can't find a search box"):
        return f"Searching {name} for {query}."
    key = SEARCH_KEYS.get(name.lower()) or SEARCH_KEYS.get(win.get("exe") or "")
    if not key:
        return f"I opened {name} but couldn't find its search box."
    desktop._keys(key)
    time.sleep(0.4)
    desktop._paste(query)
    time.sleep(0.2)
    desktop._keys("enter")
    return f"Searching {name} for {query}."


def _open(cmd: dict) -> str | None:
    """Already on the PC: bring its window up, else start the app, else a folder, else the website."""
    import webbrowser
    import desktop
    import pc
    name, query = cmd["open"], cmd.get("query") or ""
    low = name.lower()
    if query and (url := desktop.search_url(low, query)) and not pc.match_app(name, pc.installed_apps()):
        webbrowser.open(url)  # a website search: straight to the results page
        return f"Searching {name} for {query}."
    win = desktop.match_window(desktop._all_windows(), name)
    if win and not desktop.alfred_window(win["title"]):
        if not query:
            desktop._bring(win)
            return f"Here's {name}."
        return _search_app(name, query)
    app = pc.match_app(name, pc.installed_apps())
    if app:
        pc.open_app(app[0])
        return _search_app(app[0], query) if query else f"Opening {app[0]}."
    if low in pc.KNOWN_FOLDERS and not query:
        return pc.open_folder(low)
    if low in SITES and not query:
        webbrowser.open(SITES[low])
        return f"Opening {name}."
    if query and (url := desktop.search_url(low, query)):
        webbrowser.open(url)
        return f"Searching {name} for {query}."
    return None  # not on the PC: the AI works out what was meant


def _do(cmd: dict) -> str | None:
    """Runs on the desktop worker thread. None hands the request to the AI instead."""
    import desktop
    if "open" in cmd:
        return _open(cmd)
    if "windows" in cmd:
        desktop._search_windows(cmd["windows"])
        return f"Searching your PC for {cmd['windows']}."
    import pyautogui
    try:
        hwnd, title = desktop._front()
    except ValueError:
        return None
    if cmd.get("browser") and not desktop._browser_name(title):
        return None  # "go back" with no browser in front: let the AI work out what was meant
    if cmd.get("keys") in SENDS and desktop.is_outward(title):
        return None  # Enter could send an email or message: the AI asks first
    try:
        win = desktop._auto().ControlFromHandle(hwnd)
        win.SetActive()
    except Exception:
        win = None
    time.sleep(0.05)
    if "scroll" in cmd:
        if win is not None:
            rect = win.BoundingRectangle
            pyautogui.moveTo((rect.left + rect.right) // 2, (rect.top + rect.bottom) // 2)
        clicks = int(WHEEL * cmd["amount"])
        if cmd["scroll"] in ("up", "down"):
            pyautogui.scroll(clicks if cmd["scroll"] == "up" else -clicks)
        else:
            pyautogui.hscroll(clicks if cmd["scroll"] == "right" else -clicks)
    else:
        desktop._keys(cmd["keys"])
    return cmd["say"]


async def handle(text: str, settings: Settings) -> str | None:
    """Do an instant PC command and return what to say, or None when it isn't one (the AI takes it)."""
    if not WINDOWS or not getattr(settings, "enable_pc", True):
        return None
    cmd = command(text)
    if cmd is None:
        return None
    import desktop
    try:
        return await asyncio.get_running_loop().run_in_executor(desktop._pool, _do, cmd)
    except Exception as exc:  # missing part or a window that went away: the AI can still try
        print(f"[quickpc] {exc!r}", flush=True)
        return None
