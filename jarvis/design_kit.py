"""Brand kits in one step: colours, type, motion, spacing and a style-guide page to open in a browser.

make_brand_kit runs make_palette, make_type_scale and make_motion together for one client, adds spacing, corner and
shadow tokens for a shape (sharp, rounded or pill), and writes style-guide.html: a single page that shows the colour
swatches with their contrast, every heading size, buttons, a card and the spring animation, all drawn with the kit's
own CSS. Everything lands in Kinetic Web Designs/<name>, ready to hand to a client or build a site from.
"""

import html

import design_motion
import design_palette
import design_type
import memory
from config import Settings
from design_contrast import ratio
from design_extract import FOLDER

NAMES = {"make_brand_kit"}
SPACING = [4, 8, 12, 16, 24, 32, 48, 64, 96]
SHAPES = {"sharp": (2, 4, 6), "rounded": (6, 12, 20), "pill": (10, 16, 9999)}
SHADOWS = {"sm": "0 1px 2px rgb(0 0 0 / 0.06)", "md": "0 4px 12px rgb(0 0 0 / 0.08)",
           "lg": "0 12px 32px rgb(0 0 0 / 0.12)"}


def tokens_css(shape: str) -> str:
    small, medium, large = SHAPES[shape]
    lines = [":root {"]
    lines += [f"  --space-{i}: {px / 16:g}rem;" for i, px in enumerate(SPACING, 1)]
    lines += [f"  --radius-sm: {small}px;", f"  --radius-md: {medium}px;", f"  --radius-lg: {large}px;"]
    lines += [f"  --shadow-{k}: {v};" for k, v in SHADOWS.items()]
    return "\n".join(lines + ["}", ""])


def swatch(hex_: str, label: str) -> str:
    text = design_palette.on(hex_)
    return (f'<div class="swatch" style="background:{hex_};color:{text}"><b>{html.escape(label)}</b>'
            f"<span>{hex_}</span><span>{ratio(text, hex_):.1f}:1</span></div>")


def style_guide(name: str, p: dict, scale: dict, m: dict, heading: str, body: str) -> str:
    title = html.escape(name)
    light = p["roles"]["light"]
    shades = "".join(swatch(v, str(k)) for k, v in p["shades"].items())
    greys = "".join(swatch(v, str(k)) for k, v in p["greys"].items())
    accents = "".join(swatch(a["hex"], a["name"]) for a in p["accents"])
    roles = "".join(swatch(v, k) for k, v in light.items() if k not in ("background",))
    sizes = "".join(f'<p class="sample" style="font-size:var(--text-{s["name"]});line-height:var(--leading-{s["name"]});'
                    f'letter-spacing:var(--tracking-{s["name"]})"><small>{s["name"]} · {s["phone"]:g}-{s["desktop"]:g}px'
                    f' · {html.escape(s["use"])}</small><br>{title} makes it simple</p>'
                    for s in reversed(scale["steps"]))
    fonts = html.escape(f"{heading or 'system'} / {body or 'system'}")
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} brand kit</title>
<link rel="stylesheet" href="palette.css">
<link rel="stylesheet" href="type.css">
<link rel="stylesheet" href="motion.css">
<link rel="stylesheet" href="tokens.css">
<style>
body {{ margin: 0; background: var(--background); color: var(--text); font-family: var(--font-body, system-ui); }}
main {{ max-width: 1040px; margin: 0 auto; padding: var(--space-7) var(--space-5); }}
h1, h2 {{ font-family: var(--font-heading, inherit); }}
h2 {{ font-size: var(--text-2xl); margin: var(--space-8) 0 var(--space-4); }}
.muted {{ color: var(--muted-text); }}
.row {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(80px, 1fr)); gap: var(--space-2); }}
.swatch {{ border-radius: var(--radius-md); padding: var(--space-3); min-height: 72px; display: flex;
  flex-direction: column; gap: 2px; font-size: var(--text-sm); box-shadow: var(--shadow-sm); }}
.sample {{ margin: 0 0 var(--space-4); }}
.sample small {{ font-size: var(--text-xs); color: var(--muted-text); letter-spacing: 0; }}
.btn {{ background: var(--button); color: var(--button-text); border: 0; border-radius: var(--radius-md);
  padding: var(--space-3) var(--space-5); font: inherit; cursor: pointer; }}
