import asyncio

import pytest

import screen
import sidehustle_data as data
import sidehustle_ideas
import sidehustle_money
import sidehustle_plan
import sidehustle_safety
import sidehustle_store as st
import tools
from config import Settings


@pytest.fixture
def s(tmp_path):
    return Settings(memory_dir=str(tmp_path))


def ideas(s, **a):
    return sidehustle_ideas.run_tool("sidehustle_ideas", a, s)


def plan(s, **a):
    return sidehustle_plan.run_tool("sidehustle_plan", a, s)


def money(s, **a):
    return sidehustle_money.run_tool("sidehustle_money", a, s)


def safety(s, **a):
    return sidehustle_safety.run_tool("sidehustle_safety", a, s)


def kind(shown):
    assert isinstance(shown, screen.Shown)
    return shown.card["kind"]


def test_registered_and_through_tools(s):
    names = {t["name"] for t in tools.client_tool_definitions(Settings())}
    assert {"sidehustle_ideas", "sidehustle_plan", "sidehustle_money", "sidehustle_safety"} <= names
    assert {"sidehustle-ideas", "sidehustle-compare", "sidehustle-calc", "sidehustle-plan", "sidehustle-goal",
            "sidehustle-hours", "sidehustle-review", "sidehustle-redflags"} <= screen.EXTRA_KINDS
    out = asyncio.run(tools._run_tool("sidehustle_ideas", {"action": "detail", "name": "dog walking"}, s, None))
    assert kind(out) == "sidehustle-calc"


def test_idea_data_is_sound():
    rows = data.all_ideas()
    assert len(rows) >= 40 and len({r["id"] for r in rows}) == len(rows)
    assert all(r["cost_low"] <= r["cost_high"] and r["risk"] and r["uk_note"] for r in rows)
    assert all(r["category"] in data.CATEGORIES for r in rows)


def test_ideas_list_and_filters(s):
    assert kind(ideas(s, action="list")) == "sidehustle-ideas"
    assert all(i["cost"] == "free" or "£" in i["cost"] for i in ideas(s, action="list", category="care").card["data"]["ideas"])
    cheap = ideas(s, action="list", max_cost=0).card["data"]["ideas"]
    assert 0 < len(cheap) < 40
    with pytest.raises(ValueError):
        ideas(s, action="list", category="nonsense")


def test_match_uses_skills_hours_budget(s):
    with pytest.raises(ValueError):
        ideas(s, action="match")
    shown = ideas(s, action="match", skills="I love dogs and gardening", hours_per_week=5, budget=100)
    names = [i["name"] for i in shown.card["data"]["ideas"]]
    assert names[0] in {"Dog walking", "Gardening and lawn care", "Pet sitting and home visits",
                        "Growing and selling plants"}
    assert "Personal training or fitness classes" not in names
    assert "guarantee" not in shown.lower() and "promise" in shown.card["data"]["note"]


def test_profile_and_shortlist_and_compare(s):
    assert "Saved" in ideas(s, action="save_profile", skills="driving, cooking", hours_per_week=6, budget=50)
    assert kind(ideas(s, action="profile")) == "sidehustle-calc"
    assert ideas(s, action="match").card["data"]["ideas"]
    ideas(s, action="shortlist_add", name="dog walking")
    shown = ideas(s, action="shortlist_add", name="tutoring")
    assert [i["label"] for i in shown.card["items"]] == ["Dog walking", "Tutoring"]
    assert ideas(s, action="shortlist").card["kind"] == "list"
    cmp = ideas(s, action="compare")
    assert kind(cmp) == "sidehustle-compare" and cmp.card["data"]["names"] == ["Dog walking", "Tutoring"]
    assert kind(ideas(s, action="compare", names=["cleaning", "handyman", "baking"])) == "sidehustle-compare"
    with pytest.raises(ValueError):
        ideas(s, action="compare", names=["cleaning"])
    assert "Took" in ideas(s, action="shortlist_remove", name="tutoring")
    with pytest.raises(ValueError):
        ideas(s, action="shortlist_remove", name="tutoring")
    with pytest.raises(ValueError):
        ideas(s, action="save_profile", skills="zzz")


