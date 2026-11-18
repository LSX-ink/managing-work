"""Ready-made website components in a brand's colours: buttons, form boxes, cards, badges and alerts, with every state.

make_components starts from the brand colour (through make_palette) and works out each state so it stays readable:
primary, secondary, ghost and danger buttons with hover, pressed, keyboard-focus and disabled looks; text boxes with a
3:1 border and a clear focus ring, plus error and help text; cards, badges and four alert styles. Any colour pair that
would fall under WCAG AA is darkened until it passes, and the summary lists the final ratios. It saves components.css
and components.html (every state side by side, light and dark) in Kinetic Web Designs/<name>, next to the brand kit.
"""

import html

import design_palette
import memory
from config import Settings
from design_contrast import AA, UI, ratio
from design_extract import FOLDER

NAMES = {"make_components"}
SHAPES = {"sharp": (4, 4, 4), "rounded": (10, 8, 16), "pill": (9999, 10, 20)}  # button, input, card radius
STATUS = {"info": "#1d4ed8", "success": "#15803d", "warning": "#b45309", "error": "#b91c1c"}
WHITE, INK = "#ffffff", "#0b0b0f"


def darker(scale: dict, start: int, text: str, target: float = AA) -> tuple[str, int]:
    """The first shade from `start` downwards that `text` reads on."""
    steps = sorted(scale)
    for step in steps[steps.index(start):]:
        if ratio(text, scale[step]) >= target:
            return scale[step], step
    return scale[steps[-1]], steps[-1]


def states(scale: dict, step: int, text: str) -> tuple[str, str]:
    """Hover and pressed shades: deeper under white words, lighter under dark words, both still readable."""
    steps = sorted(scale)
    order = [s for s in steps if s > step] if text == WHITE else [s for s in reversed(steps) if s < step]
    usable = [scale[s] for s in order if ratio(text, scale[s]) >= AA]
    hover = usable[0] if usable else scale[step]
    return hover, usable[1] if len(usable) > 1 else hover


def first(scale: dict, steps: list[int], against: str, target: float) -> str:
    for step in steps:
        if ratio(scale[step], against) >= target:
            return scale[step]
    return scale[steps[-1]]


def build(base: str, shape: str = "rounded") -> dict:
    shape = str(shape or "rounded").lower()
    if shape not in SHAPES:
        raise ValueError(f"Pick a shape: {', '.join(SHAPES)}.")
    p = design_palette.build(base)
    shades, greys = p["shades"], p["greys"]
    text = design_palette.on(p["brand"])
    start = min(shades, key=lambda s: abs(int(s) - p["step"]))
    if ratio(text, p["brand"]) >= AA:
        primary, step = p["brand"], start
    else:  # the brand itself is too light for button words, so the button uses a deeper shade
        text = WHITE
        primary, step = darker(shades, start, WHITE)
    hover, pressed = states(shades, step, text)
    soft_text = first(shades, [700, 800, 900, 950], shades[100], AA)
    focus = first(shades, [500, 600, 700, 800, 900], WHITE, UI)
    dark_bg = greys[950]
    c = {
        "brand": p["brand"], "shape": shape,
        "primary": primary, "primary-text": text, "primary-hover": hover, "primary-pressed": pressed,
        "secondary": shades[100], "secondary-text": soft_text, "secondary-hover": shades[200],
        "ghost-text": first(shades, [600, 700, 800, 900], WHITE, AA), "ghost-border": greys[300],
        "ghost-hover": shades[50],
        "danger": STATUS["error"], "danger-text": WHITE, "danger-hover": "#991b1b",
        "disabled": greys[200], "disabled-text": greys[500],
        "focus": focus, "focus-dark": first(shades, [300, 200, 100, 50], dark_bg, UI),
        "input-border": first(greys, [400, 500, 600, 700], WHITE, UI), "input-text": greys[900],
        "placeholder": first(greys, [500, 600, 700], WHITE, AA), "help": first(greys, [600, 700], WHITE, AA),
        "surface": WHITE, "card-border": greys[200], "text": greys[900], "muted": first(greys, [600, 700], WHITE, AA),
        "dark-bg": dark_bg, "dark-surface": greys[900], "dark-text": greys[50], "dark-border": greys[800],
        "badge": shades[100], "badge-text": soft_text,
    }
    checks = {"Primary button": ratio(text, primary), "Primary hover": ratio(text, hover),
              "Secondary button": ratio(soft_text, shades[100]), "Ghost button": ratio(c["ghost-text"], WHITE),
              "Danger button": ratio(WHITE, STATUS["error"]), "Text box border": ratio(c["input-border"], WHITE),
              "Placeholder": ratio(c["placeholder"], WHITE), "Focus ring": ratio(focus, WHITE),
              "Focus ring (dark)": ratio(c["focus-dark"], dark_bg)}
    return {"colours": c, "checks": checks, "radii": SHAPES[shape], "moved": primary != p["brand"]}


