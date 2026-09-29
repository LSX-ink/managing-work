import asyncio
from datetime import datetime

import httpx
import pytest

import homestore
import screen
import tools
import watchlist_books
import watchlist_films
import watchlist_shows
import watchlist_social
from config import Settings


@pytest.fixture
def s(tmp_path, monkeypatch):
    monkeypatch.setattr(homestore, "now", lambda: datetime(2026, 9, 28, 20, 0))  # a Monday
    return Settings(memory_dir=str(tmp_path))


SHOW = {"id": 7, "name": "Slow Horses", "premiered": "2022-04-01", "genres": ["Drama", "Thriller"], "status": "Running",
        "runtime": 50, "image": {"medium": "https://img.test/sh.jpg"}, "network": {"name": "Apple TV+"}}
EPISODES = [{"season": 1, "number": n, "name": f"Ep {n}", "airdate": "2022-04-0%d" % n, "runtime": 45} for n in (1, 2)] + \
           [{"season": 2, "number": 1, "name": "New", "airdate": "2022-12-02", "runtime": 45}]


def handler(request: httpx.Request) -> httpx.Response:
    host, path, q = request.url.host, request.url.path, request.url.params
    if host == "openlibrary.org":
        return httpx.Response(200, json={"docs": [
            {"title": "Dead Lions", "author_name": ["Mick Herron"], "first_publish_year": 2013},
            {"title": "Slow Horses", "author_name": ["Mick Herron"], "first_publish_year": 2010},
            {"title": "Slow Horses", "author_name": ["Mick Herron"], "first_publish_year": 2011}]})
    assert host == "api.tvmaze.com"
    if path == "/search/shows":
        return httpx.Response(200, json=[{"score": 1, "show": SHOW}])
    if path in ("/singlesearch/shows", "/shows/7"):
        if q.get("q") == "nothing":
            return httpx.Response(404, json={})
        show = dict(SHOW)
        if q.get("embed") == "nextepisode":
            show["_embedded"] = {"nextepisode": {"season": 5, "number": 1, "name": "Return", "airdate": "2026-10-07",
                                                 "airtime": "21:00"}}
        return httpx.Response(200, json=show)
    if path == "/shows/7/episodes":
        return httpx.Response(200, json=EPISODES)
    if path == "/shows/7/cast":
        return httpx.Response(200, json=[{"person": {"name": "Gary Oldman"}, "character": {"name": "Jackson Lamb"}}])
    return httpx.Response(404, json={})


def films(s, **args):
    return watchlist_films.run_tool("watchlist", args, s)


def shows(s, **args):
    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            return await watchlist_shows.run_tool("watch_shows", args, s, http)
    return asyncio.run(go())


def books(s, **args):
    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            return await watchlist_books.run_tool("watch_books", args, s, http)
    return asyncio.run(go())


def social(s, **args):
    return watchlist_social.run_tool("watch_social", args, s)


def kinds(shown):
    assert shown.card["kind"] == "watchlist"
    return [x["type"] for x in shown.card["data"]["sections"]]


def test_registered_and_small():
    names = {t["name"] for t in tools.client_tool_definitions(Settings())}
    assert {"watchlist", "watch_shows", "watch_books", "watch_social"} <= names
    for module in (watchlist_films, watchlist_shows, watchlist_books, watchlist_social):
        for tool in module.tool_definitions():
            assert tool["input_schema"]["additionalProperties"] is False
    assert "watchlist" in screen.EXTRA_KINDS


def fill(s):
    films(s, action="watch_add", title="Heat", genre="Thriller", minutes=170, mood="tense")
    films(s, action="watch_add", title="Paddington", genre="family", minutes=95, mood="cosy", kids_safe=True)
    films(s, action="watch_add", title="Alien", genre="horror", minutes=117, mood="scary")


def test_add_list_and_duplicates(s):
    fill(s)
    assert "already on your watchlist" in films(s, action="watch_add", title="heat")
    shown = films(s, action="watch_list")
    assert kinds(shown) == ["gallery"] and len(shown.card["data"]["sections"][0]["tiles"]) == 3
    kids = films(s, action="watch_list", kids_safe=True)
    assert [t["title"] for t in kids.card["data"]["sections"][0]["tiles"]] == ["Paddington"]
    assert films(s, action="watch_list", genre="comedy").startswith("Nothing on your watchlist")


def test_watch_done_rating_and_history(s):
    fill(s)
    said = films(s, action="watch_done", title="heat", rating=5, review="Cracking shootout", date="2026-08-10")
    assert said == "Marked Heat as watched, 5 stars. That's 1 title watched this year."
    films(s, action="watch_done", title="Jaws", rating=4, genre="thriller", date="2026-09-01")  # not on the list yet
    with pytest.raises(ValueError, match="1 to 5"):
        films(s, action="watch_done", title="Alien", rating=9)
    shown = films(s, action="history")
    assert kinds(shown) == ["stats", "chart", "chart"]
    stats = {x["label"]: x["value"] for x in shown.card["data"]["sections"][0]["items"]}
    assert stats["Watched"] == "2" and stats["Average rating"] == "4.5/5"
    assert shown.card["data"]["sections"][1]["chart"]["labels"] == ["2026-08", "2026-09"]
    assert films(s, action="watch_list", kind="film").card["data"]["sections"][0]["tiles"][0]["title"] == "Paddington"


