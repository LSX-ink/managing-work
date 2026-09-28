"""Debates and brainstorms. Debate practice on one of 40 motions: Alfred takes the other side, records each
argument by round and pops up a summary (modes-debates.json). Brainstorm mode saves ideas to a board with star and
remove buttons (modes-ideas.json) and exports it as a Markdown note in Ideas.
"""

import random

import homestore as hs
import memory
import modes
import screen
from config import Settings
from modes_data import MOTIONS

screen.EXTRA_KINDS.update({"modes-debate", "modes-board"})

DEBATES = "modes-debates.json"
IDEAS = "modes-ideas.json"
KEEP_DEBATES = 50
MAX_IDEAS = 150
SIDES = ("for", "against")


# ---- debate -----------------------------------------------------------------------------------------

def debate_motions() -> screen.Shown:
    items = [{"label": f"{i}. {m}", "say": f"Let's debate motion {i}."} for i, m in enumerate(MOTIONS, 1)]
    return screen.Shown(f"{len(MOTIONS)} motions are on the screen; pick one and a side.",
                        screen.card("list", "Debate motions", "modes-motions", items=items))


def _motion(motion) -> str:
    text = hs.clean(motion, 200)
    digits = text.lower().removeprefix("motion").strip().rstrip(".")
    if digits.isdigit():
        if not 1 <= int(digits) <= len(MOTIONS):
            raise ValueError(f"Pick a motion from 1 to {len(MOTIONS)}.")
        return MOTIONS[int(digits) - 1]
    if not text:
        return random.choice(MOTIONS)
    match = [m for m in MOTIONS if text.lower() in m.lower()]
    return match[0] if len(match) == 1 else text


def _load(settings: Settings) -> list:
    return [d for d in hs.load(settings, DEBATES, []) if isinstance(d, dict)]


def debate_start(settings: Settings, motion=None, side=None) -> screen.Shown:
    motion = _motion(motion)
    side = hs.clean(side, 10).lower() or "for"
    if side not in SIDES:
        raise ValueError("Pick a side: for or against.")
    other = SIDES[1 - SIDES.index(side)]
    debates = _load(settings)
    debate = {"started": modes.stamp(), "motion": motion, "side": side, "rounds": [[]]}
    hs.save(settings, DEBATES, (debates + [debate])[-KEEP_DEBATES:])
    return modes.enter(
        settings, "debate", "Debate partner", f"{motion} - you argue {side}",
        f"Debate the motion '{motion}'. The user argues {side}, you argue {other}. Let them open. Each round: they "
        "make their case, you rebut it and add one new argument, briefly. Record every argument, theirs and yours, "
        "in a few words with debate_and_ideas debate_point (by user or alfred, point); call debate_next_round when "
        "a round is done. After three rounds, or when they want to finish, call debate_summary and give a fair "
        "verdict on who argued better and why.",
        data={"started": debate["started"]}, card=_summary_card(debate))


def _current(settings: Settings, need_open: bool = True) -> tuple[list, dict]:
    debates = _load(settings)
    running = modes.session(settings, "debate")
    if running:
        found = next((d for d in reversed(debates) if d.get("started") == running.get("started")), None)
        if found:
            return debates, found
    if need_open or not debates:
        raise ValueError("No debate is running. Say 'let's debate' to start one.")
    return debates, debates[-1]


def debate_point(settings: Settings, by, point) -> str:
    by = "alfred" if hs.clean(by).lower() in ("alfred", "you", "assistant", "jarvis") else "user"
    debates, debate = _current(settings)
    debate["rounds"][-1].append({"by": by, "point": hs.need(point, "argument", 300)})
    hs.save(settings, DEBATES, debates)
    return f"Noted for round {len(debate['rounds'])}."


def debate_next_round(settings: Settings) -> str:
    debates, debate = _current(settings)
    if not debate["rounds"][-1]:
        return f"Round {len(debate['rounds'])} has no arguments yet."
    debate["rounds"].append([])
    hs.save(settings, DEBATES, debates)
    return f"Round {len(debate['rounds'])} begins. Invite the user to make their next point."


