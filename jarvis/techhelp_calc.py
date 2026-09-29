"""Tech helper, numbers and the home network list: file sizes, how many files fit, download times, screen sharpness
and resolution facts, and a list of the devices on your home network that you type in yourself.

The network list is only what you tell Alfred (name, IP address, notes) in techhelp-network.json in the memory
folder. Nothing is scanned and nothing goes online.
"""

import ipaddress
import math

import homestore as hs
import screen
import techhelp_store as store
from config import Settings

NETWORK = "techhelp-network.json"
ACTIONS = ["filesize", "fit", "download_time", "screen_size", "resolution", "network_add", "network_list",
           "network_remove"]
UNITS = {"b": 1, "kb": 1000, "mb": 1000 ** 2, "gb": 1000 ** 3, "tb": 1000 ** 4}
NAMED = {(1280, 720): "720p HD", (1920, 1080): "1080p Full HD", (2560, 1440): "1440p QHD",
         (3440, 1440): "Ultrawide QHD", (3840, 2160): "4K Ultra HD", (7680, 4320): "8K", (1366, 768): "HD laptop",
         (2560, 1080): "Ultrawide Full HD", (1600, 900): "HD+", (2880, 1800): "Retina laptop"}
SCALES = [100, 125, 150, 175, 200, 225, 250, 300]


