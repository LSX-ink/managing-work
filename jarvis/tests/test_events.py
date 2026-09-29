import asyncio
from datetime import date

import httpx
import pytest

import events_extras as extras
import events_guests as guests
import events_money as money
import events_plan as plan
import screen
import tools
from config import Settings

TODAY = date(2026, 9, 29)


@pytest.fixture
def s(tmp_path):
    return Settings(memory_dir=str(tmp_path), city="Leeds")


def p(s, **a):
    return plan.run_tool("event_plan", a, s, None, today=TODAY)


def g(s, **a):
    return guests.run_tool("event_guests", a, s, None, today=TODAY)


def m(s, **a):
    return money.run_tool("event_money", a, s, None, today=TODAY)


def run_async(args, s, handler=None):
    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler or (lambda r: httpx.Response(500)))) as http:
            return await extras.run_tool("event_extras", args, s, http, today=TODAY)

    return asyncio.run(go())


def party(s, **extra):
    return p(s, action="create", name="Mia's party", date="2026-11-10", place="Village hall", budget=300, kind="kids", **extra)


def test_registered():
    for mod in (plan, guests, money, extras):
        assert len(mod.tool_definitions()) == 1 and mod in tools.ABILITIES
    assert {"events-dashboard", "events-timeline", "events-budget", "events-seating"} <= screen.EXTRA_KINDS


def test_create_list_update_remove(s):
    assert "in 42 days" in party(s)
    assert "steps" not in party(s, with_plan=False)
    shown = p(s, action="list")
    assert shown.card["kind"] == "table" and shown.card["rows"][0][0] == "Mia's party"
    assert "Updated" in p(s, action="update", place="Scout hut", budget=250)
    assert "Updated the name" in p(s, action="update", new_name="Mia's 7th")
    with pytest.raises(ValueError):
        p(s, action="update")
    with pytest.raises(ValueError):
        p(s, action="dashboard", name="nothing")
    assert "confirm" in p(s, action="remove", name="Mia's 7th")
    assert p(s, action="remove", name="Mia's 7th", confirmed=True) == "Removed Mia's 7th."
    with pytest.raises(ValueError):
        p(s, action="list")


def test_christmas_defaults_to_next_25_december(s):
    assert "Friday 25 December" in p(s, action="create", name="Christmas", kind="christmas")
    with pytest.raises(ValueError):
        p(s, action="create", name="Bad", date="2026-11-10", kind="nope")


def test_tasks_timeline_and_dashboard(s):
    party(s)
    assert "Added" in p(s, action="task_add", task="Book the bouncy castle", weeks_before=4)
    shown = p(s, action="timeline")
    assert shown.card["kind"] == "events-timeline"
    items = shown.card["data"]["items"]
    assert items[0]["when"] == "6 weeks before" and items[0]["say"]
    assert "Ticked" in p(s, action="task_tick", task="bouncy")
    assert "Unticked" in p(s, action="task_tick", task="bouncy", done=False)
    assert "Ticked" in p(s, action="task_tick", task="1")
    with pytest.raises(ValueError):
        p(s, action="task_tick", task="zzz")
    late = plan.run_tool("event_plan", {"action": "timeline"}, s, None, today=date(2026, 11, 5))
    assert "overdue" in late
    dash = p(s, action="dashboard")
    assert dash.card["kind"] == "events-dashboard" and dash.card["data"]["days"] == 42
    assert dash.card["data"]["tasks"]["done"] == 1 and dash.card["data"]["next"]
    assert "already has" in p(s, action="standard_plan", kind="kids")
    assert "Added" in p(s, action="standard_plan", kind="wedding")
    with pytest.raises(ValueError):
        p(s, action="task_add")


def test_uk_wedding_has_notice_of_marriage(s):
    p(s, action="create", name="Our wedding", date="2027-06-12", kind="wedding")
    items = p(s, action="timeline").card["data"]["items"]
    assert any("notice of marriage" in i["text"] for i in items) and items[0]["when"] == "12 months before"


def test_setup_checklist(s):
    party(s)
    shown = p(s, action="setup_list")
    assert shown.card["kind"] == "list" and shown.card["checks"] and len(shown.card["items"]) >= 10
    assert "Ticked" in p(s, action="setup_tick", item="balloons")
    assert len(p(s, action="setup_list", item="Cake knife").card["items"]) > 12


