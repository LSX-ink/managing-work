"""Layout grids and spacing: the columns, gutters, margins and gaps that keep a website lined up on every screen.

make_layout gives a page grid (4 columns on phones, 8 on tablets, 12 or a chosen number on desktop) with fluid gutters
and page margins, a container width, and a fluid spacing scale from 3xs to 3xl, all sized with CSS clamp() between a
360px phone and a 1280px desktop, the same way make_type_scale sizes text. A density (compact, comfortable, spacious)
sets how airy it feels. With a name it saves layout.md, layout.css (ready-made .container, .grid, .span-N, .auto-grid,
.stack and .cluster classes) and layout-preview.html, which draws the columns so they can be checked at any width.
"""

import html

import memory
from config import Settings
from design_extract import FOLDER
from design_type import MAX_VW, MIN_VW, clamp

NAMES = {"make_layout"}
BREAKPOINTS = {"sm": 640, "md": 768, "lg": 1024, "xl": 1280}
# density: (gutter phone, gutter desktop, margin phone, margin desktop, space base phone, space base desktop) in px
DENSITIES = {"compact": (12, 20, 16, 40, 14, 16), "comfortable": (16, 32, 20, 64, 16, 20),
             "spacious": (20, 48, 24, 96, 18, 24)}
SPACE_STEPS = {"3xs": 0.25, "2xs": 0.5, "xs": 0.75, "s": 1, "m": 1.5, "l": 2, "xl": 3, "2xl": 4, "3xl": 6}
SPACE_USE = {"3xs": "icon to label", "2xs": "tight gaps", "xs": "inside buttons", "s": "between lines and inputs",
             "m": "inside cards", "l": "between cards", "xl": "between blocks", "2xl": "between sections",
             "3xl": "hero padding"}


def build(density: str = "comfortable", columns: int = 12, max_width: int = 1200) -> dict:
    density = str(density or "comfortable").lower()
    if density not in DENSITIES:
        raise ValueError(f"Pick a density: {', '.join(DENSITIES)}.")
    columns, max_width = int(columns), int(max_width)
    if not 4 <= columns <= 16:
        raise ValueError("Use between 4 and 16 desktop columns (12 is the usual).")
    if not 640 <= max_width <= 1920:
        raise ValueError("Keep the container width between 640 and 1920px (1200 is the usual).")
    gutter_s, gutter_l, margin_s, margin_l, base_s, base_l = DENSITIES[density]
    space = [{"name": k, "phone": round(base_s * m, 1), "desktop": round(base_l * m, 1), "use": SPACE_USE[k]}
             for k, m in SPACE_STEPS.items()]
    for step in space:
        step["css"] = clamp(step["phone"], step["desktop"])
    usable = max_width - 2 * margin_l
    column = (usable - (columns - 1) * gutter_l) / columns
    return {"density": density, "columns": {"phone": 4, "tablet": 8 if columns >= 8 else columns, "desktop": columns},
            "gutter": {"phone": gutter_s, "desktop": gutter_l, "css": clamp(gutter_s, gutter_l)},
            "margin": {"phone": margin_s, "desktop": margin_l, "css": clamp(margin_s, margin_l)},
            "max_width": max_width, "column_width": round(column, 1), "space": space}


