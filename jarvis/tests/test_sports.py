import asyncio
import json
from datetime import datetime, timedelta, timezone

import httpx
import pytest

import reminders
import sports_games as games
import sports_live as live
import sports_scoring as scoring
import sports_teams as teams
import tools
from config import Settings

SOON = (datetime.now(timezone.utc) + timedelta(days=3)).replace(hour=14, minute=0, second=0, microsecond=0)
PAST = datetime.now(timezone.utc) - timedelta(days=2)

ARSENAL = {"idTeam": "133604", "strTeam": "Arsenal", "strLeague": "English Premier League", "strSport": "Soccer",
           "strBadge": "https://r2.thesportsdb.com/images/media/team/badge/arsenal.png"}
LAST = {"idEvent": "901", "strHomeTeam": "Arsenal", "strAwayTeam": "Chelsea", "idHomeTeam": "133604",
        "intHomeScore": "2", "intAwayScore": "1", "strTimestamp": PAST.strftime("%Y-%m-%dT15:00:00"),
        "strLeague": "English Premier League", "strHomeTeamBadge": "https://r2.thesportsdb.com/a.png",
        "strAwayTeamBadge": "http://insecure.test/b.png"}
NEXT = {"idEvent": "902", "strHomeTeam": "Spurs", "strAwayTeam": "Arsenal", "idHomeTeam": "1",
        "intHomeScore": None, "intAwayScore": None, "strTimestamp": SOON.strftime("%Y-%m-%dT%H:%M:%S"),
        "strLeague": "English Premier League"}
F1_RACES = {"MRData": {"RaceTable": {"Races": [
    {"round": "18", "raceName": "Old Grand Prix", "date": PAST.strftime("%Y-%m-%d"), "time": "13:00:00Z",
     "Circuit": {"circuitName": "Old Circuit"}},
    {"round": "19", "raceName": "United States Grand Prix", "date": SOON.strftime("%Y-%m-%d"), "time": "19:00:00Z",
     "Circuit": {"circuitName": "Circuit of the Americas", "Location": {"locality": "Austin", "country": "USA"}}},
]}}}


def sportsdb(request):
    path, params = request.url.path, request.url.params
    if request.url.host == "api.jolpi.ca":
        if path.endswith("current.json"):
            return httpx.Response(200, json=F1_RACES)
        if path.endswith("driverStandings.json"):
            return httpx.Response(200, json={"MRData": {"StandingsTable": {"StandingsLists": [{"season": "2026", "DriverStandings": [
                {"position": "1", "points": "300", "wins": "8", "Driver": {"givenName": "Lando", "familyName": "Norris"},
                 "Constructors": [{"name": "McLaren"}]},
                {"position": "2", "points": "280", "wins": "6", "Driver": {"givenName": "Oscar", "familyName": "Piastri"},
                 "Constructors": [{"name": "McLaren"}]}]}]}}})
        if path.endswith("constructorStandings.json"):
            return httpx.Response(200, json={"MRData": {"StandingsTable": {"StandingsLists": [{"season": "2026", "ConstructorStandings": [
                {"position": "1", "points": "580", "wins": "14", "Constructor": {"name": "McLaren"}}]}]}}})
        if path.endswith("last/results.json"):
            return httpx.Response(200, json={"MRData": {"RaceTable": {"Races": [{"raceName": "Singapore Grand Prix", "Results": [
                {"position": "1", "points": "25", "Driver": {"givenName": "George", "familyName": "Russell"},
                 "Constructor": {"name": "Mercedes"}, "Time": {"time": "1:40:22"}},
                {"position": "2", "points": "18", "Driver": {"givenName": "Max", "familyName": "Verstappen"},
                 "Constructor": {"name": "Red Bull"}, "status": "Finished"}]}]}}})
    assert request.url.host == "www.thesportsdb.com" and "/api/v1/json/3/" in path
    if path.endswith("searchteams.php"):
        return httpx.Response(200, json={"teams": [ARSENAL] if params["t"].lower() == "arsenal" else None})
    if path.endswith("eventslast.php"):
        return httpx.Response(200, json={"results": [LAST]})
    if path.endswith("eventsnext.php"):
        return httpx.Response(200, json={"events": [NEXT]})
    if path.endswith("lookupevent.php"):
        return httpx.Response(200, json={"events": [{**NEXT, "intHomeScore": "1", "intAwayScore": "1"}]})
    if path.endswith("lookuptable.php"):
        assert params["l"] == "4328" and params["s"] == "2025-2026"
        return httpx.Response(200, json={"table": [
            {"intRank": "2", "strTeam": "Chelsea", "intPlayed": "6", "intWin": "4", "intDraw": "1", "intLoss": "1",
             "intGoalDifference": "5", "intPoints": "13"},
            {"intRank": "1", "strTeam": "Arsenal", "intPlayed": "6", "intWin": "5", "intDraw": "1", "intLoss": "0",
             "intGoalDifference": "9", "intPoints": "16"}]})
    return httpx.Response(404)


