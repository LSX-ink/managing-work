"""Type scales for websites: every font size from small print to the biggest heading, in one rhythm.

make_type_scale picks sizes on a musical ratio (minor third, major third, perfect fourth, golden...) from a base size,
and makes them fluid: each size grows smoothly from a phone (360px wide, using a gentler ratio) to a desktop (1280px)
with CSS clamp(), so headings never look huge on a phone or tiny on a laptop. It also sets line height and letter
spacing for each step, a readable line length, and the fonts when given (with the Google Fonts link). Give it a name
and it saves type.md and type.css in Kinetic Web Designs/<name>, next to make_palette's files.
"""

from urllib.parse import quote_plus

import memory
from config import Settings
from design_extract import FOLDER

NAMES = {"make_type_scale"}
RATIOS = {"minor-second": 1.067, "major-second": 1.125, "minor-third": 1.2, "major-third": 1.25,
          "perfect-fourth": 1.333, "augmented-fourth": 1.414, "perfect-fifth": 1.5, "golden": 1.618}
STEPS = [("xs", -2), ("sm", -1), ("base", 0), ("lg", 1), ("xl", 2), ("2xl", 3), ("3xl", 4), ("4xl", 5), ("5xl", 6)]
USES = {"xs": "captions, legal", "sm": "labels, small print", "base": "body text", "lg": "lead paragraph, h6",
        "xl": "h5, card titles", "2xl": "h4", "3xl": "h3", "4xl": "h2", "5xl": "h1, hero"}
MIN_VW, MAX_VW = 360, 1280
MIN_TEXT = 12


def ratio_value(ratio) -> float:
    if isinstance(ratio, (int, float)) or str(ratio).replace(".", "", 1).isdigit():
        value = float(ratio)
        if not 1.01 <= value <= 2:
            raise ValueError("A ratio must be between 1.01 and 2, e.g. 1.25.")
        return value
    key = str(ratio or "major-third").strip().lower().replace(" ", "-")
    if key not in RATIOS:
        raise ValueError(f"Pick a ratio: {', '.join(RATIOS)}, or a number like 1.25.")
    return RATIOS[key]


def gentler(ratio: float) -> float:
    """The phone ratio: one notch below the desktop one, so big headings shrink most."""
    lower = [r for r in sorted(RATIOS.values()) if r < ratio - 0.001]
    return lower[-1] if lower else ratio


def rem(px: float) -> str:
    return f"{px / 16:.4f}".rstrip("0").rstrip(".") + "rem"


def clamp(small: float, large: float) -> str:
    if abs(large - small) < 0.01:
        return rem(large)
    slope = (large - small) / (MAX_VW - MIN_VW)
    intercept = small - slope * MIN_VW
    return f"clamp({rem(small)}, {rem(intercept)} + {slope * 100:.4f}vw, {rem(large)})"


def leading(step: int) -> float:
    return 1.6 if step <= 0 else 1.5 if step == 1 else 1.3 if step <= 3 else 1.15 if step == 4 else 1.05


def tracking(step: int) -> str:
    return "0.01em" if step < 0 else "0" if step <= 2 else "-0.01em" if step <= 4 else "-0.02em"


def build(base: float = 16, ratio="major-third", mobile_ratio=None) -> dict:
    if not 12 <= float(base) <= 24:
        raise ValueError("Keep the base (body text) size between 12 and 24 px; 16 is the web default.")
    base, big = float(base), ratio_value(ratio)
    small = ratio_value(mobile_ratio) if mobile_ratio else gentler(big)
    small = min(small, big)
    steps = []
    for name, n in STEPS:
        lo, hi = base * small ** n, base * big ** n
        if n < 0:  # small print stays put on every screen and never drops under 12px
            lo = hi = max(MIN_TEXT, base * small ** n)
        steps.append({"name": name, "step": n, "phone": round(lo, 1), "desktop": round(hi, 1), "size": clamp(lo, hi),
                      "line_height": leading(n), "tracking": tracking(n), "use": USES[name]})
    return {"base": base, "ratio": big, "mobile_ratio": small, "steps": steps}


def fonts_link(heading: str, body: str) -> str:
    families = [f for f in dict.fromkeys([heading, body]) if f]
    if not families:
        return ""
    query = "&".join(f"family={quote_plus(f)}:wght@400;600;700" for f in families)
    return f"https://fonts.googleapis.com/css2?{query}&display=swap"


