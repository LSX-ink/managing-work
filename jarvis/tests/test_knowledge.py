import asyncio
import json
import os
import time
from datetime import date

import pytest

import knowledge
import knowledge_explore
import knowledge_mindmap
import screen
import tools
from config import Settings

TODAY = date(2026, 9, 28)


@pytest.fixture
def s(tmp_path):
    return Settings(memory_dir=str(tmp_path))


def note(s, **args):
    return knowledge.run_tool("knowledge_note", args, s, today=TODAY)


def explore(s, **args):
    return knowledge_explore.run_tool("knowledge_explore", args, s, today=TODAY)


def mind(s, **args):
    return knowledge_mindmap.run_tool("knowledge_mindmap", args, s, today=TODAY)


def text_of(s, title):
    return knowledge.index(s)[title.lower()]["text"]


def seed(s):
    note(s, action="new", title="Gardening", text="Grow [[Tomatoes]] and [[Basil|herbs]]. #garden #outdoors")
    note(s, action="new", title="Tomatoes", text="Water daily. See [[Gardening#Plan]]. #garden")
    note(s, action="new", title="Lonely", text="Nobody links here.")


def test_new_note_pops_up_with_links_and_backlinks(s):
    seed(s)
    out = note(s, action="open", title="tomatoes")
    assert isinstance(out, screen.Shown) and out.startswith("Showing your note Tomatoes. It says:\nWater daily.")
    card = out.card
    assert card["kind"] == "knowledge-note" and card["data"]["backlinks"] == ["Gardening"]
    assert card["data"]["tags"] == ["garden"]
    path = knowledge.home(s) / "Gardening.md"
    assert path.read_text(encoding="utf-8").startswith("# Gardening\n\nGrow [[Tomatoes]]")
    assert note(s, action="open", title="Gardening").card["data"]["missing"] == ["Basil"]
    with pytest.raises(ValueError):
        note(s, action="new", title="gardening")
    with pytest.raises(ValueError, match="no note called"):
        note(s, action="open", title="Nope")


def test_add_to_a_section_and_new_from_template(s):
    out = note(s, action="new", title="Kitchen refit", template="project", text="Budget 5k")
    assert out.card["data"]["tags"] == ["project"]
    note(s, action="add", title="kitchen refit", section="Next steps", text="- [ ] Get quotes")
    text = text_of(s, "Kitchen refit")
    assert "## Next steps\n\n- [ ] Get quotes\n\n## Notes" in text and "Started: 2026-09-28" in text
    note(s, action="add", title="Brand new", text="Made by adding")
    assert "Made by adding" in text_of(s, "Brand new")
    templates = note(s, action="templates")
    assert [i["label"] for i in templates.card["items"]] == ["Book", "Meeting", "Person", "Project", "Recipe"]
    assert (knowledge.home(s) / "Templates" / "meeting.md").exists()
    assert "Templates" not in {n["path"].parent.name for n in knowledge.index(s).values()}


def test_daily_note_from_template(s):
    note(s, action="daily", text="").card  # noqa: B018
    path = knowledge.home(s) / "Daily" / "2026-09-28.md"
    assert path.read_text(encoding="utf-8").startswith("# Monday 28 September 2026\n\n## Plan")
    out = note(s, action="daily", text="Fixed the fence")
    assert out.card["title"] == "2026-09-28" and "## Notes\n\nFixed the fence\n\n## Grateful for" in path.read_text()
    tomorrow = knowledge.run_tool("knowledge_note", {"action": "daily"}, s, today=date(2026, 9, 29))
    assert "Previous: [[2026-09-28]]" in tomorrow.card["data"]["text"]


def test_highlight_goes_into_book_notes(s):
    out = note(s, action="highlight", text='"You do not rise to the level of your goals."', source="Atomic Habits",
               author="James Clear", page="27")
    text = text_of(s, "Atomic Habits")
    assert "Author: James Clear" in text and "#book" in text
    assert "## Highlights\n\n> You do not rise to the level of your goals.\n> — James Clear, p. 27, 2026-09-28" in text
    note(s, action="highlight", text="Second one", source="atomic habits")
    assert text_of(s, "Atomic Habits").count("> ") == 4 and out.card["kind"] == "knowledge-note"


