from datetime import datetime

import pytest

import homestore
import investlearn_calc as ic
import investlearn_data as data
import investlearn_learn as il
import investlearn_lessons as lessons
import investlearn_plan as ip
import investlearn_practice as pr
import investlearn_store as st
import screen
import tools
from config import Settings


@pytest.fixture(autouse=True)
def fixed_now(monkeypatch):
    monkeypatch.setattr(homestore, "now", lambda: datetime(2026, 9, 29, 12, 0))


@pytest.fixture
def s(tmp_path):
    return Settings(memory_dir=str(tmp_path))


def run(mod, s, action, **a):
    return mod.run_tool("x", {"action": action, **a}, s, None)


def card(x):
    assert isinstance(x, screen.Shown) and x.card
    return x.card


def test_project_maths():
    flat = st.project(1000, 0, 10, 0)
    assert flat["balances"][-1] == pytest.approx(1000)
    grown = st.project(1000, 0, 30, 5)["balances"][-1]
    assert grown == pytest.approx(1000 * 1.05 ** 30, rel=1e-9)
    assert st.project(0, 100, 1, 0)["balances"][-1] == pytest.approx(1200)
    assert st.deflate([100, 100], 10)[1] == pytest.approx(100 / 1.1)


def test_compound_range_and_disclaimer(s):
    out = run(ic, s, "compound", lump=1000, monthly=100, years=20, rate=5, inflation=2)
    c = card(out)
    assert c["kind"] == "investlearn-growth"
    names = [x["name"] for x in c["data"]["series"]]
    assert len(names) == 5 and any("today's money" in n for n in names)
    low, mid, high = (x["values"][-1] for x in c["data"]["series"][:3])
    assert low < mid < high
    assert "not guaranteed" in out and "capital is at risk" in out and "not financial advice" in out
    with pytest.raises(ValueError):
        run(ic, s, "compound", years=10)


def test_every_calc_action_is_an_illustration(s):
    calls = {
        "compound": dict(lump=500, monthly=50), "cost_of_waiting": dict(monthly=100, years=30), "target_saving": dict(target=20000, years=10),
        "years_to_target": dict(target=10000, monthly=200), "fees_drag": dict(monthly=200), "inflation": dict(amount=1000, years=20),
        "real_return": dict(rate=6, inflation=3), "rule72": dict(rate=6), "cagr": dict(start=1000, end=2000, years=10),
        "loss_recovery": dict(fall=50), "extra_saving": dict(monthly=100, extra=50), "compare_rates": dict(monthly=100),
        "pound_cost_averaging": dict(prices=[10, 8, 6, 9, 12]),
    }
    assert set(calls) == set(ic.ACTIONS)
    for action, args in calls.items():
        out = run(ic, s, action, **args)
        assert card(out)["kind"] in ("investlearn-growth", "investlearn-bars", "table"), action
        assert "not guaranteed" in out and "at risk" in out and "not financial advice" in out, action


def test_calc_numbers(s):
    assert "100.0%" in run(ic, s, "loss_recovery", fall=50)
    assert "12.0 years" in run(ic, s, "rule72", rate=6)
    assert "8.0%" in run(ic, s, "rule72", years=9)
    fees = card(run(ic, s, "fees_drag", lump=10000, years=30, rate=6))
    a, b = fees["data"]["series"][0]["values"][-1], fees["data"]["series"][1]["values"][-1]
    assert a > b > 10000
    wait = card(run(ic, s, "cost_of_waiting", monthly=100, years=30, rate=5))["data"]["rows"]
    assert wait[0]["value"] > wait[-1]["value"]
    need = card(run(ic, s, "target_saving", target=12000, years=10, lump=0, rate=0))["data"]["rows"]
    assert need[0]["text"].startswith("£100.00")
    assert "6 years" in run(ic, s, "years_to_target", target=72000, monthly=1000, rate=0)
    assert "about 1 year to" in run(ic, s, "years_to_target", target=12000, monthly=1000, rate=0)
    assert "isn't reached" in run(ic, s, "years_to_target", target=10 ** 9, monthly=1, rate=0)
    pca = run(ic, s, "pound_cost_averaging", prices=[10, 5], amount=100)
    assert "30.00 units" in pca and "average £6.67" in pca
    for bad in ({"years": 500}, {"rate": 500}):
        with pytest.raises(ValueError):
            run(ic, s, "compound", lump=1000, **bad)
    with pytest.raises(ValueError):
        run(ic, s, "pound_cost_averaging", prices=[5])
    with pytest.raises(ValueError):
        run(ic, s, "rule72")
    with pytest.raises(ValueError):
        run(ic, s, "nope")