def test_surprise_quick_wins_categories_detail(s):
    assert kind(ideas(s, action="surprise")) == "sidehustle-ideas"
    assert kind(ideas(s, action="quick_wins")) == "sidehustle-ideas"
    assert ideas(s, action="categories").card["kind"] == "list"
    assert "UK note" in [r[0] for r in ideas(s, action="detail", name="Reselling").card["data"]["rows"]]
    with pytest.raises(ValueError):
        ideas(s, action="detail", name="space pirate")


def test_hourly_rate_break_even_startup(s):
    shown = money(s, action="hourly_rate", income=300, costs=100, hours=20)
    assert kind(shown) == "sidehustle-calc" and shown.card["data"]["headline"] == "£10 an hour"
    assert any("below" in n for n in shown.card["data"]["notes"])
    be = money(s, action="break_even", fixed_costs=100, price=15, unit_cost=5, per_week=2)
    assert be.card["data"]["headline"] == "10 sales" and "5 weeks" in be
    with pytest.raises(ValueError):
        money(s, action="break_even", fixed_costs=100, price=5, unit_cost=5)
    st_cost = money(s, action="startup_cost", items=[{"item": "mower", "cost": 100}, {"item": "gloves", "cost": 10}], budget=200)
    assert st_cost.card["data"]["headline"] == "£121" and "under your budget" in st_cost.card["data"]["notes"][0]
    with pytest.raises(ValueError):
        money(s, action="startup_cost")


def test_pricing(s):
    cp = money(s, action="price_cost_plus", materials=5, hours=1, hourly_pay=10, markup_pct=0, fee_pct=10)
    assert cp.card["data"]["headline"] == "£16.67"
    with pytest.raises(ValueError):
        money(s, action="price_cost_plus")
    th = money(s, action="price_target_hourly", target_hourly=15, hours_per_job=2, unpaid_hours=1, costs_per_job=5)
    assert th.card["data"]["headline"] == "£50"
    assert "longer" in th.card["data"]["rows"][-1][0]


def test_logging_hours_income_costs_and_summaries(s):
    plan(s, action="start_hustle", name="dog walking")
    assert "hours this week" in money(s, action="log_hours", hours=3, hustle="dog")
    money(s, action="log_hours", hours=2)
    assert "Logged £60" in money(s, action="log_income", amount=60, customer="Sam")
    assert "Logged £10" in money(s, action="log_expense", amount=10, note="leads")
    with pytest.raises(ValueError):
        money(s, action="log_hours", hours=30)
    week = money(s, action="hours_week")
    assert kind(week) == "sidehustle-hours" and week.card["data"]["series"][0]["values"][-1] == 5
    summary = money(s, action="hustle_summary")
    assert summary.card["data"]["headline"] == "£10 an hour"
    assert kind(money(s, action="hourly_rate", hustle="dog walking")) == "sidehustle-calc"
    assert kind(money(s, action="hustle_summary", month=st.today().strftime("%Y-%m"))) == "sidehustle-calc"
    money(s, action="log_hours", hours=1, hustle="Reselling")
    money(s, action="log_income", amount=40, hustle="Reselling")
    comp = money(s, action="compare_rates")
    assert comp.card["kind"] == "table" and comp.card["rows"][0][0] == "Reselling"
    assert money(s, action="entries").card["rows"]
    assert money(s, action="entries", kind="income", hustle="resell").card["rows"][0][1] == "Reselling"
    need = money(s, action="sales_needed", price=20, unit_cost=5, target_profit=150)
    assert need.card["data"]["headline"] == "10 sales"


