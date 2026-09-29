"""Creator ideas, part 2: the hook library (about 60 built-in templates), the fill-in helper, the hook scorer, saved
hooks, the call-to-action library, the on-screen text and safe-zone checker and the risky-words checklist.

All offline and general guidance: platform rules change, so the risky-words checks tell the user to read the current
community guidelines and monetisation rules. New pop-up kind: "creator-safe" (a phone frame with the safe zones and
the text placed in it), drawn by popup-creatorideas.js.
"""

import random
import re

import homestore as hs
import screen
import creator_data as data
import creator_store as store
from config import Settings

screen.EXTRA_KINDS.add("creator-safe")
ACTIONS = ["hook_list", "hook_fill", "hook_score", "hook_save", "hook_saved", "cta_list", "cta_add", "text_check",
           "risky_list", "risky_check"]
GUIDELINES_NOTE = "This is general guidance only: check the platform's current community guidelines and monetisation rules."


def _kind(value) -> str:
    text = hs.clean(value).lower()
    if not text:
        return ""
    found = next((k for k in data.HOOKS if text in k.lower() or k.lower() in text), None)
    if found is None:
        raise ValueError(f"Hook types are: {', '.join(data.HOOKS)}.")
    return found


def hook_list(settings: Settings, args: dict) -> screen.Shown:
    kind = _kind(args.get("hook_type"))
    kinds = [kind] if kind else list(data.HOOKS)
    rows = [[k, t] for k in kinds for t in data.HOOKS[k]]
    total = sum(len(data.HOOKS[k]) for k in data.HOOKS)
    return screen.Shown(f"{len(rows)} hook templates" + ("" if kind else f" across {len(kinds)} types") +
                        f" out of {total}. Say fill one in with your topic.",
                        screen.card("table", f"Hooks: {kind or 'all types'}", "creator-hooks",
                                    columns=["Type", "Template"], rows=rows))


def _fill(template: str, args: dict, year: int) -> str:
    values = {"topic": hs.clean(args.get("topic"), 80), "number": hs.clean(args.get("number"), 10),
              "thing": hs.clean(args.get("thing"), 40), "year": str(year)}
    return re.sub(r"\{(\w+)\}", lambda m: values.get(m.group(1)) or f"[{m.group(1)}]", template)


def hook_fill(settings: Settings, args: dict, when) -> screen.Shown:
    topic = hs.need(args.get("topic"), "topic")
    template = hs.clean(args.get("template"), 200)
    if template:
        picks = [template]
    else:
        pool = data.HOOKS[_kind(args.get("hook_type"))] if args.get("hook_type") else \
            [t for group in data.HOOKS.values() for t in group]
        picks = random.sample(pool, min(5, len(pool)))
    lines = [_fill(t, {**args, "topic": topic}, when.year) for t in picks]
    blanks = any("[" in line for line in lines)
    note = " Some blanks are left in [brackets]; give me a number or thing to fill them." if blanks else ""
    return screen.Shown(f"Here are {len(lines)} hooks for {topic}.{note}",
                        screen.card("list", f"Hooks for {topic}", "creator-hookfill",
                                    items=[{"label": line, "say": f"Score this hook: {line}"} for line in lines]))


# ---- Scorer --------------------------------------------------------------------------------------

def _score_checks(text: str) -> list[list]:
    """Rows of [check, result, points out of, tip]."""
    tokens = re.findall(r"[\w']+", text.lower())
    count = len(tokens)
    seconds = round(count / 3, 1)
    length = 30 if 6 <= count <= 12 else 15 if 4 <= count <= 16 else 0
    curious = [w for w in tokens if w in data.CURIOSITY]
    curiosity = 30 if len(curious) >= 2 else 20 if curious else 0
    opener = tokens[:3]
    weak = [w for w in opener if w in data.WEAK_OPENERS][:1] if opener and opener[0] in data.WEAK_OPENERS else []
    specific = bool(re.search(r"\d", text) or "?" in text or "you" in tokens)
    return [
        ["Length", f"{count} words", length,
         "Aim for 6 to 12 words." if length < 30 else "Just right for a quick read."],
        ["Curiosity words", ", ".join(curious) or "none", curiosity,
         "Add a curiosity word such as secret, never or why." if curiosity < 30 else "Good pull."],
        ["First 3 words", " ".join(opener) or "none", 0 if weak else 20,
         f"Don't open with '{weak[0]}'; start with the interesting part." if weak else "Starts strong."],
        ["Specific", "yes" if specific else "no", 20 if specific else 0,
         "Add a number, a question or the word 'you'." if not specific else "Speaks to the viewer."],
        ["Reading time", f"{seconds} seconds", "-",
         "Under 3 seconds is best for the first line." if seconds > 3 else "Fits in the opening seconds."],
    ]


