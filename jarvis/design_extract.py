"""Design system extraction: read a website's look and write it down as design tokens.

Alfred fetches the page, its linked stylesheets (at most MAX_SHEETS, each up to MAX_CSS bytes) and its inline styles,
then pulls out the colours, CSS variables, fonts, type scale, spacing, corner radii, shadows, breakpoints and motion.
Colours are grouped into brand, background, text, border and accent with simple rules (which property uses them, how
light and how saturated they are). The result is spoken as a short summary and, unless save is false, written into
the memory folder Kinetic Web Designs/<name> as DESIGN.md, tokens.json (W3C design tokens format) and tokens.css.

Every link, including each stylesheet and every redirect, is checked with memory.check_public first, so a page can't
steer Alfred into this PC or the home network. Only plain HTTP is used: no scripts run and nothing is sent.
"""

import asyncio
import colorsys
import json
import re
from collections import Counter
from datetime import date
from html.parser import HTMLParser
from urllib.parse import parse_qs, urljoin, urlparse

import httpx

import memory
from config import Settings

NAMES = {"extract_design_system"}
FOLDER = "Kinetic Web Designs"
MAX_SHEETS = 8
MAX_CSS = 2 * 1024 * 1024
MAX_HTML = 3 * 1024 * 1024
TIMEOUT = 10
HEADERS = {"User-Agent": "Mozilla/5.0 Alfred-assistant"}
GENERIC_FONTS = {"serif", "sans-serif", "monospace", "cursive", "fantasy", "system-ui", "ui-sans-serif", "ui-serif",
                 "ui-monospace", "ui-rounded", "inherit", "initial", "unset", "revert", "emoji", "math", "fangsong",
                 "-apple-system", "blinkmacsystemfont"}
NAMED = {"white": "#ffffff", "black": "#000000"}
COLOUR = re.compile(r"#[0-9a-fA-F]{3,8}\b|\b(?:rgba?|hsla?)\([^)]*\)|\b(?:white|black)\b", re.I)
LENGTH = re.compile(r"^(-?\d*\.?\d+)(px|rem|em|pt)$")
DECL = re.compile(r"(?<![\w-])(--[\w-]+|[a-zA-Z-]+)\s*:\s*([^;{}]+?)\s*(?=[;}])")
EASING = re.compile(r"cubic-bezier\([^)]*\)|steps\([^)]*\)|\bease-in-out\b|\bease-in\b|\bease-out\b|\bease\b|\blinear\b")


class TooBig(Exception):
    pass


# ---- fetching ----------------------------------------------------------------------

async def fetch(http: httpx.AsyncClient, url: str, limit: int) -> tuple[str, str, str]:
    """(final url, content type, text) of a public link, re-checked after every redirect; TooBig past limit bytes."""
    for _ in range(6):
        await memory.check_public(url)
        try:
            async with http.stream("GET", url, follow_redirects=False, timeout=TIMEOUT, headers=HEADERS) as r:
                if r.is_redirect:
                    url = urljoin(url, r.headers["location"])
                    continue
                if r.status_code != 200:
                    raise ValueError(f"The site answered {r.status_code}, so I couldn't read it.")
                length = r.headers.get("content-length", "")
                if length.isdigit() and int(length) > limit:
                    raise TooBig
                body = bytearray()
                async for chunk in r.aiter_bytes():
                    body += chunk
                    if len(body) > limit:
                        raise TooBig
                return str(r.url), r.headers.get("content-type", "").lower(), \
                    body.decode(r.charset_encoding or "utf-8", errors="replace")
        except httpx.HTTPError:
            raise ValueError("I couldn't reach that site; check the address or try again later.") from None
    raise ValueError("That link redirected too many times.")


