import asyncio
from datetime import date

import pytest

import repurpose_formats as rf
import repurpose_plan as rp
import repurpose_subs as rs
import repurpose_tracker as rt
import screen
import tools
from config import Settings

TODAY = date(2026, 9, 29)
SCRIPT = ("Nobody tells you this about sleep. Most people stop caffeine too late, and that ruins the night. "
          "Try a cut-off at 2pm for one week. You will notice deeper sleep by day 3! "
          "Then move your bedtime by 15 minutes. Small steps beat big resolutions, because they stick.")


@pytest.fixture
def s(tmp_path):
    return Settings(memory_dir=str(tmp_path))


def sub(s, **a):
    return rs.run_tool("repurpose_subtitles", a, s, None)


def fmt(s, **a):
    return rf.run_tool("repurpose_formats", a, s, None)


def plan(s, **a):
    return rp.run_tool("repurpose_plan", a, s, None)


def trk(s, **a):
    return rt.run_tool("repurpose_tracker", a, s, None, TODAY)


def card(x):
    assert isinstance(x, screen.Shown) and x.card
    return x.card


# ---- Subtitles ----

def test_srt_and_vtt_made_and_saved(s, tmp_path):
    out = sub(s, action="srt_make", name="sleep", text=SCRIPT, wpm=150)
    assert card(out)["kind"] == "file"
    srt = (tmp_path / "repurpose" / "subtitles" / "sleep.srt").read_text()
    assert srt.startswith("1\n00:00:00,000 --> ") and "\n2\n" in srt
    sub(s, action="vtt_make", name="sleep", text=SCRIPT, words_per_cue=3)
    vtt = (tmp_path / "repurpose" / "subtitles" / "sleep.vtt").read_text()
    assert vtt.startswith("WEBVTT") and "00:00:00.000 -->" in vtt
    assert len(rs.parse(vtt)) > len(rs.parse(srt))
    with pytest.raises(ValueError):
        sub(s, action="srt_make", name="x")


def test_subtitle_list_show_shift_check_text(s):
    assert "haven't made" in sub(s, action="subtitle_list")
    sub(s, action="srt_make", name="sleep", text=SCRIPT)
    assert card(sub(s, action="subtitle_list"))["kind"] == "list"
    shown = card(sub(s, action="subtitle_show", name="sleep"))
    assert shown["kind"] == "repurpose-timeline" and shown["data"]["cues"]
    first = rs.parse((rs._subs(s) / "sleep.srt").read_text())[0][0]
    assert "+2" in sub(s, action="subtitle_shift", name="sleep", seconds=2)
    assert rs.parse((rs._subs(s) / "sleep.srt").read_text())[0][0] == first + 2000
    assert card(sub(s, action="subtitle_check", name="sleep"))["kind"] in ("text", "table")
    assert "Nobody tells you" in card(sub(s, action="subtitle_to_text", name="sleep"))["text"]
    with pytest.raises(ValueError):
        sub(s, action="subtitle_show", name="missing")


def test_subtitle_check_flags_problems(s):
    bad = "1\n00:00:00,000 --> 00:00:00,500\nThis is a very fast subtitle indeed\n\n2\n00:00:00,400 --> 00:00:09,000\nHi\n"
    out = sub(s, action="subtitle_check", text=bad)
    text = " ".join(" ".join(r) for r in card(out)["rows"])
    assert "too fast" in text and "overlaps" in text and "over 7 seconds" in text


def test_onscreen_lines(s):
    out = sub(s, action="onscreen_lines", text=SCRIPT)
    c = card(out)
    assert c["kind"] == "repurpose-timeline" and len(c["data"]["cues"]) == 6
    assert c["data"]["cues"][0]["text"].isupper()


def test_chapters(s):
    ok = sub(s, action="chapters_make", chapters=["0:00 Intro", "0:45 Caffeine", "2:10 Bedtime"])
    assert "valid" in ok and card(ok)["text"].startswith("0:00 Intro")
    bad = sub(s, action="chapters_make", chapters=["0:05 Intro", "0:10 Two"])
    assert "problem" in bad and "0:00" in card(bad)["text"]
    guess = sub(s, action="chapters_from_script", text=SCRIPT, count=3)
    assert card(guess)["text"].startswith("0:00")


def test_description_build(s, tmp_path):
    out = sub(s, action="description_build", title="Sleep better", summary="Three tips.", chapters=["0:00 Intro"],
              links=["https://example.com"], hashtags=["#sleep", "health", "tips", "extra"])
    assert card(out)["kind"] == "file"
    body = (tmp_path / "repurpose" / "descriptions" / "Sleep better.txt").read_text()
    assert "Chapters:\n0:00 Intro" in body and "#sleep #health #tips" in body and "#extra" not in body


# ---- Formats ----

