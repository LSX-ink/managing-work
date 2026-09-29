"""Party host: quiz night with teams. Rounds by category from a built-in bank of 150 questions (plus your own),
a big scoreboard pop-up, round results, tiebreakers, printable sheets and a buzzer screen.

The running quiz is kept in partyhost-quiz.json, your own questions in partyhost-questions.json and the questions
already asked in partyhost-seen.json (so a new night doesn't repeat them) in the memory folder.
"""

import random
from datetime import datetime

import homestore as hs
import partyhost_questions as bank
import screen
from config import Settings

screen.EXTRA_KINDS.update({"partyhost-scoreboard", "partyhost-question", "partyhost-buzzer"})

QUIZ, CUSTOM, SEEN = "partyhost-quiz.json", "partyhost-questions.json", "partyhost-seen.json"
RNG = random.Random()
MAX_TEAMS, MAX_ROUNDS, MAX_PER_ROUND, MAX_CUSTOM = 8, 10, 10, 300
ACTIONS = ("start", "categories", "question", "reveal", "award", "undo", "scoreboard", "round_results", "end",
           "add_question", "tiebreaker", "answer_sheet", "host_sheet", "buzzer")


def _custom(settings: Settings) -> list[dict]:
    return [c for c in hs.load(settings, CUSTOM, []) if isinstance(c, dict) and c.get("question")]


def _pool(settings: Settings) -> dict[str, list[tuple[str, str]]]:
    pool = {cat: list(qs) for cat, qs in bank.QUESTIONS.items()}
    for c in _custom(settings):
        pool.setdefault(c["category"], []).append((c["question"], c["answer"]))
    return pool


def _category(pool: dict, name: str) -> str:
    found = hs.find(pool, name)
    if not found:
        raise ValueError(f"I don't have a {hs.clean(name)} round. Ask me for the categories.")
    return found


def _draw(settings: Settings, pool: dict, category: str, count: int, seen: dict) -> list[dict]:
    used = set(seen.get(category, []))
    fresh = [q for q in pool[category] if q[0] not in used]
    if len(fresh) < count:
        used = set()
        fresh = list(pool[category])
    picked = RNG.sample(fresh, min(count, len(fresh)))
    seen[category] = sorted(used | {q[0] for q in picked})
    return [{"q": q, "a": a, "cat": category} for q, a in picked]


def _game(settings: Settings) -> dict:
    game = hs.load(settings, QUIZ, {})
    if not game.get("teams"):
        raise ValueError("There's no quiz on. Say 'start a quiz night' and give me the team names.")
    return game


def _team(game: dict, name) -> str:
    found = hs.find(game["teams"], hs.clean(name))
    if not found:
        raise ValueError(f"Which team? They are {', '.join(game['teams'])}.")
    return found


def _points(game: dict) -> dict[str, dict[int, int]]:
    out = {t: {} for t in game["teams"]}
    for rnd, team, pts in game["log"]:
        out[team][rnd] = out[team].get(rnd, 0) + pts
    return out


def _totals(game: dict) -> dict[str, int]:
    return {t: sum(r.values()) for t, r in _points(game).items()}


def _standings(game: dict) -> list[dict]:
    per, totals = _points(game), _totals(game)
    played = max(1, min(game["round"] + 1, len(game["rounds"])))
    order = sorted(game["teams"], key=lambda t: (-totals[t], game["teams"].index(t)))
    rows, rank = [], 0
    for i, team in enumerate(order):
        if i == 0 or totals[team] != totals[order[i - 1]]:
            rank = i + 1
        rows.append({"name": team, "total": totals[team], "rank": rank,
                     "rounds": [per[team].get(r, 0) for r in range(1, played + 1)]})
    return rows


def _scoreboard(game: dict, mode: str = "total", title: str = "Scoreboard", said: str = "") -> screen.Shown:
    rows = _standings(game)
    data = {"mode": mode, "rows": rows, "round": game["round"] + 1, "rounds": len(game["rounds"])}
    buttons = [{"label": "Next question", "say": "Quiz: next question."},
               {"label": "Round results", "say": "Quiz: show the round results."}]
    if mode == "final":
        buttons = [{"label": "Tiebreaker", "say": "Quiz: give us a tiebreaker."}] if _tied(rows) else []
    return screen.Shown(said or f"{rows[0]['name']} lead with {rows[0]['total']}.",
                        screen.card("partyhost-scoreboard", title, "partyhost-scoreboard", buttons=buttons, data=data))


