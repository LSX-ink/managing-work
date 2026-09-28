"""Windows PC control: clipboard, brightness, dark mode, windows, Wi-Fi, power, processes and Settings pages.

Windows calls (PowerShell with fixed scripts, ctypes, winreg) are only made on Windows; elsewhere the
Windows-only actions say so. User text never goes on a command line: it is passed to PowerShell on stdin.
Shutting down, restarting, sleeping, emptying the Recycle Bin and closing apps need confirmed: true.
"""

import os
import re
import socket
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import psutil

import memory
import pc
from config import Settings

WINDOWS = sys.platform == "win32"
ONLY_WINDOWS = "That only works on Windows."
CONFIRM = "Ask the user to confirm first, then call again with confirmed set to true."
PS_TIMEOUT = 20
UTF8 = "[Console]::InputEncoding=[Text.Encoding]::UTF8;[Console]::OutputEncoding=[Text.Encoding]::UTF8;"

SYSTEM_ACTIONS = ["clipboard_read", "clipboard_copy", "brightness_get", "brightness_set", "dark_mode", "light_mode",
                  "sound_device", "uptime", "top_processes", "downloads_usage", "open_settings"]
WINDOW_ACTIONS = ["list", "switch", "minimise_all", "screenshot"]
POWER_ACTIONS = ["sleep", "restart", "shutdown", "cancel_shutdown", "empty_recycle_bin", "close_app"]
NETWORK_ACTIONS = ["wifi", "ip_and_internet"]

SETTINGS_PAGES = {
    "display": "ms-settings:display", "sound": "ms-settings:sound", "bluetooth": "ms-settings:bluetooth",
    "wifi": "ms-settings:network-wifi", "updates": "ms-settings:windowsupdate", "apps": "ms-settings:appsfeatures",
    "storage": "ms-settings:storagesense", "notifications": "ms-settings:notifications",
    "power": "ms-settings:powersleep",
}
PROTECTED = {"explorer", "csrss", "winlogon", "svchost", "lsass", "smss", "services", "wininit", "system",
             "registry", "dwm", "fontdrvhost", "spoolsv", "python", "pythonw", "py", "idle"}
PERSONALIZE = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
MAX_CLIPBOARD = 4000


def tool_definitions() -> list[dict]:
    confirmed = {"type": "boolean", "description": "Set true only after the user has said yes to this."}
    return [
        {
            "name": "pc_system",
            "description": "Windows PC: read the clipboard or copy text to it; screen brightness; dark or light mode; "
                           "the sound device; uptime and last boot; top processes by memory and CPU; biggest files in "
                           "Downloads; open a Windows Settings page.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": SYSTEM_ACTIONS},
                    "text": {"type": "string", "description": "clipboard_copy: the text to copy."},
                    "level": {"type": "integer", "minimum": 0, "maximum": 100, "description": "brightness_set: percent."},
                    "target": {"type": "string", "enum": ["both", "apps", "system"],
                               "description": "dark_mode/light_mode: what to change. Default both."},
                    "page": {"type": "string", "enum": list(SETTINGS_PAGES)},
                },
                "required": ["action"],
                "additionalProperties": False,
            },
        },
        {
            "name": "pc_windows",
            "description": "Windows PC: list open windows, switch to one by name, minimise everything (show the "
                           "desktop), or save a screenshot into a memory folder.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": WINDOW_ACTIONS},
                    "name": {"type": "string", "description": "switch: part of the window title, e.g. 'Chrome'."},
                    "folder": {"type": "string", "description": "screenshot: memory folder. Default Screenshots."},
                },
                "required": ["action"],
                "additionalProperties": False,
            },
        },
        {
            "name": "pc_power",
            "description": "Windows PC: sleep, restart or shut down (60 second delay), cancel a pending shutdown, "
                           "empty the Recycle Bin, or close an app by name. Everything except cancel_shutdown needs "
                           "confirmed true, set only after the user says yes.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": POWER_ACTIONS},
                    "name": {"type": "string", "description": "close_app: the app, e.g. 'chrome' or 'spotify.exe'."},
                    "confirmed": confirmed,
                },
                "required": ["action"],
                "additionalProperties": False,
            },
        },
        {
            "name": "pc_network",
            "description": "The PC's Wi-Fi network name and signal, or its local IP address and whether the "
                           "internet is reachable.",
            "input_schema": {
                "type": "object",
                "properties": {"action": {"type": "string", "enum": NETWORK_ACTIONS}},
                "required": ["action"],
                "additionalProperties": False,
            },
        },
    ]