def test_history_empty(s):
    assert films(s, action="history").startswith("You haven't marked anything")


def test_tonight_pick_filters(s):
    fill(s)
    shown = films(s, action="tonight_pick", mood="scary")
    assert shown == "Tonight, how about Alien?" and shown.card["kind"] == "watchlist"
    shown = films(s, action="tonight_pick", who=["me", "the kids"])
    assert "Paddington" in shown and "for me, the kids" in shown
    short = films(s, action="tonight_pick", max_minutes=100)
    assert "Paddington" in short
    assert "Nothing is tagged sad" in films(s, action="tonight_pick", mood="sad", max_minutes=120)
    assert films(s, action="tonight_pick", max_minutes=30).startswith("Nothing on your watchlist fits")
    assert "Paddington" in films(s, action="tonight_pick", who=["kids"], mood="scary")


def test_top_picks_and_recommend(s):
    assert films(s, action="top_picks").startswith("Rate a few things first")
    assert films(s, action="recommend").startswith("Rate a few things first")
    fill(s)
    films(s, action="watch_done", title="Heat", rating=5)
    films(s, action="watch_done", title="Alien", rating=4)
    films(s, action="watch_done", title="Paddington", rating=3)
    top = films(s, action="top_picks")
    assert top == "Your top pick is Heat, 5 stars." and top.card["data"]["sections"][0]["rows"][0][0] == "family"
    assert films(s, action="top_picks", genre="horror") == "Your top pick for horror is Alien, 4 stars."
    books(s, action="book_finish", title="Dune", rating=5)
    rec = films(s, action="recommend")
    assert rec.startswith("Their top rated: Heat (film, thriller, 5 stars); Dune (book, 5 stars)")
    assert "suggest three or four similar" in rec and rec.card["kind"] == "watchlist"
    assert "Dune" not in films(s, action="recommend", kind="film")
    assert "similar books" in films(s, action="recommend", kind="book")


def test_rewatch_kids_flag_remove(s):
    fill(s)
    with pytest.raises(ValueError, match="can't find"):
        films(s, action="rewatch", title="Heat")  # not watched yet
    films(s, action="watch_done", title="Heat", rating=5)
    assert films(s, action="rewatch", title="Heat") == "Added Heat to your rewatch list."
    assert kinds(films(s, action="rewatch")) == ["gallery"]
    assert films(s, action="kids_flag", title="Alien") == "Alien is now marked kids-safe."
    assert films(s, action="kids_flag", title="Alien", kids_safe=False) == "Alien is now marked not for kids."
    assert films(s, action="watch_remove", title="Alien").startswith("Ask the user to confirm")
    assert films(s, action="watch_remove", title="Alien", confirmed=True) == "Removed Alien."
    with pytest.raises(ValueError):
        films(s, action="nope")


def test_show_progress_and_status(s):
    assert shows(s, action="show_status").startswith("You're not following")
    said = shows(s, action="show_progress", title="Slow Horses", season=2, episode=3)
    assert said.startswith("Slow Horses: you're on season 2, episode 3. Next up is episode 4.")
    assert kinds(said) == ["gallery", "table"] and said.card["data"]["sections"][1]["rows"] == [["Slow Horses", "S2 E3", "S2 E4"]]
    assert shows(s, action="episode_done", title="slow").startswith("Done, Slow Horses season 2, episode 4.")
    assert shows(s, action="show_status").card["kind"] == "watchlist"
    with pytest.raises(ValueError, match="Add it first"):
        shows(s, action="episode_done", title="Unknown")


def test_tv_search_add_episodes_next_cast(s):
    found = shows(s, action="tv_search", query="slow horses")
    tile = found.card["data"]["sections"][0]["tiles"][0]
    assert tile["say"] == "Add the TV show Slow Horses (TVmaze id 7) to my watchlist." and tile["image"] == "https://img.test/sh.jpg"
    assert shows(s, action="tv_add", tvmaze_id=7) == "Added Slow Horses to your watchlist with its TVmaze details."
    assert "already on your watchlist" in shows(s, action="tv_add", tvmaze_id=7)
    eps = shows(s, action="tv_episodes", title="Slow Horses", season=1)
    assert eps.card["data"]["sections"][0]["rows"][0][:2] == ["E1", "Ep 1"] and "2 episodes" in eps
    shows(s, action="show_progress", title="Slow Horses", season=1, episode=2)
    assert shows(s, action="episode_done", title="Slow Horses").startswith("Done, Slow Horses season 2, episode 1.")
    nxt = shows(s, action="tv_next_episode", title="Slow Horses")
    assert "season 5, episode 1, Return, on Wednesday 7 October at 21:00" in nxt and nxt.card["kind"] == "watchlist"
    assert "Gary Oldman" in shows(s, action="tv_cast", title="Slow Horses")
    with pytest.raises(ValueError, match="doesn't know a show"):
        shows(s, action="tv_next_episode", title="nothing")
    with pytest.raises(ValueError):
        shows(s, action="nope")


