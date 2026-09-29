import math
from datetime import timedelta

import pytest

import homestore as hs
import photo_calc
import photo_gear
import photo_ideas
import photo_shoots
import screen
import tools
from config import Settings


@pytest.fixture
def s(tmp_path):
    return Settings(memory_dir=str(tmp_path))


def calc(s, **args):
    return photo_calc.run_tool("photo_calc", args, s)


def shoots(s, **args):
    return photo_shoots.run_tool("photo_shoots", args, s)


def gear(s, **args):
    return photo_gear.run_tool("photo_gear", args, s)


def ideas(s, **args):
    return photo_ideas.run_tool("photo_ideas", args, s)


def rows(out):
    return {r[0]: r[1] for r in out.card["rows"]}


def test_registered_and_small():
    names = {t["name"] for t in tools.client_tool_definitions(Settings())}
    for module in (photo_calc, photo_shoots, photo_gear, photo_ideas):
        assert module in tools.ABILITIES
        (tool,) = module.tool_definitions()
        assert tool["name"] in names and tool["input_schema"]["additionalProperties"] is False
    assert {"photo-dof", "photo-fov", "photo-crop", "photo-shots", "photo-progress", "photo-grid"} <= screen.EXTRA_KINDS


def test_every_action_is_declared():
    enum = photo_calc.tool_definitions()[0]["input_schema"]["properties"]["action"]["enum"]
    assert set(enum) == set(photo_calc.ALL) and len(enum) == 15
    for module in (photo_shoots, photo_gear, photo_ideas):
        enum = module.tool_definitions()[0]["input_schema"]["properties"]["action"]["enum"]
        assert list(enum) == list(module.ACTIONS)


# ---- calculators ---------------------------------------------------------------------------------

def test_exposure_solves_shutter(s):
    out = calc(s, action="exposure", aperture=2.8, shutter="1/125", iso=100, new_aperture=8, new_iso=100)
    assert isinstance(out, screen.Shown) and out.card["kind"] == "table"
    assert "f/8, 1/15 s at ISO 100" in out


def test_exposure_solves_iso_and_aperture(s):
    out = calc(s, action="exposure", aperture=4, shutter="1/60", iso=100, new_aperture=2, new_shutter="1/250")
    assert rows(out)["Same exposure"].endswith("ISO 100")
    out = calc(s, action="exposure", aperture=4, shutter="1/60", iso=100, new_shutter="1/250", new_iso=400)
    assert rows(out)["Same exposure"].startswith("f/4")


def test_exposure_ladder_when_nothing_changes(s):
    out = calc(s, action="exposure", aperture=2.8, shutter="1/125", iso=100)
    assert len(out.card["rows"]) == 8 and out.card["rows"][2][:2] == ["f/2.8", "1/125 s"]


def test_ev_both_ways(s):
    out = calc(s, action="ev", aperture=16, shutter="1/100", iso=100)
    assert rows(out)["EV at ISO 100"] == "14.6" and "EV 14.6" in out
    out = calc(s, action="ev", ev=15, aperture=16, iso=100)
    assert rows(out)["Shutter"] == "1/125 s"


def test_sunny16(s):
    out = calc(s, action="sunny16", iso=200)
    assert out.card["rows"][0] == ["Sunny, hard shadows", "f/16", "1/200 s"]


def test_handheld(s):
    out = calc(s, action="handheld", focal_mm=100, sensor="aps-c")
    assert out.card["rows"][0][0] == "None" and "1/160 s" in out


def test_dof_and_hyperfocal(s):
    out = calc(s, action="dof", focal_mm=50, aperture=1.8, distance_m=2)
    assert out.card["kind"] == "photo-dof"
    d = out.card["data"]
    assert d["near"] < 2 < d["far"] and math.isclose(d["hyperfocal"], 46.35, abs_tol=0.05)
    far = calc(s, action="dof", focal_mm=24, aperture=11, distance_m=10)
    assert far.card["data"]["far"] is None and "infinity" in far
    hyper = calc(s, action="hyperfocal", focal_mm=24, aperture=8)
    assert hyper.card["kind"] == "table" and rows(hyper)["Sharp to"] == "infinity"
    assert rows(hyper)["Hyperfocal distance"] == "2.42 m"


