"""Game night and the course: golf scorecards (your own courses and pars), a pub quiz or game night league with a
running table, a five-a-side team picker that balances skill, and a quick reference of sports rules.

Courses and rounds are kept in sports-golf.json, league nights in sports-league.json, in the memory folder.
"""

import random
from datetime import date

import homestore as hs
import screen
from config import Settings

GOLF, LEAGUE = "sports-golf.json", "sports-league.json"
RNG = random.Random()
MAX_COURSES = 50
MAX_ROUNDS = 300
MAX_NIGHTS = 500
TERMS = {-3: "an albatross", -2: "an eagle", -1: "a birdie", 0: "par", 1: "a bogey", 2: "a double bogey",
         3: "a triple bogey"}

RULES = {
    "offside": ("Football: offside",
                "A player is offside if, when a team-mate plays the ball to them, any part they can score with "
                "(head, body or feet, not arms) is in the opponents' half and nearer the goal line than both the ball "
                "and the second-last defender (the goalkeeper usually counts as one).\n\nIt isn't an offence just to "
                "be there: they must become involved in play. Level counts as onside. There's no offside from a goal "
                "kick, throw-in or corner, or in your own half. The punishment is an indirect free kick."),
    "lbw": ("Cricket: LBW",
            "Leg before wicket. The batter is out if the ball would have hit the stumps but hits their body (usually "
            "the pad) first, not the bat.\n\nThe ball must not pitch outside leg stump. If it hits the batter "
            "outside the line of off stump, they're only out if they didn't try to play a shot. The umpire judges "
            "whether it was going on to hit the wicket; DRS ball-tracking can review it in pro games."),
    "tennis_scoring": ("Tennis: scoring",
                       "Points go love, 15, 30, 40, game. At 40-40 it's deuce: win two points in a row to take the "
                       "game (advantage, then game).\n\nA set is the first to six games with a two-game lead. At "
                       "six all there's a tie-break. Matches are best of three sets (five in men's Grand Slams). "
                       "Players change serve every game and change ends after odd games."),
    "tennis_tiebreak": ("Tennis: tie-break",
                        "Played at six games all. First to seven points with a two-point lead wins the set 7-6.\n\n"
                        "The player due to serve serves the first point, then players serve two points each in "
                        "turn. Change ends every six points. Grand Slam final sets use a first-to-ten tie-break."),
    "darts": ("Darts: 501",
              "Each player starts on 501 and throws three darts a visit, taking the total away. The outer ring "
              "doubles, the inner ring trebles; the outer bull is 25, the bullseye 50.\n\nYou must finish exactly "
              "on zero, with your last dart in a double (the bullseye counts as double 25). Going below zero, "
              "to exactly one, or to zero without a double is a bust: the score goes back to where the visit "
              "started. The highest checkout is 170 (treble 20, treble 20, bull)."),
    "snooker": ("Snooker: points",
                "Reds are worth 1, then yellow 2, green 3, brown 4, blue 5, pink 6, black 7.\n\nPot a red, then a "
                "colour, which comes back on its spot; repeat while reds remain. Then clear the colours in order, "
                "yellow to black. A maximum break is 147.\n\nFouls give the opponent at least 4 points, or the "
                "value of the ball involved if higher (up to 7). A snooker is when you can't hit the ball on "
                "directly."),
    "badminton": ("Badminton: scoring",
                  "Every rally wins a point, whoever served. A game is to 21 with a two-point lead, up to a cap of "
                  "30 (at 29 all, the next point wins). Matches are best of three games. The rally winner serves "
                  "next, from the right court on an even score and the left on an odd one."),
    "table_tennis": ("Table tennis: scoring",
                     "Games go to 11 with a two-point lead. Service changes every two points, and every point "
                     "from 10 all. Matches are best of five or seven games. A serve that clips the net and lands "
                     "in is a let and is played again."),
    "rugby_union": ("Rugby union: points",
                    "A try is 5 points and the conversion kick after it 2. A penalty kick or drop goal is 3. A "
                    "penalty try is worth 7 with no kick needed."),
}


# ---- Golf -----------------------------------------------------------------------------------------

def _golf(settings: Settings) -> dict:
    data = hs.load(settings, GOLF, {})
    data.setdefault("courses", {})
    data.setdefault("rounds", [])
    return data


def _vs(n: int) -> str:
    return "level par" if n == 0 else f"{abs(n)} {'over' if n > 0 else 'under'}"


