"""Alfred's own long-term memory, powered by Claude Mem.

Claude Mem (github.com/thedotmack/claude-mem) is the memory plugin installed for Claude Code on this PC. Alfred runs
his OWN copy of its memory worker, with its own database in the alfred-mem folder next to this file and its own port
(37778 by default), so nothing he remembers mixes with Claude Code's memory (that one lives in ~/.claude-mem on 37777).

What it does:
- after every conversation turn, the exchange is saved to his memory, so he can look back at anything said before;
- facts he's told to remember about the user are saved there too;
- the long_term_memory tool searches it, lists the latest memories, or saves something on purpose;
- the newest memories are in his instructions when Jarvis starts, so he picks up where he left off.

Jarvis starts the worker itself the first time it's needed, using the scripts Claude Code installed. Turn it off with
JARVIS_ALFRED_MEM=false; move it with JARVIS_ALFRED_MEM_PORT. If Claude Mem isn't installed, Alfred says so and the
rest of Jarvis carries on as normal.
"""

import os
import re
import subprocess
import sys
import threading
from pathlib import Path

import httpx

from config import ROOT, Settings

NAMES = {"long_term_memory"}
ACTIONS = ["search", "recent", "save"]
PROJECT = "alfred"
TIMEOUT = 10.0
START_SECONDS = 120  # the first start can install the worker's own helpers
MAX_TEXT = 6000
MAX_SAVE = 4000
MAX_TURN_PART = 1500  # characters kept from each side of an exchange
PROMPT_MEMORIES = 8
NOT_INSTALLED = ("Claude Mem isn't installed on this PC, so I have no long-term memory yet. Install it with: "
                 "npx claude-mem install")
NOT_RUNNING = "My long-term memory didn't start. Restart Jarvis and try again."

_lock = threading.Lock()
_started = False
_snapshot = ""  # newest memories, taken once when Jarvis starts so the instructions stay the same all session


def enabled(settings: Settings) -> bool:
    return settings.alfred_mem


def base_url(settings: Settings) -> str:
    return f"http://127.0.0.1:{settings.alfred_mem_port}"


def data_dir() -> Path:
    return ROOT / "alfred-mem"


def _version_key(path: Path) -> tuple:
    return tuple(int(n) for n in re.findall(r"\d+", path.name)[:3]) + (0 if "-" in path.name else 1,)


