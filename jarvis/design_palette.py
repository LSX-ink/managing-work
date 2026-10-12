"""Brand palettes from one colour, for websites, apps and brand kits.

make_palette turns a brand colour into a full set: a 50-950 shade scale (like Tailwind's), a matching grey scale with a
hint of the brand's hue, accent colours from a colour-wheel harmony (complementary, analogous, triadic, split or mono),
and ready-to-use roles for a light and a dark page (background, surface, text, muted text, border, button and button
text). Every text role is checked with design_contrast and nudged until it passes WCAG AA, so the palette is readable
as soon as it's made. Give it a name and it saves palette.md and palette.css in Kinetic Web Designs/<name>.
"""

import colorsys

import memory
from config import Settings
from design_contrast import AA, colour, fix, ratio, rgb
from design_extract import FOLDER, colour_name

NAMES = {"make_palette"}
STEPS = {50: 0.97, 100: 0.94, 200: 0.86, 300: 0.76, 400: 0.64, 500: 0.52, 600: 0.43, 700: 0.35, 800: 0.27, 900: 0.2,
         950: 0.12}
HARMONIES = {"complementary": [180], "analogous": [-30, 30], "triadic": [120, 240], "split": [150, 210], "mono": []}


def hls(hex_: str) -> tuple[float, float, float]:
    return colorsys.rgb_to_hls(*(c / 255 for c in rgb(hex_)))


def from_hls(h: float, l: float, s: float) -> str:
    return "#" + "".join(f"{round(c * 255):02x}" for c in colorsys.hls_to_rgb(h % 1, max(0, min(1, l)), max(0, min(1, s))))


def scale(hex_: str, saturation: float | None = None) -> dict[int, str]:
    h, _, s = hls(hex_)
    s = s if saturation is None else saturation
    return {step: from_hls(h, light, s) for step, light in STEPS.items()}


def nearest_step(hex_: str) -> int:
    light = hls(hex_)[1]
    return min(STEPS, key=lambda step: abs(STEPS[step] - light))


def accents(hex_: str, harmony: str) -> list[str]:
    h, l, s = hls(hex_)
    return [from_hls(h + turn / 360, l, s) for turn in HARMONIES[harmony]]


def on(background: str) -> str:
    """White or near-black, whichever reads better on `background`."""
    return "#ffffff" if ratio("#ffffff", background) >= ratio("#0b0b0f", background) else "#0b0b0f"


def readable(text: str, background: str) -> str:
    return text if ratio(text, background) >= AA else fix(text, background)


def roles(brand: str, greys: dict[int, str], shades: dict[int, str]) -> dict[str, dict[str, str]]:
    light = {"background": "#ffffff", "surface": greys[50], "border": greys[200]}
    light["text"] = readable(greys[900], light["background"])
    light["muted text"] = readable(greys[600], light["background"])
    light["button"] = brand
    light["button text"] = on(brand)
    light["link"] = readable(brand, light["background"])
    dark = {"background": greys[950], "surface": greys[900], "border": greys[800]}
    dark["text"] = readable(greys[50], dark["background"])
    dark["muted text"] = readable(greys[400], dark["background"])
    dark["button"] = shades[400] if ratio(brand, dark["background"]) < 3 else brand
    dark["button text"] = on(dark["button"])
    dark["link"] = readable(shades[300], dark["background"])
    return {"light": light, "dark": dark}


def build(base: str, harmony: str = "complementary") -> dict:
    if harmony not in HARMONIES:
        raise ValueError(f"Pick a harmony: {', '.join(HARMONIES)}.")
    brand = colour(base)
    shades = scale(brand)
    greys = scale(brand, min(hls(brand)[2], 0.1))
    extra = [{"hex": a, "name": colour_name(a), "scale": scale(a)} for a in accents(brand, harmony)]
    return {"brand": brand, "name": colour_name(brand), "step": nearest_step(brand), "harmony": harmony,
            "shades": shades, "greys": greys, "accents": extra, "roles": roles(brand, greys, shades)}


def css(p: dict) -> str:
    lines = [":root {"]
    lines += [f"  --brand-{k}: {v};" for k, v in p["shades"].items()]
    lines += [f"  --grey-{k}: {v};" for k, v in p["greys"].items()]
    for i, a in enumerate(p["accents"], 1):
        lines += [f"  --accent{i}-{k}: {v};" for k, v in a["scale"].items()]
    lines += [f"  --{k.replace(' ', '-')}: {v};" for k, v in p["roles"]["light"].items()]
    lines += ["}", "@media (prefers-color-scheme: dark) {", "  :root {"]
    lines += [f"    --{k.replace(' ', '-')}: {v};" for k, v in p["roles"]["dark"].items()]
    return "\n".join(lines + ["  }", "}", ""])


