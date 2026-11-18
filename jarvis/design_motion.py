"""Motion tokens for websites and apps: how long animations take, how they ease, and real springs in plain CSS.

make_motion picks a set of durations (instant to slow) and easing curves for a feel (snappy, smooth, bouncy or calm),
following the usual rules from the Emil Kowalski guides: enter with ease-out, move with ease-in-out, keep UI motion
under about 300ms. It also turns a spring (stiffness and damping, like Framer Motion or React Spring use) into a CSS
linear() easing with its natural duration, so a bounce works with no JavaScript. Every set comes with a
prefers-reduced-motion block. Give it a name and it saves motion.md and motion.css in Kinetic Web Designs/<name>,
next to make_palette's and make_type_scale's files.
"""

import math

import memory
from config import Settings
from design_extract import FOLDER

NAMES = {"make_motion"}
DURATIONS = {"instant": 100, "fast": 150, "base": 200, "slow": 300, "slower": 450, "page": 600}
FEELS = {
    "snappy": {"speed": 0.8, "spring": (400, 32), "out": (0.23, 1, 0.32, 1), "in_out": (0.77, 0, 0.175, 1)},
    "smooth": {"speed": 1.0, "spring": (170, 26), "out": (0.22, 1, 0.36, 1), "in_out": (0.65, 0, 0.35, 1)},
    "bouncy": {"speed": 1.0, "spring": (300, 14), "out": (0.34, 1.56, 0.64, 1), "in_out": (0.68, -0.6, 0.32, 1.6)},
    "calm": {"speed": 1.3, "spring": (120, 22), "out": (0.25, 1, 0.5, 1), "in_out": (0.45, 0, 0.55, 1)},
}
SAMPLES = 40
MAX_SECONDS = 3.0


def spring(stiffness: float, damping: float, mass: float = 1.0) -> tuple[list[float], int]:
    """Positions of a spring going from 0 to 1, sampled evenly, and how long it takes to settle (ms)."""
    if stiffness <= 0 or damping <= 0 or mass <= 0:
        raise ValueError("Stiffness, damping and mass must all be above 0 (e.g. stiffness 170, damping 26).")
    dt, x, v, t, trail = 1 / 1000, 0.0, 0.0, 0.0, [0.0]
    still = 0.0
    while t < MAX_SECONDS:
        a = (-stiffness * (x - 1) - damping * v) / mass
        v += a * dt
        x += v * dt
        t += dt
        trail.append(x)
        still = still + dt if abs(x - 1) < 0.001 and abs(v) < 0.01 else 0.0
        if still >= 0.05:
            break
    settle = len(trail) - 1 - round(still * 1000)
    settle = max(settle, 1)
    points = [trail[round(i * settle / SAMPLES)] for i in range(SAMPLES + 1)]
    points[-1] = 1.0
    return points, settle


def linear_easing(points: list[float]) -> str:
    return "linear(" + ", ".join(f"{p:.3f}".rstrip("0").rstrip(".") or "0" for p in points) + ")"


def overshoot(points: list[float]) -> float:
    return max(0.0, max(points) - 1)


def bezier(c: tuple) -> str:
    return "cubic-bezier(" + ", ".join(f"{n:g}" for n in c) + ")"


def build(feel: str = "smooth", stiffness: float | None = None, damping: float | None = None,
          mass: float = 1.0) -> dict:
    key = str(feel or "smooth").strip().lower()
    if key not in FEELS:
        raise ValueError(f"Pick a feel: {', '.join(FEELS)}.")
    f = FEELS[key]
    k, c = f["spring"]
    points, settle = spring(float(stiffness or k), float(damping or c), float(mass or 1))
    durations = {name: max(50, round(ms * f["speed"] / 10) * 10) for name, ms in DURATIONS.items()}
    return {"feel": key, "durations": durations, "ease_out": bezier(f["out"]), "ease_in_out": bezier(f["in_out"]),
            "ease_in": bezier((f["in_out"][0], 0, 1, 1)), "spring": linear_easing(points), "spring_ms": settle,
            "stiffness": float(stiffness or k), "damping": float(damping or c), "mass": float(mass or 1),
            "bounce": round(overshoot(points) * 100)}


