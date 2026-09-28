"""Keeping score: a score counter pop-up for any game, a darts 501 scorer with checkout suggestions, and a
tennis, badminton or table tennis match scorer that knows deuce, advantage, tie-breaks and who serves.

The score counter runs in its "sports-score" window (+/- buttons and a history); pressing Save there sends the
final scores back to Alfred, which keeps them in sports-scores.json. Darts ("sports-darts" window) and racket
matches keep their game in sports-darts.json and sports-match.json, as a list of visits or points replayed each time,
so undo is simply dropping the last one.
"""

import itertools

import homestore as hs
import screen
from config import Settings

screen.EXTRA_KINDS.update({"sports-score", "sports-darts"})

SCORES, DARTS, MATCH = "sports-scores.json", "sports-darts.json", "sports-match.json"
MAX_PLAYERS = 12
MAX_SAVED = 1000

# ---- Score counter --------------------------------------------------------------------------------


def _players(players, low: int = 2, high: int = MAX_PLAYERS) -> list[str]:
    names = []
    for p in players or []:
        name = hs.clean(p, 30)
        if name and name.lower() not in (n.lower() for n in names):
            names.append(name)
    if not low <= len(names) <= high:
        raise ValueError(f"I need {low} to {high} different player or team names." if low != high
                         else f"I need exactly {low} player names.")
    return names


def scorekeeper(players, game: str, start) -> screen.Shown:
    names = _players(players)
    game = hs.clean(game, 40) or "Game"
    start = int(start or 0)
    data = {"game": game, "players": [{"name": n, "score": start} for n in names], "start": start}
    return screen.Shown(f"Scoreboard up for {game}: {', '.join(names)}. Press Save when you finish.",
                        screen.card("sports-score", f"{game} scores", "sports-score", data=data))


def save_scores(settings: Settings, game: str, scores) -> screen.Shown:
    rows = []
    for s in scores or []:
        if isinstance(s, dict) and hs.clean(s.get("name")):
            try:
                rows.append({"name": hs.clean(s["name"], 30), "score": float(s.get("score") or 0)})
            except (TypeError, ValueError):
                raise ValueError("Scores need to be numbers.") from None
    if not rows:
        raise ValueError("Which scores should I save?")
    for r in rows:
        r["score"] = int(r["score"]) if r["score"].is_integer() else r["score"]
    game = hs.clean(game, 40) or "Game"
    saved = hs.load(settings, SCORES, [])[-(MAX_SAVED - 1):]
    saved.append({"date": hs.today().isoformat(), "game": game, "scores": rows})
    hs.save(settings, SCORES, saved)
    top = max(r["score"] for r in rows)
    winners = [r["name"] for r in rows if r["score"] == top]
    result = (f"{winners[0]} won" if len(winners) == 1 else f"{' and '.join(winners)} drew") + f" on {top:g}"
    return screen.Shown(f"Saved the {game} scores. {result}.", saved_card(saved, game))


def saved_card(saved: list[dict], game: str = "") -> dict:
    want = hs.clean(game).lower()
    games = [g for g in saved if isinstance(g, dict) and (not want or want in str(g.get("game", "")).lower())]
    rows = [[g.get("date", ""), g.get("game", ""), ", ".join(f"{s['name']} {s['score']:g}" for s in g["scores"])]
            for g in games[-50:][::-1]]
    return screen.card("table", f"Saved scores{': ' + game if want else ''}", "sports-saved-scores",
                       columns=["Date", "Game", "Scores"], rows=rows)


def wins(games: list[dict]) -> dict[str, int]:
    tally: dict[str, int] = {}
    for g in games:
        top = max(s["score"] for s in g["scores"])
        for s in g["scores"]:
            tally[s["name"]] = tally.get(s["name"], 0) + (s["score"] == top)
    return tally


def saved_scores(settings: Settings, game: str) -> screen.Shown:
    saved = [g for g in hs.load(settings, SCORES, []) if isinstance(g, dict) and g.get("scores")]
    card = saved_card(saved, game)
    if not card["rows"]:
        return screen.Shown("No saved scores yet." if not game else f"No saved scores for {game}.", card)
    want = hs.clean(game).lower()
    tally = wins([g for g in saved if not want or want in g["game"].lower()])
    best = sorted(tally.items(), key=lambda x: -x[1])[:3]
    return screen.Shown(f"{len(card['rows'])} saved games. Most wins: "
                        + ", ".join(f"{n} {w}" for n, w in best) + ".", card)


# ---- Darts ------------------------------------------------------------------------------------------