def _tied(rows: list[dict]) -> bool:
    return len(rows) > 1 and rows[0]["rank"] == rows[1]["rank"]


def _question_card(game: dict, cur: dict, reveal: bool) -> screen.Shown:
    label = "Tiebreaker" if cur.get("tiebreak") else f"Round {cur['round']} of {len(game['rounds'])}"
    data = {"round": cur["round"], "label": label, "category": cur["cat"], "n": cur.get("n", 0),
            "total": cur.get("total", 0), "question": cur["q"], "answer": cur["a"] if reveal else "",
            "tiebreak": bool(cur.get("tiebreak"))}
    buttons = [{"label": "Reveal answer", "say": "Quiz: reveal the answer."}] if not reveal else [
        {"label": "Next question", "say": "Quiz: next question."}, {"label": "Scoreboard", "say": "Quiz: show the scoreboard."}]
    text = f"The answer is {cur['a']}." if reveal else f"{label}, {cur['cat']}. {cur['q']}"
    return screen.Shown(text, screen.card("partyhost-question", f"Quiz: {label}", "partyhost-question", buttons=buttons,
                                          data=data))


# ---- Actions ---------------------------------------------------------------------------------

def start(settings: Settings, a: dict) -> screen.Shown:
    old = hs.load(settings, QUIZ, {})
    if old.get("teams") and not old.get("ended") and old.get("log") and not a.get("confirmed"):
        raise ValueError("A quiz is already running with scores. Ask the user whether to start a fresh one, and set "
                         "confirmed to true only if they say yes.")
    names = [hs.clean(t, 30) for t in (a.get("teams") or []) if hs.clean(t, 30)]
    count = int(a.get("team_count") or 0)
    if not names and count:
        names = [f"Team {i + 1}" for i in range(count)]
    names = list(dict.fromkeys(names))
    if not 2 <= len(names) <= MAX_TEAMS:
        raise ValueError(f"A quiz needs 2 to {MAX_TEAMS} teams. Give me the team names.")
    rounds = min(MAX_ROUNDS, max(1, int(a.get("rounds") or 4)))
    per = min(MAX_PER_ROUND, max(1, int(a.get("per_round") or 5)))
    pool, seen = _pool(settings), hs.load(settings, SEEN, {})
    wanted = [_category(pool, c) for c in a.get("categories") or []]
    if not wanted:
        wanted = RNG.sample(list(pool), min(rounds, len(pool)))
    cats = [wanted[i % len(wanted)] for i in range(rounds)]
    plan = [{"category": c, "qs": _draw(settings, pool, c, per, seen)} for c in cats]
    hs.save(settings, SEEN, seen)
    game = {"teams": names, "rounds": plan, "round": 0, "q": -1, "current": None, "log": [], "ended": False,
            "started": datetime.now().isoformat(timespec="minutes")}
    hs.save(settings, QUIZ, game)
    text = (f"Quiz night is on with {len(names)} teams and {rounds} rounds of {per}: "
            f"{', '.join(dict.fromkeys(cats))}. Say 'next question' when you're ready.")
    view = _scoreboard(game, title="Quiz night")
    return screen.Shown(text, view.card)


def question(settings: Settings) -> screen.Shown:
    game = _game(settings)
    rnd = game["rounds"][game["round"]]
    if game["q"] + 1 >= len(rnd["qs"]):
        if game["round"] + 1 >= len(game["rounds"]):
            return _scoreboard(game, "total", "Scoreboard", "That was the last question. Say 'final scores' to finish.")
        game["round"], game["q"] = game["round"] + 1, -1
        rnd = game["rounds"][game["round"]]
    game["q"] += 1
    item = rnd["qs"][game["q"]]
    game["current"] = {**item, "round": game["round"] + 1, "n": game["q"] + 1, "total": len(rnd["qs"])}
    hs.save(settings, QUIZ, game)
    return _question_card(game, game["current"], False)


