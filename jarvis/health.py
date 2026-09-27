"""How the PC is doing (CPU, memory, disk, battery) and which of Jarvis's features are set up."""

import shutil
from pathlib import Path

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