NAMES = {t["name"] for t in tool_definitions()}


# ---- Windows plumbing ----------------------------------------------------------------

def powershell(script: str, stdin: str = "") -> subprocess.CompletedProcess:
    """Run a fixed PowerShell script; any user text goes in on stdin."""
    return subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", UTF8 + script],
                          input=stdin, capture_output=True, text=True, encoding="utf-8", timeout=PS_TIMEOUT)


def user32():
    import ctypes
    return ctypes.windll.user32  # type: ignore[attr-defined]


def shell32():
    import ctypes
    return ctypes.windll.shell32  # type: ignore[attr-defined]


def winreg_module():
    import winreg  # type: ignore[import-not-found]
    return winreg


# ---- clipboard, brightness, theme, sound ---------------------------------------------

def clipboard_read() -> str:
    text = powershell("Get-Clipboard -Raw").stdout.strip()
    if not text:
        return "The clipboard is empty, or holds something that isn't text."
    if len(text) > MAX_CLIPBOARD:
        text = text[:MAX_CLIPBOARD] + " […truncated]"
    return f"On the clipboard: {text}"


def clipboard_copy(text: str) -> str:
    if not text:
        raise ValueError("There's no text to copy.")
    result = powershell("Set-Clipboard -Value ([Console]::In.ReadToEnd())", stdin=text)
    if result.returncode:
        return "I couldn't copy that to the clipboard."
    return "Copied to the clipboard."


NO_BRIGHTNESS = "This screen doesn't let Windows change its brightness; desktop monitors usually use their own buttons."


def brightness_get() -> str:
    out = powershell("(Get-CimInstance -Namespace root/WMI -ClassName WmiMonitorBrightness "
                     "-ErrorAction Stop | Select-Object -First 1).CurrentBrightness").stdout.strip()
    return f"The screen brightness is {out}%." if out.isdigit() else NO_BRIGHTNESS


def brightness_set(level) -> str:
    if level is None:
        raise ValueError("Say a brightness from 0 to 100.")
    level = max(0, min(int(level), 100))
    result = powershell("$l=[int]([Console]::In.ReadToEnd()); Get-CimInstance -Namespace root/WMI -ClassName "
                        "WmiMonitorBrightnessMethods -ErrorAction Stop | Invoke-CimMethod -MethodName WmiSetBrightness "
                        "-Arguments @{Timeout=1; Brightness=$l} -ErrorAction Stop | Out-Null", stdin=str(level))
    return NO_BRIGHTNESS if result.returncode else f"Set the screen brightness to {level}%."


def set_theme(dark: bool, target: str = "both") -> str:
    winreg = winreg_module()
    target = target if target in ("apps", "system") else "both"
    values = {"apps": ["AppsUseLightTheme"], "system": ["SystemUsesLightTheme"],
              "both": ["AppsUseLightTheme", "SystemUsesLightTheme"]}[target]
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, PERSONALIZE, 0, winreg.KEY_SET_VALUE) as key:
        for value in values:
            winreg.SetValueEx(key, value, 0, winreg.REG_DWORD, 0 if dark else 1)
    what = {"apps": "apps", "system": "Windows", "both": "Windows and apps"}[target]
    return f"Switched {what} to {'dark' if dark else 'light'} mode."


