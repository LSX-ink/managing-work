import asyncio
from datetime import date

import httpx
import pytest

import memory
import screen
import tools
import widgets
from config import Settings

DAY = date(2026, 9, 28)


def run(args, s=None):
    return widgets.run_tool("open_widget", args, s or Settings(), None, DAY)


def data_of(shown):
    assert isinstance(shown, screen.Shown)
    assert shown.card["kind"] == "widget" and shown.card["id"].startswith("widget-")
    return shown.card["data"]


@pytest.mark.parametrize("action", sorted(widgets.WIDGETS))
def test_every_widget_pops_up(action):
    shown = run({"action": action})
    assert data_of(shown)["widget"] == action
    assert shown.card["title"] == widgets.WIDGETS[action]
    assert str(shown).startswith("Here")


def test_calculator_and_converter_start_values():
    assert data_of(run({"action": "calculator", "expression": "12*3"}))["expression"] == "12*3"
    d = data_of(run({"action": "unit_converter", "category": "temperature", "value": 350}))
    assert d == {"widget": "unit_converter", "category": "temperature", "value": 350.0}
    assert data_of(run({"action": "unit_converter"}))["category"] == "length"
    with pytest.raises(ValueError):
        run({"action": "unit_converter", "category": "speed"})


def test_sketch_pad_and_notepad_save_into_a_real_folder():
    assert data_of(run({"action": "sketch_pad"}))["folder"] == "Ideas"
    assert data_of(run({"action": "sketch_pad", "folder": "work"}))["folder"] == "Work"
    with pytest.raises(ValueError):
        run({"action": "notepad", "folder": "Nowhere"})
    d = data_of(run({"action": "notepad", "text": "Milk", "title": "List"}))
    assert d["text"] == "Milk" and d["title"] == "List"


def test_notepad_opens_an_existing_note():
    s = Settings()
    memory.save_note(s, "Personal", "Holiday plans", "Pack the tent.")
    shown = run({"action": "notepad", "note": "holiday"}, s)
    d = data_of(shown)
    assert d["title"] == "Holiday plans" and d["text"] == "Pack the tent." and d["folder"] == "Personal"
    assert "opened Holiday plans" in shown
    memory.save_file(s, "Personal", "photo.png", b"\x89PNG")
    with pytest.raises(ValueError):
        run({"action": "notepad", "note": "photo.png"}, s)


def test_timers():
    d = data_of(run({"action": "countdown", "minutes": 2, "seconds": 30}))
    assert d["seconds"] == 150 and d["autostart"] is True
    assert data_of(run({"action": "countdown"})) == {"widget": "countdown", "seconds": 300, "autostart": False}
    assert data_of(run({"action": "pomodoro", "minutes": 50, "break_minutes": 10}))["work"] == 50
    assert data_of(run({"action": "pomodoro"}))["rest"] == 5
    with pytest.raises(ValueError):
        run({"action": "countdown", "minutes": -1})
    assert data_of(run({"action": "stopwatch"})) == {"widget": "stopwatch"}


def test_world_clocks_map_cities_to_zones():
    shown = run({"action": "world_clocks", "cities": ["Tokyo", "Cape Town", "Europe/Oslo", "Atlantis"]})
    assert data_of(shown)["clocks"] == [{"label": "Tokyo", "zone": "Asia/Tokyo"},
                                        {"label": "Cape Town", "zone": "Africa/Johannesburg"},
                                        {"label": "Oslo", "zone": "Europe/Oslo"}]
    assert "Atlantis" in shown
    assert len(data_of(run({"action": "world_clocks"}))["clocks"]) == 4
    with pytest.raises(ValueError):
        run({"action": "world_clocks", "cities": ["Atlantis"]})


def test_calendar_month():
    assert data_of(run({"action": "calendar"}))["month"] == 9
    d = data_of(run({"action": "calendar", "month": "2027-02"}))
    assert (d["year"], d["month"]) == (2027, 2)
    with pytest.raises(ValueError):
        run({"action": "calendar", "month": "February"})


def test_dice_and_coin():
    assert widgets.parse_dice("2d6") == {"count": 2, "sides": 6}
    assert widgets.parse_dice("D20") == {"count": 1, "sides": 20}
    for bad in ("3d7", "11d6", "six"):
        with pytest.raises(ValueError):
            widgets.parse_dice(bad)
    assert data_of(run({"action": "dice", "dice": "3d8"}))["count"] == 3
    assert data_of(run({"action": "coin_flip"})) == {"widget": "coin_flip"}


def test_colour_metronome_ambient_breathing():
    assert data_of(run({"action": "colour_picker", "colour": "FF8800"}))["colour"] == "#ff8800"
    with pytest.raises(ValueError):
        run({"action": "colour_picker", "colour": "orange"})
    assert data_of(run({"action": "metronome", "bpm": 120}))["bpm"] == 120
    with pytest.raises(ValueError):
        run({"action": "metronome", "bpm": 500})
    d = data_of(run({"action": "ambient_sound", "sound": "brown", "minutes": 30}))
    assert d["sound"] == "brown" and d["minutes"] == 30
    assert data_of(run({"action": "ambient_sound"}))["sound"] == "rain"
    assert data_of(run({"action": "breathing", "pattern": "4-7-8"}))["pattern"] == "4-7-8"
    with pytest.raises(ValueError):
        run({"action": "breathing", "pattern": "fast"})


def test_typing_test_and_picker_wheel():
    assert data_of(run({"action": "typing_test"})) == {"widget": "typing_test"}
    d = data_of(run({"action": "picker_wheel", "options": ["Pizza", " ", "Curry"]}))
    assert d["options"] == ["Pizza", "Curry"]
    with pytest.raises(ValueError):
        run({"action": "picker_wheel", "options": [str(n) for n in range(30)]})
    with pytest.raises(ValueError):
        run({"action": "juggler"})


def test_open_widget_through_alfred():
    names = {t["name"] for t in tools.client_tool_definitions(Settings())}
    assert "open_widget" in names
    shown = []

    async def page(message):
        shown.append(message)

    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(500))) as http:
            return await tools.run_tool("open_widget", {"action": "calculator"}, Settings(), http, page)

    assert "calculator" in asyncio.run(go())
    assert shown and shown[0]["card"]["data"]["widget"] == "calculator"