def reveal(settings: Settings) -> screen.Shown:
    game = _game(settings)
    if not game.get("current"):
        raise ValueError("No question is up yet. Say 'next question'.")
    return _question_card(game, game["current"], True)


def award(settings: Settings, a: dict) -> screen.Shown:
    game = _game(settings)
    team = _team(game, a.get("team"))
    pts = a.get("points")
    pts = 1 if pts is None else int(pts)
    if not -20 <= pts <= 50 or pts == 0:
        raise ValueError("Give between -20 and 50 points.")
    game["log"].append([game["round"] + 1, team, pts])
    hs.save(settings, QUIZ, game)
    total = _totals(game)[team]
    word = f"{pts} point{'s' if abs(pts) != 1 else ''}"
    return _scoreboard(game, "total", "Scoreboard", f"{word} to {team}. That makes {total}.")


def undo(settings: Settings) -> screen.Shown:
    game = _game(settings)
    if not game["log"]:
        raise ValueError("There are no points to take back.")
    _, team, pts = game["log"].pop()
    hs.save(settings, QUIZ, game)
    return _scoreboard(game, "total", "Scoreboard", f"Taken back {pts} from {team}.")


def round_results(settings: Settings, a: dict) -> screen.Shown:
    game = _game(settings)
    number = int(a.get("round") or game["round"] + 1)
    if not 1 <= number <= len(game["rounds"]):
        raise ValueError(f"There are {len(game['rounds'])} rounds.")
    per = _points(game)
    rows = sorted(game["teams"], key=lambda t: -per[t].get(number, 0))
    cat = game["rounds"][number - 1]["category"]
    data = {"mode": "round", "round": number, "rounds": len(game["rounds"]), "category": cat, "rows": [
        {"name": t, "total": _totals(game)[t], "rank": 0, "rounds": [per[t].get(number, 0)]} for t in rows]}
    for i, row in enumerate(data["rows"]):
        row["rank"] = 1 + sum(1 for r in data["rows"] if r["rounds"][0] > row["rounds"][0])
    best = data["rows"][0]
    return screen.Shown(f"Round {number}, {cat}: {best['name']} won it with {best['rounds'][0]}.", screen.card(
        "partyhost-scoreboard", f"Round {number} results", "partyhost-scoreboard", data=data,
        buttons=[{"label": "Scoreboard", "say": "Quiz: show the scoreboard."}]))


def end(settings: Settings) -> screen.Shown:
    game = _game(settings)
    game["ended"] = True
    hs.save(settings, QUIZ, game)
    rows = _standings(game)
    game_ = dict(game, round=len(game["rounds"]) - 1)
    if _tied(rows):
        tied = [r["name"] for r in rows if r["rank"] == 1]
        text = f"It's a tie between {' and '.join(tied)} on {rows[0]['total']}. Time for a tiebreaker?"
    else:
        text = f"{rows[0]['name']} win with {rows[0]['total']} points. Well played, everyone."
    view = _scoreboard(game_, "final", "Final scores", text)
    return screen.Shown(text, view.card)


def categories(settings: Settings) -> screen.Shown:
    pool = _pool(settings)
    rows = [[c, len(qs)] for c, qs in pool.items()]
    card = screen.card("table", "Quiz categories", columns=["Category", "Questions"], rows=rows,
                       buttons=[{"label": "Start a quiz", "say": "Start a quiz night."}])
    return screen.Shown(f"There are {len(rows)} categories and {sum(r[1] for r in rows)} questions.", card)


def add_question(settings: Settings, a: dict) -> str:
    q, ans = hs.need(a.get("question"), "question", 250), hs.need(a.get("answer"), "answer", 120)
    cat = hs.clean(a.get("category"), 40) or "My questions"
    found = hs.find(bank.QUESTIONS, cat)
    items = _custom(settings)
    if len(items) >= MAX_CUSTOM:
        raise ValueError("That's the most own questions I can keep.")
    items.append({"category": found or cat, "question": q, "answer": ans})
    hs.save(settings, CUSTOM, items)
    return f"Added your question to {found or cat}."


