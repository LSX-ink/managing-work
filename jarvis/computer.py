"""Mouse-and-keyboard control for Claude's computer toolset (computer_toolset_20260801).

Claude sees downscaled screenshots of the main screen and gives coordinates in that
image's pixel space; this module scales them back to real screen pixels.
Moving the mouse into a screen corner aborts any action in progress (PyAutoGUI failsafe).
"""

import base64
import io
import math
import sys
import time

TOOLSET = "computer"
NOT_EXECUTED = "Not executed: an earlier computer action in this turn failed."

# Actions that only look or wait; everything else needs the user's OK.
PASSIVE = {"screenshot", "zoom", "cursor_position", "wait", "mouse_move"}

MAX_LONG_EDGE = 1568
MAX_PIXELS = 1_150_000
MAX_WAIT = 10.0

# xdotool-style key names Claude uses -> PyAutoGUI names.
KEY_NAMES = {
    "return": "enter", "kp_enter": "enter", "backspace": "backspace", "escape": "esc",
    "page_up": "pageup", "page_down": "pagedown", "prior": "pageup", "next": "pagedown",
    "super": "win", "super_l": "win", "meta": "win", "cmd": "command", "control": "ctrl",
    "control_l": "ctrl", "control_r": "ctrl", "alt_l": "alt", "alt_r": "alt",
    "shift_l": "shift", "shift_r": "shift", "caps_lock": "capslock", "print": "printscreen",
    "space": "space", "tab": "tab", "delete": "delete", "insert": "insert", "home": "home", "end": "end",
    "left": "left", "right": "right", "up": "up", "down": "down",
}
if sys.platform == "darwin":
    KEY_NAMES["super"] = KEY_NAMES["super_l"] = KEY_NAMES["meta"] = "command"


def scale_factor(width: int, height: int) -> float:
    """Downscale so screenshots fit the model's image limits."""
    return min(1.0, MAX_LONG_EDGE / max(width, height), math.sqrt(MAX_PIXELS / (width * height)))


def to_keys(combo: str) -> list[str]:
    keys = []
    for part in combo.replace(" ", "").split("+"):
        if not part:
            continue
        low = part.lower()
        keys.append(KEY_NAMES.get(low, low))
    return keys


def describe(name: str, args: dict) -> str:
    """A short plain-English line for the confirmation prompt."""
    at = f" at {tuple(args['coordinate'])}" if args.get("coordinate") else ""
    mods = f" holding {args['text']}" if args.get("text") and name.endswith(("click", "scroll", "drag")) else ""
    if name in ("left_click", "right_click", "middle_click", "double_click", "triple_click"):
        return f"{name.replace('_', ' ').capitalize()}{at}{mods}"
    if name == "left_click_drag":
        return f"Drag from {tuple(args.get('start_coordinate', []))} to {tuple(args.get('coordinate', []))}{mods}"
    if name == "type":
        text = args.get("text", "")
        return f"Type \"{text[:80]}{'…' if len(text) > 80 else ''}\""
    if name == "key":
        rep = f" ×{args['repeat']}" if args.get("repeat", 1) > 1 else ""
        return f"Press {args.get('text', '')}{rep}"
    if name == "hold_key":
        return f"Hold {args.get('text', '')} for {args.get('duration', 0)}s"
    if name == "scroll":
        return f"Scroll {args.get('scroll_direction')} {args.get('scroll_amount')}{at}{mods}"
    if name in ("left_mouse_down", "left_mouse_up"):
        return name.replace("_", " ").capitalize()
    return f"{name} {args}"


