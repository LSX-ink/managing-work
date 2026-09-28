"""Sport from keyless public feeds: football league tables and a team's next or last matches (TheSportsDB's
free key "3"), and Formula 1 standings, results and the next race (the Jolpica Ergast-compatible API).

Only a league number, a team name or a team number is ever sent. Matches pop up in the "sports-matches" window
(frontend/popup-sports.js):
  {sections: [{title, note?, matches: [{home, away, home_badge, away_badge, score, when, league, outcome?, say?}]}]}
"""

import asyncio
from datetime import date, datetime, timezone

import httpx

import homestore as hs
import screen
from config import Settings
from feeds import fetch_json

screen.EXTRA_KINDS.add("sports-matches")

SPORTSDB = "https://www.thesportsdb.com/api/v1/json/3"
F1 = "https://api.jolpi.ca/ergast/f1"
FAVOURITES = "sports-favourites.json"
LEAGUES = {
    "premier_league": (4328, "Premier League"), "championship": (4329, "Championship"),
    "la_liga": (4335, "La Liga"), "serie_a": (4332, "Serie A"), "bundesliga": (4331, "Bundesliga"),
    "ligue_1": (4334, "Ligue 1"), "scottish_premiership": (4330, "Scottish Premiership"),
}


def now() -> datetime:
    return datetime.now(timezone.utc)


def season(day: date) -> str:
    """The football season running on a day, e.g. '2026-2027' from July onwards."""
    start = day.year if day.month >= 7 else day.year - 1
    return f"{start}-{start + 1}"


def _https(url) -> str:
    return url if isinstance(url, str) and url.startswith("https://") else ""


def _int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


# ---- Teams and matches --------------------------------------------------------------------------

def favourites(settings: Settings) -> list[dict]:
    return [f for f in hs.load(settings, FAVOURITES, []) if isinstance(f, dict) and f.get("id") and f.get("name")]


def _team(t: dict) -> dict:
    return {"id": str(t.get("idTeam")), "name": t.get("strTeam") or "", "league": t.get("strLeague") or "",
            "badge": _https(t.get("strBadge") or t.get("strTeamBadge"))}


async def find_team(http: httpx.AsyncClient, settings: Settings, name: str) -> dict:
    """A team from the favourites (no lookup needed) or from TheSportsDB's team search, football first."""
    name = hs.need(name, "team", 60)
    saved = hs.find([f["name"] for f in favourites(settings)], name)
    if saved:
        return next(f for f in favourites(settings) if f["name"] == saved)
    found = (await fetch_json(http, f"{SPORTSDB}/searchteams.php", "sports results", params={"t": name}))
    teams = [t for t in (found or {}).get("teams") or [] if isinstance(t, dict) and t.get("idTeam")]
    if not teams:
        raise ValueError(f"I couldn't find a team called {name}.")
    teams.sort(key=lambda t: t.get("strSport") != "Soccer")
    return _team(teams[0])


def kickoff(e: dict) -> datetime | None:
    """Kick-off in local time; TheSportsDB times are UTC."""
    text = e.get("strTimestamp") or (f"{e['dateEvent']}T{e.get('strTime') or '00:00:00'}" if e.get("dateEvent") else "")
    try:
        at = datetime.fromisoformat(str(text).replace("Z", "+00:00"))
    except ValueError:
        return None
    return (at if at.tzinfo else at.replace(tzinfo=timezone.utc)).astimezone()


def spoken_day(at: datetime | None, clock: bool = True) -> str:
    if not at:
        return "on a date to be confirmed"
    day = f"{at:%A} {at.day} {at:%B}"
    return f"{day} at {at:%H:%M}" if clock and (at.hour or at.minute) else day


