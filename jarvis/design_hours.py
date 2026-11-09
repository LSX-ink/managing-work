"""Opening hours: one set of hours turned into a website block Google can read and a door sign, so they always match.

make_opening_hours takes the hours in plain words ("Mon-Fri": "9am-5:30pm", "Sat": "10-4", "Sun": "closed", and split
days like "9-12, 1-5") and makes:
- hours.html: a brand-colour table to paste into a site, with today's row picked out and an "Open now" / "Closed now"
  line worked out in the visitor's browser (it still reads fine with scripts off), plus the schema.org
  openingHoursSpecification JSON-LD Google uses for the hours in search results and Maps;
- hours-sign.png and hours-sign.pdf: an A5 door or window sign (300 dpi, 3mm bleed) with the same hours.
Times are checked (a day can't close before it opens) and written the UK way (9am, 5:30pm). Files go in
Kinetic Web Designs/<name>/web.
"""

import html
import json
import re

from PIL import Image, ImageDraw

import memory
from config import Settings
from design_contrast import AA, colour, fix, ratio, rgb
from design_extract import FOLDER
from design_palette import on
from design_social import fit
from docs_tools import font

NAMES = {"make_opening_hours"}
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
SHORT = {d[:3].lower(): i for i, d in enumerate(DAYS)} | {"tues": 1, "weds": 2, "thur": 3, "thurs": 3}
DPI = 300
MM = DPI / 25.4
BLEED, MARGIN = round(3 * MM), round(12 * MM)
INK, MUTED = (24, 24, 27), (82, 82, 91)


def day_index(word: str) -> int:
    w = word.strip().lower().rstrip(".")
    if w in SHORT:
        return SHORT[w]
    if len(w) >= 3 and w[:3] in SHORT and DAYS[SHORT[w[:3]]].lower().startswith(w):
        return SHORT[w[:3]]  # "Monday", "Wednes"
    raise ValueError(f"I don't know the day '{word}'; use names like Mon or Monday.")


def days_of(key: str) -> list[int]:
    """'Mon-Fri' -> 0..4, 'Sat & Sun' / 'Sat, Sun' -> 5, 6, 'Fri-Mon' wraps round the weekend."""
    out: list[int] = []
    for part in re.split(r"\s*(?:,|&|\band\b)\s*", key.strip()):
        if not part:
            continue
        ends = re.split(r"\s*(?:-|–|\bto\b)\s*", part)
        if len(ends) == 2:
            a, b = day_index(ends[0]), day_index(ends[1])
            span = (b - a) % 7
            out += [(a + i) % 7 for i in range(span + 1)]
        elif len(ends) == 1:
            out.append(day_index(part))
        else:
            raise ValueError(f"I couldn't read the days '{key}'.")
    return out


def minutes(word: str) -> tuple[int, bool]:
    """(minutes after midnight, whether am/pm or a 24-hour time made it certain)."""
    w = word.strip().lower()
    if w in ("noon", "midday"):
        return 12 * 60, True
    if w == "midnight":
        return 24 * 60, True
    m = re.fullmatch(r"(\d{1,2})(?:[:.](\d{2}))?\s*(am|pm)?", w)
    if not m:
        raise ValueError(f"I couldn't read the time '{word}'; use something like 9am, 17:30 or 5:30pm.")
    h, mins, half = int(m.group(1)), int(m.group(2) or 0), m.group(3)
    if mins > 59 or h > 24 or (half and not 1 <= h <= 12):
        raise ValueError(f"'{word}' isn't a real time.")
    if half == "pm" and h != 12:
        h += 12
    elif half == "am" and h == 12:
        h = 0
    return h * 60 + mins, bool(half) or h >= 13 or h == 0


def spans_of(text: str) -> list[tuple[int, int]]:
    """'9am-5:30pm' or '9-12, 1-5' -> [(540, 1050)] / [(540, 720), (780, 1020)]; 'closed' -> [].

    A time without am/pm is read as the afternoon when that's the only way it makes sense: '10-4' closes at 4pm and
    the '1-5' after '9-12' runs 1pm to 5pm.
    """
    t = text.strip().lower()
    if t in ("closed", "shut", "off", "-", ""):
        return []
    if t in ("24 hours", "24h", "open 24 hours", "all day"):
        return [(0, 24 * 60)]
    out: list[tuple[int, int]] = []
    for part in re.split(r"\s*(?:,|&|\band\b)\s*", t):
        ends = re.split(r"\s*(?:-|–|\bto\b)\s*", part)
        if len(ends) != 2:
            raise ValueError(f"I couldn't read the hours '{text}'; use something like 9am-5pm or closed.")
        (start, sure_start), (end, sure_end) = minutes(ends[0]), minutes(ends[1])
        start %= 24 * 60  # opening at midnight is the start of the day
        if not sure_start and out and start < out[-1][1] and start < 12 * 60:
            start += 12 * 60
        if not sure_end and end <= start and end < 12 * 60:
            end += 12 * 60
        if end <= start:
            raise ValueError(f"In '{text}' the closing time is before the opening time.")
        out.append((start, end))
    if any(b[0] < a[1] for a, b in zip(out, out[1:])):
        raise ValueError(f"The times in '{text}' overlap or are out of order.")
    return out