class PageParser(HTMLParser):
    """Title, theme colour, favicon, stylesheet links, <style> blocks and style="" attributes of a page."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title, self.theme, self.icon = "", "", ""
        self.sheets, self.styles, self.inline = [], [], []
        self._in = ""

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v or "") for k, v in attrs}
        if a.get("style"):
            self.inline.append(a["style"])
        rel = a.get("rel", "").lower().split()
        if tag == "link" and "stylesheet" in rel and a.get("href"):
            self.sheets.append(a["href"])
        elif tag == "link" and "icon" in rel and a.get("href") and not self.icon:
            self.icon = a["href"]
        elif tag == "meta" and a.get("name", "").lower() == "theme-color" and not self.theme:
            self.theme = a.get("content", "").strip()
        elif tag in ("title", "style"):
            self._in = tag

    def handle_endtag(self, tag):
        if tag == self._in:
            self._in = ""

    def handle_data(self, data):
        if self._in == "title" and not self.title:
            self.title = re.sub(r"\s+", " ", data).strip()[:120]
        elif self._in == "style":
            self.styles.append(data)


def google_fonts(url: str) -> list[str]:
    """Family names in a fonts.googleapis.com link."""
    if "fonts.googleapis.com" not in url:
        return []
    return [f.split(":")[0].replace("+", " ").strip() for f in parse_qs(urlparse(url).query).get("family", [])
            for f in f.split("|") if f.strip()]


def imports(css: str) -> list[str]:
    return re.findall(r"@import\s+(?:url\()?\s*[\"']?([^\"')\s;]+)", css)


# ---- colours -----------------------------------------------------------------------

def to_hex(text: str) -> str:
    """A CSS colour as #rrggbb (or #rrggbbaa when see-through); empty if it can't be read or is invisible."""
    t = text.strip().lower()
    if t in NAMED:
        return NAMED[t]
    if t.startswith("#"):
        h = t[1:]
        if len(h) in (3, 4):
            h = "".join(c * 2 for c in h)
        if len(h) not in (6, 8):
            return ""
        if len(h) == 8:
            if h[6:] == "00":
                return ""
            if h[6:] == "ff":
                h = h[:6]
        return "#" + h
    m = re.match(r"(rgba?|hsla?)\((.*)\)", t)
    if not m:
        return ""
    parts = [p for p in re.split(r"[\s,/]+", m.group(2).strip()) if p]
    if len(parts) < 3:
        return ""
    try:
        alpha = 1.0
        if len(parts) > 3:
            alpha = float(parts[3][:-1]) / 100 if parts[3].endswith("%") else float(parts[3])
        if m.group(1).startswith("rgb"):
            rgb = [float(p[:-1]) * 2.55 if p.endswith("%") else float(p) for p in parts[:3]]
        else:
            hue = float(re.sub(r"deg$", "", parts[0])) % 360 / 360
            sat, light = (float(p.rstrip("%")) / 100 for p in parts[1:3])
            rgb = [c * 255 for c in colorsys.hls_to_rgb(hue, light, sat)]
    except ValueError:
        return ""
    if alpha <= 0:
        return ""
    out = "#" + "".join(f"{max(0, min(255, round(c))):02x}" for c in rgb)
    return out if alpha >= 1 else out + f"{round(alpha * 255):02x}"


def hls(hex_: str) -> tuple[float, float, float]:
    r, g, b = (int(hex_[i:i + 2], 16) / 255 for i in (1, 3, 5))
    return colorsys.rgb_to_hls(r, g, b)


def colour_name(hex_: str) -> str:
    h, l, s = hls(hex_)
    if s < 0.15 or l < 0.15 or l > 0.92:
        return "white" if l > 0.9 else "black" if l < 0.15 else "grey"
    deg = h * 360
    for top, name in ((15, "red"), (45, "orange"), (70, "yellow"), (165, "green"), (195, "teal"), (255, "blue"),
                      (290, "purple"), (345, "pink"), (361, "red")):
        if deg < top:
            return name
    return "red"


# ---- CSS reading -------------------------------------------------------------------

