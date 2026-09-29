"""Turning niche research into a decision: positioning statement and angle ideas, a lean canvas, a one-page business plan saved as a
file, validation experiments, a smoke-test checklist, a go/no-go checklist with a saved verdict, a lessons journal and a next-step guide.

Data is in nicheresearch.json in the memory folder; files go in the "Niche research" folder. The smoke tests are ideas for you to do
yourself: nothing is built, posted or sent, and a test result is evidence, not a guarantee of sales.
"""

import nicheresearch_store as nr
import screen
from config import Settings

NAMES = {"nicheresearch_plan"}
CANVAS = {"problem": "Problem", "customers": "Customer segments", "value": "Unique value", "solution": "Solution", "channels": "Channels",
          "revenue": "Revenue streams", "costs": "Cost structure", "metrics": "Key metrics", "advantage": "Unfair advantage"}
POSITION = {"audience": "For", "problem": "who struggle with", "category": "the", "benefit": "that helps them", "alternative": "Unlike",
            "difference": "this one"}
DECISIONS = ["waiting", "keep", "change", "stop"]
SMOKE = [
    ("Describe the offer in one sentence and read it to 5 people", "Do they say 'tell me more' or just 'nice'?"),
    ("Sketch a one-page landing page on paper", "Headline, three benefits, one call to action. Do not build anything yet."),
    ("Ask 10 people in your audience what they do about the problem today", "Real spending and workarounds are the best sign."),
    ("Plan a waitlist: what would you ask, and what counts as a good sign-up number?", "Decide the number before you look."),
    ("Plan a pre-order or deposit test", "Only if you can deliver and refund. Someone willing to pay is stronger than someone willing to say yes."),
    ("Try the service by hand for one person (a 'concierge' test)", "Do it manually before automating anything."),
    ("Write the price you would charge and ask 5 people if it feels fair", "Listen for surprise, not politeness."),
    ("Set a stop rule: what result means you drop this idea?", "Writing it down now keeps you honest later."),
]
QUESTIONS = [
    "Have at least five real people said they have this problem?", "Has anyone paid, or tried to pay, for a fix?", "Can you reach the audience where they already are?",
    "Is there something different about your angle?", "Can you deliver it with the skills, time and money you have now?",
    "Do the numbers work at a realistic price and volume?", "Would you still enjoy this after six months?",
    "Have you run at least one test with real people?", "Can you afford to lose what you would spend on the first version?",
    "Is it honest, legal and something you are happy to put your name to?",
]
ANGLES = ["The {n} guide for {a}", "{n} in {c}, without {e}", "{n} for {a} who {p}", "What {a} get wrong about {n}", "{n} for people who hate {e}",
          "{n} the slow way: {o}", "A simple {n} plan for {a} with {c}", "{n}: {o}, no {e}"]
STEPS = [("rate", "Rate it 1-5 on the six measures", "Rate {n}: demand 4, competition 3, passion 5, skill 3, profit 3, evergreen 4"),
         ("persona", "Describe your ideal person", "Save a persona for {n}"),
         ("pains", "Bank three pain points", "Add a pain point to {n}"),
         ("competitors", "Note three competitors", "Add a competitor to {n}"),
         ("prices", "Log three prices you saw", "Log a price seen in {n}"),
         ("position", "Write a positioning statement", "Make a positioning statement for {n}"),
         ("experiment", "Run one validation experiment", "Add an experiment for {n}"),
         ("decision", "Save a go or no-go verdict", "Show the go no-go checklist for {n}")]


def _done(n: dict) -> dict:
    return {"rate": len(n["ratings"]) == len(nr.CRITERIA), "persona": bool(n["persona"]), "pains": len(n["pains"]) >= 3,
            "competitors": len(n["competitors"]) >= 3, "prices": len(n["prices"]) >= 3, "position": bool(n["positioning"].get("statement")),
            "experiment": any(e["decision"] != "waiting" or e["result"] for e in n["experiments"]), "decision": bool(n["decision"].get("verdict"))}


