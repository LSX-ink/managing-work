"""Making money: Alfred researches ways to earn on the web and saves each piece of research as files you can
download (a Markdown report plus a web page that opens on any phone or PC), and keeps a board of the ideas
you're trying with what each one has earned.

Reports go in the Work memory folder under Money Research. The ideas board is money-ideas.json in the memory folder.
"""

import html
import json
import re
from datetime import date

import tiktokstudio_store as cs
import memory
import screen
from config import Settings

FILE = "money-ideas.json"
STATUSES = ["idea", "testing", "earning", "dropped"]
MAX_REPORT = 60_000
PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>{title}</title>
<style>body{{max-width:760px;margin:24px auto;padding:0 16px;font:16px/1.6 system-ui,sans-serif;color:#1b1b1b}}
h1,h2,h3{{line-height:1.25}} table{{border-collapse:collapse}} td,th{{border:1px solid #ccc;padding:4px 8px}}
a{{color:#0b57d0}} .meta{{color:#666;font-size:14px}}</style></head><body>
<p class="meta">Researched by Alfred on {day}</p>{body}</body></html>"""


def money(n: float, settings: Settings) -> str:
    symbol = {"GBP": "£", "USD": "$", "EUR": "€", "ZAR": "R"}.get(settings.currency, settings.currency + " ")
    return f"{symbol}{n:,.2f}"


# ---- research reports ---------------------------------------------------------------------------------------

def research(args: dict) -> str:
    topic = cs.clean(args.get("topic"), 300) or "realistic ways to make extra money"
    about = []
    for key, label in (("budget", "starting budget"), ("hours", "hours a week"), ("skills", "skills"),
                       ("country", "country")):
        if cs.clean(args.get(key)):
            about.append(f"{label}: {cs.clean(args.get(key), 200)}")
    return (f"INSTRUCTION for Alfred: research '{topic}' for the user" + (f" ({'; '.join(about)})" if about else "")
            + ". Use web_search several times (and web_fetch on the best pages) for current, real figures. Then call "
            "money_research with action save_report, a clear title, and a full Markdown report with: a two-line "
            "summary; a table of the options (start-up cost, time to first money, realistic monthly earnings, "
            "difficulty); for the best three, step-by-step how to start this week; the risks and scams to avoid; "
            "and a Sources list of the links you used. Be honest about what's realistic and never promise income. "
            "Then tell the user in one or two sentences what you found and that the files are ready to download.")


def markdown_html(text: str) -> str:
    """A small Markdown-to-HTML for the report page: headings, lists, tables, bold, links; everything escaped."""
    out, in_list, in_table = [], False, False

    def inline(s: str) -> str:
        s = html.escape(s)
        s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
        return re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", r'<a href="\2">\1</a>', s)

    for line in text.splitlines():
        stripped = line.strip()
        if in_list and not re.match(r"^([-*]|\d+\.)\s", stripped):
            out.append("</ul>")
            in_list = False
        if in_table and not stripped.startswith("|"):
            out.append("</table>")
            in_table = False
        if not stripped:
            continue
        heading = re.match(r"^(#{1,4})\s+(.*)", stripped)
        if heading:
            n = len(heading[1])
            out.append(f"<h{n}>{inline(heading[2])}</h{n}>")
        elif re.match(r"^([-*]|\d+\.)\s", stripped):
            if not in_list:
                out.append("<ul>")
                in_list = True
            item = re.sub(r"^([-*]|\d+\.)\s+", "", stripped)
            out.append(f"<li>{inline(item)}</li>")
        elif stripped.startswith("|"):
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
                continue
            if not in_table:
                out.append("<table>")
                in_table = True
            out.append("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in cells) + "</tr>")
        else:
            out.append(f"<p>{inline(stripped)}</p>")
    out += ["</ul>"] if in_list else []
    out += ["</table>"] if in_table else []
    return "\n".join(out)


def save_report(settings: Settings, args: dict) -> screen.Shown:
    title = cs.clean(args.get("title"), 90)
    report = str(args.get("report") or "").strip()[:MAX_REPORT]
    if not title or len(report) < 40:
        raise ValueError("I need a title and the report itself.")
    folder = cs.work_folder(settings, "Money Research")
    name = cs.slug(f"{date.today().isoformat()} {title}", "Research")
    md = memory.unique_path(folder / f"{name}.md")
    md.write_text(f"# {title}\n\n_Researched by Alfred on {date.today():%d %B %Y}_\n\n{report}\n", encoding="utf-8")
    page = md.with_suffix(".html")
    page.write_text(PAGE.format(title=html.escape(title), day=f"{date.today():%d %B %Y}",
                                body=f"<h1>{html.escape(title)}</h1>\n{markdown_html(report)}"), encoding="utf-8")
    link = lambda p: f"/screen/file?path={screen.quote(cs.relative(settings, p))}"
    card = screen.file_card(settings, md, buttons=[{"label": "Download report", "download": link(md)},
                                                   {"label": "Download web page", "download": link(page)}])
    return screen.Shown(f"Saved '{title}' in Money Research as {md.name} and {page.name}.", card)


def reports(settings: Settings) -> screen.Shown:
    folder = cs.work_folder(settings, "Money Research")
    files = sorted(folder.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)[:40]
    items = [{"label": p.stem, "say": f"Show the file {p.name} from Money Research."} for p in files]
    said = f"You have {len(files)} money research report{'s' if len(files) != 1 else ''}." if files else \
        "No money research yet. Ask me to research ways to make money."
    return screen.Shown(said, screen.card("list", "Money research", "money-reports", items=items))


# ---- the ideas board ----------------------------------------------------------------------------------------

def load(settings: Settings) -> list[dict]:
    try:
        data = json.loads((memory.root(settings) / FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = []
    return data if isinstance(data, list) else []


def save(settings: Settings, ideas: list[dict]) -> None:
    (memory.root(settings) / FILE).parent.mkdir(parents=True, exist_ok=True)
    (memory.root(settings) / FILE).write_text(json.dumps(ideas, indent=2, ensure_ascii=False), encoding="utf-8")


def find(ideas: list[dict], name) -> dict:
    want = cs.clean(name, 80).lower()
    for i in ideas:
        if i["name"].lower() == want:
            return i
    match = next((i for i in ideas if want and want in i["name"].lower()), None)
    if not match:
        raise ValueError(f"There's no money idea called {name}. Ideas: {', '.join(i['name'] for i in ideas) or 'none yet'}.")
    return match


def board(settings: Settings, ideas: list[dict]) -> screen.Shown:
    rows = [[i["name"], i["status"], money(i.get("start_cost", 0), settings), str(i.get("hours_week") or "-"),
             money(sum(e["amount"] for e in i.get("earned", [])), settings)] for i in ideas]
    total = sum(e["amount"] for i in ideas for e in i.get("earned", []))
    return screen.Shown(f"{len(ideas)} money idea{'s' if len(ideas) != 1 else ''}, {money(total, settings)} earned so far.",
                        screen.card("table", "Money ideas", "money-ideas",
                                    columns=["Idea", "Status", "Start cost", "Hours/week", "Earned"], rows=rows))


def number(value) -> float:
    try:
        return float(str(value or 0).replace(",", "").lstrip("£$€R"))
    except ValueError:
        raise ValueError("I need that amount as a number.") from None


def add_idea(settings: Settings, args: dict) -> screen.Shown:
    ideas = load(settings)
    name = cs.clean(args.get("idea"), 80)
    if not name:
        raise ValueError("What's the idea called?")
    if any(i["name"].lower() == name.lower() for i in ideas):
        raise ValueError("That idea is already on the board.")
    ideas.append({"name": name, "status": "idea", "start_cost": number(args.get("start_cost")),
                  "hours_week": cs.clean(args.get("hours"), 20), "notes": cs.clean(args.get("notes"), 500),
                  "added": date.today().isoformat(), "earned": []})
    save(settings, ideas)
    return board(settings, ideas)


def update_idea(settings: Settings, args: dict) -> screen.Shown:
    ideas = load(settings)
    idea = find(ideas, args.get("idea"))
    status = cs.clean(args.get("status"), 20).lower()
    if status:
        if status not in STATUSES:
            raise ValueError(f"Status is one of {', '.join(STATUSES)}.")
        idea["status"] = status
    if cs.clean(args.get("notes")):
        idea["notes"] = cs.clean(args.get("notes"), 500)
    save(settings, ideas)
    return board(settings, ideas)


def log_income(settings: Settings, args: dict) -> screen.Shown:
    ideas = load(settings)
    idea = find(ideas, args.get("idea"))
    amount = number(args.get("amount"))
    idea.setdefault("earned", []).append({"amount": amount, "on": date.today().isoformat(),
                                          "note": cs.clean(args.get("notes"), 200)})
    if idea["status"] in ("idea", "testing") and amount > 0:
        idea["status"] = "earning"
    save(settings, ideas)
    return board(settings, ideas)


ACTIONS = ["research", "save_report", "reports", "add_idea", "ideas", "update_idea", "log_income"]


def tool_definitions() -> list[dict]:
    return [{
        "name": "money_research",
        "description": "Ways to make the user money. research (topic, budget, hours, skills, country) tells you how "
                       "to research it on the web and save it. save_report (title, report in Markdown with sources) "
                       "saves the research as a downloadable Markdown file and web page in Work/Money Research and "
                       "shows it with Download buttons. reports lists saved research. The ideas board: add_idea (idea, "
                       "start_cost, hours, notes), ideas shows the board, update_idea (idea, status idea/testing/"
                       "earning/dropped, notes), log_income (idea, amount, notes) records money earned.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "topic": {"type": "string"},
                "budget": {"type": "string"},
                "hours": {"type": "string", "description": "Hours a week the user can give it."},
                "skills": {"type": "string"},
                "country": {"type": "string"},
                "title": {"type": "string"},
                "report": {"type": "string", "description": "save_report: the full report in Markdown."},
                "idea": {"type": "string"},
                "status": {"type": "string", "enum": STATUSES},
                "start_cost": {"type": "number"},
                "amount": {"type": "number"},
                "notes": {"type": "string"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"money_research"}


def run_tool(name: str, args: dict, settings: Settings, http=None):
    action = args.get("action")
    if action == "research":
        return research(args)
    if action == "save_report":
        return save_report(settings, args)
    if action == "reports":
        return reports(settings)
    if action == "add_idea":
        return add_idea(settings, args)
    if action == "ideas":
        return board(settings, load(settings))
    if action == "update_idea":
        return update_idea(settings, args)
    if action == "log_income":
        return log_income(settings, args)
    raise ValueError(f"Unknown money action: {action}")