def css(m: dict) -> str:
    lines = [":root {"]
    lines += [f"  --duration-{name}: {ms}ms;" for name, ms in m["durations"].items()]
    lines += [f"  --ease-out: {m['ease_out']};", f"  --ease-in-out: {m['ease_in_out']};",
              f"  --ease-in: {m['ease_in']};", f"  --ease-spring: {m['spring']};",
              f"  --duration-spring: {m['spring_ms']}ms;", "}", "",
              "/* Enter and appear: ease-out. Move on screen: ease-in-out. Leave: ease-in, a little faster. */",
              ".fade-in { animation: fade-in var(--duration-base) var(--ease-out) both; }",
              ".pop-in { animation: pop-in var(--duration-spring) var(--ease-spring) both; }",
              "@keyframes fade-in { from { opacity: 0; transform: translateY(8px); } }",
              "@keyframes pop-in { from { opacity: 0; transform: scale(0.9); } }",
              "button { transition: transform var(--duration-fast) var(--ease-out); }",
              "button:active { transform: scale(0.97); }", "",
              "@media (prefers-reduced-motion: reduce) {",
              "  *, *::before, *::after { animation-duration: 1ms !important; animation-iteration-count: 1 !important;",
              "    transition-duration: 1ms !important; scroll-behavior: auto !important; }", "}"]
    return "\n".join(lines) + "\n"


def markdown(m: dict, title: str) -> str:
    out = [f"# {title} motion", "", f"Feel: {m['feel']}.", "", "| Token | Value | Use |", "| --- | --- | --- |"]
    uses = {"instant": "hover colour, toggles", "fast": "button press, tooltips", "base": "dropdowns, fades",
            "slow": "modals, drawers", "slower": "large panels", "page": "page transitions (use rarely)"}
    out += [f"| duration-{n} | {ms}ms | {uses[n]} |" for n, ms in m["durations"].items()]
    out += [f"| ease-out | {m['ease_out']} | things appearing |", f"| ease-in-out | {m['ease_in_out']} | moving |",
            f"| ease-in | {m['ease_in']} | things leaving |",
            f"| ease-spring | linear(...) over {m['spring_ms']}ms | pop-ins, cards, playful UI |"]
    out += ["", f"Spring: stiffness {m['stiffness']:g}, damping {m['damping']:g}, mass {m['mass']:g}, "
            f"{m['bounce']}% overshoot.", "",
            "Rules: keep UI motion under 300ms, animate transform and opacity only, never block a click on an "
            "animation, and always honour reduced motion."]
    return "\n".join(out) + "\n"


def summary(m: dict, where: str = "") -> str:
    lines = [f"Motion set ({m['feel']}): durations "
             + ", ".join(f"{n} {ms}ms" for n, ms in m["durations"].items()) + ".",
             f"Easing: ease-out {m['ease_out']} for things appearing, ease-in-out {m['ease_in_out']} for moving, "
             f"ease-in {m['ease_in']} for leaving.",
             f"Spring (stiffness {m['stiffness']:g}, damping {m['damping']:g}): settles in {m['spring_ms']}ms with "
             f"{m['bounce']}% overshoot, as CSS: {m['spring']}",
             "Includes a reduced-motion switch-off for people who turn animation down."]
    if where:
        lines.append(f"Saved motion.md and motion.css in {where}.")
    return "\n".join(lines)


def save(settings: Settings, m: dict, name: str) -> str:
    name = memory.safe_name(name, "folder name")
    (memory.root(settings) / FOLDER).mkdir(parents=True, exist_ok=True)
    path = memory.folder(settings, f"{FOLDER}/{name}", create=True)
    (path / "motion.md").write_text(markdown(m, name), encoding="utf-8")
    (path / "motion.css").write_text(css(m), encoding="utf-8")
    return path.relative_to(memory.root(settings)).as_posix()


def tool_definitions() -> list[dict]:
    return [{
        "name": "make_motion",
        "description": "Make animation timing for a website or app: durations (instant to page), easing curves and a "
                       "real spring turned into a CSS linear() easing, for a feel: snappy, smooth (default), bouncy "
                       "or calm. Or give spring stiffness/damping (as in Framer Motion or React Spring) to convert it. "
                       "Always includes a reduced-motion block. Give name to save motion.md and motion.css in Kinetic "
                       "Web Designs/<name>. Pairs with make_palette, make_type_scale and the Emil Kowalski guides. "
                       "Answer in plain words.",
        "input_schema": {
            "type": "object",
            "properties": {
                "feel": {"type": "string", "enum": list(FEELS)},
                "stiffness": {"type": "number", "minimum": 1, "maximum": 2000},
                "damping": {"type": "number", "minimum": 1, "maximum": 200},
                "mass": {"type": "number", "minimum": 0.1, "maximum": 10},
                "name": {"type": "string", "description": "Brand or client name; saves the files when given."},
            },
            "additionalProperties": False,
        },
    }]


async def run_tool(name: str, args: dict, settings: Settings, http=None) -> str:
    try:
        m = build(args.get("feel") or "smooth", args.get("stiffness"), args.get("damping"), args.get("mass") or 1)
        title = str(args.get("name") or "").strip()
        return summary(m, save(settings, m, title) if title else "")
    except (TypeError, ValueError) as e:
        return str(e)