def next_step(settings: Settings, args: dict):
    d, row = nr.open_niche(settings, args)
    done = _done(row)
    todo = [k for k, _, _ in STEPS if not done[k]]
    rows = [(f"{i + 1}. {label}", "ok" if done[k] else "todo", "", say.format(n=row["name"])) for i, (k, label, say) in enumerate(STEPS)]
    head = f"{len(STEPS) - len(todo)} of {len(STEPS)} research steps done"
    spoken = f"Next for {row['name']}: {next(l for k, l, _ in STEPS if k == todo[0]).lower()}." if todo else f"Every research step for {row['name']} is done."
    return nr.check(spoken, f"Research progress: {row['name']}", head, rows, "Tap a step to start it.")


# ---- positioning ------------------------------------------------------------------------------------------------------

def positioning_make(settings: Settings, args: dict):
    d, row = nr.open_niche(settings, args)
    p = row["positioning"]
    for key in POSITION:
        if args.get(key):
            p[key] = nr.clean(args[key], 160)
    p.setdefault("audience", row["persona"].get("persona_name", ""))
    if not p.get("problem") and row["pains"]:
        p["problem"] = max(row["pains"], key=lambda x: x["intensity"] * x["frequency"])["text"]
    if not p.get("alternative") and row["competitors"]:
        p["alternative"] = row["competitors"][0]["name"]
    missing = [k for k in ("audience", "problem", "benefit") if not p.get(k)]
    if missing:
        raise ValueError(f"To write it I still need: {', '.join(missing)}.")
    p["statement"] = (f"For {p['audience']} who struggle with {p['problem']}, {row['name']} is the {p.get('category') or 'simple answer'} "
                      f"that helps them {p['benefit']}."
                      + (f" Unlike {p['alternative']}, {p['difference']}." if p.get("alternative") and p.get("difference") else ""))
    if args.get("angle"):
        p["angle"] = nr.clean(args["angle"], 200)
    nr.save(settings, nr.FILE, d)
    return nr.sheet("Here is your positioning statement.", f"Positioning: {row['name']}", [
        ("Statement", [p["statement"]]), ("Unique angle", [p.get("angle") or "(none saved yet. Say 'give me angle ideas')"])],
        "Read it aloud to someone in your audience. If they don't nod, keep working on it.", headline=row["name"])


def angle_ideas(settings: Settings, args: dict):
    d, row = nr.open_niche(settings, args)
    vals = {"n": row["name"], "a": nr.clean(args.get("audience")) or row["persona"].get("persona_name") or "beginners",
            "c": nr.clean(args.get("constraint")) or "limited time", "e": nr.clean(args.get("enemy")) or "jargon",
            "p": nr.clean(args.get("problem")) or (row["pains"][0]["text"] if row["pains"] else "feel stuck"),
            "o": nr.clean(args.get("outcome")) or "small steps that stick"}
    out = [f.format(**vals) for f in ANGLES]
    return nr.tappable("Eight angle ideas from your answers. Tap one to save it.", "Unique angle ideas",
                       [(x, f"Save this as my unique angle for {row['name']}: {x}") for x in out])


# ---- lean canvas and plan ---------------------------------------------------------------------------------------------

def _canvas(row: dict) -> dict:
    c = dict(row["canvas"])
    if not c.get("problem") and row["pains"]:
        c["problem"] = "; ".join(p["text"] for p in sorted(row["pains"], key=lambda x: -x["intensity"] * x["frequency"])[:3])
    if not c.get("customers") and row["persona"]:
        c["customers"] = row["persona"].get("persona_name", "") + " " + row["persona"].get("job", "")
    if not c.get("value") and row["positioning"].get("statement"):
        c["value"] = row["positioning"]["statement"]
    return {k: nr.clean(c.get(k), 300) for k in CANVAS}