def run(module, args, settings=None, handler=sportsdb):
    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            out = module.run_tool(module.tool_definitions()[0]["name"], args, settings or Settings(), http)
            return await out if asyncio.iscoroutine(out) else out

    return asyncio.run(go())


def test_registered_and_deferred():
    names = {t["name"] for t in tools.client_tool_definitions(Settings())}
    for module in (live, teams, scoring, games):
        assert module in tools.ABILITIES and module not in tools.ALWAYS_LOADED
        (tool,) = module.tool_definitions()
        assert tool["name"] in names and tool["input_schema"]["additionalProperties"] is False


# ---- Live scores ------------------------------------------------------------------------------------

def test_league_table():
    out = run(live, {"action": "league_table", "league": "premier_league", "season": "2025-2026"})
    assert out == "Arsenal top the Premier League on 16 points, 3 clear of Chelsea."
    assert out.card["kind"] == "table" and out.card["rows"][0][1] == "Arsenal"
    assert live.season(datetime(2026, 9, 28).date()) == "2026-2027"
    assert live.season(datetime(2027, 3, 1).date()) == "2026-2027"


def test_team_matches_with_badges():
    out = run(live, {"action": "team_matches", "team": "arsenal"})
    assert out.startswith("Arsenal beat Chelsea 2-1 on") and "Arsenal play Spurs away on" in out
    card = out.card
    assert card["kind"] == "sports-matches"
    last, nxt = card["data"]["sections"]
    assert last["matches"][0]["outcome"] == "W" and last["matches"][0]["home_badge"].startswith("https://")
    assert last["matches"][0]["away_badge"] == ""  # only https pictures
    assert nxt["matches"][0]["score"] == ""
    with pytest.raises(ValueError, match="couldn't find a team"):
        run(live, {"action": "team_matches", "team": "Nowhere Rovers"})


def test_friendly_error_when_feed_is_down():
    with pytest.raises(ValueError, match="isn't answering"):
        run(live, {"action": "league_table", "league": "la_liga"}, handler=lambda r: httpx.Response(503))


def test_f1():
    out = run(live, {"action": "f1_standings"})
    assert out == "Lando Norris leads on 300 points, 20 ahead of Oscar Piastri."
    assert out.card["columns"] == ["#", "Driver", "Team", "Points", "Wins"]
    out = run(live, {"action": "f1_standings", "standings": "constructors"})
    assert out.startswith("McLaren lead on 580") and out.card["rows"][0] == ["1", "McLaren", "580", "14"]
    out = run(live, {"action": "f1_last_race"})
    assert out == "George Russell won the Singapore Grand Prix, ahead of Max Verstappen."
    out = run(live, {"action": "f1_next_race"})
    assert out.startswith("The next race is the United States Grand Prix at Circuit of the Americas")
    assert out.card["kind"] == "timer" and out.card["ends_at"] > datetime.now().timestamp() * 1000


# ---- My teams -----------------------------------------------------------------------------------------

def test_favourites(tmp_path):
    s = Settings(memory_dir=str(tmp_path))
    out = run(teams, {"action": "add_favourite", "team": "Arsenal"}, s)
    assert out == "Saved Arsenal as a favourite team." and out.card["items"][0]["say"] == "How did Arsenal do?"
    assert json.loads((tmp_path / "sports-favourites.json").read_text())[0]["id"] == "133604"
    assert run(teams, {"action": "add_favourite", "team": "arsenal"}, s) == "Arsenal is already a favourite."
    assert run(teams, {"action": "favourites"}, s) == "Your favourite teams: Arsenal."
    assert "Say yes" in run(teams, {"action": "remove_favourite", "team": "arsenal"}, s)
    assert len(live.favourites(s)) == 1
    assert run(teams, {"action": "remove_favourite", "team": "arsenal", "confirmed": True}, s) == \
        "Removed Arsenal from your favourites."
    assert live.favourites(s) == []