def test_content_size():
    assert len(data.GLOSSARY) >= 60
    assert len(lessons.LESSONS) == 10
    for lesson in lessons.LESSONS:
        assert len(lesson["quiz"]) == 3
        for _q, options, right, _why in lesson["quiz"]:
            assert len(options) == 3 and 0 <= right < 3


def test_lessons_quiz_and_progress(s):
    out = run(il, s, "lesson_list")
    assert card(out)["kind"] == "list" and len(card(out)["items"]) == 10
    assert card(run(il, s, "lesson", lesson="2"))["kind"] == "text"
    assert card(run(il, s, "lesson", lesson="fees"))["title"].startswith("Lesson 5")
    q = run(il, s, "quiz", lesson="fees")
    assert len(card(q)["items"]) == 3 and card(q)["items"][0]["say"]
    right = run(il, s, "answer", lesson="fees", question=1, choice="B")
    assert right.startswith("Correct.")
    wrong = run(il, s, "answer", lesson="fees", question=2, choice="C")
    assert wrong.startswith("Not quite")
    assert "Question 3" in run(il, s, "quiz", lesson="fees")
    finished = run(il, s, "answer", lesson="fees", question=3, choice="2")
    assert "Quiz finished: 2 of 3" in finished
    bars = card(run(il, s, "progress"))
    assert bars["kind"] == "investlearn-bars" and any("quiz 2/3" in r["text"] for r in bars["data"]["rows"])
    assert "confirm" in run(il, s, "reset_progress").lower()
    assert "reset" in run(il, s, "reset_progress", confirmed=True).lower()
    assert all(r["value"] == 0 for r in card(run(il, s, "progress"))["data"]["rows"])
    with pytest.raises(ValueError):
        run(il, s, "answer", lesson="fees", question=1, choice="Z")
    with pytest.raises(ValueError):
        run(il, s, "lesson", lesson="astrology")


def test_glossary_and_jargon(s):
    assert len(card(run(il, s, "glossary"))["items"]) == len(data.GLOSSARY)
    assert "yearly cost" in run(il, s, "glossary", term="OCF")
    assert card(run(il, s, "glossary", term="isa"))["kind"] == "text"
    assert card(run(il, s, "glossary", term="income"))["kind"] == "list"
    with pytest.raises(ValueError):
        run(il, s, "glossary", term="zzzzqq")
    cards = card(run(il, s, "flashcards", count=5))
    assert cards["kind"] == "investlearn-cards" and len(cards["data"]["cards"]) == 5
    buster = card(run(il, s, "jargon_buster", text="The ETF has a low OCF and pays a dividend in a bull market."))
    labels = " ".join(i["label"] for i in buster["items"])
    assert "etf" in labels and "ocf" in labels and "dividend" in labels and "bull market" in labels
    with pytest.raises(ValueError):
        run(il, s, "jargon_buster", text="hello there")


def test_myths_scams_wrappers_explain(s):
    assert card(run(il, s, "myths"))["kind"] == "investlearn-cards"
    scams = run(il, s, "scam_warnings")
    assert "FCA Register" in scams and "Guaranteed returns" in str(card(scams))
    assert card(run(il, s, "scam_check"))["kind"] == "list"
    bad = run(il, s, "scam_check", answers=[True, True, True, False, False, False])
    assert "likely scam" in bad
    assert "No red flags" in run(il, s, "scam_check", answers=[False] * 6)
    assert len(card(run(il, s, "wrappers"))["items"]) == len(data.WRAPPERS)
    lisa = run(il, s, "wrappers", name="lifetime isa")
    assert "GOV.UK" in lisa and "25%" in lisa
    with pytest.raises(ValueError):
        run(il, s, "wrappers", name="mystery")
    for topic in data.EXPLAINERS:
        out = run(il, s, "explain", topic=topic)
        assert card(out)["kind"] == "text"
    assert "not a promise" in run(il, s, "explain", topic="four_percent").card["text"]
    with pytest.raises(ValueError):
        run(il, s, "explain", topic="lottery")