def test_guests_rsvp_counts_and_dietary(s):
    party(s)
    g(s, action="guest_add", guests=["Ava", "Leo", "Zara"])
    assert "Ben" in g(s, action="guest_add", guest="Ben", rsvp="yes", dietary="nut allergy", plus_ones=1)
    assert "3 people" in g(s, action="rsvp", guest="ava", rsvp="yes")
    g(s, action="rsvp", guest="Leo", rsvp="no")
    shown = g(s, action="guests")
    assert shown.card["kind"] == "table" and shown.card["rows"][0][1] == "yes"
    assert any(r[3] == "nut allergy" for r in shown.card["rows"])
    c = g(s, action="counts")
    assert c.card["kind"] == "chart" and c.card["chart"]["values"] == [2, 0, 1, 1] and "nut allergy" in c
    with pytest.raises(ValueError):
        g(s, action="rsvp", guest="Ava", rsvp="perhaps")
    assert "confirm" in g(s, action="guest_remove", guest="Zara")
    assert "Took Zara" in g(s, action="guest_remove", guest="Zara", confirmed=True)


def test_seating_plan(s):
    party(s)
    g(s, action="guest_add", guests=["Ava", "Ben"], rsvp="yes")
    with pytest.raises(ValueError):
        g(s, action="seating")
    assert "2 tables" in g(s, action="tables", tables=2, seats_per_table=4)
    assert g(s, action="seat", guest="Ava", table="1") == "Ava is at Table 1, seat 1."
    assert "seat 2" in g(s, action="seat", guest="Ben", table="Table 1")
    with pytest.raises(ValueError):
        g(s, action="seat", guest="Ben", table="1", seat=1)
    with pytest.raises(ValueError):
        g(s, action="seat", guest="Ben", table="9")
    shown = g(s, action="seating")
    d = shown.card["data"]
    assert shown.card["kind"] == "events-seating" and d["tables"][0]["seats"][0]["guest"] == "Ava" and d["unseated"] == []
    assert "no longer" in g(s, action="seat", guest="Ava")
    assert g(s, action="seating").card["data"]["unseated"] == ["Ava"]


def test_invitation_and_thanks(s):
    party(s)
    text = g(s, action="invitation", style="kids", time="2pm", rsvp_by="1 November", host="Sam")
    assert "Village hall" in text and "2pm" in text and "Write a short kids invitation" in text
    with pytest.raises(ValueError):
        g(s, action="invitation", style="rude")
    with pytest.raises(ValueError):
        g(s, action="thanks")
    g(s, action="guest_add", guests=["Ava", "Ben"], rsvp="yes")
    assert "Noted" in g(s, action="thanks_sent", guest="Ava", gift="a book")
    shown = g(s, action="thanks")
    assert shown.card["items"][0]["label"] == "Ava: a book" and shown.card["items"][0]["say"]
    assert "Ticked" in g(s, action="thanks_sent", guest="Ava")
    assert g(s, action="thanks").card["items"][0]["done"] and "1 of 2" in g(s, action="thanks")


def test_budget_and_spending(s):
    party(s)
    with pytest.raises(ValueError):
        m(s, action="budget")
    m(s, action="budget_set", category="Cake", amount=40)
    m(s, action="budget_set", category="venue", amount=100)
    assert "£30 on cake" in m(s, action="spend", category="cake", amount=30, note="bakery")
    assert "over budget" in m(s, action="spend", category="venue", amount=290)
    shown = m(s, action="budget")
    rows = {r["cat"]: r for r in shown.card["data"]["rows"]}
    assert shown.card["kind"] == "events-budget" and rows["cake"] == {"cat": "cake", "planned": 40, "spent": 30}
    assert "over" in shown
    with pytest.raises(ValueError):
        m(s, action="spend", category="cake", amount="lots")


def test_suppliers_and_deposits(s):
    party(s)
    with pytest.raises(ValueError):
        m(s, action="suppliers")
    assert "balance £150" in m(s, action="supplier_add", supplier="Hall", role="venue", cost=200, deposit=50,
                               deposit_due="2026-09-01", balance_due="2026-11-01", phone="01234 567890")
    with pytest.raises(ValueError):
        m(s, action="supplier_add", supplier="DJ", cost=100, deposit=150)
    shown = m(s, action="suppliers")
    assert shown.card["rows"][0][3] == "£50 due 2026-09-01" and "Overdue: Hall deposit" in shown
    assert "paid (£50)" in m(s, action="supplier_pay", supplier="hall")
    assert "already" in m(s, action="supplier_pay", supplier="hall")
    assert "paid (£150)" in m(s, action="supplier_pay", supplier="hall", part="balance")
    assert m(s, action="budget").card["data"]["total"]["spent"] == 200
    assert m(s, action="suppliers").card["rows"][0][3] == "paid"
    with pytest.raises(ValueError):
        m(s, action="supplier_pay", supplier="Hall", part="tip")