def week_of(hours) -> list[list[tuple[int, int]]]:
    if not isinstance(hours, dict) or not hours:
        raise ValueError("Give the hours by day, e.g. Mon-Fri: 9am-5pm, Sat: 10am-4pm, Sun: closed.")
    week: list[list[tuple[int, int]] | None] = [None] * 7
    for key, value in hours.items():
        for d in days_of(str(key)):
            if week[d] is not None:
                raise ValueError(f"{DAYS[d]} is given twice.")
            week[d] = spans_of(str(value))
    return [w if w is not None else [] for w in week]  # days not given are closed


def nice(m: int) -> str:
    if m in (0, 24 * 60):
        return "midnight"
    if m == 12 * 60:
        return "noon"
    h, mins = divmod(m, 60)
    half = "am" if h < 12 else "pm"
    h = h % 12 or 12
    return f"{h}{':%02d' % mins if mins else ''}{half}"


def words(spans: list[tuple[int, int]]) -> str:
    if not spans:
        return "Closed"
    if spans == [(0, 24 * 60)]:
        return "Open 24 hours"
    return ", ".join(f"{nice(a)} – {nice(b)}" for a, b in spans)


def hhmm(m: int) -> str:
    return "23:59" if m >= 24 * 60 else f"{m // 60:02d}:{m % 60:02d}"


def schema(business: str, week, url: str) -> dict:
    """schema.org LocalBusiness with one openingHoursSpecification per run of days that share the same times."""
    specs = []
    for spans in {tuple(s) for s in week if s}:
        days = [f"https://schema.org/{DAYS[i]}" for i, s in enumerate(week) if tuple(s) == spans]
        for a, b in spans:
            specs.append({"@type": "OpeningHoursSpecification", "dayOfWeek": days, "opens": hhmm(a),
                          "closes": hhmm(b)})
    specs.sort(key=lambda s: (DAYS.index(s["dayOfWeek"][0].rsplit("/", 1)[1]), s["opens"]))
    data = {"@context": "https://schema.org", "@type": "LocalBusiness", "name": business,
            "openingHoursSpecification": specs}
    if url:
        data["url"] = url
    return data


def web_block(business: str, brand: str, week, url: str) -> str:
    accent = brand if ratio(brand, "#ffffff") >= AA else fix(brand, "#ffffff", AA)
    rows = "\n".join(f'    <tr data-day="{(i + 1) % 7}"><th scope="row">{DAYS[i]}</th><td>{words(s)}</td></tr>'
                     for i, s in enumerate(week))
    spans = json.dumps([[[a, b] for a, b in week[(d - 1) % 7]] for d in range(7)])  # JS order: Sunday first
    ld = json.dumps(schema(business, week, url), indent=2).replace("</", "<\\/")
    return f"""<!-- Opening hours for {html.escape(business)}: paste this block where the hours should show. -->
<section class="hours" aria-labelledby="hours-title" style="--hours-accent:{accent}">
  <style>
    .hours {{ font-family: system-ui, sans-serif; max-width: 26rem; color: #18181b; }}
    .hours h2 {{ margin: 0 0 .25rem; font-size: 1.25rem; }}
    .hours .now {{ margin: 0 0 .75rem; font-weight: 600; color: var(--hours-accent); min-height: 1.4em; }}
    .hours table {{ width: 100%; border-collapse: collapse; }}
    .hours th, .hours td {{ text-align: left; padding: .45rem .5rem; border-bottom: 1px solid #e4e4e7; }}
    .hours th {{ font-weight: 500; }}
    .hours td {{ text-align: right; font-variant-numeric: tabular-nums; }}
    .hours tr.today {{ background: color-mix(in srgb, var(--hours-accent) 10%, white); font-weight: 700; }}
    .hours tr.today th {{ box-shadow: inset 4px 0 var(--hours-accent); }}
  </style>
  <h2 id="hours-title">Opening hours</h2>
  <p class="now" aria-live="polite"></p>
  <table>
{rows}
  </table>
  <script>
    (() => {{
      const s = document.currentScript.closest(".hours"), now = new Date(), d = now.getDay();
      const m = now.getHours() * 60 + now.getMinutes(), week = {spans};
      s.querySelector(`tr[data-day="${{d}}"]`)?.classList.add("today");
      const open = week[d].some(([a, b]) => m >= a && m < b);
      s.querySelector(".now").textContent = open ? "Open now" : "Closed now";
    }})();
  </script>
  <script type="application/ld+json">
{ld}
  </script>
</section>
"""


