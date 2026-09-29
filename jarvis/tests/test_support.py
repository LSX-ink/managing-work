import asyncio
import json
from datetime import datetime

import httpx
import pytest
from PIL import Image

import screen
import support_care as care
import support_day as day
import support_people as people
import support_see as see
import tools
from config import Settings

NOW = datetime(2026, 9, 29, 9, 30)


@pytest.fixture
def s(tmp_path):
    return Settings(memory_dir=str(tmp_path), city="Leeds")


def d(s, **a):
    return day.run_tool("support_day", a, s, None, now=NOW)


def p(s, **a):
    return people.run_tool("support_people", a, s, None)


def c(s, now=NOW, **a):
    return care.run_tool("support_care", a, s, None, now=now)


def v(s, **a):
    return see.run_tool("support_see", a, s, None)


def test_registered():
    for mod in (day, people, care, see):
        assert mod in tools.ABILITIES and len(mod.tool_definitions()) == 1
    for kind in ("support-today", "support-home", "support-steps", "support-people", "support-big", "support-magnify"):
        assert kind in screen.EXTRA_KINDS


def test_through_tools_run_tool(s):
    async def go():
        async with httpx.AsyncClient() as http:
            return await tools._run_tool("support_day", {"action": "simple_mode"}, s, http)

    assert asyncio.run(go()).card["kind"] == "support-home"


def test_today_and_plan(s):
    assert d(s, action="plan_add", text="Doctor", time="14:30").startswith("Added")
    d(s, action="plan_add", text="Feed the cat")
    shown = d(s, action="today")
    assert shown.card["kind"] == "support-today" and "Tuesday 29 September, morning" in shown
    assert shown.card["data"]["part"] == "morning" and len(shown.card["data"]["plan"]) == 2
    assert d(s, action="plan_show").card["kind"] == "list"
    assert d(s, action="plan_done", text="doct") == "Ticked off Doctor."
    assert d(s, action="plan_show").card["items"][0]["done"]
    assert "nothing planned" in d(s, action="plan_show", day="tomorrow")
    with pytest.raises(ValueError):
        d(s, action="plan_add", text="x", time="99")
    with pytest.raises(ValueError):
        d(s, action="plan_done", text="zzz")


def test_simple_mode_has_six_buttons(s):
    assert len(d(s, action="simple_mode").card["data"]["buttons"]) == 6


def test_routines(s):
    with pytest.raises(ValueError):
        d(s, action="routine_show", routine="morning")
    assert "3 steps" in d(s, action="routine_set", routine="morning", items=["Wash", "Dress", "Pills"])
    assert d(s, action="routine_show", routine="morning").card["checks"]
    shown = d(s, action="routine_tick", routine="morning", text="wash")
    assert shown.card["items"][0]["done"] and "next is Dress" in shown
    with pytest.raises(ValueError):
        d(s, action="routine_set", routine="lunch", items=["x"])


def test_break_and_repeat_slower(s, tmp_path):
    assert d(s, action="break").card["buttons"][0]["say"].startswith("Ground me")
    with pytest.raises(ValueError):
        d(s, action="repeat_slower")
    (tmp_path / ".recent-chat.json").write_text(json.dumps([{"user": "hi", "reply": "Turn left."}]))
    assert d(s, action="repeat_slower").endswith("Turn left.")


def test_people(s, tmp_path):
    (tmp_path / "Personal").mkdir(exist_ok=True)
    Image.new("RGB", (8, 8), "red").save(tmp_path / "Personal" / "sam.jpg")
    assert p(s, action="people_add", name="Sam", relation="grandson", photo="Personal/sam.jpg") == "Saved Sam, your grandson."
    shown = p(s, action="people_who", name="grandson")
    assert shown.card["kind"] == "support-people" and shown.card["data"]["people"][0]["src"].startswith("/screen/file")
    assert "grandson" in p(s, action="people_who", name="sam")
    assert p(s, action="people_list").card["kind"] == "support-people"
    with pytest.raises(ValueError):
        p(s, action="people_add", name="Kim", photo="Personal/missing.jpg")
    with pytest.raises(ValueError):
        p(s, action="people_who", name="nobody")
    assert "confirm" in p(s, action="people_remove", name="Sam")
    assert p(s, action="people_remove", name="Sam", confirmed=True) == "Removed Sam."
    assert isinstance(p(s, action="people_list"), screen.Shown)


def test_guides(s):
    assert p(s, action="guide_list").startswith("You haven't")
    p(s, action="guide_save", name="Washing machine", steps=["Open door", "Put clothes in", "Press start"])
    shown = p(s, action="guide_show", name="washing", step=2)
    assert shown.card["kind"] == "support-steps" and shown.card["data"]["index"] == 1 and "Put clothes in" in shown
    assert p(s, action="guide_list").card["kind"] == "list"
    with pytest.raises(ValueError):
        p(s, action="guide_save", name="Empty", steps=[])
    assert "confirm" in p(s, action="guide_delete", name="washing")
    assert p(s, action="guide_delete", name="washing", confirmed=True).startswith("Deleted")


