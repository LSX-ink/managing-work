"""My teams: favourite football teams, "how did my team do?", a sports summary, match reminders and score
predictions scored against the real results (3 points for the exact score, 1 for the right result).

Favourites live in sports-favourites.json and predictions in sports-predictions.json in the memory folder.
Only team names and numbers, and match numbers, are sent to TheSportsDB.
"""

import asyncio
from datetime import datetime, timedelta

import httpx

import homestore as hs
import reminders
import screen
import sports_live as live
from config import Settings
from feeds import fetch_json

PREDICTIONS = "sports-predictions.json"
MAX_FAVOURITES = 12
MAX_PREDICTIONS = 500


# ---- Favourites ----------------------------------------------------------------------------------

def favourites_card(teams: list[dict]) -> dict:
    items = [{"label": f"{t['name']} ({t['league']})" if t.get("league") else t["name"],
              "say": f"How did {t['name']} do?"} for t in teams]
    return screen.card("list", "Favourite teams", "sports-favourites", items=items,
                       buttons=[{"label": "Sports summary", "say": "Give me my sports summary."}])


async def add_favourite(http: httpx.AsyncClient, settings: Settings, name: str) -> screen.Shown:
    teams = live.favourites(settings)
    team = await live.find_team(http, settings, name)
    if any(t["id"] == team["id"] for t in teams):
        return screen.Shown(f"{team['name']} is already a favourite.", favourites_card(teams))
    if len(teams) >= MAX_FAVOURITES:
        raise ValueError(f"You already have {MAX_FAVOURITES} favourite teams; remove one first.")
    teams.append(team)
    hs.save(settings, live.FAVOURITES, teams)
    return screen.Shown(f"Saved {team['name']} as a favourite team.", favourites_card(teams))


def list_favourites(settings: Settings) -> screen.Shown:
    teams = live.favourites(settings)
    if not teams:
        return screen.Shown("You haven't saved any favourite teams yet. Say 'save Arsenal as a favourite'.",
                            favourites_card([]))
    return screen.Shown(f"Your favourite teams: {', '.join(t['name'] for t in teams)}.", favourites_card(teams))


def remove_favourite(settings: Settings, name: str, confirmed: bool) -> screen.Shown:
    teams = live.favourites(settings)
    found = hs.find([t["name"] for t in teams], hs.need(name, "team"))
    if not found:
        raise ValueError(f"{name} isn't one of your favourite teams.")
    if not confirmed:
        return screen.Shown(f"Remove {found} from your favourite teams? Say yes to confirm.", favourites_card(teams))
    teams = [t for t in teams if t["name"] != found]
    hs.save(settings, live.FAVOURITES, teams)
    return screen.Shown(f"Removed {found} from your favourites.", favourites_card(teams))


def _pick(settings: Settings, name: str) -> list[dict] | None:
    teams = live.favourites(settings)
    if not hs.clean(name):
        if not teams:
            raise ValueError("Which team? You haven't saved any favourites yet.")
        return teams
    return None


async def how_did_we_do(http: httpx.AsyncClient, settings: Settings, name: str) -> screen.Shown:
    teams = _pick(settings, name) or [await live.find_team(http, settings, name)]
    teams = teams[:6]
    found = await asyncio.gather(*(live.events(http, t, "last") for t in teams), return_exceptions=True)
    sections, said = [], []
    for team, rows in zip(teams, found):
        rows = [] if isinstance(rows, Exception) else [e for e in rows if live.match(e)["score"]][:5]
        sections.append({"title": team["name"], "badge": team.get("badge", ""),
                         "matches": [live._card_row(live.match(e, team)) for e in rows],
                         "note": "" if rows else "No recent results found."})
        if rows:
            said.append(live.said_last(team, rows[0]))
    text = " ".join(said) or "I couldn't find any recent results."
    title = teams[0]["name"] if len(teams) == 1 else "How my teams did"
    card = screen.card("sports-matches", title, "sports-how-did", data={"sections": sections},
                       buttons=[{"label": "Next matches", "say": f"When do {teams[0]['name']} play next?"}])
    return screen.Shown(text, card)