def test_rename_updates_links_and_asks_when_many(s):
    seed(s)
    out = note(s, action="rename", title="Tomatoes", new_title="Cherry tomatoes")
    assert out.startswith("Renamed Tomatoes to Cherry tomatoes and updated links in 1 notes.")
    assert "[[Cherry tomatoes]]" in text_of(s, "Gardening")
    assert text_of(s, "Cherry tomatoes").startswith("# Cherry tomatoes")
    for i in range(11):
        note(s, action="new", title=f"Link {i}", text="[[Lonely]]")
    ask = note(s, action="rename", title="Lonely", new_title="Solo")
    assert "11 notes" in ask and "confirmed" in ask and "lonely" in knowledge.index(s)
    note(s, action="rename", title="Lonely", new_title="Solo", confirmed=True)
    assert "[[Solo]]" in text_of(s, "Link 3")


def test_merge_needs_confirmation(s):
    seed(s)
    ask = note(s, action="merge", title="Tomatoes", into="Gardening")
    assert "confirmed" in ask and "tomatoes" in knowledge.index(s)
    out = note(s, action="merge", title="Tomatoes", into="Gardening", confirmed=True)
    text = text_of(s, "Gardening")
    assert "## From Tomatoes\n\nWater daily." in text and "[[Gardening]] and" in text
    assert "tomatoes" not in knowledge.index(s) and (knowledge.home(s) / ".merged" / "Tomatoes.md").exists()
    assert out.card["title"] == "Gardening"


def test_backlinks_tags_and_tagged(s):
    seed(s)
    out = explore(s, action="backlinks", title="Gardening")
    assert out == "1 notes link to Gardening: Tomatoes." and out.card["items"][0]["say"] == "Open my note Tomatoes"
    tags = explore(s, action="tags")
    assert tags.card["items"][0] == {"label": "#garden (2)", "done": False, "say": "Show my notes tagged #garden"}
    assert explore(s, action="tagged", tag="#Garden").startswith("2 notes tagged #garden: Gardening, Tomatoes")


def test_graph_orphans_and_broken_links(s):
    seed(s)
    g = explore(s, action="graph")
    assert g.card["kind"] == "knowledge-graph"
    titles = [n["title"] for n in g.card["data"]["nodes"]]
    assert set(titles) == {"Gardening", "Tomatoes", "Lonely"} and len(g.card["data"]["edges"]) == 2
    near = explore(s, action="graph", title="Tomatoes")
    assert {n["title"] for n in near.card["data"]["nodes"]} == {"Gardening", "Tomatoes"}
    assert near.card["data"]["nodes"][near.card["data"]["focus"]]["title"] == "Tomatoes"
    assert explore(s, action="orphans").startswith("1 notes have no links in or out: Lonely")
    b = explore(s, action="broken_links")
    assert b.card["items"][0]["say"] == "Create a note called Basil" and "Gardening" in b.card["items"][0]["label"]


def test_graph_caps_nodes(s):
    folder = knowledge.home(s)
    for i in range(160):
        (folder / f"N{i}.md").write_text(f"[[N{(i + 1) % 160}]]", encoding="utf-8")
    out = explore(s, action="graph")
    assert len(out.card["data"]["nodes"]) == 150 and "150 most linked" in out


def test_table_of_all_notes(s):
    seed(s)
    out = explore(s, action="all_notes")
    assert out.card["kind"] == "table" and out.card["columns"][2:4] == ["Links", "Linked from"]
    assert out.card["rows"][0][:4] == ["Gardening", "#garden #outdoors", "2", "1"]


