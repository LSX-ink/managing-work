import random
from datetime import datetime, timedelta

import pytest

import homestore
import screen
import tools
import writing_bible
import writing_data
import writing_goals
import writing_helpers
import writing_projects
import writing_store as ws
from config import Settings

NOW = datetime(2026, 9, 28, 10, 0)


@pytest.fixture
def s(tmp_path, monkeypatch):
    monkeypatch.setattr(homestore, "now", lambda: NOW)
    monkeypatch.setattr(writing_helpers, "rng", random.Random(7))
    return Settings(memory_dir=str(tmp_path))


def proj(s, **args):
    return writing_projects.run_tool("writing_project", args, s)


def goal(s, **args):
    return writing_goals.run_tool("writing_goal", args, s)


def bible(s, **args):
    return writing_bible.run_tool("writing_story_bible", args, s)


def helper(s, **args):
    return writing_helpers.run_tool("writing_helper", args, s)


def sections(shown, kind=None):
    assert isinstance(shown, screen.Shown) and shown.card["kind"] == ws.KIND
    return [x for x in shown.card["data"]["sections"] if kind is None or x["type"] == kind]


def novel(s):
    proj(s, action="create", project="Ashes", kind="novel", word_goal=1000, deadline="2026-10-08")
    proj(s, action="add_piece", title="The Fire", text="It was a cold night. The fire burned slowly.")
    proj(s, action="add_piece", title="The Road", text="They walked for days and days.")


def test_registered_and_small():
    names = {t["name"] for t in tools.client_tool_definitions(Settings())}
    mods = (writing_projects, writing_goals, writing_bible, writing_helpers)
    assert {"writing_project", "writing_goal", "writing_story_bible", "writing_helper"} <= names
    for module in mods:
        for tool in module.tool_definitions():
            assert tool["input_schema"]["additionalProperties"] is False
    assert sum(len(m.tool_definitions()) for m in mods) == 4
    assert ws.KIND in screen.EXTRA_KINDS
    assert sum(len(v) for v in writing_data.PROMPTS.values()) == 100


def test_create_list_update_and_dashboard(s, tmp_path):
    out = proj(s, action="create", project="Ashes", kind="novel", word_goal=1000, deadline="2026-10-08")
    assert "Started the novel Ashes" in out and (tmp_path / "Writing" / "Ashes").is_dir()
    assert sections(out, "stats")[0]["items"][3]["value"] == "10 days to go"
    with pytest.raises(ValueError):
        proj(s, action="create", project="ashes")
    shown = proj(s, action="list")
    assert "1 writing project" in shown and sections(shown, "list")[0]["items"][0]["say"].endswith("Ashes.")
    out = proj(s, action="update", word_goal=2000)
    assert sections(out, "meters")[0]["rows"][0]["max"] == 2000
    out = proj(s, action="dashboard")
    assert "0 words of 2,000" in out and "200 words a day" in out


def test_pieces_add_write_rename_move_delete(s, tmp_path):
    novel(s)
    folder = tmp_path / "Writing" / "Ashes"
    assert (folder / "The Fire.md").read_text().startswith("# The Fire\n\nIt was a cold night.")
    out = proj(s, action="outline")
    rows = sections(out, "table")[0]["rows"]
    assert rows[0] == ["1", "The Fire", "9"] and rows[-1] == ["", "Total", "15"]
    out = proj(s, action="write_piece", piece="road", text="Then it rained.")
    assert "9 words" in out and out.card["kind"] == "file"
    out = proj(s, action="write_piece", piece="2", text="Only this.", mode="replace")
    assert (folder / "The Road.md").read_text() == "# The Road\n\nOnly this.\n"
    assert "It says:\nOnly this." in proj(s, action="show_piece", piece="The Road")
    proj(s, action="rename_piece", piece="road", new_title="The Long Road")
    assert (folder / "The Long Road.md").read_text().startswith("# The Long Road") and not (folder / "The Road.md").exists()
    out = proj(s, action="move_piece", piece="long road", position=1)
    assert sections(out, "table")[0]["rows"][0][1] == "The Long Road"
    assert "confirm" in proj(s, action="delete_piece", piece="fire")
    out = proj(s, action="delete_piece", piece="fire", confirmed=True)
    assert not (folder / "The Fire.md").exists() and len(sections(out, "table")[0]["rows"]) == 2
    with pytest.raises(ValueError):
        proj(s, action="add_piece", title="the long road")


def test_compile_manuscript(s, tmp_path):
    novel(s)
    out = proj(s, action="compile")
    md = (tmp_path / "Writing" / "Ashes" / "Manuscript" / "Ashes.md").read_text()
    assert md.startswith("# Ashes\n\n## The Fire\n\nIt was") and md.index("The Fire") < md.index("The Road")
    assert out.card["kind"] == "file" and out.card["name"] == "Ashes.pdf"
    assert (tmp_path / "Writing" / "Ashes" / "Manuscript" / "Ashes.pdf").read_bytes().startswith(b"%PDF")