def test_series_split_and_show(s):
    out = fmt(s, action="series_split", text=SCRIPT, parts=3, name="Sleep")
    c = card(out)
    assert c["kind"] == "table" and len(c["rows"]) == 3 and "Part 2 next" in c["rows"][0][3]
    assert "end" in c["rows"][2][3]
    assert card(fmt(s, action="series_show", name="sleep"))["kind"] == "list"
    part = card(fmt(s, action="series_show", name="sleep", part=2))
    assert part["text"].startswith("Last time:")
    with pytest.raises(ValueError):
        fmt(s, action="series_split", text="One. Two.", parts=5)
    with pytest.raises(ValueError):
        fmt(s, action="series_show", name="nope")


@pytest.mark.parametrize("action", ["shorts_version", "reels_version", "pin_version", "blog_version",
                                    "newsletter_version", "podcast_points"])
def test_version_briefs(s, action):
    out = fmt(s, action=action, text=SCRIPT, angle="beginners")
    assert "Script:" in out and "no claims about earnings" in out and "beginners" in out


def test_thread_version(s):
    long = " ".join(f"Sentence number {i} says something useful about sleep." for i in range(20))
    c = card(fmt(s, action="thread_version", text=long))
    posts = [p.split("\n")[0] for p in c["text"].split("\n\n")]
    assert c["kind"] == "text" and len(posts) > 2 and all(len(p) <= 280 for p in posts) and posts[0].endswith(f"(1/{len(posts)})")


def test_titles_and_thumbnails(s):
    assert len(card(fmt(s, action="titles", topic="sleep"))["rows"]) == 8
    check = card(fmt(s, action="title_check", title="5 sleep mistakes to stop", platform="YouTube"))
    assert check["kind"] == "table" and any("mistakes" in r[1] for r in check["rows"])
    thumbs = card(fmt(s, action="thumbnail_text", topic="Why nobody sleeps properly anymore"))
    assert thumbs["rows"] and all(int(r[1]) <= 4 for r in thumbs["rows"])
    assert "long" in fmt(s, action="thumb_check", text="this is a far too long piece of cover text")
    assert card(fmt(s, action="thumb_check", text="STOP SNOOZING", title="Stop snoozing now"))["rows"][-1][1] == "yes"


def test_quote_cards_and_limits(s):
    q = card(fmt(s, action="quote_cards", text=SCRIPT, count=2))
    assert q["kind"] == "list" and len(q["items"]) == 2
    assert card(fmt(s, action="char_limits"))["kind"] == "table"
    assert "too many" in fmt(s, action="limits_check", text="x" * 300, platform="X")
    assert "fits" in fmt(s, action="limits_check", text="short", platform="Instagram")
    with pytest.raises(ValueError):
        fmt(s, action="limits_check", text="x", platform="Myspace")


def test_cta_and_guide(s):
    assert len(card(fmt(s, action="cta_swap"))["rows"]) == 8
    assert len(card(fmt(s, action="cta_swap", platform="pinterest"))["rows"]) == 1
    with pytest.raises(ValueError):
        fmt(s, action="cta_swap", platform="Bebo")
    assert card(fmt(s, action="format_guide"))["kind"] == "table"


# ---- Plans ----

def test_atoms(s):
    out = plan(s, action="atomise", idea="sleep", count=10)
    assert len(card(out)["items"]) == 10
    assert card(plan(s, action="atoms_show"))["kind"] == "list"
    done = plan(s, action="atom_done", idea="sleep", number=2)
    assert card(done)["items"][1]["done"] and "1 of 10" in card(done)["title"]
    assert "confirm" in plan(s, action="atoms_remove", idea="sleep")
    assert "Removed" in plan(s, action="atoms_remove", idea="sleep", confirmed=True)
    assert plan(s, action="atoms_show") == "You haven't atomised an idea yet."


def test_checklists(s):
    c = card(plan(s, action="checklist_make", video="Sleep video"))
    assert len(c["items"]) == 12 and c["items"][0]["say"]
    assert card(plan(s, action="checklist_tick", video="sleep", step="2"))["items"][1]["done"]
    assert card(plan(s, action="checklist_tick", video="sleep", step="subtitles", done=False))["items"][1]["done"] is False
    assert card(plan(s, action="checklist_show"))["kind"] == "list"
    assert card(plan(s, action="checklist_show", video="sleep"))["title"].startswith("Repurposing")
    with pytest.raises(ValueError):
        plan(s, action="checklist_tick", video="sleep", step="nonsense")
    assert "confirm" in plan(s, action="checklist_remove", video="sleep")
    assert "Removed" in plan(s, action="checklist_remove", video="sleep", confirmed=True)


def test_template(s):
    assert len(card(plan(s, action="template_show"))["items"]) == 12
    assert len(card(plan(s, action="template_set", steps=["Cut it", "Post it"]))["items"]) == 2
    assert len(card(plan(s, action="checklist_make", video="Two step"))["items"]) == 2
    assert len(card(plan(s, action="template_set", steps=[]))["items"]) == 12