def test_dof_feet(s):
    out = calc(s, action="dof", focal_mm=35, aperture=2, distance_ft=10)
    assert math.isclose(out.card["data"]["focus"], 3.048, abs_tol=0.001)


def test_fov(s):
    out = calc(s, action="fov", focal_mm=50, sensor="aps-c", distance_m=10)
    assert out.card["kind"] == "photo-fov"
    assert math.isclose(out.card["data"]["angle"], 26.6, abs_tol=0.1) and "76 mm" in out
    assert calc(s, action="fov", focal_mm=35, crop_factor=2).card["data"]["facts"][3][1] == "70 mm"


def test_star_rules(s):
    out = calc(s, action="star", focal_mm=14, aperture=2.8, megapixels=24)
    assert rows(out)["500 rule"] == "35.7 s" and rows(out)["NPF rule"] == "19.9 s"
    assert out.card["rows"][2][2] == "full frame"


def test_nd(s):
    out = calc(s, action="nd", shutter="1/125", nd_stops=10)
    assert "8.2 s" in out and len(out.card["rows"]) == 8
    assert "8.2 s" in calc(s, action="nd", shutter="1/125", nd_factor=1024)
    assert calc(s, action="nd", shutter="1/125", nd_density=3.0).card["rows"][0][2] == "8 s"
    need = calc(s, action="nd", shutter="1/125", target_shutter=30)
    assert rows(need)["Closest filter"] == "ND32000"


def test_flash(s):
    out = calc(s, action="flash", guide_number=40, aperture=4)
    assert "10.0 metres" in out
    assert "f/5.6" in calc(s, action="flash", guide_number=40, distance_m=5, flash_power="1/2")
    assert "guide number" in calc(s, action="flash", guide_number=40, distance_m=5, aperture=8)


def test_print(s):
    out = calc(s, action="print", width_px=6000, height_px=4000)
    assert out.card["rows"][0][0] == "6 x 4 in" and "51 by 34" in out
    back = calc(s, action="print", print_width=30, print_height=20)
    assert rows(back)["Pixels needed"] == "3544 x 2363"
    inches = calc(s, action="print", print_width=10, print_height=8, print_unit="in", dpi=200)
    assert rows(inches)["Pixels needed"] == "2000 x 1600"


def test_crop(s):
    out = calc(s, action="crop", width_px=6000, height_px=4000, ratio="16:9")
    d = out.card["data"]
    assert out.card["kind"] == "photo-crop" and (d["cw"], d["ch"], d["y"]) == (6000, 3375, 312)
    tall = calc(s, action="crop", width_px=6000, height_px=4000, ratio="4:5", anchor="left")
    assert (tall.card["data"]["cw"], tall.card["data"]["ch"], tall.card["data"]["x"]) == (3200, 4000, 0)
    assert len(calc(s, action="crop", width_px=6000, height_px=4000).card["rows"]) == 11


def test_video_and_card(s):
    out = calc(s, action="video", preset="4k30", card_gb=128)
    assert rows(out)["Recording time"] == "2 h 38 min"
    need = calc(s, action="video", bitrate_mbps=100, minutes=30)
    assert rows(need)["Storage needed"] == "22.5 GB" and rows(need)["Card to buy"] == "32 GB or more"
    assert len(calc(s, action="video").card["rows"]) == 10
    photos = calc(s, action="card", card_gb=64, megapixels=24)
    assert photos.card["rows"][0][1] == "1,549"
    assert calc(s, action="card", card_gb=64, file_mb=10).card["rows"][0][1] == "5,952"


def test_timelapse(s):
    out = calc(s, action="timelapse", interval_s=5, duration_min=120)
    assert rows(out)["Frames"] == "1,440" and rows(out)["Clip length"] == "57.6 s"
    assert rows(calc(s, action="timelapse", interval_s=5, clip_s=10, fps=25, file_mb=25))["Storage"] == "6.2 GB"
    solved = calc(s, action="timelapse", duration_min=60, clip_s=30, fps=24)
    assert rows(solved)["Interval"].startswith("5.0")