def test_how_did_we_do_and_summary(tmp_path):
    s = Settings(memory_dir=str(tmp_path))
    with pytest.raises(ValueError):
        run(teams, {"action": "how_did_we_do"}, s)
    run(teams, {"action": "add_favourite", "team": "Arsenal"}, s)
    out = run(teams, {"action": "how_did_we_do"}, s)
    assert out.startswith("Arsenal beat Chelsea 2-1") and out.card["kind"] == "sports-matches"
    out = run(teams, {"action": "summary"}, s)
    assert "Arsenal beat Chelsea" in out and "Arsenal play Spurs away" in out and "United States Grand Prix" in out
    titles = [sec["title"] for sec in out.card["data"]["sections"]]
    assert titles == ["Arsenal", "Formula 1"] and len(out.card["data"]["sections"][0]["matches"]) == 2


def test_match_reminder(tmp_path):
    s = Settings(memory_dir=str(tmp_path))
    out = run(teams, {"action": "match_reminder", "team": "Arsenal", "minutes_before": 30}, s)
    assert out.startswith("I'll remind them") and out.card["kind"] == "sports-matches"
    saved = reminders.load(s)
    local = SOON.astimezone() - timedelta(minutes=30)
    assert saved[0]["at"] == local.strftime("%Y-%m-%d %H:%M") and "Spurs v Arsenal" in saved[0]["text"]
    with pytest.raises(ValueError, match="next match against Chelsea"):
        run(teams, {"action": "match_reminder", "team": "Arsenal", "opponent": "Chelsea"}, s)


def test_predictions(tmp_path, monkeypatch):
    s = Settings(memory_dir=str(tmp_path))
    out = run(teams, {"action": "predict", "team": "Arsenal", "home_goals": 1, "away_goals": 1}, s)
    assert out == "Saved your prediction: Spurs 1, Arsenal 1." and out.card["kind"] == "table"
    out = run(teams, {"action": "my_predictions"}, s)
    assert out == "You have 0 points from 0 scored predictions."  # not played yet
    monkeypatch.setattr(live, "now", lambda: SOON + timedelta(hours=3))
    out = run(teams, {"action": "my_predictions"}, s)
    assert out.startswith("1 new result in, worth 3 points.") and out.card["rows"][0][3] == "1-1"
    assert teams.points([2, 1], [3, 0]) == 1 and teams.points([0, 0], [1, 0]) == 0
    with pytest.raises(ValueError):
        run(teams, {"action": "predict", "team": "Arsenal", "home_goals": -1, "away_goals": 1}, s)


# ---- Scorekeeping ----------------------------------------------------------------------------------------

def test_scorekeeper_and_saving(tmp_path):
    s = Settings(memory_dir=str(tmp_path))
    out = run(scoring, {"action": "scorekeeper", "players": ["Amy", "Ben", "amy"], "game": "Scrabble"}, s)
    assert out.card["kind"] == "sports-score"
    assert out.card["data"]["players"] == [{"name": "Amy", "score": 0}, {"name": "Ben", "score": 0}]
    with pytest.raises(ValueError):
        run(scoring, {"action": "scorekeeper", "players": ["Solo"]}, s)
    out = run(scoring, {"action": "save_scores", "game": "Scrabble",
                        "scores": [{"name": "Amy", "score": 312}, {"name": "Ben", "score": 290}]}, s)
    assert out == "Saved the Scrabble scores. Amy won on 312." and out.card["rows"][0][2] == "Amy 312, Ben 290"
    run(scoring, {"action": "save_scores", "game": "Uno", "scores": [{"name": "Ben", "score": 5}, {"name": "Amy", "score": 5}]}, s)
    out = run(scoring, {"action": "saved_scores"}, s)
    assert out.startswith("2 saved games. Most wins: Amy 2, Ben 1") and out.card["kind"] == "table"
    assert run(scoring, {"action": "saved_scores", "game": "chess"}, s) == "No saved scores for chess."