def test_formats_map_and_spread(s):
    assert all(r[0] == "Podcast" for r in card(plan(s, action="formats_map", source="podcast"))["rows"])
    with pytest.raises(ValueError):
        plan(s, action="formats_map", source="hologram")
    out = rp.spread_plan(s, {"video": "Sleep", "date": "2026-10-01", "save": True}, TODAY)
    assert card(out)["rows"][1][:2] == ["YouTube Shorts", "2026-10-02"]
    assert len(card(trk(s, action="video_versions", video="Sleep"))["rows"]) == 7


# ---- Tracker ----

def test_versions_and_matrix(s):
    assert "Nothing is tracked" in trk(s, action="tracker_show")
    assert "TikTok is posted" in trk(s, action="version_log", video="Sleep", platform="tiktok", date="2026-09-20", url="typed-link")
    trk(s, action="version_log", video="Sleep", platform="Blog", status="planned", date="2026-10-05")
    trk(s, action="version_log", video="Sleep", platform="Blog", status="posted", date="2026-10-06")
    c = card(trk(s, action="tracker_show"))
    assert c["kind"] == "repurpose-matrix" and c["data"]["rows"][0]["cells"][0]["status"] == "posted"
    assert len(card(trk(s, action="video_versions", video="sleep"))["rows"]) == 2
    with pytest.raises(ValueError):
        trk(s, action="version_log", video="Sleep", platform="X", status="sent")


def test_edit_remove_gaps_stats_export(s, tmp_path):
    trk(s, action="version_log", video="Sleep", platform="TikTok")
    trk(s, action="version_log", video="Sleep", platform="Pinterest", status="planned")
    assert "Updated" in trk(s, action="version_edit", id=2, status="posted", note="pin done")
    gaps = card(trk(s, action="gaps", video="Sleep"))["rows"][0]
    assert gaps[1] == "Pinterest, TikTok" and "Blog" in gaps[3]
    assert "2 posted versions of 1 videos" in trk(s, action="tracker_stats")
    assert card(trk(s, action="tracker_stats"))["kind"] == "chart"
    assert card(trk(s, action="tracker_export"))["kind"] == "file"
    assert (tmp_path / "repurpose" / "repurpose-tracker.csv").read_text().startswith("id,video")
    assert "confirm" in trk(s, action="version_remove", id=1)
    assert "Removed" in trk(s, action="version_remove", id=1, confirmed=True)
    with pytest.raises(ValueError):
        trk(s, action="version_edit", id=99)


def test_platforms_set(s):
    assert trk(s, action="platforms_set", platforms=["TikTok", "Blog"]) == "Tracking TikTok, Blog."
    trk(s, action="version_log", video="Sleep", platform="TikTok")
    assert card(trk(s, action="gaps"))["rows"][0][3] == "Blog"
    assert "TikTok, YouTube Shorts" in trk(s, action="platforms_set", platforms=[])


def test_evergreen(s):
    assert trk(s, action="evergreen_due") == "Nothing is due for a re-post in the next two weeks."
    assert "2027-01-30" in trk(s, action="evergreen_mark", video="Sleep", months=4, date="2026-09-30")
    trk(s, action="evergreen_mark", video="Old one", months=3, date="2026-05-01")
    due = card(trk(s, action="evergreen_due"))
    assert due["kind"] == "list" and len(due["items"]) == 1 and "overdue" in due["items"][0]["label"]
    rows = card(trk(s, action="evergreen_list"))["rows"]
    assert [r[0] for r in rows] == ["Old one", "Sleep"] and rows[1][2] == "later"
    assert "Next one 2026-12-29" in trk(s, action="evergreen_done", video="old")
    assert "confirm" in trk(s, action="evergreen_remove", video="Sleep")
    assert "Removed" in trk(s, action="evergreen_remove", video="Sleep", confirmed=True)
    with pytest.raises(ValueError):
        trk(s, action="evergreen_done", video="ghost")


def test_add_months_clamps():
    assert rt.add_months(date(2026, 1, 31), 1) == date(2026, 2, 28)
    assert rt.add_months(date(2026, 11, 15), 3) == date(2027, 2, 15)


# ---- Registry ----

def test_registered_and_through_tools(s):
    names = {t["name"] for t in tools.tool_definitions(s)} if callable(getattr(tools, "tool_definitions", None)) else set()
    for mod in (rs, rf, rp, rt):
        for t in mod.tool_definitions():
            assert t["input_schema"]["additionalProperties"] is False
            assert set(t["input_schema"]["properties"]["action"]["enum"]) == set(mod.ACTIONS)
    assert names == set() or {"repurpose_subtitles", "repurpose_tracker"} <= names
    out = asyncio.run(tools._run_tool("repurpose_formats", {"action": "titles", "topic": "sleep"}, s, None))
    assert isinstance(out, screen.Shown) and out.card["kind"] == "table"
    out = asyncio.run(tools._run_tool("repurpose_tracker", {"action": "tracker_show"}, s, None))
    assert "Nothing is tracked" in out