@pytest.mark.parametrize("args", [
    {"action": "nope"}, {"action": "exposure", "aperture": 2.8, "shutter": "fast"}, {"action": "nd", "shutter": "1/125"},
    {"action": "fov", "focal_mm": 50, "sensor": "banana"}, {"action": "timelapse", "interval_s": 5},
    {"action": "flash", "aperture": 4}, {"action": "video", "card_gb": 64}, {"action": "crop", "width_px": 10, "height_px": 10, "ratio": "x"},
    {"action": "print"}, {"action": "card", "card_gb": 64, "format": "tiff"},
])
def test_calc_friendly_errors(s, args):
    with pytest.raises(ValueError):
        calc(s, **args)


# ---- shot lists and projects ---------------------------------------------------------------------

def test_shot_list_lifecycle(s):
    out = shoots(s, action="shots_new", name="Sam's wedding", type="wedding")
    assert out.card["kind"] == "photo-shots" and out.card["data"]["type"] == "wedding"
    assert out.card["data"]["shots"][0]["say"].startswith("Tick off shot 1")
    out = shoots(s, action="shots_tick", name="wedding", shot=1)
    assert out.card["data"]["shots"][0]["done"] and out.card["data"]["shots"][0]["say"].startswith("Untick")
    out = shoots(s, action="shots_tick", name="wedding", shot="rings")
    assert "1 of 14" in out
    out = shoots(s, action="shots_add", name="wedding", shots=["Bouquet toss"])
    assert out.card["data"]["shots"][-1]["text"] == "Bouquet toss"
    out = shoots(s, action="shots_tick", name="wedding", shot="bouquet")
    assert "2 of 15" in out
    out = shoots(s, action="shots_tick", name="wedding", shot=1, done=False)
    assert "1 of 15" in out
    out = shoots(s, action="shots_remove", name="wedding", shot="bouquet")
    assert len(out.card["data"]["shots"]) == 14
    assert shoots(s, action="shots_show", name="wedding").card["kind"] == "photo-shots"
    out = shoots(s, action="shots_reset", name="wedding")
    assert not any(x["done"] for x in out.card["data"]["shots"])
    lists = shoots(s, action="shots_lists")
    assert lists.card["rows"][0][:2] == ["Sam's wedding", "0 of 14"]


def test_shot_list_custom_and_errors(s):
    out = shoots(s, action="shots_new", name="Park", shots=["Ducks", "Trees"])
    assert len(out.card["data"]["shots"]) == 2
    with pytest.raises(ValueError):
        shoots(s, action="shots_new", name="Park", shots=["x"])
    with pytest.raises(ValueError):
        shoots(s, action="shots_new", name="Empty")
    with pytest.raises(ValueError):
        shoots(s, action="shots_tick", name="Park", shot="zebra")
    with pytest.raises(ValueError):
        shoots(s, action="shots_show", name="Nowhere")
    assert shoots(s, action="shots_lists").card["kind"] == "table"


def test_shot_list_delete_needs_confirmation(s):
    shoots(s, action="shots_new", name="Park", shots=["Ducks"])
    assert "confirm" in shoots(s, action="shots_delete", name="Park")
    assert hs.load(s, "photo-shots.json", {})
    assert "Deleted" in shoots(s, action="shots_delete", name="Park", confirmed=True)
    assert "Park" not in hs.load(s, "photo-shots.json", {})


def test_shot_starters(s):
    index = shoots(s, action="shots_starter")
    assert index.card["kind"] == "table" and len(index.card["rows"]) >= 12
    out = shoots(s, action="shots_starter", type="street")
    assert out.card["kind"] == "photo-shots" and out.card["buttons"][0]["label"] == "Save this list"
    with pytest.raises(ValueError):
        shoots(s, action="shots_starter", type="underwater")