async def summary(http: httpx.AsyncClient, settings: Settings) -> screen.Shown:
    teams = live.favourites(settings)[:6]
    jobs = [live.events(http, t, w) for t in teams for w in ("last", "next")]
    found = await asyncio.gather(*jobs, live.next_race(http), return_exceptions=True)
    sections, said = [], []
    for i, team in enumerate(teams):
        last, nxt = found[2 * i], found[2 * i + 1]
        last = [] if isinstance(last, Exception) else [e for e in last if live.match(e)["score"]][:1]
        nxt = [] if isinstance(nxt, Exception) else nxt[:1]
        sections.append({"title": team["name"], "badge": team.get("badge", ""),
                         "matches": [live._card_row(live.match(e, team)) for e in last + nxt],
                         "note": "" if last or nxt else "Nothing listed right now."})
        said += [live.said_last(team, e) for e in last] + [live.said_next(team, e) for e in nxt]
    race = found[-1]
    if race and not isinstance(race, Exception):
        words = live.race_words(*race)
        sections.append({"title": "Formula 1", "matches": [], "note": words})
        said.append(words)
    if not teams:
        said.insert(0, "You have no favourite teams yet, so here's just F1.")
    return screen.Shown(" ".join(said) or "I couldn't get any sport news right now.",
                        screen.card("sports-matches", "Sports summary", "sports-summary", data={"sections": sections},
                                    buttons=[{"label": "F1 standings", "say": "Show the F1 drivers' standings."},
                                             {"label": "My predictions", "say": "How are my score predictions doing?"}]))


# ---- Fixtures: reminders and predictions ----------------------------------------------------------

async def fixture(http: httpx.AsyncClient, settings: Settings, name: str, opponent: str = "") -> tuple[dict, dict]:
    """(team, next event), or the next one against opponent."""
    team = await live.find_team(http, settings, name)
    rows = await live.events(http, team, "next")
    want = hs.clean(opponent).lower()
    if want:
        rows = [e for e in rows if want in f"{e.get('strHomeTeam')} {e.get('strAwayTeam')}".lower()]
    if not rows:
        raise ValueError(f"I can't find {team['name']}'s next match" + (f" against {opponent}." if want else "."))
    return team, rows[0]


async def match_reminder(http: httpx.AsyncClient, settings: Settings, name: str, opponent: str,
                         minutes: int) -> screen.Shown:
    team, e = await fixture(http, settings, name, opponent)
    at = live.kickoff(e)
    if not at:
        raise ValueError("That match doesn't have a kick-off time yet.")
    minutes = min(max(int(minutes), 0), 7 * 24 * 60)
    when = (at - timedelta(minutes=minutes)).replace(tzinfo=None)
    row = live.match(e, team)
    said = reminders.add(settings, when.strftime("%Y-%m-%d %H:%M"),
                         f"{row['home']} v {row['away']} kicks off at {at:%H:%M}")
    card = screen.card("sports-matches", "Match reminder", "sports-reminder",
                       data={"sections": [{"title": f"Reminder {minutes} minutes before", "matches": [live._card_row(row)]}]})
    return screen.Shown(said, card)


def _outcome(h: int, a: int) -> int:
    return (h > a) - (h < a)


def points(pred: list, actual: list) -> int:
    if list(pred) == list(actual):
        return 3
    return 1 if _outcome(*pred) == _outcome(*actual) else 0


def _goals(value, what: str) -> int:
    try:
        n = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"How many goals for the {what} team?") from None
    if not 0 <= n <= 20:
        raise ValueError("Keep predictions between 0 and 20 goals.")
    return n


async def predict(http: httpx.AsyncClient, settings: Settings, name: str, opponent: str, home, away) -> screen.Shown:
    h, a = _goals(home, "home"), _goals(away, "away")
    team, e = await fixture(http, settings, name, opponent)
    row = live.match(e, team)
    saved = [p for p in hs.load(settings, PREDICTIONS, []) if isinstance(p, dict) and p.get("id") != row["id"]]
    if len(saved) >= MAX_PREDICTIONS:
        saved = saved[-(MAX_PREDICTIONS - 1):]
    saved.append({"id": row["id"], "home": row["home"], "away": row["away"], "at": row["at"], "pred": [h, a],
                  "made": live.now().isoformat(timespec="minutes")})
    hs.save(settings, PREDICTIONS, saved)
    return screen.Shown(f"Saved your prediction: {row['home']} {h}, {row['away']} {a}.", predictions_card(saved))


