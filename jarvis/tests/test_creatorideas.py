import asyncio
from datetime import datetime

import httpx
import pytest

import creator_hooks
import creator_ideas
import creator_plan
import creator_scripts
import screen
import tools
from config import Settings

NOW = datetime(2026, 9, 29, 10, 0)


@pytest.fixture
def s(tmp_path):
    return Settings(memory_dir=str(tmp_path))


def ideas(s, **a):
    return creator_ideas.run_tool("creator_ideas", a, s, now=NOW)


def hooks(s, **a):
    return creator_hooks.run_tool("creator_hooks", a, s, now=NOW)


def scripts(s, **a):
    return creator_scripts.run_tool("creator_scripts", a, s)


def plan(s, later=None, **a):
    return creator_plan.run_tool("creator_plan", a, s, now=later or NOW)


def is_card(x, kind):
    return isinstance(x, screen.Shown) and x.card["kind"] == kind


def test_pillars(s):
    assert "2 pillars" in ideas(s, action="pillar_add", account="mindglitch.fyi", pillars=["psychology", "dark history"])
    assert is_card(ideas(s, action="pillar_list"), "table")
    ideas(s, action="pillar_remove", account="mindglitch.fyi", text="psychology", confirmed=True)
    assert ideas(s, action="pillar_list").card["rows"][0][1] == "dark history"


def test_idea_bank(s):
    assert "idea 1" in ideas(s, action="idea_add", text="Why we sigh", tags=["psych"], account="mindglitch.fyi")
    assert "Saved 2" in ideas(s, action="idea_save", ideas=["Ghost ship", "Lost city"])
    assert is_card(ideas(s, action="idea_list"), "table")
    assert len(ideas(s, action="idea_search", query="ghost").card["rows"]) == 1
    assert len(ideas(s, action="idea_search", tag="psych").card["rows"]) == 1
    assert "scripted" in ideas(s, action="idea_status", id=2, status="scripted")
    assert "winner" in ideas(s, action="winner_mark", id=1)
    assert "confirm" in ideas(s, action="idea_remove", id=3)
    assert "Removed" in ideas(s, action="idea_remove", id=3, confirmed=True)
    with pytest.raises(ValueError):
        ideas(s, action="idea_status", id=99, status="ready")


def test_generate_and_board(s):
    ideas(s, action="pillar_add", account="lowkey.lore", pillars=["folklore"])
    ideas(s, action="idea_add", text="The bell that rang alone")
    ideas(s, action="winner_mark", id=1)
    text = ideas(s, action="idea_generate", niche="lowkey.lore", count=5)
    assert "folklore" in text and "bell" in text
    ideas(s, action="idea_add", text="Fresh idea")
    shown = ideas(s, action="board")
    assert shown.card["kind"] == "creator-board"
    assert shown.card["data"]["columns"][0]["items"][0]["say"].startswith("Move idea")


def test_hooks(s):
    assert is_card(hooks(s, action="hook_list"), "table") or is_card(hooks(s, action="hook_list"), "list")
    filled = hooks(s, action="hook_fill", topic="sleep", hook_type="POV", number="5")
    assert filled.card["kind"] == "list" and "sleep" in filled.card["items"][0]["label"]
    score = hooks(s, action="hook_score", text="Nobody tells you the secret about sleep")
    assert "out of 100" in score and score.card["kind"] == "table"
    assert "Saved" in hooks(s, action="hook_save", text="Why do we dream?")
    assert is_card(hooks(s, action="hook_saved"), "list")


def test_ctas_and_checks(s):
    assert is_card(hooks(s, action="cta_list", goal="follow"), "table")
    assert "Added" in hooks(s, action="cta_add", goal="save", text="Save it for later, friend.")
    assert any("yours" in r[0] for r in hooks(s, action="cta_list").card["rows"])
    safe = hooks(s, action="text_check", text="A very long line of on-screen text that will not fit at all", kind="onscreen")
    assert safe.card["kind"] == "creator-safe" and safe.card["data"]["issues"]
    assert is_card(hooks(s, action="risky_list"), "table")
    risky = hooks(s, action="risky_check", text="This miracle cure is guaranteed")
    assert is_card(risky, "table") and "check the platform" in risky
    assert "Nothing" in hooks(s, action="risky_check", text="A calm walk in the park")