def var_role(name: str) -> str:
    n = name.lower()
    for role, words in (("brand", ("primary", "brand")), ("accent", ("accent", "secondary", "highlight")),
                        ("border", ("border", "stroke", "divider", "outline")),
                        ("background", ("bg", "background", "surface", "canvas", "base")),
                        ("text", ("text", "foreground", "fg", "ink", "body", "heading"))):
        if any(w in n for w in words):
            return role
    return ""


def prop_role(prop: str) -> str:
    if prop.startswith("background"):
        return "background"
    if prop == "color":
        return "text"
    if prop.startswith(("border", "outline")):
        return "border"
    return ""


def px(value: str) -> float | None:
    m = LENGTH.match(value.strip().lower())
    if not m:
        return None
    n = float(m.group(1))
    return n * {"px": 1, "rem": 16, "em": 16, "pt": 4 / 3}[m.group(2)]


def tidy(n: float) -> str:
    return f"{n:g}px" if n == int(n) else f"{round(n, 1):g}px"


def resolve(value: str, variables: dict) -> str:
    """Swap var(--x, fallback) for the variable's value, a few levels deep."""
    for _ in range(4):
        if "var(" not in value:
            break
        value = re.sub(r"var\(\s*(--[\w-]+)\s*(?:,\s*([^()]*(?:\([^()]*\))?[^()]*))?\)",
                       lambda m: variables.get(m.group(1), m.group(2) or ""), value)
    return value


def first_family(stack: str) -> str:
    for part in stack.split(","):
        name = part.strip().strip("\"'").strip()
        if name and name.lower() not in GENERIC_FONTS and not name.lower().startswith("var("):
            return name
    return ""


def analyse(css: str) -> dict:
    """Design tokens found in a lump of CSS."""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    faces = [first_family(m) for m in re.findall(r"@font-face\s*{[^}]*?font-family\s*:\s*([^;}]+)", css, re.I)]
    css = re.sub(r"@font-face\s*{[^}]*}", "", css, flags=re.I)
    decls = [(p.lower(), v.strip()) for p, v in DECL.findall(css)]
    decls = [(p, re.sub(r"\s*!important$", "", v, flags=re.I)) for p, v in decls]
    variables = {}
    for p, v in decls:
        if p.startswith("--"):
            variables.setdefault(p, v)
    colours, roles = Counter(), {}
    fonts, stacks, sizes, weights, heights = Counter(), {}, Counter(), Counter(), Counter()
    spacing, radii, shadows, durations, easings = Counter(), Counter(), Counter(), Counter(), Counter()

    def add_colours(value, role):
        for c in COLOUR.findall(re.sub(r"url\([^)]*\)", "", value)):
            hex_ = to_hex(c)
            if hex_:
                colours[hex_] += 1
                if role:
                    roles.setdefault(hex_, Counter())[role] += 1

    for p, raw in decls:
        if p.startswith("--"):
            add_colours(raw, var_role(p))
            continue
        v = resolve(raw, variables).strip()
        if not v:
            continue
        if p in ("box-shadow", "text-shadow"):
            if p == "box-shadow" and v.lower() not in ("none", "0", "initial", "inherit", "unset"):
                shadows[re.sub(r"\s+", " ", v)] += 1
            continue
        add_colours(v, prop_role(p))
        if p in ("font-family", "font"):
            m = re.search(r"(?:^|\s)\d*\.?\d+(?:px|rem|em|pt|%)(?:/\S+)?\s+(.+)$", v)
            stack = v if p == "font-family" else m.group(1) if m else ""
            name = first_family(stack)
            if name:
                fonts[name] += 1
                stacks.setdefault(name, [s.strip().strip("\"'") for s in stack.split(",") if s.strip()])
        if p == "font-size" and (n := px(v)) and 8 <= n <= 160:
            sizes[round(n * 2) / 2] += 1
        elif p == "font-weight":
            w = {"normal": "400", "bold": "700"}.get(v.lower(), v)
            if w.isdigit():
                weights[int(w)] += 1
        elif p == "line-height" and re.fullmatch(r"\d*\.?\d+(px|rem|em|%)?|normal", v.lower()):
            heights[v.lower()] += 1
        elif re.match(r"(margin|padding)(-(top|right|bottom|left|inline|block)(-start|-end)?)?$|(row-|column-)?gap$", p):
            for part in v.split():
                n = px(part)
                if n and 0 < abs(n) <= 256:
                    spacing[round(abs(n), 1)] += 1
        elif p.startswith("border") and p.endswith("radius"):
            first = v.split("/")[0].split()[0] if v.split() else ""
            n = px(first)
            if first.endswith("%") and first.rstrip("%").replace(".", "").isdigit() and float(first[:-1]) >= 50 or \
                    (n and n >= 999):
                radii["full"] += 1
            elif n is not None and n > 0:
                radii[tidy(n)] += 1
        elif p in ("transition", "transition-duration", "animation", "animation-duration"):
            for num, unit in re.findall(r"(?<![\w.-])(\d*\.?\d+)(ms|s)\b", v):
                ms = float(num) * (1000 if unit == "s" else 1)
                if 0 < ms <= 5000:
                    durations[int(ms)] += 1
            for e in EASING.findall(v):
                easings[e.replace(" ", "")] += 1
        elif p in ("transition-timing-function", "animation-timing-function"):
            for e in EASING.findall(v):
                easings[e.replace(" ", "")] += 1
    points = Counter()
    for prelude in re.findall(r"@media([^{]+){", css, re.I):
        for num, unit in re.findall(r"(?:min|max)-width\s*:\s*(\d*\.?\d+)(px|em|rem)", prelude, re.I):
            points[round(float(num) * (1 if unit.lower() == "px" else 16))] += 1
    return {"colours": colours, "roles": roles, "variables": variables, "fonts": fonts, "stacks": stacks,
            "faces": [f for f in faces if f], "sizes": sizes, "weights": weights, "heights": heights,
            "spacing": spacing, "radii": radii, "shadows": shadows, "breakpoints": points, "durations": durations,
            "easings": easings}


