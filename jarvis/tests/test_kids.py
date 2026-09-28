from datetime import datetime, timedelta

import pytest

import homestore
import kids_day
import kids_fun
import kids_logs
import kids_rewards
import screen
import tools
from config import Settings

NOW = datetime(2026, 9, 28, 18, 0)  # a Monday


@pytest.fixture
def s(tmp_path, monkeypatch):
    monkeypatch.setattr(homestore, "now", lambda: NOW)
    return Settings(memory_dir=str(tmp_path))


def rewards(s, **args):
    return kids_rewards.run_tool("kids_rewards", args, s)


def logs(s, **args):
    return kids_logs.run_tool("kids_logs", args, s)


def day(s, **args):
    return kids_day.run_tool("kids_day", args, s)


def fun(s, **args):
    return kids_fun.run_tool("kids_fun", args, s)


def test_registered_and_small():
    names = {t["name"] for t in tools.client_tool_definitions(Settings())}
    mods = (kids_rewards, kids_logs, kids_day, kids_fun)
    for module in mods:
        assert module in tools.ABILITIES
        (tool,) = module.tool_definitions()
        assert tool["name"] in names and tool["input_schema"]["additionalProperties"] is False


# ---- sticker chart and rewards -------------------------------------------------------------------

def test_star_goals_and_add_star(s):
    out = rewards(s, action="star_goals", child="Mia", items=["brushing teeth", "tidying up"])
    assert out == "Mia's sticker chart goals: brushing teeth, tidying up."
    out = rewards(s, action="add_star", child="mia", goal="brushing teeth")
    assert isinstance(out, screen.Shown) and out.startswith("A star for Mia for brushing teeth!")
    assert out.card["kind"] == "kids-stars"
    row = next(r for r in out.card["data"]["grid"] if r["goal"] == "brushing teeth")
    assert row["cells"][NOW.weekday()] == 1
    out = rewards(s, action="add_star", child="Mia", goal="tidying up", count=2)
    assert "2 stars for Mia for tidying up!" in out
    assert "3 stars this week" in out
    with pytest.raises(ValueError, match="How many stars"):
        rewards(s, action="add_star", child="Mia", count=0)


def test_add_star_other_goal_and_negative(s):
    rewards(s, action="star_goals", child="Mia", items=["reading"])
    out = rewards(s, action="add_star", child="Mia", goal="", count=1)
    assert "A star for Mia! " in out
    grid = out.card["data"]["grid"]
    assert any(r["goal"] == "Other stars" for r in grid)
    out = rewards(s, action="add_star", child="Mia", count=-1)
    assert out.startswith("Took 1 star off Mia.")
    assert kids_rewards.balance({"stars": [{"n": 1}, {"n": -1}], "spent": 0}) == 0


def test_sticker_chart_no_goals(s):
    rewards(s, action="star_goals", child="Mia", items=["reading"])
    out = rewards(s, action="sticker_chart", child="Mia")
    assert out.card["data"]["grid"][0]["goal"] == "reading"
    # calling with no name and one child works via only_child
    only = rewards(s, action="sticker_chart")
    assert only.card["data"]["child"] == "Mia"


def test_rewards_progress_and_claim(s):
    rewards(s, action="star_goals", child="Mia", items=["reading"])
    out = rewards(s, action="set_reward", child="Mia", reward="Trip to the park", stars=3)
    assert out.startswith("Trip to the park for Mia at 3 stars; 3 to go.")
    for _ in range(3):
        rewards(s, action="add_star", child="Mia", goal="reading")
    out = rewards(s, action="star_rewards", child="Mia")
    assert out.card["data"]["rewards"][0]["have"] == 3
    out = rewards(s, action="claim_reward", child="Mia", reward="Trip to the park")
    assert out == "Well done Mia! Trip to the park claimed for 3 stars."
    assert kids_rewards.balance(kids_rewards._kid(kids_rewards.ks.load(s, kids_rewards.STARS), "Mia")[1]) == 0
    with pytest.raises(ValueError, match="hasn't got a reward"):
        rewards(s, action="claim_reward", child="Mia", reward="Trip to the park")