def tool_definitions() -> list[dict]:
    num = {"type": "number"}
    unit = {"type": "string", "enum": ["B", "KB", "MB", "GB", "TB"]}
    return [{
        "name": "techhelp_calc",
        "description": "Tech calculators and the home network list. filesize (size + unit: convert to all units), "
                       "fit (how many files of size + unit fit in capacity + capacity_unit, e.g. photos on a "
                       "phone), download_time (size + unit at speed_mbps, and at other speeds), screen_size "
                       "(diagonal_inches + width_px + height_px: sharpness in PPI, physical size, aspect ratio, "
                       "Windows scaling), resolution (width_px + height_px, or nothing for a table of common "
                       "resolutions). network_add (name, ip, kind, note: the user's own device list, never scanned), "
                       "network_list, network_remove (name; confirmed true only after the user confirms).",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "size": num, "unit": unit, "capacity": num, "capacity_unit": unit,
                "speed_mbps": {**num, "description": "Connection speed in megabits per second."},
                "diagonal_inches": num, "width_px": {"type": "integer"}, "height_px": {"type": "integer"},
                "name": {"type": "string", "description": "Network device name, e.g. 'Living room TV'."},
                "ip": {"type": "string", "description": "IP address the user gave, e.g. 192.168.1.20."},
                "kind": {"type": "string"}, "note": {"type": "string"},
                "confirmed": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"techhelp_calc"}


def _bytes(value, unit, what: str = "size") -> float:
    key = str(unit or "MB").lower()
    if key not in UNITS:
        raise ValueError("Use B, KB, MB, GB or TB.")
    return hs.number(value, what, 0, 1e18) * UNITS[key]


def _nice(n: float) -> str:
    if n >= 1e6 or (0 < n < 0.001):
        return f"{n:.3g}"
    return f"{n:,.4f}".rstrip("0").rstrip(".") if n < 100 else f"{n:,.0f}"


def _size_text(b: float) -> str:
    for name in ("TB", "GB", "MB", "KB"):
        if b >= UNITS[name.lower()]:
            return f"{b / UNITS[name.lower()]:.2f} {name}"
    return f"{b:.0f} B"


def _duration(seconds: float) -> str:
    if seconds < 1:
        return "under a second"
    if seconds < 90:
        return f"{seconds:.0f} seconds"
    if seconds < 5400:
        return f"{seconds / 60:.0f} minutes"
    if seconds < 172800:
        return f"{seconds / 3600:.1f} hours"
    return f"{seconds / 86400:.1f} days"


# ---- files and downloads ----------------------------------------------------------------------

def filesize(args: dict) -> screen.Shown:
    b = _bytes(args.get("size"), args.get("unit"))
    rows = [[u.upper(), _nice(b / v), _nice(b / 1024 ** i)] for i, (u, v) in enumerate(UNITS.items())]
    return screen.Shown(f"That's {_size_text(b)}, or {_nice(b * 8)} bits.", screen.card(
        "table", "File size", "techhelp-filesize", columns=["Unit", "Decimal (1000)", "Binary (1024)"], rows=rows,
        text="Windows and storage makers count differently: a '500 GB' drive shows as about 465 GB in Windows."))


def fit(args: dict) -> screen.Shown:
    cap = _bytes(args.get("capacity"), args.get("capacity_unit"), "capacity")
    one = _bytes(args.get("size"), args.get("unit"), "file size")
    if one <= 0:
        raise ValueError("The file size must be more than zero.")
    count = math.floor(cap / one)
    rows = [["Capacity", _size_text(cap)], ["Each file", _size_text(one)], ["Files that fit", f"{count:,}"],
            ["Left over", _size_text(cap - count * one)]]
    return screen.Shown(f"About {count:,} files of {_size_text(one)} fit in {_size_text(cap)}.", screen.card(
        "table", "How many fit", "techhelp-fit", columns=["", ""], rows=rows))


def download_time(args: dict) -> screen.Shown:
    b = _bytes(args.get("size"), args.get("unit"))
    speed = hs.number(args.get("speed_mbps"), "speed", 0.001, 100000)
    seconds = b * 8 / (speed * 1e6)
    real = seconds / 0.9
    rows = [[f"{s:g} Mbps" + (" (yours)" if s == speed else ""), _duration(b * 8 / (s * 1e6) / 0.9)]
            for s in sorted({speed, 10, 50, 100, 500, 1000})]
    return screen.Shown(f"{_size_text(b)} at {speed:g} Mbps takes about {_duration(real)}.", screen.card(
        "table", "Download time", "techhelp-download", columns=["Speed", "Time"], rows=rows,
        text="Includes about 10% for overheads. Speeds are megabits, files are megabytes: divide Mbps by 8."))


# ---- screens ---------------------------------------------------------------------------------

def _ratio(w: int, h: int) -> str:
    g = math.gcd(w, h)
    a, b = w // g, h // g
    for x, y in ((16, 9), (16, 10), (21, 9), (4, 3), (3, 2), (32, 9)):
        if abs(w / h - x / y) < 0.02:
            return f"{x}:{y}"
    return f"{a}:{b}"


def _dims(args: dict) -> tuple[int, int]:
    w = int(hs.number(args.get("width_px"), "width", 1, 20000))
    h = int(hs.number(args.get("height_px"), "height", 1, 20000))
    return w, h


def screen_size(args: dict) -> screen.Shown:
    w, h = _dims(args)
    diag = hs.number(args.get("diagonal_inches"), "screen size", 1, 200)
    ppi = math.hypot(w, h) / diag
    wi = diag * w / math.hypot(w, h)
    hi = diag * h / math.hypot(w, h)
    scale = min(SCALES, key=lambda s: abs(s - ppi / 96 * 100)) if ppi > 96 else 100
    look = "crisp, like a phone" if ppi >= 300 else "very sharp" if ppi >= 200 else "sharp" if ppi >= 110 else "a bit coarse up close"
    rows = [["Sharpness", f"{ppi:.0f} PPI ({look})"], ["Size", f"{wi * 2.54:.1f} by {hi * 2.54:.1f} cm ({wi:.1f} by {hi:.1f} in)"],
            ["Aspect ratio", _ratio(w, h)], ["Pixels", f"{w * h / 1e6:.1f} megapixels"],
            ["Windows scaling to try", f"{scale}%"]]
    return screen.Shown(f"A {diag:g} inch {w} by {h} screen is {ppi:.0f} pixels per inch, {look}. Try {scale}% scaling.",
                        screen.card("table", "Screen size", "techhelp-screen", columns=["", ""], rows=rows))


def resolution(args: dict) -> screen.Shown:
    if args.get("width_px") is None and args.get("height_px") is None:
        rows = [[name, f"{w} x {h}", _ratio(w, h), f"{w * h / 1e6:.1f}"] for (w, h), name in sorted(NAMED.items(), key=lambda x: x[0][0] * x[0][1])]
        return screen.Shown("Here are the common screen resolutions.", screen.card(
            "table", "Common resolutions", "techhelp-resolutions", columns=["Name", "Pixels", "Shape", "Megapixels"], rows=rows))
    w, h = _dims(args)
    name = NAMED.get((w, h), "custom size")
    times = w * h / (1920 * 1080)
    rows = [["Name", name], ["Aspect ratio", _ratio(w, h)], ["Megapixels", f"{w * h / 1e6:.2f}"],
            ["Compared with Full HD", f"{times:.2g} times the pixels"]]
    return screen.Shown(f"{w} by {h} is {name}, shape {_ratio(w, h)}, {w * h / 1e6:.1f} megapixels.", screen.card(
        "table", f"{w} x {h}", "techhelp-resolution", columns=["", ""], rows=rows))


# ---- home network list -----------------------------------------------------------------------

def network_add(settings: Settings, args: dict) -> str:
    found = store.rows(settings, NETWORK)
    name = hs.need(args.get("name"), "device name", 40)
    try:
        ip = ipaddress.ip_address(hs.clean(args.get("ip")))
    except ValueError:
        raise ValueError("Give the IP address like 192.168.1.20.") from None
    clash = next((k for k, v in found.items() if v.get("ip") == str(ip) and k.lower() != name.lower()), None)
    if clash:
        raise ValueError(f"{clash} already has {ip}. Two devices can't share an address.")
    key = next((k for k in found if k.lower() == name.lower()), name)
    store.put(settings, NETWORK, found, key, {"ip": str(ip), "kind": hs.clean(args.get("kind"), 30),
                                             "note": hs.clean(args.get("note"), 120)})
    extra = "" if ip.is_private else " Note that isn't a home-style address."
    return f"Saved {key} at {ip}.{extra}"


def network_list(settings: Settings) -> screen.Shown:
    found = store.rows(settings, NETWORK)
    if not found:
        return screen.Shown("Your network list is empty. Tell me a device name and its IP address to add it.",
                            screen.card("text", "Home network", "techhelp-network", text="No devices yet."))
    ordered = sorted(found.items(), key=lambda kv: int(ipaddress.ip_address(kv[1]["ip"])))
    rows = [[k, v["ip"], v.get("kind", ""), v.get("note", "")] for k, v in ordered]
    return screen.Shown(f"{len(rows)} devices on your network list.", screen.card(
        "table", "Home network", "techhelp-network", columns=["Device", "IP address", "Type", "Note"], rows=rows,
        text="Just the list you gave me; I never scan your network."))


def run_tool(name: str, args: dict, settings: Settings, http=None):
    action = args.get("action")
    if action == "filesize":
        return filesize(args)
    if action == "fit":
        return fit(args)
    if action == "download_time":
        return download_time(args)
    if action == "screen_size":
        return screen_size(args)
    if action == "resolution":
        return resolution(args)
    if action == "network_add":
        return network_add(settings, args)
    if action == "network_list":
        return network_list(settings)
    if action == "network_remove":
        return store.remove(settings, NETWORK, args.get("name"), "device", bool(args.get("confirmed")))
    raise ValueError(f"Unknown action {action}.")