# ---- grouping ----------------------------------------------------------------------

def group_colours(colours: Counter, roles: dict) -> dict:
    """Pick brand, background, text, border and accent colours from the counted colours."""
    solid = [c for c, _ in colours.most_common() if len(c) == 7]
    role = lambda c, r: roles.get(c, Counter())[r]  # noqa: E731
    sat = lambda c: hls(c)[2] if 0.08 < hls(c)[1] < 0.95 else 0  # noqa: E731

    def best(r, ok, exclude=()):
        pool = [c for c in solid if c not in exclude and ok(c)]
        ranked = sorted(pool, key=lambda c: (role(c, r), colours[c]), reverse=True)
        return ranked[0] if ranked and role(ranked[0], r) else ""

    picked = {}
    picked["background"] = best("background", lambda c: sat(c) < 0.3) or \
        next((c for c in solid if hls(c)[1] > 0.93), "")
    bg_light = hls(picked["background"])[1] if picked["background"] else 1.0
    far = lambda c: abs(hls(c)[1] - bg_light) > 0.4  # noqa: E731
    picked["text"] = best("text", lambda c: sat(c) < 0.4 and far(c), [picked["background"]]) or \
        next((c for c in solid if sat(c) < 0.4 and far(c)), "")
    vivid = lambda c: sat(c) >= 0.35 and 0.2 <= hls(c)[1] <= 0.8  # noqa: E731
    used = [picked["background"], picked["text"]]
    picked["brand"] = best("brand", lambda c: sat(c) >= 0.2, used) or next((c for c in solid if c not in used
                                                                            and vivid(c)), "")
    used.append(picked["brand"])

    def other_hue(c):
        if not picked["brand"]:
            return True
        d = abs(hls(c)[0] - hls(picked["brand"])[0]) * 360
        return min(d, 360 - d) > 30

    picked["accent"] = best("accent", lambda c: sat(c) >= 0.2, used) or \
        next((c for c in solid if c not in used and vivid(c) and other_hue(c)), "")
    used.append(picked["accent"])
    picked["border"] = best("border", lambda c: True, used)
    return {k: picked[k] for k in ("brand", "background", "text", "border", "accent")}


