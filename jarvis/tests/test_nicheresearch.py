import asyncio

import httpx
import pytest

import nicheresearch_audience
import nicheresearch_market
import nicheresearch_plan
import nicheresearch_score
import nicheresearch_store as nr
import screen
import tools
from config import Settings


@pytest.fixture
def s(tmp_path):
    return Settings(memory_dir=str(tmp_path))


def call(mod, name):
    def run(s, action, **a):
        out = mod.run_tool(name, {"action": action, **a}, s)
        return asyncio.run(out) if asyncio.iscoroutine(out) else out
    return run


score = call(nicheresearch_score, "nicheresearch_score")
aud = call(nicheresearch_audience, "nicheresearch_audience")
mkt = call(nicheresearch_market, "nicheresearch_market")
plan = call(nicheresearch_plan, "nicheresearch_plan")
RATE = dict(demand=4, competition=3, passion=5, skill=3, profit=4, evergreen=4)


def kind(shown):
    assert isinstance(shown, screen.Shown)
    return shown.card["kind"]


def seeded(s):
    score(s, "add_niche", name="Sourdough baking", note="home bakers")
    score(s, "rate_niche", niche="Sourdough", **RATE)
    return s


def test_registered_and_through_tools(s):
    names = {t["name"] for t in tools.client_tool_definitions(Settings())}
    assert {"nicheresearch_score", "nicheresearch_audience", "nicheresearch_market", "nicheresearch_plan"} <= names
    for k in (nr.SHEET, nr.RADAR, nr.SWOT, nr.CHECK, nr.BOARD):
        assert k in screen.EXTRA_KINDS
    out = asyncio.run(tools._run_tool("nicheresearch_score", {"action": "add_niche", "name": "Chess"}, s, None, None))
    assert "Added niche 1" in out


def test_scoring(s):
    assert "Added niche 1" in score(s, "add_niche", name="Sourdough baking")
    with pytest.raises(ValueError):
        score(s, "add_niche", name="sourdough baking")
    assert "Still to rate" in score(s, "rate_niche", niche="1", demand=5)
    with pytest.raises(ValueError):
        score(s, "rate_niche", niche="1", demand=9)
    with pytest.raises(ValueError):
        score(s, "rate_niche", niche="1")
    out = score(s, "rate_niche", niche="1", **{**RATE, "demand": 5})
    assert "out of 100" in out
    lst = score(s, "list_niches")
    assert kind(lst) == "list" and lst.card["items"][0]["say"]
    assert "demand 5" in score(s, "set_weights", weight_demand=5)
    with pytest.raises(ValueError):
        score(s, "set_weights")
    assert "demand 3" in score(s, "set_weights", reset=True)
    with pytest.raises(ValueError):
        score(s, "set_weights", weight_demand=0, weight_competition=0, weight_passion=0, weight_skill=0, weight_profit=0, weight_evergreen=0)
    assert kind(score(s, "explain_criteria")) == nr.SHEET
    assert "Updated" in score(s, "edit_niche", niche="1", name="Sourdough", note="x")


def test_ranking_radar_compare_weak(s):
    with pytest.raises(ValueError):
        score(s, "ranked_table")
    seeded(s)
    score(s, "add_niche", name="Chess")
    score(s, "rate_niche", niche="Chess", demand=2, competition=2, passion=3, skill=4, profit=2, evergreen=5)
    rank = score(s, "ranked_table")
    assert kind(rank) == "table" and rank.card["rows"][0][1] == "Sourdough baking" and len(rank.card["rows"]) == 2
    rad = score(s, "radar")
    assert kind(rad) == nr.RADAR and len(rad.card["data"]["series"]) == 2 and len(rad.card["data"]["axes"]) == 6
    assert len(score(s, "radar", niche="Chess").card["data"]["series"]) == 1
    cmp_ = score(s, "compare_niches", niches="Sourdough, Chess")
    assert kind(cmp_) == "table" and cmp_.card["columns"] == ["Measure", "Sourdough baking", "Chess"]
    with pytest.raises(ValueError):
        score(s, "compare_niches", niches="Chess")
    weak = score(s, "weakest_points", niche="Chess")
    assert kind(weak) == nr.SHEET and "Weak spots" in weak.card["title"]
    assert "confirm" in score(s, "remove_niche", niche="Chess")
    assert "Removed" in score(s, "remove_niche", niche="Chess", confirmed=True)


