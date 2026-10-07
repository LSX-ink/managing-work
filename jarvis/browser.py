"""Alfred's own web browser (Playwright): he opens a real browser window on the PC and drives it himself, opening
pages, reading them, clicking links and buttons, filling in search boxes and taking screenshots to look at.

It uses Microsoft Edge (already on every Windows PC), then Chrome, then Playwright's own Chromium if neither is there
(python -m playwright install chromium). The window is visible unless JARVIS_BROWSER_HEADLESS is true, so the user
can watch, and it keeps its own profile in the memory folder (memory/.browser), so a site the user logs into there
stays logged in. Playwright's objects belong to the thread that made them, so every step runs on one worker thread.

Safety: Alfred never types into password or card-number fields (the user does that in the window), and he asks before
any click that buys, pays, sends, posts or deletes something.
"""

import asyncio
import base64
import os
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlparse

from config import Settings

NAMES = {"web_browser"}
ACTIONS = ["open", "read", "click", "type", "scroll", "back", "screenshot", "close"]
MAX_TEXT = 6000
MAX_ITEMS = 60
CHANNELS = ("msedge", "chrome", None)  # None is Playwright's bundled Chromium
TIMEOUT_MS = 20000
SECRET_TYPES = {"password"}
SECRET_HINTS = ("password", "passcode", "card number", "cardnumber", "cc-number", "cvv", "cvc", "security code", "pin")
RISKY_WORDS = ("buy", "pay", "checkout", "place order", "purchase", "send", "post", "publish", "delete", "remove",
               "subscribe", "confirm order", "transfer")

# Every visible link, button and box gets a number (data-alfred-id) so Alfred can say "click 12" or "type into 4".
MARK = """() => {
  const seen = [];
  const els = document.querySelectorAll('a[href], button, input, textarea, select, [role=button], [role=link], [contenteditable=true]');
  let n = 0;
  for (const el of els) {
    el.removeAttribute('data-alfred-id');
    const r = el.getBoundingClientRect();
    const style = getComputedStyle(el);
    if (r.width < 2 || r.height < 2 || style.visibility === 'hidden' || style.display === 'none') continue;
    if (el.type === 'hidden') continue;
    n += 1;
    el.setAttribute('data-alfred-id', String(n));
    const tag = el.tagName.toLowerCase();
    const label = (el.innerText || el.value || el.getAttribute('aria-label') || el.getAttribute('placeholder')
                   || el.getAttribute('title') || el.getAttribute('name') || el.getAttribute('alt') || '').trim();
    const box = ['input', 'textarea', 'select'].includes(tag) || el.isContentEditable;
    seen.push({id: n, kind: box ? 'box' : (tag === 'a' ? 'link' : 'button'), label: label.replace(/\\s+/g, ' ').slice(0, 80),
               type: (el.getAttribute('type') || '').toLowerCase(),
               auto: (el.getAttribute('autocomplete') || '').toLowerCase(),
               name: ((el.getAttribute('name') || '') + ' ' + (el.getAttribute('id') || '') + ' ' + (el.getAttribute('placeholder') || '')).toLowerCase()});
  }
  return seen;
}"""

_pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="alfred-browser")
_state: dict = {"pw": None, "context": None, "page": None, "items": [], "engine": ""}