def test_risk_questionnaire_explains_only(s):
    first = run(il, s, "risk_quiz")
    assert "Risk question 1" in first
    for q in range(1, 6):
        assert "Risk question" in run(il, s, "risk_answer", question=q, choice="C")
    done = run(il, s, "risk_answer", question=6, choice="C")
    assert "adventurous" in done and "not advice" in done.lower()
    for word in ("buy", "recommend fund"):
        assert word not in done.card["text"].lower().replace("not a product recommendation", "")
    assert "Risk question 1" in run(il, s, "risk_quiz", restart=True)


def test_uk_calculators(s):
    relief = run(ip, s, "pension_relief", amount=800, band="higher")
    assert "£1,000" in relief and "£200" in relief and "GOV.UK" in relief
    with pytest.raises(ValueError):
        run(ip, s, "pension_relief", amount=100, band="royal")
    lisa = run(ip, s, "lisa", amount=4000)
    assert "£1,000" in lisa and "less than you paid in" in lisa and "GOV.UK" in lisa
    isa = run(ip, s, "isa_allowance", used=5000)
    assert "£15,000" in isa and "5 April 2027" in isa and "GOV.UK" in isa
    match = run(ip, s, "pension_match", salary=30000, employee_pct=3, employer_pct=3, more_employee_pct=5, more_employer_pct=5)
    assert "£600 a year more from your employer" in match
    emerg = run(ip, s, "emergency_fund", essentials=1500, savings=3000, months=3)
    assert "2.0 months" in emerg and "£1,500 more" in emerg
    assert card(emerg)["kind"] == "investlearn-bars"


def test_fire_and_drawdown(s):
    fire = run(ip, s, "fire_number", spending=20000, balance=100000)
    assert "£500,000" in fire and "not a promise" in fire and "20 percent" in fire
    assert card(fire)["kind"] == "table"
    fi = run(ip, s, "years_to_fi", spending=20000, balance=50000, monthly=1000, rate=5, inflation=2.5)
    assert card(fi)["kind"] == "investlearn-growth" and "not guaranteed" in fi
    assert "isn't reached" in run(ip, s, "years_to_fi", spending=1_000_000, monthly=1, rate=0)
    dd = run(ip, s, "drawdown", balance=100000, withdrawal=10000, rate=0, inflation=0, spread=0)
    assert "10 years" in dd
    long = run(ip, s, "drawdown", balance=1_000_000, withdrawal=10000, rate=6, inflation=2)
    assert "beyond 60 years" in long
    assert card(dd)["kind"] == "investlearn-growth"


def test_goals_and_milestones(s):
    with pytest.raises(ValueError):
        run(ip, s, "goal_show")
    out = run(ip, s, "goal_add", name="House deposit", kind="house_deposit", target=20000, saved=2000, monthly=300, rate=4, date="2030-01-01")
    assert card(out)["kind"] == "investlearn-growth" and "not guaranteed" in out
    run(ip, s, "goal_add", name="Retirement", kind="retirement", target=500000, monthly=200)
    assert card(run(ip, s, "goal_show"))["kind"] == "investlearn-bars"
    assert card(run(ip, s, "goal_show", name="house"))["kind"] == "investlearn-growth"
    run(ip, s, "goal_update", name="house", add=1000)
    assert st.load(s)["goals"][0]["saved"] == 3000
    ms = card(run(ip, s, "milestones", name="House deposit"))
    assert ms["kind"] == "table" and ms["rows"][0][2] != "" and len(ms["rows"]) == 4
    assert "confirm" in run(ip, s, "goal_remove", name="Retirement").lower()
    assert "Removed" in run(ip, s, "goal_remove", name="Retirement", confirmed=True)
    assert len(st.load(s)["goals"]) == 1
    with pytest.raises(ValueError):
        run(ip, s, "goal_add", name="X", kind="lottery", target=10)