def test_persona_and_pains(s):
    seeded(s)
    with pytest.raises(ValueError):
        aud(s, "persona_show")
    with pytest.raises(ValueError):
        aud(s, "persona_save")
    assert "Still blank" in aud(s, "persona_save", persona_name="Busy Beth", goals="fresh bread", frustrations="flat loaves")
    shown = aud(s, "persona_show")
    assert kind(shown) == nr.SHEET and shown.card["data"]["headline"] == "Busy Beth"
    assert kind(aud(s, "interview_questions")) == nr.SHEET
    assert kind(aud(s, "where_to_find")) == nr.SHEET
    with pytest.raises(ValueError):
        aud(s, "pain_list")
    aud(s, "pain_add", text="Loaves come out flat", intensity=5, frequency=4, source="a forum thread")
    aud(s, "pain_add", text="Starter smells odd", intensity=2, frequency=2)
    lst = aud(s, "pain_list")
    assert kind(lst) == "list" and lst.card["items"][0]["label"].startswith("1. Loaves") and lst.card["items"][0]["say"]
    assert "Updated" in aud(s, "pain_update", pain="2", intensity=4)
    ideas = aud(s, "pain_to_ideas")
    assert kind(ideas) == "list" and len(ideas.card["items"]) == 7 and "flat" in ideas.card["items"][0]["label"]
    assert "confirm" in aud(s, "pain_remove", pain="2")
    assert "Removed" in aud(s, "pain_remove", pain="2", confirmed=True)
    survey = aud(s, "survey_draft")
    assert kind(survey) == nr.SHEET and "Loaves come out flat" in str(survey.card["data"])


def test_brainstorm_and_gap(s):
    out = aud(s, "keyword_brainstorm", seeds="sourdough, rye")
    assert kind(out) == "list" and "not search volumes" in out and len(out.card["items"]) <= 40
    assert any(i["label"] == "sourdough for beginners" for i in out.card["items"])
    with pytest.raises(ValueError):
        aud(s, "keyword_brainstorm")
    seeded(s)
    assert kind(aud(s, "keyword_brainstorm")) == "list"
    with pytest.raises(ValueError):
        aud(s, "content_gap")
    gap = aud(s, "content_gap", competitor_topics="How to feed a starter; Sourdough for beginners; Baking in a Dutch oven",
              my_topics="feed your starter, sourdough for beginners")
    assert kind(gap) == nr.SHEET
    text = str(gap.card["data"])
    assert "Baking in a Dutch oven" in text and "1 topics competitors cover" in gap
    assert "topics" in aud(s, "add_topic", topic="scoring loaves")


