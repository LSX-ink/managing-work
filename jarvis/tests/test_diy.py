import pytest

import diy_calc
import diy_guide
import diy_projects
import diy_room
import screen
import tools
from config import Settings


@pytest.fixture
def s(tmp_path):
    return Settings(memory_dir=str(tmp_path))


def calc(s, **args):
    return diy_calc.run_tool("diy_calc", args, s)


def room(s, **args):
    return diy_room.run_tool("diy_room", args, s)


def guide(s, **args):
    return diy_guide.run_tool("diy_guide", args, s)


def proj(s, **args):
    return diy_projects.run_tool("diy_projects", args, s)


def rows(out):
    return {r[0]: r[1] for r in out.card["rows"]}


def test_registered_and_small():
    names = {t["name"] for t in tools.client_tool_definitions(Settings())}
    for module in (diy_calc, diy_room, diy_guide, diy_projects):
        assert module in tools.ABILITIES
        (tool,) = module.tool_definitions()
        assert tool["name"] in names and tool["input_schema"]["additionalProperties"] is False
    assert {"diy-plan", "diy-guide"} <= screen.EXTRA_KINDS


# ---- calculators ---------------------------------------------------------------------------------

def test_paint(s):
    out = calc(s, what="paint", length=4, width=3, height=2.4, doors=1, windows=1, coats=2)
    assert isinstance(out, screen.Shown) and out.card["kind"] == "table"
    area = 2 * 7 * 2.4 - 1.6 - 1.2
    assert rows(out)["Area to paint"] == f"{area:.1f} m²"
    assert rows(out)["Paint needed"] == f"{area * 2 / 12:.1f} L"
    assert "litres of paint" in out
    assert diy_calc._tins(6.1) == "1 x 5 L + 1 x 2.5 L"


def test_paint_ceiling_and_cm(s):
    out = calc(s, what="paint", length=400, width=300, height=240, unit="cm", include_ceiling=True, coats=1)
    assert rows(out)["Area to paint"] == f"{2 * 7 * 2.4 + 12:.1f} m²"


def test_paint_needs_sizes(s):
    with pytest.raises(ValueError, match="height"):
        calc(s, what="paint", length=4, width=3)


def test_wallpaper(s):
    out = calc(s, what="wallpaper", length=4, width=3, height=2.4)
    r = rows(out)
    assert r["Drops (strips)"] == "27" and r["Drops per roll"] == "4" and r["Rolls to buy"] == "7"
    pattern = calc(s, what="wallpaper", length=4, width=3, height=2.4, pattern_repeat_m=0.64)
    assert rows(pattern)["Length of each drop"] == "2.56 m"


def test_floor_tiles_and_grout(s):
    out = calc(s, what="floor_tiles", area_m2=10, tile_w_mm=300, joint_mm=3, pack_m2=1.44)
    assert rows(out)["Tiles to buy"] == "120"
    assert rows(out)["Boxes"] == "8"
    g = calc(s, what="grout", area_m2=10, tile_w_mm=300, tile_h_mm=300, joint_mm=3, tile_thickness_mm=8)
    assert "kilos of grout" in g and g.card["kind"] == "table"


def test_laminate_skirting(s):
    out = calc(s, what="laminate", length=5, width=4)
    assert rows(out)["Packs to buy"] == "10"
    sk = calc(s, what="skirting", length=5, width=4, doors=1)
    assert rows(sk)["Run of wall"] == "17.2 m" and rows(sk)["Boards to buy"] == "8"
    assert rows(calc(s, what="skirting", run_m=10, board_length_m=3))["Boards to buy"] == "4"


def test_fence_concrete_decking(s):
    out = calc(s, what="fence", run_m=9)
    assert rows(out)["Panels"] == "5" and rows(out)["Posts"] == "6"
    with pytest.raises(ValueError, match="fence run"):
        calc(s, what="fence")
    c = calc(s, what="concrete", length=2, width=2, depth_mm=100)
    assert rows(c)["Volume"] == "0.40 m³"
    d = calc(s, what="decking", length=4, width=3)
    assert int(rows(d)["Boards"]) >= 30 and "decking boards" in d