def test_claim_reward_needs_enough_stars(s):
    rewards(s, action="star_goals", child="Mia", items=["reading"])
    rewards(s, action="set_reward", child="Mia", reward="Cinema", stars=5)
    rewards(s, action="add_star", child="Mia", goal="reading")
    with pytest.raises(ValueError, match="more star"):
        rewards(s, action="claim_reward", child="Mia", reward="Cinema")


def test_star_goals_needs_new_items(s):
    rewards(s, action="star_goals", child="Mia", items=["reading"])
    with pytest.raises(ValueError, match="Which goals"):
        rewards(s, action="star_goals", child="Mia", items=["Reading"])


# ---- pocket money jars ---------------------------------------------------------------------------

def test_pocket_money_set_and_jars(s):
    out = rewards(s, action="pocket_money_set", child="Mia", amount=10, split=[50, 30, 20])
    assert "gets £10.00 a week" in out and "50% spend, 30% save, 20% give" in out
    assert "in the jars already" in out
    out = rewards(s, action="pocket_money_jars", child="Mia")
    assert out.card["kind"] == "kids-jars"
    kid = out.card["data"]["children"][0]
    assert kid["child"] == "Mia"
    amounts = {j["jar"]: j["amount"] for j in kid["jars"]}
    assert amounts["spend"] == 5.0 and amounts["save"] == 3.0 and amounts["give"] == 2.0


def test_pocket_money_bad_split(s):
    with pytest.raises(ValueError, match="add up to 100"):
        rewards(s, action="pocket_money_set", child="Mia", amount=10, split=[50, 30, 30])


def test_pocket_money_add_and_spend(s):
    rewards(s, action="pocket_money_set", child="Mia", amount=0)
    out = rewards(s, action="pocket_money_add", child="Mia", amount=20, note="Birthday")
    assert out == "Added £20.00 to Mia's jars."
    out = rewards(s, action="pocket_money_spend", child="Mia", amount=5, jar="spend")
    assert "Took £5.00 from Mia's spend jar" in out
    with pytest.raises(ValueError, match="only has"):
        rewards(s, action="pocket_money_spend", child="Mia", amount=500, jar="spend")
    with pytest.raises(ValueError, match="jars are spend, save and give"):
        rewards(s, action="pocket_money_spend", child="Mia", amount=1, jar="candy")


def test_pocket_money_show_needs_setup(s):
    with pytest.raises(ValueError, match="No pocket money"):
        rewards(s, action="pocket_money_jars")


def test_pocket_money_pays_weekly(s, monkeypatch):
    rewards(s, action="pocket_money_set", child="Mia", amount=5)
    monkeypatch.setattr(homestore, "now", lambda: NOW + timedelta(days=7))
    out = rewards(s, action="pocket_money_jars", child="Mia")
    total = sum(j["amount"] for j in out.card["data"]["children"][0]["jars"])
    assert total == 10.0  # this week's plus the following Monday's payment


# ---- reading log and certificate -----------------------------------------------------------------

def test_reading_log_and_certificate(s):
    out = logs(s, action="reading_log", child="Mia", book="The Gruffalo", minutes=15, finished=True, target=2)
    assert "Logged 15 minutes" in out and "Finished" in out
    out = logs(s, action="reading_log", child="Mia", book="Room on the Broom", minutes=10, finished=True)
    assert isinstance(out, screen.Shown) and "certificate pops up" in out
    assert out.card["kind"] == "kids-certificate"
    assert out.card["data"]["books"] == 2
    out = logs(s, action="reading_certificate", child="Mia")
    assert out.card["data"]["award"] == "Super Reader"
    out = logs(s, action="reading_show", child="Mia")
    assert out.card["kind"] == "table" and out.card["rows"][0][1] == "Room on the Broom"


def test_reading_log_needs_something(s):
    with pytest.raises(ValueError, match="What did they read"):
        logs(s, action="reading_log", child="Mia")


def test_reading_certificate_not_yet(s):
    logs(s, action="reading_log", child="Mia", book="A book", minutes=5, finished=True, target=5)
    out = logs(s, action="reading_certificate", child="Mia")
    assert out == "Mia has read 1 book; 4 more for a certificate."