def test_letter(s, tmp_path):
    assert "LETTER:\nPay £50" in p(s, action="letter", text="Pay £50 by Friday")
    (tmp_path / "Personal").mkdir()
    (tmp_path / "Personal" / "bill.txt").write_text("Gas bill 40 pounds", encoding="utf-8")
    assert "Gas bill" in p(s, action="letter", folder="Personal", filename="bill.txt")
    with pytest.raises(ValueError):
        p(s, action="letter")
    with pytest.raises(ValueError):
        p(s, action="bogus")


def test_medicines_check_twice(s):
    assert c(s, action="med_add", name="Aspirin", dose="75mg", times=["08:00"]) == "Saved Aspirin at 08:00."
    assert "Not yet" in c(s, action="med_today").card["rows"][0]
    assert "nothing is logged" in c(s, action="med_check", name="aspirin").lower()
    assert c(s, action="med_taken", name="Aspirin").startswith("Logged")
    assert "Yes, Aspirin" in c(s, action="med_check", name="Aspirin")
    assert c(s, action="med_taken", name="Aspirin").startswith("Stop")
    assert c(s, action="med_taken", name="Aspirin", confirmed=True).startswith("Logged")
    assert c(s, action="med_today").card["kind"] == "table"
    assert "confirm" in c(s, action="med_remove", name="Aspirin")
    assert c(s, action="med_remove", name="Aspirin", confirmed=True).startswith("Removed")
    assert "haven't listed" in c(s, action="med_today")


def test_checkin_and_handover(s):
    assert "calm break" in c(s, action="checkin", score=2, text="Bad night")
    c(s, action="checkin", score=4)
    shown = c(s, action="checkin_week")
    assert shown.card["kind"] == "chart" and shown.card["chart"]["values"][-1] == 3.0 and "Bad night" in shown
    with pytest.raises(ValueError):
        c(s, action="checkin", score=9)
    assert c(s, action="handover_add", text="Ate well, slept badly") == "Added to the handover notes."
    assert c(s, action="handover_show").card["rows"][0][1] == "Ate well, slept badly"
    assert "no handover" in c(s, action="handover_show", now=datetime(2027, 1, 1))
    assert "no check-ins" in c(s, now=datetime(2027, 1, 1), action="checkin_week")


def test_emergency_contact_and_lost(s):
    with pytest.raises(ValueError):
        c(s, action="emergency_show")
    with pytest.raises(ValueError):
        c(s, action="lost_help")
    with pytest.raises(ValueError):
        c(s, action="emergency_set")
    c(s, action="emergency_set", name="Ann Lee", address="4 High St, Leeds", gp="Dr Rao", allergies="Penicillin")
    shown = c(s, action="emergency_show")
    assert shown.card["kind"] == "support-big" and any(l["value"] == "Penicillin" for l in shown.card["data"]["lines"])
    with pytest.raises(ValueError):
        c(s, action="contact_show")
    c(s, action="contact_set", name="Jo", phone="07700 900123", relation="daughter")
    assert "07700 900123" in c(s, action="contact_show")
    lost = c(s, action="lost_help")
    assert "4 High St" in json.dumps(lost.card["data"]) and "07700" in json.dumps(lost.card["data"])
    with pytest.raises(ValueError):
        c(s, action="nope")


def test_magnifier_colours_and_big_shopping(s, tmp_path):
    (tmp_path / "Personal").mkdir()
    im = Image.new("RGB", (40, 40), (10, 20, 120))
    im.paste((240, 240, 240), (0, 0, 10, 40))
    im.save(tmp_path / "Personal" / "door.png")
    shown = v(s, action="magnifier", folder="Personal", filename="door.png")
    assert shown.card["kind"] == "support-magnify" and shown.card["data"]["src"].startswith("/screen/file")
    col = v(s, action="colours", folder="Personal", filename="door.png")
    assert col.card["kind"] == "table" and "dark blue" in col
    assert see.colour_word("#ff0000") == "red" and see.colour_word("#ffffff") == "white"
    assert see.colour_word("#808080") == "grey" and see.colour_word("#90ee90") == "light green"
    assert v(s, action="big_shopping") == "Your shopping list is empty."
    (tmp_path / "Shopping").mkdir(exist_ok=True)
    tools.shopping.add(s, ["milk", "bread"])
    assert v(s, action="big_shopping").card["data"]["lines"][1]["value"] == "bread"
    with pytest.raises(ValueError):
        v(s, action="magnifier", filename="missing.png")
    with pytest.raises(ValueError):
        v(s, action="nope")