def ordered_scale(counter: Counter, top: int) -> list[float]:
    return sorted(v for v, _ in counter.most_common(top))


def radius_sort(value: str) -> float:
    return 10_000 if value == "full" else float(value[:-2])


def vibe(found: dict) -> str:
    groups, bg = found["groups"], found["groups"]["background"]
    mood = "dark" if bg and hls(bg)[1] < 0.35 else "light"
    radii = [r for r, _ in found["radii"].most_common(3)]
    main = radii[0] if radii else ""
    corners = "square, sharp corners" if not main or main != "full" and float(main[:-2]) <= 2 else \
        "pill-shaped buttons and round corners" if main == "full" or float(main[:-2]) >= 16 else \
        "softly rounded corners"
    shadows = len(found["shadows"])
    depth = "no shadows (flat)" if not shadows else "gentle shadows" if shadows < 4 else "plenty of layered shadows"
    font = found["font_list"][0] if found["font_list"] else ""
    kind = "a serif" if re.search(r"serif|times|georgia|garamond|playfair|merriweather|lora", font, re.I) and \
        "sans" not in font.lower() else "a monospace" if re.search(r"mono|code|courier", font, re.I) else "a sans-serif"
    brand = groups["brand"]
    tone = (("vivid " if hls(brand)[2] > 0.6 else "muted ") + colour_name(brand) + " brand colour") if brand \
        else "a mostly neutral palette"
    return f"A {mood} look with {corners}, {depth}, {kind} typeface and {tone}."


# ---- writing -----------------------------------------------------------------------

def shadow_token(value: str):
    """The first layer of a box-shadow as a DTCG shadow object, else the CSS text."""
    layer = re.split(r",(?![^(]*\))", value)[0].strip()
    colour = COLOUR.search(layer)
    rest = (layer[:colour.start()] + layer[colour.end():]) if colour else layer
    nums = [p for p in rest.replace("inset", "").split() if p]
    if colour and to_hex(colour.group()) and 2 <= len(nums) <= 4 and all(p == "0" or px(p) is not None for p in nums):
        nums = [p if p != "0" else "0px" for p in nums] + ["0px"] * (4 - len(nums))
        return {"color": to_hex(colour.group()), "offsetX": nums[0], "offsetY": nums[1], "blur": nums[2],
                "spread": nums[3], **({"inset": True} if "inset" in layer else {})}
    return value


def tokens(found: dict) -> dict:
    t = {"$description": f"Design tokens extracted from {found['url']} by Alfred on {date.today().isoformat()}."}
    colour = {k: {"$type": "color", "$value": v} for k, v in found["groups"].items() if v}
    colour["palette"] = {str(i + 1): {"$type": "color", "$value": c} for i, c in enumerate(found["palette"])}
    t["color"] = colour
    t["fontFamily"] = {("primary", "secondary", "tertiary")[i] if i < 3 else str(i + 1):
                       {"$type": "fontFamily", "$value": found["stacks"].get(f, [f])} for i, f in
                       enumerate(found["font_list"][:4])}
    t["fontSize"] = {str(i + 1): {"$type": "dimension", "$value": tidy(n)} for i, n in enumerate(found["type_scale"])}
    t["spacing"] = {str(i + 1): {"$type": "dimension", "$value": tidy(n)} for i, n in enumerate(found["space_scale"])}
    t["borderRadius"] = {("full" if r == "full" else str(i + 1)): {"$type": "dimension",
                                                                   "$value": "9999px" if r == "full" else r}
                         for i, r in enumerate(found["radius_scale"])}
    t["shadow"] = {str(i + 1): {"$type": "shadow", "$value": shadow_token(s)} for i, s in enumerate(found["shadow_list"])}
    t["duration"] = {str(i + 1): {"$type": "duration", "$value": f"{ms}ms"} for i, ms in enumerate(found["duration_list"])}
    return t