def css(layout: dict) -> str:
    cols = layout["columns"]
    lines = [f"/* Layout grid and spacing by Alfred. Fluid from a {MIN_VW}px phone to a {MAX_VW}px desktop. */",
             ":root {", f"  --columns: {cols['phone']};", f"  --gutter: {layout['gutter']['css']};",
             f"  --page-margin: {layout['margin']['css']};", f"  --container: {layout['max_width'] / 16:g}rem;"]
    lines += [f"  --space-{s['name']}: {s['css']};" for s in layout["space"]]
    lines += ["}", f"@media (min-width: {BREAKPOINTS['md']}px) {{ :root {{ --columns: {cols['tablet']}; }} }}",
              f"@media (min-width: {BREAKPOINTS['lg']}px) {{ :root {{ --columns: {cols['desktop']}; }} }}", "",
              ".container { width: 100%; max-width: var(--container); margin-inline: auto;"
              " padding-inline: var(--page-margin); box-sizing: border-box; }",
              ".grid { display: grid; grid-template-columns: repeat(var(--columns), minmax(0, 1fr));"
              " gap: var(--gutter); }",
              ".grid > * { grid-column: 1 / -1; }  /* full width on phones until a span says otherwise */"]
    for bp, at in (("md", BREAKPOINTS["md"]), ("lg", BREAKPOINTS["lg"])):
        n = cols["tablet"] if bp == "md" else cols["desktop"]
        spans = " ".join(f".{bp}\\:span-{i} {{ grid-column: span {i}; }}" for i in range(1, n + 1))
        lines.append(f"@media (min-width: {at}px) {{ {spans} }}")
    lines += ["/* Cards that wrap by themselves: as many 280px-or-wider columns as fit */",
              ".auto-grid { display: grid; gap: var(--gutter);"
              " grid-template-columns: repeat(auto-fill, minmax(min(100%, 280px), 1fr)); }",
              ".stack { display: flex; flex-direction: column; gap: var(--stack-gap, var(--space-s)); }",
              ".cluster { display: flex; flex-wrap: wrap; align-items: center; gap: var(--space-xs) var(--space-s); }",
              ".section { padding-block: var(--space-2xl); }", ""]
    return "\n".join(lines)


def markdown(layout: dict, name: str) -> str:
    cols, g, m = layout["columns"], layout["gutter"], layout["margin"]
    rows = "\n".join(f"| {s['name']} | {s['phone']:g}px | {s['desktop']:g}px | {s['use']} |" for s in layout["space"])
    return (f"# {name} layout ({layout['density']})\n\n"
            f"- Columns: {cols['phone']} on phones, {cols['tablet']} from {BREAKPOINTS['md']}px, "
            f"{cols['desktop']} from {BREAKPOINTS['lg']}px\n"
            f"- Gutters {g['phone']}-{g['desktop']}px, page margins {m['phone']}-{m['desktop']}px\n"
            f"- Container {layout['max_width']}px, so each desktop column is about {layout['column_width']:g}px\n"
            f"- Breakpoints: " + ", ".join(f"{k} {v}px" for k, v in BREAKPOINTS.items()) + "\n\n"
            "| Space | Phone | Desktop | Use for |\n|---|---|---|---|\n" + rows + "\n\n"
            "Use the classes in layout.css: `.container` > `.grid` with `md:span-4 lg:span-6` children, `.auto-grid` "
            "for card lists, `.stack` and `.cluster` for spacing inside blocks, `.section` between page sections.\n")


