"""How the PC is doing (CPU, memory, disk, battery) and which of Jarvis's features are set up.

watch() also keeps an eye on things by itself every few minutes: the drive filling up, memory staying full, the
Kinetic HQ dashboard and the website going down (HQ is restarted once by itself first). Each problem is said once
(and pushed to the phone), again after a few hours if it's still there, and "all clear" when it's fixed."""

import asyncio
import os
import shutil
import subprocess
import time
from pathlib import Path

import httpx
import psutil

import agenda
from config import Settings


def pc_health() -> str:
    cpu = psutil.cpu_percent(interval=0.5)
    mem = psutil.virtual_memory()
    disk = shutil.disk_usage(Path.home().anchor or "/")
    parts = [f"CPU {cpu:.0f}% busy", f"memory {mem.percent:.0f}% used ({mem.available / 2**30:.1f} GB free)",
             f"main drive {disk.used / disk.total:.0%} full ({disk.free / 2**30:.0f} GB free)"]
    battery = psutil.sensors_battery() if hasattr(psutil, "sensors_battery") else None
    if battery:
        parts.append(f"battery {battery.percent:.0f}%{' charging' if battery.power_plugged else ''}")
    busiest = sorted(psutil.process_iter(["name", "memory_percent"]), key=lambda p: p.info["memory_percent"] or 0,
                     reverse=True)[:3]
    names = ", ".join(f"{p.info['name']} ({p.info['memory_percent']:.0f}%)" for p in busiest if p.info["name"])
    warnings = [w for w, bad in (("memory is nearly full", mem.percent > 90),
                                 ("the drive is nearly full", disk.free < 10 * 2**30),
                                 ("the CPU is very busy", cpu > 90)) if bad]
    return ("; ".join(parts) + f". Using the most memory: {names}."
            + (f" Warning: {', '.join(warnings)}." if warnings else " All looks healthy."))


HEALTH_EVERY = 600  # seconds between checks
HEALTH_FIRST = 120  # after a start, so a quick restart never alerts
HEALTH_REPEAT = 6 * 3600  # a problem that stays is said again after this long
LOW_DISK_GB = 10
FULL_MEMORY = 92  # percent, two checks in a row
STARTUP = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
SITES = {"hq": ("The Kinetic HQ dashboard", "http://127.0.0.1:8341/", "Kinetic HQ (hidden).vbs"),
         "site": ("kineticwebdesigns.co.uk", "https://kineticwebdesigns.co.uk/", "")}


async def _up(http: httpx.AsyncClient, url: str) -> bool:
    try:
        return (await http.get(url, timeout=20, follow_redirects=True)).status_code < 500
    except httpx.HTTPError:
        return False


def _restart(script: str) -> bool:
    path = STARTUP / script
    if not script or not path.exists():
        return False
    subprocess.Popen(["wscript.exe", str(path)])
    return True


async def problems(http: httpx.AsyncClient, state: dict, sites=None, restart=_restart, wait: float = 20) -> dict[str, str]:
    """What's wrong right now, by key -> a sentence. `state` carries memory readings between checks."""
    found = {}
    disk = shutil.disk_usage(Path.home().anchor or "/")
    if disk.free < LOW_DISK_GB * 2**30:
        found["disk"] = f"the main drive is nearly full, only {disk.free / 2**30:.0f} GB left"
    mem = psutil.virtual_memory().percent
    if mem > FULL_MEMORY and state.get("mem_high"):
        found["memory"] = f"memory has stayed {mem:.0f}% full, so things will be slow"
    state["mem_high"] = mem > FULL_MEMORY
    for key, (name, url, script) in (SITES if sites is None else sites).items():
        if await _up(http, url):
            continue
        if restart(script):
            await asyncio.sleep(wait)
            if await _up(http, url):
                print(f"[jarvis] {name} was down; restarted it.", flush=True)
                continue
        found[key] = f"{name} isn't answering" + (" even after a restart" if script else "")
    return found


def health_news(found: dict[str, str], said: dict[str, float], now: float, address: str = "sir") -> str:
    """The sentence to say for this check (new or long-standing problems, and fixes), updating `said`."""
    new = [found[k] for k in found if now - said.get(k, -HEALTH_REPEAT) >= HEALTH_REPEAT]
    fixed = [k for k in said if k not in found]
    for k in fixed:
        del said[k]
    for k in found:
        if now - said.get(k, -HEALTH_REPEAT) >= HEALTH_REPEAT:
            said[k] = now
    parts = []
    if new:
        parts.append(f"{address.capitalize()}, a health check: " + "; ".join(new) + ".")
    if fixed and not new:
        parts.append(f"All clear, {address}: " + ("that's fixed now." if len(fixed) == 1 else "those are fixed now."))
    return " ".join(parts)


async def watch(settings: Settings, announce) -> None:
    """Check every HEALTH_EVERY seconds and say what's gone wrong (or right again)."""
    await asyncio.sleep(HEALTH_FIRST)
    state, said = {}, {}
    async with httpx.AsyncClient(headers={"User-Agent": "Alfred health check"}) as http:
        while True:
            try:
                if text := health_news(await problems(http, state), said, time.time(), settings.user_address):
                    await announce(text, "health")
            except Exception as exc:  # a check that breaks must not stop the watcher
                print(f"[jarvis] Health check: {exc!r}", flush=True)
            await asyncio.sleep(HEALTH_EVERY)


def status(settings: Settings) -> str:
    """Which features are on, and what's missing, in plain words. Never reveals keys or passwords."""
    def on(flag: bool, yes: str, no: str) -> str:
        return f"- {yes}" if flag else f"- {no}"
    lines = [
        on(bool(settings.city), f"Weather: on, for {settings.city}.", "Weather: no home city (set JARVIS_CITY)."),
        on(settings.email_enabled, "Email: set up (deliveries, inbox summary, filing rules).",
           "Email: not set up (JARVIS_EMAIL_ADDRESS and JARVIS_EMAIL_APP_PASSWORD)."),
        on(agenda.configured(settings), "Calendar: connected.", "Calendar: not connected (JARVIS_CALENDAR_URL)."),
        on(bool(settings.elevenlabs_api_key), "Voice: ElevenLabs.", "Voice: the browser's own voice (ELEVENLABS_API_KEY for a better one)."),
        on(bool(settings.github_token), "New abilities: filed automatically.", "New abilities: open a page to click Submit (JARVIS_GITHUB_TOKEN to automate)."),
        on(bool(settings.password), "Login password: on.", "Login password: off (fine on this PC only)."),
        on(settings.enable_pc, "PC control: on.", "PC control: off."),
        on(settings.enable_web, "Web search: on.", "Web search: off."),
        on(settings.tasks_file != "", "Task list: connected.", "Task list: none (JARVIS_TASKS_FILE)."),
    ]
    return "Jarvis setup:\n" + "\n".join(lines)


def tool_definitions() -> list[dict]:
    empty = {"type": "object", "properties": {}, "additionalProperties": False}
    return [
        {"name": "pc_health", "description": "How the PC is doing: CPU, memory, disk space, battery and which apps "
                                            "use the most memory. For 'why is my PC slow?' or 'how much space do I have?'.",
         "input_schema": empty},
        {"name": "jarvis_status", "description": "Which of your own features are set up and what's missing from "
                                                "the .env file, for 'what can you do?' or 'is my email set up?'.",
         "input_schema": empty},
    ]


NAMES = {"pc_health", "jarvis_status"}


def run_tool(name: str, settings: Settings) -> str:
    return pc_health() if name == "pc_health" else status(settings)