def test_menu_and_food_calculator(s):
    party(s)
    with pytest.raises(ValueError):
        m(s, action="menu")
    assert "Mains" in m(s, action="menu_add", course="mains", dishes=["Pizza", "Salad"])
    m(s, action="menu_add", dishes=["Pizza", "Chips"])
    g(s, action="guest_add", guest="Ava", rsvp="yes", dietary="vegan", plus_ones=1)
    menu = m(s, action="menu")
    assert menu.card["rows"][0] == ["Mains", "Pizza, Salad, Chips"] and menu.card["rows"][-1][1] == "vegan"
    calc = m(s, action="food_calc")
    assert dict(calc.card["rows"])["Sandwiches"] == "6 rounds" and "2 adults" in calc
    kids = m(s, action="food_calc", adults=10, children=10)
    assert dict(kids.card["rows"])["Cake"] == "20 slices" and dict(kids.card["rows"])["Crisps and nibbles"] == "700 g"
    with pytest.raises(ValueError):
        m(s, action="food_calc", adults=0)


def test_christmas_dinner_timetable():
    shown = run_async({"action": "christmas_dinner", "serve_at": "14:00", "turkey_kg": 5}, None)
    items = shown.card["data"]["items"]
    assert shown.card["kind"] == "events-timeline" and items[-1] == {**items[-1], "when": "14:00", "text": "Serve Christmas dinner"}
    assert any(i["text"].startswith("Turkey in") and i["when"] == "09:50" for i in items)
    assert [i["when"] for i in items] == sorted(i["when"] for i in items)
    with pytest.raises(ValueError):
        run_async({"action": "christmas_dinner", "serve_at": "late"}, None)


def test_kids_party_and_bags():
    shown = run_async({"action": "kids_party", "age": 7, "start_at": "15:00"}, None)
    d = shown.card["data"]
    assert d["items"][0]["when"] == "15:00" and "Treasure hunt" in d["note"]
    assert "Under 3s" in run_async({"action": "kids_party", "age": 2}, None).card["data"]["note"]
    bags = run_async({"action": "party_bags", "children": 12}, None)
    assert bags.card["kind"] == "list" and bags.card["items"][0]["label"].endswith(": 12")
    with pytest.raises(ValueError):
        run_async({"action": "kids_party"}, None)


def test_memory_note_saved_in_memory_folder(s, tmp_path):
    with pytest.raises(ValueError):
        run_async({"action": "memory_note", "note": "x"}, s)
    party(s)
    shown = run_async({"action": "memory_note", "note": "Mia loved the treasure hunt."}, s)
    assert shown.card["kind"] == "file"
    saved = list((tmp_path / "Personal").glob("Memories*"))
    assert saved and "treasure hunt" in saved[0].read_text()


def forecast(request):
    if "geocoding" in str(request.url):
        return httpx.Response(200, json={"results": [{"name": "Leeds", "latitude": 53.8, "longitude": -1.55}]})
    days = [f"2026-09-{d}" for d in range(29, 31)] + [f"2026-10-{d:02d}" for d in range(1, 16)]
    n = len(days)
    return httpx.Response(200, json={"daily": {
        "time": days, "weathercode": [61] * n, "temperature_2m_max": [14] * n, "temperature_2m_min": [8] * n,
        "precipitation_probability_max": [70] * n, "wind_speed_10m_max": [20] * n}})


def test_weather_only_within_two_weeks(s):
    p(s, action="create", name="Garden lunch", date="2026-10-05", kind="gathering")
    shown = run_async({"action": "weather"}, s, forecast)
    assert shown.card["kind"] == "table" and "rain" in shown and "indoor backup" in shown
    p(s, action="create", name="Far off", date="2026-12-25")
    with pytest.raises(ValueError, match="14 days"):
        run_async({"action": "weather", "name": "Far off"}, s, forecast)
    p(s, action="create", name="Gone", date="2026-09-01")
    with pytest.raises(ValueError, match="already happened"):
        run_async({"action": "weather", "name": "Gone"}, s, forecast)


def test_weather_failure_is_friendly(s):
    p(s, action="create", name="Garden lunch", date="2026-10-05")
    with pytest.raises(ValueError):
        run_async({"action": "weather"}, s)


def test_unknown_actions(s):
    for fn in (p, g, m):
        with pytest.raises(ValueError):
            fn(s, action="mystery")
    with pytest.raises(ValueError):
        run_async({"action": "mystery"}, s)


def test_through_tools_run_tool(s):
    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(500))) as http:
            first = await tools._run_tool("event_plan", {"action": "create", "name": "Party", "date": "2027-01-01"}, s, http)
            second = await tools._run_tool("event_extras", {"action": "party_bags"}, s, http)
            return first, second

    first, second = asyncio.run(go())
    assert "Saved Party" in first and second.card["kind"] == "list"
