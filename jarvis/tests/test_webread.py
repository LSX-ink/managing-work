import asyncio

import httpx
import pytest

import memory
import screen
import tools
import webread_explain as explain
import webread_extract as ex
import webread_page as outline
import webread_read as reader
import webread_store as store
from config import Settings

LONG = ("The committee, having considered the various proposals that had been submitted by several interested parties "
        "over the course of the preceding financial year, ultimately decided to postpone the announcement of its "
        "recommendations until further consultation could be undertaken.")
PAGE = f"""<html lang="en-GB"><head><title>Big Story | News Site</title><script>var x = "ignore me";</script></head><body>
<nav><a href="/home">Home</a><a href="/sport">Sport</a></nav>
<div class="cookie-banner"><p>We use cookies to improve your experience, please accept all cookies now.</p></div>
<article><h1>Big Story</h1>
<p>The town council met on Tuesday evening to talk about the new library and the extraordinary cost of building it.</p>
<h2>What happens next</h2>
<p>{LONG}</p>
<p>Residents can read the plans <a href="/plans">here</a> or see the <a href="https://other.test/map">interactive map</a>.</p>
<img src="/img/library.jpg" alt="An artist drawing of the new library"><img src="/img/crowd.jpg">
<img src="/img/line.png" alt="" width="200">
<ul><li>Vote on the budget is next month and everyone is welcome</li></ul>
</article><footer><p>All rights reserved. Copyright somebody.</p><a href="/about">About us</a></footer></body></html>"""
NOTE = "# My notes\n\nThis is the first paragraph of my notes, which is long enough.\n\n## Part two\n\nSecond paragraph of the notes goes here, with more words."
DICT = [{"word": "extraordinary", "phonetic": "/ɪkˈstrɔːdɪnəri/", "meanings": [{"partOfSpeech": "adjective",
        "definitions": [{"definition": "Very unusual or remarkable."}]}]}]


def handler(request: httpx.Request) -> httpx.Response:
    host = request.url.host
    if host == "news.test":
        return httpx.Response(200, text=PAGE, headers={"content-type": "text/html; charset=utf-8"})
    if host == "plain.test":
        return httpx.Response(200, text=NOTE, headers={"content-type": "text/plain"})
    if host == "pdf.test":
        return httpx.Response(200, content=b"%PDF", headers={"content-type": "application/pdf"})
    if host == "empty.test":
        return httpx.Response(200, text="<html><body><p>Hi</p></body></html>", headers={"content-type": "text/html"})
    if host == "api.dictionaryapi.dev":
        if request.url.path.endswith("/extraordinary"):
            return httpx.Response(200, json=DICT)
        return httpx.Response(404, json={})
    return httpx.Response(404)


@pytest.fixture(autouse=True)
def public_links(monkeypatch):
    async def ok(url):
        if "192.168." in url:
            raise ValueError("home network")
    monkeypatch.setattr(memory, "check_public", ok)


@pytest.fixture
def s(tmp_path):
    return Settings(memory_dir=str(tmp_path))


def call(module, name, s, **args):
    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            return await module.run_tool(name, args, s, http)
    return asyncio.run(go())


def rd(s, **args):
    return call(reader, "web_read_aloud", s, **args)


def ex_(s, **args):
    return call(explain, "web_read_explain", s, **args)


def ol(s, **args):
    return call(outline, "web_read_outline", s, **args)


def test_registered_and_small():
    names = {t["name"] for t in tools.client_tool_definitions(Settings())}
    for module, actions in ((reader, reader.ACTIONS), (explain, explain.ACTIONS), (outline, outline.ACTIONS)):
        assert module in tools.ABILITIES
        (tool,) = module.tool_definitions()
        assert tool["name"] in names and tool["input_schema"]["additionalProperties"] is False
        assert set(tool["input_schema"]["properties"]["action"]["enum"]) == set(actions)
    assert "webread-reader" in screen.EXTRA_KINDS


def test_extraction_drops_menus_cookies_and_scripts():
    page = ex.parse_html(PAGE, "https://news.test/story")
    text = ex.plain(page["blocks"])
    assert page["title"] == "Big Story | News Site" and page["lang"] == "en-GB"
    assert "town council" in text and "What happens next" in text
    for junk in ("ignore me", "cookies", "All rights reserved", "Sport"):
        assert junk not in text
    assert [b["k"] for b in page["blocks"]][:2] == ["h1", "p"]