def test_plasterboard_gravel_turf_bricks(s):
    p = calc(s, what="plasterboard", length=4, width=3, height=2.4)
    assert p.card["kind"] == "table" and "sheets" in p
    g = calc(s, what="gravel", area_m2=20, depth_mm=50)
    assert rows(g)["Weight"] == "1.60 tonnes"
    t = calc(s, what="turf", area_m2=20)
    assert rows(t)["Rolls"] == "21"
    b = calc(s, what="bricks", area_m2=10)
    assert rows(b)["Bricks"] == "630"


def test_calc_errors(s):
    with pytest.raises(ValueError, match="can't work out"):
        calc(s, what="jam")
    with pytest.raises(ValueError, match="Use metres"):
        calc(s, what="paint", length=1, width=1, height=1, unit="furlong")
    with pytest.raises(ValueError, match="number"):
        calc(s, what="gravel", area_m2="lots")


# ---- rooms ---------------------------------------------------------------------------------------

def test_room_save_details_and_book(s):
    assert room(s, action="save_room", name="Lounge", length=5, width=4) .startswith("Saved Lounge: 5 x 4 m, 2.4 m high")
    room(s, action="save_room", name="Kitchen", length=300, width=250, height=250, unit="cm")
    room(s, action="add_opening", name="lounge", kind="door", wall="south")
    room(s, action="add_opening", name="lounge", kind="window", wall="north", size=1.5, offset=1)
    book = room(s, action="measurements_book")
    assert book.card["kind"] == "table" and len(book.card["rows"]) == 2
    d = room(s, action="room_details", name="Lounge")
    assert d.card["kind"] == "table" and "Floor 20.0 square metres" in d
    out = calc(s, what="paint", room="lounge", coats=2)
    assert rows(out)["Area to paint"] == f"{2 * 9 * 2.4 - 1.6 - 1.2:.1f} m²"


def test_room_update_keeps_openings(s):
    room(s, action="save_room", name="Lounge", length=5, width=4)
    room(s, action="add_opening", name="Lounge", kind="door", wall="east")
    room(s, action="save_room", name="lounge", height=2.6)
    found = diy_room.rooms(s)["Lounge"]
    assert found["height"] == 2.6 and len(found["doors"]) == 1


def test_room_errors(s):
    with pytest.raises(ValueError, match="How long"):
        room(s, action="save_room", name="Hall")
    with pytest.raises(ValueError, match="measurements book"):
        room(s, action="room_details", name="Attic")
    room(s, action="save_room", name="Hall", length=3, width=2)
    with pytest.raises(ValueError, match="door or a window"):
        room(s, action="add_opening", name="Hall", kind="hatch", wall="north")
    with pytest.raises(ValueError, match="Which wall"):
        room(s, action="add_opening", name="Hall", kind="door", wall="up")
    with pytest.raises(ValueError, match="wider"):
        room(s, action="add_opening", name="Hall", kind="window", wall="north", size=5)
    with pytest.raises(ValueError, match="bigger than the room"):
        room(s, action="add_furniture", name="Hall", item="Piano", width=4, depth=1)


def test_empty_book(s):
    assert "empty" in room(s, action="measurements_book")


def test_floor_plan_and_furniture(s):
    room(s, action="save_room", name="Bedroom", length=4, width=3)
    room(s, action="add_opening", name="Bedroom", kind="door", wall="west", offset=0.2)
    out = room(s, action="add_furniture", name="Bedroom", item="Bed", width=1.5, depth=2, position="north east")
    assert out.card["kind"] == "diy-plan"
    bed = out.card["data"]["items"][0]
    assert bed["x"] == 2.5 and bed["y"] == 0
    out = room(s, action="add_furniture", name="Bedroom", item="Wardrobe", width=1, depth=0.6, x=0, y=2.4)
    assert len(out.card["data"]["items"]) == 2 and out.card["data"]["doors"][0]["wall"] == "west"
    # Same name replaces rather than repeats.
    out = room(s, action="add_furniture", name="Bedroom", item="bed", width=1.4, depth=2, position="centre")
    assert len(out.card["data"]["items"]) == 2
    plan = room(s, action="show_plan", name="Bedroom")
    assert plan.card["kind"] == "diy-plan" and plan.card["data"]["length"] == 4
    sketch = room(s, action="show_plan", length=3, width=2.5)
    assert sketch.card["data"]["name"] == "Sketch"
    with pytest.raises(ValueError, match="Which room"):
        room(s, action="show_plan")