def test_house_and_retirement(s):
    house = run(ip, s, "house_deposit", price=250000, saved=5000, monthly=400)
    assert card(house)["kind"] == "table" and "£25,000" in house and "stamp duty" in house
    assert any("Save as goal" in b["label"] for b in card(house)["buttons"])
    ret = run(ip, s, "retirement_plan", age=30, retire_age=67, spending=20000, balance=10000, monthly=300, rate=5)
    assert card(ret)["kind"] == "investlearn-growth" and "GOV.UK" in ret and "not guaranteed" in ret
    with pytest.raises(ValueError):
        run(ip, s, "retirement_plan", age=60, retire_age=50, spending=1000)


def test_practice_portfolio(s):
    with pytest.raises(ValueError):
        run(pr, s, "show")
    out = run(pr, s, "add_holding", name="Example Fund", units=10, buy_price=5)
    assert card(out)["kind"] == "table" and "Practice" in out and "not advice" in out.lower()
    run(pr, s, "add_holding", name="Made Up Bond", units=20, buy_price=2, price=2)
    run(pr, s, "add_holding", name="Example Fund", units=10, buy_price=7)
    h = {x["name"]: x for x in st.load(s)["holdings"]}
    assert h["Example Fund"]["units"] == 20 and h["Example Fund"]["cost"] == pytest.approx(6)
    run(pr, s, "set_price", name="example", price=9)
    assert st.load(s)["holdings"][0]["price"] == 9
    alloc = card(run(pr, s, "allocation"))
    assert alloc["kind"] == "investlearn-bars" and alloc["data"]["rows"][0]["label"] == "Example Fund"
    assert "£220.00 to £176.00" in run(pr, s, "what_if", fall=20)
    wi = run(pr, s, "what_if", fall=50)
    assert "100.0%" in wi and "made-up" in wi
    assert "concentrated" in run(pr, s, "allocation")
    div = run(pr, s, "diversification_check")
    assert "Largest is Example Fund" in div
    reb = card(run(pr, s, "rebalance", targets=[{"name": "Example Fund", "percent": 50}, {"name": "Made Up Bond", "percent": 50}]))
    assert reb["kind"] == "table" and "move out" in reb["rows"][0][3]
    with pytest.raises(ValueError):
        run(pr, s, "rebalance", targets=[{"name": "Example Fund", "percent": 30}])
    sold = run(pr, s, "sell", name="Made Up Bond", units=5, price=3)
    assert "gain £5.00" in sold
    assert card(run(pr, s, "trade_log"))["kind"] == "table"
    with pytest.raises(ValueError):
        run(pr, s, "sell", name="Made Up Bond", units=999)
    assert "confirm" in run(pr, s, "remove_holding", name="Made Up Bond").lower()
    assert "Removed" in run(pr, s, "remove_holding", name="Made Up Bond", confirmed=True)
    assert "confirm" in run(pr, s, "reset").lower()
    assert "cleared" in run(pr, s, "reset", confirmed=True)
    assert st.load(s)["holdings"] == []


def test_registration_and_through_tools(s):
    names = set()
    for mod in (ic, il, ip, pr):
        assert mod in tools.ABILITIES
        for d in mod.tool_definitions():
            assert d["input_schema"]["additionalProperties"] is False
            names.add(d["name"])
        assert mod.NAMES <= names
    assert names == {"invest_calc", "invest_learn", "invest_plan", "invest_practice"}
    assert {st.GROWTH, st.BARS, st.CARDS} <= screen.EXTRA_KINDS
    import asyncio
    out = asyncio.run(tools._run_tool("invest_calc", {"action": "rule72", "rate": 8}, s, None))
    assert "9.0 years" in out and card(out)["kind"] == "table"