def sound_device() -> str:
    out = powershell("Get-CimInstance Win32_SoundDevice | Where-Object Status -eq 'OK' | "
                     "ForEach-Object { $_.Name }").stdout
    names = [line.strip() for line in out.splitlines() if line.strip()]
    return f"Sound devices: {', '.join(names)}." if names else "I couldn't find a working sound device."


def open_settings(page: str) -> str:
    uri = SETTINGS_PAGES.get(str(page or "").casefold().strip())
    if not uri:
        return f"I can open these Settings pages: {', '.join(SETTINGS_PAGES)}."
    os.startfile(uri)  # type: ignore[attr-defined]
    return f"Opened the {page} settings."


# ---- uptime, processes, Downloads ----------------------------------------------------

def uptime() -> str:
    booted = psutil.boot_time()
    hours = int((time.time() - booted) // 3600)
    days, hours = divmod(hours, 24)
    since = datetime.fromtimestamp(booted).strftime("%A %d %B at %H:%M")
    span = f"{days} day{'s' * (days != 1)} and {hours} hour{'s' * (hours != 1)}" if days else f"{hours} hour{'s' * (hours != 1)}"
    return f"The PC has been on for {span}, since {since}."


def top_processes(count: int = 5) -> str:
    procs = list(psutil.process_iter(["name", "memory_info"]))
    for p in procs:
        try:
            p.cpu_percent(None)
        except psutil.Error:
            pass
    time.sleep(0.5)
    rows = []
    cores = psutil.cpu_count() or 1
    for p in procs:
        try:
            rows.append((p.info["name"] or "?", (p.info["memory_info"].rss if p.info["memory_info"] else 0),
                         p.cpu_percent(None) / cores))
        except psutil.Error:
            continue
    by_mem = sorted(rows, key=lambda r: r[1], reverse=True)[:count]
    by_cpu = sorted(rows, key=lambda r: r[2], reverse=True)[:count]
    mem = ", ".join(f"{n} ({m / 2**20:,.0f} MB)" for n, m, _ in by_mem)
    cpu = ", ".join(f"{n} ({c:.0f}%)" for n, _, c in by_cpu)
    return f"Most memory: {mem}. Most CPU: {cpu}."


def human_size(size: float) -> str:
    for unit in ("bytes", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:,.0f} {unit}" if unit == "bytes" else f"{size:,.1f} {unit}"
        size /= 1024
    return f"{size:,.1f} GB"


def downloads_usage(limit: int = 10, max_entries: int = 100_000) -> str:
    folder = pc.resolve_folder("downloads")
    if not folder:
        return "I couldn't find a Downloads folder."
    files: list[tuple[int, Path]] = []
    total = 0
    for dirpath, dirnames, filenames in os.walk(folder):
        dirnames[:] = [d for d in dirnames if d not in pc.SKIP_DIRS]
        for name in filenames:
            path = Path(dirpath) / name
            try:
                size = path.stat().st_size
            except OSError:
                continue
            total += size
            files.append((size, path))
            if len(files) >= max_entries:
                break
    biggest = sorted(files, key=lambda f: f[0], reverse=True)[:limit]
    lines = [f"Downloads holds {len(files)} files using {human_size(total)}."]
    lines += [f"- {p.relative_to(folder)}: {human_size(s)}" for s, p in biggest]
    return "\n".join(lines)


# ---- windows -------------------------------------------------------------------------

def window_titles() -> list[tuple[int, str]]:
    """(handle, title) of visible top-level windows that have a title."""
    import ctypes

    u = user32()
    found: list[tuple[int, str]] = []
    proto = getattr(ctypes, "WINFUNCTYPE", ctypes.CFUNCTYPE)

    def visit(hwnd, _):
        if u.IsWindowVisible(hwnd):
            length = u.GetWindowTextLengthW(hwnd)
            if length:
                buf = ctypes.create_unicode_buffer(length + 1)
                u.GetWindowTextW(hwnd, buf, length + 1)
                if buf.value.strip() and buf.value not in ("Program Manager",):
                    found.append((hwnd, buf.value))
        return True

    u.EnumWindows(proto(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)(visit), 0)
    return found


def list_windows() -> str:
    titles = [t for _, t in window_titles()]
    return "Open windows:\n" + "\n".join(f"- {t}" for t in titles) if titles else "No windows are open."


def switch_window(name: str) -> str:
    q = str(name or "").casefold().strip()
    if not q:
        raise ValueError("Say which window to switch to.")
    windows = window_titles()
    hits = [w for w in windows if q in w[1].casefold()]
    if not hits:
        return f"No open window matches {name!r}. Open: {', '.join(t for _, t in windows[:8]) or 'none'}."
    hwnd, title = hits[0]
    u = user32()
    if u.IsIconic(hwnd):
        u.ShowWindow(hwnd, 9)  # SW_RESTORE
    u.keybd_event(0x12, 0, 0, 0)  # a tap of Alt lets Windows hand over the foreground
    u.keybd_event(0x12, 0, 2, 0)
    u.SetForegroundWindow(hwnd)
    return f"Switched to {title}."


def minimise_all() -> str:
    powershell("(New-Object -ComObject Shell.Application).MinimizeAll()")
    return "Minimised all windows."


def screenshot(settings: Settings, folder: str = "") -> str:
    from PIL import ImageGrab  # imported lazily: optional on headless machines

    if str(folder or "").strip():
        target = memory.folder(settings, folder)
    else:
        target = memory.root(settings) / "Screenshots"
        target.mkdir(parents=True, exist_ok=True)
    image = ImageGrab.grab(all_screens=True)
    path = memory.unique_path(target / f"Screenshot {datetime.now():%Y-%m-%d %H-%M-%S}.png")
    image.save(path, format="PNG")
    return f"Saved a screenshot to the {target.name} folder as {path.name}."


# ---- power, recycle bin, closing apps ------------------------------------------------

def power(action: str) -> str:
    if action == "sleep":
        powershell("Add-Type -AssemblyName System.Windows.Forms; "
                   "[System.Windows.Forms.Application]::SetSuspendState('Suspend', $false, $false) | Out-Null")
        return "Putting the PC to sleep."
    if action == "cancel_shutdown":
        result = subprocess.run(["shutdown", "/a"], capture_output=True, text=True, timeout=PS_TIMEOUT)
        return "Cancelled the shutdown." if result.returncode == 0 else "There was no shutdown or restart to cancel."
    flag = "/r" if action == "restart" else "/s"
    subprocess.run(["shutdown", flag, "/t", "60"], capture_output=True, text=True, timeout=PS_TIMEOUT)
    word = "Restarting" if action == "restart" else "Shutting down"
    return f"{word} in 60 seconds. Say cancel the shutdown to stop it."


def empty_recycle_bin() -> str:
    result = shell32().SHEmptyRecycleBinW(None, None, 0x7)  # no confirmation, progress or sound
    if result == 0:
        return "Emptied the Recycle Bin."
    return "The Recycle Bin is already empty." if result & 0xFFFFFFFF == 0x8000FFFF else "I couldn't empty the Recycle Bin."


def own_pids() -> set[int]:
    pids = {os.getpid()}
    try:
        pids |= {p.pid for p in psutil.Process().parents()}
    except psutil.Error:
        pass
    return pids


def close_app(name: str) -> str:
    key = re.sub(r"\.exe$", "", str(name or "").casefold().strip())
    if not key:
        raise ValueError("Say which app to close.")
    if key in PROTECTED or key.startswith("python"):
        return f"I won't close {name}: Windows or Jarvis itself needs it."
    matches = [p for p in psutil.process_iter(["name"])
               if re.sub(r"\.exe$", "", (p.info["name"] or "").casefold()) == key]
    if not matches:
        return f"{name} isn't running."
    if own_pids() & {p.pid for p in matches}:
        return f"I won't close {name}: Jarvis itself is running in it."
    closed = 0
    for p in matches:
        try:
            p.terminate()
            closed += 1
        except psutil.Error:
            pass
    psutil.wait_procs(matches, timeout=3)
    if not closed:
        return f"Windows wouldn't let me close {name}."
    return f"Closed {name}" + (f" ({closed} windows or processes)." if closed > 1 else ".")


# ---- network -------------------------------------------------------------------------

def wifi() -> str:
    out = subprocess.run(["netsh", "wlan", "show", "interfaces"], capture_output=True, text=True,
                         timeout=PS_TIMEOUT).stdout
    ssid = re.search(r"^\s*SSID\s*:\s*(.+)$", out, re.MULTILINE)
    signal = re.search(r"^\s*Signal\s*:\s*(\d+)%", out, re.MULTILINE)
    if not ssid:
        return "The PC isn't connected to Wi-Fi (it may be on a cable)."
    return f"Connected to {ssid.group(1).strip()}" + (f" with {signal.group(1)}% signal." if signal else ".")


def local_ip() -> str:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.connect(("1.1.1.1", 80))  # picks the outgoing interface; no packet is sent
        return s.getsockname()[0]


def internet_up() -> bool:
    try:
        socket.create_connection(("1.1.1.1", 443), timeout=3).close()
        return True
    except OSError:
        return False


def ip_and_internet() -> str:
    try:
        ip = local_ip()
    except OSError:
        ip = ""
    online = internet_up()
    where = f"The PC's local IP address is {ip}. " if ip else "The PC has no network address. "
    return where + ("The internet is reachable." if online else "The internet isn't reachable right now.")


# ---- dispatch ------------------------------------------------------------------------

WINDOWS_ONLY = {"clipboard_read", "clipboard_copy", "brightness_get", "brightness_set", "dark_mode", "light_mode",
                "sound_device", "open_settings", "list", "switch", "minimise_all", "sleep", "restart", "shutdown",
                "cancel_shutdown", "empty_recycle_bin", "wifi"}
NEEDS_CONFIRM = {"sleep", "restart", "shutdown", "empty_recycle_bin", "close_app"}


def run_tool(name: str, args: dict, settings: Settings) -> str:
    """Dispatch one call (blocking; call from a worker thread)."""
    action = args.get("action")
    allowed = {"pc_system": SYSTEM_ACTIONS, "pc_windows": WINDOW_ACTIONS,
               "pc_power": POWER_ACTIONS, "pc_network": NETWORK_ACTIONS}.get(name, [])
    if action not in allowed:
        raise ValueError(f"Unknown action {action!r} for {name}.")
    if action in WINDOWS_ONLY and not WINDOWS:
        return ONLY_WINDOWS
    if action in NEEDS_CONFIRM and args.get("confirmed") is not True:
        return CONFIRM
    handlers = {
        "clipboard_read": clipboard_read,
        "clipboard_copy": lambda: clipboard_copy(args.get("text") or ""),
        "brightness_get": brightness_get,
        "brightness_set": lambda: brightness_set(args.get("level")),
        "dark_mode": lambda: set_theme(True, args.get("target") or "both"),
        "light_mode": lambda: set_theme(False, args.get("target") or "both"),
        "sound_device": sound_device,
        "uptime": uptime,
        "top_processes": top_processes,
        "downloads_usage": downloads_usage,
        "open_settings": lambda: open_settings(args.get("page") or ""),
        "list": list_windows,
        "switch": lambda: switch_window(args.get("name") or ""),
        "minimise_all": minimise_all,
        "screenshot": lambda: screenshot(settings, args.get("folder") or ""),
        "sleep": lambda: power("sleep"),
        "restart": lambda: power("restart"),
        "shutdown": lambda: power("shutdown"),
        "cancel_shutdown": lambda: power("cancel_shutdown"),
        "empty_recycle_bin": empty_recycle_bin,
        "close_app": lambda: close_app(args.get("name") or ""),
        "wifi": wifi,
        "ip_and_internet": ip_and_internet,
    }
    try:
        return handlers[action]()
    except subprocess.TimeoutExpired:
        return "Windows took too long to answer, so I gave up."