def css(kit: dict) -> str:
    c, (button_r, input_r, card_r) = kit["colours"], kit["radii"]
    tokens = "\n".join(f"  --c-{k}: {v};" for k, v in c.items() if k not in ("brand", "shape"))
    alerts = "\n".join(f".alert-{k} {{ --alert: {v}; }}" for k, v in STATUS.items())
    return f"""/* Components by Alfred for brand {c['brand']} ({c['shape']} corners). Every pair passes WCAG AA. */
:root {{
{tokens}
  --radius-button: {button_r}px;
  --radius-input: {input_r}px;
  --radius-card: {card_r}px;
}}

.btn {{ display: inline-flex; align-items: center; justify-content: center; gap: 0.5em; min-height: 44px;
  padding: 0.65em 1.25em; border: 1px solid transparent; border-radius: var(--radius-button); font: inherit;
  font-weight: 600; line-height: 1.2; text-decoration: none; cursor: pointer;
  transition: background-color 150ms ease, border-color 150ms ease, transform 100ms ease; }}
.btn:focus-visible, .input:focus-visible, .is-focus {{ outline: 3px solid var(--c-focus); outline-offset: 2px; }}
.btn:active, .btn.is-pressed {{ transform: translateY(1px); }}
.btn-primary {{ background: var(--c-primary); color: var(--c-primary-text); }}
.btn-primary:hover, .btn-primary.is-hover {{ background: var(--c-primary-hover); }}
.btn-primary:active, .btn-primary.is-pressed {{ background: var(--c-primary-pressed); }}
.btn-secondary {{ background: var(--c-secondary); color: var(--c-secondary-text); }}
.btn-secondary:hover, .btn-secondary.is-hover {{ background: var(--c-secondary-hover); }}
.btn-ghost {{ background: transparent; color: var(--c-ghost-text); border-color: var(--c-ghost-border); }}
.btn-ghost:hover, .btn-ghost.is-hover {{ background: var(--c-ghost-hover); }}
.btn-danger {{ background: var(--c-danger); color: var(--c-danger-text); }}
.btn-danger:hover, .btn-danger.is-hover {{ background: var(--c-danger-hover); }}
.btn:disabled, .btn[aria-disabled="true"] {{ background: var(--c-disabled); color: var(--c-disabled-text);
  border-color: transparent; cursor: not-allowed; transform: none; }}

.field {{ display: grid; gap: 0.35em; max-width: 360px; }}
.field label {{ font-weight: 600; color: var(--c-text); }}
.input {{ min-height: 44px; padding: 0.6em 0.8em; border: 1px solid var(--c-input-border);
  border-radius: var(--radius-input); background: var(--c-surface); color: var(--c-input-text); font: inherit; }}
.input::placeholder {{ color: var(--c-placeholder); }}
.input:focus-visible {{ border-color: var(--c-focus); }}
.input[aria-invalid="true"] {{ border-color: var(--c-danger); }}
.help {{ font-size: 0.875em; color: var(--c-help); }}
.error {{ font-size: 0.875em; color: var(--c-danger); font-weight: 600; }}

.card {{ background: var(--c-surface); color: var(--c-text); border: 1px solid var(--c-card-border);
  border-radius: var(--radius-card); padding: 1.5rem; box-shadow: 0 4px 12px rgb(0 0 0 / 0.06); }}
.card .muted {{ color: var(--c-muted); }}
.badge {{ display: inline-block; padding: 0.2em 0.65em; border-radius: 999px; background: var(--c-badge);
  color: var(--c-badge-text); font-size: 0.8125em; font-weight: 600; }}
.alert {{ border-left: 4px solid var(--alert); background: color-mix(in srgb, var(--alert) 8%, white);
  color: var(--c-text); padding: 0.85rem 1rem; border-radius: 6px; }}
.alert strong {{ color: var(--alert); }}
{alerts}

.dark {{ background: var(--c-dark-bg); color: var(--c-dark-text); --c-focus: var(--c-focus-dark); }}
.dark .card {{ background: var(--c-dark-surface); color: var(--c-dark-text); border-color: var(--c-dark-border); }}

@media (prefers-reduced-motion: reduce) {{ .btn {{ transition: none; }} .btn:active {{ transform: none; }} }}
"""


def preview(kit: dict, name: str) -> str:
    title = html.escape(name)
    rows = []
    for kind in ("primary", "secondary", "ghost", "danger"):
        rows.append(f'<div class="row"><span class="label">{kind.title()}</span>'
                    f'<button class="btn btn-{kind}">Get a quote</button>'
                    f'<button class="btn btn-{kind} is-hover">Hover</button>'
                    f'<button class="btn btn-{kind} is-pressed">Pressed</button>'
                    f'<button class="btn btn-{kind} is-focus">Keyboard focus</button>'
                    f'<button class="btn btn-{kind}" disabled>Disabled</button></div>')
    checks = "".join(f"<li>{html.escape(k)}: {v:.1f}:1</li>" for k, v in kit["checks"].items())
    words = {"info": "Bookings open at 9am.", "success": "Your booking is saved.",
             "warning": "Only 2 slots left today.", "error": "That card was declined."}
    alerts = "".join(f'<div class="alert alert-{k}"><strong>{k.title()}:</strong> {words[k]}</div>' for k in STATUS)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} components</title><link rel="stylesheet" href="components.css">