def match(e: dict, team: dict | None = None) -> dict:
    """One event as a row for the sports-matches window, with W/D/L from the team's side when played."""
    home, away = _int(e.get("intHomeScore")), _int(e.get("intAwayScore"))
    at = kickoff(e)
    row = {"id": str(e.get("idEvent") or ""), "home": e.get("strHomeTeam") or "", "away": e.get("strAwayTeam") or "",
           "home_badge": _https(e.get("strHomeTeamBadge")), "away_badge": _https(e.get("strAwayTeamBadge")),
           "score": f"{home}-{away}" if home is not None and away is not None else "",
           "when": f"{at:%a %d %b %H:%M}" if at else "TBC", "at": at.isoformat() if at else "",
           "league": e.get("strLeague") or ""}
    if team and row["score"]:
        mine = home if _is_home(e, team) else away
        theirs = away if _is_home(e, team) else home
        row["outcome"] = "W" if mine > theirs else "L" if mine < theirs else "D"
    return row


def _is_home(e: dict, team: dict) -> bool:
    return str(e.get("idHomeTeam")) == team["id"] or (e.get("strHomeTeam") or "").lower() == team["name"].lower()


def _card_row(row: dict) -> dict:
    return {k: v for k, v in row.items() if k != "at"}


async def events(http: httpx.AsyncClient, team: dict, which: str) -> list[dict]:
    url, key = (f"{SPORTSDB}/eventsnext.php", "events") if which == "next" else (f"{SPORTSDB}/eventslast.php", "results")
    found = await fetch_json(http, url, "sports results", params={"id": team["id"]})
    rows = [e for e in (found or {}).get(key) or [] if isinstance(e, dict)]
    rows.sort(key=lambda e: (kickoff(e) or now()).timestamp(), reverse=which == "last")
    return rows


def said_last(team: dict, e: dict) -> str:
    row = match(e, team)
    other = row["away"] if _is_home(e, team) else row["home"]
    goals = row["score"].split("-")
    mine, theirs = goals if _is_home(e, team) else goals[::-1]
    verb = {"W": "beat", "L": "lost to", "D": "drew with"}[row["outcome"]]
    return f"{team['name']} {verb} {other} {mine}-{theirs} on {spoken_day(kickoff(e), clock=False)}."


def said_next(team: dict, e: dict) -> str:
    home = _is_home(e, team)
    other = e.get("strAwayTeam") if home else e.get("strHomeTeam")
    return f"{team['name']} play {other} {'at home' if home else 'away'} on {spoken_day(kickoff(e))}."


async def team_matches(http: httpx.AsyncClient, settings: Settings, name: str, which: str) -> screen.Shown:
    team = await find_team(http, settings, name)
    which = which if which in ("next", "last") else "both"
    parts = ["last", "next"] if which == "both" else [which]
    found = await asyncio.gather(*(events(http, team, w) for w in parts))
    sections, said = [], []
    for part, rows in zip(parts, found):
        rows = [e for e in rows if part == "next" or match(e)["score"]][:5]
        title = "Latest results" if part == "last" else "Coming up"
        sections.append({"title": title, "matches": [_card_row(match(e, team)) for e in rows],
                         "note": "" if rows else "Nothing listed."})
        if rows:
            said.append(said_last(team, rows[0]) if part == "last" else said_next(team, rows[0]))
    text = " ".join(said) or f"I couldn't find any {'' if which == 'both' else which + ' '}matches for {team['name']}."
    card = screen.card("sports-matches", team["name"], f"sports-team-{team['id']}",
                       data={"badge": team["badge"], "sections": sections},
                       buttons=[{"label": "Save as favourite", "say": f"Save {team['name']} as a favourite team."}])
    return screen.Shown(text, card)