.btn.ghost {{ background: transparent; color: var(--link); box-shadow: inset 0 0 0 1px var(--border); }}
.card {{ background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-lg);
  padding: var(--space-6); box-shadow: var(--shadow-md); max-width: 420px; }}
a {{ color: var(--link); }}
</style>
</head>
<body>
<main>
<h1>{title}</h1>
<p class="muted">Brand kit · fonts {fonts} · {p['harmony']} colours · {m['feel']} motion. Made by Alfred.</p>
<h2>Brand colour</h2><div class="row">{shades}</div>
<h2>Greys</h2><div class="row">{greys}</div>
{"<h2>Accents</h2><div class='row'>" + accents + "</div>" if accents else ""}
<h2>Page colours</h2><div class="row">{roles}</div>
<h2>Type</h2>{sizes}
<h2>Buttons and cards</h2>
<p><button class="btn">Get a quote</button> <button class="btn ghost">See our work</button></p>
<div class="card pop-in"><h3 style="margin-top:0">A card that springs in</h3>
<p class="muted">Spring {m['spring_ms']}ms with {m['bounce']}% overshoot. <a href="#">A link in the brand colour</a>.</p></div>
</main>
</body>
</html>
"""


def build(settings: Settings, args: dict) -> str:
    name = str(args.get("name") or "").strip()
    if not name:
        raise ValueError("Give the brand or client a name so I know which folder to make.")
    shape = str(args.get("shape") or "rounded").lower()
    if shape not in SHAPES:
        raise ValueError(f"Pick a shape: {', '.join(SHAPES)}.")
    heading = str(args.get("heading_font") or "").strip()
    body = str(args.get("body_font") or "").strip()
    p = design_palette.build(args.get("colour") or "", args.get("harmony") or "complementary")
    scale = design_type.build(args.get("base") or 16, args.get("ratio") or "major-third")
    m = design_motion.build(args.get("feel") or "smooth")
    where = design_palette.save(settings, p, name)
    design_type.save(settings, scale, name, heading, body)
    design_motion.save(settings, m, name)
    folder = memory.root(settings) / where
    (folder / "tokens.css").write_text(tokens_css(shape), encoding="utf-8")
    (folder / "style-guide.html").write_text(style_guide(memory.safe_name(name), p, scale, m, heading, body),
                                             encoding="utf-8")
    light = p["roles"]["light"]
    return (f"Brand kit for {name} saved in {where}: style-guide.html (open it in a browser to see everything), "
            f"palette, type, motion and tokens files.\nBrand {p['brand']} ({p['name']}), button text "
            f"{light['button text']}, body text {light['text']} on {light['background']}; "
            + (f"{p['harmony']} accents " + ", ".join(a["hex"] for a in p["accents"]) + "; " if p["accents"] else "")
            + f"type ratio {scale['ratio']} from {scale['base']:g}px; {m['feel']} motion; {shape} corners."
            + (f" Fonts: {heading or 'system'} headings, {body or 'system'} text." if heading or body else ""))


def tool_definitions() -> list[dict]:
    return [{
        "name": "make_brand_kit",
        "description": "Make a whole brand kit for a client or brand in one go: colour palette (make_palette), type "
                       "scale (make_type_scale), motion (make_motion), spacing, corner and shadow tokens, and "
                       "style-guide.html, a page showing it all with the kit's own CSS. Saves to Kinetic Web "
                       "Designs/<name>. Use when starting a new website or brand; use the single tools to change one "
                       "part. Answer in plain words and tell the user to open style-guide.html.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Brand or client name (the folder)."},
                "colour": {"type": "string", "description": "Brand colour, e.g. '#c2410c'."},
                "harmony": {"type": "string", "enum": list(design_palette.HARMONIES)},
                "heading_font": {"type": "string"},
                "body_font": {"type": "string"},
                "ratio": {"type": "string", "description": "Type ratio, e.g. 'major-third' or 'perfect-fourth'."},
                "base": {"type": "number", "minimum": 12, "maximum": 24},
                "feel": {"type": "string", "enum": list(design_motion.FEELS)},
                "shape": {"type": "string", "enum": list(SHAPES)},
            },
            "required": ["name", "colour"],
            "additionalProperties": False,
        },
    }]


async def run_tool(name: str, args: dict, settings: Settings, http=None) -> str:
    try:
        return build(settings, args)
    except (TypeError, ValueError) as e:
        return str(e)
