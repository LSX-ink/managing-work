"""DIY project steps and the tool inventory.

Projects (diy-projects.json) are a named list of steps you tick off; the pop-up shows progress and ticking a step
tells Alfred. Costs and materials for a project are kept by the household DIY projects ability, not here.
The tool inventory (diy-tools.json) lists what you own, where it lives, and who has borrowed it. Removing anything
needs confirmed true.
"""

import homestore as hs
import screen
from config import Settings
from diy_store import table

PROJECTS, TOOLS = "diy-projects.json", "diy-tools.json"
MAX_PROJECTS, MAX_STEPS, MAX_TOOLS = 40, 60, 300
ACTIONS = ("project_add", "step_done", "project_show", "project_list", "project_remove",
           "tool_add", "tool_lend", "tool_return", "tool_list", "tool_remove")


def _load(settings: Settings, name: str) -> dict:
    return {k: v for k, v in hs.load(settings, name, {}).items() if isinstance(v, dict)}


def _key(found: dict, label, what: str) -> str:
    k = hs.find(found, hs.need(label, what))
    if k is None:
        raise ValueError(f"I haven't got a {what} called {hs.clean(label)}.")
    return k


def _progress(p: dict) -> str:
    done = sum(1 for s in p["steps"] if s["done"])
    return f"{done} of {len(p['steps'])}"


# Projects

def project_add(settings: Settings, name, steps) -> str:
    found = _load(settings, PROJECTS)
    label = hs.need(name, "project", 50)
    k = hs.find(found, label) or label
    if k not in found and len(found) >= MAX_PROJECTS:
        raise ValueError("That's as many projects as I can keep; remove one first.")
    project = found.setdefault(k, {"steps": []})
    have = {s["text"].lower() for s in project["steps"]}
    new = [hs.clean(s, 120) for s in steps or [] if hs.clean(s)]
    new = [s for i, s in enumerate(new) if s.lower() not in have and s.lower() not in {x.lower() for x in new[:i]}]
    if len(project["steps"]) + len(new) > MAX_STEPS:
        raise ValueError("That project has too many steps already.")
    project["steps"] += [{"text": s, "done": False} for s in new]
    hs.save(settings, PROJECTS, found)
    return f"{k}: added {hs.plural(len(new), 'step')}, {len(project['steps'])} in all."


def _step_index(project: dict, step) -> int:
    text = hs.clean(step).lower()
    if text.isdigit() and 1 <= int(text) <= len(project["steps"]):
        return int(text) - 1
    hits = [i for i, s in enumerate(project["steps"]) if text and text in s["text"].lower()]
    if len(hits) == 1:
        return hits[0]
    raise ValueError("Which step? Give its number or some of its words." if not hits else "That matches more than one step; say its number.")


def step_done(settings: Settings, name, step, undo) -> screen.Shown | str:
    found = _load(settings, PROJECTS)
    k = _key(found, name, "project")
    project = found[k]
    i = _step_index(project, step)
    project["steps"][i]["done"] = not undo
    hs.save(settings, PROJECTS, found)
    text = f"{'Unticked' if undo else 'Ticked off'} step {i + 1}, {project['steps'][i]['text']}. {_progress(project)} done."
    if all(s["done"] for s in project["steps"]):
        return f"{text} That's the whole {k} project finished!"
    return text


def _card(k: str, project: dict) -> dict:
    items = [{"label": f"{i + 1}. {s['text']}", "done": s["done"],
              "say": f"Step {i + 1} of the {k} project is {'not done after all' if s['done'] else 'done'}."}
             for i, s in enumerate(project["steps"])]
    return screen.card("list", f"DIY project: {k} ({_progress(project)})", f"diy-project-{k.lower()}", items=items, checks=True,
                       buttons=[{"label": "All projects", "say": "Show my DIY projects and their progress."}])


def project_show(settings: Settings, name) -> screen.Shown:
    found = _load(settings, PROJECTS)
    k = _key(found, name, "project")
    project = found[k]
    if not project["steps"]:
        raise ValueError(f"The {k} project has no steps yet.")
    nxt = next((s["text"] for s in project["steps"] if not s["done"]), None)
    text = f"{k}: {_progress(project)} steps done." + (f" Next: {nxt}." if nxt else " All finished!")
    return screen.Shown(text, _card(k, project))


def project_list(settings: Settings) -> screen.Shown | str:
    found = _load(settings, PROJECTS)
    if not found:
        return "No DIY projects yet. Say a project name and its steps."
    rows = [[k, _progress(p), next((s["text"] for s in p["steps"] if not s["done"]), "Finished")] for k, p in sorted(found.items())]
    card = table("DIY projects", ["Project", "Steps done", "Next step"], rows, "diy-projects")
    return screen.Shown(f"You have {hs.plural(len(found), 'DIY project')} on the go.", card)


def project_remove(settings: Settings, name, confirmed) -> str:
    found = _load(settings, PROJECTS)
    k = _key(found, name, "project")
    if not confirmed:
        return f"Ask the user to confirm removing the {k} project, then call again with confirmed true."
    del found[k]
    hs.save(settings, PROJECTS, found)
    return f"Removed the {k} project."