def canvas_set(settings: Settings, args: dict):
    d, row = nr.open_niche(settings, args)
    given = {k: nr.clean(args[k], 300) for k in CANVAS if args.get(k)}
    if not given:
        raise ValueError("Give at least one box: " + ", ".join(CANVAS) + ".")
    row["canvas"].update(given)
    nr.save(settings, nr.FILE, d)
    return f"Saved {len(given)} lean canvas boxes for {row['name']}."


def canvas_show(settings: Settings, args: dict):
    d, row = nr.open_niche(settings, args)
    c = _canvas(row)
    return nr.sheet(f"Lean canvas for {row['name']}: {sum(1 for v in c.values() if v)} of 9 boxes filled.", f"Lean canvas: {row['name']}",
                    [(label, [c[k] or (f"(empty) Say the {label.lower()}", f"Set the {label.lower()} for {row['name']}")]) for k, label in CANVAS.items()],
                    "Boxes for problem, customers and value fill themselves from your pain points, persona and positioning.",
                    [{"label": "Save as file", "say": f"Save the lean canvas for {row['name']} as a file"}])


def canvas_save_file(settings: Settings, args: dict):
    d, row = nr.open_niche(settings, args)
    c = _canvas(row)
    text = f"# Lean canvas: {row['name']}\n\n" + "\n\n".join(f"## {label}\n{c[k] or '(not filled in yet)'}" for k, label in CANVAS.items())
    path = nr.write_file(settings, f"Lean canvas {row['name']}.md", text + f"\n\nSaved {nr.today().isoformat()}. {nr.HONEST}\n")
    return screen.Shown(f"Saved the lean canvas as {path.name}.", screen.file_card(settings, path))


def _plan_text(d: dict, row: dict) -> str:
    w = nr.weights(d)
    score = nr.weighted(row, w)
    c = _canvas(row)
    lines = [f"# One-page plan: {row['name']}", f"_{nr.today().isoformat()}. {nr.HONEST}_", "",
             "## The idea", row["note"] or row["name"],
             "", "## Fit score", f"{score} out of 100 ({nr.band(score)})" if score is not None else "Not fully rated yet.",
             "", "## Who it is for", c["customers"] or "(to do)",
             "", "## The problem", c["problem"] or "(to do)",
             "", "## Positioning", row["positioning"].get("statement") or "(to do)",
             "", "## Competitors", *([f"- {x['name']}: {x['weaknesses'] or x['strengths'] or 'no notes'}" for x in row["competitors"]] or ["(none noted)"]),
             "", "## Prices seen", *([f"- {p['item']}: {nr.gbp(p['price'])}" for p in row["prices"][:8]] or ["(none logged)"]),
             "", "## How I will make money", c["revenue"] or "(to do)", "", "## Costs", c["costs"] or "(to do)",
             "", "## Tests so far", *([f"- {e['hypothesis']} -> {e['result'] or 'no result yet'} ({e['decision']})" for e in row["experiments"]] or ["(none)"]),
             "", "## Verdict", (f"{row['decision']['verdict']}: {row['decision'].get('reason', '')}" if row["decision"].get("verdict") else "(not decided)"),
             "", "## Next three steps"]
    left = [f"- {label}" for k, label, _ in STEPS if not _done(row)[k]][:3]
    return "\n".join(lines + (left or ["- Review the plan with someone you trust"]) + ["", "Any tax or legal points: this is general guidance, check GOV.UK.", ""])


def business_plan_file(settings: Settings, args: dict):
    d, row = nr.open_niche(settings, args)
    path = nr.write_file(settings, f"One-page plan {row['name']}.md", _plan_text(d, row))
    return screen.Shown(f"Saved a one-page plan as {path.name}.", screen.file_card(settings, path))


# ---- experiments ------------------------------------------------------------------------------------------------------

def _exp(row: dict, args: dict) -> dict:
    return nr.pick(row["experiments"], args.get("experiment"), "hypothesis", "experiment")