def sign(business: str, brand: str, week, footer: str) -> Image.Image:
    size = (round(148 * MM) + 2 * BLEED, round(210 * MM) + 2 * BLEED)
    image = Image.new("RGB", size, (255, 255, 255))
    d = ImageDraw.Draw(image)
    header = round(330) + BLEED
    d.rectangle((0, 0, size[0], header), fill=rgb(brand))
    inner = size[0] - 2 * (BLEED + MARGIN)
    big, rows = fit(d, business, inner, (96, 84, 72, 62), 1, True)
    d.text((size[0] / 2, BLEED + (header - BLEED) / 2), rows[0], font=font(big, True), fill=rgb(on(brand)),
           anchor="mm")
    accent = rgb(brand if ratio(brand, "#ffffff") >= AA else fix(brand, "#ffffff", AA))
    y = header + round(MARGIN * 1.2)
    d.text((size[0] / 2, y), "OPENING HOURS", font=font(88, True), fill=accent, anchor="mt")
    y += 170
    left, right = BLEED + MARGIN, size[0] - BLEED - MARGIN
    room = size[1] - BLEED - MARGIN - (110 if footer else 0) - y
    step = min(260, room // 7)
    for i, spans in enumerate(week):
        text = words(spans)
        tsize, trows = fit(d, text, inner - 520, (80, 70, 60, 50, 42), 1, False)  # big enough to read through glass
        d.text((left, y + step / 2), DAYS[i], font=font(76, True), fill=INK, anchor="lm")
        d.text((right, y + step / 2), trows[0], font=font(tsize), fill=MUTED if not spans else INK, anchor="rm")
        if i < 6:
            d.line((left, y + step, right, y + step), fill=(228, 228, 231), width=3)
        y += step
    if footer:
        fsize, frows = fit(d, footer, inner, (52, 46, 40), 1, False)
        d.text((size[0] / 2, size[1] - BLEED - MARGIN), frows[0], font=font(fsize), fill=MUTED, anchor="ms")
    return image


def run(settings: Settings, args: dict) -> str:
    business = " ".join(str(args.get("name") or "").split())
    if not business:
        raise ValueError("Give the business name for the opening hours.")
    brand = colour(args.get("colour") or "")
    week = week_of(args.get("hours"))
    if not any(week):
        raise ValueError("Every day is closed; give at least one day's hours.")
    website = " ".join(str(args.get("website") or "").split())
    url = ""
    if website:
        url = website if "://" in website else "https://" + website
        if not re.match(r"(?i)^https://[^\s/]+\.[^\s/]+(/\S*)?$", url):
            raise ValueError(f"'{website}' isn't a web address; use something like lebosbakery.co.uk.")
    footer = " ".join(str(args.get("footer") or "").split())[:80]
    (memory.root(settings) / FOLDER).mkdir(parents=True, exist_ok=True)
    path = memory.folder(settings, f"{FOLDER}/{memory.safe_name(business, 'folder name')}/web", create=True)
    (path / "hours.html").write_text(web_block(business, brand, week, url), encoding="utf-8")
    page = sign(business, brand, week, footer)
    page.save(path / "hours-sign.png", dpi=(DPI, DPI), optimize=True)
    page.save(path / "hours-sign.pdf", "PDF", resolution=DPI)
    where = path.relative_to(memory.root(settings)).as_posix()
    summary = "; ".join(f"{DAYS[i][:3]} {words(s)}" for i, s in enumerate(week))
    return (f"Made the opening hours for {business} in {where}: hours.html to paste into the site (a table with "
            "today picked out, an 'Open now' line, and the schema.org hours Google shows in search and Maps), and "
            f"hours-sign.png and hours-sign.pdf, an A5 door sign with the same hours. The hours: {summary}. Check "
            "Google with its Rich Results Test after the site goes live.")


def tool_definitions() -> list[dict]:
    return [{
        "name": "make_opening_hours",
        "description": "Turn a business's opening hours into a website block (brand-colour table, today picked out, "
                       "'Open now', and schema.org JSON-LD so Google shows the hours in search and Maps) and a "
                       "matching A5 door sign (PNG and print-ready PDF). Hours are plain words by day, e.g. "
                       "{'Mon-Fri': '9am-5:30pm', 'Sat': '10-4', 'Sun': 'closed'}. Saves in Kinetic Web "
                       "Designs/<name>/web. Answer in plain words.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Business name (sign header and folder)."},
                "colour": {"type": "string", "description": "Brand colour, e.g. '#c2410c'."},
                "hours": {"type": "object", "description": "Days (Mon, Mon-Fri, Sat & Sun) to hours ('9am-5pm', "
                                                          "'9-12, 1-5', 'closed', '24 hours'). Missing days are "
                                                          "closed."},
                "website": {"type": "string", "description": "The site's address, for Google's data."},
                "footer": {"type": "string", "description": "Bottom line of the sign, e.g. phone or web address."},
            },
            "required": ["name", "colour", "hours"],
            "additionalProperties": False,
        },
    }]


async def run_tool(name: str, args: dict, settings: Settings, http=None) -> str:
    try:
        return run(settings, args)
    except (TypeError, ValueError) as e:
        return str(e)