# ---- growth chart ---------------------------------------------------------------------------------

def test_growth_log_and_chart(s):
    logs(s, action="growth_log", child="Mia", height_cm=110, date="2026-08-01")
    out = logs(s, action="growth_log", child="Mia", height_cm=112, weight_kg=19.5, date="2026-09-01")
    assert "112 cm" in out and "19.5 kg" in out
    out = logs(s, action="growth_chart", child="Mia", measure="height")
    assert out.startswith("Mia is 112 cm, up 2 cm since")
    assert out.card["chart"]["values"] == [110, 112]
    out = logs(s, action="growth_chart", child="Mia", measure="weight")
    assert out.card["chart"]["values"] == [19.5]
    with pytest.raises(ValueError):
        logs(s, action="growth_log", child="Mia")


def test_growth_chart_needs_data(s):
    with pytest.raises(ValueError, match="haven't got any"):
        logs(s, action="growth_chart", child="Mia", measure="weight")


# ---- milestones -----------------------------------------------------------------------------------

def test_milestones(s):
    logs(s, action="milestone_add", child="Mia", text="First tooth", date="2026-09-01")
    logs(s, action="milestone_add", child="Mia", text="First steps", date="2026-09-15")
    out = logs(s, action="milestones", child="Mia")
    assert out.card["kind"] == "table" and len(out.card["rows"]) == 2
    assert out.card["rows"][0][2] == "First steps"  # newest first


def test_milestones_empty(s):
    with pytest.raises(ValueError, match="No milestones"):
        logs(s, action="milestones")


# ---- temperature and medicine log ------------------------------------------------------------------

def test_health_log_and_show(s):
    out = logs(s, action="temperature_medicine_log", child="Mia", temperature=39.2, medicine="Calpol", amount="5ml")
    assert "39.2°C" in out and "high temperature" in out and "NHS 111" in out
    out = logs(s, action="temperature_medicine_show", child="Mia")
    assert out.card["kind"] == "table" and "NHS 111" in out.card["text"]


def test_health_log_needs_something(s):
    with pytest.raises(ValueError, match="temperature, or which medicine"):
        logs(s, action="temperature_medicine_log", child="Mia")


# ---- undo -------------------------------------------------------------------------------------------

def test_undo_last(s):
    logs(s, action="milestone_add", child="Mia", text="First tooth")
    out = logs(s, action="undo_last", child="Mia", log="milestone", confirmed=False)
    assert "confirm" in out
    out = logs(s, action="undo_last", child="Mia", log="milestone", confirmed=True)
    assert out.startswith("Removed Mia's last milestone entry")
    with pytest.raises(ValueError, match="nothing in"):
        logs(s, action="undo_last", child="Mia", log="milestone", confirmed=True)


def test_undo_last_bad_log(s):
    with pytest.raises(ValueError, match="Which log"):
        logs(s, action="undo_last", child="Mia", log="nope", confirmed=True)


# ---- bedtime routine ------------------------------------------------------------------------------

def test_bedtime_steps_and_done(s):
    out = day(s, action="bedtime_steps", child="Mia", items=["Bath", "Teeth", "Story"])
    assert out == "Mia's bedtime routine has 3 steps." and out.card["kind"] == "list"
    out = day(s, action="bedtime_routine", child="Mia")
    assert out == "Bedtime for Mia: 3 steps to go."
    out = day(s, action="bedtime_done", child="Mia", items=["Bath", "teeth"])
    assert "Bath, Teeth done. 1 step to go." in out
    out = day(s, action="bedtime_done", child="Mia", items=["story"])
    assert out.startswith("All done! Sleep tight, Mia.")
    with pytest.raises(ValueError, match="isn't in"):
        day(s, action="bedtime_done", child="Mia", items=["homework"])


def test_bedtime_default_steps_for_only_child(s):
    out = day(s, action="bedtime_routine", child="Mia")
    assert [i["label"] for i in out.card["items"]] == kids_day.DEFAULT_STEPS


# ---- turn taker -------------------------------------------------------------------------------------