def experiment_add(settings: Settings, args: dict):
    d, row = nr.open_niche(settings, args)
    e = {"id": nr.next_id(row["experiments"]), "hypothesis": nr.need(args.get("hypothesis"), "hypothesis", 200), "test": nr.clean(args.get("test"), 200),
         "metric": nr.clean(args.get("metric"), 200), "result": "", "decision": "waiting", "date": nr.today().isoformat()}
    row["experiments"].append(e)
    nr.save(settings, nr.FILE, d)
    return f"Added experiment {e['id']}. " + ("" if e["metric"] else "Tip: decide what counts as success before you start.")


def experiment_update(settings: Settings, args: dict):
    d, row = nr.open_niche(settings, args)
    e = _exp(row, args)
    if args.get("decision"):
        word = nr.clean(args["decision"]).lower()
        if word not in DECISIONS:
            raise ValueError("The decision should be waiting, keep, change or stop.")
        e["decision"] = word
    for key, limit in (("result", 300), ("test", 200), ("metric", 200), ("hypothesis", 200)):
        if args.get(key) is not None:
            e[key] = nr.clean(args[key], limit)
    nr.save(settings, nr.FILE, d)
    return f"Experiment {e['id']}: {e['decision']}."


def experiment_remove(settings: Settings, args: dict):
    d, row = nr.open_niche(settings, args)
    e = _exp(row, args)
    ask = nr.confirm_first(args, f"experiment {e['id']}")
    if ask:
        return ask
    row["experiments"] = [x for x in row["experiments"] if x is not e]
    nr.save(settings, nr.FILE, d)
    return "Removed that experiment."


def experiment_list(settings: Settings, args: dict):
    d, row = nr.open_niche(settings, args)
    if not row["experiments"]:
        raise ValueError(f"No experiments for {row['name']} yet. Say a hypothesis to test.")
    names = {"waiting": "Waiting", "keep": "Keep going", "change": "Change it", "stop": "Stop"}
    cols = [(names[k], [(e["hypothesis"], f"Test: {e['test'] or '-'} | Success: {e['metric'] or '-'}" + (f" | Result: {e['result']}" if e["result"] else ""),
                         f"Update experiment {e['id']} for {row['name']}") for e in row["experiments"] if e["decision"] == k]) for k in DECISIONS]
    return nr.board(f"{len(row['experiments'])} experiments for {row['name']}.", f"Experiments: {row['name']}", cols, "Tap one to record its result.")


def experiment_template(settings: Settings, args: dict):
    return nr.sheet("A good experiment is small, cheap and has a success number.", "How to write an experiment", [
        ("Hypothesis", ["We believe [audience] will [do something] because [reason]."]),
        ("Test", ["The cheapest way to see it: ask 10 people, a paper landing page, a manual trial."]),
        ("Success metric", ["Pick a number first, for example 3 of 10 people ask how to buy."]),
        ("Result and decision", ["Write what happened, then choose: keep going, change it or stop."]),
        ("Example", ["We believe busy parents will join a waitlist for meal plans. Test: show a mock page to 20 parents. "
                     "Success: 4 say they would pay 5 pounds a month."])])


# ---- smoke tests ------------------------------------------------------------------------------------------------------

def smoke_checklist(settings: Settings, args: dict):
    d, row = nr.open_niche(settings, args)
    done = set(row["smoke"])
    rows = [(f"{i + 1}. {t}", "ok" if i in done else "todo", detail, f"Tick smoke test step {i + 1} for {row['name']}") for i, (t, detail) in enumerate(SMOKE)]
    return nr.check(f"{len(done)} of {len(SMOKE)} smoke test steps done for {row['name']}.", f"Smoke tests: {row['name']}", f"{len(done)} of {len(SMOKE)} done", rows,
                    "These are things for you to do. Alfred builds and posts nothing. Be open with people about what is real.")