def plugin_scripts() -> Path | None:
    """The scripts folder of the newest Claude Mem that Claude Code installed, or None."""
    claude = Path(os.getenv("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")
    cache = claude / "plugins" / "cache" / "thedotmack" / "claude-mem"
    versions = sorted((p for p in cache.glob("*") if p.is_dir() and not (p / ".orphaned_at").exists()
                       and re.match(r"\d", p.name)), key=_version_key, reverse=True) if cache.is_dir() else []
    for root in [*versions, claude / "plugins" / "marketplaces" / "thedotmack" / "plugin"]:
        for scripts in (root / "plugin" / "scripts", root / "scripts"):
            if (scripts / "worker-service.cjs").is_file() and (scripts / "bun-runner.js").is_file():
                return scripts
    return None


def worker_env(settings: Settings) -> dict:
    env = dict(os.environ)
    env.update({"CLAUDE_MEM_DATA_DIR": str(data_dir()), "CLAUDE_MEM_WORKER_PORT": str(settings.alfred_mem_port),
                "CLAUDE_MEM_WORKER_HOST": "127.0.0.1", "CLAUDE_MEM_ONLINE_OPTIN": "false"})
    return env


def healthy(settings: Settings) -> bool:
    try:
        return httpx.get(base_url(settings) + "/api/health", timeout=3).status_code == 200
    except httpx.HTTPError:
        return False


def ensure_running(settings: Settings) -> None:
    """Start Alfred's own memory worker if it isn't answering yet. ValueError if it can't."""
    global _started
    with _lock:
        if healthy(settings):
            _started = True
            return
        scripts = plugin_scripts()
        if not scripts:
            raise ValueError(NOT_INSTALLED)
        data_dir().mkdir(parents=True, exist_ok=True)
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0
        try:
            subprocess.run(["node", str(scripts / "bun-runner.js"), str(scripts / "worker-service.cjs"), "start"],
                           env=worker_env(settings), cwd=str(data_dir()), stdin=subprocess.DEVNULL,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,  # the worker keeps running after
                           timeout=START_SECONDS, creationflags=flags)
        except (OSError, subprocess.TimeoutExpired) as exc:
            print(f"[jarvis] Alfred's memory didn't start: {exc!r}", flush=True)
        if not healthy(settings):
            raise ValueError(NOT_RUNNING)
        _started = True


def _call(settings: Settings, method: str, path: str, **kwargs) -> httpx.Response:
    ensure_running(settings)
    try:
        r = httpx.request(method, base_url(settings) + path, timeout=TIMEOUT, **kwargs)
    except httpx.HTTPError:
        raise ValueError(NOT_RUNNING)
    if r.status_code >= 400:
        raise ValueError(f"My memory said no ({r.status_code}): {r.text[:200]}")
    return r


def _observations(settings: Settings, params: dict) -> list[dict]:
    params = {**params, "project": PROJECT, "type": "observations", "format": "json"}
    body = _call(settings, "GET", "/api/search", params=params).json()
    found = body.get("observations") if isinstance(body, dict) else None
    return [o for o in found or [] if isinstance(o, dict) and o.get("project") == PROJECT]


def as_lines(found: list[dict]) -> str:
    lines = []
    for o in found:
        when = str(o.get("created_at") or "")[:16].replace("T", " ")
        title = str(o.get("title") or "").strip()
        body = str(o.get("narrative") or o.get("text") or "").strip()
        lines.append(f"- {when} {title}: {body}" if body and body != title else f"- {when} {title}")
    text = "\n".join(lines)
    return text[:MAX_TEXT] + "\n[cut short]" if len(text) > MAX_TEXT else text


def search(settings: Settings, query: str, limit: int = 8) -> str:
    query = str(query or "").strip()
    if not query:
        raise ValueError("Say what to look for.")
    return as_lines(_observations(settings, {"query": query, "limit": limit})) or "Nothing about that in my memory."


def recent(settings: Settings, limit: int = 8) -> str:
    found = _observations(settings, {"limit": limit, "orderBy": "date_desc"})
    return as_lines(found) or "My long-term memory is empty so far."


def save(settings: Settings, text: str, title: str = "") -> str:
    text = str(text or "").strip()[:MAX_SAVE]
    if not text:
        raise ValueError("There's nothing to save.")
    body = {"text": text, "project": PROJECT}
    if str(title or "").strip():
        body["title"] = str(title).strip()[:120]
    _call(settings, "POST", "/api/memory/save", json=body)
    return "Saved to my long-term memory."


def _quietly(settings: Settings, text: str, title: str) -> None:
    if not enabled(settings):
        return
    try:
        save(settings, text, title)
    except ValueError as exc:
        print(f"[jarvis] Couldn't save to Alfred's memory: {exc}", flush=True)


def remember_turn(settings: Settings, user_text: str, reply: str) -> None:
    """Keep one exchange. Runs in a thread after each turn; never raises."""
    said = re.sub(r"^\(Local time: [^)]*\)\n", "", str(user_text or "")).strip()
    said = re.sub(r"^(\(You announced at [^)]*\)\n)+", "", said).strip()
    if not said or said.startswith("[activate]") or not str(reply or "").strip():
        return
    text = f"The user said: {said[:MAX_TURN_PART]}\nAlfred replied: {str(reply).strip()[:MAX_TURN_PART]}"
    title = said[:80] + ("..." if len(said) > 80 else "")
    _quietly(settings, text, title)


def remember_fact(settings: Settings, fact: str) -> None:
    _quietly(settings, f"About the user: {fact}", "Fact about the user")


def take_snapshot(settings: Settings) -> None:
    """Read the newest memories once (at start-up) for Alfred's instructions. Never raises."""
    global _snapshot
    if not enabled(settings):
        return
    try:
        _snapshot = as_lines(_observations(settings, {"limit": PROMPT_MEMORIES, "orderBy": "date_desc"}))
    except (ValueError, httpx.HTTPError) as exc:
        print(f"[jarvis] Alfred's memory isn't available: {exc}", flush=True)


def prompt_section(settings: Settings) -> str:
    if not enabled(settings):
        return ""
    newest = f" Your newest memories, from before this session:\n{_snapshot}" if _snapshot else ""
    return ("\n\nLong-term memory: everything said in past conversations is kept in your own long-term memory. When "
            "the user mentions something from before ('like I said last week', 'what did we decide about...'), or you "
            "don't know something they expect you to, search it with long_term_memory before saying you don't "
            f"remember. Save decisions, plans and finished work there on purpose too.{newest}")


def tool_definitions() -> list[dict]:
    return [{
        "name": "long_term_memory",
        "description": "Your own long-term memory (powered by Claude Mem): every past conversation is in it. search "
                       "(query) finds what was said or decided before ('what did I say about the TikTok plan', "
                       "'when did we talk about my car'); recent lists the newest memories; save (text, optional "
                       "title) keeps something on purpose, such as a decision, a plan or finished work. Search "
                       "before saying you don't remember. Lasting facts about the user still go to "
                       "remember_about_user (they are copied here automatically).",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "query": {"type": "string", "description": "search: what to look for, in a few words."},
                "text": {"type": "string", "description": "save: the memory, one or two clear sentences."},
                "title": {"type": "string", "description": "save: a short title (optional)."},
                "limit": {"type": "integer", "description": "search or recent: how many (default 8)."},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


def run_tool(name: str, args: dict, settings: Settings, http=None) -> str:
    if not enabled(settings):
        return "My long-term memory is turned off (JARVIS_ALFRED_MEM)."
    action = args.get("action")
    limit = min(max(int(args.get("limit") or 8), 1), 25)
    if action == "search":
        return search(settings, args.get("query", ""), limit)
    if action == "recent":
        return recent(settings, limit)
    if action == "save":
        return save(settings, args.get("text", ""), args.get("title", ""))
    raise ValueError(f"Unknown action; use one of {', '.join(ACTIONS)}.")