def test_daily_project(s, monkeypatch):
    day = hs.today()
    start = (day - timedelta(days=4)).isoformat()
    out = shoots(s, action="project_start", name="365", target=365, start=start)
    assert out.card["kind"] == "photo-progress" and len(out.card["data"]["cells"]) == 365
    shoots(s, action="project_log", name="365", note="Sunrise", date=(day - timedelta(days=1)).isoformat())
    out = shoots(s, action="project_log", name="365", note="Sunset")
    d = out.card["data"]
    assert d["done"] == 2 and d["cells"][3] and d["cells"][4] and not d["cells"][0]
    facts = dict(d["facts"])
    assert facts["Day"] == "5 of 365" and facts["Missed"] == "3" and facts["Streak"] == "2 days"
    assert d["notes"][-1].endswith("Sunset")
    out = shoots(s, action="project_log", name="365", note="Sunset again")
    assert out.card["data"]["done"] == 2
    assert shoots(s, action="project_progress", name="365").card["kind"] == "photo-progress"
    assert shoots(s, action="project_list").card["rows"] == [["365", "daily", "2 of 365"]]


def test_count_project_and_delete(s):
    out = shoots(s, action="project_start", name="100 portraits", target=100, project_kind="count")
    assert out.card["data"]["kind"] == "count"
    out = shoots(s, action="project_log", name="portraits")
    out = shoots(s, action="project_log", name="portraits")
    assert out.card["data"]["done"] == 2 and out.card["data"]["cells"][:3] == [True, True, False]
    with pytest.raises(ValueError):
        shoots(s, action="project_start", name="100 portraits")
    with pytest.raises(ValueError):
        shoots(s, action="project_start", name="Odd", project_kind="weekly")
    assert "confirm" in shoots(s, action="project_delete", name="portraits")
    assert "Deleted" in shoots(s, action="project_delete", name="portraits", confirmed=True)
    assert shoots(s, action="project_list").card["rows"] == []


def test_shoots_unknown_action(s):
    with pytest.raises(ValueError):
        shoots(s, action="dance")


# ---- gear ----------------------------------------------------------------------------------------

def test_gear_lifecycle(s):
    out = gear(s, action="gear_add", name="Sony A6400", kind="camera", sensor="aps-c", megapixels=24)
    assert isinstance(out, screen.Shown) and out.card["kind"] == "table"
    gear(s, action="gear_add", name="Sigma 56mm", kind="lens", focal_min=56, max_aperture=1.4, mount="E")
    gear(s, action="gear_add", name="Tamron 28-75", kind="lens", focal_min=28, focal_max=75, max_aperture=2.8)
    gear(s, action="gear_add", name="Peak Design tripod", kind="tripod")
    listed = gear(s, action="gear_list")
    assert len(listed.card["rows"]) == 4 and listed.card["rows"][0][1] == "camera"
    assert len(gear(s, action="gear_list", kind="lens").card["rows"]) == 2
    show = gear(s, action="gear_show", name="sigma")
    r = rows(show)
    assert r["Focal length"] == "56 mm" and r["Equivalent"] == "86 to 86 mm on full frame"
    assert r["Widest aperture"] == "f/1.4"
    updated = gear(s, action="gear_update", name="Sigma 56mm", notes="Sharp wide open")
    assert rows(updated)["Notes"] == "Sharp wide open"
    with pytest.raises(ValueError):
        gear(s, action="gear_add", name="Sigma 56mm", kind="lens")
    with pytest.raises(ValueError):
        gear(s, action="gear_update", name="Sigma 56mm")
    with pytest.raises(ValueError):
        gear(s, action="gear_add", name="Thing", kind="spaceship")
    assert "confirm" in gear(s, action="gear_remove", name="Sigma 56mm")
    assert "Removed" in gear(s, action="gear_remove", name="Sigma 56mm", confirmed=True)
    assert len(gear(s, action="gear_list").card["rows"]) == 3


def test_empty_gear_list(s):
    out = gear(s, action="gear_list")
    assert out.card["rows"] == [] and "empty" in out