def test_read_page_pops_up_the_reader(s):
    shown = rd(s, action="page", url="https://news.test/story")
    assert isinstance(shown, screen.Shown) and shown.card["kind"] == "webread-reader"
    data = shown.card["data"]
    assert data["title"] == "Big Story | News Site" and data["site"] == "news.test"
    assert data["paras"][0] == {"t": "Big Story", "h": True} and data["start"] == 0
    assert data["prefs"]["tint"] == "cream"
    assert "press Read aloud" in shown and shown.count(".") <= 2
    assert [b["label"] for b in shown.card["buttons"]] == ["Simple version", "Summary"]


def test_read_from_heading_and_paragraph(s):
    shown = rd(s, action="page", url="https://news.test/story", from_heading="what happens")
    assert shown.card["data"]["start"] == 2 and "from paragraph 3" in shown
    assert rd(s, action="page", url="https://news.test/story", from_paragraph=4).card["data"]["start"] == 3
    with pytest.raises(ValueError, match="couldn't find a heading"):
        rd(s, action="page", url="https://news.test/story", from_heading="nothing like it")


def test_read_pasted_text_and_file(s, tmp_path):
    shown = rd(s, action="text", text=NOTE, title="Notes")
    assert [p["h"] for p in shown.card["data"]["paras"]] == [True, False, True, False]
    (tmp_path / "Ideas").mkdir()
    (tmp_path / "Ideas" / "diary.md").write_text(NOTE, encoding="utf-8")
    shown = rd(s, action="file", folder="Ideas", filename="diary")
    assert shown.card["data"]["filename"] == "diary.md" and shown.card["data"]["folder"] == "Ideas"
    (tmp_path / "Ideas" / "scan.pdf").write_bytes(b"%PDF-1.4")
    with pytest.raises(ValueError, match="PDF"):
        rd(s, action="file", folder="Ideas", filename="scan.pdf")
    with pytest.raises(ValueError, match="web link"):
        rd(s, action="page")


def test_page_problems_are_friendly(s):
    for url, words in (("https://pdf.test/a.pdf", "isn't a web page"), ("https://empty.test/", "readable words"),
                       ("https://gone.test/", "answered 404"), ("http://192.168.1.1/", "home network")):
        with pytest.raises(ValueError, match=words):
            rd(s, action="page", url=url)


def test_save_resume_places_and_forget(s):
    said = rd(s, action="save_place", url="https://news.test/story#top", index=3, total=4, title="Big Story")
    assert "paragraph 3 of 4" in said
    assert store.load(s)["places"]["https://news.test/story"]["index"] == 2
    shown = rd(s, action="resume")
    assert shown.card["kind"] == "webread-reader" and shown.card["data"]["start"] == 2
    assert "paragraph 3 of 4" in shown
    listing = rd(s, action="places")
    assert listing.card["kind"] == "list" and listing.card["items"][0]["say"] == "Carry on reading Big Story."
    assert rd(s, action="resume", title="big story").card["data"]["start"] == 2
    with pytest.raises(ValueError, match="saved place"):
        rd(s, action="resume", title="zzz")
    assert "confirm" in rd(s, action="forget_place", title="Big Story")
    assert store.load(s)["places"]
    assert "Forgot" in rd(s, action="forget_place", title="Big Story", confirmed=True)
    assert not store.load(s)["places"]
    assert "haven't saved" in rd(s, action="places")


def test_resume_a_file(s, tmp_path):
    (tmp_path / "Ideas").mkdir()
    (tmp_path / "Ideas" / "diary.md").write_text(NOTE, encoding="utf-8")
    rd(s, action="save_place", folder="Ideas", filename="diary.md", index=3, total=4, title="diary")
    shown = rd(s, action="resume", filename="diary")
    assert shown.card["data"]["start"] == 2 and shown.card["data"]["filename"] == "diary.md"
    assert (tmp_path / "reading.json").exists()