DOUBLE_ORDER = [20, 16, 18, 12, 10, 8, 14, 6, 4, 2, 19, 17, 15, 13, 11, 9, 7, 5, 3, 1]
GOOD_DOUBLES = 6  # the first six above are the doubles players aim to leave
IMPOSSIBLE_VISITS = {179, 178, 176, 175, 173, 172, 169, 166, 163}


def _darts() -> tuple[list, dict]:
    """(every dart as (name, value, rank), {finishing value: (name, tier, rank)}); lower is preferred."""
    darts = [(f"T{n}", 3 * n, 20 - n) for n in range(20, 0, -1)] + [(str(n), n, 40 - n) for n in range(20, 0, -1)]
    darts += [("25", 25, 70), ("Bull", 50, 75)] + [(f"D{n}", 2 * n, 80 + i) for i, n in enumerate(DOUBLE_ORDER)]
    doubles = {2 * n: (f"D{n}", 0 if i < GOOD_DOUBLES else 1, i) for i, n in enumerate(DOUBLE_ORDER)}
    doubles[50] = ("Bull", 2, 99)
    return darts, doubles


def _key(route: list, double: tuple) -> tuple:
    """Fewest darts, a good double, fewest hard setup darts (trebles, doubles, bull); then favourites."""
    trebles = sum(not d[0].isdigit() for d in route)
    ranks = [d[2] for d in route] + [0, 0]
    order = (ranks[0], ranks[1], double[2]) if trebles else (double[2], ranks[0], ranks[1])
    return (len(route) + 1, double[1], trebles) + order


def checkout_table() -> dict[int, list[str]]:
    """The preferred finish, ending on a double, for every score from 2 to 170 that can be checked out."""
    darts, doubles = _darts()
    routes = [[]] + [[a] for a in darts] + [[a, b] for a, b in itertools.product(darts, repeat=2) if a[2] <= b[2]]
    best: dict[int, tuple] = {}
    for route in routes:
        before = sum(d[1] for d in route)
        for value, double in doubles.items():
            total = before + value
            if total <= 170:
                key = _key(route, double)
                if total not in best or key < best[total][0]:
                    best[total] = (key, [d[0] for d in route] + [double[0]])
    return {total: found[1] for total, found in sorted(best.items())}


CHECKOUTS = checkout_table()


def checkout(number) -> screen.Shown:
    n = int(number or 0)
    route = CHECKOUTS.get(n)
    if not route:
        why = "is too big to finish in three darts" if n > 170 else "can't be finished in three darts" if n > 1 else \
            "can't be finished, as you have to end on a double"
        text = f"{n} {why}."
    else:
        text = f"{n}: {', '.join(route)}."
    return screen.Shown(text, screen.card("text", f"Checkout {n}", "sports-checkout", text=text))


def _visit_score(value) -> int:
    try:
        n = int(value)
    except (TypeError, ValueError):
        raise ValueError("What did they score with that visit?") from None
    if not 0 <= n <= 180 or n in IMPOSSIBLE_VISITS:
        raise ValueError(f"{n} isn't possible with three darts.")
    return n


def darts_state(game: dict) -> dict:
    """Replays the visits: remaining scores, whose turn it is, averages and the winner."""
    names, start = game["players"], game["start"]
    remaining, scored, turns = [start] * len(names), [0] * len(names), [0] * len(names)
    history = [[] for _ in names]
    winner, message = None, ""
    for k, score in enumerate(game["visits"]):
        i = (game["starter"] + k) % len(names)
        left = remaining[i] - score
        bust = left < 0 or left == 1 or (left == 0 and remaining[i] not in CHECKOUTS)
        turns[i] += 1
        if bust:
            history[i].append(f"{score} bust")
            message = f"{names[i]} bust; still on {remaining[i]}."
            continue
        remaining[i], scored[i] = left, scored[i] + score
        history[i].append(str(score))
        message = f"{names[i]} scored {score}, {left} left."
        if left == 0:
            winner, message = i, f"Game shot! {names[i]} wins the leg."
            break
    turn = (game["starter"] + len(game["visits"])) % len(names)
    return {"remaining": remaining, "turn": turn, "winner": winner, "message": message, "history": history,
            "averages": [round(scored[i] / turns[i], 1) if turns[i] else 0 for i in range(len(names))]}