def test_pack_list_uses_your_gear(s):
    gear(s, action="gear_add", name="Sony A6400", kind="camera")
    gear(s, action="gear_add", name="Peak Design tripod", kind="tripod")
    out = gear(s, action="pack_list", shoot="landscape")
    assert out.card["kind"] == "list" and out.card.get("checks")
    labels = [i["label"] for i in out.card["items"]]
    assert "Camera body (yours: Sony A6400)" in labels
    assert "Sturdy tripod (yours: Peak Design tripod)" in labels
    assert "ND filters (not in your gear list)" in labels and "2 are in your gear list" in out
    with pytest.raises(ValueError):
        gear(s, action="pack_list", shoot="rocket launch")


def test_lens_for(s):
    gear(s, action="gear_add", name="Sony A6400", kind="camera", sensor="aps-c")
    gear(s, action="gear_add", name="Sigma 56mm", kind="lens", focal_min=56, max_aperture=1.4)
    gear(s, action="gear_add", name="Sigma 16mm", kind="lens", focal_min=16, max_aperture=1.4)
    out = gear(s, action="lens_for", subject="portrait")
    assert out.card["rows"][0][0] == "Sigma 56mm" and "Sigma 56mm" in out
    none = gear(s, action="lens_for", subject="wildlife")
    assert none.card["rows"][0][0] == "None of your lenses" and "None of your lenses" in none
    guide = gear(s, action="lens_for")
    assert guide.card["kind"] == "table" and len(guide.card["rows"]) >= 10


# ---- ideas ---------------------------------------------------------------------------------------

def test_composition_tips(s):
    out = ideas(s, action="composition", tip="rule of thirds")
    assert out.card["kind"] == "photo-grid" and out.card["data"]["overlay"] == "thirds"
    assert ideas(s, action="composition", tip="leading").card["data"]["overlay"] == "leading"
    with pytest.raises(ValueError):
        ideas(s, action="composition", tip="zzz")
    lst = ideas(s, action="composition_list")
    assert lst.card["kind"] == "list" and len(lst.card["items"]) == 12 and lst.card["items"][0]["say"]


def test_every_composition_has_a_drawing():
    import re
    from pathlib import Path
    js = Path(__file__).resolve().parent.parent.joinpath("frontend", "popup-photo.js").read_text(encoding="utf-8")
    import photo_data
    for key, (_, _, _, overlay) in photo_data.COMPOSITION.items():
        assert re.search(rf"^\s+{overlay}\(g\)", js, re.M), key


def test_challenges(s, monkeypatch):
    out = ideas(s, action="challenge")
    assert out.card["kind"] == "text" and out.card["title"] == "Photo challenge of the day"
    assert ideas(s, action="challenge").card["text"] == out.card["text"]
    rand = ideas(s, action="challenge_random")
    assert rand.card["buttons"][0]["label"] == "Another one"


def test_walk(s):
    out = ideas(s, action="walk", place="seaside", minutes=60)
    assert out.card["kind"] == "list" and out.card.get("checks") and len(out.card["items"]) == 6
    assert out.card["items"][0]["label"].startswith("Theme:") and "60 minute" in out
    assert ideas(s, action="walk").card["title"].startswith("Photo walk: town")
    with pytest.raises(ValueError):
        ideas(s, action="walk", place="moon")


def test_settings_and_terms(s):
    out = ideas(s, action="settings", scene="stars")
    assert rows(out)["Focus"].startswith("Manual") and "ISO 1600 to 3200" in out
    assert len(ideas(s, action="settings").card["rows"]) >= 12
    with pytest.raises(ValueError):
        ideas(s, action="settings", scene="volcano")
    out = ideas(s, action="term", word="bokeh")
    assert out.card["kind"] == "text" and "background" in out
    assert ideas(s, action="term", word="ISO").card["title"] == "Iso"
    assert ideas(s, action="term").card["kind"] == "list"
    with pytest.raises(ValueError):
        ideas(s, action="term", word="flibbertigibbet")
    with pytest.raises(ValueError):
        ideas(s, action="dance")