async def league_table(http: httpx.AsyncClient, league: str, which_season: str = "") -> screen.Shown:
    if league not in LEAGUES:
        raise ValueError("Which league? Premier League, Championship, La Liga, Serie A, Bundesliga, Ligue 1 or "
                         "the Scottish Premiership.")
    lid, title = LEAGUES[league]
    which_season = hs.clean(which_season, 9) or season(now().date())
    found = await fetch_json(http, f"{SPORTSDB}/lookuptable.php", "football tables",
                             params={"l": lid, "s": which_season})
    rows = [r for r in (found or {}).get("table") or [] if isinstance(r, dict)]
    if not rows:
        raise ValueError(f"There's no {title} table for {which_season} yet.")
    rows.sort(key=lambda r: _int(r.get("intRank")) or 99)
    table = [[r.get("intRank") or "", r.get("strTeam") or "", r.get("intPlayed") or "", r.get("intWin") or "",
              r.get("intDraw") or "", r.get("intLoss") or "", r.get("intGoalDifference") or "",
              r.get("intPoints") or ""] for r in rows]
    top, second = rows[0], rows[1] if len(rows) > 1 else None
    gap = (_int(top.get("intPoints")) or 0) - (_int(second.get("intPoints")) or 0) if second else 0
    text = (f"{top.get('strTeam')} top the {title} on {top.get('intPoints')} points"
            + (f", {gap} clear of {second.get('strTeam')}." if second and gap else
               f", level with {second.get('strTeam')}." if second else "."))
    card = screen.card("table", f"{title} {which_season}", f"sports-table-{league}",
                       columns=["#", "Team", "P", "W", "D", "L", "GD", "Pts"], rows=table,
                       buttons=[{"label": f"How did {r.get('strTeam')} do?", "say": f"How did {r.get('strTeam')} do?"}
                                for r in rows[:1]])
    return screen.Shown(text, card)


# ---- Formula 1 ---------------------------------------------------------------------------------

async def _f1(http: httpx.AsyncClient, path: str) -> dict:
    return ((await fetch_json(http, f"{F1}/{path}", "Formula 1")) or {}).get("MRData") or {}


def _driver(d: dict) -> str:
    return f"{d.get('givenName', '')} {d.get('familyName', '')}".strip()


async def f1_standings(http: httpx.AsyncClient, kind: str) -> screen.Shown:
    teams = kind == "constructors"
    data = await _f1(http, "current/constructorStandings.json" if teams else "current/driverStandings.json")
    lists = (data.get("StandingsTable") or {}).get("StandingsLists") or []
    rows = (lists[0].get("ConstructorStandings" if teams else "DriverStandings") or []) if lists else []
    if not rows:
        raise ValueError("There are no Formula 1 standings yet this season.")
    name = (lambda r: (r.get("Constructor") or {}).get("name", "")) if teams else (lambda r: _driver(r.get("Driver") or {}))
    table = [[r.get("position", ""), name(r)] + ([] if teams else [", ".join(c.get("name", "") for c in r.get("Constructors") or [])])
             + [r.get("points", ""), r.get("wins", "")] for r in rows]
    columns = ["#", "Team", "Points", "Wins"] if teams else ["#", "Driver", "Team", "Points", "Wins"]
    lead = float(rows[0].get("points") or 0) - float(rows[1].get("points") or 0) if len(rows) > 1 else 0
    text = f"{name(rows[0])} lead{'' if teams else 's'} on {rows[0].get('points')} points" + (
        f", {lead:g} ahead of {name(rows[1])}." if len(rows) > 1 else ".")
    title = f"F1 {'constructors' if teams else 'drivers'} {lists[0].get('season', '')}".strip()
    other = "drivers" if teams else "constructors"
    return screen.Shown(text, screen.card("table", title, f"sports-f1-{kind}", columns=columns, rows=table,
                                          buttons=[{"label": f"Show {other}", "say": f"Show the F1 {other} standings."}]))


async def f1_last_race(http: httpx.AsyncClient) -> screen.Shown:
    races = ((await _f1(http, "current/last/results.json")).get("RaceTable") or {}).get("Races") or []
    if not races or not races[0].get("Results"):
        raise ValueError("There are no Formula 1 results yet this season.")
    race = races[0]
    results = race["Results"]
    rows = [[r.get("position", ""), _driver(r.get("Driver") or {}), (r.get("Constructor") or {}).get("name", ""),
             (r.get("Time") or {}).get("time") or r.get("status", ""), r.get("points", "")] for r in results]
    podium = [_driver(r.get("Driver") or {}) for r in results[:3]]
    text = f"{podium[0]} won the {race.get('raceName')}" + (
        f", ahead of {' and '.join(podium[1:])}." if len(podium) > 1 else ".")
    return screen.Shown(text, screen.card("table", race.get("raceName", "Last race"), "sports-f1-last",
                                          columns=["#", "Driver", "Team", "Time", "Pts"], rows=rows,
                                          buttons=[{"label": "Standings", "say": "Show the F1 drivers' standings."}]))


