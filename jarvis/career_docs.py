"""Career paperwork: a cover-letter builder that fills a saved template from your CV, a brag file of wins,
and a skills gap list for a target role.

The CV sections are only read (cv.json, edited by docs_tools_forms.py). Letters are saved as Markdown in
Documents/Letters. Kept in career-cover.json, career-brag.json and career-skills.json.
"""

import re

import career_store as cs
import docs_tools as dt
import docs_tools_forms as forms
import memory
import screen
from config import Settings

ACTIONS = ["cover_template", "cover_letter", "brag_add", "brag_show", "skills_gap", "skills_show", "skills_tick"]
DEFAULT_TEMPLATE = (
    "Dear Hiring Manager,\n\n"
    "I am writing to apply for the {role} position at {company}. {profile}\n\n"
    "My experience includes {experience}. My key skills are {skills}.\n\n"
    "I would welcome the chance to talk about how I could contribute to {company}. Thank you for your time and "
    "consideration.\n\nYours faithfully,\n{name}")
PLACEHOLDERS = "{name}, {company}, {role}, {profile}, {experience}, {skills}, {date}"


def _first_line(text: str) -> str:
    return next((re.sub(r"^[-*•\s]+", "", ln).strip() for ln in str(text).splitlines() if ln.strip()), "")


def _items(text: str) -> list[str]:
    parts = re.split(r"[,\n;]", str(text))
    return [re.sub(r"^[-*•\s]+", "", p).strip() for p in parts if p.strip()]


def cover_template(settings: Settings, args: dict) -> screen.Shown:
    text = str(args.get("text") or "").strip()[:4000]
    if not text:
        raise ValueError("What should the template say? Use placeholders like {company} and {role}.")
    cs.save(settings, cs.COVER, {"template": text})
    return screen.Shown("Saved your cover letter template.", screen.card(
        "text", "Cover letter template", "career-cover-template", text=text,
        buttons=[{"label": "Write a letter", "say": "Write a cover letter for "}]))


def _template(settings: Settings) -> str:
    return str(cs.load(settings, cs.COVER, {}).get("template") or DEFAULT_TEMPLATE)


def cover_letter(settings: Settings, args: dict) -> screen.Shown:
    company = cs.need(args.get("company"), "company")
    role = cs.clean(args.get("role"), 80)
    if not role:
        apps = [a for a in cs.load(settings, cs.APPLICATIONS, []) if isinstance(a, dict)
                and a.get("company", "").lower() == company.lower() and a.get("role")]
        role = apps[0]["role"] if apps else "advertised"
    cv = forms.cv_load(settings)
    fills = {
        "name": cv.get("name") or "Your name",
        "company": company, "role": role,
        "profile": _first_line(cv.get("profile", "")) or "",
        "experience": "; ".join(_items(cv.get("experience", ""))[:2]) or "a range of relevant roles",
        "skills": ", ".join(_items(cv.get("skills", ""))[:6]) or "listed on my CV",
        "date": forms.uk_date(cs.today()),
    }
    letter = _template(settings)
    for key, value in fills.items():
        letter = letter.replace("{" + key + "}", str(value))
    letter = re.sub(r" {2,}", " ", letter)
    path = memory.unique_path(dt.home(settings, "Letters") / f"{memory.safe_name(f'Cover letter - {company}', 'title')}.md")
    dt.write(path, letter + "\n")
    tip = "" if cv.get("profile") else " Your CV has no profile yet, so add one and I'll fill it in next time."
    return screen.Shown(f"Wrote a cover letter for {company} and saved it as {path.stem}.{tip}", screen.card(
        "text", f"Cover letter - {company}", f"career-cover-{company}", text=letter,
        buttons=[{"label": "Edit template", "say": "Change my cover letter template."},
                 {"label": "Show my CV", "say": "Show me my CV."}]))


def brag_add(settings: Settings, args: dict) -> screen.Shown:
    win = cs.need(args.get("text"), "win", 300)
    day = cs.parse_date(args.get("date"), "date") or cs.today()
    wins = [w for w in cs.load(settings, cs.BRAG, []) if isinstance(w, dict)]
    wins.append({"date": day.isoformat(), "win": win})
    cs.save(settings, cs.BRAG, wins[-cs.MAX_ROWS:])
    return brag_show(settings, args, f"Added to your brag file. That's {len(wins)} wins.")