def test_competitors_prices_swot(s):
    seeded(s)
    with pytest.raises(ValueError):
        mkt(s, "competitor_list")
    assert "Added competitor 1" in mkt(s, "competitor_add", name="Bake Club", strengths="big list", weaknesses="dull videos", prices="19 a month", topics="starter, oven")
    mkt(s, "competitor_add", name="Loaf Lab", weaknesses="no beginners")
    assert "Updated" in mkt(s, "competitor_update", competitor="Loaf", strengths="lovely photos")
    lst = mkt(s, "competitor_list")
    assert kind(lst) == "table" and len(lst.card["rows"]) == 2
    cmp_ = mkt(s, "competitor_compare")
    assert kind(cmp_) == nr.SHEET and "dull videos" in str(cmp_.card["data"])
    assert "confirm" in mkt(s, "competitor_remove", competitor="Loaf")
    assert "Removed" in mkt(s, "competitor_remove", competitor="Loaf", confirmed=True)
    with pytest.raises(ValueError):
        mkt(s, "competitor_compare")
    with pytest.raises(ValueError):
        mkt(s, "price_list")
    with pytest.raises(ValueError):
        mkt(s, "price_stats")
    mkt(s, "price_add", item="Starter course", price="£49", seller="A")
    mkt(s, "price_add", item="Ebook", price=9, seller="B")
    mkt(s, "price_add", item="Workshop", price=120)
    assert kind(mkt(s, "price_list")) == "table"
    stats = mkt(s, "price_stats")
    assert kind(stats) == "chart" and "middle £49" in stats
    pos = mkt(s, "price_position", my_price=60)
    assert kind(pos) == nr.SHEET and "middle" in pos
    with pytest.raises(ValueError):
        mkt(s, "price_add", item="x", price="abc")
    assert "confirm" in mkt(s, "price_remove", price_ref="Ebook")
    assert "Removed" in mkt(s, "price_remove", price_ref="Ebook", confirmed=True)
    with pytest.raises(ValueError):
        mkt(s, "swot_show")
    assert "strengths" in mkt(s, "swot_add", quadrant="strength", text="I bake daily, know starters")
    mkt(s, "swot_add", quadrant="threat", text="cheap courses")
    mkt(s, "swot_add", quadrant="opportunity", text="no beginner videos")
    with pytest.raises(ValueError):
        mkt(s, "swot_add", quadrant="luck", text="x")
    swot = mkt(s, "swot_show")
    assert kind(swot) == nr.SWOT and len(swot.card["data"]["boxes"]) == 4 and swot.card["data"]["boxes"][0]["items"][0] == "I bake daily"
    assert kind(mkt(s, "swot_prompts")) == nr.SHEET
    assert len(mkt(s, "swot_prompts", quadrant="threat").card["data"]["sections"]) == 1
    assert "confirm" in mkt(s, "swot_clear")
    assert "Cleared" in mkt(s, "swot_clear", confirmed=True)


def test_interest_over_time(s):
    seen = []

    def handler(request):
        seen.append(request)
        if "Missing" in str(request.url):
            return httpx.Response(404)
        items = [{"timestamp": f"2026{m:02d}0100", "views": 100 + m * 20} for m in range(1, 10)]
        return httpx.Response(200, json={"items": items})

    async def go(topic):
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            return await nicheresearch_market.run_tool("nicheresearch_market", {"action": "interest_over_time", "topic": topic}, s, http)

    out = asyncio.run(go("Sourdough"))
    assert kind(out) == "chart" and "rough interest signal only" in out and "rising" in out
    assert "Sourdough" in str(seen[0].url) and seen[0].url.host == "wikimedia.org" and "batch" not in str(seen[0].url)
    assert "personal" not in str(seen[0].headers)
    with pytest.raises(ValueError, match="no page"):
        asyncio.run(go("Missing thing"))

    def boom(request):
        raise httpx.ConnectError("down")

    async def down():
        async with httpx.AsyncClient(transport=httpx.MockTransport(boom)) as http:
            return await nicheresearch_market.run_tool("nicheresearch_market", {"action": "interest_over_time", "topic": "x"}, s, http)

    with pytest.raises(ValueError, match="couldn't reach"):
        asyncio.run(down())


def test_positioning_angles_canvas_plan(s):
    seeded(s)
    with pytest.raises(ValueError, match="still need"):
        plan(s, "positioning_make")
    aud(s, "pain_add", text="flat loaves", intensity=5, frequency=5)
    mkt(s, "competitor_add", name="Bake Club")
    out = plan(s, "positioning_make", audience="busy parents", benefit="bake tall loaves in 30 minutes", difference="it needs no kneading",
              angle="Bread without the fuss")
    assert kind(out) == nr.SHEET
    text = str(out.card["data"])
    assert "For busy parents who struggle with flat loaves" in text and "Unlike Bake Club, it needs no kneading." in text
    ang = plan(s, "angle_ideas", audience="busy parents", enemy="kneading")
    assert kind(ang) == "list" and len(ang.card["items"]) == 8 and "busy parents" in ang.card["items"][0]["label"]
    with pytest.raises(ValueError):
        plan(s, "canvas_set")
    assert "Saved 2" in plan(s, "canvas_set", revenue="Workshops", costs="Flour")
    cv = plan(s, "canvas_show")
    assert kind(cv) == nr.SHEET and "flat loaves" in str(cv.card["data"]) and cv.card["buttons"]
    f = plan(s, "canvas_save_file")
    assert kind(f) == "file" and (s.memory_dir and f.card["name"].startswith("Lean canvas"))
    p = plan(s, "business_plan_file")
    assert kind(p) == "file"
    body = (nr.memory.root(s) / nr.FOLDER / p.card["name"]).read_text(encoding="utf-8")
    assert "GOV.UK" in body and "flat loaves" in body and "Fit score" in body