def smoke_tick(settings: Settings, args: dict):
    d, row = nr.open_niche(settings, args)
    step = int(nr.number(args.get("step"), "step number", 1, len(SMOKE))) - 1
    row["smoke"] = [s for s in row["smoke"] if s != step] if step in row["smoke"] else row["smoke"] + [step]
    nr.save(settings, nr.FILE, d)
    return f"Step {step + 1} is now {'done' if step in row['smoke'] else 'not done'}."


# ---- go / no-go -------------------------------------------------------------------------------------------------------

def _answers(row: dict) -> dict:
    return row["decision"].setdefault("answers", {})


def decision_answer(settings: Settings, args: dict):
    d, row = nr.open_niche(settings, args)
    q = str(int(nr.number(args.get("question"), "question number", 1, len(QUESTIONS))))
    ans = nr.clean(args.get("answer")).lower()
    if ans not in ("yes", "no", "unsure"):
        raise ValueError("Answer yes, no or unsure.")
    _answers(row)[q] = ans
    nr.save(settings, nr.FILE, d)
    return f"Question {q}: {ans}."


def decision_checklist(settings: Settings, args: dict):
    d, row = nr.open_niche(settings, args)
    ans = _answers(row)
    marks = {"yes": "ok", "no": "fail", "unsure": "warn"}
    rows = [(f"{i + 1}. {q}", marks.get(ans.get(str(i + 1)), "todo"), ans.get(str(i + 1), ""), f"Answer go no-go question {i + 1} for {row['name']}")
            for i, q in enumerate(QUESTIONS)]
    yes = sum(1 for v in ans.values() if v == "yes")
    no = sum(1 for v in ans.values() if v == "no")
    hint = ("Answer every question honestly to get a suggestion." if len(ans) < len(QUESTIONS)
            else "Suggestion: go, with a small first step." if no == 0 and yes >= 8 else "Suggestion: not yet. Fix the noes or test more." if no >= 3 else "Suggestion: run one more small test.")
    return nr.check(hint, f"Go or no-go: {row['name']}", f"{yes} yes, {no} no, {len(ans) - yes - no} unsure", rows,
                    "A suggestion from your own answers. The decision is yours. Only risk money you can afford to lose.",
                    [{"label": "Save verdict", "say": f"Save my verdict for {row['name']}"}])


def verdict_save(settings: Settings, args: dict):
    d, row = nr.open_niche(settings, args)
    word = nr.clean(args.get("verdict")).lower()
    if word not in ("go", "no-go", "park", "pivot"):
        raise ValueError("The verdict should be go, no-go, park or pivot.")
    row["decision"].update({"verdict": word, "reason": nr.clean(args.get("reason"), 300), "date": nr.today().isoformat()})
    nr.save(settings, nr.FILE, d)
    return f"Saved the verdict for {row['name']}: {word}."


def verdict_show(settings: Settings, args: dict):
    d, row = nr.open_niche(settings, args)
    v = row["decision"]
    if not v.get("verdict"):
        raise ValueError(f"No verdict saved for {row['name']} yet.")
    return nr.sheet(f"{row['name']}: {v['verdict']}.", f"Verdict: {row['name']}", [
        ("Decision", [v["verdict"].upper()]), ("Why", [v.get("reason") or "(no reason written)"]), ("Date", [v.get("date", "")])],
        "You can change your mind when you learn more. Write the lesson in the journal.", headline=v["verdict"].upper())


# ---- journal ----------------------------------------------------------------------------------------------------------

def journal_add(settings: Settings, args: dict):
    d = nr.open_data(settings)
    name = ""
    if nr.clean(args.get("niche")):
        name = nr.niche(d, args)["name"]
    e = {"id": nr.next_id(d["journal"]), "niche": name, "lesson": nr.need(args.get("lesson"), "lesson", 400), "date": nr.today().isoformat()}
    d["journal"] = (d["journal"] + [e])[-nr.MAX_ROWS:]
    nr.save(settings, nr.FILE, d)
    return f"Saved lesson {e['id']} in your niche journal."