def golf_course(settings: Settings, name: str, pars) -> screen.Shown:
    name = hs.need(name, "course", 50)
    try:
        pars = [int(p) for p in pars or []]
    except (TypeError, ValueError):
        raise ValueError("Pars must be whole numbers.") from None
    if len(pars) not in (9, 18) or not all(3 <= p <= 6 for p in pars):
        raise ValueError("Give 9 or 18 pars, each between 3 and 6.")
    data = _golf(settings)
    key = hs.find(data["courses"], name) or name
    if key not in data["courses"] and len(data["courses"]) >= MAX_COURSES:
        raise ValueError("That's a lot of courses; remove one first.")
    data["courses"][key] = {"pars": pars}
    hs.save(settings, GOLF, data)
    rows = [[str(i + 1), str(p)] for i, p in enumerate(pars)] + [["Total", str(sum(pars))]]
    return screen.Shown(f"Saved {key}: {len(pars)} holes, par {sum(pars)}.",
                        screen.card("table", key, "sports-golf-course", columns=["Hole", "Par"], rows=rows,
                                    buttons=[{"label": "Start a round", "say": f"Start a round of golf at {key}."}]))


def golf_card(round_: dict) -> dict:
    pars, players = round_["pars"], round_["players"]
    rows = [[str(h + 1), str(p)] + [str(round_["scores"][n][h] or "") for n in players] for h, p in enumerate(pars)]

    def total(n, holes):
        return sum(round_["scores"][n][h] or 0 for h in holes)

    halves = [("Out", range(9)), ("In", range(9, 18))] if len(pars) == 18 else []
    for label, holes in halves + [("Total", range(len(pars)))]:
        rows.append([label, str(sum(pars[h] for h in holes))] + [str(total(n, holes)) for n in players])
    rows.append(["vs par", ""] + [_vs(to_par(round_, n)) for n in players])
    return screen.card("table", f"{round_['course']} {round_['date']}", "sports-golf-card",
                       columns=["Hole", "Par"] + players, rows=rows)


def to_par(round_: dict, name: str) -> int:
    return sum(s - p for s, p in zip(round_["scores"][name], round_["pars"]) if s)


def golf_round(settings: Settings, course: str, players) -> screen.Shown:
    data = _golf(settings)
    key = hs.find(data["courses"], hs.need(course, "course"))
    if not key:
        known = ", ".join(data["courses"]) or "none yet"
        raise ValueError(f"I don't know the course {course}. Tell me its pars first. Saved courses: {known}.")
    names = [hs.clean(p, 30) for p in players or [] if hs.clean(p)] or ["Me"]
    names = list(dict.fromkeys(names))[:4]
    pars = data["courses"][key]["pars"]
    data["round"] = {"course": key, "date": hs.today().isoformat(), "pars": pars, "players": names,
                     "scores": {n: [None] * len(pars) for n in names}}
    hs.save(settings, GOLF, data)
    return screen.Shown(f"Round started at {key}, par {sum(pars)}. First hole is a par {pars[0]}.",
                        golf_card(data["round"]))


def golf_hole(settings: Settings, hole, strokes, player: str) -> screen.Shown:
    data = _golf(settings)
    round_ = data.get("round")
    if not round_:
        raise ValueError("There's no round on. Say 'start a round of golf at' and the course.")
    name = hs.find(round_["players"], player) if hs.clean(player) else round_["players"][0]
    if not name:
        raise ValueError(f"The players are {', '.join(round_['players'])}.")
    try:
        hole, strokes = int(hole), int(strokes)
    except (TypeError, ValueError):
        raise ValueError("Which hole, and how many shots?") from None
    if not 1 <= hole <= len(round_["pars"]) or not 1 <= strokes <= 20:
        raise ValueError(f"Holes go from 1 to {len(round_['pars'])}, and shots from 1 to 20.")
    round_["scores"][name][hole - 1] = strokes
    diff = strokes - round_["pars"][hole - 1]
    term = "a hole in one" if strokes == 1 else TERMS.get(diff, f"{diff} over par")
    played = sum(1 for s in round_["scores"][name] if s)
    text = f"Hole {hole}, {strokes} for {name}: {term}. {_vs(to_par(round_, name)).capitalize()} after {played}."
    if all(all(round_["scores"][n]) for n in round_["players"]):
        summary = {"course": round_["course"], "date": round_["date"],
                   "totals": {n: sum(round_["scores"][n]) for n in round_["players"]}}
        data["rounds"] = [r for r in data["rounds"] if r.get("date") != summary["date"]
                          or r.get("course") != summary["course"]][-(MAX_ROUNDS - 1):] + [summary]
        text += " That's the round finished and saved."
    hs.save(settings, GOLF, data)
    return screen.Shown(text, golf_card(round_))