def test_resurface_oldest_note_not_seen_for_30_days(s):
    seed(s)
    old = time.mktime(date(2026, 6, 1).timetuple())
    for title in ("Gardening", "Lonely"):
        os.utime(knowledge.home(s) / f"{title}.md", (old, old))
    (knowledge.home(s).parent / ".knowledge-views.json").unlink()
    knowledge.mark_viewed(s, "Gardening", date(2026, 7, 1))
    out = explore(s, action="resurface")
    assert out.startswith("Here's an old note, Lonely, last seen 01 June 2026.")
    assert json.loads((knowledge.home(s).parent / ".knowledge-views.json").read_text())["lonely"] == "2026-09-28"
    assert explore(s, action="resurface").card["title"] == "Gardening"
    assert explore(s, action="resurface").startswith("Every note")


def test_what_do_i_know(s):
    seed(s)
    out = explore(s, action="know", query="What do I know about tomatoes?")
    assert out.splitlines()[1] == "- Tomatoes: Water daily. See [[Gardening#Plan]]. #garden"
    assert out.splitlines()[2].startswith("- Gardening") and out.card["items"][0]["say"] == "Open my note Tomatoes"
    assert explore(s, action="know", query="submarines") == "None of your notes mention submarines."


def test_mindmap_by_voice(s):
    out = mind(s, action="new", topic="Holiday", outline="- Places\n  - Rome\n  - Oslo\n- Budget")
    assert out.card["kind"] == "knowledge-mindmap" and "Branches: Places, Budget." in out
    root = out.card["data"]["root"]
    assert [c["text"] for c in root["children"][0]["children"]] == ["Rome", "Oslo"]
    mind(s, action="add", node="Paris", parent="places")
    ask = mind(s, action="remove", node="Places")
    assert "3 branches" in ask and "confirmed" in ask
    mind(s, action="remove", topic="holiday", node="Oslo")
    renamed = mind(s, action="rename", node="Budget", new_name="Money")
    assert [c["text"] for c in renamed.card["data"]["root"]["children"]] == ["Places", "Money"]
    assert [c["text"] for c in renamed.card["data"]["root"]["children"][0]["children"]] == ["Rome", "Paris"]
    with pytest.raises(ValueError):
        mind(s, action="remove", node="Holiday")
    mind(s, action="remove", node="Places", confirmed=True)
    assert mind(s, action="show").card["data"]["root"]["children"] == [{"text": "Money", "children": []}]
    assert "confirmed" in mind(s, action="new", topic="holiday")
    assert mind(s, action="list").card["items"][0]["say"] == "Show my mind map Holiday."


def test_mindmap_to_outline_and_back(s):
    mind(s, action="new", topic="Garden", outline="- Veg\n  - Peas\n- Flowers")
    out = mind(s, action="to_outline")
    assert out.card["kind"] == "knowledge-note" and out.card["title"] == "Garden mind map"
    assert text_of(s, "Garden mind map") == "# Garden mind map\n\n- Veg\n  - Peas\n- Flowers\n"
    assert "confirmed" in mind(s, action="to_outline")
    note(s, action="new", title="Party", text="## Food\n\n- Cake\n  - Candles\n\n## Music\n- Playlist")
    back = mind(s, action="from_outline", title="party")
    tree = back.card["data"]["root"]
    assert tree["text"] == "Party" and [c["text"] for c in tree["children"]] == ["Food", "Music"]
    assert tree["children"][0]["children"][0]["children"][0]["text"] == "Candles"
    again = mind(s, action="from_outline", title="Garden mind map", confirmed=True)
    assert again.card["data"]["topic"] == "Garden"


def test_registered_and_schemas_strict():
    names = {t["name"] for t in tools.tool_definitions(Settings())} if hasattr(tools, "tool_definitions") else set()
    for module in (knowledge, knowledge_explore, knowledge_mindmap):
        assert module in tools.ABILITIES
        for t in module.tool_definitions():
            assert t["input_schema"]["additionalProperties"] is False
            assert not names or t["name"] in names
    assert {"knowledge-note", "knowledge-graph", "knowledge-mindmap"} <= screen.EXTRA_KINDS


def test_runs_through_tools(s):
    async def go():
        return await tools.run_tool("knowledge_note", {"action": "new", "title": "Via tools", "text": "hi"}, s, None)

    out = asyncio.run(go())
    assert out.startswith("Made the note Via tools.")