def _summary_card(debate: dict) -> dict:
    other = SIDES[1 - SIDES.index(debate["side"])]
    rounds = [{"user": [p["point"] for p in r if p["by"] == "user"],
               "alfred": [p["point"] for p in r if p["by"] == "alfred"]} for r in debate["rounds"] if r]
    return screen.card("modes-debate", "Debate", "modes-debate",
                       buttons=[{"label": "Next round", "say": "Next round of the debate."},
                                {"label": "Finish", "say": "Finish the debate and give your verdict."}],
                       data={"motion": debate["motion"], "user_side": debate["side"], "alfred_side": other,
                             "rounds": rounds})


def debate_summary(settings: Settings) -> screen.Shown:
    _, debate = _current(settings, need_open=False)
    count = sum(len(r) for r in debate["rounds"])
    return screen.Shown(f"{hs.plural(count, 'argument')} over {hs.plural(len([r for r in debate['rounds'] if r]), 'round')} "
                        f"on '{debate['motion']}'. The summary is on the screen.", _summary_card(debate))


# ---- brainstorm board -------------------------------------------------------------------------------

def _ideas(settings: Settings) -> dict:
    found = hs.load(settings, IDEAS, {})
    boards = {k: [i for i in v if isinstance(i, dict)] for k, v in (found.get("boards") or {}).items() if isinstance(v, list)}
    return {"current": found.get("current") if found.get("current") in boards else "", "boards": boards}


def _board_card(topic: str, ideas: list) -> dict:
    return screen.card("modes-board", f"Brainstorm: {topic}", "modes-board",
                       buttons=[{"label": "Export to note", "say": "Export my brainstorm ideas to a note."}],
                       data={"topic": topic, "ideas": [
                           {"n": n, "text": i["text"], "star": bool(i.get("star")),
                            "star_say": f"{'Unstar' if i.get('star') else 'Star'} idea {n} on the brainstorm board.",
                            "remove_say": f"Remove idea {n} from the brainstorm board."}
                           for n, i in enumerate(ideas, 1)]})


def brainstorm_start(settings: Settings, topic=None) -> screen.Shown:
    topic = hs.clean(topic, 80) or "Open brainstorm"
    data = _ideas(settings)
    topic = hs.find(data["boards"], topic) or topic
    data["boards"].setdefault(topic, [])
    data["current"] = topic
    hs.save(settings, IDEAS, data)
    return modes.enter(
        settings, "brainstorm", "Brainstorm", topic,
        f"Brainstorm '{topic}' with the user. Build on their ideas and offer bold ones of your own, one or two at a "
        "time; no judging yet. Save every idea worth keeping (theirs and yours) in a few words with "
        "debate_and_ideas idea_add.", card=_board_card(topic, data["boards"][topic]))


def _board(settings: Settings, topic=None) -> tuple[dict, str]:
    data = _ideas(settings)
    key = hs.find(data["boards"], topic) if hs.clean(topic) else data["current"]
    if not key:
        raise ValueError("There's no brainstorm board yet. Say 'let's brainstorm' and a topic.")
    return data, key


def idea_add(settings: Settings, ideas, topic=None) -> screen.Shown:
    items = [hs.clean(i, 200) for i in (ideas if isinstance(ideas, list) else [ideas]) if hs.clean(i)]
    if not items:
        raise ValueError("Which idea?")
    data = _ideas(settings)
    key = (hs.find(data["boards"], topic) or hs.clean(topic, 80)) if hs.clean(topic) else data["current"] or "Open brainstorm"
    board = data["boards"].setdefault(key, [])
    data["current"] = key
    have = {i["text"].lower() for i in board}
    for text in items:
        if text.lower() not in have and len(board) < MAX_IDEAS:
            have.add(text.lower())
            board.append({"text": text, "star": False, "at": modes.stamp()})
    hs.save(settings, IDEAS, data)
    return screen.Shown(f"Saved. {hs.plural(len(board), 'idea')} on the {key} board.", _board_card(key, board))


def idea_board(settings: Settings, topic=None) -> screen.Shown:
    data, key = _board(settings, topic)
    board = data["boards"][key]
    stars = sum(bool(i.get("star")) for i in board)
    return screen.Shown(f"{hs.plural(len(board), 'idea')} on the {key} board, {stars} starred.", _board_card(key, board))


def _pick(board: list, number) -> int:
    n = int(hs.number(number, "idea number", 1, max(1, len(board))))
    if n > len(board):
        raise ValueError("There's no idea with that number.")
    return n - 1


