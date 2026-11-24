"""Play: "play Blinding Lights" starts it playing, instead of just searching (owner, 24 Nov 2026: "instead of just
searching if i say play plays").

- Spotify (the default when the Spotify app is on the PC): opens Spotify's search for it, then presses the Play
  button on the top result, read with Windows UI Automation, and checks the music started.
- YouTube (videos, or when Spotify isn't there or can't find it): finds the first video for the search and opens it
  in the user's browser, where it starts by itself.
- Apple Music: the existing apple_music tool opens the song in the app.
"""

import asyncio
import os
import re
import sys
import time
import webbrowser
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import quote, quote_plus

import httpx

from config import Settings

NAMES = {"play"}
APPS = ["auto", "spotify", "youtube"]
WINDOWS = sys.platform == "win32"
VIDEO_ID = re.compile(r'"videoId":"([\w-]{11})"')
WAIT = 9.0  # seconds for Spotify's results to appear
_pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="alfred-play")


def tool_definitions() -> list[dict]:
    return [{
        "name": "play",
        "description": "Play a song, artist, album, playlist, podcast or video right away when the user says "
                       "'play ...' ('play Blinding Lights', 'play some Drake', 'play lo-fi beats', 'play the Arsenal "
                       "highlights'). It starts playing; never just search when they say play. app auto (default) "
                       "uses Spotify for music when it's on the PC and YouTube otherwise; use youtube for videos, "
                       "clips, trailers, highlights or when they say YouTube. For pause, skip and volume use "
                       "media_control.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "What to play, e.g. 'Blinding Lights The Weeknd'."},
                "app": {"type": "string", "enum": APPS},
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    }]


# ---- plain logic (tested anywhere) ---------------------------------------------------------------------------

def clean_query(query: str) -> str:
    """'play some Drake on Spotify please' -> 'Drake'."""
    q = re.sub(r"\s+", " ", str(query or "")).strip()
    q = re.sub(r"^(?:alfred,?\s+)?(?:can you\s+|could you\s+|please\s+)?(?:play|put on|stick on)\s+", "", q, flags=re.I)
    q = re.sub(r"\s+(?:on|in|from|using)\s+(?:spotify|youtube|you tube)\b.*$", "", q, flags=re.I)
    q = re.sub(r"\s+(?:please|for me|now)$", "", q, flags=re.I)
    q = re.sub(r"^(?:some|a bit of|a little|me some|me)\s+", "", q, flags=re.I)
    return q.strip(" .!?")


def is_video(query: str) -> bool:
    return bool(re.search(r"\b(?:video|videos|clip|clips|trailer|highlights|episode|film|movie|vlog|tutorial|"
                          r"youtube|you tube|live stream|stream)\b", query or "", re.I))


def first_video(html: str) -> str | None:
    m = VIDEO_ID.search(html or "")
    return m.group(1) if m else None


def pick_play_button(names: list[str]) -> int | None:
    """Of the buttons on Spotify's results page (in screen order), the one that plays the top result.

    The player bar has a bare 'Play' (or 'Pause') first; results have 'Play <title>' or a bare 'Play' on the top
    result card, which comes after the first 'More options for ...' button."""
    seen_result = False
    for i, name in enumerate(names):
        low = name.lower()
        if low.startswith("more options for "):
            seen_result = True
        elif low.startswith("play ") and len(name) > 5:
            return i
        elif low == "play" and seen_result:
            return i
    return None


# ---- Spotify -------------------------------------------------------------------------------------------------

def spotify_installed() -> bool:
    if not WINDOWS:
        return False
    try:
        import winreg
        winreg.CloseKey(winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, "spotify"))  # desktop and Store versions
        return True
    except OSError:
        pass
    return Path(os.path.expandvars(r"%APPDATA%\Spotify\Spotify.exe")).exists()


def _spotify_job(query: str) -> str | None:
    """Runs on the worker thread. Returns what played, or None if it couldn't."""
    import desktop
    desktop._com_init()
    auto = desktop._auto()
    os.startfile("spotify:search:" + quote(query))
    deadline = time.time() + WAIT
    win = None
    while time.time() < deadline:
        win = desktop.match_window(desktop._all_windows(), "spotify")
        if win:
            break
        time.sleep(0.5)
    if not win:
        return None
    time.sleep(1.2)
    desktop._bring(win)  # Spotify only shows its results to UI Automation when it's in front
    words = [w for w in re.findall(r"[a-z0-9']+", query.lower()) if len(w) > 2][:3]
    while time.time() < deadline + 4:
        root = auto.ControlFromHandle(win["hwnd"])
        buttons, controls = [], []
        found_words = False
        for c, _d in auto.WalkControl(root, includeTop=False, maxDepth=60):
            name = (c.Name or "").strip()
            if words and any(w in name.lower() for w in words):
                found_words = True
            if c.ControlTypeName == "ButtonControl" and name:
                buttons.append(name)
                controls.append(c)
        pick = pick_play_button(buttons) if (found_words or not words) else None
        if pick is not None:
            button = controls[pick]
            try:
                button.GetInvokePattern().Invoke()
            except Exception:
                button.Click(simulateMove=False)
            title = buttons[pick][5:].strip() or query
            time.sleep(1.5)
            playing = any((c.Name or "") == "Pause" and c.ControlTypeName == "ButtonControl"
                          for c, _d in auto.WalkControl(auto.ControlFromHandle(win["hwnd"]), includeTop=False,
                                                        maxDepth=30))
            return title if playing else title + " (it may need a moment to start)"
        time.sleep(0.8)
    return None


# ---- YouTube -------------------------------------------------------------------------------------------------

async def youtube(http: httpx.AsyncClient, query: str) -> str:
    url = "https://www.youtube.com/results?search_query=" + quote_plus(query)
    vid = None
    try:
        r = await http.get(url, headers={"User-Agent": "Mozilla/5.0", "Accept-Language": "en-GB,en;q=0.8"},
                           timeout=10, follow_redirects=True)
        vid = first_video(r.text)
    except Exception:
        pass
    if not vid:
        await asyncio.to_thread(webbrowser.open, url)
        return f"I couldn't pick a video, so I've opened the YouTube results for '{query}'."
    await asyncio.to_thread(webbrowser.open, f"https://www.youtube.com/watch?v={vid}")
    return f"Playing '{query}' on YouTube in your browser."


async def run_tool(name: str, args: dict, settings: Settings, http=None) -> str:
    if not getattr(settings, "enable_pc", True):
        raise ValueError("PC control is switched off (JARVIS_ENABLE_PC).")
    query = clean_query(args.get("query", ""))
    if not query:
        raise ValueError("What should I play?")
    app = args.get("app") or "auto"
    if app == "auto":
        app = "youtube" if is_video(args.get("query", "")) or not spotify_installed() else "spotify"
    if app == "spotify":
        try:
            played = await asyncio.get_running_loop().run_in_executor(_pool, _spotify_job, query)
        except Exception:
            played = None
        if played:
            return f"Playing {played} on Spotify."
        if args.get("app") == "spotify":
            return f"Spotify opened its search for '{query}', but I couldn't press play. Say 'click play' and I'll try."
    own = http is None
    http = http or httpx.AsyncClient()
    try:
        return await youtube(http, query)
    finally:
        if own:
            await http.aclose()