# Tools

def tool_add(settings: Settings, tool, where) -> str:
    found = _load(settings, TOOLS)
    label = hs.need(tool, "tool", 50)
    k = hs.find(found, label) or label
    if k not in found and len(found) >= MAX_TOOLS:
        raise ValueError("That's as many tools as I can keep track of.")
    entry = found.get(k, {})
    entry["where"] = hs.clean(where, 60) or entry.get("where", "")
    found[k] = entry
    hs.save(settings, TOOLS, found)
    return f"Noted the {k}" + (f" in the {entry['where']}." if entry["where"] else ".")


def tool_lend(settings: Settings, tool, to) -> str:
    found = _load(settings, TOOLS)
    who = hs.need(to, "borrower", 40)
    label = hs.need(tool, "tool", 50)
    k = hs.find(found, label)
    if k is None:
        k = label
        found[k] = {"where": ""}
    if found[k].get("with") and found[k]["with"].lower() != who.lower():
        raise ValueError(f"The {k} is already out with {found[k]['with']}.")
    found[k]["with"], found[k]["since"] = who, hs.today().isoformat()
    hs.save(settings, TOOLS, found)
    return f"Noted that {who} has borrowed the {k}."


def tool_return(settings: Settings, tool) -> str:
    found = _load(settings, TOOLS)
    k = _key(found, tool, "tool")
    if not found[k].get("with"):
        return f"The {k} wasn't lent out."
    who = found[k].pop("with")
    found[k].pop("since", None)
    hs.save(settings, TOOLS, found)
    return f"The {k} is back from {who}."


def tool_list(settings: Settings, only_out) -> screen.Shown | str:
    found = _load(settings, TOOLS)
    if only_out:
        found = {k: v for k, v in found.items() if v.get("with")}
    if not found:
        return "Nothing is lent out." if only_out else "No tools saved yet. Say what you own and where you keep it."
    today = hs.today()
    rows = []
    for k, v in sorted(found.items()):
        days = ""
        if v.get("since"):
            try:
                days = f"{(today - hs.parse_day(v['since'])).days} days"
            except ValueError:
                pass
        rows.append([k, v.get("where") or "", v.get("with") or "In", days])
    title = "Tools lent out" if only_out else "Tool inventory"
    card = table(title, ["Tool", "Kept in", "Borrowed by", "Out for"], rows, "diy-tools",
                 buttons=[{"label": "Who has what", "say": "Which of my tools are lent out?"}])
    out = sum(1 for v in found.values() if v.get("with"))
    return screen.Shown(f"{hs.plural(len(found), 'tool')} listed, {out} lent out." if not only_out else
                        "Lent out: " + ", ".join(f"{k} with {v['with']}" for k, v in sorted(found.items())) + ".", card)


def tool_remove(settings: Settings, tool, confirmed) -> str:
    found = _load(settings, TOOLS)
    k = _key(found, tool, "tool")
    if not confirmed:
        return f"Ask the user to confirm removing the {k} from the tool inventory, then call again with confirmed true."
    del found[k]
    hs.save(settings, TOOLS, found)
    return f"Removed the {k} from your tools."


def tool_definitions() -> list[dict]:
    text = {"type": "string"}
    return [{
        "name": "diy_projects",
        "description": "DIY project steps and tool inventory. action: 'project_add' a project with steps (adds steps "
                       "to an existing one); 'step_done' tick a step by number or words (undo true to untick); "
                       "'project_show' the step tick-list with progress; 'project_list'; 'project_remove'; 'tool_add' "
                       "a tool you own and where it is kept; 'tool_lend' who borrowed a tool; 'tool_return'; "
                       "'tool_list' the inventory (only_out true for what is lent out); 'tool_remove'. For removing, "
                       "set confirmed true only after the user confirms. Materials and costs are the household DIY ability.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": list(ACTIONS)},
                "project": text,
                "steps": {"type": "array", "items": text},
                "step": {**text, "description": "Step number or some of its words."},
                "undo": {"type": "boolean"},
                "tool": text,
                "where": {**text, "description": "Where the tool is kept."},
                "to": {**text, "description": "Who borrowed it."},
                "only_out": {"type": "boolean"},
                "confirmed": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"diy_projects"}


def run_tool(name: str, args: dict, settings: Settings, http=None):
    a = args.get
    actions = {
        "project_add": lambda: project_add(settings, a("project"), a("steps")),
        "step_done": lambda: step_done(settings, a("project"), a("step"), a("undo")),
        "project_show": lambda: project_show(settings, a("project")),
        "project_list": lambda: project_list(settings),
        "project_remove": lambda: project_remove(settings, a("project"), a("confirmed")),
        "tool_add": lambda: tool_add(settings, a("tool"), a("where")),
        "tool_lend": lambda: tool_lend(settings, a("tool"), a("to")),
        "tool_return": lambda: tool_return(settings, a("tool")),
        "tool_list": lambda: tool_list(settings, a("only_out")),
        "tool_remove": lambda: tool_remove(settings, a("tool"), a("confirmed")),
    }
    if a("action") not in actions:
        raise ValueError(f"I can't do {a('action')} with DIY projects.")
    return actions[a("action")]()