def test_room_remove_needs_confirmation(s):
    room(s, action="save_room", name="Bedroom", length=4, width=3)
    room(s, action="add_furniture", name="Bedroom", item="Bed", width=1.5, depth=2)
    assert "confirm" in room(s, action="remove", name="Bedroom", item="bed")
    assert len(diy_room.rooms(s)["Bedroom"]["items"]) == 1
    assert room(s, action="remove", name="Bedroom", item="bed", confirmed=True) == "Removed the Bed from Bedroom."
    with pytest.raises(ValueError, match="no cot"):
        room(s, action="remove", name="Bedroom", item="cot")
    assert "confirm" in room(s, action="remove", name="Bedroom")
    assert room(s, action="remove", name="Bedroom", confirmed=True) == "Removed Bedroom."
    assert diy_room.rooms(s) == {}


# ---- guides --------------------------------------------------------------------------------------

@pytest.mark.parametrize("topic", ["bleed a radiator", "change a fuse", "unblock a sink", "fix a dripping tap",
                                   "hang a picture level", "reset a tripped RCD", "paint a room"])
def test_how_to_guides(s, topic):
    out = guide(s, action="how_to", topic=topic)
    assert out.card["kind"] == "diy-guide"
    d = out.card["data"]
    assert d["steps"] and d["safety"] and d["tools"] and d["pro"]
    assert "Safety first" in out


def test_how_to_partial_and_list(s):
    assert guide(s, action="how_to", topic="radiator").card["data"]["title"] == "Bleed a radiator"
    assert guide(s, action="how_to", topic="dripping tap").card["data"]["title"] == "Fix a dripping tap"
    listing = guide(s, action="how_to")
    assert listing.card["kind"] == "table" and len(listing.card["rows"]) == len(diy_guide.GUIDES)
    with pytest.raises(ValueError, match="haven't got a guide"):
        guide(s, action="how_to", topic="build a rocket")


def test_safety(s):
    out = guide(s, action="safety", topic="before you drill")
    assert out.card["kind"] == "list" and any("detector" in i["label"] for i in out.card["items"])
    assert guide(s, action="safety", topic="gas").card["items"]
    assert "0800 111 999" in guide(s, action="safety", topic="gas").card["items"][1]["label"]
    assert guide(s, action="safety").card["kind"] == "table"
    with pytest.raises(ValueError, match="safety topic"):
        guide(s, action="safety", topic="zzz")


def test_drill_bits_and_screws(s):
    out = guide(s, action="drill_bits", topic="brick")
    assert out.card["kind"] == "table" and "Masonry" in out
    assert len(guide(s, action="drill_bits").card["rows"]) == len(diy_guide.DRILL_BITS)
    with pytest.raises(ValueError, match="drilling advice"):
        guide(s, action="drill_bits", topic="cheese")
    one = guide(s, action="screw_sizes", topic="No. 8")
    assert len(one.card["rows"]) == 1 and "5 mm clearance" in one
    assert len(guide(s, action="screw_sizes", topic="4.8mm").card["rows"]) == 1
    assert len(guide(s, action="screw_sizes").card["rows"]) == 6
    with pytest.raises(ValueError, match="gauge"):
        guide(s, action="screw_sizes", topic="99")


def test_fixings_finishes_stains(s):
    out = guide(s, action="wall_fixings", topic="plasterboard")
    assert out.card["kind"] == "table" and len(out.card["rows"]) == 2
    assert len(guide(s, action="wall_fixings").card["rows"]) == len(diy_guide.FIXINGS)
    fin = guide(s, action="paint_finish", topic="gloss")
    assert fin.card["rows"][0][0] == "Gloss"
    assert guide(s, action="paint_finish").card["kind"] == "table"
    with pytest.raises(ValueError, match="Try matt"):
        guide(s, action="paint_finish", topic="sparkly")
    st = guide(s, action="wood_stain", topic="decking")
    assert st.card["kind"] == "table" and len(st.card["rows"]) == 2
    with pytest.raises(ValueError, match="Try stain"):
        guide(s, action="wood_stain", topic="ketchup")