def idea_star(settings: Settings, number, star=None, topic=None) -> screen.Shown:
    data, key = _board(settings, topic)
    board = data["boards"][key]
    idea = board[_pick(board, number)]
    idea["star"] = (not idea.get("star")) if star is None else bool(star)
    hs.save(settings, IDEAS, data)
    return screen.Shown(f"{'Starred' if idea['star'] else 'Unstarred'} {idea['text']}.", _board_card(key, board))


def idea_remove(settings: Settings, number, topic=None) -> screen.Shown:
    data, key = _board(settings, topic)
    board = data["boards"][key]
    gone = board.pop(_pick(board, number))
    hs.save(settings, IDEAS, data)
    return screen.Shown(f"Removed {gone['text']}.", _board_card(key, board))


def idea_export(settings: Settings, title=None, topic=None) -> screen.Shown:
    data, key = _board(settings, topic)
    board = data["boards"][key]
    if not board:
        raise ValueError("That board has no ideas to export yet.")
    starred = [i["text"] for i in board if i.get("star")]
    lines = [f"# Brainstorm: {key}", "", f"_{hs.spoken(hs.today())}_", ""]
    if starred:
        lines += ["## Starred", *[f"- {t}" for t in starred], ""]
    lines += ["## All ideas", *[f"- {i['text']}" for i in board], ""]
    name = memory.safe_name(hs.clean(title, 50) or f"Brainstorm {key}"[:50], "note title")
    path = memory.unique_path(memory.folder(settings, "Ideas") / f"{name}.md")
    path.write_text("\n".join(lines), encoding="utf-8")
    return screen.Shown(f"Saved {hs.plural(len(board), 'idea')} to {path.name} in Ideas.", screen.file_card(settings, path))


# ---- tool -------------------------------------------------------------------------------------------

def tool_definitions() -> list[dict]:
    return [{
        "name": "debate_and_ideas",
        "description": "Debate practice: debate_motions lists 40 motions; debate_start (motion text or number, "
                       "side for/against the user takes; you argue the other side); debate_point (by user or "
                       "alfred, point) records each argument; debate_next_round; debate_summary pops up the "
                       "arguments. Brainstorm board: brainstorm_start (topic) starts brainstorm mode; idea_add "
                       "(ideas) saves ideas; idea_board shows them; idea_star / idea_remove (number); idea_export "
                       "(title) saves the board as a Markdown note in Ideas.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": [
                    "debate_motions", "debate_start", "debate_point", "debate_next_round", "debate_summary",
                    "brainstorm_start", "idea_add", "idea_board", "idea_star", "idea_remove", "idea_export"]},
                "motion": {"type": "string"},
                "side": {"type": "string", "enum": list(SIDES)},
                "by": {"type": "string", "enum": ["user", "alfred"]},
                "point": {"type": "string"},
                "topic": {"type": "string", "description": "Brainstorm topic (board)."},
                "ideas": {"type": "array", "items": {"type": "string"}},
                "number": {"type": "integer", "description": "Idea number on the board."},
                "star": {"type": "boolean", "description": "idea_star: false to unstar; leave out to toggle."},
                "title": {"type": "string"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"debate_and_ideas"}
modes.STARTERS["debate"] = lambda settings, topic: debate_start(settings, topic)
modes.STARTERS["brainstorm"] = brainstorm_start


def run_tool(name: str, args: dict, settings: Settings, http=None):
    action = args.get("action")
    if action == "debate_motions":
        return debate_motions()
    if action == "debate_start":
        return debate_start(settings, args.get("motion"), args.get("side"))
    if action == "debate_point":
        return debate_point(settings, args.get("by"), args.get("point"))
    if action == "debate_next_round":
        return debate_next_round(settings)
    if action == "debate_summary":
        return debate_summary(settings)
    if action == "brainstorm_start":
        return brainstorm_start(settings, args.get("topic"))
    if action == "idea_add":
        return idea_add(settings, args.get("ideas"), args.get("topic"))
    if action == "idea_board":
        return idea_board(settings, args.get("topic"))
    if action == "idea_star":
        return idea_star(settings, args.get("number"), args.get("star"), args.get("topic"))
    if action == "idea_remove":
        return idea_remove(settings, args.get("number"), args.get("topic"))
    if action == "idea_export":
        return idea_export(settings, args.get("title"), args.get("topic"))
    raise ValueError("Unknown debate or brainstorm action.")