def darts_card(game: dict, st: dict) -> dict:
    players = [{"name": n, "remaining": st["remaining"][i], "average": st["averages"][i],
                "last": st["history"][i][-3:], "legs": game["legs"].get(n, 0),
                "checkout": " ".join(CHECKOUTS.get(st["remaining"][i], []))} for i, n in enumerate(game["players"])]
    data = {"start": game["start"], "turn": st["turn"], "winner": st["winner"], "players": players,
            "message": st["message"]}
    buttons = [{"label": "Undo", "say": "Undo the last darts visit."}]
    if st["winner"] is not None:
        buttons.insert(0, {"label": "Next leg", "say": "Start the next darts leg."})
    return screen.card("sports-darts", f"Darts {game['start']}", "sports-darts", data=data, buttons=buttons)


def _load_darts(settings: Settings) -> dict:
    game = hs.load(settings, DARTS, {})
    if not game.get("players"):
        raise ValueError("There's no darts game on. Say 'start a game of darts with Sam and Alex'.")
    return game


def darts_start(settings: Settings, players, start) -> screen.Shown:
    old = hs.load(settings, DARTS, {})
    if players:
        game = {"players": _players(players, 1, 8), "legs": {}, "starter": 0}
    elif old.get("players"):
        game = {"players": old["players"], "legs": old.get("legs", {}),
                "starter": (old.get("starter", 0) + 1) % len(old["players"])}
        start = start or old.get("start")
    else:
        raise ValueError("Who's playing darts?")
    start = int(start or 501)
    if start not in (101, 170, 301, 501, 701, 1001):
        raise ValueError("Darts games start from 101, 170, 301, 501, 701 or 1001.")
    game.update(start=start, visits=[])
    hs.save(settings, DARTS, game)
    first = game["players"][game["starter"]]
    return screen.Shown(f"Darts, {game['start']} up. {first} to throw first.", darts_card(game, darts_state(game)))


def _speak(game: dict, st: dict) -> str:
    if st["winner"] is not None:
        return st["message"]
    nxt, left = game["players"][st["turn"]], st["remaining"][st["turn"]]
    route = CHECKOUTS.get(left)
    return f"{st['message']} {nxt} needs {left}" + (f": {' '.join(route)}." if route else ".")


def darts_visit(settings: Settings, score) -> screen.Shown:
    game = _load_darts(settings)
    if darts_state(game)["winner"] is not None:
        raise ValueError("That leg is over. Say 'next leg' to play another.")
    game["visits"].append(_visit_score(score))
    st = darts_state(game)
    if st["winner"] is not None:
        name = game["players"][st["winner"]]
        game["legs"][name] = game["legs"].get(name, 0) + 1
    hs.save(settings, DARTS, game)
    return screen.Shown(_speak(game, st), darts_card(game, st))


def darts_undo(settings: Settings) -> screen.Shown:
    game = _load_darts(settings)
    if not game["visits"]:
        raise ValueError("There's nothing to undo in this leg.")
    before = darts_state(game)
    game["visits"].pop()
    if before["winner"] is not None:
        name = game["players"][before["winner"]]
        game["legs"][name] = max(0, game["legs"].get(name, 0) - 1)
    hs.save(settings, DARTS, game)
    st = darts_state(game)
    nxt = game["players"][st["turn"]]
    return screen.Shown(f"Undone. {nxt} to throw, needing {st['remaining'][st['turn']]}.", darts_card(game, st))


# ---- Tennis, badminton, table tennis ------------------------------------------------------------------

SPORTS = {"tennis": ("Tennis", 3, (1, 3, 5)), "badminton": ("Badminton", 3, (1, 3)),
          "table_tennis": ("Table tennis", 5, (1, 3, 5, 7))}
CALLS = ["love", "15", "30", "40"]


def _tennis_point(st: dict, w: int, names: list[str]) -> None:
    pts, games = st["points"], st["games"]
    target = 7 if st["tiebreak"] else 4
    if not (pts[w] >= target and pts[w] - pts[1 - w] >= 2):
        return
    games[w] += 1
    st["points"] = [0, 0]
    lead = w if games[w] > games[1 - w] else 1 - w
    st["event"] = f"Game {names[w]}. " + (f"{games[w]} all." if games[0] == games[1] else
                                          f"{names[lead]} leads {max(games)}-{min(games)}.")
    set_won = st["tiebreak"] or (games[w] >= 6 and games[w] - games[1 - w] >= 2)
    st["server"] = 1 - st["tb_first"] if st["tiebreak"] else 1 - st["server"]
    st["tiebreak"] = False
    if set_won:
        _set_won(st, w, list(games), names)
        st["games"] = [0, 0]
    elif games == [6, 6]:
        st["tiebreak"], st["tb_first"] = True, st["server"]
        st["event"] = "Six all. Tie-break."