def race_start(race: dict) -> datetime | None:
    try:
        at = datetime.fromisoformat(f"{race['date']}T{(race.get('time') or '12:00:00Z')}".replace("Z", "+00:00"))
    except (KeyError, ValueError):
        return None
    return at if at.tzinfo else at.replace(tzinfo=timezone.utc)


async def next_race(http: httpx.AsyncClient) -> tuple[dict, datetime] | None:
    races = ((await _f1(http, "current.json")).get("RaceTable") or {}).get("Races") or []
    upcoming = [(r, race_start(r)) for r in races if race_start(r) and race_start(r) > now()]
    return min(upcoming, key=lambda x: x[1]) if upcoming else None


def race_words(race: dict, at: datetime) -> str:
    days = (at.date() - now().date()).days
    when = "today" if days <= 0 else "tomorrow" if days == 1 else f"in {days} days"
    where = (race.get("Circuit") or {}).get("circuitName") or ""
    return (f"The next race is the {race.get('raceName')}" + (f" at {where}" if where else "")
            + f", {spoken_day(at.astimezone())}, {when}.")


async def f1_next_race(http: httpx.AsyncClient) -> screen.Shown:
    found = await next_race(http)
    if not found:
        return screen.Shown("The Formula 1 season is over; there are no more races this year.",
                            screen.card("text", "F1 next race", "sports-f1-next", text="No more races this season."))
    race, at = found
    loc = ((race.get("Circuit") or {}).get("Location") or {})
    text = race_words(race, at)
    card = screen.card("timer", race.get("raceName", "Next race"), "sports-f1-next",
                       ends_at=at.timestamp() * 1000,
                       text=f"Round {race.get('round', '?')}, {(race.get('Circuit') or {}).get('circuitName', '')}, "
                            f"{loc.get('locality', '')} {loc.get('country', '')}\nLights out {at.astimezone():%a %d %b %H:%M}",
                       buttons=[{"label": "Last race", "say": "Show the last F1 race results."}])
    return screen.Shown(text, card)


# ---- The tool -------------------------------------------------------------------------------------

def tool_definitions() -> list[dict]:
    return [{
        "name": "sports_scores",
        "description": "Football and Formula 1 from live feeds, shown in a pop-up. league_table: the league "
                       "table/standings for the Premier League, Championship, La Liga, Serie A, Bundesliga, Ligue 1 "
                       "or Scottish Premiership. team_matches: a football team's next fixtures and/or last results "
                       "with badges ('when do Arsenal play next', 'Celtic's last results'). f1_standings: F1 "
                       "drivers' or constructors' championship. f1_last_race: last Grand Prix results. f1_next_race: "
                       "when and where the next Grand Prix is, with a countdown.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["league_table", "team_matches", "f1_standings", "f1_last_race",
                                                      "f1_next_race"]},
                "league": {"type": "string", "enum": list(LEAGUES)},
                "season": {"type": "string", "description": "league_table: e.g. '2025-2026'. Default the current one."},
                "team": {"type": "string", "description": "team_matches: football team name, e.g. 'Arsenal'."},
                "which": {"type": "string", "enum": ["next", "last", "both"], "description": "team_matches. Default both."},
                "standings": {"type": "string", "enum": ["drivers", "constructors"], "description": "Default drivers."},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"sports_scores"}


async def run_tool(name: str, args: dict, settings: Settings, http: httpx.AsyncClient):
    action = args.get("action")
    if action == "league_table":
        return await league_table(http, args.get("league") or "premier_league", args.get("season") or "")
    if action == "team_matches":
        return await team_matches(http, settings, args.get("team"), args.get("which") or "both")
    if action == "f1_standings":
        return await f1_standings(http, args.get("standings") or "drivers")
    if action == "f1_last_race":
        return await f1_last_race(http)
    if action == "f1_next_race":
        return await f1_next_race(http)
    raise ValueError(f"Unknown sports scores action: {action}")