def css_file(found: dict) -> str:
    lines = [f"/* Design tokens extracted from {found['url']} by Alfred. */", ":root {"]
    lines += [f"  --color-{k}: {v};" for k, v in found["groups"].items() if v]
    lines += [f"  --color-palette-{i + 1}: {c};" for i, c in enumerate(found["palette"])]
    for i, f in enumerate(found["font_list"][:4]):
        stack = ", ".join(f'"{s}"' if " " in s else s for s in found["stacks"].get(f, [f]))
        lines.append(f"  --font-{('primary', 'secondary', 'tertiary')[i] if i < 3 else i + 1}: {stack};")
    lines += [f"  --font-size-{i + 1}: {tidy(n)};" for i, n in enumerate(found["type_scale"])]
    lines += [f"  --space-{i + 1}: {tidy(n)};" for i, n in enumerate(found["space_scale"])]
    lines += [f"  --radius-{'full' if r == 'full' else i + 1}: {'9999px' if r == 'full' else r};"
              for i, r in enumerate(found["radius_scale"])]
    lines += [f"  --shadow-{i + 1}: {s};" for i, s in enumerate(found["shadow_list"])]
    lines += [f"  --duration-{i + 1}: {ms}ms;" for i, ms in enumerate(found["duration_list"])]
    lines += [f"  --ease-{i + 1}: {e};" for i, e in enumerate(found["easing_list"])]
    own = list(found["variables"].items())[:60]
    if own:
        lines.append("\n  /* The site's own variables */")
        lines += [f"  {k}: {v};" for k, v in own]
    return "\n".join(lines) + "\n}\n"


def table(head: list[str], rows: list[list]) -> list[str]:
    if not rows:
        return ["None found.", ""]
    out = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    out += ["| " + " | ".join(str(c).replace("|", "\\|") for c in r) + " |" for r in rows]
    return out + [""]


def design_md(found: dict) -> str:
    a = found
    md = [f"# {a['title']} design system", "", f"Extracted from {a['url']} by Alfred on {date.today().isoformat()}.",
          "", "## Overview", "", a["vibe"], "",
          "Pair it with design_advice: ask Alfred to build a page in this style and he'll follow these tokens.", "",
          "## Colours", ""]
    md += table(["Role", "Hex", "Uses"], [[k.title(), f"`{v}`", a["colours"][v]] for k, v in a["groups"].items() if v])
    md += ["### Full palette", ""]
    md += table(["Hex", "Looks", "Uses"], [[f"`{c}`", colour_name(c), a["colours"][c]] for c in a["palette"]])
    md += ["## Typography", ""]
    md += table(["Font", "Stack", "Uses"], [[f, ", ".join(a["stacks"].get(f, [f])), a["fonts"][f]]
                                             for f in a["font_list"]])
    if a["google"]:
        md += ["Google Fonts: " + ", ".join(a["google"]), ""]
    if a["faces"]:
        md += ["Self-hosted fonts (@font-face): " + ", ".join(sorted(set(a["faces"]))), ""]
    md += ["### Type scale", ""]
    md += table(["Step", "Size", "rem"], [[i + 1, tidy(n), f"{n / 16:g}rem"] for i, n in enumerate(a["type_scale"])])
    md += ["Weights: " + (", ".join(str(w) for w in sorted(a["weights"])) or "none set"),
           "Line heights: " + (", ".join(h for h, _ in a["heights"].most_common(6)) or "none set"), "",
           "## Spacing", ""]
    md += table(["Step", "Size", "Uses"], [[i + 1, tidy(n), a["spacing"][n]] for i, n in enumerate(a["space_scale"])])
    md += ["## Corners", ""]
    md += table(["Radius", "Uses"], [[r, a["radii"][r]] for r in a["radius_scale"]])
    md += ["## Shadows", ""]
    md += table(["Shadow", "Uses"], [[f"`{s}`", a["shadows"][s]] for s in a["shadow_list"]])
    md += ["## Breakpoints", ""]
    md += table(["Width", "Uses"], [[f"{b}px", a["breakpoints"][b]] for b in a["breakpoint_list"]])
    md += ["## Motion", "", "Durations: " + (", ".join(f"{ms}ms" for ms in a["duration_list"]) or "none set"),
           "Easings: " + (", ".join(a["easing_list"]) or "none set"), "", "## CSS variables", ""]
    md += table(["Variable", "Value"], [[f"`{k}`", f"`{v[:80]}`"] for k, v in list(a["variables"].items())[:40]])
    if len(a["variables"]) > 40:
        md += [f"...and {len(a['variables']) - 40} more in tokens.css.", ""]
    md += ["## Page details", "", f"- Title: {a['title']}", f"- Theme colour: {a['theme'] or 'none'}",
           f"- Favicon: {a['icon'] or 'none'}", f"- Stylesheets read: {a['sheet_count']}", ""]
    return "\n".join(md)