<style>
body {{ margin: 0; font-family: system-ui, sans-serif; color: var(--c-text); }}
section {{ padding: 32px 24px; display: grid; gap: 20px; }}
.row {{ display: flex; flex-wrap: wrap; gap: 12px; align-items: center; }}
.label {{ width: 90px; font-size: 13px; opacity: 0.75; }}
.cards {{ display: grid; gap: 16px; grid-template-columns: repeat(auto-fill, minmax(min(100%, 260px), 1fr)); }}
ul {{ margin: 0; padding-left: 18px; font-size: 14px; }}
</style></head>
<body>
<section><h1 style="margin:0">{title} components</h1>
{''.join(rows)}
<div class="row"><div class="field"><label for="name">Your name</label>
<input class="input" id="name" placeholder="e.g. Lebo Mokoena">
<span class="help">As it appears on your card.</span></div>
<div class="field"><label for="email">Email</label><input class="input is-focus" id="email" value="lebo@">
<span class="help">Keyboard focus shown.</span></div>
<div class="field"><label for="phone">Phone</label><input class="input" id="phone" aria-invalid="true" value="07">
<span class="error">That number looks too short.</span></div></div>
<div class="cards"><div class="card"><span class="badge">New</span><h3>Business website</h3>
<p class="muted">Up to 8 pages, booking form and Google listing.</p><a class="btn btn-primary" href="#">Choose</a></div>
<div class="card"><span class="badge">Popular</span><h3>Shop</h3><p class="muted">Sell online with card payments.</p>
<a class="btn btn-ghost" href="#">See more</a></div></div>
{alerts}
<div><b>Contrast</b><ul>{checks}</ul></div></section>
<section class="dark"><div class="row"><button class="btn btn-primary">On dark</button>
<button class="btn btn-primary is-focus">Keyboard focus</button><button class="btn btn-danger">Delete</button></div>
<div class="cards"><div class="card"><span class="badge">Dark</span><h3>Card on dark</h3>
<p>Text on the dark surface.</p></div></div></section>
</body></html>
"""


def summary(kit: dict, where: str = "") -> str:
    c = kit["colours"]
    passes = ", ".join(f"{k} {v:.1f}:1" for k, v in kit["checks"].items())
    moved = (f" The brand colour {c['brand']} is too light for white or black button words, so buttons use "
             f"{c['primary']} instead." if kit["moved"] else "")
    saved = f" Saved components.css and components.html in {where}; open the page to see every state." if where else ""
    return (f"Components for {c['brand']} ({c['shape']} corners): primary button {c['primary']} with "
            f"{c['primary-text']} words (hover {c['primary-hover']}, pressed {c['primary-pressed']}), secondary "
            f"{c['secondary']}, ghost text {c['ghost-text']}, focus ring {c['focus']}, text box border "
            f"{c['input-border']}.{moved} Contrast: {passes}.{saved}")


def save(settings: Settings, kit: dict, name: str) -> str:
    name = memory.safe_name(name, "folder name")
    (memory.root(settings) / FOLDER).mkdir(parents=True, exist_ok=True)
    path = memory.folder(settings, f"{FOLDER}/{name}", create=True)
    (path / "components.css").write_text(css(kit), encoding="utf-8")
    (path / "components.html").write_text(preview(kit, name), encoding="utf-8")
    return path.relative_to(memory.root(settings)).as_posix()


def tool_definitions() -> list[dict]:
    return [{
        "name": "make_components",
        "description": "Make ready-to-use website components in a brand colour: primary, secondary, ghost and danger "
                       "buttons with hover, pressed, keyboard-focus and disabled states; text boxes with labels, help "
                       "and error text; cards, badges and alerts. Every colour pair is checked and darkened to pass "
                       "WCAG AA. With a name, saves components.css and components.html in Kinetic Web Designs/<name>, "
                       "next to make_brand_kit's files. Answer in plain words.",
        "input_schema": {
            "type": "object",
            "properties": {
                "colour": {"type": "string", "description": "Brand colour, e.g. '#c2410c'."},
                "name": {"type": "string", "description": "Brand or client folder to save in (optional)."},
                "shape": {"type": "string", "enum": list(SHAPES)},
            },
            "required": ["colour"],
            "additionalProperties": False,
        },
    }]


async def run_tool(name: str, args: dict, settings: Settings, http=None) -> str:
    try:
        kit = build(args.get("colour") or "", args.get("shape") or "rounded")
        where = save(settings, kit, str(args["name"])) if args.get("name") else ""
        return summary(kit, where)
    except (TypeError, ValueError) as e:
        return str(e)