def test_experiments_smoke_decision_journal(s):
    seeded(s)
    with pytest.raises(ValueError):
        plan(s, "experiment_list")
    assert kind(plan(s, "experiment_template")) == nr.SHEET
    assert "Tip" in plan(s, "experiment_add", hypothesis="Parents will join a waitlist")
    plan(s, "experiment_add", hypothesis="Bakers pay 5 pounds", test="mock page", metric="4 of 20 say yes")
    assert "keep" in plan(s, "experiment_update", experiment="1", result="6 of 20", decision="keep")
    with pytest.raises(ValueError):
        plan(s, "experiment_update", experiment="1", decision="maybe")
    board = plan(s, "experiment_list")
    assert kind(board) == nr.BOARD and [len(c["cards"]) for c in board.card["data"]["columns"]] == [1, 1, 0, 0]
    assert "confirm" in plan(s, "experiment_remove", experiment="2")
    assert "Removed" in plan(s, "experiment_remove", experiment="2", confirmed=True)

    sm = plan(s, "smoke_checklist")
    assert kind(sm) == nr.CHECK and len(sm.card["data"]["items"]) == 8 and "nothing" in sm.card["data"]["note"].lower()
    assert "done" in plan(s, "smoke_tick", step=2)
    assert plan(s, "smoke_checklist").card["data"]["items"][1]["status"] == "ok"
    assert "not done" in plan(s, "smoke_tick", step=2)
    with pytest.raises(ValueError):
        plan(s, "smoke_tick", step=99)

    dec = plan(s, "decision_checklist")
    assert kind(dec) == nr.CHECK and "Answer every" in dec
    with pytest.raises(ValueError):
        plan(s, "decision_answer", question=1, answer="perhaps")
    for i in range(1, 11):
        plan(s, "decision_answer", question=i, answer="yes")
    assert "go, with a small first step" in plan(s, "decision_checklist")
    for i in (1, 2, 3):
        plan(s, "decision_answer", question=i, answer="no")
    assert "not yet" in plan(s, "decision_checklist")
    with pytest.raises(ValueError):
        plan(s, "verdict_show")
    with pytest.raises(ValueError):
        plan(s, "verdict_save", verdict="maybe")
    assert "go" in plan(s, "verdict_save", verdict="go", reason="Six of twenty said yes")
    v = plan(s, "verdict_show")
    assert kind(v) == nr.SHEET and v.card["data"]["headline"] == "GO"

    with pytest.raises(ValueError):
        plan(s, "journal_list")
    plan(s, "journal_add", lesson="Ask about the past, not the future", niche="Sourdough")
    plan(s, "journal_add", lesson="Price tests beat opinions")
    lst = plan(s, "journal_list")
    assert kind(lst) == "list" and len(lst.card["items"]) == 2
    assert len(plan(s, "journal_list", niche="Sourdough").card["items"]) == 1
    assert "confirm" in plan(s, "journal_remove", entry="1")
    assert "Removed" in plan(s, "journal_remove", entry="1", confirmed=True)


def test_next_step_progress(s):
    seeded(s)
    first = plan(s, "next_step")
    assert kind(first) == nr.CHECK and "ideal person" in first
    assert first.card["data"]["items"][0]["status"] == "ok" and first.card["data"]["items"][1]["status"] == "todo"
    aud(s, "persona_save", persona_name="Beth")
    assert "1 of" not in plan(s, "next_step").card["data"]["headline"]


def test_bad_action_and_no_niche(s):
    with pytest.raises(ValueError):
        score(s, "nope")
    with pytest.raises(ValueError, match="No niches"):
        aud(s, "persona_show")
    score(s, "add_niche", name="A")
    score(s, "add_niche", name="B")
    with pytest.raises(ValueError, match="Which niche"):
        aud(s, "pain_list")