def css(scale: dict, heading: str = "", body: str = "") -> str:
    out = []
    link = fonts_link(heading, body)
    if link:
        out += [f"@import url('{link}');", ""]
    out.append(":root {")
    if body:
        out.append(f"  --font-body: '{body}', system-ui, sans-serif;")
    if heading:
        out.append(f"  --font-heading: '{heading}', system-ui, sans-serif;")
    for s in scale["steps"]:
        out += [f"  --text-{s['name']}: {s['size']};", f"  --leading-{s['name']}: {s['line_height']};",
                f"  --tracking-{s['name']}: {s['tracking']};"]
    out += ["  --measure: 65ch;", "}", ""]
    out.append("body { font-size: var(--text-base); line-height: var(--leading-base);"
               + (" font-family: var(--font-body);" if body else "") + " }")
    out.append("p, li { max-width: var(--measure); }")
    for tag, name in (("h1", "5xl"), ("h2", "4xl"), ("h3", "3xl"), ("h4", "2xl"), ("h5", "xl"), ("h6", "lg")):
        out.append(f"{tag} {{ font-size: var(--text-{name}); line-height: var(--leading-{name}); "
                   f"letter-spacing: var(--tracking-{name});" + (" font-family: var(--font-heading);" if heading else "")
                   + " }")
    out.append("small { font-size: var(--text-sm); }")
    return "\n".join(out) + "\n"


def markdown(scale: dict, title: str, heading: str = "", body: str = "") -> str:
    out = [f"# {title} type scale", "", f"Base {scale['base']:g}px. Desktop ratio {scale['ratio']}, phone ratio "
           f"{scale['mobile_ratio']}. Sizes grow smoothly from {MIN_VW}px to {MAX_VW}px wide screens."]
    if heading or body:
        out += ["", f"Fonts: headings {heading or 'same as body'}, body {body or 'system font'}."]
    out += ["", "| Step | Phone | Desktop | Line height | Use |", "| --- | --- | --- | --- | --- |"]
    out += [f"| {s['name']} | {s['phone']:g}px | {s['desktop']:g}px | {s['line_height']} | {s['use']} |"
            for s in scale["steps"]]
    out += ["", "Keep paragraphs to about 65 characters a line (max-width: 65ch)."]
    return "\n".join(out) + "\n"


def summary(scale: dict, where: str = "", heading: str = "", body: str = "") -> str:
    lines = [f"Type scale from {scale['base']:g}px, ratio {scale['ratio']} on desktop and {scale['mobile_ratio']} on "
             "phones (sizes in px, phone to desktop):"]
    lines.append("; ".join(f"{s['name']} {s['phone']:g}-{s['desktop']:g} ({s['use']})" for s in scale["steps"]) + ".")
    lines.append("Body line height 1.6, big headings 1.05-1.15 with slightly tighter letter spacing; paragraphs up to "
                 "65 characters wide.")
    if heading or body:
        lines.append(f"Fonts: {heading or 'body font'} for headings, {body or 'system font'} for text "
                     f"({fonts_link(heading, body)}).")
    if where:
        lines.append(f"Saved type.md and type.css (ready-to-paste CSS with clamp() sizes) in {where}.")
    return "\n".join(lines)


def save(settings: Settings, scale: dict, name: str, heading: str = "", body: str = "") -> str:
    name = memory.safe_name(name, "folder name")
    (memory.root(settings) / FOLDER).mkdir(parents=True, exist_ok=True)
    path = memory.folder(settings, f"{FOLDER}/{name}", create=True)
    (path / "type.md").write_text(markdown(scale, name, heading, body), encoding="utf-8")
    (path / "type.css").write_text(css(scale, heading, body), encoding="utf-8")
    return path.relative_to(memory.root(settings)).as_posix()


def tool_definitions() -> list[dict]:
    return [{
        "name": "make_type_scale",
        "description": "Make a website type scale: every font size from captions to the hero heading on one ratio "
                       "(minor-third, major-third, perfect-fourth, golden...), fluid from phone to desktop with CSS "
                       "clamp(), plus line heights, letter spacing and a readable line length. Optional heading and "
                       "body fonts (Google Fonts names, e.g. from design_advice). Give name to save type.md and "
                       "type.css in Kinetic Web Designs/<name>. Pairs with make_palette. Answer in plain words.",
        "input_schema": {
            "type": "object",
            "properties": {
                "base": {"type": "number", "minimum": 12, "maximum": 24, "description": "Body text px (default 16)."},
                "ratio": {"type": "string", "description": "Desktop ratio name or number. Calm: major-second or "
                                                           "minor-third; balanced: major-third (default); bold: "
                                                           "perfect-fourth, perfect-fifth or golden."},
                "mobile_ratio": {"type": "string", "description": "Phone ratio; default one notch gentler."},
                "heading_font": {"type": "string", "description": "e.g. 'Space Grotesk'."},
                "body_font": {"type": "string", "description": "e.g. 'Inter'."},
                "name": {"type": "string", "description": "Brand or client name; saves the files when given."},
            },
            "additionalProperties": False,
        },
    }]


async def run_tool(name: str, args: dict, settings: Settings, http=None) -> str:
    heading = str(args.get("heading_font") or "").strip()
    body = str(args.get("body_font") or "").strip()
    try:
        scale = build(args.get("base") or 16, args.get("ratio") or "major-third", args.get("mobile_ratio"))
        title = str(args.get("name") or "").strip()
        where = save(settings, scale, title, heading, body) if title else ""
        return summary(scale, where, heading, body)
    except (TypeError, ValueError) as e:
        return str(e)