def test_checkouts():
    assert scoring.CHECKOUTS[170] == ["T20", "T20", "Bull"]
    assert scoring.CHECKOUTS[100] == ["T20", "D20"] and scoring.CHECKOUTS[40] == ["D20"]
    assert scoring.CHECKOUTS[141] == ["T20", "T19", "D12"]
    assert [n for n in range(2, 171) if n not in scoring.CHECKOUTS] == [159, 162, 163, 165, 166, 168, 169]
    assert run(scoring, {"action": "darts_checkout", "number": 121}).card["kind"] == "text"
    assert "can't be finished" in run(scoring, {"action": "darts_checkout", "number": 169})


def test_darts_leg(tmp_path):
    s = Settings(memory_dir=str(tmp_path))
    with pytest.raises(ValueError):
        run(scoring, {"action": "darts_visit", "score": 60}, s)
    out = run(scoring, {"action": "darts_start", "players": ["Sam", "Alex"], "start": 101}, s)
    assert out == "Darts, 101 up. Sam to throw first." and out.card["kind"] == "sports-darts"
    out = run(scoring, {"action": "darts_visit", "score": 60}, s)
    assert out == "Sam scored 60, 41 left. Alex needs 101: T17 Bull."
    with pytest.raises(ValueError):
        run(scoring, {"action": "darts_visit", "score": 179}, s)
    out = run(scoring, {"action": "darts_visit", "score": 100}, s)  # 1 left is a bust
    assert out.startswith("Alex bust; still on 101.") and out.card["data"]["players"][1]["remaining"] == 101
    out = run(scoring, {"action": "darts_visit", "score": 41}, s)
    assert out == "Game shot! Sam wins the leg." and out.card["data"]["winner"] == 0
    assert out.card["data"]["players"][0]["legs"] == 1
    assert run(scoring, {"action": "darts_undo"}, s).startswith("Undone. Sam to throw, needing 41.")
    run(scoring, {"action": "darts_visit", "score": 41}, s)
    out = run(scoring, {"action": "darts_start"}, s)  # next leg, Alex starts
    assert out == "Darts, 101 up. Alex to throw first." and out.card["data"]["players"][0]["legs"] == 1


def _points(s, *who):
    out = None
    for w in who:
        out = run(scoring, {"action": "match_point", "player": w}, s)
    return out


def test_tennis_scoring(tmp_path):
    s = Settings(memory_dir=str(tmp_path))
    out = run(scoring, {"action": "match_start", "players": ["Sam", "Alex"], "sport": "tennis", "best_of": 1}, s)
    assert out.card["kind"] == "table" and out.card["rows"][0][0] == "● Sam"
    assert _points(s, "Sam") == "15-love. Sam to serve."
    assert _points(s, "Alex", "Sam", "Alex", "Sam", "Alex") == "Deuce. Sam to serve."
    assert _points(s, "Alex") == "Advantage Alex. Sam to serve."
    out = _points(s, "Alex")
    assert out == "Game Alex. Alex leads 1-0. Alex to serve."
    assert run(scoring, {"action": "match_undo"}, s) == "Undone. Advantage Alex. Sam to serve."
    _points(s, "Alex")
    for game in range(11):  # games go with serve up to 6-6
        who = "Sam" if game % 2 == 0 else "Alex"
        out = _points(s, who, who, who, who)
    assert "Six all. Tie-break." in out
    m = scoring.match_state(scoring.hs.load(s, scoring.MATCH, {}))
    assert m["tiebreak"] and m["serving"] == 0  # Sam serves first in the tie-break
    out = _points(s, "Alex")
    assert out == "Tie-break 1-0. Alex to serve."  # server's score first
    out = _points(s, *["Alex"] * 6)
    assert out == "Game, set and match Alex. 7-6."
    assert [b["label"] for b in out.card["buttons"]] == ["Undo"]
    with pytest.raises(ValueError):
        _points(s, "Sam")


def test_badminton_and_table_tennis(tmp_path):
    s = Settings(memory_dir=str(tmp_path))
    run(scoring, {"action": "match_start", "players": ["Amy", "Ben"], "sport": "badminton"}, s)
    m = scoring.hs.load(s, scoring.MATCH, {})
    m["points"] = [0, 1] * 29  # 29 all
    scoring.hs.save(s, scoring.MATCH, m)
    out = _points(s, "Ben")
    assert out == "Game Ben, 30-29. Ben to serve."
    run(scoring, {"action": "match_start", "players": ["Amy", "Ben"], "sport": "table_tennis", "best_of": 3}, s)
    assert _points(s, "Amy") == "1-0. Amy to serve."
    assert _points(s, "Amy") == "0-2. Ben to serve."  # service changes every two points; server first
    with pytest.raises(ValueError):
        run(scoring, {"action": "match_start", "players": ["Amy", "Ben"], "sport": "badminton", "best_of": 5}, s)