def test_bad_actions(s):
    for fn in (calc, room, guide, proj):
        with pytest.raises(ValueError):
            fn(s, action="fly", what="fly")


# ---- projects and tools --------------------------------------------------------------------------

def test_project_steps(s):
    out = proj(s, action="project_add", project="Shelves", steps=["Mark the wall", "Drill holes", "Fix brackets", "mark the wall"])
    assert out == "Shelves: added 3 steps, 3 in all."
    assert proj(s, action="project_add", project="shelves", steps=["Paint them"]).endswith("4 in all.")
    shown = proj(s, action="project_show", project="shelves")
    assert shown.card["kind"] == "list" and shown.card["checks"] and len(shown.card["items"]) == 4
    assert shown.card["items"][0]["say"].startswith("Step 1 of the Shelves project")
    assert "Next: Mark the wall" in shown
    assert proj(s, action="step_done", project="Shelves", step="1").startswith("Ticked off step 1, Mark the wall. 1 of 4")
    assert "Ticked off step 2" in proj(s, action="step_done", project="Shelves", step="drill")
    assert proj(s, action="step_done", project="Shelves", step=2, undo=True).startswith("Unticked step 2")
    ls = proj(s, action="project_list")
    assert ls.card["rows"] == [["Shelves", "1 of 4", "Drill holes"]]
    for step in ("2", "3", "4"):
        out = proj(s, action="step_done", project="Shelves", step=step)
    assert "finished" in out
    assert proj(s, action="project_list").card["rows"][0][2] == "Finished"


def test_project_errors_and_remove(s):
    assert "No DIY projects" in proj(s, action="project_list")
    with pytest.raises(ValueError, match="haven't got a project"):
        proj(s, action="project_show", project="Shed")
    proj(s, action="project_add", project="Shed", steps=["Base", "Base walls"])
    with pytest.raises(ValueError, match="more than one"):
        proj(s, action="step_done", project="Shed", step="base")
    with pytest.raises(ValueError, match="Which step"):
        proj(s, action="step_done", project="Shed", step="roof")
    proj(s, action="project_add", project="Empty")
    with pytest.raises(ValueError, match="no steps"):
        proj(s, action="project_show", project="Empty")
    assert "confirm" in proj(s, action="project_remove", project="Shed")
    assert proj(s, action="project_remove", project="Shed", confirmed=True) == "Removed the Shed project."


def test_tool_inventory(s):
    assert "No tools" in proj(s, action="tool_list")
    proj(s, action="tool_add", tool="Cordless drill", where="garage")
    proj(s, action="tool_add", tool="Spirit level")
    assert proj(s, action="tool_lend", tool="drill", to="Sam") == "Noted that Sam has borrowed the Cordless drill."
    with pytest.raises(ValueError, match="already out with Sam"):
        proj(s, action="tool_lend", tool="drill", to="Jo")
    out = proj(s, action="tool_list")
    assert out.card["kind"] == "table" and "2 tools listed, 1 lent out" in out
    assert ["Cordless drill", "garage", "Sam", "0 days"] in out.card["rows"]
    out = proj(s, action="tool_list", only_out=True)
    assert len(out.card["rows"]) == 1 and "Cordless drill with Sam" in out
    assert proj(s, action="tool_return", tool="drill") == "The Cordless drill is back from Sam."
    assert "wasn't lent out" in proj(s, action="tool_return", tool="drill")
    assert proj(s, action="tool_list", only_out=True) == "Nothing is lent out."
    assert "Noted that Jo has borrowed the Hammer" in proj(s, action="tool_lend", tool="Hammer", to="Jo")
    assert "confirm" in proj(s, action="tool_remove", tool="hammer")
    assert proj(s, action="tool_remove", tool="hammer", confirmed=True) == "Removed the Hammer from your tools."
    with pytest.raises(ValueError, match="haven't got a tool"):
        proj(s, action="tool_return", tool="saw")