def preview(layout: dict, name: str) -> str:
    desktop = layout["columns"]["desktop"]
    cells = "".join(f'<div class="col">{i}</div>' for i in range(1, desktop + 1))
    half = desktop // 2
    third = desktop // 3 if desktop % 3 == 0 else half
    spaces = "".join(f'<div class="cluster"><span class="bar" style="width:var(--space-{s["name"]})"></span>'
                     f'<small>--space-{s["name"]} · {s["phone"]:g}-{s["desktop"]:g}px · {html.escape(s["use"])}'
                     f"</small></div>" for s in layout["space"])
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(name)} layout</title><link rel="stylesheet" href="layout.css">
<style>
body {{ margin: 0; font-family: system-ui, sans-serif; color: #1f2937; background: #fff; }}
.grid > .col {{ grid-column: auto; }}
.col {{ background: rgb(239 68 68 / 0.14); color: #b91c1c; font-size: 12px; text-align: center; padding: 8px 0; }}
.box {{ background: #eef2ff; border: 1px solid #c7d2fe; border-radius: 8px; padding: var(--space-m); }}
.bar {{ display: inline-block; height: 16px; background: #6366f1; border-radius: 2px; }}
small {{ color: #6b7280; }}
</style></head>
<body><main class="container section stack" style="--stack-gap: var(--space-l)">
<h1 style="margin:0">{html.escape(name)} layout</h1>
<p style="margin:0">{layout['density'].title()} · {desktop} columns · {layout['max_width']}px container.
Make the window narrower to watch it go to {layout['columns']['tablet']} then {layout['columns']['phone']} columns.</p>
<div class="grid">{cells}</div>
<div class="grid"><div class="box md:span-{layout['columns']['tablet'] // 2} lg:span-{half}">Half</div>
<div class="box md:span-{layout['columns']['tablet'] // 2} lg:span-{half}">Half</div>
<div class="box md:span-{layout['columns']['tablet'] // 2} lg:span-{third}">Third</div>
<div class="box md:span-{layout['columns']['tablet'] // 2} lg:span-{desktop - third}">The rest</div></div>
<h2 style="margin:0">Cards that wrap</h2>
<div class="auto-grid">{''.join(f'<div class="box">Card {i}</div>' for i in range(1, 7))}</div>
<h2 style="margin:0">Spacing</h2><div class="stack">{spaces}</div>
</main></body></html>
"""


def save(settings: Settings, layout: dict, name: str) -> str:
    name = memory.safe_name(name, "folder name")
    (memory.root(settings) / FOLDER).mkdir(parents=True, exist_ok=True)
    path = memory.folder(settings, f"{FOLDER}/{name}", create=True)
    (path / "layout.md").write_text(markdown(layout, name), encoding="utf-8")
    (path / "layout.css").write_text(css(layout), encoding="utf-8")
    (path / "layout-preview.html").write_text(preview(layout, name), encoding="utf-8")
    return path.relative_to(memory.root(settings)).as_posix()


def summary(layout: dict) -> str:
    cols, g, m = layout["columns"], layout["gutter"], layout["margin"]
    space = ", ".join(f"{s['name']} {s['phone']:g}-{s['desktop']:g}" for s in layout["space"])
    return (f"Layout grid ({layout['density']}): {cols['phone']} columns on phones, {cols['tablet']} on tablets, "
            f"{cols['desktop']} on desktop; gutters {g['phone']}-{g['desktop']}px, page margins "
            f"{m['phone']}-{m['desktop']}px, {layout['max_width']}px container (desktop columns about "
            f"{layout['column_width']:g}px). Spacing in px: {space}.")


def tool_definitions() -> list[dict]:
    return [{
        "name": "make_layout",
        "description": "Make a website layout grid and spacing system: columns for phone, tablet and desktop, fluid "
                       "gutters and page margins, a container width and a spacing scale (3xs to 3xl) with CSS "
                       "clamp(). Density sets how airy it is. With a name, saves layout.md, layout.css (container, "
                       "grid, span, auto-grid, stack and cluster classes) and layout-preview.html in Kinetic Web "
                       "Designs/<name>, next to make_brand_kit's files. Answer in plain words.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Brand or client folder to save in (optional)."},
                "density": {"type": "string", "enum": list(DENSITIES)},
                "columns": {"type": "integer", "minimum": 4, "maximum": 16, "description": "Desktop columns."},
                "max_width": {"type": "integer", "minimum": 640, "maximum": 1920,
                              "description": "Container width in px (default 1200)."},
            },
            "additionalProperties": False,
        },
    }]


async def run_tool(name: str, args: dict, settings: Settings, http=None) -> str:
    try:
        layout = build(args.get("density") or "comfortable", args.get("columns") or 12, args.get("max_width") or 1200)
        text = summary(layout)
        if args.get("name"):
            where = save(settings, layout, str(args["name"]))
            text += f" Saved layout.md, layout.css and layout-preview.html in {where}; open the preview to check it."
        return text
    except (TypeError, ValueError) as e:
        return str(e)