def brag_show(settings: Settings, args: dict, said: str = "") -> screen.Shown | str:
    wins = [w for w in cs.load(settings, cs.BRAG, []) if isinstance(w, dict)]
    query = cs.clean(args.get("query")).lower()
    if query:
        wins = [w for w in wins if query in w.get("win", "").lower()]
    if not wins:
        return "Your brag file is empty. Tell me about a win and I'll keep it for your CV and appraisals."
    wins.sort(key=lambda w: w.get("date", ""), reverse=True)
    rows = [[w.get("date", ""), w.get("win", "")] for w in wins]
    return screen.Shown(said or f"{len(wins)} wins in your brag file. The latest: {wins[0]['win']}", screen.card(
        "table", "Brag file", "career-brag", columns=["Date", "Win"], rows=rows,
        buttons=[{"label": "Add a win", "say": "Add to my brag file: "}]))


def _cv_skills(settings: Settings) -> str:
    return str(forms.cv_load(settings).get("skills", "")).lower()


def _skills_card(role: str, entry: dict) -> screen.Shown:
    skills = entry["skills"]
    have = [s for s, ok in skills.items() if ok]
    gaps = [s for s, ok in skills.items() if not ok]
    rows = [[s, "have" if ok else "gap"] for s, ok in skills.items()]
    said = f"For {role} you have {len(have)} of {len(skills)} skills." + (f" Gaps: {', '.join(gaps)}." if gaps else " No gaps!")
    return screen.Shown(said, screen.card(
        "table", f"Skills gap: {role}", f"career-skills-{role}", columns=["Skill", "Status"], rows=rows,
        buttons=[{"label": f"Learn {g}"[:40], "say": f"Help me learn {g}."} for g in gaps[:3]]))


def skills_gap(settings: Settings, args: dict) -> screen.Shown:
    role = cs.need(args.get("role"), "target role")
    wanted = [cs.clean(s, 60) for s in (args.get("skills") or []) if cs.clean(s, 60)][:40]
    if not wanted:
        raise ValueError("Which skills does that role need?")
    mine = {cs.clean(s, 60).lower() for s in (args.get("have") or [])}
    cv = _cv_skills(settings)
    found = cs.load(settings, cs.SKILLS, {})
    entry = found.setdefault(role, {"skills": {}})
    for s in wanted:
        entry["skills"][s] = s.lower() in mine or (s.lower() in cv)
    cs.save(settings, cs.SKILLS, found)
    return _skills_card(role, entry)


def skills_show(settings: Settings, args: dict) -> screen.Shown | str:
    found = {k: v for k, v in cs.load(settings, cs.SKILLS, {}).items() if isinstance(v, dict) and v.get("skills")}
    if not found:
        return "No target role saved yet. Tell me a role and the skills it needs."
    role = cs.find(found, args.get("role") or "") or (list(found)[-1] if not args.get("role") else None)
    if role is None:
        raise ValueError(f"I have skills lists for {', '.join(found)}.")
    return _skills_card(role, found[role])


def skills_tick(settings: Settings, args: dict) -> screen.Shown:
    found = cs.load(settings, cs.SKILLS, {})
    role = cs.find(found, args.get("role") or "") or (list(found)[-1] if found and not args.get("role") else None)
    if role is None:
        raise ValueError("Which target role?")
    skill = cs.find(found[role]["skills"], cs.need(args.get("skill"), "skill"))
    if skill is None:
        raise ValueError(f"{role} doesn't list that skill.")
    found[role]["skills"][skill] = True
    cs.save(settings, cs.SKILLS, found)
    return _skills_card(role, found[role])


def tool_definitions() -> list[dict]:
    listed = {"type": "array", "items": {"type": "string"}}
    return [{
        "name": "career_documents",
        "description": "Career paperwork. Actions: cover_template (save a cover letter template in text, with "
                       "placeholders " + PLACEHOLDERS + "); cover_letter (write a cover letter for a company and "
                       "role from the template and the user's CV sections, saved in Documents/Letters); brag_add "
                       "(save a work win in text) and brag_show (the brag file, optional query); skills_gap (for a "
                       "target role give the skills it needs, and 'have' for the ones the user has; the CV skills are "
                       "checked too); skills_show (the gap list); skills_tick (a skill is now learned).",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "company": {"type": "string"},
                "role": {"type": "string"},
                "text": {"type": "string", "description": "Template text, or the win to save."},
                "date": {"type": "string", "description": "brag_add: YYYY-MM-DD, default today."},
                "query": {"type": "string"},
                "skills": listed,
                "have": listed,
                "skill": {"type": "string"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"career_documents"}


def run_tool(name: str, args: dict, settings: Settings, http=None):
    action = args.get("action")
    if action == "cover_template":
        return cover_template(settings, args)
    if action == "cover_letter":
        return cover_letter(settings, args)
    if action == "brag_add":
        return brag_add(settings, args)
    if action == "brag_show":
        return brag_show(settings, args)
    if action == "skills_gap":
        return skills_gap(settings, args)
    if action == "skills_show":
        return skills_show(settings, args)
    if action == "skills_tick":
        return skills_tick(settings, args)
    raise ValueError(f"Try one of: {', '.join(ACTIONS)}.")