def journal_list(settings: Settings, args: dict):
    d = nr.open_data(settings)
    name = nr.niche(d, args)["name"] if nr.clean(args.get("niche")) else ""
    rows = [e for e in d["journal"] if not name or e["niche"] == name]
    if not rows:
        raise ValueError("No lessons in the niche journal yet.")
    return nr.tappable(f"{len(rows)} lessons.", "Niche journal", [(f"{e['id']}. {e['date']} {e['niche'] + ': ' if e['niche'] else ''}{e['lesson']}", "") for e in reversed(rows)])


def journal_remove(settings: Settings, args: dict):
    d = nr.open_data(settings)
    e = nr.pick(d["journal"], args.get("entry"), "lesson", "lesson")
    ask = nr.confirm_first(args, "that journal lesson")
    if ask:
        return ask
    d["journal"] = [x for x in d["journal"] if x is not e]
    nr.save(settings, nr.FILE, d)
    return "Removed that lesson."


ACTIONS = {"next_step": next_step, "positioning_make": positioning_make, "angle_ideas": angle_ideas, "canvas_set": canvas_set,
           "canvas_show": canvas_show, "canvas_save_file": canvas_save_file, "business_plan_file": business_plan_file,
           "experiment_add": experiment_add, "experiment_update": experiment_update, "experiment_list": experiment_list,
           "experiment_remove": experiment_remove, "experiment_template": experiment_template, "smoke_checklist": smoke_checklist,
           "smoke_tick": smoke_tick, "decision_answer": decision_answer, "decision_checklist": decision_checklist,
           "verdict_save": verdict_save, "verdict_show": verdict_show, "journal_add": journal_add, "journal_list": journal_list,
           "journal_remove": journal_remove}


def tool_definitions() -> list[dict]:
    props = {k: {"type": "string", "description": f"Lean canvas box: {v}."} for k, v in CANVAS.items() if k not in ("problem",)}
    return [{
        "name": "nicheresearch_plan",
        "description": "Turn niche research into a decision: positioning statement and unique angle ideas, lean canvas (also saved as a file), "
                       "one-page business plan file, validation experiments (hypothesis, test, success metric, result, decision), smoke-test "
                       "checklist (ideas only, nothing built or posted), go/no-go checklist and saved verdict, niche journal of lessons, "
                       "and a next-step guide. Set confirmed only after the user agrees to any remove action.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": list(ACTIONS)},
                "niche": {"type": "string", "description": "Niche number or name (optional when there is only one)."},
                "audience": {"type": "string"}, "problem": {"type": "string"}, "category": {"type": "string"}, "benefit": {"type": "string"},
                "alternative": {"type": "string", "description": "What people use instead."}, "difference": {"type": "string"},
                "angle": {"type": "string"}, "constraint": {"type": "string"}, "enemy": {"type": "string", "description": "What annoys people about how it is done now."},
                "outcome": {"type": "string"}, "experiment": {"type": "string", "description": "Experiment number or hypothesis text."},
                "hypothesis": {"type": "string"}, "test": {"type": "string"}, "metric": {"type": "string", "description": "Success metric."},
                "result": {"type": "string"}, "decision": {"type": "string", "enum": DECISIONS},
                "step": {"type": "number", "description": "Smoke test step number."}, "question": {"type": "number", "description": "Go/no-go question number."},
                "answer": {"type": "string", "enum": ["yes", "no", "unsure"]}, "verdict": {"type": "string", "enum": ["go", "no-go", "park", "pivot"]},
                "reason": {"type": "string"}, "lesson": {"type": "string"}, "entry": {"type": "string", "description": "Journal lesson number."},
                "confirmed": {"type": "boolean"}, **props,
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


def run_tool(name: str, args: dict, settings: Settings, http=None):
    return nr.dispatch(ACTIONS, settings, args)