# ---- Game night -----------------------------------------------------------------------------------------

def test_golf(tmp_path):
    s = Settings(memory_dir=str(tmp_path))
    pars = [4, 3, 5, 4, 4, 3, 4, 5, 4]
    out = run(games, {"action": "golf_course", "course": "Hilltop", "pars": pars}, s)
    assert out == "Saved Hilltop: 9 holes, par 36." and out.card["kind"] == "table"
    with pytest.raises(ValueError):
        run(games, {"action": "golf_course", "course": "Bad", "pars": [4, 3]}, s)
    with pytest.raises(ValueError, match="Tell me its pars"):
        run(games, {"action": "golf_round", "course": "Nowhere"}, s)
    run(games, {"action": "golf_round", "course": "hilltop", "players": ["Me", "Dad"]}, s)
    out = run(games, {"action": "golf_hole", "hole": 1, "strokes": 3}, s)
    assert out == "Hole 1, 3 for Me: a birdie. 1 under after 1."
    out = run(games, {"action": "golf_hole", "hole": 2, "strokes": 5, "player": "dad"}, s)
    assert out.startswith("Hole 2, 5 for Dad: a double bogey.")
    for hole, par in enumerate(pars, 1):
        run(games, {"action": "golf_hole", "hole": hole, "strokes": par, "player": "Dad"}, s)
        out = run(games, {"action": "golf_hole", "hole": hole, "strokes": par + (hole == 1) * -1}, s)
    assert out.endswith("That's the round finished and saved.")
    out = run(games, {"action": "golf_card"}, s)
    assert out == "Hilltop: Me 1 under, Dad level par."
    assert out.card["rows"][-2] == ["Total", "36", "35", "36"]


def test_league(tmp_path):
    s = Settings(memory_dir=str(tmp_path))
    with pytest.raises(ValueError):
        run(games, {"action": "league_table"}, s)
    run(games, {"action": "league_result", "league": "Quiz", "date": "2026-09-01",
                "results": [{"name": "Amy", "points": 30}, {"name": "Ben", "points": 25}]}, s)
    out = run(games, {"action": "league_result", "league": "quiz",
                      "results": [{"name": "Amy", "points": 20}, {"name": "Ben", "points": 28}]}, s)
    assert out == "Ben won tonight with 28. Ben leads the Quiz league on 53 points."
    out = run(games, {"action": "league_table"}, s)
    assert out.startswith("Ben leads the Quiz league") and out.card["rows"][0] == ["1", "Ben", "2", "1", "53", "26.5"]
    with pytest.raises(ValueError):
        run(games, {"action": "league_result", "date": "Friday", "results": [{"name": "A", "points": 1}]}, s)


def test_pick_teams():
    players = [{"name": n, "skill": k} for n, k in [("A", 5), ("B", 5), ("C", 3), ("D", 3), ("E", 1), ("F", 1)]]
    out = run(games, {"action": "pick_teams", "team_players": players})
    totals = sorted(float(c.split("(")[1].rstrip(")")) for c in out.card["columns"])
    assert totals == [9, 9] and out.card["kind"] == "table"
    out = run(games, {"action": "pick_teams", "team_players": [{"name": n} for n in "ABCDEFG"], "teams": 3})
    assert sorted(sum(1 for r in out.card["rows"] if r[i]) for i in range(3)) == [2, 2, 3]
    with pytest.raises(ValueError):
        run(games, {"action": "pick_teams", "team_players": [{"name": "A"}]})


def test_rules():
    out = run(games, {"action": "rules", "topic": "offside"})
    assert out.startswith("A player is offside") and out.card["title"] == "Football: offside"
    assert out.card["buttons"]
    for topic in games.RULES:
        assert run(games, {"action": "rules", "topic": topic}).card["kind"] == "text"
    with pytest.raises(ValueError):
        run(games, {"action": "rules", "topic": "quidditch"})