def test_books_progress_finish_and_goal(s):
    assert books(s, action="reading_now").startswith("You're not reading")
    assert books(s, action="book_add", title="Dune", author="Frank Herbert", pages=600).startswith("Added Dune by Frank Herbert")
    assert "already on" in books(s, action="book_add", title="dune")
    shown = books(s, action="book_progress", title="Dune", page=150)
    row = shown.card["data"]["sections"][0]["rows"][0]
    assert shown.card["kind"] == "watchlist" and row["note"] == "page 150 of 600 (25%)" and "450 to go" in shown
    with pytest.raises(ValueError, match="only has 600"):
        books(s, action="book_progress", title="Dune", page=700)
    assert kinds(books(s, action="reading_now")) == ["meters"]
    assert books(s, action="goal_show").startswith("You haven't set")
    goal = books(s, action="goal_set", goal=12)
    assert kinds(goal) == ["ring"] and goal.card["data"]["sections"][0]["max"] == 12
    said = books(s, action="book_finish", title="Dune", rating=5, review="Epic")
    assert said == "Finished Dune by Frank Herbert, 5 stars. That's 1 book this year of your 12 goal."
    shown = books(s, action="goal_show")
    assert shown.card["data"]["sections"][0]["value"] == 1 and kinds(shown) == ["ring", "list"]


def test_streak_and_log(s):
    assert books(s, action="reading_streak").startswith("No reading logged")
    books(s, action="log_reading", pages=10, date="2026-09-26")
    books(s, action="log_reading", pages=10, date="yesterday")
    shown = books(s, action="log_reading", pages=5)
    assert shown.startswith("Logged 5 pages. Reading streak: 3 days. Your longest is 3.")
    assert kinds(shown) == ["stats", "chart"]
    books(s, action="log_reading", pages=5, date="2026-09-20")
    assert "Your longest is 3" in books(s, action="reading_streak")


def test_notes_and_quotes(s):
    books(s, action="book_add", title="Dune")
    assert books(s, action="book_note", title="Dune", text="Spice is oil", page=10) == "Saved that note for Dune. It has 1 note."
    assert books(s, action="book_quote", title="Dune", text="Fear is the mind-killer", page=12).endswith("1 quote.")
    shown = books(s, action="notes_show", title="Dune")
    assert kinds(shown) == ["list", "list"] and "(p. 12)" in shown.card["data"]["sections"][1]["items"][0]["label"]
    assert "Fear is the mind-killer" in books(s, action="notes_show")
    with pytest.raises(ValueError, match="can't find a book"):
        books(s, action="book_note", title="Nope", text="x")


def test_series_order(s):
    shown = books(s, action="series_order", query="Slow Horses")
    rows = shown.card["data"]["sections"][0]["rows"]
    assert [r[1] for r in rows] == ["Slow Horses", "Dead Lions"] and rows[0][3] == "2010" and shown.card["kind"] == "watchlist"


def test_lending(s):
    assert social(s, action="lend_list") == "Nothing is lent out right now."
    assert social(s, action="lend", item="Dune", to="Sam", date="2026-08-01") == "Noted: Dune is with Sam since Saturday 1 August."
    social(s, action="lend", item="Alien DVD", to="Priya", date="2026-09-20")
    shown = social(s, action="lend_list")
    assert "1 out for over a month" in shown and shown.card["data"]["sections"][0]["rows"][0][3] == "58 days (overdue)"
    assert social(s, action="lend_return", to="sam") == "Great, Dune is back from Sam."
    assert social(s, action="lend_return", item="Dune") == "I've nothing lent out that matches that."
    with pytest.raises(ValueError, match="Which item"):
        social(s, action="lend_return")


def test_book_club(s):
    assert social(s, action="club_show").startswith("No book club planned")
    shown = social(s, action="club_set", title="Rebecca", date="2026-10-09", place="Jo's")
    assert "Book club: Rebecca, meeting Friday 9 October." in shown and shown.card["kind"] == "watchlist"
    ask = social(s, action="club_questions")
    assert ask.startswith("Write six thoughtful discussion questions") and not hasattr(ask, "card")
    saved = social(s, action="club_questions", questions=["Who is the narrator?", "Was Maxim guilty?"])
    assert kinds(saved) == ["table", "list"] and len(saved.card["data"]["sections"][1]["items"]) == 2
    social(s, action="club_set", title="Emma")
    assert kinds(social(s, action="club_show")) == ["table"]  # new book, questions cleared


def test_film_night(s):
    assert social(s, action="night_show").startswith("No film night planned")
    shown = social(s, action="night_plan", title="Alien", date="saturday", time="8pm", who=["Sam", "Priya"], snacks=["popcorn", "pizza"])
    assert "Film night planned: Alien on Saturday 3 October at 8pm." in shown
    assert shown.card["data"]["sections"][1]["items"][0]["say"] == "Add popcorn to my shopping list."
    assert "Next film night: Alien" in social(s, action="night_show")
    with pytest.raises(ValueError):
        social(s, action="nope")