def test_daily_goal_log_and_streak(s):
    novel(s)
    out = goal(s, action="set_daily_goal", words=10)
    assert "10 words" in out and sections(out, "meters")
    out = goal(s, action="log_words")
    assert "noted" in out  # first count only sets the baseline
    proj(s, action="write_piece", piece="road", text="one two three four five six seven eight nine ten eleven")
    out = goal(s, action="log_words")
    assert "Logged 11 words; 11 today." in out
    assert goal(s, action="log_words") == "No new words in your projects since the last count."
    log = ws.load_log(s)
    log["days"][(NOW.date() - timedelta(days=1)).isoformat()] = 50
    log["days"][(NOW.date() - timedelta(days=2)).isoformat()] = 5  # under the goal: breaks the streak
    ws.save_log(s, log)
    out = goal(s, action="progress")
    assert "Streak: 2 days" in out and sections(out, "chart")[0]["chart"]["values"][-1] == 11
    out = goal(s, action="log_words", words=4)
    assert "15 today" in out
    dash = proj(s, action="dashboard")
    assert sections(dash, "stats")[0]["items"][2]["value"] == "2 days"
    assert any(x["title"] == "Words written, last 14 days" for x in sections(dash, "chart"))


def test_sprint(s, monkeypatch):
    novel(s)
    out = goal(s, action="sprint_start", minutes=15)
    assert out.card["kind"] == "timer" and out.card["ends_at"] == int((NOW + timedelta(minutes=15)).timestamp() * 1000)
    proj(s, action="write_piece", piece="fire", text="five more words right here")
    monkeypatch.setattr(homestore, "now", lambda: NOW + timedelta(minutes=15))
    out = goal(s, action="sprint_finish")
    assert "5 words in 15 minutes" in out and sections(out, "stats")[0]["items"][2]["value"] == "20"
    with pytest.raises(ValueError):
        goal(s, action="sprint_finish")
    goal(s, action="sprint_start", minutes=10, words=100)
    assert "20 words in" in goal(s, action="sprint_finish", words_after=120)


def test_blog_planner(s):
    out = goal(s, action="blog_add", title="Five cheap days out", publish_date="2026-10-05")
    assert "as idea" in out and sections(out, "list")[0]["title"] == "Idea (1)"
    goal(s, action="blog_add", title="My kit", status="drafting")
    out = goal(s, action="blog_update", title="cheap days", status="drafting", publish_date="2026-10-02")
    assert "now drafting, 2026-10-02" in out
    out = goal(s, action="blog_list")
    assert "2 drafting" in out and "Next up: Five cheap days out" in out
    assert "confirm" in goal(s, action="blog_delete", title="my kit")
    out = goal(s, action="blog_delete", title="my kit", confirmed=True)
    assert "Removed My kit" in out


def test_characters(s):
    novel(s)
    out = bible(s, action="character_add", name="Mara", role="hero", traits="stubborn, kind", appearance="red coat")
    assert "Added Mara" in out and sections(out, "fields")[0]["items"][0] == {"label": "Role", "value": "hero"}
    out = bible(s, action="character_add", name="mara", notes="Afraid of water.")
    assert "Updated Mara" in out and sections(out, "text")[0]["text"] == "Afraid of water."
    bible(s, action="character_add", name="Tom", role="brother")
    out = bible(s, action="character_list")
    assert "2 characters" in out and sections(out, "table")[0]["rows"][0][:2] == ["Mara", "hero"]
    assert "role: hero" in bible(s, action="character_card", name="mara")
    assert "confirm" in bible(s, action="character_delete", name="tom")
    out = bible(s, action="character_delete", name="tom", confirmed=True)
    assert "1 character" in out


def test_world_notes(s):
    novel(s)
    bible(s, action="world_add", name="Greyhaven", type="place", notes="A port town in fog.")
    out = bible(s, action="world_add", name="The Burning", type="lore", notes="The fire of 1802.")
    titles = [x["title"] for x in sections(out, "list")]
    assert titles == ["Places (1)", "Lore (1)"]
    assert "Greyhaven: A port town" in bible(s, action="world_list")
    assert "confirm" in bible(s, action="world_delete", name="greyhaven")
    assert "Deleted Greyhaven" in bible(s, action="world_delete", name="greyhaven", confirmed=True)