def tiebreaker(settings: Settings) -> screen.Shown:
    game = _game(settings)
    q, ans = RNG.choice(bank.TIEBREAKERS)
    cur = {"q": q + "  (closest number wins)", "a": str(ans), "cat": "Tiebreaker", "round": 0, "tiebreak": True}
    game["current"] = cur
    hs.save(settings, QUIZ, game)
    return _question_card(game, cur, False)


def answer_sheet(settings: Settings) -> screen.Shown:
    game = _game(settings)
    rows = [[f"Round {r + 1}: {rnd['category']}", n + 1, ""] for r, rnd in enumerate(game["rounds"])
            for n in range(len(rnd["qs"]))]
    return screen.Shown("Here's the answer sheet for the teams.", screen.card(
        "table", "Answer sheet", columns=["Round", "Question", "Your answer"], rows=rows))


def host_sheet(settings: Settings) -> screen.Shown:
    game = _game(settings)
    rows = [[f"{r + 1}.{n + 1}", item["q"], item["a"]] for r, rnd in enumerate(game["rounds"])
            for n, item in enumerate(rnd["qs"])]
    return screen.Shown("Here's the host's sheet with every answer. Keep it to yourself.", screen.card(
        "table", "Host answer key", columns=["Q", "Question", "Answer"], rows=rows))


def buzzer(settings: Settings, a: dict) -> screen.Shown:
    names = [hs.clean(t, 30) for t in (a.get("teams") or []) if hs.clean(t, 30)]
    if not names:
        game = hs.load(settings, QUIZ, {})
        names = list(game.get("teams") or [])
    names = list(dict.fromkeys(names))
    if not 2 <= len(names) <= MAX_TEAMS:
        raise ValueError("The buzzer needs 2 to 8 team names.")
    data = {"teams": [{"name": n, "key": str(i + 1)} for i, n in enumerate(names)]}
    return screen.Shown("The buzzer is up. First to press wins. Each team has its own number key, or click.",
                        screen.card("partyhost-buzzer", "Buzzer", "partyhost-buzzer", data=data))


# ---- Tool ------------------------------------------------------------------------------------

def tool_definitions() -> list[dict]:
    return [{
        "name": "party_quiz",
        "description": "Host a quiz night or game night with teams. action: 'start' (teams or team_count, rounds, "
                       "per_round, categories; picks questions from a 150-question bank; if a quiz with scores is on, "
                       "ask first and set confirmed only after a yes), 'categories', 'question' (next question on "
                       "the big screen), 'reveal' (the answer), 'award' (team, points, default 1), 'undo' (last "
                       "points), 'scoreboard' (big scoreboard), 'round_results', 'end' (final scores), "
                       "'add_question' (category, question, answer of your own), 'tiebreaker' (closest number), "
                       "'answer_sheet' (for teams), 'host_sheet' (all answers), 'buzzer' (pop-up buzzer where "
                       "the first press wins; teams optional).",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": list(ACTIONS)},
                "teams": {"type": "array", "items": {"type": "string"}},
                "team": {"type": "string", "description": "award: the team to give points to."},
                "team_count": {"type": "integer"},
                "rounds": {"type": "integer"}, "per_round": {"type": "integer"}, "round": {"type": "integer"},
                "categories": {"type": "array", "items": {"type": "string"}},
                "points": {"type": "integer"},
                "category": {"type": "string"}, "question": {"type": "string"}, "answer": {"type": "string"},
                "confirmed": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"party_quiz"}


def run_tool(name: str, args: dict, settings: Settings, http=None):
    action = args.get("action")
    simple = {"question": question, "reveal": reveal, "undo": undo, "end": end, "categories": categories,
              "tiebreaker": tiebreaker, "answer_sheet": answer_sheet, "host_sheet": host_sheet}
    if action in simple:
        return simple[action](settings)
    if action == "scoreboard":
        return _scoreboard(_game(settings))
    handlers = {"start": start, "award": award, "round_results": round_results, "add_question": add_question,
                "buzzer": buzzer}
    if action not in handlers:
        raise ValueError(f"I don't know the quiz action {action}.")
    return handlers[action](settings, args)