def golf_scorecard(settings: Settings) -> screen.Shown:
    data = _golf(settings)
    round_ = data.get("round")
    if not round_:
        raise ValueError("There's no golf round yet.")
    said = ", ".join(f"{n} {_vs(to_par(round_, n))}" for n in round_["players"])
    return screen.Shown(f"{round_['course']}: {said}.", golf_card(round_))


# ---- Pub quiz and game night league ---------------------------------------------------------------------

def _league(settings: Settings) -> dict:
    return {k: v for k, v in hs.load(settings, LEAGUE, {}).items() if isinstance(v, list)}


def standings(nights: list[dict]) -> list[dict]:
    table: dict[str, dict] = {}
    for night in nights:
        results = night.get("results") or {}
        if not results:
            continue
        top = max(results.values())
        for name, pts in results.items():
            row = table.setdefault(name, {"name": name, "played": 0, "wins": 0, "points": 0.0})
            row["played"] += 1
            row["points"] += pts
            row["wins"] += pts == top
    return sorted(table.values(), key=lambda r: (-r["points"], -r["wins"], r["name"].lower()))


def league_card(name: str, nights: list[dict]) -> dict:
    rows = [[str(i + 1), r["name"], str(r["played"]), str(r["wins"]), f"{r['points']:g}",
             f"{r['points'] / r['played']:.1f}"] for i, r in enumerate(standings(nights))]
    return screen.card("table", f"{name} league", f"sports-league-{name}",
                       columns=["#", "Player", "Nights", "Wins", "Points", "Avg"], rows=rows)


def league_result(settings: Settings, league: str, results, day: str) -> screen.Shown:
    name = hs.clean(league, 40) or "Game night"
    scores: dict[str, float] = {}
    for r in results or []:
        if isinstance(r, dict) and hs.clean(r.get("name")):
            try:
                scores[hs.clean(r["name"], 30)] = float(r.get("points") or 0)
            except (TypeError, ValueError):
                raise ValueError("Points need to be numbers.") from None
    if not scores:
        raise ValueError("Who played, and how many points did each get?")
    data = _league(settings)
    key = hs.find(data, name) or name
    nights = data.setdefault(key, [])[-(MAX_NIGHTS - 1):]
    try:
        when = date.fromisoformat(hs.clean(day, 10)) if hs.clean(day) else hs.today()
    except ValueError:
        raise ValueError("Give the date as YYYY-MM-DD.") from None
    nights.append({"date": when.isoformat(), "results": scores})
    data[key] = nights
    hs.save(settings, LEAGUE, data)
    top = max(scores.values())
    winners = [n for n, p in scores.items() if p == top]
    leader = standings(nights)[0]
    text = (f"{' and '.join(winners)} won tonight with {top:g}. {leader['name']} leads the {key} league on "
            f"{leader['points']:g} points.")
    return screen.Shown(text, league_card(key, nights))


def league_table(settings: Settings, league: str) -> screen.Shown:
    data = _league(settings)
    if not data:
        raise ValueError("There's no league yet. Tell me tonight's scores to start one.")
    key = hs.find(data, league) if hs.clean(league) else next(iter(data))
    if not key:
        raise ValueError(f"There's no league called {league}. Leagues: {', '.join(data)}.")
    table = standings(data[key])
    lead = table[0] if table else None
    text = f"{lead['name']} leads the {key} league on {lead['points']:g} points after {len(data[key])} nights." \
        if lead else f"No results in the {key} league yet."
    return screen.Shown(text, league_card(key, data[key]))


# ---- Team picker ------------------------------------------------------------------------------------------