def test_hashtags_and_caption(s):
    assert "1 broad" in scripts(s, action="hashtag_save", niche="psychology", broad=["fyp"], niche_tags=["mindtricks", "psych"],
                                branded=["mindglitch"])
    assert is_card(scripts(s, action="hashtag_show"), "table")
    checked = scripts(s, action="hashtag_check", tags="#fyp #mindtricks #psych #mindglitch")
    assert "4 hashtags" in checked
    assert is_card(scripts(s, action="hashtag_check", niche="psychology"), "table")
    cap = scripts(s, action="caption_scaffold", topic="why we yawn", niche="psychology", goal="share")
    assert "#fyp" in cap
    assert "confirm" in scripts(s, action="hashtag_remove", niche="psychology")
    scripts(s, action="hashtag_remove", niche="psychology", confirmed=True)
    assert "any hashtag" in scripts(s, action="hashtag_show")


def test_outline_pacing_check(s):
    shown = scripts(s, action="outline", template="listicle", seconds=60)
    assert is_card(shown, "table") and len(shown.card["rows"]) == 7
    assert is_card(scripts(s, action="outline_list"), "list")
    assert "150 words" in scripts(s, action="pacing", seconds=60)
    assert "seconds" in scripts(s, action="pacing", text="one two three four five six")
    check = scripts(s, action="script_check", text="Short one. " * 5)
    assert is_card(check, "table")
    with pytest.raises(ValueError):
        scripts(s, action="outline", template="nonsense")


def test_series_trends_swipe(s):
    shown = plan(s, action="series_new", name="Birth Months")
    assert shown.card["kind"] == "list" and len(shown.card["items"]) == 12
    done = plan(s, action="series_done", name="Birth Months", episode=1)
    assert "January is done" in done and done.card["items"][0]["done"]
    assert is_card(plan(s, action="series_show", name="Birth Months"), "list")
    assert is_card(plan(s, action="series_list"), "table")
    assert "confirm" in plan(s, action="series_remove", name="Birth Months")
    plan(s, action="series_remove", name="Birth Months", confirmed=True)
    assert "haven't" in plan(s, action="series_list")
    plan(s, action="trend_add", text="slow zoom format", kind="format")
    assert is_card(plan(s, action="trend_list"), "table")
    plan(s, action="trend_add", text="second note")
    assert "Removed" in plan(s, action="trend_remove", number=1)
    assert "No current" in plan(s, later=datetime(2026, 10, 30), action="trend_list")
    plan(s, action="swipe_add", title="Ghost ship story", why="strong hook", tags=["history"])
    assert is_card(plan(s, action="swipe_list", query="ghost"), "table")
    assert "confirm" in plan(s, action="swipe_remove", number=1)
    assert "Removed" in plan(s, action="swipe_remove", number=1, confirmed=True)


def test_comment_reply_and_angles(s):
    ideas(s, action="pillar_add", account="mindglitch.fyi", pillars=["psychology"])
    assert "Write three" in plan(s, action="comment_reply", comment="Is this real?", account="mindglitch.fyi")
    text = plan(s, action="trend_angles", keywords=["sleep", "dreams"], account="mindglitch.fyi")
    assert "sleep" in text and "psychology" in text and "do not claim" in text


def test_registered_and_run_through_tools(s):
    for mod in (creator_ideas, creator_hooks, creator_scripts, creator_plan):
        assert mod in tools.ABILITIES
        assert all(d["input_schema"]["additionalProperties"] is False for d in mod.tool_definitions())
    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200))) as http:
            return await tools._run_tool("creator_scripts", {"action": "pacing", "seconds": 30}, s, http)
    assert "words" in asyncio.run(go())