def tool_definitions() -> list[dict]:
    return [{
        "name": "web_browser",
        "description": "Alfred's own web browser, a real window on the user's PC that he drives himself (Playwright): "
                       "'open bbc.co.uk', 'search Amazon for running shoes', 'go to my bank's opening hours page', "
                       "'what does that page say', 'click the second result', 'scroll down', 'go back', 'take a "
                       "look at the page'. open (url) loads a page and returns its text plus a numbered list of its "
                       "links, buttons and boxes; click (target: a number from that list, or the visible text) and "
                       "type (target, text, submit true to press Enter) work on those numbers; read gives the current "
                       "page's text again; scroll (direction up/down); back; screenshot returns a picture of the page "
                       "for you to look at; close shuts the window. Use it when the user wants something done on a "
                       "website or a page read that the quick page reader can't load. Never type passwords or card "
                       "details (tell the user to type those in the window themselves), and ask the user before any "
                       "click that buys, pays, sends, posts or deletes something (then call again with confirmed).",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "url": {"type": "string", "description": "open: the address, e.g. bbc.co.uk or https://..."},
                "target": {"type": "string", "description": "click or type: a number from the page's list, or the "
                                                            "visible text of the link, button or box."},
                "text": {"type": "string", "description": "type: what to type."},
                "submit": {"type": "boolean", "description": "type: press Enter afterwards (e.g. to search)."},
                "direction": {"type": "string", "enum": ["down", "up"]},
                "confirmed": {"type": "boolean", "description": "click: the user said yes to a buy/pay/send/delete click."},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


def normalise_url(url: str) -> str:
    """bbc.co.uk -> https://bbc.co.uk; only web addresses (no file:, javascript: or data: pages)."""
    url = (url or "").strip()
    if not url:
        raise ValueError("Which page should I open?")
    if "://" not in url:
        if re.match(r"^[a-zA-Z][\w+.-]*:(?!\d)", url):  # javascript:, data:, mailto: and the like
            raise ValueError("I can only open web addresses (http or https).")
        url = "https://" + url
    parts = urlparse(url)
    if parts.scheme not in ("http", "https") or not parts.netloc:
        raise ValueError("I can only open web addresses (http or https).")
    return url


def is_secret(item: dict) -> bool:
    """A password, card number, CVV or PIN box: Alfred never types into these."""
    if item.get("type") in SECRET_TYPES or item.get("auto", "").startswith("cc-") or item.get("auto") in (
            "current-password", "new-password", "one-time-code"):
        return True
    words = f"{item.get('label', '')} {item.get('name', '')}".lower()
    return any(h in words for h in SECRET_HINTS)


def is_risky(label: str) -> bool:
    """A click that buys, pays, sends, posts or deletes: Alfred asks the user first."""
    return bool(re.search(r"\b(" + "|".join(RISKY_WORDS) + r")\b", label.lower()))


def find_item(items: list[dict], target: str, boxes: bool = False) -> dict:
    """The page item a target means: its number, or the best match for its visible text."""
    target = (target or "").strip()
    if not items:
        raise ValueError("Open a page first.")
    pool = [i for i in items if (i["kind"] == "box") == boxes] or items
    if target.isdigit():
        for item in items:
            if item["id"] == int(target):
                return item
        raise ValueError(f"There's no item {target} on this page.")
    if not target:
        if boxes and pool:
            return pool[0]  # the first box: usually the search box
        raise ValueError("Say which link or button.")
    low = target.lower()
    for test in (lambda l: l == low, lambda l: l.startswith(low), lambda l: low in l):
        for item in pool:
            if test(item["label"].lower()):
                return item
    raise ValueError(f"I can't see '{target}' on this page.")


def item_lines(items: list[dict]) -> str:
    rows = [f"[{i['id']}] {i['kind']}: {i['label'] or '(no label)'}" for i in items[:MAX_ITEMS]]
    more = f"\n... and {len(items) - MAX_ITEMS} more" if len(items) > MAX_ITEMS else ""
    return "\n".join(rows) + more


def headless(settings: Settings) -> bool:
    return str(os.getenv("JARVIS_BROWSER_HEADLESS", "")).strip().lower() in ("1", "true", "yes", "on")


# ---- the browser itself (all on the worker thread) ---------------------------------------------------------

def _start(settings: Settings):
    if _state["page"] is not None and not _state["page"].is_closed():
        return _state["page"]
    if _state["context"] is not None:
        _close()
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise ValueError("The browser isn't installed yet. In the jarvis folder run: pip install -r requirements.txt "
                         "then restart Alfred.") from None
    _state["pw"] = sync_playwright().start()
    profile = Path(settings.memory_dir) / ".browser"
    profile.mkdir(parents=True, exist_ok=True)
    last = None
    for channel in CHANNELS:
        try:
            context = _state["pw"].chromium.launch_persistent_context(
                str(profile), channel=channel, headless=headless(settings), viewport={"width": 1280, "height": 860})
            _state["engine"] = channel or "chromium"
            break
        except Exception as exc:  # that browser isn't on this PC: try the next
            last = exc
    else:
        _state["pw"].stop()
        _state["pw"] = None
        raise ValueError("I couldn't start a browser. Install Microsoft Edge or Chrome, or run: python -m playwright "
                         f"install chromium ({str(last).splitlines()[0][:120]})")
    context.set_default_timeout(TIMEOUT_MS)
    _state["context"] = context
    _state["page"] = context.pages[0] if context.pages else context.new_page()
    return _state["page"]


def _page():
    page = _state["page"]
    if page is None or page.is_closed():
        raise ValueError("The browser isn't open. Open a page first.")
    return page


def _snapshot(page, with_text: bool = True) -> str:
    try:
        page.wait_for_load_state("domcontentloaded", timeout=TIMEOUT_MS)
    except Exception:
        pass
    _state["items"] = page.evaluate(MARK)
    text = ""
    if with_text:
        try:
            text = page.inner_text("body", timeout=5000)
        except Exception:
            text = ""
        text = "\n".join(line.strip() for line in text.splitlines() if line.strip())
        if len(text) > MAX_TEXT:
            text = text[:MAX_TEXT] + "\n... (more below: scroll or read again after scrolling)"
    return (f"Page: {page.title() or '(untitled)'}\nAddress: {page.url}\n\n"
            + (f"{text}\n\n" if with_text else "")
            + f"Links, buttons and boxes (use the numbers):\n{item_lines(_state['items'])}")


def _locator(page, item: dict):
    return page.locator(f'[data-alfred-id="{item["id"]}"]').first


def _close() -> str:
    for key in ("context", "pw"):
        thing = _state[key]
        if thing is not None:
            try:
                thing.close() if key == "context" else thing.stop()
            except Exception:
                pass
    _state.update(pw=None, context=None, page=None, items=[], engine="")
    return "Closed the browser."


def _run(action: str, args: dict, settings: Settings):
    if action == "close":
        return _close()
    if action == "open":
        page = _start(settings)
        page.goto(normalise_url(args.get("url", "")), wait_until="domcontentloaded")
        return _snapshot(page)
    page = _page()
    if action == "read":
        return _snapshot(page)
    if action == "back":
        page.go_back(wait_until="domcontentloaded")
        return _snapshot(page)
    if action == "scroll":
        page.mouse.wheel(0, -700 if args.get("direction") == "up" else 700)
        page.wait_for_timeout(300)
        return _snapshot(page)
    if action == "click":
        item = find_item(_state["items"], str(args.get("target", "")))
        if is_risky(item["label"]) and not args.get("confirmed"):
            return (f"'{item['label']}' could buy, send, post or delete something. Ask the user to confirm, then call "
                    "again with confirmed.")
        _locator(page, item).click()
        page.wait_for_timeout(500)
        return f"Clicked {item['label'] or 'item ' + str(item['id'])}.\n\n" + _snapshot(page)
    if action == "type":
        item = find_item(_state["items"], str(args.get("target", "")), boxes=True)
        if is_secret(item):
            return ("That's a password or card box. I never type those: ask the user to type it into the browser "
                    "window themselves.")
        box = _locator(page, item)
        box.fill(str(args.get("text", "")))
        if args.get("submit"):
            box.press("Enter")
            page.wait_for_timeout(800)
        return f"Typed into {item['label'] or 'box ' + str(item['id'])}.\n\n" + _snapshot(page)
    if action == "screenshot":
        shot = page.screenshot(type="jpeg", quality=70)
        return [{"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                             "data": base64.b64encode(shot).decode()}},
                {"type": "text", "text": f"The page as it looks now: {page.title()} ({page.url})."}]
    raise ValueError(f"Unknown browser action: {action}")


async def run_tool(name: str, args: dict, settings: Settings, http=None):
    action = args.get("action")
    if action not in ACTIONS:
        raise ValueError(f"Pick one of: {', '.join(ACTIONS)}.")
    loop = asyncio.get_running_loop()
    try:
        return await loop.run_in_executor(_pool, _run, action, args, settings)
    except ValueError:
        raise
    except Exception as exc:  # a timeout or a page that went away: say what happened in a line
        first = str(exc).strip().splitlines()[0] if str(exc).strip() else type(exc).__name__
        raise ValueError(f"The browser couldn't do that: {first[:200]}") from None
