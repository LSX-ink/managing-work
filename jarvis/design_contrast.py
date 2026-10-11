"""Colour contrast checks (WCAG 2.2) for websites, apps and thumbnails.

check_contrast measures how readable text is on a background: the contrast ratio, whether it passes AA and AAA for
normal and large text and for buttons, icons and borders (3:1), and, when it fails, the nearest shade of the same
colour that passes AA. Give it a palette instead and it lists every text and background pair that is safe to use.
Colours can be hex, rgb(), hsl() or white/black, so the hex codes from design_advice and extract_design_system fit
straight in. Everything is worked out locally.
"""

import colorsys

from config import Settings
from design_extract import to_hex

NAMES = {"check_contrast"}
AA, AAA, LARGE_AA, LARGE_AAA, UI = 4.5, 7.0, 3.0, 4.5, 3.0
MAX_PALETTE = 12


def colour(text: str, under: str = "#ffffff") -> str:
    """#rrggbb; a see-through colour is blended over `under`, as a browser would draw it."""
    hex_ = to_hex(str(text or ""))
    if not hex_:
        raise ValueError(f"Can't read the colour '{text}'. Use hex like #1a2b3c, rgb(...) or hsl(...).")
    if len(hex_) == 9:
        alpha = int(hex_[7:], 16) / 255
        top, base = rgb(hex_[:7]), rgb(under)
        hex_ = "#" + "".join(f"{round(t * alpha + b * (1 - alpha)):02x}" for t, b in zip(top, base))
    return hex_


def rgb(hex_: str) -> tuple[int, int, int]:
    return tuple(int(hex_[i:i + 2], 16) for i in (1, 3, 5))


def luminance(hex_: str) -> float:
    def channel(c: int) -> float:
        c = c / 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (channel(c) for c in rgb(hex_))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def ratio(a: str, b: str) -> float:
    hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def grades(r: float) -> dict:
    return {"AA text": r >= AA, "AAA text": r >= AAA, "AA large": r >= LARGE_AA, "AAA large": r >= LARGE_AAA,
            "UI parts": r >= UI}


def fix(text: str, background: str, target: float = AA) -> str:
    """The closest shade of `text` (same hue and saturation) that reaches `target` on `background`."""
    r, g, b = (c / 255 for c in rgb(text))
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    best = ""
    for step in range(1, 101):
        for light in (l - step / 100, l + step / 100):
            if not 0 <= light <= 1:
                continue
            shade = "#" + "".join(f"{round(c * 255):02x}" for c in colorsys.hls_to_rgb(h, light, s))
            if ratio(shade, background) >= target:
                best = shade
                break
        if best:
            return best
    return "#000000" if ratio("#000000", background) >= ratio("#ffffff", background) else "#ffffff"


def verdict(r: float) -> str:
    if r >= AAA:
        return "excellent, passes everything"
    if r >= AA:
        return "good for all text (AA)"
    if r >= LARGE_AA:
        return "only for large text (24px, or 19px bold) and icons/borders"
    return "fails, too hard to read"


def check_pair(text: str, background: str) -> str:
    bg = colour(background)
    fg = colour(text, bg)
    r = ratio(fg, bg)
    passed = grades(r)
    lines = [f"{fg} on {bg}: {r:.2f}:1, {verdict(r)}.",
             "  " + ", ".join(f"{k} {'pass' if v else 'fail'}" for k, v in passed.items())]
    if not passed["AA text"]:
        better = fix(fg, bg)
        lines.append(f"  Fix: use {better} instead ({ratio(better, bg):.2f}:1, passes AA).")
    return "\n".join(lines)


def check_palette(palette: list) -> str:
    colours = []
    for c in palette[:MAX_PALETTE]:
        hex_ = colour(c)
        if hex_ not in colours:
            colours.append(hex_)
    if len(colours) < 2:
        raise ValueError("Give at least two colours to compare.")
    good, large = [], []
    for i, a in enumerate(colours):
        for b in colours[i + 1:]:
            r = ratio(a, b)
            (good if r >= AA else large if r >= LARGE_AA else []).append(f"{a} + {b} ({r:.2f}:1)")
    lines = [f"Checked {len(colours)} colours ({len(colours) * (len(colours) - 1) // 2} pairs)."]
    lines.append("Safe for any text: " + ("; ".join(good) if good else "none, add a much darker or lighter colour."))
    if large:
        lines.append("Large text, icons and borders only: " + "; ".join(large))
    if len(palette) > MAX_PALETTE:
        lines.append(f"Only the first {MAX_PALETTE} colours were checked.")
    return "\n".join(lines)


def tool_definitions() -> list[dict]:
    return [{
        "name": "check_contrast",
        "description": "Check colour contrast for readability (WCAG 2.2) when designing or reviewing a website, app, "
                       "HUD, slide or thumbnail. Give text and background for one pair (ratio, AA/AAA for normal and "
                       "large text and UI parts, and the nearest passing shade if it fails), pairs for several, or "
                       "palette to list every safe text/background combination. Colours as hex, rgb(), hsl(), white "
                       "or black. Use it on palettes from design_advice, extract_design_system or theme-factory "
                       "before building. Answer in plain words.",
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text (foreground) colour, e.g. '#6b7280'."},
                "background": {"type": "string", "description": "Background colour, e.g. '#ffffff'."},
                "pairs": {"type": "array", "items": {"type": "array", "items": {"type": "string"},
                                                     "minItems": 2, "maxItems": 2},
                          "description": "Several [text, background] pairs."},
                "palette": {"type": "array", "items": {"type": "string"},
                            "description": "A whole palette to find every readable pairing."},
            },
            "additionalProperties": False,
        },
    }]


async def run_tool(name: str, args: dict, settings: Settings, http=None) -> str:
    try:
        if args.get("palette"):
            return check_palette(list(args["palette"]))
        pairs = [list(p) for p in args.get("pairs") or []]
        if args.get("text") or args.get("background"):
            pairs.insert(0, [args.get("text") or "#000000", args.get("background") or "#ffffff"])
        if not pairs:
            return "Give a text and background colour, some pairs, or a palette to check."
        return "\n".join(check_pair(t, b) for t, b in pairs[:20])
    except ValueError as e:
        return str(e)