def pick_teams(players, teams) -> screen.Shown:
    people = []
    for p in players or []:
        if isinstance(p, dict):
            name, skill = hs.clean(p.get("name"), 30), p.get("skill")
        else:
            name, skill = hs.clean(p, 30), None
        if name:
            people.append((name, float(skill) if skill is not None else None))
    count = int(teams or 2)
    if not 2 <= count <= 6 or len(people) < count:
        raise ValueError("I need 2 to 6 teams and at least one player per team.")
    rated = any(s is not None for _, s in people)
    RNG.shuffle(people)
    if rated:
        known = [s for _, s in people if s is not None]
        middle = sum(known) / len(known)
        people.sort(key=lambda p: -(p[1] if p[1] is not None else middle))
    sides = [{"players": [], "skill": 0.0} for _ in range(count)]
    size = -(-len(people) // count)
    for name, skill in people:
        open_sides = [s for s in sides if len(s["players"]) < size]
        side = min(open_sides, key=lambda s: (s["skill"], len(s["players"]))) if rated else \
            min(open_sides, key=lambda s: len(s["players"]))
        side["players"].append(name)
        side["skill"] += skill if skill is not None else (middle if rated else 0)
    columns = [f"Team {i + 1}" + (f" ({s['skill']:g})" if rated else "") for i, s in enumerate(sides)]
    rows = [[s["players"][r] if r < len(s["players"]) else "" for s in sides] for r in range(size)]
    again = ", ".join(n if s is None else f"{n} {s:g}" for n, s in people)
    said = ". ".join(f"Team {i + 1}: {', '.join(s['players'])}" for i, s in enumerate(sides)) + "."
    return screen.Shown(said, screen.card("table", "Teams", "sports-teams", columns=columns, rows=rows, buttons=[
        {"label": "Shuffle again", "say": f"Pick {count} teams again from: {again}."}]))


def rules(topic: str) -> screen.Shown:
    key = hs.find(RULES, hs.clean(topic).replace(" ", "_"))
    if not key:
        topics = ", ".join(k.replace("_", " ") for k in RULES)
        raise ValueError(f"I have quick rules for: {topics}.")
    title, text = RULES[key]
    others = [{"label": t.split(": ")[-1].capitalize(), "say": f"Explain the {k.replace('_', ' ')} rule."}
              for k, (t, _) in RULES.items() if k != key][:4]
    return screen.Shown(text.split("\n\n")[0], screen.card("text", title, "sports-rules", text=text, buttons=others))


# ---- The tool -------------------------------------------------------------------------------------

def tool_definitions() -> list[dict]:
    return [{
        "name": "sports_game_night",
        "description": "Golf scorecard, game night league, team picker and sports rules, in pop-ups. golf_course: "
                       "save a course's pars per hole; golf_round: start a round; golf_hole: my score on a hole; "
                       "golf_card: the scorecard with totals vs par. league_result: record a pub quiz or game night "
                       "(points per player); league_table: the running league table. pick_teams: split players into "
                       "balanced teams (five-a-side), optional skill ratings. rules: quick reference for offside, "
                       "LBW, tennis scoring and tie-breaks, darts, snooker, badminton, table tennis, rugby points.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["golf_course", "golf_round", "golf_hole", "golf_card",
                                                      "league_result", "league_table", "pick_teams", "rules"]},
                "course": {"type": "string"},
                "pars": {"type": "array", "items": {"type": "integer"}, "description": "golf_course: 9 or 18 pars."},
                "players": {"type": "array", "items": {"type": "string"}, "description": "golf_round players."},
                "hole": {"type": "integer"},
                "strokes": {"type": "integer"},
                "player": {"type": "string", "description": "golf_hole: default the first player."},
                "league": {"type": "string", "description": "Default 'Game night'."},
                "results": {"type": "array", "items": {"type": "object", "properties": {
                    "name": {"type": "string"}, "points": {"type": "number"}},
                    "required": ["name", "points"], "additionalProperties": False}},
                "date": {"type": "string", "description": "league_result: YYYY-MM-DD, default today."},
                "team_players": {"type": "array", "items": {"type": "object", "properties": {
                    "name": {"type": "string"}, "skill": {"type": "number", "description": "Optional, e.g. 1-5."}},
                    "required": ["name"], "additionalProperties": False}, "description": "pick_teams."},
                "teams": {"type": "integer", "description": "pick_teams: how many teams, default 2."},
                "topic": {"type": "string", "enum": list(RULES)},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"sports_game_night"}


def run_tool(name: str, args: dict, settings: Settings, http=None):
    action = args.get("action")
    if action == "golf_course":
        return golf_course(settings, args.get("course"), args.get("pars"))
    if action == "golf_round":
        return golf_round(settings, args.get("course"), args.get("players"))
    if action == "golf_hole":
        return golf_hole(settings, args.get("hole"), args.get("strokes"), args.get("player") or "")
    if action == "golf_card":
        return golf_scorecard(settings)
    if action == "league_result":
        return league_result(settings, args.get("league") or "", args.get("results"), args.get("date") or "")
    if action == "league_table":
        return league_table(settings, args.get("league") or "")
    if action == "pick_teams":
        return pick_teams(args.get("team_players"), args.get("teams"))
    if action == "rules":
        return rules(args.get("topic") or "")
    raise ValueError(f"Unknown game night action: {action}")