def test_reader_look_is_saved_and_clamped(s):
    shown = rd(s, action="look", size=99, spacing=2.0, tint="Blue", ruler=True, speed=0.8)
    assert shown.card["kind"] == "text"
    prefs = store.load(s)["prefs"]
    assert prefs == {"size": 48, "spacing": 2.0, "tint": "blue", "ruler": True, "speed": 0.8}
    assert rd(s, action="page", url="https://news.test/story").card["data"]["prefs"]["tint"] == "blue"
    with pytest.raises(ValueError, match="tint"):
        rd(s, action="look", tint="purple")


def test_simplify_and_summarise_hand_over_the_words(s):
    said = ex_(s, action="simplify", url="https://news.test/story")
    assert isinstance(said, str) and "plain, easy English" in said and "town council" in said and "cookies" not in said
    said = ex_(s, action="summarise", text="Some words. " * 30)
    assert "3 short bullet points" in said and "Your text" in said
    with pytest.raises(ValueError):
        ex_(s, action="simplify")


def test_readability_scores_and_flags_long_sentences(s):
    shown = ex_(s, action="readability", url="https://news.test/story")
    assert shown.card["kind"] == "table"
    rows = dict(shown.card["rows"])
    assert rows["Long sentences"] == "1 over 25 words" and "committee" in shown.card["text"]
    easy = ex_(s, action="readability", text="The cat sat on the mat. The dog ran to the man. It was fun.")
    assert float(dict(easy.card["rows"])["Reading ease"].split()[0]) > 90 and "easy" in easy
    hard = explain.score(LONG)
    assert hard["ease"] < 30 and hard["long"] == [LONG]


def test_hard_words_list_taps_to_define(s):
    shown = ex_(s, action="hard_words", url="https://news.test/story")
    labels = [i["label"] for i in shown.card["items"]]
    assert any(x.startswith("extraordinary") for x in labels)
    assert shown.card["items"][0]["say"].startswith("What does ")
    plain = ex_(s, action="hard_words", text="The cat sat on the mat.")
    assert plain.card["kind"] == "text"


def test_define_reuses_the_dictionary(s):
    shown = ex_(s, action="define", word="extraordinary")
    assert shown.card["kind"] == "text" and "Very unusual" in shown.card["text"]
    assert "Very unusual" in shown
    assert "couldn't find" in ex_(s, action="define", word="zzzzq")
    with pytest.raises(ValueError):
        ex_(s, action="define", word="")


def test_headings_outline_jumps(s):
    shown = ol(s, action="headings", url="https://news.test/story")
    items = shown.card["items"]
    assert [i["label"] for i in items] == ["Big Story", "What happens next"]
    assert items[1]["say"] == "Read https://news.test/story from the heading What happens next."
    with pytest.raises(ValueError, match="no headings"):
        outline.headings({"blocks": [{"k": "p", "t": "x" * 50}], "title": "t"})


def test_links_in_plain_words_flag_unclear_ones(s):
    shown = ol(s, action="links", url="https://news.test/story")
    labels = [i["label"] for i in shown.card["items"]]
    assert "here (unclear, goes to news.test/plans)" in labels
    assert "interactive map (other.test)" in labels
    assert any(x.endswith("[menu]") for x in labels) and shown.card["items"][0]["say"].startswith("Read the page https://")


def test_images_flag_missing_descriptions(s):
    shown = ol(s, action="images", url="https://news.test/story")
    rows = shown.card["rows"]
    assert rows[0] == ["1", "library.jpg", "An artist drawing of the new library"]
    assert rows[1][2] == "NO DESCRIPTION" and "decorative" in rows[2][2]
    assert "1 of 3" in shown.card["text"] and "1 have no description" in shown


def test_about_page(s, tmp_path):
    shown = ol(s, action="about", url="https://news.test/story")
    rows = dict(shown.card["rows"])
    assert rows["Language"] == "en-GB" and rows["Headings"] == "2" and rows["Pictures"] == "3 (1 with no description)"
    (tmp_path / "Ideas").mkdir()
    (tmp_path / "Ideas" / "diary.md").write_text(NOTE, encoding="utf-8")
    assert ol(s, action="headings", folder="Ideas", filename="diary").card["items"][0]["say"].startswith("Read the file diary.md")
    with pytest.raises(ValueError, match="Pick one"):
        ol(s, action="nope")


def test_plain_text_links_are_read_as_text(s):
    shown = rd(s, action="page", url="https://plain.test/notes.txt")
    assert shown.card["data"]["paras"][0] == {"t": "My notes", "h": True}