def test_start_plan_and_tasks(s):
    shown = plan(s, action="start_hustle", name="Reselling")
    assert kind(shown) == "sidehustle-plan" and shown.card["data"]["total"] >= 19
    with pytest.raises(ValueError):
        plan(s, action="start_hustle", name="reselling")
    plan(s, action="start_hustle", name="Candle stall", date="2020-01-01")
    with pytest.raises(ValueError):
        plan(s, action="launch_plan")
    tick = plan(s, action="tick_task", hustle="reselling", task_id=1)
    assert tick.card["data"]["done"] == 1
    assert plan(s, action="tick_task", hustle="reselling", task="budget cap").card["data"]["done"] == 2
    assert plan(s, action="tick_task", hustle="reselling", task_id=1, done=False).card["data"]["done"] == 1
    added = plan(s, action="add_task", hustle="candle", task="Buy wax", day=2)
    assert any(t["text"] == "Buy wax" for w in added.card["data"]["weeks"] for t in w["tasks"])
    late = plan(s, action="launch_plan", hustle="candle").card["data"]["weeks"][0]["tasks"]
    assert any(t["late"] for t in late)
    nxt = plan(s, action="next_tasks")
    assert nxt.card["kind"] == "list" and nxt.card["items"][0]["say"].startswith("Tick off task")
    with pytest.raises(ValueError):
        plan(s, action="tick_task", hustle="reselling", task_id=999)


def test_hustles_status_and_remove(s):
    with pytest.raises(ValueError):
        plan(s, action="hustles")
    plan(s, action="start_hustle", name="Tutoring")
    assert plan(s, action="hustles").card["rows"][0][:2] == ["Tutoring", "active"]
    assert "paused" in plan(s, action="set_status", hustle="tutoring", status="paused")
    assert plan(s, action="hustles").card["rows"][0][1] == "paused"
    with pytest.raises(ValueError):
        plan(s, action="next_tasks")
    with pytest.raises(ValueError):
        plan(s, action="set_status", status="fast")
    assert "Say yes" in plan(s, action="remove_hustle", hustle="tutoring")
    assert plan(s, action="hustles")
    assert "Removed" in plan(s, action="remove_hustle", hustle="tutoring", confirmed=True)
    with pytest.raises(ValueError):
        plan(s, action="hustles")


def test_goal_progress(s):
    with pytest.raises(ValueError):
        plan(s, action="goal_progress")
    assert "not a promise" in plan(s, action="goal_set", amount=300)
    money(s, action="log_income", amount=120, hustle="Reselling")
    money(s, action="log_expense", amount=20, hustle="Reselling")
    shown = plan(s, action="goal_progress")
    assert kind(shown) == "sidehustle-goal"
    assert shown.card["data"]["so_far"] == 100 and shown.card["data"]["pct"] == 33
    with pytest.raises(ValueError):
        plan(s, action="goal_set", amount=0)


def test_monthly_review_and_history(s):
    empty = plan(s, action="monthly_review", hustle="Reselling")
    assert empty.card["data"]["verdict"] == "nodata"
    money(s, action="log_hours", hours=10, hustle="Reselling")
    money(s, action="log_income", amount=20, hustle="Reselling")
    money(s, action="log_expense", amount=30, hustle="Reselling")
    losing = plan(s, action="monthly_review", hustle="Reselling")
    assert kind(losing) == "sidehustle-review" and losing.card["data"]["verdict"] == "change"
    assert "decision is yours" in losing
    money(s, action="log_income", amount=300, hustle="Reselling")
    assert plan(s, action="monthly_review", hustle="Reselling", decision="keep going").card["data"]["verdict"] == "keep"
    assert plan(s, action="review_history").card["rows"][0][2] == "keep going"
    with pytest.raises(ValueError):
        plan(s, action="monthly_review", decision="panic")


def test_long_unprofitable_hustle_suggests_stopping(s):
    plan(s, action="start_hustle", name="Candle stall", date="2026-01-05")
    money(s, action="log_hours", hours=15, hustle="Candle stall")
    money(s, action="log_expense", amount=50, hustle="Candle stall")
    assert plan(s, action="monthly_review", hustle="Candle stall").card["data"]["verdict"] == "stop"