def _set_won(st: dict, w: int, score: list[int], names: list[str]) -> None:
    st["sets"].append(score)
    won = sum(1 for s in st["sets"] if s[w] > s[1 - w])
    word = "Set" if st["sport"] == "tennis" else "Game"
    st["event"] = f"{word} {names[w]}, {score[w]}-{score[1 - w]}."
    if won == st["best_of"] // 2 + 1:
        st["winner"] = w
        st["event"] = (f"Game, set and match {names[w]}. " if st["sport"] == "tennis" else f"Match to {names[w]}. ") + \
            ", ".join(f"{s[w]}-{s[1 - w]}" for s in st["sets"]) + "."


def _rally_point(st: dict, w: int, names: list[str]) -> None:
    pts = st["points"]
    target, cap = (21, 30) if st["sport"] == "badminton" else (11, None)
    if st["sport"] == "badminton":
        st["server"] = w
    if pts[w] >= target and (pts[w] - pts[1 - w] >= 2 or pts[w] == cap):
        _set_won(st, w, list(pts), names)
        st["points"] = [0, 0]


def match_state(m: dict) -> dict:
    """Replays the points of a match under its sport's rules."""
    names = m["players"]
    st = {"sport": m["sport"], "best_of": m["best_of"], "sets": [], "games": [0, 0], "points": [0, 0],
          "tiebreak": False, "tb_first": 0, "server": 0, "winner": None, "event": ""}
    for w in m["points"]:
        st["event"] = ""
        st["points"][w] += 1
        (_tennis_point if m["sport"] == "tennis" else _rally_point)(st, w, names)
        if st["winner"] is not None:
            break
    k = sum(st["points"])
    if st["sport"] == "tennis" and st["tiebreak"]:
        st["serving"] = st["tb_first"] if ((k + 1) // 2) % 2 == 0 else 1 - st["tb_first"]
    elif st["sport"] == "table_tennis":
        first = len(st["sets"]) % 2
        st["serving"] = first if ((k // 2) if k < 20 else k) % 2 == 0 else 1 - first
    else:
        st["serving"] = st["server"]
    return st


def point_labels(st: dict) -> list[str]:
    a, b = st["points"]
    if st["sport"] != "tennis" or st["tiebreak"]:
        return [str(a), str(b)]
    if a >= 3 and b >= 3:
        return ["AD" if a > b else "40", "AD" if b > a else "40"]
    return [("0", "15", "30", "40")[a], ("0", "15", "30", "40")[b]]


def call(st: dict, names: list[str]) -> str:
    """The umpire's call, server's score first."""
    s, o = st["serving"], 1 - st["serving"]
    p = st["points"]
    if st["sport"] == "tennis" and not st["tiebreak"]:
        if p[0] >= 3 and p[1] >= 3:
            return "Deuce." if p[0] == p[1] else f"Advantage {names[0 if p[0] > p[1] else 1]}."
        if p[s] == p[o]:
            return f"{CALLS[p[s]].capitalize()} all." if p[s] else ""
        return f"{CALLS[p[s]].capitalize()}-{CALLS[p[o]]}."
    if not p[s] and not p[o]:
        return ""
    return f"{'Tie-break ' if st['tiebreak'] else ''}{p[s]}-{p[o]}" + (" all." if p[s] == p[o] else ".")


def match_card(m: dict, st: dict) -> dict:
    title = SPORTS[m["sport"]][0]
    names = m["players"]
    live = st["sport"] == "tennis"
    heads = [f"S{i + 1}" if live else f"G{i + 1}" for i in range(len(st["sets"]))]
    columns = ["Player"] + heads + (["Games"] if live else []) + ["Points"]
    labels = point_labels(st)
    rows = [[("● " if st["serving"] == i and st["winner"] is None else "") + n]
            + [str(s[i]) for s in st["sets"]] + ([str(st["games"][i])] if live else []) + [labels[i]]
            for i, n in enumerate(names)]
    buttons = [] if st["winner"] is not None else [
        {"label": f"Point {n}", "say": f"Point to {n} in the {title.lower()} match."} for n in names]
    buttons.append({"label": "Undo", "say": f"Undo the last point in the {title.lower()} match."})
    text = st["event"] or ("Tie-break" if st["tiebreak"] else "")
    return screen.card("table", f"{title}: {names[0]} v {names[1]}", "sports-match", columns=columns, rows=rows,
                       buttons=buttons, text=text)


def _load_match(settings: Settings) -> dict:
    m = hs.load(settings, MATCH, {})
    if m.get("sport") not in SPORTS or len(m.get("players") or []) != 2:
        raise ValueError("There's no match on. Say 'score a tennis match between Sam and Alex'.")
    return m


def _match_said(m: dict, st: dict) -> str:
    serving = "" if st["winner"] is not None else f" {m['players'][st['serving']]} to serve."
    return (" ".join(x for x in (st["event"], call(st, m["players"])) if x) or "Love all.") + serving


def match_start(settings: Settings, players, sport: str, best_of) -> screen.Shown:
    if sport not in SPORTS:
        raise ValueError("Tennis, badminton or table tennis?")
    title, default, allowed = SPORTS[sport]
    best_of = int(best_of or default)
    if best_of not in allowed:
        raise ValueError(f"{title} matches can be best of {', '.join(map(str, allowed))}.")
    m = {"sport": sport, "players": _players(players, 2, 2), "best_of": best_of, "points": []}
    hs.save(settings, MATCH, m)
    st = match_state(m)
    return screen.Shown(f"{title}, best of {best_of}. {m['players'][0]} to serve.", match_card(m, st))


def match_point(settings: Settings, player: str) -> screen.Shown:
    m = _load_match(settings)
    if match_state(m)["winner"] is not None:
        raise ValueError("That match is over. Start a new one whenever you like.")
    found = hs.find(m["players"], hs.need(player, "player"))
    if not found:
        raise ValueError(f"The players are {m['players'][0]} and {m['players'][1]}.")
    m["points"].append(m["players"].index(found))
    hs.save(settings, MATCH, m)
    st = match_state(m)
    return screen.Shown(_match_said(m, st), match_card(m, st))


def match_undo(settings: Settings) -> screen.Shown:
    m = _load_match(settings)
    if not m["points"]:
        raise ValueError("No points have been played yet.")
    m["points"].pop()
    hs.save(settings, MATCH, m)
    st = match_state(m)
    return screen.Shown("Undone. " + _match_said(m, st), match_card(m, st))


# ---- The tool -------------------------------------------------------------------------------------

def tool_definitions() -> list[dict]:
    return [{
        "name": "sports_scorekeeper",
        "description": "Keep score in a pop-up. scorekeeper: score counter/tally for any game with +/- buttons for "
                       "2+ players or teams; save_scores stores final scores (the pop-up's Save sends them); "
                       "saved_scores: past games and wins. darts_start / darts_visit (score for a visit of three "
                       "darts) / darts_undo: darts 501 scorer; darts_checkout: how to check out a number. "
                       "match_start / match_point / match_undo: tennis, badminton or table tennis match scorer "
                       "with deuce, tie-breaks and serve.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["scorekeeper", "save_scores", "saved_scores", "darts_start",
                                                      "darts_visit", "darts_undo", "darts_checkout", "match_start",
                                                      "match_point", "match_undo"]},
                "players": {"type": "array", "items": {"type": "string"}, "description": "Player or team names."},
                "game": {"type": "string", "description": "scorekeeper/save_scores/saved_scores: e.g. 'Scrabble'."},
                "start": {"type": "integer", "description": "scorekeeper: starting score (0). darts_start: 501, 301..."},
                "scores": {"type": "array", "items": {"type": "object", "properties": {
                    "name": {"type": "string"}, "score": {"type": "number"}},
                    "required": ["name", "score"], "additionalProperties": False}},
                "score": {"type": "integer", "description": "darts_visit: total of the three darts."},
                "number": {"type": "integer", "description": "darts_checkout: score left, 2 to 170."},
                "sport": {"type": "string", "enum": list(SPORTS)},
                "best_of": {"type": "integer", "description": "match_start: sets or games, e.g. 3 or 5."},
                "player": {"type": "string", "description": "match_point: who won the point."},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"sports_scorekeeper"}


def run_tool(name: str, args: dict, settings: Settings, http=None):
    action = args.get("action")
    if action == "scorekeeper":
        return scorekeeper(args.get("players"), args.get("game") or "", args.get("start"))
    if action == "save_scores":
        return save_scores(settings, args.get("game") or "", args.get("scores"))
    if action == "saved_scores":
        return saved_scores(settings, args.get("game") or "")
    if action == "darts_start":
        return darts_start(settings, args.get("players"), args.get("start"))
    if action == "darts_visit":
        return darts_visit(settings, args.get("score"))
    if action == "darts_undo":
        return darts_undo(settings)
    if action == "darts_checkout":
        return checkout(args.get("number"))
    if action == "match_start":
        return match_start(settings, args.get("players"), args.get("sport") or "tennis", args.get("best_of"))
    if action == "match_point":
        return match_point(settings, args.get("player"))
    if action == "match_undo":
        return match_undo(settings)
    raise ValueError(f"Unknown scorekeeper action: {action}")