# ---- the tool ----------------------------------------------------------------------

def check_url(url: str) -> str:
    url = str(url or "").strip()
    if not url:
        raise ValueError("Say which website, e.g. stripe.com.")
    if not re.match(r"^https?://", url, re.I):
        if "://" in url:
            raise ValueError("I can only read http or https websites.")
        url = "https://" + url
    host = urlparse(url).hostname or ""
    if " " in url or not host or ("." not in host and ":" not in host):
        raise ValueError("That doesn't look like a website address. Try something like stripe.com.")
    return url


def default_name(url: str) -> str:
    return re.sub(r"^www\.", "", urlparse(url).hostname or "site")


async def extract(http: httpx.AsyncClient, url: str) -> dict:
    url = check_url(url)
    try:
        final, kind, markup = await fetch(http, url, MAX_HTML)
    except TooBig:
        raise ValueError("That page is too big for me to read.") from None
    if kind and "html" not in kind:
        raise ValueError("That link isn't a web page, so there's no design to read.")
    page = PageParser()
    page.feed(markup)
    css_parts = list(page.styles) + [f"x{{{s}}}" for s in page.inline]
    google = [f for href in page.sheets for f in google_fonts(urljoin(final, href))]
    queue = [urljoin(final, h) for h in page.sheets if "fonts.googleapis.com" not in h]
    queue += [urljoin(final, h) for s in page.styles for h in imports(s)]
    seen, skipped, fetched = set(), 0, 0

    async def one(link):
        try:
            _, kind, text = await fetch(http, link, MAX_CSS)
            return link, "" if "html" in kind else text  # an error page, not a stylesheet
        except TooBig:
            return link, None
        except ValueError:
            return link, ""

    while queue and fetched < MAX_SHEETS:
        batch = []
        for link in queue:
            if link in seen or not link.startswith("http"):
                continue
            seen.add(link)
            if google_fonts(link):
                google += google_fonts(link)
                continue
            if fetched + len(batch) < MAX_SHEETS:
                batch.append(link)
        queue = []
        for link, text in await asyncio.gather(*(one(x) for x in batch)):
            fetched += 1
            if text is None:
                skipped += 1
            elif text:
                css_parts.append(text)
                queue += [urljoin(link, h) for h in imports(text)]
    if not any(p.strip() for p in css_parts):
        raise ValueError("I couldn't find any CSS on that page, so there's no design system to pull out. "
                         "It may build its look with scripts.")
    found = analyse("\n".join(css_parts))
    found["groups"] = group_colours(found["colours"], found["roles"])
    if page.theme and (theme := to_hex(page.theme)) and not found["groups"]["brand"]:
        found["groups"]["brand"] = theme[:7]
    found.update(url=final, title=page.title or default_name(final), theme=page.theme,
                 icon=urljoin(final, page.icon or "/favicon.ico"), google=list(dict.fromkeys(google)),
                 sheet_count=fetched - skipped, skipped=skipped,
                 palette=[c for c, _ in found["colours"].most_common() if len(c) == 7][:12],
                 font_list=list(dict.fromkeys(list(dict.fromkeys(google)) + [f for f, _ in found["fonts"].most_common(6)]))[:6],
                 type_scale=ordered_scale(found["sizes"], 10), space_scale=ordered_scale(found["spacing"], 12),
                 radius_scale=sorted((r for r, _ in found["radii"].most_common(6)), key=radius_sort),
                 shadow_list=[s for s, _ in found["shadows"].most_common(5)],
                 breakpoint_list=ordered_scale(found["breakpoints"], 8),
                 duration_list=ordered_scale(found["durations"], 5), easing_list=[e for e, _ in found["easings"].most_common(4)])
    for f in found["google"]:
        found["stacks"].setdefault(f, [f])
    found["vibe"] = vibe(found)
    return found