def hook_score(settings: Settings, args: dict) -> screen.Shown:
    text = hs.need(args.get("text"), "hook", 300)
    rows = _score_checks(text)
    total = sum(r[2] for r in rows if isinstance(r[2], int))
    tip = next((r[3] for r, best in zip(rows, (30, 30, 20, 20)) if r[2] < best), "Nothing to fix.")
    return screen.Shown(f"That hook scores {total} out of 100. {tip}",
                        screen.card("table", f"Hook score: {total}/100", "creator-score",
                                    columns=["Check", "Result", "Points", "Tip"],
                                    rows=[[c, r, str(p), t] for c, r, p, t in rows]))


def hook_save(settings: Settings, args: dict) -> str:
    text = hs.need(args.get("text"), "hook", 300)
    saved = store.load(settings)
    if text.lower() not in [h.lower() for h in saved["hooks"]]:
        store.put(saved["hooks"], text, 100)
    store.save(settings, saved)
    return f"Saved that hook. You have {len(saved['hooks'])} saved."


def hook_saved(settings: Settings, args: dict) -> screen.Shown | str:
    hooks = store.load(settings)["hooks"]
    if not hooks:
        return "You haven't saved any hooks yet."
    return screen.Shown(f"You have {len(hooks)} saved hooks.",
                        screen.card("list", "Saved hooks", "creator-savedhooks",
                                    items=[{"label": h, "say": f"Score this hook: {h}"} for h in hooks[-40:]]))


# ---- CTAs ----------------------------------------------------------------------------------------

def cta_list(settings: Settings, args: dict) -> screen.Shown:
    goal = hs.clean(args.get("goal")).lower()
    if goal and goal not in data.CTAS:
        raise ValueError(f"Goals are: {', '.join(data.CTAS)}.")
    mine = store.load(settings)["ctas"]
    rows = [[g, c] for g, cs in data.CTAS.items() if not goal or g == goal for c in cs]
    rows += [[m["goal"] + " (yours)", m["text"]] for m in mine if not goal or m["goal"] == goal]
    return screen.Shown(f"{len(rows)} calls to action" + (f" for {goal}." if goal else "."),
                        screen.card("table", "Calls to action", "creator-ctas", columns=["Goal", "Line"], rows=rows))


def cta_add(settings: Settings, args: dict) -> str:
    goal = hs.clean(args.get("goal"), 20).lower() or "follow"
    if goal not in data.CTAS:
        raise ValueError(f"Goals are: {', '.join(data.CTAS)}.")
    saved = store.load(settings)
    store.put(saved["ctas"], {"goal": goal, "text": hs.need(args.get("text"), "line", 150)}, 60)
    store.save(settings, saved)
    return f"Added your own {goal} line."


# ---- Text length and safe zones ------------------------------------------------------------------

LIMITS = {"onscreen": (40, 3, "on-screen text"), "title": (70, 1, "title or cover text"),
          "caption": (150, 2, "the visible start of a caption")}