def predictions_card(saved: list[dict]) -> dict:
    rows = [[p.get("at", "")[:10], f"{p['home']} v {p['away']}", "{}-{}".format(*p["pred"]),
             "{}-{}".format(*p["actual"]) if p.get("actual") else "to play",
             str(p["points"]) if "points" in p else ""] for p in saved[-40:][::-1]]
    total = sum(p.get("points", 0) for p in saved)
    return screen.card("table", f"My predictions: {total} points", "sports-predictions",
                       columns=["Date", "Match", "Mine", "Result", "Pts"], rows=rows,
                       buttons=[{"label": "Check results", "say": "Score my football predictions."}])


async def _result(http: httpx.AsyncClient, event_id: str) -> list[int] | None:
    found = await fetch_json(http, f"{live.SPORTSDB}/lookupevent.php", "sports results", params={"id": event_id})
    events = (found or {}).get("events") or []
    if not events:
        return None
    h, a = live._int(events[0].get("intHomeScore")), live._int(events[0].get("intAwayScore"))
    return [h, a] if h is not None and a is not None else None


async def score_predictions(http: httpx.AsyncClient, settings: Settings) -> screen.Shown:
    saved = [p for p in hs.load(settings, PREDICTIONS, []) if isinstance(p, dict) and p.get("pred")]
    if not saved:
        return screen.Shown("You haven't made any predictions yet. Say 'I predict Arsenal 2 Chelsea 1'.",
                            predictions_card([]))
    due = [p for p in saved if "points" not in p and p.get("at")
           and datetime.fromisoformat(p["at"]) + timedelta(hours=2) < live.now()]
    found = await asyncio.gather(*(_result(http, p["id"]) for p in due[:20]), return_exceptions=True)
    newly = []
    for p, actual in zip(due, found):
        if actual and not isinstance(actual, Exception):
            p["actual"], p["points"] = actual, points(p["pred"], actual)
            newly.append(p)
    hs.save(settings, PREDICTIONS, saved)
    total = sum(p.get("points", 0) for p in saved)
    scored = sum("points" in p for p in saved)
    gained = sum(p["points"] for p in newly)
    text = (f"{len(newly)} new result{'s' if len(newly) != 1 else ''} in, worth {gained} points. " if newly else "")
    text += f"You have {total} points from {scored} scored prediction{'s' if scored != 1 else ''}."
    return screen.Shown(text, predictions_card(saved))


# ---- The tool -------------------------------------------------------------------------------------

def tool_definitions() -> list[dict]:
    return [{
        "name": "sports_my_teams",
        "description": "My favourite football teams. add_favourite / favourites / remove_favourite (set confirmed "
                       "true only after the user says yes). how_did_we_do: 'how did my team do?', latest results "
                       "for a team or all favourites. summary: sports summary pop-up of favourites' latest results "
                       "and next fixtures plus the next F1 race. match_reminder: remind me before my team's next "
                       "match (kick-off). predict: save my score prediction for a team's next match. "
                       "my_predictions: score my predictions against results (exact score 3, right result 1).",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["add_favourite", "favourites", "remove_favourite",
                                                      "how_did_we_do", "summary", "match_reminder", "predict",
                                                      "my_predictions"]},
                "team": {"type": "string", "description": "Team name. how_did_we_do: leave out for all favourites."},
                "opponent": {"type": "string", "description": "match_reminder/predict: the opponent, to pick a fixture."},
                "minutes_before": {"type": "integer", "description": "match_reminder: default 60."},
                "home_goals": {"type": "integer", "description": "predict: goals for the HOME side of the fixture."},
                "away_goals": {"type": "integer", "description": "predict: goals for the AWAY side."},
                "confirmed": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"sports_my_teams"}


async def run_tool(name: str, args: dict, settings: Settings, http: httpx.AsyncClient):
    action, team = args.get("action"), args.get("team") or ""
    if action == "add_favourite":
        return await add_favourite(http, settings, team)
    if action == "favourites":
        return list_favourites(settings)
    if action == "remove_favourite":
        return remove_favourite(settings, team, bool(args.get("confirmed")))
    if action == "how_did_we_do":
        return await how_did_we_do(http, settings, team)
    if action == "summary":
        return await summary(http, settings)
    if action == "match_reminder":
        return await match_reminder(http, settings, team, args.get("opponent") or "",
                                    60 if args.get("minutes_before") is None else args["minutes_before"])
    if action == "predict":
        return await predict(http, settings, team, args.get("opponent") or "", args.get("home_goals"),
                             args.get("away_goals"))
    if action == "my_predictions":
        return await score_predictions(http, settings)
    raise ValueError(f"Unknown my teams action: {action}")