def summary(found: dict, where: str = "") -> str:
    g = found["groups"]
    colours = ", ".join(f"{k} {v}" for k, v in g.items() if v) or "no clear colours"
    fonts = ", ".join(f + (" (Google Fonts)" if f in found["google"] else "") for f in found["font_list"][:3]) \
        or "the browser's default fonts"
    scale = ", ".join(f"{n:g}" for n in found["type_scale"][:8])
    radius = [r for r, _ in found["radii"].most_common(2)]
    corner = f"mostly {radius[0]} corners" + (f" (also {radius[1]})" if len(radius) > 1 else "") if radius \
        else "square corners"
    shadow = f"{len(found['shadows'])} shadow style{'s' if len(found['shadows']) != 1 else ''}" if found["shadows"] \
        else "no shadows"
    out = [f"{found['title']}: {found['vibe']}", f"Palette: {colours}.", f"Fonts: {fonts}."]
    if scale:
        out.append(f"Type scale: {scale}px.")
    out.append(f"Shape: {corner}, {shadow}.")
    if found["skipped"]:
        out.append(f"I skipped {found['skipped']} stylesheet{'s' if found['skipped'] > 1 else ''} that were too big.")
    if where:
        out.append(f"Saved DESIGN.md, tokens.json and tokens.css in {where}.")
    return " ".join(out)


def save(settings: Settings, found: dict, name: str) -> str:
    name = memory.safe_name(name, "folder name")
    try:
        memory.folder(settings, FOLDER)
    except ValueError:
        (memory.root(settings) / FOLDER).mkdir(parents=True, exist_ok=True)
    path = memory.folder(settings, f"{FOLDER}/{name}", create=True)
    (path / "DESIGN.md").write_text(design_md(found), encoding="utf-8")
    (path / "tokens.json").write_text(json.dumps(tokens(found), indent=2), encoding="utf-8")
    (path / "tokens.css").write_text(css_file(found), encoding="utf-8")
    return path.relative_to(memory.root(settings)).as_posix()


def tool_definitions() -> list[dict]:
    return [{
        "name": "extract_design_system",
        "description": "Read a website's design system from its HTML and CSS: the colour palette (brand, "
                       "background, text, border, accent with hex codes), CSS variables, fonts and Google Fonts, the "
                       "type scale, weights, spacing, corner radii, shadows, breakpoints and motion. Saves DESIGN.md, "
                       "tokens.json (W3C design tokens) and tokens.css in Kinetic Web Designs/<name>. Pairs with "
                       "design_advice and design_guide: extract a site the user likes, then build in that style. "
                       "Summarise the result in plain words.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "The website, e.g. 'stripe.com'."},
                "name": {"type": "string", "description": "Folder name. Default: the site's domain."},
                "save": {"type": "boolean", "description": "Save the files (default true)."},
            },
            "required": ["url"],
            "additionalProperties": False,
        },
    }]


async def run_tool(name: str, args: dict, settings: Settings, http: httpx.AsyncClient | None = None) -> str:
    if http is None:
        async with httpx.AsyncClient() as own:
            return await run_tool(name, args, settings, own)
    found = await extract(http, args.get("url"))
    where = ""
    if args.get("save", True):
        where = save(settings, found, str(args.get("name") or "").strip() or default_name(found["url"]))
    return summary(found, where)