def markdown(p: dict, title: str) -> str:
    out = [f"# {title} palette", "", f"Brand colour {p['brand']} ({p['name']}, close to step {p['step']}). "
           f"Harmony: {p['harmony']}.", "", "## Brand shades", "", "| Step | Hex |", "| --- | --- |"]
    out += [f"| {k} | {v} |" for k, v in p["shades"].items()]
    out += ["", "## Greys", "", "| Step | Hex |", "| --- | --- |"] + [f"| {k} | {v} |" for k, v in p["greys"].items()]
    if p["accents"]:
        out += ["", "## Accents", ""] + [f"- {a['hex']} ({a['name']})" for a in p["accents"]]
    for mode in ("light", "dark"):
        r = p["roles"][mode]
        out += ["", f"## {mode.title()} page", "", "| Role | Hex | Contrast |", "| --- | --- | --- |"]
        for role, hex_ in r.items():
            against = r["button"] if role == "button text" else r["background"]
            out.append(f"| {role} | {hex_} | {ratio(hex_, against):.2f}:1 |" if role not in ("background",)
                       else f"| {role} | {hex_} | |")
    return "\n".join(out) + "\n"


def summary(p: dict, where: str = "") -> str:
    light, dark = p["roles"]["light"], p["roles"]["dark"]
    parts = [f"Palette from {p['brand']} ({p['name']}). Shades 50-950: "
             + ", ".join(f"{k} {v}" for k, v in p["shades"].items()) + ".",
             "Greys: " + ", ".join(f"{k} {v}" for k, v in p["greys"].items()) + "."]
    if p["accents"]:
        parts.append(f"{p['harmony'].title()} accents: " + ", ".join(f"{a['hex']} ({a['name']})" for a in p["accents"])
                     + ".")
    for mode, r in (("Light", light), ("Dark", dark)):
        parts.append(f"{mode} page: background {r['background']}, surface {r['surface']}, text {r['text']} "
                     f"({ratio(r['text'], r['background']):.1f}:1), muted {r['muted text']} "
                     f"({ratio(r['muted text'], r['background']):.1f}:1), border {r['border']}, button {r['button']} "
                     f"with {r['button text']} text ({ratio(r['button text'], r['button']):.1f}:1), link {r['link']}.")
    if where:
        parts.append(f"Saved palette.md and palette.css in {where}.")
    return "\n".join(parts)


def save(settings: Settings, p: dict, name: str) -> str:
    name = memory.safe_name(name, "folder name")
    (memory.root(settings) / FOLDER).mkdir(parents=True, exist_ok=True)
    path = memory.folder(settings, f"{FOLDER}/{name}", create=True)
    (path / "palette.md").write_text(markdown(p, name), encoding="utf-8")
    (path / "palette.css").write_text(css(p), encoding="utf-8")
    return path.relative_to(memory.root(settings)).as_posix()


def tool_definitions() -> list[dict]:
    return [{
        "name": "make_palette",
        "description": "Make a full brand colour palette from one colour for a website, app, logo or brand kit: "
                       "shades 50-950, matching greys, accent colours (harmony: complementary, analogous, triadic, "
                       "split or mono) and readable roles for light and dark pages (background, surface, text, muted "
                       "text, border, button, button text, link), all contrast-checked to WCAG AA. Give name to save "
                       "palette.md and palette.css in Kinetic Web Designs/<name>. Answer in plain words with the key "
                       "hex codes.",
        "input_schema": {
            "type": "object",
            "properties": {
                "colour": {"type": "string", "description": "Brand colour, e.g. '#4f46e5' or 'rgb(220, 38, 38)'."},
                "harmony": {"type": "string", "enum": list(HARMONIES)},
                "name": {"type": "string", "description": "Brand or client name; saves the files when given."},
            },
            "required": ["colour"],
            "additionalProperties": False,
        },
    }]


async def run_tool(name: str, args: dict, settings: Settings, http=None) -> str:
    try:
        p = build(args.get("colour") or "", args.get("harmony") or "complementary")
        title = str(args.get("name") or "").strip()
        return summary(p, save(settings, p, title) if title else "")
    except ValueError as e:
        return str(e)