class Computer:
    def __init__(self):
        import pyautogui  # imported here: only needed when computer control is switched on

        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.05
        self.gui = pyautogui
        self._shot_size: tuple[int, int] | None = None  # full-size screenshot pixels, set on capture

    # -- geometry --------------------------------------------------------------
    # Claude's coordinates -> (÷ scale) screenshot pixels -> (× ratio) screen pixels.
    # The ratio is 1 unless display scaling makes screenshots differ from mouse coordinates.

    def _shot(self):
        from PIL import ImageGrab  # main screen only, matching PyAutoGUI's mouse coordinates

        shot = ImageGrab.grab()
        self._shot_size = shot.size
        return shot

    def _geometry(self) -> tuple[float, float, float]:
        gw, gh = self.gui.size()
        sw, sh = self._shot_size or (gw, gh)
        return scale_factor(sw, sh), gw / sw, gh / sh

    def _to_screen(self, coord) -> tuple[int, int]:
        s, rx, ry = self._geometry()
        gw, gh = self.gui.size()
        x, y = coord
        return (min(gw - 1, max(0, round(x / s * rx))), min(gh - 1, max(0, round(y / s * ry))))

    def _from_screen(self, x: float, y: float) -> tuple[int, int]:
        s, rx, ry = self._geometry()
        return round(x / rx * s), round(y / ry * s)

    @staticmethod
    def _jpeg_block(image) -> dict:
        buf = io.BytesIO()
        image.convert("RGB").save(buf, format="JPEG", quality=85)
        return {"type": "image",
                "source": {"type": "base64", "media_type": "image/jpeg", "data": base64.b64encode(buf.getvalue()).decode()}}

    def screenshot(self) -> list[dict]:
        shot = self._shot()
        s = scale_factor(*shot.size)
        if s < 1:
            shot = shot.resize((round(shot.width * s), round(shot.height * s)))
        return [self._jpeg_block(shot)]

    def zoom(self, region) -> list[dict]:
        from PIL import Image

        shot = self._shot()
        s = scale_factor(*shot.size)
        x0, y0, x1, y1 = (round(v / s) for v in region)
        crop = shot.crop((min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)))
        f = scale_factor(*crop.size)
        if f < 1:
            crop = crop.resize((round(crop.width * f), round(crop.height * f)), Image.LANCZOS)
        return [self._jpeg_block(crop)]

    # -- actions ---------------------------------------------------------------

    def _with_mods(self, mods: str | None, action) -> None:
        keys = to_keys(mods) if mods else []
        for k in keys:
            self.gui.keyDown(k)
        try:
            action()
        finally:
            for k in reversed(keys):
                self.gui.keyUp(k)

    def run(self, name: str, args: dict):
        """Execute one member action (blocking). Returns text or image content."""
        g = self.gui
        coord = self._to_screen(args["coordinate"]) if args.get("coordinate") else None
        clicks = {"left_click": ("left", 1), "right_click": ("right", 1), "middle_click": ("middle", 1),
                  "double_click": ("left", 2), "triple_click": ("left", 3)}

        if name == "screenshot":
            return self.screenshot()
        if name == "zoom":
            return self.zoom(args["region"])
        if name == "cursor_position":
            x, y = self._from_screen(*g.position())
            return f"X={x}, Y={y}"
        if name == "wait":
            time.sleep(min(float(args.get("duration", 1)), MAX_WAIT))
        elif name == "mouse_move":
            g.moveTo(*coord, duration=0.1)
        elif name in clicks:
            button, n = clicks[name]
            pos = coord or g.position()
            self._with_mods(args.get("text"), lambda: g.click(*pos, clicks=n, interval=0.08, button=button))
        elif name == "left_click_drag":
            start = self._to_screen(args["start_coordinate"])
            end = coord or g.position()

            def drag():
                g.moveTo(*start, duration=0.1)
                g.dragTo(*end, duration=0.4, button="left")
            self._with_mods(args.get("text"), drag)
        elif name == "left_mouse_down":
            g.mouseDown(button="left")
        elif name == "left_mouse_up":
            g.mouseUp(button="left")
        elif name == "type":
            g.write(args["text"], interval=0.01)
        elif name == "key":
            keys = to_keys(args["text"])
            for _ in range(max(1, min(int(args.get("repeat", 1)), 100))):
                g.hotkey(*keys)
        elif name == "hold_key":
            keys = to_keys(args["text"])
            for k in keys:
                g.keyDown(k)
            time.sleep(min(float(args.get("duration", 1)), MAX_WAIT))
            for k in reversed(keys):
                g.keyUp(k)
        elif name == "scroll":
            if coord:
                g.moveTo(*coord, duration=0.05)
            direction = args.get("scroll_direction", "down")
            amount = int(args.get("scroll_amount", 3))
            notches = amount * (120 if sys.platform == "win32" else 1)  # Windows scrolls in 1/120 notches
            signed = notches if direction in ("up", "left") else -notches
            mods = args.get("text") or ""
            if direction in ("left", "right"):  # horizontal scroll = shift + wheel on all platforms
                mods = f"{mods}+shift" if mods else "shift"
            self._with_mods(mods, lambda: g.scroll(signed))
        else:
            raise ValueError(f"Unsupported computer action: {name}")
        return "OK"