def test_plot_planner(s):
    novel(s)
    bible(s, action="scene_add", name="The fire starts", act=1)
    bible(s, action="scene_add", name="On the road", act=2)
    bible(s, action="scene_add", name="Meeting Tom", act=1, notes="At the inn.")
    out = bible(s, action="scene_add", name="Prologue", act=1, position=1)
    acts = sections(out, "table")
    assert [r[1] for r in acts[0]["rows"]] == ["Prologue", "The fire starts", "Meeting Tom"]
    assert acts[0]["title"] == "Act 1" and acts[1]["title"] == "Act 2"
    out = bible(s, action="scene_move", name="meeting", act=2, position=1)
    assert "act 2, scene 1" in out
    assert [r[1] for r in sections(out, "table")[1]["rows"]] == ["Meeting Tom", "On the road"]
    assert "act 1: 2, act 2: 2, act 3: 0" in bible(s, action="scene_list")
    assert "confirm" in bible(s, action="scene_delete", name="prologue")
    assert "Deleted the scene Prologue" in bible(s, action="scene_delete", name="prologue", confirmed=True)


def test_prompt_and_names(s):
    out = helper(s, action="prompt", genre="horror")
    assert out.card["kind"] == "text" and out.card["text"] in writing_data.PROMPTS["horror"]
    assert out.card["buttons"][0]["label"] == "Start a piece from this" and out.card["text"] in out.card["buttons"][0]["say"]
    with pytest.raises(ValueError):
        helper(s, action="prompt", genre="westerns")
    for style in ("fantasy", "sci-fi", "english", "places"):
        out = helper(s, action="names", style=style, count=8)
        labels = [i["label"] for i in out.card["items"]]
        assert len(labels) == len(set(labels)) == 8 and all(x[0].isupper() for x in labels)
    assert "world notes" in out.card["items"][0]["say"]


def test_poem_forms_and_syllables(s):
    out = helper(s, action="poem_form")
    assert out.card["kind"] == "list" and len(out.card["items"]) == len(writing_data.POEM_FORMS)
    out = helper(s, action="poem_form", form="Villanelle")
    assert "Nineteen lines" in out and out.card["kind"] == "text"
    assert "5-7-5" in helper(s, action="poem_form", form="haiku").card["text"]
    out = helper(s, action="syllables", text="An old silent pond / A frog jumps into the pond / Splash! Silence again.",
                 form="haiku")
    assert out.startswith("Syllables: 5, 7, 5. That fits a haiku.") and out.card["kind"] == "table"
    assert out.card["rows"][1][1:] == ["7", "7", "yes"]
    out = helper(s, action="syllables", text="The cat sat\non the mat", form="haiku")
    assert "A haiku wants 5-7-5" in out
    assert helper(s, action="syllables", text="beautiful").startswith("Syllables: 3.")
    assert [writing_helpers.syllables_in(w) for w in ("the", "table", "moonlight", "autumn", "every")] == [1, 2, 2, 2, 3]


def test_readability(s):
    text = ("The dog ran quickly. The dog barked loudly at the cat! Then the dog slept happily in the warm sun, "
            "and the family was happy.")
    out = helper(s, action="readability", text=text)
    items = {x["label"]: x["value"] for x in sections(out, "stats")[0]["items"]}
    assert items["Sentences"] == "3" and items["Words"] == "25" and items["-ly adverbs"] == "3"
    assert sections(out, "table")[0]["rows"][0] == ["dog", "3"]
    assert "family" not in sections(out, "text")[0]["text"]
    novel(s)
    out = helper(s, action="readability", piece="fire")
    assert out.startswith("The Fire: reading ease")
    assert helper(s, action="readability").startswith("Ashes:")


def test_songs(s, tmp_path):
    out = helper(s, action="song_new", title="Night Drive", shape="verse-chorus")
    assert "in Songs" in out and [x["title"] for x in sections(out)] == \
        ["Verse 1", "Chorus", "Verse 2", "Chorus", "Bridge", "Chorus"]
    out = helper(s, action="song_section", piece="night drive", section="chorus", text="Windows down\nNo one around")
    chorus = [x for x in sections(out) if x["title"] == "Chorus"]
    assert len(chorus) == 3 and all(x["text"] == "Windows down\nNo one around" for x in chorus)
    out = helper(s, action="song_section", piece="night drive", section="Coda", text="Home at last")
    assert sections(out)[-1] == {"type": "text", "title": "Coda", "text": "Home at last"}
    out = helper(s, action="song_show", piece="night drive")
    assert out.startswith("Night Drive:\nChorus:\nWindows down")
    text = (tmp_path / "Writing" / "Songs" / "Night Drive.md").read_text()
    assert "Structure: Verse 1 → Chorus → Verse 2 → Chorus → Bridge → Chorus → Coda" in text
    assert "8 words" in proj(s, action="outline", project="songs")