def test_whose_turn_remembers_last(s):
    out = day(s, action="whose_turn", activity="Xbox", people=["Mia", "Jack"])
    assert out.startswith("Mia goes first.")
    out = day(s, action="whose_turn", activity="Xbox")
    assert out.startswith("Jack goes first this time; Mia went first last time.")


def test_whose_turn_needs_two(s):
    with pytest.raises(ValueError, match="at least two names"):
        day(s, action="whose_turn", activity="Xbox", people=["Mia"])


# ---- visual timer -------------------------------------------------------------------------------------

def test_kids_timer(s):
    out = day(s, action="kids_timer", minutes=1, colour="green", people=["Mia", "Jack"])
    assert out.startswith("Turns: 1 minute, Mia first. Go!")
    assert out.card["kind"] == "kids-timer"
    assert out.card["data"]["seconds"] == 60 and out.card["data"]["colour"] == "green"
    with pytest.raises(ValueError, match="How long"):
        day(s, action="kids_timer", seconds=2)


# ---- packed lunches -------------------------------------------------------------------------------------

def test_lunch_plan_and_week(s):
    out = day(s, action="lunch_plan", day="Monday", text="Cheese sandwich", child="Mia")
    assert "Cheese sandwich for Mia's lunch on Monday." in out
    out = day(s, action="lunch_week", child="Mia")
    assert out.card["kind"] == "table"
    with pytest.raises(ValueError, match="school days"):
        day(s, action="lunch_plan", day="Saturday", text="Anything")


def test_lunch_week_fills_gaps(s):
    out = day(s, action="lunch_week", fill=True)
    assert "Filled 5 days" in out
    rows = out.card["rows"]
    assert all(row[1] for row in rows)


def test_lunch_ideas(s):
    out = day(s, action="lunch_ideas", items=["Pasta salad"])
    assert "Added Pasta salad" in out
    assert any(i["label"] == "Pasta salad" for i in out.card["items"])


# ---- family week -------------------------------------------------------------------------------------

def test_family_week(s):
    rewards(s, action="add_star", child="Mia", goal="reading")
    logs(s, action="milestone_add", child="Mia", text="First tooth")
    out = day(s, action="family_week")
    assert out.card["kind"] == "table"
    row = out.card["rows"][0]
    assert row[0] == "Mia" and row[1] == "1" and "First tooth" in row[5]


def test_family_week_needs_children(s):
    with pytest.raises(ValueError, match="haven't got anything"):
        day(s, action="family_week")


# ---- kids fun: stories, activities, jokes, drawing pad -------------------------------------------------

def test_bedtime_story(s):
    out = fun(s, action="bedtime_story", characters=["Mia", "Sparkle the dragon"], place="a castle",
              theme="bravery", child="Mia")
    assert isinstance(out, screen.Shown)
    assert out.card["kind"] == "text" and "Title:" in out.card["text"]
    assert out.startswith("Tell this now as a gentle bedtime story")
    out = fun(s, action="stories_told")
    assert out.card["kind"] == "table" and len(out.card["rows"]) == 1


def test_stories_told_empty(s):
    with pytest.raises(ValueError, match="No bedtime stories"):
        fun(s, action="stories_told")


def test_activity_idea(s):
    out = fun(s, action="activity_idea", setting="indoor", free=True, age=6)
    assert out.card["kind"] == "text"
    out = fun(s, action="activity_idea", setting="indoor", free=True, age=6, show_all=True)
    assert out.card["kind"] == "list" and len(out.card["items"]) >= 1
    with pytest.raises(ValueError):
        fun(s, action="activity_idea", setting="indoor", free=True, age=200)


def test_joke_and_tongue_twister(s):
    out = fun(s, action="kids_joke")
    assert out.card["kind"] == "text" and out.card["text"]
    out = fun(s, action="tongue_twister")
    assert out.card["kind"] == "text" and out.card["text"]


def test_drawing_pad(s):
    out = fun(s, action="drawing_pad", folder="Ideas", child="Mia")
    assert out.card["kind"] == "kids-draw"
    assert out.card["data"]["folder"] == "Ideas" and out.card["data"]["child"] == "Mia"
    with pytest.raises(ValueError, match="I can only save drawings"):
        fun(s, action="drawing_pad", folder="Nowhere")