def test_orders_and_customers(s):
    added = plan(s, action="order_add", hustle="Baking", customer="Jo", item="12 cupcakes", price=30, due="2030-01-01")
    assert added.card["kind"] == "table" and added.card["rows"][0][:2] == ["1", "Jo"]
    plan(s, action="order_add", hustle="Baking", customer="Jo", item="Birthday cake", price=45, status="agreed")
    with pytest.raises(ValueError):
        plan(s, action="order_update", customer="Jo", status="delivered")
    upd = plan(s, action="order_update", order_id=1, status="paid")
    assert "Logged £30" in upd
    plan(s, action="order_update", order_id=1, status="paid")
    assert st.totals(st.log(s), "Baking")["income"] == 30
    assert len(plan(s, action="orders", status="agreed").card["rows"]) == 1
    assert len(plan(s, action="orders", hustle="bak").card["rows"]) == 2
    cust = plan(s, action="customers")
    assert cust.card["rows"][0][0] == "Jo (repeat)" and cust.card["rows"][0][2] == "£30"
    assert "Noted" in plan(s, action="customer_note", customer="Jo", note="Nut allergy in family")
    assert "Nut allergy" in plan(s, action="customers").card["rows"][0][4]
    assert "Say yes" in plan(s, action="order_remove", order_id=2)
    assert len(plan(s, action="orders").card["rows"]) == 2
    assert "Removed" in plan(s, action="order_remove", order_id=2, confirmed=True)
    with pytest.raises(ValueError):
        plan(s, action="order_add", hustle="Baking", customer="Jo", item="x", price=5, status="lost")
    assert plan(s, action="goal_set", amount=100) and plan(s, action="goal_progress").card["data"]["note"]


def test_check_offer_flags_scams(s):
    bad = safety(s, action="check_offer", text="Guaranteed £500 a day! Pay a small registration fee for your starter kit, "
                                               "recruit friends, message us on WhatsApp. Limited spots, act now.")
    data_ = bad.card["data"]
    assert kind(bad) == "sidehustle-redflags" and data_["score"] >= 8 and "scam" in data_["level"]
    assert len(data_["flags"]) >= 5
    crypto = safety(s, action="check_offer", text="Elon crypto giveaway: send 0.1 bitcoin and get 0.2 back")
    assert any("Crypto" in f["label"] for f in crypto.card["data"]["flags"])
    clean = safety(s, action="check_offer", text="Dog walker needed Tuesdays, £14 an hour, paid weekly by bank transfer.")
    assert clean.card["data"]["score"] == 0 and "isn't proof" in clean.card["data"]["level"]
    with pytest.raises(ValueError):
        safety(s, action="check_offer")


def test_scam_guides(s):
    assert kind(safety(s, action="red_flag_guide")) == "sidehustle-redflags"
    assert len(safety(s, action="scam_types").card["items"]) == 7
    for q, word in [("MLM", "MLM"), ("pyramid", "MLM"), ("upfront fee", "Upfront"), ("bitcoin giveaway", "Crypto"),
                    ("fake cheque", "Overpayment"), ("task scam", "Task"), ("forex bot", "Trading"), ("dropshipping", "course")]:
        assert word.lower() in safety(s, action="explain_scam", scam_type=q).card["title"].lower()
    with pytest.raises(ValueError):
        safety(s, action="explain_scam", scam_type="unicorns")
    for action in ("before_you_pay", "if_scammed", "verify_company", "legit_signs"):
        shown = safety(s, action=action)
        assert shown.card["kind"] == "list" and len(shown.card["items"]) >= 6
    assert "159" in " ".join(i["label"] for i in safety(s, action="if_scammed").card["items"])


def test_mlm_math(s):
    bad = safety(s, action="mlm_math", joining_cost=200, monthly_cost=80, monthly_earnings=60)
    assert bad.card["data"]["headline"] == "£-440" or "-" in bad.card["data"]["headline"]
    assert "never" in bad.card["data"]["rows"][-1][1]
    ok = safety(s, action="mlm_math", joining_cost=100, monthly_cost=20, monthly_earnings=70, months=6)
    assert ok.card["data"]["rows"][-1][1] == "about 2 months"
    with pytest.raises(ValueError):
        safety(s, action="mlm_math", monthly_earnings=10)


def test_unknown_actions_and_hygiene(s):
    for fn in (plan, money, safety):
        with pytest.raises(ValueError):
            fn(s, action="nope")
    for mod in (sidehustle_ideas, sidehustle_plan, sidehustle_money, sidehustle_safety):
        tool = mod.tool_definitions()[0]
        assert tool["input_schema"]["additionalProperties"] is False
        assert set(tool["input_schema"]["properties"]["action"]["enum"]) == set(mod.ACTIONS)
        assert len(tool["description"]) < 700