def text_check(settings: Settings, args: dict) -> screen.Shown:
    kind = hs.clean(args.get("kind")).lower() or "onscreen"
    if kind not in LIMITS:
        raise ValueError(f"Kind can be {', '.join(LIMITS)}.")
    per_line, max_lines, label = LIMITS[kind]
    lines = [hs.clean(x, 300) for x in re.split(r"[\n|]", str(args.get("text") or "")) if x.strip()]
    if not lines:
        raise ValueError("What text should I check?")
    issues = [f"Line {n} is {len(x)} characters; keep it under {per_line}." for n, x in enumerate(lines, 1)
              if len(x) > per_line]
    if len(lines) > max_lines:
        issues.append(f"{len(lines)} lines is a lot; {max_lines} is the most that reads easily.")
    words = sum(store.words(x) for x in lines)
    seconds = max(2, round(words / 3 + 0.5))
    issues.append(f"Leave it on screen for about {seconds} seconds so it can be read.")
    spoken = "That fits." if len(issues) == 1 else f"{len(issues) - 1} problem{'s' if len(issues) > 2 else ''} to fix."
    return screen.Shown(f"Checking {label}: {spoken} Keep it out of the shaded edges.",
                        screen.card("creator-safe", "Text and safe zones", "creator-safe",
                                    data={"lines": lines, "zones": data.SAFE_ZONE, "issues": issues,
                                          "per_line": per_line}))


# ---- Risky words ---------------------------------------------------------------------------------

def risky_list(settings: Settings, args: dict) -> screen.Shown:
    rows = [[k, ", ".join(w[:4]), advice] for k, (w, advice) in data.RISKY.items()]
    return screen.Shown(f"{len(rows)} areas to watch for monetised content. {GUIDELINES_NOTE}",
                        screen.card("table", "Risky words checklist", "creator-risky",
                                    columns=["Area", "Example words", "Safer approach"], rows=rows))


def risky_check(settings: Settings, args: dict) -> screen.Shown | str:
    text = hs.need(args.get("text"), "script or caption", 6000).lower()
    hits = [[area, word, advice] for area, (words, advice) in data.RISKY.items() for word in words
            if re.search(rf"(?<!\w){re.escape(word)}(?!\w)", text)]
    if not hits:
        return f"Nothing on my checklist stands out. {GUIDELINES_NOTE}"
    return screen.Shown(f"{len(hits)} word{'s' if len(hits) != 1 else ''} to think about. {GUIDELINES_NOTE}",
                        screen.card("table", "Words to check", "creator-riskcheck",
                                    columns=["Area", "Found", "Safer approach"], rows=hits))


def tool_definitions() -> list[dict]:
    return [{
        "name": "creator_hooks",
        "description": "Hooks, calls to action and text checks for short-form videos. action: hook_list (hook_type: "
                       "question / shock stat / story / POV / list / nobody talks about) = about 60 templates; "
                       "hook_fill (topic, hook_type or template, number, thing) = 'write hooks about X'; hook_score "
                       "(text) = length, curiosity words, first 3 words, reading time with tips; hook_save (text) / "
                       "hook_saved; cta_list (goal follow/comment/share/save/series) / cta_add (goal, text); "
                       "text_check (text, kind onscreen/title/caption) = length and TikTok safe zones pop-up; "
                       "risky_list / risky_check (text) = words that can limit reach or monetising (general "
                       "guidance only, tell the user to check the platform's current rules).",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "hook_type": {"type": "string"},
                "topic": {"type": "string"},
                "template": {"type": "string", "description": "hook_fill: a template with {topic} {number} {thing}."},
                "number": {"type": "string"},
                "thing": {"type": "string"},
                "text": {"type": "string", "description": "The hook, script, caption, CTA or on-screen text."},
                "goal": {"type": "string"},
                "kind": {"type": "string", "enum": list(LIMITS)},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"creator_hooks"}


def run_tool(name: str, args: dict, settings: Settings, http=None, now=None):
    action = args.get("action")
    if action == "hook_fill":
        return hook_fill(settings, args, store.now(now))
    found = {"hook_list": hook_list, "hook_score": hook_score, "hook_save": hook_save, "hook_saved": hook_saved,
             "cta_list": cta_list, "cta_add": cta_add, "text_check": text_check, "risky_list": risky_list,
             "risky_check": risky_check}.get(action)
    if found is None:
        raise ValueError("I can't do that one.")
    return found(settings, args)
